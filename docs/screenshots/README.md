# Evidências de execução

- `dados_carregados_amostra.png` e `tecnologias_mais_frequentes.png` — gerados automaticamente a partir de consultas reais ao PostgreSQL, pelo script [`gerar_evidencias.py`](gerar_evidencias.py) deste diretório. Para regenerar com os dados mais recentes (precisa do `matplotlib`, que não faz parte das dependências do pipeline em si — `pip install matplotlib` dentro do venv):
  ```bash
  source venv/bin/activate
  pip install matplotlib
  python docs/screenshots/gerar_evidencias.py
  ```
- `airflow_graph_success.png` — print da interface do Airflow (`pipeline_vagas_tecnologia` → Graph) mostrando as 4 tasks em sucesso, com o histórico de execuções na mini-grade lateral.
