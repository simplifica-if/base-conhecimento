# Operação do Notion por agentes

Este guia orienta agentes IA trabalhando a partir de um checkout local deste repositório quando a tarefa envolver a base Notion operacional da Gestão de Cursos do IFPR.

## Regra principal

Para dados operacionais de gestão, o Notion é a fonte da verdade. Os JSONs em `institucional/ifpr/campi/` e `institucional/ifpr/processos-seletivos/` são artefatos públicos gerados.

Use este guia quando a solicitação envolver:

- Campi;
- Cursos;
- Documentos de Curso;
- Lifecycle de Cursos;
- Processos SEI;
- Tarefas;
- SUAP Cursos;
- Horários de Aula;
- Processos Seletivos;
- Editais de Ingresso;
- Ofertas de Ingresso.

## Autenticação padrão

Por padrão, não presuma que o Notion MCP local do usuário tem acesso a esta base.

Em geral, o MCP local do usuário estará conectado ao Notion pessoal dele, enquanto esta base Notion fica em um workspace organizacional. Portanto, o fluxo padrão para agentes é usar a API do Notion com `NOTION_TOKEN` deste projeto.

Antes de operar no Notion:

1. Verifique se existe `.env.local` na raiz do repositório.
2. Verifique se `.env.local` contém `NOTION_TOKEN=...`.
3. Se não houver token, peça ao usuário o token da integração Notion organizacional desta base.
4. Grave o token em `.env.local` no formato:

```bash
NOTION_TOKEN=secret_...
```

Nunca commite `.env.local` nem escreva o token em documentação, logs ou exemplos.

Os scripts Notion deste repositório carregam `.env.local` automaticamente quando usam `scripts/notion_client.py`.

## MCP, API e scripts locais

Ordem preferida de operação:

1. Use os scripts locais quando a tarefa já estiver coberta por eles, como exportar JSON público ou aplicar bootstrap de schema.
2. Use a API do Notion com `scripts/notion_client.py` para operações repetíveis, migrações, consultas estruturadas ou alterações em lote.
3. Use Notion MCP apenas quando estiver claro que o MCP disponível está conectado ao workspace organizacional correto e consegue acessar a página raiz desta base.

Se MCP e API divergirem, confie na API com `NOTION_TOKEN` do projeto.

## Como localizar as bases

Use `config/notion.json` como mapa operacional. Ele contém:

- `parent_page_id`: página raiz Notion da Gestão de Cursos;
- `databases.<chave>.id`: ID da database/página Notion;
- `databases.<chave>.data_source_id`: ID do data source usado para consultas e escrita;
- `databases.<chave>.title`: nome humano da base.

Não dependa apenas do nome visual da base no Notion. Use as chaves e IDs de `config/notion.json`.

Chaves atuais:

- `campi`;
- `cursos`;
- `documentos`;
- `lifecycle`;
- `processos_sei`;
- `tarefas`;
- `processos_seletivos`;
- `editais_ingresso`;
- `ofertas_ingresso`;
- `suap_cursos`;
- `horarios_aula`.

## Quando usar Notion

Use Notion quando o usuário pedir para:

- consultar ou alterar cadastro atual de campus ou curso;
- registrar ou revisar processo SEI de curso;
- criar, corrigir ou consultar evento de lifecycle;
- preencher horários de aula;
- revisar dados SUAP de cursos;
- criar ou revisar processo seletivo, edital ou oferta de ingresso;
- executar curadoria operacional que depois será publicada nos JSONs.

## Quando não usar Notion primeiro

Não comece pelo Notion quando a tarefa for:

- responder pergunta normativa geral: leia `llms.txt`;
- consultar legislação, resoluções, portarias, CNCT ou PPCs publicados;
- alterar scripts, schemas ou documentação do repositório;
- debugar geração ou validação de JSON público.

Nesses casos, use os arquivos locais e a hierarquia de fontes definida em `llms.txt`.

## Regras de escrita

Ao alterar dados no Notion:

- preserve identificadores estáveis, como `campus_id`, `curso_id`, `id_composto`, `documento_id`, `Número SEI`, `suap_curso_id` e IDs de processo seletivo;
- não crie campos técnicos de sincronização, migração ou controle interno sem necessidade operacional atual;
- não crie propriedades novas diretamente no Notion sem também avaliar `scripts/notion_bootstrap.py` e a documentação em `docs/notion-gestao-cursos.md`;
- registre fontes, datas de coleta e notas de curadoria quando a informação vier de site externo, planilha, SEI ou SUAP;
- prefira relações entre bases, não duplicação textual, quando a relação já existir no modelo;
- não edite manualmente os JSONs públicos para refletir curadoria operacional.

## Fluxos típicos

### Consultar uma base

1. Leia `config/notion.json`.
2. Obtenha o `data_source_id` da base.
3. Consulte o data source com a API do Notion ou com script local.
4. Se precisar cruzar relações, busque os registros relacionados pelos IDs de página.

### Alterar dados operacionais

1. Confirme que `NOTION_TOKEN` está disponível em `.env.local`.
2. Localize a base e o registro Notion correto.
3. Aplique a alteração via API ou MCP conectado ao workspace correto.
4. Exporte os JSONs públicos.
5. Regenere índices quando necessário.
6. Valide a base.

Comandos:

```bash
python3 scripts/notion_exportar_base_publica.py
python3 scripts/gerar_indice_ppcs.py
python3 scripts/validar_base.py
```

### Criar evento de lifecycle

1. Localize o curso em `Cursos`.
2. Localize ou crie o processo em `Processos SEI`.
3. Crie uma entrada em `Lifecycle de Cursos`.
4. Relacione o lifecycle ao curso e ao processo SEI principal.
5. Preencha classe, tipo, fase, resumo, situação resultante e campos de origem quando houver.

### Registrar processo SEI

1. Use `Número SEI` como identificador operacional.
2. Relacione o processo aos cursos e campi pertinentes.
3. Relacione os lifecycles que representam eventos na linha do tempo.
4. Mantenha `Data de abertura` e `Última movimentação` preenchidas sempre que o processo for localizado ou revisado. `Data de abertura` é a autuação/criação do processo; `Última movimentação` é a data mais recente encontrada no andamento ou nos documentos, não a conclusão administrativa.
5. Se a autuação exata não estiver disponível e você usar a primeira data documentada como aproximação, registre isso em `Observações`.
6. Escreva `Observações` em blocos curtos, com quebras de linha e marcadores, para facilitar leitura humana e reuso por agentes. Comece com uma frase simples no formato `Revisado em AAAA-MM-DD via <ferramenta ou fonte>.` Em seguida, use, quando aplicável, os blocos `Contexto`, `Evidências`, `Datas de controle` e `Observação técnica`. Não inclua caminho local de snapshot.
7. Se a informação vier de coleta automatizada, preserve `Planilha origem`, `Linhas origem`, observações ou notas relevantes.

## Documentos relacionados

- `docs/notion-gestao-cursos.md`: modelo operacional das bases.
- `docs/curadoria-metadados-institucionais.md`: regras de curadoria institucional.
- `config/notion.json`: IDs das bases Notion.
- `scripts/notion_client.py`: cliente mínimo da API Notion.
- `scripts/notion_bootstrap.py`: bootstrap e atualização de schema.
- `scripts/notion_exportar_base_publica.py`: exportação Notion para JSON público.
