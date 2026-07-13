# Screenshots pendentes

Este diretório deve conter os prints referenciados no README principal do projeto. Tire e salve com exatamente estes nomes (o README já aponta pra eles):

1. **`airflow_graph_success.png`**
   - Acesse `http://localhost:8080` (login `airflow` / `airflow`)
   - Menu **DAGs** → `pipeline_vagas_tecnologia` → aba **Graph**
   - Print mostrando as 4 tasks (`extract`, `validate`, `transform`, `load`) com contorno verde (success)

2. **`airflow_grid_success.png`**
   - Mesma DAG, aba **Grid**
   - Print mostrando o histórico de execuções (colunas coloridas por task)

Depois de salvar os dois arquivos aqui, rode a partir da raiz do projeto:

```bash
git add docs/screenshots/*.png
git commit -m "Adiciona screenshots de evidência da execução no Airflow"
git push
```

Este próprio arquivo (`docs/screenshots/README.md`) pode ser apagado depois que os prints forem adicionados.
