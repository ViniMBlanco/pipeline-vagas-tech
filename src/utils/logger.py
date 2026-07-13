"""
Utilitário de logging do pipeline.

Cobre dois destinos, propositalmente independentes:
1. Arquivo de log em disco (logs/pipeline.log) — sempre funciona, mesmo
   se o Postgres estiver fora do ar. Útil para depuração local.
2. Tabela log_execucao no Postgres (RF07) — histórico consultável do
   pipeline, usado por outras etapas/dashboards.

Uso típico em qualquer etapa (extract, validate, transform, load):

    from src.utils.logger import get_logger, registrar_log

    logger = get_logger("extract")
    logger.info("Iniciando extração...")
    registrar_log("extract", "sucesso", "Extração concluída", qtd_registros=120)
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from sqlalchemy import text

from src.utils.db import get_engine

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_LOG_DIR = _PROJECT_ROOT / "logs"
_LOG_DIR.mkdir(parents=True, exist_ok=True)
_LOG_FILE = _LOG_DIR / "pipeline.log"

_FORMATO = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"

_configurado = False


def _configurar_root() -> None:
    """Configura handlers (arquivo + console) uma única vez por processo."""
    global _configurado
    if _configurado:
        return

    formatter = logging.Formatter(_FORMATO)

    file_handler = logging.FileHandler(_LOG_FILE, encoding="utf-8")
    file_handler.setFormatter(formatter)

    # Usa sys.__stderr__ (a referência original, salva pelo interpretador
    # na inicialização) em vez de sys.stderr. Sob o Airflow, sys.stderr é
    # substituído por um objeto que redireciona escritas de volta para o
    # próprio logging: se apontássemos para ele, cada linha logada aqui
    # seria recapturada e logada de novo, causando um loop de amplificação
    # exponencial até a task falhar.
    console_handler = logging.StreamHandler(sys.__stderr__)
    console_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(file_handler)
    root.addHandler(console_handler)

    _configurado = True


def get_logger(nome_etapa: str) -> logging.Logger:
    """Retorna um logger nomeado (ex.: 'extract', 'validate') já configurado."""
    _configurar_root()
    return logging.getLogger(nome_etapa)


def registrar_log(
    etapa: str,
    status: str,
    mensagem: str,
    qtd_registros: int | None = None,
) -> None:
    """
    Insere um registro na tabela log_execucao.

    Parâmetros
    ----------
    etapa: 'extract' | 'validate' | 'transform' | 'load'
    status: 'sucesso' | 'erro' | 'alerta'
    mensagem: descrição livre do que aconteceu
    qtd_registros: quantidade de registros processados/afetados, se aplicável

    Falhas ao gravar no banco NÃO derrubam o pipeline — apenas registram
    um erro no log de arquivo, já que a etapa em si pode ter dado certo.
    """
    logger = get_logger(etapa)
    try:
        engine = get_engine()
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO log_execucao (etapa, status, mensagem, qtd_registros)
                    VALUES (:etapa, :status, :mensagem, :qtd_registros)
                    """
                ),
                {
                    "etapa": etapa,
                    "status": status,
                    "mensagem": mensagem,
                    "qtd_registros": qtd_registros,
                },
            )
    except Exception:
        logger.exception(
            "Falha ao registrar log de execução no banco (etapa=%s, status=%s)",
            etapa,
            status,
        )