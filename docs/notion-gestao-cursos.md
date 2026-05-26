# Gestão de cursos no Notion

Este documento registra o modelo operacional de gestão de Campi, Cursos, PPCs, movimentações de cursos, processos SEI, SUAP, horários de aula e processos seletivos no Notion.

## Decisões atuais

- O Notion é a fonte da verdade operacional.
- Os JSONs em `institucional/ifpr/campi/` e `institucional/ifpr/processos-seletivos/` são artefatos públicos gerados.
- Não edite os JSONs institucionais manualmente para curadoria operacional.
- O repositório mantém o exportador público, validações, normas, catálogos, PPCs convertidos e índices.
- Campos de sincronização da importação inicial foram removidos, não escondidos.

## Bases operacionais

### Campi

Cadastro institucional dos campi.

Campos principais: `Nome`, `campus_id`, `Tipo de unidade`, `Site`, `Calendário acadêmico`, `Horário de aulas`, `Status de curadoria`, `Verificado em`.

### Cursos

Cada registro representa uma oferta de curso em um campus. O vínculo operacional entre os JSONs publicados e o Notion é feito por `notion_page_id`; `campus_id` e `curso_id` seguem como identificadores semânticos públicos.

Campos principais: `Nome`, `curso_id`, `Campus`, `Nível`, `Forma de oferta`, `Modalidade`, `Situação`, `Escopo`, `URL oficial`.

Metadados SUAP ficam apenas na base `SUAP Cursos`.

### PPCs

Base operacional dos Projetos Pedagógicos de Curso. Cada registro representa um PPC associado a um curso; documentos auxiliares, matrizes isoladas, editais, resoluções e formulários não devem ser cadastrados nesta base.

Regra operacional: um curso pode ter vários PPCs históricos, mas deve haver no máximo um PPC vigente por curso.

Campos principais: `Título`, `Curso`, `Campus`, `Status`, `URL oficial`, `Markdown Link`, `Ano do documento`, `Vagas`, `Periodicidade vagas`, `Trecho fonte das vagas`, `Curadoria`, `Data curadoria`, `Observações`.

`URL oficial` registra a fonte oficial do PPC. `Markdown Link` aponta para a versão Markdown publicada, quando disponível, usando URL absoluta em `https://simplifica-if.github.io/base-conhecimento/institucional/ifpr/ppcs/...`. Na publicação JSON, esse link é convertido de volta para `ppc.markdown_path`; o status público de conversão é derivado desse campo, não de propriedades técnicas no Notion.

`Curadoria` é uma propriedade Notion do tipo `select`, usada para indicar a confiabilidade dos metadados extraídos do PPC. Use `Precisa de revisão` para extrações automáticas ou preenchimentos ainda não conferidos, `Revisado` para metadados conferidos na fonte oficial, `Inconsistente` quando houver conflito ou ambiguidade, e `Pendente` quando a informação ainda não foi localizada. `Data curadoria` registra quando essa conferência foi feita.

Metadados extraídos do PPC, como ano do documento e vagas, devem sempre ter contexto de curadoria. `Vagas` é um campo de texto: use número simples quando o PPC declarar quantidade fixa, como `40`, e intervalo quando o PPC declarar mínimo e máximo, como `20-40`. Registre junto `Trecho fonte das vagas`, `Periodicidade vagas` quando aplicável, `Curadoria` e `Data curadoria`. Na publicação JSON, o status é normalizado como `precisa_revisao`, `revisado`, `inconsistente` ou `pendente`.

### Movimentações de Cursos

Linha do tempo operacional e histórica dos cursos.

Cada mudança relevante vira um registro próprio. O eixo da linha do tempo é a relação única `Processo SEI`.

Campos principais: `Título`, `Categoria`, `Tipo`, `Situação`, `Cursos`, `Campi`, `Processo SEI`, `Data do ato`, `Início da vigência`, `Anotações`.

`Categoria` é o agrupamento amplo da movimentação, como `PPC`, `SUAP`, `cadastro`, `processo seletivo` ou `curadoria`. Use `Tipo` para a natureza administrativa específica, como abertura, ajuste, atualização, suspensão ou reversão de suspensão.

`Situação` é uma propriedade Notion do tipo `status` e representa a etapa da movimentação, como `Não iniciada`, `Triagem`, `Em instrução no campus`, `Em análise Proens`, `Em colegiados/conselhos`, `Em andamento`, `Aguardando ato/publicação`, `Concluído` ou `Arquivado`. Não use `Ativo` em movimentações: atividade, suspensão ou extinção do curso pertencem à propriedade `Situação` da base `Cursos`, não ao estado da movimentação.

`Data do ato` registra a data do ato formal que fundamenta a movimentação, como resolução, portaria, aprovação final em conselho/colegiado, despacho decisório ou publicação equivalente. Não use este campo para a autuação do processo ou para a última tramitação no SEI.

`Início da vigência` registra quando a mudança passa a produzir efeito acadêmico ou administrativo no curso, como início da oferta, início de suspensão, reversão de suspensão ou vigência de ajuste curricular. Preencha apenas quando houver evidência explícita; datas gerais de tramitação pertencem à base `Processos SEI`.

`Anotações` consolida observações de curadoria, evidências e pendências em texto curto. Evite repetir o que já está classificado em `Tipo`, remover referências internas como `Linha 12` e não registrar caminhos locais de coleta.

### Processos SEI

Entidade própria para processos administrativos associados ao histórico de cursos.

Quando a curadoria depender de dados do Sistema Eletrônico de Informações, use `../sei-cli` conforme `docs/sei-cli-operacao-agentes.md` para extrair ou inspecionar uma fotografia local do processo antes de preencher estes campos.

Campos principais: `Número SEI`, `Link SEI`, `Tipo principal`, `Status`, `Data de abertura`, `Data Última mov.`, `Última movimentação`, `Unidade responsável`, `Campi`, `Cursos`, `Movimentações de Cursos`, `Observações`, `Planilha origem`, `Linhas origem`.

`Link SEI` é uma propriedade URL para acesso rápido ao processo por usuários autenticados e autorizados no SEI. Use o formato limpo `https://sei.ifpr.edu.br/sei/controlador.php?acao=procedimento_trabalhar&id_procedimento=<id>`. Não grave URLs copiadas da barra do navegador que contenham `infra_hash`, `infra_unidade_atual` ou outros parâmetros voláteis de sessão.

`Status` é uma propriedade Notion do tipo `status`, não `select`. Use como estado geral do processo na base: `Não iniciada` para processo ainda não localizado/revisado; `Em andamento` para processo localizado sem encerramento claro; `Concluído` para processo com ato/evento principal concluído; `Cancelado` para cancelamento formal; `Arquivado` para arquivamento formal. Não use `Status` para distinguir etapas finas como instrução no campus, análise Proens ou colegiados; registre essa granularidade em `Movimentações de Cursos.Situação`.

`Data de abertura` registra a data de autuação/criação do processo no SEI. Quando a autuação exata não estiver disponível, use a primeira movimentação ou o primeiro documento datado apenas se isso estiver claro nas evidências; se for uma aproximação, registre a limitação em `Observações`.

`Data Última mov.` registra a data mais recente localizada no andamento ou nos documentos do processo. Não é data de conclusão: processos antigos podem continuar recebendo despachos, portarias, declarações ou juntadas depois do ato principal.

`Última movimentação` registra um resumo textual curto das duas movimentações mais recentes do histórico do SEI, com data em formato `DD/MM/AA`, descrição e unidade quando disponíveis. Esse campo dá contexto humano para `Data Última mov.`, especialmente quando o evento mais recente é apenas recebimento, envio ou atribuição.

Sempre atualize `Data de abertura`, `Data Última mov.` e `Última movimentação` ao localizar, baixar ou revisar um processo SEI.

`Observações` deve ser legível no próprio Notion. Prefira texto em blocos com quebras de linha e marcadores, em vez de parágrafo corrido, e use datas textuais em formato brasileiro curto `DD/MM/AA`. Comece com uma frase simples, como `Revisado em 25/05/26 via sei-cli.` Em seguida, use blocos como `Contexto` para curso, campus e origem; `Evidências` para documentos SEI citados; `Datas de controle` para justificar `Data de abertura` e `Data Última mov.`; `Observação técnica` para limitações da extração ou ressalvas. Não inclua caminho local de snapshot.

### SUAP Cursos

Base própria para metadados administrativos de cursos vindos do SUAP.

Campos principais: `Nome`, `suap_curso_id`, `SUAP ID`, `Código SUAP`, `Vagas SUAP`, `Curso`, `Diretoria SUAP`, `campus_id inferido`, `Status de vínculo`, `Fonte`, `Coletado em`, `Atualizado em`.

### Horários de Aula

Base própria para fontes de horários de aula dos campi.

Campos principais: `Nome`, `horario_aula_id`, `Campus`, `campus_id_original`, `URL`, `Título da fonte`, `Tipo de fonte`, `Período de referência`, `Status de curadoria`, `Fonte ativa?`, `Coletado em`, `Observações`.

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

A base Notion operacional já existe e é mantida diretamente no workspace organizacional. Quando o schema mudar, atualize este documento e os scripts de leitura/exportação afetados. O fluxo ativo é Notion -> JSON público.
