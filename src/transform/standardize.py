"""
Funções de padronização/transformação (RF05), separadas da orquestração
(src/transform/main.py) pelo mesmo motivo de rules.py na validação: cada
peça da transformação fica isolada e testável.

A entrada aqui é sempre a lista de vagas JÁ VALIDADAS (data/validated/),
ainda com os nomes de campo originais da API RemoteOK. A saída são
DataFrames já no formato/nome de coluna esperado pelo schema do Postgres.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

# Mapeamento: nome do campo na API RemoteOK -> nome da coluna no Postgres
MAPA_COLUNAS = {
    "id": "id_externo",
    "position": "cargo",
    "company": "empresa",
    "location": "localizacao",
    "salary_min": "salario_min",
    "salary_max": "salario_max",
    "date": "data_publicacao",
    "url": "url_vaga",
}


def montar_dataframe_vagas(vagas: list[dict[str, Any]], data_coleta: pd.Timestamp) -> pd.DataFrame:
    """
    Converte a lista de vagas validadas num DataFrame já com as colunas,
    nomes e tipos que a tabela `vagas` espera.

    Não define `tipo_vaga` a partir de nenhuma heurística sobre as tags —
    a API RemoteOK não traz um campo de tipo de vaga estruturado e
    "adivinhar" a partir de texto livre gera dado errado com confiança
    falsa. Fica NULL até existir uma fonte confiável para esse campo.
    """
    df = pd.DataFrame(vagas)

    # Garante que todas as colunas de origem existam, mesmo que faltando
    # em algum registro (evita KeyError no rename/seleção abaixo).
    for coluna_origem in MAPA_COLUNAS:
        if coluna_origem not in df.columns:
            df[coluna_origem] = pd.NA

    df = df.rename(columns=MAPA_COLUNAS)

    # id_externo e textos: string, sem espaços nas pontas
    df["id_externo"] = df["id_externo"].astype(str).str.strip()
    for coluna_texto in ("cargo", "empresa", "localizacao", "url_vaga"):
        df[coluna_texto] = df[coluna_texto].astype("string").str.strip()

    # Numéricos: converte o que der, o que não der vira NaN (não derruba o pipeline)
    df["salario_min"] = pd.to_numeric(df["salario_min"], errors="coerce")
    df["salario_max"] = pd.to_numeric(df["salario_max"], errors="coerce")

    # Data: já vem validada como ISO 8601 na etapa anterior, mas usamos
    # errors="coerce" por segurança (vira NaT em vez de derrubar o pipeline
    # caso algum formato escape da validação).
    df["data_publicacao"] = pd.to_datetime(df["data_publicacao"], errors="coerce", utc=True)

    df["moeda"] = "USD"
    df["tipo_vaga"] = pd.NA
    df["data_coleta"] = data_coleta

    colunas_finais = [
        "id_externo",
        "cargo",
        "empresa",
        "localizacao",
        "tipo_vaga",
        "salario_min",
        "salario_max",
        "moeda",
        "data_publicacao",
        "url_vaga",
        "data_coleta",
    ]
    return df[colunas_finais]


def normalizar_tecnologia(tag: str) -> str:
    """
    Forma canônica de uma tecnologia: minúsculas + sem espaço nas pontas.
    Evita que 'Python', 'python' e ' Python ' virem 3 linhas diferentes em
    `tecnologias`, já que `nome` é UNIQUE no schema.
    """
    return tag.strip().lower()


def montar_dataframes_tecnologias(
    vagas: list[dict[str, Any]],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    A partir da lista de vagas (campo 'tags'), monta:
    - tecnologias_df: lista única de tecnologias (coluna 'nome')
    - vaga_tecnologias_df: associação N:N via chaves NATURAIS
      ('id_externo' da vaga, 'tecnologia_nome'). A resolução para os IDs
      substitutos (FKs reais) acontece na etapa de LOAD, depois que
      `vagas` e `tecnologias` já foram inseridas e têm `id` gerado.
    """
    associacoes: list[dict[str, str]] = []

    for vaga in vagas:
        id_externo = str(vaga.get("id", "")).strip()
        tags = vaga.get("tags") or []
        if not isinstance(tags, list):
            continue

        for tag in tags:
            if not isinstance(tag, str) or not tag.strip():
                continue
            nome_tecnologia = normalizar_tecnologia(tag)
            associacoes.append(
                {"id_externo": id_externo, "tecnologia_nome": nome_tecnologia}
            )

    vaga_tecnologias_df = pd.DataFrame(
        associacoes, columns=["id_externo", "tecnologia_nome"]
    ).drop_duplicates()

    tecnologias_df = (
        pd.DataFrame({"nome": vaga_tecnologias_df["tecnologia_nome"].unique()})
        .sort_values("nome")
        .reset_index(drop=True)
    )

    return tecnologias_df, vaga_tecnologias_df