# Pipeline ELT - Vagas de Tecnologia (RemoteOK)

Pipeline de dados para coleta, validação, transformação e armazenamento
de vagas de tecnologia utilizando a API RemoteOK.

## Estrutura
- `src/extract` - extração da API
- `src/validate` - validação de qualidade
- `src/transform` - transformação/padronização
- `src/load` - carga no PostgreSQL
- `dags` - orquestração via Airflow
- `data/raw` - dados brutos
- `data/quarantine` - registros inválidos
- `sql` - scripts de banco

## Como rodar
1. `source venv/bin/activate`
2. `pip install -r requirements.txt`
3. Configurar `.env`
4. Rodar extração: `python src/extract/main.py`
