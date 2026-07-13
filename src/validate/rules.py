"""
Regras de validação de qualidade das vagas extraídas da RemoteOK.

Cada função `validar_*` recebe o dicionário bruto de uma vaga (como veio da
API) e retorna uma lista de mensagens de erro — lista vazia significa que a
regra passou. Isso deixa fácil adicionar/remover/ajustar regras sem mexer na
orquestração (src/validate/main.py), e também testar cada regra isolada.

Campos esperados no dicionário bruto da RemoteOK (nomes originais da API,
ainda não padronizados — a padronização/renomeação é responsabilidade da
etapa de TRANSFORMAÇÃO, não desta):
    id, position, company, location, tags, date, salary_min, salary_max, url
"""

from __future__ import annotations

from datetime import datetime
from typing import Any


def _texto_valido(valor: Any) -> bool:
    """Considera válido texto não vazio após remover espaços nas pontas."""
    return isinstance(valor, str) and valor.strip() != ""


def validar_id_externo(vaga: dict[str, Any]) -> list[str]:
    """id_externo é a chave de deduplicação (UNIQUE no banco) — obrigatório."""
    valor = vaga.get("id")
    if valor is None or str(valor).strip() == "":
        return ["id_externo (campo 'id') ausente ou vazio"]
    return []


def validar_cargo(vaga: dict[str, Any]) -> list[str]:
    if not _texto_valido(vaga.get("position")):
        return ["cargo (campo 'position') ausente ou vazio"]
    return []


def validar_empresa(vaga: dict[str, Any]) -> list[str]:
    if not _texto_valido(vaga.get("company")):
        return ["empresa (campo 'company') ausente ou vazio"]
    return []


def validar_data_publicacao(vaga: dict[str, Any]) -> list[str]:
    """A RemoteOK envia a data no formato ISO 8601 (ex: 2026-07-10T12:00:00+00:00)."""
    valor = vaga.get("date")
    if valor is None or str(valor).strip() == "":
        return ["data_publicacao (campo 'date') ausente"]
    try:
        datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
    except ValueError:
        return [f"data_publicacao (campo 'date') em formato inválido: {valor!r}"]
    return []


def validar_salario(vaga: dict[str, Any]) -> list[str]:
    """
    Salário é opcional na RemoteOK (nem toda vaga divulga). Quando presente,
    porém, precisa ser numérico, não-negativo, e min <= max.
    """
    erros: list[str] = []
    salario_min = vaga.get("salary_min")
    salario_max = vaga.get("salary_max")

    def _numero_valido(valor: Any) -> bool:
        try:
            return float(valor) >= 0
        except (TypeError, ValueError):
            return False

    if salario_min not in (None, "") and not _numero_valido(salario_min):
        erros.append(f"salario_min inválido: {salario_min!r}")
    if salario_max not in (None, "") and not _numero_valido(salario_max):
        erros.append(f"salario_max inválido: {salario_max!r}")

    if (
        not erros
        and salario_min not in (None, "")
        and salario_max not in (None, "")
        and float(salario_min) > float(salario_max)
    ):
        erros.append(
            f"salario_min ({salario_min}) maior que salario_max ({salario_max})"
        )

    return erros


def validar_url(vaga: dict[str, Any]) -> list[str]:
    """URL é opcional, mas se vier preenchida precisa parecer uma URL de verdade."""
    valor = vaga.get("url")
    if valor in (None, ""):
        return []
    if not str(valor).startswith(("http://", "https://")):
        return [f"url (campo 'url') não parece uma URL válida: {valor!r}"]
    return []


# Lista central de regras aplicadas a cada vaga. Adicionar uma nova regra de
# qualidade = escrever a função acima e incluir aqui, nada mais muda.
REGRAS = (
    validar_id_externo,
    validar_cargo,
    validar_empresa,
    validar_data_publicacao,
    validar_salario,
    validar_url,
)


def validar_vaga(vaga: dict[str, Any]) -> list[str]:
    """Roda todas as regras sobre uma vaga e retorna a lista combinada de erros."""
    erros: list[str] = []
    for regra in REGRAS:
        erros.extend(regra(vaga))
    return erros