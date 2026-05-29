# Operação do Notion por agentes

Este guia orienta agentes IA trabalhando a partir de um checkout local deste repositório quando a tarefa envolver a base Notion operacional da Gestão de Cursos do IFPR.

## Regra principal

Para dados operacionais de gestão, o Notion é a fonte da verdade, inclusive para propriedades, tipos e opções vigentes das bases. Os JSONs em `institucional/ifpr/campi/` e `institucional/ifpr/processos-seletivos/` são artefatos públicos gerados.

Use este guia quando a solicitação envolver:

- Campi;
- Cursos;
- metadados de PPC em Cursos;
- Movimentações de Cursos;
- Tarefas;
- horários dos campi;
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

1. Use os scripts locais quando a tarefa já estiver coberta por eles, como exportar JSON público, regenerar índices ou validar a base.
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

Antes de criar ou alterar registros, consulte o data source no Notion para confirmar as propriedades, tipos e opções atuais. A documentação local descreve fluxos e propriedades recorrentes, mas não substitui o schema vivo do Notion.

Chaves atuais:

- `campi`;
- `cursos`;
- `movimentacoes_cursos`;
- `tarefas`;
- `processos_seletivos`;
- `editais_ingresso`;
- `ofertas_ingresso`.

## Quando usar Notion

Use Notion quando o usuário pedir para:

- consultar ou alterar cadastro atual de campus ou curso;
- registrar ou revisar processo SEI de curso;
- criar, corrigir ou consultar movimentação de curso;
- revisar dados de horários dos campi;
- revisar dados SUAP em cursos;
- criar ou revisar processo seletivo, edital ou oferta de ingresso;
- executar curadoria operacional que depois será publicada nos JSONs.

Quando a consulta ou alteração depender de evidência do Sistema Eletrônico de Informações, leia também `docs/sei-cli-operacao-agentes.md` e use `../sei-cli` para localizar, extrair ou inspecionar o processo antes de registrar dados no Notion.

## Quando não usar Notion primeiro

Não comece pelo Notion quando a tarefa for:

- responder pergunta normativa geral: leia `llms.txt`;
- consultar legislação, resoluções, portarias, CNCT ou PPCs publicados;
- alterar scripts, schemas ou documentação do repositório;
- debugar geração ou validação de JSON público.

Nesses casos, use os arquivos locais e a hierarquia de fontes definida em `llms.txt`.

## Regras de escrita

Ao alterar dados no Notion:

- preserve identificadores estáveis, como `campus_id`, `curso_id`, `notion_page_id`, `SEI Processo`, `SUAP ID`, `SUAP Código` e IDs de processo seletivo;
- não crie campos técnicos de sincronização, migração ou controle interno sem necessidade operacional atual;
- não crie propriedades novas no Notion sem verificar o schema atual, a necessidade operacional e os scripts que leem ou exportam a base;
- se o Notion contiver um valor ou propriedade operacional legítima que a validação local rejeite, ajuste o exportador, schemas públicos ou validadores locais. Não altere o Notion apenas para caber em enumerações locais desatualizadas;
- registre fontes, datas de coleta e notas de curadoria quando a informação vier de site externo, planilha, SEI ou SUAP;
- prefira relações entre bases, não duplicação textual, quando a relação já existir no modelo;
- não edite manualmente os JSONs públicos para refletir curadoria operacional.

## Fluxos típicos

### Consultar uma base

1. Leia `config/notion.json`.
2. Obtenha o `data_source_id` da base.
3. Consulte o data source com a API do Notion ou com script local, incluindo o schema/propriedades quando isso afetar escrita, filtros ou validação.
4. Se precisar cruzar relações, busque os registros relacionados pelos IDs de página. Em `Cursos`, use `Página oficial` como URL pública do curso; scripts antigos ainda aceitam `URL oficial` como fallback.

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

### Criar movimentação de curso

1. Localize o curso em `Cursos`.
2. Crie uma entrada em `Movimentações de Cursos`.
3. Preencha tipo, situação e anotações quando houver evidências, pendências ou nuances de curadoria.
4. Quando houver processo SEI, preencha na própria movimentação `SEI Processo`, `Data de abertura SEI`, `Data Última mov. SEI`, `Última movimentação SEI` e `Observações SEI`.
5. O mesmo `SEI Processo` pode aparecer em mais de uma movimentação quando um único processo fundamentar mudanças em cursos diferentes.

### Registrar dados SEI em movimentação

1. Use `SEI Processo` como identificador operacional no formato `00000.000000/0000-00`.
2. Quando o `id_procedimento` for confirmado no SEI, faça do próprio valor de `SEI Processo` um hyperlink para a URL interna limpa do processo, no formato `https://sei.ifpr.edu.br/sei/controlador.php?acao=procedimento_trabalhar&id_procedimento=<id>`. Não grave URLs com `infra_hash`, pois esse parâmetro é volátil, e não crie propriedade separada para o link.
3. Mantenha `Data de abertura SEI`, `Data Última mov. SEI` e `Última movimentação SEI` preenchidas sempre que o processo for localizado ou revisado. `Data de abertura SEI` é a autuação/criação do processo; `Data Última mov. SEI` é a data mais recente encontrada no andamento ou nos documentos, não a conclusão administrativa. `Última movimentação SEI` é um resumo textual curto das duas movimentações mais recentes.
4. Se a autuação exata não estiver disponível e você usar a primeira data documentada como aproximação, registre isso em `Observações SEI`.
5. Escreva `Observações SEI` em blocos curtos, com quebras de linha e marcadores, para facilitar leitura humana e reuso por agentes. Em campos textuais do Notion, use datas no formato brasileiro curto `DD/MM/AA`. Comece com uma frase simples no formato `Revisado em DD/MM/AA via <ferramenta ou fonte>.` Em seguida, use, quando aplicável, os blocos `Contexto`, `Evidências`, `Datas de controle` e `Observação técnica`. Não inclua caminho local de snapshot.
6. Se a informação vier de coleta automatizada, preserve origem, linhas, observações ou notas relevantes em `Observações SEI` ou `Anotações`.

Quando usar `sei-cli`, registre `Revisado em DD/MM/AA via sei-cli.` e cite nas evidências os documentos ou eventos usados, como `SEI 1234567 (DD/MM/AA): Parecer ...`. Não grave caminhos locais do snapshot em `Observações`.

## Documentos relacionados

- `docs/notion-gestao-cursos.md`: modelo operacional das bases.
- `docs/curadoria-metadados-institucionais.md`: regras de curadoria institucional.
- `docs/sei-cli-operacao-agentes.md`: uso do `../sei-cli` para extrair e inspecionar processos SEI.
- `config/notion.json`: IDs das bases Notion.
- `scripts/notion_client.py`: cliente mínimo da API Notion.
- `scripts/notion_exportar_base_publica.py`: exportação Notion para JSON público.
