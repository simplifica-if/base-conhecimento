# Gestão de cursos no Notion

Este documento registra o modelo operacional de gestão de Campi, Cursos, PPCs, movimentações de cursos, processos SEI, SUAP, horários de aula e processos seletivos no Notion.

## Decisões atuais

- O Notion é a fonte da verdade operacional, inclusive para o schema vigente das bases.
- Os JSONs em `institucional/ifpr/campi/` e `institucional/ifpr/processos-seletivos/` são artefatos públicos gerados.
- Não edite os JSONs institucionais manualmente para curadoria operacional.
- O repositório mantém o exportador público, validações, normas, catálogos, PPCs convertidos e índices.
- Campos de sincronização da importação inicial foram removidos, não escondidos.
- Esta documentação orienta o uso esperado das bases, mas não é contrato fechado de propriedades ou valores. Antes de operar, verifique no Notion as propriedades atuais do data source indicado em `config/notion.json`.
- Se uma propriedade ou valor válido no Notion ainda não for aceito pelo exportador, schema ou validador local, ajuste o modelo local em vez de corrigir o Notion apenas para satisfazer uma enumeração desatualizada.

## Bases operacionais

### Campi

Cadastro institucional dos campi.

Verifique no Notion as propriedades atuais da base `campi`. Propriedades recorrentes usadas pelos scripts incluem `Nome`, `campus_id`, `Site`, `Calendário acadêmico` e relações com outras bases.

### Cursos

Cada registro representa uma oferta de curso em um campus. O vínculo operacional entre os JSONs publicados e o Notion é feito por `notion_page_id`; `campus_id` e `curso_id` seguem como identificadores semânticos públicos.

Verifique no Notion as propriedades e opções atuais da base `cursos`. Propriedades recorrentes usadas pelos scripts incluem `Nome`, `curso_id`, `Campus`, `Nível`, `Forma de oferta`, `Modalidade`, `Situação`, `Escopo` e `URL oficial`.

Metadados SUAP ficam apenas na base `SUAP Cursos`.

### PPCs

Base operacional dos Projetos Pedagógicos de Curso. Cada registro representa um PPC associado a um curso; documentos auxiliares, matrizes isoladas, editais, resoluções e formulários não devem ser cadastrados nesta base. O vínculo operacional entre os JSONs publicados e o Notion é feito por `notion_page_id`.

Regra operacional: um curso pode ter vários PPCs históricos, mas deve haver no máximo um PPC vigente por curso.

Verifique no Notion as propriedades e opções atuais da base `documentos` (`PPCs`). Propriedades recorrentes usadas pelos scripts incluem `Título`, `Curso`, `Campus`, `Status do PPC`, `URL oficial`, `Markdown Link`, `Ano do documento`, `Vagas`, `Periodicidade vagas`, `Trecho fonte das vagas`, `Curadoria`, `Data curadoria` e `Observações`.

`URL oficial` registra a fonte oficial do PPC. `Markdown Link` aponta para a versão Markdown publicada, quando disponível, usando URL absoluta em `https://simplifica-if.github.io/base-conhecimento/institucional/ifpr/ppcs/...`. Na publicação JSON, esse link é convertido de volta para `ppc.markdown_path`; o status público de conversão é derivado desse campo, não de propriedades técnicas no Notion.

`Curadoria` indica a confiabilidade dos metadados extraídos do PPC. Use as opções atuais disponíveis no Notion, preservando a semântica esperada: extração ainda não conferida, metadado revisado na fonte oficial, conflito/ambiguidade ou informação ainda não localizada. `Data curadoria` registra quando essa conferência foi feita.

Metadados extraídos do PPC, como ano do documento e vagas, devem sempre ter contexto de curadoria. `Vagas` é um campo de texto: use número simples quando o PPC declarar quantidade fixa, como `40`, e intervalo quando o PPC declarar mínimo e máximo, como `20-40`. Registre junto `Trecho fonte das vagas`, `Periodicidade vagas` quando aplicável, `Curadoria` e `Data curadoria`. Na publicação JSON, o status pode ser normalizado para os valores públicos esperados pelo validador local. Se o Notion passar a usar opções novas legítimas, ajuste a normalização local.

### Movimentações de Cursos

Linha do tempo operacional e histórica dos cursos.

Cada mudança relevante vira um registro próprio. O eixo da linha do tempo é a relação única `Processo SEI`.

Verifique no Notion as propriedades e opções atuais da base `movimentacoes_cursos`. Propriedades recorrentes usadas pelos scripts incluem `Título`, `Categoria`, `Tipo`, `Situação`, `Cursos`, `Campi`, `Processo SEI`, `Data do ato`, `Início da vigência` e `Anotações`.

`Categoria` é o agrupamento amplo da movimentação. `Tipo` registra a natureza administrativa específica. Consulte no Notion as opções atuais antes de criar ou alterar registros.

`Situação` é uma propriedade Notion do tipo `status` e representa a etapa da movimentação. Use as opções atuais da base no Notion. Não use esse campo para registrar atividade, suspensão ou extinção do curso: esses estados pertencem à propriedade `Situação` da base `Cursos`.

`Data do ato` registra a data do ato formal que fundamenta a movimentação, como resolução, portaria, aprovação final em conselho/colegiado, despacho decisório ou publicação equivalente. Não use este campo para a autuação do processo ou para a última tramitação no SEI.

`Início da vigência` registra quando a mudança passa a produzir efeito acadêmico ou administrativo no curso, como início da oferta, início de suspensão, reversão de suspensão ou vigência de ajuste curricular. Preencha apenas quando houver evidência explícita; datas gerais de tramitação pertencem à base `Processos SEI`.

`Anotações` consolida observações de curadoria, evidências e pendências em texto curto. Evite repetir o que já está classificado em `Tipo`, remover referências internas como `Linha 12` e não registrar caminhos locais de coleta.

### Processos SEI

Entidade própria para processos administrativos associados ao histórico de cursos.

Quando a curadoria depender de dados do Sistema Eletrônico de Informações, use `../sei-cli` conforme `docs/sei-cli-operacao-agentes.md` para extrair ou inspecionar uma fotografia local do processo antes de preencher estes campos.

Verifique no Notion as propriedades e opções atuais da base `processos_sei`. Propriedades recorrentes usadas pelos scripts incluem `Número SEI`, `Link SEI`, `Tipo principal`, `Status`, `Data de abertura`, `Data Última mov.`, `Última movimentação`, `Unidade responsável`, `Campi`, `Cursos`, `Movimentações de Cursos`, `Observações`, `Planilha origem` e `Linhas origem`.

`Link SEI` é uma propriedade URL para acesso rápido ao processo por usuários autenticados e autorizados no SEI. Use o formato limpo `https://sei.ifpr.edu.br/sei/controlador.php?acao=procedimento_trabalhar&id_procedimento=<id>`. Não grave URLs copiadas da barra do navegador que contenham `infra_hash`, `infra_unidade_atual` ou outros parâmetros voláteis de sessão.

`Status` é uma propriedade Notion do tipo `status`, não `select`. Use como estado geral do processo na base, conforme as opções atuais do Notion. Não use `Status` para distinguir etapas finas como instrução no campus, análise Proens ou colegiados; registre essa granularidade em `Movimentações de Cursos.Situação`.

`Data de abertura` registra a data de autuação/criação do processo no SEI. Quando a autuação exata não estiver disponível, use a primeira movimentação ou o primeiro documento datado apenas se isso estiver claro nas evidências; se for uma aproximação, registre a limitação em `Observações`.

`Data Última mov.` registra a data mais recente localizada no andamento ou nos documentos do processo. Não é data de conclusão: processos antigos podem continuar recebendo despachos, portarias, declarações ou juntadas depois do ato principal.

`Última movimentação` registra um resumo textual curto das duas movimentações mais recentes do histórico do SEI, com data em formato `DD/MM/AA`, descrição e unidade quando disponíveis. Esse campo dá contexto humano para `Data Última mov.`, especialmente quando o evento mais recente é apenas recebimento, envio ou atribuição.

Sempre atualize `Data de abertura`, `Data Última mov.` e `Última movimentação` ao localizar, baixar ou revisar um processo SEI.

`Observações` deve ser legível no próprio Notion. Prefira texto em blocos com quebras de linha e marcadores, em vez de parágrafo corrido, e use datas textuais em formato brasileiro curto `DD/MM/AA`. Comece com uma frase simples, como `Revisado em 25/05/26 via sei-cli.` Em seguida, use blocos como `Contexto` para curso, campus e origem; `Evidências` para documentos SEI citados; `Datas de controle` para justificar `Data de abertura` e `Data Última mov.`; `Observação técnica` para limitações da extração ou ressalvas. Não inclua caminho local de snapshot.

### SUAP Cursos

Base própria para metadados administrativos de cursos vindos do SUAP.

Verifique no Notion as propriedades atuais da base `suap_cursos`. Propriedades recorrentes usadas pelos scripts incluem `Nome`, `SUAP ID`, `Código SUAP`, `Vagas SUAP`, `Curso`, `Coletado em` e `Atualizado em`. No JSON público, o vínculo operacional com a página Notion é publicado em `cursos[].suap.notion_page_id`.

### Horários de Aula

Base própria para fontes de horários de aula dos campi.

Verifique no Notion as propriedades e opções atuais da base `horarios_aula`. Propriedades recorrentes usadas pelos scripts incluem `Nome`, `horario_aula_id`, `Campus`, `campus_id_original`, `URL`, `Título da fonte`, `Tipo de fonte`, `Período de referência`, `Status de curadoria`, `Fonte ativa?`, `Coletado em` e `Observações`.

### Processos seletivos

Processos seletivos formam um módulo próprio conectado a `Campi`, `Cursos` e `Tarefas`.

- `Processos Seletivos`: uma página por campanha/ano de ingresso.
- `Editais de Ingresso`: uma página por edital dentro de um processo seletivo.
- `Ofertas de Ingresso`: uma página por oferta de vagas em edital/processo seletivo.

Ofertas de ingresso não criam movimentação de curso automaticamente. Quando uma oferta revelar divergência relevante no cadastro de curso, a equipe pode criar tarefa e movimentação de `Curadoria de cadastro`.

### Tarefas

Base única da equipe.

Nem toda tarefa cria movimentação. Templates formais, como suspensão, abertura, reversão, extinção ou ajuste de curso, devem criar ou exigir vínculo com um item de movimentação em situação inicial.

## Publicação

O exportador Notion gera os JSONs públicos usados pela base de conhecimento:

```bash
python3 scripts/notion_exportar_base_publica.py
```

Depois de exportar, regenere índices de PPCs quando a alteração afetar cursos, documentos ou caminhos de PPC:

```bash
python3 scripts/gerar_indice_ppcs.py
```

Valide a base:

```bash
python3 scripts/validar_base.py
```

## Schema Notion

A base Notion operacional já existe e é mantida diretamente no workspace organizacional. O schema vigente deve ser consultado no próprio Notion, via API/data source configurado em `config/notion.json`.

Quando o schema mudar, atualize os scripts de leitura/exportação, schemas públicos e validações afetadas. Atualize esta documentação apenas quando a mudança alterar uma regra operacional ou um fluxo de trabalho; não repita listas fechadas de propriedades que possam ser conferidas no Notion. O fluxo ativo é Notion -> JSON público.
