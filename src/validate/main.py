"""
Etapa de VALIDAÇÃO do pipeline ELT (RF03 / RF04).

Responsabilidades:
- Ler o arquivo RAW mais recente gerado pela extração (data/raw/)
- Aplicar as regras de qualidade definidas em src/validate/rules.py
- Detectar duplicidade de id_externo dentro do próprio lote
- Separar os registros em:
    - válidos     -> data/validated/ (entrada da próxima etapa: transformação)
    - inválidos   -> data/quarantine/ (guardados COM o motivo da rejeição,
                      para auditoria — RNF02/RNF03)
- Registrar logs de execução em arquivo e na tabela log_execucao (RF07)

Uso:
    python -m src.validate.main
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from config.settings import QUARANTINE_DIR, RAW_DIR, VALIDATED_DIR  # noqa: E402
from src.utils.logger import get_logger, registrar_log  # noqa: E402
from src.validate.rules import validar_vaga  # noqa: E402

logger = get_logger("validate")


class ValidationError(Exception):
    """Erro irrecuperável na etapa de validação (ex.: nenhum RAW encontrado)."""


def localizar_raw_mais_recente() -> Path:
    """Encontra o arquivo RAW mais recente pelo nome (timestamp no próprio nome)."""
    arquivos = sorted(RAW_DIR.glob("remoteok_raw_*.json"))
    if not arquivos:
        raise ValidationError(
            f"Nenhum arquivo RAW encontrado em {RAW_DIR}. Rode a extração primeiro."
        )
    return arquivos[-1]


def carregar_raw(caminho: Path) -> list[dict[str, Any]]:
    with caminho.open("r", encoding="utf-8") as f:
        dados = json.load(f)

    # O primeiro item do payload da RemoteOK costuma ser um aviso legal,
    # não uma vaga — mesmo filtro já aplicado na extração (defensivo aqui
    # também, caso o RAW tenha sido gerado por outra fonte/execução).
    if dados and isinstance(dados[0], dict) and "legal" in dados[0]:
        dados = dados[1:]

    return dados


def detectar_duplicatas(vagas: list[dict[str, Any]]) -> set[int]:
    """
    Retorna os índices (posição na lista) das vagas cujo id_externo já
    apareceu antes no mesmo lote. Mantém a primeira ocorrência como válida
    e marca as repetições seguintes como inconsistentes (RF04).
    """
    contagem_vistos: Counter[str] = Counter()
    indices_duplicados: set[int] = set()

    for indice, vaga in enumerate(vagas):
        id_externo = str(vaga.get("id"))
        contagem_vistos[id_externo] += 1
        if contagem_vistos[id_externo] > 1:
            indices_duplicados.add(indice)

    return indices_duplicados


def separar_validos_invalidos(
    vagas: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Aplica as regras de qualidade + checagem de duplicidade e retorna
    (validos, invalidos). Cada inválido recebe o campo extra
    '_erros_validacao' com a lista de motivos da rejeição.
    """
    indices_duplicados = detectar_duplicatas(vagas)

    validos: list[dict[str, Any]] = []
    invalidos: list[dict[str, Any]] = []

    for indice, vaga in enumerate(vagas):
        erros = validar_vaga(vaga)
        if indice in indices_duplicados:
            erros.append("id_externo duplicado dentro do mesmo lote extraído")

        if erros:
            vaga_com_motivo = {**vaga, "_erros_validacao": erros}
            invalidos.append(vaga_com_motivo)
        else:
            validos.append(vaga)

    return validos, invalidos


def salvar_lote(dados: list[dict[str, Any]], diretorio: Path, prefixo: str) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    caminho = diretorio / f"{prefixo}_{timestamp}.json"
    with caminho.open("w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
    return caminho


def run() -> tuple[Path, Path | None]:
    """
    Executa a etapa de validação de ponta a ponta.
    Retorna (caminho_validados, caminho_quarantine_ou_None).
    """
    try:
        caminho_raw = localizar_raw_mais_recente()
        logger.info("Lendo RAW: %s", caminho_raw)

        vagas = carregar_raw(caminho_raw)
        logger.info("Total de registros lidos: %d", len(vagas))

        validos, invalidos = separar_validos_invalidos(vagas)
        logger.info(
            "Validação concluída: %d válidos, %d inválidos", len(validos), len(invalidos)
        )

        caminho_validados = salvar_lote(validos, VALIDATED_DIR, "vagas_validadas")
        logger.info("Válidos salvos em %s", caminho_validados)

        caminho_quarantine = None
        if invalidos:
            caminho_quarantine = salvar_lote(invalidos, QUARANTINE_DIR, "quarantine")
            logger.warning(
                "%d registro(s) enviado(s) para quarentena: %s",
                len(invalidos),
                caminho_quarantine,
            )

        status = "alerta" if invalidos else "sucesso"
        registrar_log(
            etapa="validate",
            status=status,
            mensagem=(
                f"{len(validos)} válidos ({caminho_validados.name}), "
                f"{len(invalidos)} em quarentena"
                + (f" ({caminho_quarantine.name})" if caminho_quarantine else "")
            ),
            qtd_registros=len(validos),
        )

        return caminho_validados, caminho_quarantine

    except ValidationError as exc:
        logger.error("Validação falhou definitivamente: %s", exc)
        registrar_log(
            etapa="validate",
            status="erro",
            mensagem=str(exc),
            qtd_registros=0,
        )
        raise


if __name__ == "__main__":
    run()