# Gestão de cursos no Notion

Este documento registra o modelo operacional de gestão de Campi, Cursos, documentos, lifecycle, processos SEI, SUAP, horários de aula e processos seletivos no Notion.

## Decisões atuais

- O Notion é a fonte da verdade operacional.
- Os JSONs em `institucional/ifpr/campi/` e `institucional/ifpr/processos-seletivos/` são artefatos públicos gerados.
- Não edite os JSONs institucionais manualmente para curadoria operacional.
- O repositório mantém o bootstrap do schema Notion, o exportador público, validações, normas, catálogos, PPCs convertidos e índices.
- Campos de sincronização da importação inicial foram removidos, não escondidos.

## Bases operacionais

### Campi

Cadastro institucional dos campi.

Campos principais: `Nome`, `campus_id`, `Tipo de unidade`, `Site`, `Calendário acadêmico`, `Horário de aulas`, `Status de curadoria`, `Verificado em`.

### Cursos

Cada registro representa uma oferta de curso em um campus, identificada por `campus_id/curso_id`.

Campos principais: `Nome`, `curso_id`, `id_composto`, `Campus`, `Nível`, `Tipo de oferta`, `Modalidade`, `Situação`, `Escopo`, `URL oficial`.

Metadados SUAP ficam apenas na base `SUAP Cursos`.

### Documentos de Curso

Base própria para PPCs e documentos relacionados ao curso.

Regra operacional: um curso pode ter vários documentos, mas deve haver no máximo um PPC vigente por curso.

### Lifecycle de Cursos

Linha do tempo operacional e histórica dos cursos.

Cada mudança relevante vira um registro próprio. O eixo da linha do tempo é a relação única `Processo SEI`.

Campos principais: `Título`, `Classe`, `Tipo`, `Situação`, `Cursos`, `Campi`, `Processo SEI`, `Situação resultante`, `Anotações`.

`Situação` é uma propriedade Notion do tipo `status` e representa a etapa do evento de lifecycle, como `Não iniciada`, `Triagem`, `Em instrução no campus`, `Em análise Proens`, `Em colegiados/conselhos`, `Em andamento`, `Aguardando ato/publicação`, `Concluído` ou `Arquivado`. Não use `Ativo` em lifecycle: atividade, suspensão ou extinção do curso pertencem à propriedade `Situação` da base `Cursos`, não ao estado do evento.

`Anotações` consolida observações de curadoria, evidências e pendências em texto curto. Evite repetir o que já está classificado em `Tipo`, remover referências internas como `Linha 12` e não registrar caminhos locais de coleta.

### Processos SEI

Entidade própria para processos administrativos associados ao histórico de cursos.

Campos principais: `Número SEI`, `Tipo principal`, `Status`, `Data de abertura`, `Última movimentação`, `Unidade responsável`, `Campi`, `Cursos`, `Lifecycle de Cursos`, `Observações`, `Planilha origem`, `Linhas origem`.

`Status` é uma propriedade Notion do tipo `status`, não `select`. Use como estado geral do processo na base: `Não iniciada` para processo ainda não localizado/revisado; `Em andamento` para processo localizado sem encerramento claro; `Concluído` para processo com ato/evento principal concluído; `Cancelado` para cancelamento formal; `Arquivado` para arquivamento formal. Não use `Status` para distinguir etapas finas como instrução no campus, análise Proens ou colegiados; registre essa granularidade em `Lifecycle de Cursos.Situação`.

`Data de abertura` registra a data de autuação/criação do processo no SEI. Quando a autuação exata não estiver disponível, use a primeira movimentação ou o primeiro documento datado apenas se isso estiver claro nas evidências; se for uma aproximação, registre a limitação em `Observações`.

`Última movimentação` registra a data mais recente localizada no andamento ou nos documentos do processo. Não é data de conclusão: processos antigos podem continuar recebendo despachos, portarias, declarações ou juntadas depois do ato principal. Sempre atualize `Data de abertura` e `Última movimentação` ao localizar, baixar ou revisar um processo SEI.

`Observações` deve ser legível no próprio Notion. Prefira texto em blocos com quebras de linha e marcadores, em vez de parágrafo corrido. Comece com uma frase simples, como `Revisado em 2026-05-25 via sei-cli.` Em seguida, use blocos como `Contexto` para curso, campus e origem; `Evidências` para documentos SEI citados; `Datas de controle` para justificar `Data de abertura` e `Última movimentação`; `Observação técnica` para limitações da extração ou ressalvas. Não inclua caminho local de snapshot.

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

Ofertas de ingresso não criam lifecycle de curso automaticamente. Quando uma oferta revelar divergência relevante no cadastro de curso, a equipe pode criar tarefa e lifecycle de `Curadoria de cadastro`.

### Tarefas

Base única da equipe.

Nem toda tarefa cria lifecycle. Templates formais, como suspensão, abertura, reversão, extinção ou ajuste de curso, devem criar ou exigir vínculo com um item de lifecycle em situação inicial.

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

## Bootstrap

Crie uma integração Notion, compartilhe a página raiz com ela e configure as variáveis:

```bash
export NOTION_PARENT_PAGE_ID=367f5b131dbd803eb664f38a3ce8d8f9
export NOTION_TOKEN=...
```

Bootstrap do schema:

```bash
python3 scripts/notion_bootstrap.py --dry-run
python3 scripts/notion_bootstrap.py
```

Os antigos scripts de importação JSON -> Notion foram removidos. O fluxo ativo é Notion -> JSON público.
