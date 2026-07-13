"""
Etapa de EXTRAÇÃO do pipeline ELT (RF01 / RF02).

Responsabilidades:
- Consumir a API pública da RemoteOK (https://remoteok.com/api)
- Tratar falhas de rede/HTTP com retry + backoff exponencial (RNF04)
- Salvar o JSON bruto, sem qualquer transformação, em data/raw/
  (permite auditoria e reprocessamento — RNF02)
- Registrar logs de execução em arquivo e na tabela log_execucao (RF07)

Uso:
    python -m src.extract.main
    # ou, dentro do venv, a partir da raiz do projeto:
    python src/extract/main.py
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

# Permite rodar tanto via `python -m src.extract.main` quanto
# `python src/extract/main.py` a partir da raiz do projeto.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from config.settings import (  # noqa: E402
    MAX_RETRIES,
    RAW_DIR,
    REMOTEOK_API_URL,
    REMOTEOK_HEADERS,
    REQUEST_TIMEOUT_SECONDS,
    RETRY_BACKOFF_SECONDS,
)
from src.utils.logger import get_logger, registrar_log  # noqa: E402

logger = get_logger("extract")


class ExtractionError(Exception):
    """Erro irrecuperável na etapa de extração (após esgotar as tentativas)."""


def fetch_jobs() -> list[dict[str, Any]]:
    """
    Busca as vagas na API RemoteOK, com retry e backoff exponencial.

    A API retorna uma lista onde o primeiro elemento costuma ser um aviso
    legal/metadado (contém a chave "legal"), não uma vaga de fato. Esse
    elemento é filtrado aqui para que o RAW já contenha só registros de vaga
    — mas o payload original completo também é preservado no arquivo salvo,
    para auditoria total.
    """
    ultima_excecao: Exception | None = None

    for tentativa in range(1, MAX_RETRIES + 1):
        try:
            logger.info(
                "Buscando vagas na RemoteOK (tentativa %d/%d)...",
                tentativa,
                MAX_RETRIES,
            )
            resposta = requests.get(
                REMOTEOK_API_URL,
                headers=REMOTEOK_HEADERS,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            resposta.raise_for_status()

            dados = resposta.json()

            if not isinstance(dados, list) or len(dados) == 0:
                raise ExtractionError(
                    f"Resposta da API em formato inesperado: {type(dados)}"
                )

            logger.info("Extração bem-sucedida: %d itens recebidos.", len(dados))
            return dados

        except (requests.RequestException, ValueError, ExtractionError) as exc:
            ultima_excecao = exc
            logger.warning(
                "Falha na tentativa %d/%d: %s", tentativa, MAX_RETRIES, exc
            )
            if tentativa < MAX_RETRIES:
                espera = RETRY_BACKOFF_SECONDS * (2 ** (tentativa - 1))
                logger.info("Aguardando %ds antes da próxima tentativa...", espera)
                time.sleep(espera)

    raise ExtractionError(
        f"Falha ao extrair dados da RemoteOK após {MAX_RETRIES} tentativas"
    ) from ultima_excecao


def separar_metadado(dados: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """Separa o item de aviso legal (se presente) das vagas propriamente ditas."""
    if dados and isinstance(dados[0], dict) and "legal" in dados[0]:
        return dados[0], dados[1:]
    return None, dados


def save_raw(dados: list[dict[str, Any]]) -> Path:
    """Salva o payload bruto (tal como recebido da API) em data/raw/."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    caminho = RAW_DIR / f"remoteok_raw_{timestamp}.json"

    with caminho.open("w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

    logger.info("RAW salvo em %s", caminho)
    return caminho


def run() -> Path:
    """Executa a etapa de extração de ponta a ponta e retorna o caminho do RAW salvo."""
    try:
        dados_completos = fetch_jobs()
        _, vagas = separar_metadado(dados_completos)

        caminho_raw = save_raw(dados_completos)

        registrar_log(
            etapa="extract",
            status="sucesso",
            mensagem=f"RAW salvo em {caminho_raw.name}",
            qtd_registros=len(vagas),
        )
        return caminho_raw

    except ExtractionError as exc:
        logger.error("Extração falhou definitivamente: %s", exc)
        registrar_log(
            etapa="extract",
            status="erro",
            mensagem=str(exc),
            qtd_registros=0,
        )
        raise


if __name__ == "__main__":
    run()