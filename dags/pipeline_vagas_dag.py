"""
DAG do pipeline de vagas de tecnologia (RemoteOK -> PostgreSQL).

Encadeia: extract -> validate -> transform -> load.

Sobre DB_HOST: o .env do projeto continua com DB_HOST=localhost, sem
nenhuma alteração (assim o pipeline continua rodando normalmente fora do
Docker, no venv). Dentro do container do Airflow, porém, "localhost"
aponta para o próprio container, não para o host onde o PostgreSQL do
projeto está rodando nativamente. Por isso sobrescrevemos a variável de
ambiente aqui, ANTES de qualquer import de código de src/, apenas para a
execução dentro do Airflow.
"""
import os
import sys
from datetime import datetime

# Precisa vir antes de qualquer import de src.*, porque src/utils/db.py
# lê DB_HOST do ambiente no momento em que é importado (engine singleton).
os.environ["DB_HOST"] = "host.docker.internal"

# Permite "from src.extract.main import main" etc., já que src/ está
# montado em /opt/airflow/src (ver docker-compose.yaml).
sys.path.insert(0, "/opt/airflow")

from airflow import DAG
from airflow.operators.python import PythonOperator

default_args = {
    "owner": "vinicius",
    "retries": 1,
}


# Imports de src.* ficam dentro das funções (lazy import), não no topo do
# arquivo. Isso garante que os.environ["DB_HOST"] já esteja setado antes
# do engine do SQLAlchemy ser criado, e evita que o parser do Airflow
# (que importa este arquivo periodicamente) precise ter as libs do
# projeto disponíveis fora do momento de execução da task.

def _run_extract():
    from src.extract.main import run
    run()


def _run_validate():
    from src.validate.main import run
    run()


def _run_transform():
    from src.transform.main import run
    run()


def _run_load():
    from src.load.main import run
    run()


with DAG(
    dag_id="pipeline_vagas_tecnologia",
    description="Extrai, valida, transforma e carrega vagas da RemoteOK no PostgreSQL",
    schedule="@daily",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args=default_args,
    tags=["vagas-tech", "elt"],
) as dag:

    extract = PythonOperator(task_id="extract", python_callable=_run_extract)
    validate = PythonOperator(task_id="validate", python_callable=_run_validate)
    transform = PythonOperator(task_id="transform", python_callable=_run_transform)
    load = PythonOperator(task_id="load", python_callable=_run_load)

    extract >> validate >> transform >> load
