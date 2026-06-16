# Gestão de cursos no Notion

Este documento resume o modelo operacional atual das bases Notion da Gestão de Cursos do IFPR.

## Princípios

- O Notion é a fonte operacional de verdade para campi, cursos, metadados de PPC, horários dos campi, movimentações, processos seletivos, editais e ofertas de ingresso.
- Os JSONs em `institucional/ifpr/campi/` e `institucional/ifpr/processos-seletivos/` são artefatos públicos gerados a partir do Notion.
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

## Publicação

Depois de alterar dados institucionais no Notion:

```bash
python3 scripts/notion_exportar_base_publica.py
python3 scripts/gerar_indice_ppcs.py
python3 scripts/validar_base.py
```

O fluxo ativo é sempre Notion -> JSON público.
