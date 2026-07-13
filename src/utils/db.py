"""
Utilitário central de conexão com o PostgreSQL do projeto.

Lê as credenciais do arquivo .env (na raiz do projeto) e expõe:
- get_engine(): retorna um SQLAlchemy Engine (com pool simples)
- get_connection(): context manager de conveniência para uma conexão

Variáveis esperadas no .env:
    DB_HOST=localhost
    DB_PORT=5432
    DB_NAME=vagas_tech
    DB_USER=vagas_user
    DB_PASSWORD=sua_senha
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Connection, Engine

# Carrega o .env a partir da raiz do projeto, independente de onde o
# script for chamado (evita depender do cwd atual).
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_PROJECT_ROOT / ".env")

_ENGINE: Engine | None = None


def _build_url() -> str:
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME", "vagas_tech")
    user = os.getenv("DB_USER", "vagas_user")
    password = os.getenv("DB_PASSWORD", "")

    faltantes = [
        var
        for var, val in {
            "DB_NAME": name,
            "DB_USER": user,
            "DB_PASSWORD": password,
        }.items()
        if not val
    ]
    if faltantes:
        raise RuntimeError(
            f"Variáveis de ambiente ausentes no .env: {', '.join(faltantes)}"
        )

    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}"


def get_engine() -> Engine:
    """Retorna um Engine único (singleton) para reaproveitar o pool de conexões."""
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = create_engine(_build_url(), pool_pre_ping=True, future=True)
    return _ENGINE


@contextmanager
def get_connection() -> Iterator[Connection]:
    """Context manager que já cuida de fechar a conexão ao sair do bloco."""
    engine = get_engine()
    conn = engine.connect()
    try:
        yield conn
    finally:
        conn.close()    