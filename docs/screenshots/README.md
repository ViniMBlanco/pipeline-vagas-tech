# Evidências de execução

- `dados_carregados_amostra.png` e `tecnologias_mais_frequentes.png` — gerados automaticamente a partir de consultas reais ao PostgreSQL, pelo script [`gerar_evidencias.py`](gerar_evidencias.py) deste diretório. Para regenerar com os dados mais recentes (precisa do `matplotlib`, que não faz parte das dependências do pipeline em si — `pip install matplotlib` dentro do venv):
  ```bash
  source venv/bin/activate
  pip install matplotlib
  python docs/screenshots/gerar_evidencias.py
  ```

## Pendente (opcional): screenshots do Airflow

Ainda faltam os 2 prints da interface do Airflow referenciados no README principal. Tire e salve com exatamente estes nomes:

1. **`airflow_graph_success.png`**
   - Acesse `http://localhost:8080` (login `airflow` / `airflow`)
   - Menu **DAGs** → `pipeline_vagas_tecnologia` → aba **Graph**
   - Print mostrando as 4 tasks (`extract`, `validate`, `transform`, `load`) com contorno verde (success)

2. **`airflow_grid_success.png`**
   - Mesma DAG, aba **Grid**
   - Print mostrando o histórico de execuções (colunas coloridas por task)

Depois de salvar os dois arquivos aqui:

```bash
git add docs/screenshots/*.png
git commit -m "Adiciona screenshots de evidência da execução no Airflow"
git push
```
