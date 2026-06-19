# Instruções para agentes

Este repositório contém uma base de conhecimento local do IFPR com normas, catálogos, PPCs, metadados institucionais e painéis derivados. A fonte da base fica em `base-conhecimento/`; a saída publicável é gerada em `site/`.

Também contém skills operacionais em `skills/`. Ao fazer alterações em qualquer skill, leia primeiro o `README.md` da própria skill, quando existir. Use esse arquivo para entender propósito, fluxo de uso, comandos de manutenção e convenções locais antes de editar scripts, fichas, prompts, testes ou documentação. Se a alteração envolver base gerada ou índice consolidado, procure no `README.md` da skill o comando de regeneração ou validação correspondente e execute-o antes de concluir.

## Consulta local da base

Para consultas, respostas a perguntas ou uso desta base como fonte por LLM, use primeiro os arquivos locais deste checkout. Não substitua arquivos locais por URLs públicas quando o conteúdo estiver disponível no repositório.

Use os manifestos locais como ponto de entrada:

- `base-conhecimento/manifest.json`: normas, legislação, resoluções, portarias, notas técnicas e referências gerais.
- `base-conhecimento/institucional_manifest.json`: coleções institucionais do IFPR.
- `base-conhecimento/catalogos_manifest.json`: catálogos publicados, incluindo o CNCT.
- `base-conhecimento/institucional/ifpr/ppcs/index.json`: índice dos PPCs convertidos.

Os campos `path` dos manifestos são relativos a `base-conhecimento/`. Ao abrir um arquivo indicado por manifesto, prefixe o caminho com `base-conhecimento/`.

Procedimento recomendado:

1. Consulte o manifesto local adequado e filtre por `title`, `aliases`, `keywords`, `ementa`, `orgao`, `ano`, `status_vigencia`, campus, curso, nível ou tipo de oferta.
2. Abra os arquivos locais indicados no campo `path`, dentro de `base-conhecimento/`.
3. Para normas, legislação e resoluções, use os Markdown em `base-conhecimento/normas/` como fonte principal e cite o título, a fonte oficial registrada no front matter e o artigo, seção ou item usado.
4. Para metadados institucionais, use os JSONs em `base-conhecimento/institucional/ifpr/`.
5. Para CNCT, use `base-conhecimento/catalogos/cnct/manifest.json`, `base-conhecimento/catalogos/cnct/index.json` e, quando necessário, os arquivos em `base-conhecimento/catalogos/cnct/cursos/`.
6. Para PPCs, use `base-conhecimento/institucional/ifpr/ppcs/index.json`, os índices de seções em `base-conhecimento/institucional/ifpr/ppcs/secoes/` e depois abra o Markdown completo do PPC antes de redigir resposta substantiva.
7. Use busca online apenas quando o dado necessário não existir na base local, quando a pergunta exigir atualização externa ou quando for preciso confirmar informação em fonte oficial. Ao usar fonte externa, deixe isso explícito.

PPCs servem como exemplos institucionais observados, não como fonte normativa obrigatória. Em elaboração, revisão ou comparação de PPC, combine PPCs similares com normas vigentes da base e, para cursos técnicos, com o CNCT.

## Curadoria e operação

Para tarefas de curadoria de metadados institucionais, especialmente campi e cursos, leia primeiro:

- [Curadoria de metadados institucionais](base-conhecimento/docs/curadoria-metadados-institucionais.md)

Para solicitações sobre dados operacionais no Notion, como Campi, Cursos, metadados de PPC, Movimentações de Cursos, horários dos campi, Processos Seletivos, Editais ou Ofertas de Ingresso, leia primeiro:

- [Operação do Notion por agentes](base-conhecimento/docs/notion-operacao-agentes.md)

Para perguntas, conferências ou curadoria que dependam de dados do Sistema Eletrônico de Informações (SEI), use o repositório irmão `../sei-cli` como ferramenta operacional e leia primeiro:

- [Uso do sei-cli por agentes](base-conhecimento/docs/sei-cli-operacao-agentes.md)

Por padrão, use a API do Notion com `NOTION_TOKEN` do projeto. Não presuma que o Notion MCP local do usuário acessa esta base, pois ele pode estar conectado ao Notion pessoal do usuário. Se `NOTION_TOKEN` não estiver disponível, peça ao usuário o token da integração Notion organizacional e grave em `.env.local`.

Depois de alterar dados institucionais no Notion, rode:

```bash
python3 scripts/notion_exportar_base_publica.py
python3 scripts/gerar_indice_ppcs.py
python3 scripts/validar_base.py
python3 scripts/gerar_site.py
```

Depois de alterar normas, catálogos, PPCs convertidos ou manifestos locais, rode:

```bash
python3 scripts/validar_base.py
python3 scripts/gerar_site.py
```

Depois de alterar skills, rode os testes ou validações da skill afetada. Para a skill `analise-ppc`, use:

```bash
python3 -m pytest skills/analise-ppc/tests
```
