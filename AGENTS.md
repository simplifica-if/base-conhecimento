# Instruções para agentes

Este repositório contém uma base de conhecimento local do IFPR com normas, catálogos, PPCs, metadados institucionais e painéis derivados.

## Consulta local da base

Para consultas, respostas a perguntas ou uso desta base como fonte por LLM, use primeiro os arquivos locais deste checkout. Não substitua arquivos locais por URLs públicas quando o conteúdo estiver disponível no repositório.

Use os manifestos locais como ponto de entrada:

- `manifest.json`: normas, legislação, resoluções, portarias, notas técnicas e referências gerais.
- `institucional_manifest.json`: coleções institucionais do IFPR.
- `catalogos_manifest.json`: catálogos publicados, incluindo o CNCT.
- `institucional/ifpr/ppcs/index.json`: índice dos PPCs convertidos.

Procedimento recomendado:

1. Consulte o manifesto local adequado e filtre por `title`, `aliases`, `keywords`, `ementa`, `orgao`, `ano`, `status_vigencia`, campus, curso, nível ou tipo de oferta.
2. Abra os arquivos locais indicados no campo `path`.
3. Para normas, legislação e resoluções, use os Markdown em `normas/` como fonte principal e cite o título, a fonte oficial registrada no front matter e o artigo, seção ou item usado.
4. Para metadados institucionais, use os JSONs em `institucional/ifpr/`.
5. Para CNCT, use `catalogos/cnct/manifest.json`, `catalogos/cnct/index.json` e, quando necessário, os arquivos em `catalogos/cnct/cursos/`.
6. Para PPCs, use `institucional/ifpr/ppcs/index.json`, os índices de seções em `institucional/ifpr/ppcs/secoes/` e depois abra o Markdown completo do PPC antes de redigir resposta substantiva.
7. Use busca online apenas quando o dado necessário não existir na base local, quando a pergunta exigir atualização externa ou quando for preciso confirmar informação em fonte oficial. Ao usar fonte externa, deixe isso explícito.

PPCs servem como exemplos institucionais observados, não como fonte normativa obrigatória. Em elaboração, revisão ou comparação de PPC, combine PPCs similares com normas vigentes da base e, para cursos técnicos, com o CNCT.

## Curadoria e operação

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

Depois de alterar normas, catálogos, PPCs convertidos ou manifestos locais, rode:

```bash
python3 scripts/validar_base.py
```
