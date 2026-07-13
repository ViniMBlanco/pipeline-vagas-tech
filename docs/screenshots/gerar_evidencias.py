"""
Gera imagens de evidência (docs/screenshots/) a partir de consultas reais
ao PostgreSQL do projeto. Não usa dados fictícios — reflete o estado atual
do banco no momento em que é executado.

Uso (com o venv do projeto ativado, a partir da raiz do projeto):
    python docs/screenshots/gerar_evidencias.py
"""

import sys
from pathlib import Path

SCREENSHOTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCREENSHOTS_DIR.parents[1]))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from sqlalchemy import text  # noqa: E402

from src.utils.db import get_engine  # noqa: E402

engine = get_engine()

with engine.connect() as conn:
    rows = conn.execute(
        text(
            """
            SELECT cargo, empresa, localizacao, data_publicacao::date
            FROM vagas
            WHERE localizacao IS NOT NULL AND localizacao != ''
            ORDER BY data_publicacao DESC
            LIMIT 8
            """
        )
    ).fetchall()

    counts = conn.execute(
        text(
            """
            SELECT (SELECT COUNT(*) FROM vagas),
                   (SELECT COUNT(*) FROM tecnologias),
                   (SELECT COUNT(*) FROM vaga_tecnologias)
            """
        )
    ).fetchone()

    top_tech = conn.execute(
        text(
            """
            SELECT t.nome, COUNT(*) AS qtd
            FROM vaga_tecnologias vt
            JOIN tecnologias t ON t.id = vt.tecnologia_id
            GROUP BY t.nome
            ORDER BY qtd DESC
            LIMIT 10
            """
        )
    ).fetchall()


def truncar(s, n):
    s = str(s)
    return s if len(s) <= n else s[: n - 1] + "…"


# --- 1. Amostra da tabela vagas ---
fig, ax = plt.subplots(figsize=(11, 4.5))
ax.axis("off")
ax.set_title(
    f"Tabela vagas — PostgreSQL (vagas_tech)   |   Total: {counts[0]} vagas · "
    f"{counts[1]} tecnologias · {counts[2]} associações",
    fontsize=11,
    fontweight="bold",
    pad=14,
    loc="left",
)

col_labels = ["Cargo", "Empresa", "Localização", "Publicada em"]
table_data = [
    [truncar(r[0], 40), truncar(r[1], 30), truncar(r[2], 25), str(r[3])] for r in rows
]

tbl = ax.table(
    cellText=table_data,
    colLabels=col_labels,
    cellLoc="left",
    colLoc="left",
    loc="upper left",
    colWidths=[0.4, 0.28, 0.22, 0.14],
)
tbl.auto_set_font_size(False)
tbl.set_fontsize(9)
tbl.scale(1, 1.8)

for (row, _col), cell in tbl.get_celld().items():
    if row == 0:
        cell.set_facecolor("#2c3e50")
        cell.set_text_props(color="white", fontweight="bold")
    else:
        cell.set_facecolor("#f4f6f7" if row % 2 == 0 else "white")

plt.tight_layout()
plt.savefig(SCREENSHOTS_DIR / "dados_carregados_amostra.png", dpi=150, bbox_inches="tight")
plt.close()

# --- 2. Tecnologias mais frequentes ---
nomes = [r[0] for r in top_tech][::-1]
qtds = [r[1] for r in top_tech][::-1]

fig, ax = plt.subplots(figsize=(8, 5))
bars = ax.barh(nomes, qtds, color="#2980b9")
ax.set_title(
    "Tecnologias mais frequentes nas vagas carregadas (PostgreSQL)",
    fontsize=11,
    fontweight="bold",
)
ax.set_xlabel("Quantidade de vagas")
ax.bar_label(bars, padding=3, fontsize=9)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
plt.tight_layout()
plt.savefig(SCREENSHOTS_DIR / "tecnologias_mais_frequentes.png", dpi=150, bbox_inches="tight")
plt.close()

print("OK - imagens geradas em", SCREENSHOTS_DIR)
