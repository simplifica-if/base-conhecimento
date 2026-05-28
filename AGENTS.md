# Instruções para agentes

Este repositório contém uma base de conhecimento do IFPR com normas e metadados institucionais.

Para tarefas de consulta, resposta a perguntas ou uso desta base como fonte por LLM, leia primeiro:

- [Instruções públicas para LLMs](llms.txt)

Esse arquivo define a hierarquia de fontes, os manifestos principais, o procedimento de consulta e as regras para uso de normas, metadados institucionais, catálogos e PPCs.

Para tarefas de curadoria de metadados institucionais, especialmente campi e cursos, leia primeiro:

- [Curadoria de metadados institucionais](docs/curadoria-metadados-institucionais.md)

Para solicitações sobre dados operacionais no Notion, como Campi, Cursos, metadados de PPC, Movimentações de Cursos, horários dos campi, Processos Seletivos, Editais ou Ofertas de Ingresso, leia primeiro:

- [Operação do Notion por agentes](docs/notion-operacao-agentes.md)

Para perguntas, conferências ou curadoria que dependam de dados do Sistema Eletrônico de Informações (SEI), use o repositório irmão `../sei-cli` como ferramenta operacional e leia primeiro:

- [Uso do sei-cli por agentes](docs/sei-cli-operacao-agentes.md)

Por padrão, use a API do Notion com `NOTION_TOKEN` do projeto. Não presuma que o Notion MCP local do usuário acessa esta base, pois ele pode estar conectado ao Notion pessoal do usuário. Se `NOTION_TOKEN` não estiver disponível, peça ao usuário o token da integração Notion organizacional e grave em `.env.local`.

Depois de alterar dados institucionais no Notion, rode:

```bash
python3 scripts/notion_exportar_base_publica.py
python3 scripts/gerar_indice_ppcs.py
python3 scripts/validar_base.py
```
