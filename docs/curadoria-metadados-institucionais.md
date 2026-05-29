# Curadoria de metadados institucionais

Este documento reúne regras práticas para manter metadados institucionais do IFPR no Notion e publicar os JSONs desta base.

## Fonte operacional

O Notion é a fonte operacional de verdade para campi, cursos, metadados de PPC, horários dos campi, movimentações de cursos, processos seletivos, editais e ofertas de ingresso. O schema vigente também está no Notion: antes de escrever, confira propriedades, tipos e opções no data source indicado em `config/notion.json`.

Os arquivos em `institucional/ifpr/campi/` e `institucional/ifpr/processos-seletivos/` são artefatos públicos gerados. Não os edite manualmente para curadoria operacional.

Depois de alterar dados institucionais no Notion, rode:

```bash
python3 scripts/notion_exportar_base_publica.py
python3 scripts/gerar_indice_ppcs.py
python3 scripts/validar_base.py
```

Se o Notion contiver uma propriedade ou opção operacional legítima que a validação local rejeite, ajuste o exportador, schemas ou validadores locais.

## Organização da base

Use `docs/` apenas para documentação de apoio à manutenção e curadoria. Conteúdos destinados à consulta pública devem ficar na coleção temática correspondente, como `normas/`, `catalogos/`, `institucional/ifpr/referencias/`, `institucional/ifpr/campi/` ou `institucional/ifpr/processos-seletivos/`.

Para referências institucionais transversais do IFPR que não sejam cadastro de campus, PPC ou processo seletivo, use `institucional/ifpr/referencias/` e atualize o índice da coleção quando necessário.

## Cursos

Cada registro em `Cursos` representa uma oferta de curso em um campus.

Ao pesquisar cursos em páginas dos campi:

1. Prefira fontes oficiais do IFPR.
2. Quando existir, use a origem `https://ifpr.edu.br/<campus_id>/`.
3. Em sites WordPress do IFPR, use a REST API para localizar páginas: `https://ifpr.edu.br/<campus_id>/wp-json/wp/v2/pages?per_page=100`.
4. Use a página oficial do curso para preencher nome, nível, forma de oferta, modalidade, situação, escopo e URL.
5. Não cadastre páginas auxiliares, notícias, páginas históricas ou ofertas temporárias como cursos ativos sem evidência clara de vigência atual.
6. Para FIC e programas institucionais, preserve a distinção entre curso regular, oferta temporária e programa conforme o modelo vigente no Notion e no JSON público.

## SUAP

Metadados administrativos do SUAP ficam diretamente na base `Cursos`.

Use estas propriedades:

- `SUAP ID`;
- `SUAP Código`;
- `SUAP Vagas`;
- `SUAP Coletado em`;
- `SUAP Atualizado em`.

No JSON público, esses dados aparecem em `cursos[].suap`. `cursos[].suap.vagas` representa vagas cadastradas no sistema acadêmico. Não confunda com:

- `cursos[].ppc.metadados.vagas`, que vem do PPC;
- `processos-seletivos[].ofertas[].vagas`, que vem de edital de ingresso.

Para relatórios brutos do SUAP com coluna `DIRETORIA`, use `institucional/ifpr/referencias/suap-diretorias.json` como apoio para associar diretoria a `campus_id`. Não trate esse mapeamento como coluna obrigatória no Notion.

## Horários de aula

Registre a fonte principal de horários diretamente na base `Campi`. Como a informação muda por período letivo, preencha sempre `Horários Coletado em`.

Registre:

- `Horários URL`, quando houver uma fonte confiável;
- `Horários Coletado em`, sempre que a busca for revisada.

Aceite fontes externas, como Google Sheets ou Edupage, somente quando forem apontadas pelo site oficial do campus. Não use horário de atendimento, monitorias, ônibus, laboratórios ou secretaria como substituto de horário das aulas.

## PPCs

Quando a página oficial do curso indicar o Projeto Pedagógico de Curso, registre o PPC vigente diretamente no registro do curso.

Regras:

1. Use como fonte primária a página oficial do curso.
2. Aceite documentos descritos como PPC, Projeto Pedagógico do Curso, Projeto Político Pedagógico do Curso ou Plano de Curso equivalente.
3. Não use matriz curricular, edital, resolução, formulário, manual, notícia ou documento auxiliar como substituto de PPC.
4. Quando houver mais de um PPC, registre como vigente o documento mais recente ou explicitamente marcado como vigente.
5. Registre `PPC URL oficial` com HTTPS absoluto.
6. Registre `PPC Markdown Link` quando o PPC convertido existir.
7. Registre ano do documento e vagas nas propriedades `PPC ...` somente com evidência textual e status de curadoria.

`PPC Vagas` é campo textual: use número simples, como `40`, ou intervalo, como `20-40`. A publicação normaliza esses dados em `ppc.metadados.vagas`.

PPCs históricos, quando forem relevantes para o histórico administrativo do curso, devem ser documentados em `Movimentações de Cursos` e nas evidências SEI.

Para converter PDFs em Markdown, use `scripts/converter_ppcs_markdown.py`. Depois de converter ou alterar PPCs, regenere os índices:

```bash
python3 scripts/gerar_indice_ppcs.py
python3 scripts/validar_base.py
```

## Movimentações e SEI

Use `Movimentações de Cursos` para registrar processos administrativos associados ao histórico do curso, como abertura, ajuste, atualização, suspensão, reversão de suspensão ou extinção.

Quando a curadoria depender do Sistema Eletrônico de Informações, leia `docs/sei-cli-operacao-agentes.md` e use `../sei-cli`.

Regras:

1. Registre processos SEI no nível da movimentação, não dentro de `ppc`.
2. Use `SEI Processo` no formato `00000.000000/0000-00`.
3. Quando o processo tiver link confirmado, faça do próprio valor de `SEI Processo` um hyperlink para a URL limpa no formato `https://sei.ifpr.edu.br/sei/controlador.php?acao=procedimento_trabalhar&id_procedimento=<id>`.
4. Mantenha `Data de abertura SEI`, `Data Última mov. SEI` e `Última movimentação SEI` atualizadas quando o processo for revisado.
5. Use `Data do ato` para o ato formal que fundamenta a movimentação.
6. Use `Início da vigência` apenas quando houver evidência de efeito acadêmico ou administrativo.
7. Atualize `Cursos.Situação` quando a situação atual do curso decorrer da movimentação.
8. Escreva `Observações SEI` em blocos curtos, com datas em `DD/MM/AA`, evidências e limitações da coleta.

## Processos seletivos

Use:

- `Processos Seletivos` para a campanha ou ano de ingresso;
- `Editais de Ingresso` para cada edital;
- `Ofertas de Ingresso` para cada oferta de vagas.

Regras:

1. Não registre vagas de processo seletivo dentro do cadastro do curso.
2. Sempre que possível, relacione a oferta ao curso e ao campus.
3. Preserve a fonte oficial do edital ou anexo em `ofertas[].fonte.url`.
4. Use `trecho_fonte` para evidenciar a quantidade de vagas.
5. Quando houver cotas, registre total e detalhamento.

## Índices globais de PPCs

A coleção `institucional/ifpr/ppcs/` contém PPCs convertidos e índices derivados:

- `institucional/ifpr/ppcs/index.json`;
- `institucional/ifpr/ppcs/secoes/*.jsonl`.

Esses arquivos são gerados automaticamente. Não os edite manualmente; ajuste a origem no Notion, no JSON de campus ou no Markdown convertido e rode novamente os comandos de publicação.
