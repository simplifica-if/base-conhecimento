# Gestão de cursos no Notion

Este documento resume o modelo operacional atual das bases Notion da Gestão de Cursos do IFPR.

## Princípios

- O Notion é a fonte operacional de verdade para campi, cursos, metadados de PPC, horários dos campi, movimentações, processos seletivos, editais e ofertas de ingresso.
- O Notion também mantém bases operacionais auxiliares para conselhos institucionais, inicialmente o Consepe, e para o diretório central de servidores associado a conselheiros e relatores.
- Os JSONs em `institucional/ifpr/campi/`, `institucional/ifpr/processos-seletivos/` e outros índices derivados são artefatos públicos gerados a partir do Notion e de fontes documentais locais.
- Não trate JSON derivado como espelho operacional. Para curadoria, consulta de estado atual ou atualização de dados de gestão, use o Notion.
- Não edite os JSONs institucionais manualmente para curadoria operacional.
- Antes de escrever no Notion, confira o schema vivo do data source em `config/notion.json`.
- Se o Notion contiver uma opção operacional legítima ainda rejeitada por scripts ou schemas locais, ajuste o modelo local.

## Bases operacionais

### Campi

Cadastro institucional dos campi. Propriedades recorrentes usadas pelos scripts: `Nome`, `campus_id`, `Site`, `Calendário acadêmico`, `Horários URL`, `Horários Coletado em` e relações com outras bases.

### Cursos

Cada registro representa uma oferta de curso em um campus. O vínculo público com o Notion é `notion_page_id`; `curso_slug` é um slug local, legível e único apenas dentro do campus. Quando for preciso identificar um curso globalmente na base pública, use o par `campus_id/curso_slug`.

Propriedades recorrentes usadas pelos scripts:

- `Nome`;
- `curso_slug`;
- `Campus`;
- `Nível`;
- `Forma de oferta`;
- `Modalidade`;
- `Situação`;
- `Página oficial`;
- `SUAP ID`;
- `SUAP Código`;
- `SUAP Vagas`;
- `SUAP Coletado em`;
- `SUAP Atualizado em`;
- `PPC URL oficial`;
- `PPC Markdown Link`;
- `PPC Ano do documento`;
- `PPC Vagas`;
- `PPC Periodicidade vagas`;
- `PPC Trecho fonte das vagas`;
- `PPC Curadoria`;
- `PPC Data curadoria`;
- `PPC Observações`.

Os metadados SUAP ficam diretamente em `Cursos`. No JSON público, são publicados em `cursos[].suap`. `SUAP Vagas` representa o dado administrativo do sistema acadêmico, não as vagas previstas no PPC nem as vagas ofertadas em edital.

`Página oficial` deve ser preenchida quando houver página pública específica do curso. Cursos em abertura podem ficar temporariamente sem URL pública no JSON até a página oficial existir.

### PPC vigente

O PPC vigente é registrado diretamente em `Cursos`. A base operacional não mantém uma tabela separada de PPCs nem múltiplos PPCs históricos por curso.

`PPC URL oficial` registra a fonte oficial do PPC. `PPC Markdown Link` aponta para a versão Markdown publicada, quando disponível. Na publicação JSON, esse link vira `ppc.markdown_path`; o status de conversão é derivado desse campo.

Metadados extraídos do PPC, como ano do documento e vagas, devem ter evidência e status de curadoria. `PPC Vagas` é texto: use número simples, como `40`, ou intervalo, como `20-40`.

PPCs históricos, quando forem relevantes para o histórico administrativo, devem ser documentados em `Movimentações de Cursos` e nas evidências SEI, não em registros paralelos de PPC.

### Movimentações de Cursos

Linha do tempo operacional e histórica dos cursos. Cada mudança relevante vira um registro próprio.

Propriedades recorrentes usadas pelos scripts: `Movimentação`, `Tipo`, `Situação`, `Curso`, `Campus`, `SEI Processo`, `Data de abertura SEI`, `Data Última mov. SEI`, `Última movimentação SEI`, `Data do ato`, `Início da vigência`, `Anotações` e `Observações SEI`.

Quando houver processo SEI, registre seus metadados na movimentação. O mesmo `SEI Processo` pode aparecer em mais de uma movimentação quando um único processo fundamentar mudanças em cursos diferentes. Quando o link interno limpo estiver confirmado, o próprio número em `SEI Processo` deve ser hyperlink para o processo no SEI, sem propriedade separada de link.

`Situação` da movimentação representa etapa de tramitação. A situação operacional do curso fica em `Cursos.Situação`.

### Pareceres de Curso

Repositório operacional de pareceres vinculados a processos SEI de movimentações de curso. Cada registro representa um documento SEI específico, não apenas o parecer vigente da movimentação, para preservar revisões e versões sucessivas.

Propriedades recorrentes usadas para curadoria: `Parecer`, `Movimentação de Curso`, `SEI Processo`, `SEI Documento`, `Tipo de parecer`, `Data do parecer`, `Autor`, `SIAPE/Autor SEI`, `Conclusão`, `Substitui parecer` e `Substituído por`.

`SEI Processo` é um roll-up da relação `Movimentação de Curso`, derivado da propriedade homônima em `Movimentações de Cursos`. Não preencha esse valor manualmente na base de pareceres.

Uma movimentação pode ter vários pareceres. Use `Substitui parecer` para encadear versões ou revisões quando um documento posterior tornar outro obsoleto. Quando o parecer for identificado por snapshot do `sei-cli`, registre número SEI, data, autoria/assinatura e processo, sem gravar caminhos locais do snapshot no Notion.

### Horários dos campi

A fonte principal de horários de aula fica diretamente em `Campi`.

Use `Horários URL` para a página, planilha ou sistema principal de horários do campus. Use `Horários Coletado em` para registrar quando a fonte foi conferida.

### Processos seletivos

Processos seletivos usam três bases conectadas:

- `Processos Seletivos`: uma página por campanha/ano de ingresso;
- `Editais de Ingresso`: uma página por edital;
- `Ofertas de Ingresso`: uma página por oferta de vagas.

Ofertas de ingresso não alteram automaticamente o cadastro de curso. Quando uma oferta revelar divergência relevante, crie tarefa ou movimentação de curadoria.

### Tarefas

Base única da equipe. Nem toda tarefa cria movimentação. Templates formais, como abertura, suspensão, reversão, extinção ou ajuste de curso, devem exigir vínculo com uma movimentação quando houver mudança administrativa do curso.

### Conselhos

Cadastro dos órgãos colegiados institucionais usados pela base operacional. O primeiro registro é o Conselho de Ensino, Pesquisa e Extensão (`Consepe`).

Propriedades recorrentes: `Name`, `Sigla`, `Status` e `Página oficial`.

Use esta base para permitir reaproveitamento do modelo com outros conselhos, como Consup, Consap ou Codir, sem codificar o Consepe diretamente nas reuniões e documentos.

### Reuniões de Conselho

Cada registro representa uma reunião de um conselho. A reunião se relaciona a `Conselhos` e concentra metadados de data, ano, tipo, status, transmissão e fonte oficial.

Propriedades recorrentes: `Name`, `Conselho`, `Data`, `Ano`, `Tipo`, `Status`, `Link YouTube`, `Página oficial`, `Fonte oficial`, `Resumo`, `Data de coleta` e `ID externo`.

Documentos e itens de pauta apontam para a reunião. Processos SEI devem ser registrados nos itens ou documentos específicos; a reunião pode receber processos por roll-up quando necessário para visualização.

### Documentos

Repositório de documentos públicos ou operacionais de conselhos institucionais, inicialmente populado com documentos do Consepe, como pautas, atas, pareceres, legislação e anexos. Quando o documento pertence a uma reunião, relacione-o em `Reunião`.

Propriedades recorrentes: `Name`, `Reunião`, `Tipo`, `Data do documento`, `Ano`, `URL oficial`, `Texto extraído`, `Resumo`, `Número`, `Processo SEI`, `Documento SEI`, `Status de extração`, `ID externo` e `Data de coleta`.

Use `Status de extração` para distinguir metadados simples de documentos já extraídos ou revisados. Em documentos SEI públicos, preserve o link oficial e registre número de parecer/documento quando disponível.

### Itens de Pauta

Base granular para perguntas sobre conselhos institucionais, inicialmente populada com itens do Consepe. Cada registro representa um assunto pautado, deliberado ou identificado em parecer/ata.

Propriedades recorrentes: `Name`, `Reunião`, `Documento de origem`, `Ordem`, `Tipo de demanda`, `Processo SEI`, `Documento SEI`, `Campus`, `Curso`, `Relator(a)`, `Conselheiros relacionados`, `Resultado`, `Trecho da pauta`, `Trecho da ata`, `Resumo`, `Palavras-chave` e `ID externo`.

O processo SEI deve ficar preferencialmente no item de pauta, pois ele se refere ao assunto analisado. Relacione `Conselheiros relacionados` quando o documento indicar relator, relatora, conselheiro ou conselheira responsável. Quando o vínculo vier apenas de relatoria em parecer e não de composição formal, mantenha o status do conselheiro como `Não confirmado`.

### Servidores

Diretório central de pessoas servidoras usadas em relações operacionais, como conselheiros e relatores. Esta base evita duplicar nomes em cada conselho ou documento.

Propriedades recorrentes: `Name`, `Nome social`, `E-mail institucional`, `Campus`, `Campus/Unidade`, `Setor`, `Cargo/Função`, `SIAPE`, `Lattes`, `Fonte`, `Status`, `Notas` e `ID externo`.

`Campus` é relação com `Campi` e deve ser preferido para dados normalizados. `Campus/Unidade` é campo textual auxiliar para preservar a origem quando a fonte menciona unidades não normalizadas ou enquanto o vínculo ainda não foi conferido.

### Conselheiros

Representa a participação de um servidor em um conselho, com mandato e função. Um mesmo servidor pode ter vários registros ao longo do tempo ou em conselhos diferentes.

Propriedades recorrentes: `Name`, `Servidor`, `Conselho`, `Segmento`, `Representação`, `Função no conselho`, `Mandato início`, `Mandato fim`, `Status`, `Ato/Portaria`, `Fonte`, `Notas` e `ID externo`.

Use `Status = Não confirmado` para resultados provisórios, relatorias sem fonte de composição ou registros incompletos. Use `Ativo` quando houver fonte de posse, mandato, homologação final ou composição vigente.

## Publicação

Depois de alterar dados institucionais no Notion:

```bash
python3 scripts/notion_exportar_base_publica.py
python3 scripts/gerar_indice_ppcs.py
python3 scripts/validar_base.py
```

O fluxo ativo é sempre Notion -> JSON público. Quando a tarefa for atualização rotineira de andamento SEI em `Movimentações de Cursos`, use antes:

```bash
python3 scripts/notion_atualizar_movimentacoes_sei.py --apply
```
