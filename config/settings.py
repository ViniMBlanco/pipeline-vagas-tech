"""
Configurações centrais do pipeline. Mantém caminhos e parâmetros num único
lugar para que extract/validate/transform/load não hardcodem nada (RNF01).
"""

from __future__ import annotations

from pathlib import Path

# Raiz do projeto (2 níveis acima deste arquivo: config/settings.py -> raiz)
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# --- Diretórios de dados ---
RAW_DIR = PROJECT_ROOT / "data" / "raw"
QUARANTINE_DIR = PROJECT_ROOT / "data" / "quarantine"
# Registros que passaram na validação, mas ainda não foram transformados/
# padronizados (RF05). Fica entre RAW e PROCESSED no fluxo do pipeline.
VALIDATED_DIR = PROJECT_ROOT / "data" / "validated"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
LOGS_DIR = PROJECT_ROOT / "logs"

for _dir in (RAW_DIR, QUARANTINE_DIR, VALIDATED_DIR, PROCESSED_DIR, LOGS_DIR):
    _dir.mkdir(parents=True, exist_ok=True)

# --- API RemoteOK ---
REMOTEOK_API_URL = "https://remoteok.com/api"

# RemoteOK bloqueia requisições sem um User-Agent "de navegador" (retorna 403).
REMOTEOK_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "application/json",
}

REQUEST_TIMEOUT_SECONDS = 15
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 2  # backoff exponencial: 2s, 4s, 8s...