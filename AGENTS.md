# Instruções para agentes

Este repositório contém uma base de conhecimento do IFPR com normas e metadados institucionais.

Para tarefas de consulta, resposta a perguntas ou uso desta base como fonte por LLM, leia primeiro:

- [Instruções públicas para LLMs](llms.txt)

Esse arquivo define a hierarquia de fontes, os manifestos principais, o procedimento de consulta e as regras para uso de normas, metadados institucionais, catálogos e PPCs.

Para tarefas de curadoria de metadados institucionais, especialmente campi e cursos, leia primeiro:

- [Curadoria de metadados institucionais](docs/curadoria-metadados-institucionais.md)

Depois de alterar dados institucionais, rode:

```bash
python3 scripts/validar_base.py
```
