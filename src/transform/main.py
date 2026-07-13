"""
Etapa de TRANSFORMAÇÃO do pipeline ELT (RF05).

Responsabilidades:
- Ler o lote de vagas mais recente já validado (data/validated/)
- Padronizar nomes de campos, tipos e formato (via src/transform/standardize.py)
- Extrair a lista de tecnologias e a associação N:N vaga-tecnologia
- Salvar os três resultados em data/processed/, prontos para a carga (RF06)
- Registrar logs de execução em arquivo e na tabela log_execucao (RF07)

Uso:
    python -m src.transform.main
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from config.settings import PROCESSED_DIR, VALIDATED_DIR  # noqa: E402
from src.transform.standardize import (  # noqa: E402
    montar_dataframe_vagas,
    montar_dataframes_tecnologias,
)
from src.utils.logger import get_logger, registrar_log  # noqa: E402

logger = get_logger("transform")

_PADRAO_TIMESTAMP = re.compile(r"(\d{8}T\d{6}Z)")


class TransformError(Exception):
    """Erro irrecuperável na etapa de transformação (ex.: nenhum lote validado encontrado)."""


def localizar_validado_mais_recente() -> Path:
    arquivos = sorted(VALIDATED_DIR.glob("vagas_validadas_*.json"))
    if not arquivos:
        raise TransformError(
            f"Nenhum arquivo de vagas validadas encontrado em {VALIDATED_DIR}. "
            "Rode a validação primeiro."
        )
    return arquivos[-1]


def extrair_timestamp_do_nome(caminho: Path) -> pd.Timestamp:
    """
    Recupera o timestamp de extração a partir do nome do arquivo
    (ex: vagas_validadas_20260713T130042Z.json), para usar como
    `data_coleta` — a data em que o pipeline efetivamente coletou o dado,
    não a data em que a transformação rodou.
    """
    match = _PADRAO_TIMESTAMP.search(caminho.name)
    if not match:
        logger.warning(
            "Não foi possível extrair timestamp do nome %s; usando horário atual.",
            caminho.name,
        )
        return pd.Timestamp(datetime.now(timezone.utc))

    dt = datetime.strptime(match.group(1), "%Y%m%dT%H%M%SZ").replace(
        tzinfo=timezone.utc
    )
    return pd.Timestamp(dt)


def carregar_validados(caminho: Path) -> list[dict]:
    with caminho.open("r", encoding="utf-8") as f:
        return json.load(f)


def salvar_csv(df: pd.DataFrame, prefixo: str, timestamp_arquivo: str) -> Path:
    caminho = PROCESSED_DIR / f"{prefixo}_{timestamp_arquivo}.csv"
    df.to_csv(caminho, index=False)
    return caminho


def run() -> tuple[Path, Path, Path]:
    """
    Executa a transformação de ponta a ponta.
    Retorna (caminho_vagas, caminho_tecnologias, caminho_vaga_tecnologias).
    """
    try:
        caminho_validado = localizar_validado_mais_recente()
        logger.info("Lendo validados: %s", caminho_validado)

        vagas = carregar_validados(caminho_validado)
        logger.info("Total de registros a transformar: %d", len(vagas))

        data_coleta = extrair_timestamp_do_nome(caminho_validado)

        df_vagas = montar_dataframe_vagas(vagas, data_coleta=data_coleta)
        df_tecnologias, df_vaga_tecnologias = montar_dataframes_tecnologias(vagas)

        logger.info(
            "Transformação concluída: %d vagas, %d tecnologias únicas, %d associações",
            len(df_vagas),
            len(df_tecnologias),
            len(df_vaga_tecnologias),
        )

        timestamp_arquivo = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        caminho_vagas = salvar_csv(df_vagas, "vagas_processadas", timestamp_arquivo)
        caminho_tecnologias = salvar_csv(
            df_tecnologias, "tecnologias_processadas", timestamp_arquivo
        )
        caminho_vaga_tecnologias = salvar_csv(
            df_vaga_tecnologias, "vaga_tecnologias_processadas", timestamp_arquivo
        )

        logger.info("Arquivos salvos em %s", PROCESSED_DIR)

        registrar_log(
            etapa="transform",
            status="sucesso",
            mensagem=(
                f"{caminho_vagas.name}, {caminho_tecnologias.name}, "
                f"{caminho_vaga_tecnologias.name}"
            ),
            qtd_registros=len(df_vagas),
        )

        return caminho_vagas, caminho_tecnologias, caminho_vaga_tecnologias

    except TransformError as exc:
        logger.error("Transformação falhou definitivamente: %s", exc)
        registrar_log(
            etapa="transform",
            status="erro",
            mensagem=str(exc),
            qtd_registros=0,
        )
        raise


if __name__ == "__main__":
    run()