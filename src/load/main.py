"""
Etapa de CARGA do pipeline ELT (RF06).

Responsabilidades:
- Ler o trio mais recente de CSVs gerados pela transformação (data/processed/)
- Upsert de `vagas` (chave: id_externo) e `tecnologias` (chave: nome)
- Resolver os IDs substitutos (surrogate keys) gerados pelo Postgres e
  usá-los para gravar a associação N:N em `vaga_tecnologias`
- Fazer tudo dentro de uma única transação: se qualquer passo falhar,
  nada fica gravado pela metade (RNF06 — persistência consistente)
- Registrar logs de execução em arquivo e na tabela log_execucao (RF07)

Uso:
    python -m src.load.main
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from config.settings import PROCESSED_DIR  # noqa: E402
from src.load.repository import (  # noqa: E402
    inserir_vaga_tecnologias,
    resolver_ids_tecnologias,
    resolver_ids_vagas,
    upsert_tecnologias,
    upsert_vagas,
)
from src.utils.db import get_engine  # noqa: E402
from src.utils.logger import get_logger, registrar_log  # noqa: E402

logger = get_logger("load")

_PADRAO_TIMESTAMP = re.compile(r"(\d{8}T\d{6}Z)")


class LoadError(Exception):
    """Erro irrecuperável na etapa de carga (ex.: nenhum lote processado encontrado)."""


def localizar_lote_processado_mais_recente() -> tuple[Path, Path, Path]:
    """
    Encontra o trio mais recente de arquivos processados (vagas, tecnologias,
    vaga_tecnologias) com o MESMO timestamp — garante que os três arquivos
    vêm da mesma execução da transformação, não de execuções misturadas.
    """
    arquivos_vagas = sorted(PROCESSED_DIR.glob("vagas_processadas_*.csv"))
    if not arquivos_vagas:
        raise LoadError(
            f"Nenhum arquivo de vagas processadas encontrado em {PROCESSED_DIR}. "
            "Rode a transformação primeiro."
        )

    caminho_vagas = arquivos_vagas[-1]
    match = _PADRAO_TIMESTAMP.search(caminho_vagas.name)
    if not match:
        raise LoadError(f"Não foi possível extrair timestamp de {caminho_vagas.name}")
    timestamp = match.group(1)

    caminho_tecnologias = PROCESSED_DIR / f"tecnologias_processadas_{timestamp}.csv"
    caminho_vaga_tecnologias = (
        PROCESSED_DIR / f"vaga_tecnologias_processadas_{timestamp}.csv"
    )

    for caminho in (caminho_tecnologias, caminho_vaga_tecnologias):
        if not caminho.exists():
            raise LoadError(
                f"Arquivo esperado não encontrado: {caminho}. "
                "O lote processado parece incompleto — rode a transformação novamente."
            )

    return caminho_vagas, caminho_tecnologias, caminho_vaga_tecnologias


def _para_registros(df: pd.DataFrame) -> list[dict]:
    """Converte um DataFrame em lista de dicts, trocando NaN/NaT por None (NULL no SQL)."""
    return df.astype(object).where(pd.notnull(df), None).to_dict(orient="records")


def run() -> dict[str, int]:
    """Executa a carga de ponta a ponta. Retorna um resumo com as contagens gravadas."""
    try:
        caminho_vagas, caminho_tecnologias, caminho_vt = (
            localizar_lote_processado_mais_recente()
        )
        logger.info("Lendo processados: %s", caminho_vagas.name)

        df_vagas = pd.read_csv(
            caminho_vagas,
            parse_dates=["data_publicacao", "data_coleta"],
            dtype={"id_externo": str},
        )
        df_tecnologias = pd.read_csv(caminho_tecnologias)
        df_vaga_tecnologias = pd.read_csv(caminho_vt, dtype={"id_externo": str})

        logger.info(
            "Registros lidos: %d vagas, %d tecnologias, %d associações",
            len(df_vagas),
            len(df_tecnologias),
            len(df_vaga_tecnologias),
        )

        engine = get_engine()
        with engine.begin() as conn:
            qtd_vagas = upsert_vagas(conn, _para_registros(df_vagas))
            qtd_tecnologias = upsert_tecnologias(
                conn, df_tecnologias["nome"].tolist()
            )

            mapa_vagas = resolver_ids_vagas(
                conn, df_vagas["id_externo"].astype(str).tolist()
            )
            mapa_tecnologias = resolver_ids_tecnologias(
                conn, df_tecnologias["nome"].tolist()
            )

            pares: list[dict[str, int]] = []
            nao_resolvidos = 0
            for linha in df_vaga_tecnologias.itertuples(index=False):
                vaga_id = mapa_vagas.get(linha.id_externo)
                tecnologia_id = mapa_tecnologias.get(linha.tecnologia_nome)
                if vaga_id is None or tecnologia_id is None:
                    nao_resolvidos += 1
                    continue
                pares.append({"vaga_id": vaga_id, "tecnologia_id": tecnologia_id})

            if nao_resolvidos:
                logger.warning(
                    "%d associação(ões) vaga-tecnologia não puderam ser resolvidas "
                    "(id_externo ou tecnologia ausente no banco após o upsert).",
                    nao_resolvidos,
                )

            qtd_associacoes = inserir_vaga_tecnologias(conn, pares)

        logger.info(
            "Carga concluída: %d vagas, %d tecnologias, %d associações gravadas",
            qtd_vagas,
            qtd_tecnologias,
            qtd_associacoes,
        )

        registrar_log(
            etapa="load",
            status="alerta" if nao_resolvidos else "sucesso",
            mensagem=(
                f"{qtd_vagas} vagas, {qtd_tecnologias} tecnologias, "
                f"{qtd_associacoes} associações"
                + (f", {nao_resolvidos} não resolvidas" if nao_resolvidos else "")
            ),
            qtd_registros=qtd_vagas,
        )

        return {
            "vagas": qtd_vagas,
            "tecnologias": qtd_tecnologias,
            "associacoes": qtd_associacoes,
            "nao_resolvidos": nao_resolvidos,
        }

    except LoadError as exc:
        logger.error("Carga falhou definitivamente: %s", exc)
        registrar_log(etapa="load", status="erro", mensagem=str(exc), qtd_registros=0)
        raise


if __name__ == "__main__":
    run()