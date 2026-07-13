"""
Funções de escrita no Postgres para a etapa de CARGA (RF06), separadas da
orquestração (src/load/main.py) pelo mesmo padrão das outras etapas.

Todas as funções recebem uma `Connection` do SQLAlchemy já aberta (dentro
de uma transação controlada por src/load/main.py) — nenhuma delas abre ou
fecha conexão sozinha, para que toda a carga aconteça atomicamente: se
qualquer passo falhar, nada é gravado (rollback automático do `engine.begin()`).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

_UPSERT_VAGAS = text(
    """
    INSERT INTO vagas (
        id_externo, cargo, empresa, localizacao, tipo_vaga,
        salario_min, salario_max, moeda, data_publicacao, url_vaga, data_coleta
    )
    VALUES (
        :id_externo, :cargo, :empresa, :localizacao, :tipo_vaga,
        :salario_min, :salario_max, :moeda, :data_publicacao, :url_vaga, :data_coleta
    )
    ON CONFLICT (id_externo) DO UPDATE SET
        cargo            = EXCLUDED.cargo,
        empresa          = EXCLUDED.empresa,
        localizacao      = EXCLUDED.localizacao,
        tipo_vaga        = EXCLUDED.tipo_vaga,
        salario_min      = EXCLUDED.salario_min,
        salario_max      = EXCLUDED.salario_max,
        moeda            = EXCLUDED.moeda,
        data_publicacao  = EXCLUDED.data_publicacao,
        url_vaga         = EXCLUDED.url_vaga,
        data_coleta      = EXCLUDED.data_coleta
    """
)

_UPSERT_TECNOLOGIAS = text(
    """
    INSERT INTO tecnologias (nome)
    VALUES (:nome)
    ON CONFLICT (nome) DO NOTHING
    """
)

_SELECT_IDS_VAGAS = text(
    "SELECT id, id_externo FROM vagas WHERE id_externo = ANY(:ids_externos)"
)

_SELECT_IDS_TECNOLOGIAS = text(
    "SELECT id, nome FROM tecnologias WHERE nome = ANY(:nomes)"
)

_INSERT_VAGA_TECNOLOGIAS = text(
    """
    INSERT INTO vaga_tecnologias (vaga_id, tecnologia_id)
    VALUES (:vaga_id, :tecnologia_id)
    ON CONFLICT (vaga_id, tecnologia_id) DO NOTHING
    """
)


def upsert_vagas(conn: Connection, registros: list[dict[str, Any]]) -> int:
    """Insere vagas novas / atualiza existentes (chave: id_externo). Retorna a quantidade processada."""
    if not registros:
        return 0
    conn.execute(_UPSERT_VAGAS, registros)
    return len(registros)


def upsert_tecnologias(conn: Connection, nomes: list[str]) -> int:
    """Insere tecnologias novas (ignora as que já existem, via ON CONFLICT DO NOTHING)."""
    if not nomes:
        return 0
    conn.execute(_UPSERT_TECNOLOGIAS, [{"nome": nome} for nome in nomes])
    return len(nomes)


def resolver_ids_vagas(conn: Connection, ids_externos: list[str]) -> dict[str, int]:
    """Retorna {id_externo: id (surrogate)} para as vagas informadas."""
    if not ids_externos:
        return {}
    resultado = conn.execute(_SELECT_IDS_VAGAS, {"ids_externos": ids_externos})
    return {linha.id_externo: linha.id for linha in resultado}


def resolver_ids_tecnologias(conn: Connection, nomes: list[str]) -> dict[str, int]:
    """Retorna {nome: id (surrogate)} para as tecnologias informadas."""
    if not nomes:
        return {}
    resultado = conn.execute(_SELECT_IDS_TECNOLOGIAS, {"nomes": nomes})
    return {linha.nome: linha.id for linha in resultado}


def inserir_vaga_tecnologias(conn: Connection, pares: list[dict[str, int]]) -> int:
    """Insere associações (vaga_id, tecnologia_id), ignorando duplicatas já existentes."""
    if not pares:
        return 0
    conn.execute(_INSERT_VAGA_TECNOLOGIAS, pares)
    return len(pares)