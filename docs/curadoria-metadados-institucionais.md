# Curadoria de metadados institucionais

Este documento registra práticas para manter metadados institucionais do IFPR, com foco em consumo por agentes IA.

## Fonte operacional

O Notion é a fonte operacional de verdade para campi, cursos, PPCs, SUAP Cursos, horários de aula, movimentações de cursos, processos SEI, processos seletivos, editais e ofertas de ingresso. Isso inclui o schema vigente das bases: propriedades, tipos e opções devem ser verificados no Notion antes de operações de escrita ou mudanças no modelo local.

Os arquivos JSON em `institucional/ifpr/campi/` e `institucional/ifpr/processos-seletivos/` são artefatos públicos gerados a partir do Notion. Não edite esses JSONs manualmente para curadoria operacional.

Quando houver divergência entre Notion e scripts, schemas ou validações locais, trate o Notion como fonte primária. Ajuste o modelo local quando o dado do Notion representar uma opção operacional legítima; corrija o Notion somente quando houver erro de curadoria sustentado por evidência.

Fluxo normal de manutenção:

1. Faça a curadoria nas bases Notion.
2. Exporte os JSONs públicos:

```bash
python3 scripts/notion_exportar_base_publica.py
```

3. Regenere os índices de PPCs quando houver mudança em cursos, PPCs ou caminhos de PPC:

```bash
python3 scripts/gerar_indice_ppcs.py
```

4. Valide a base:

```bash
python3 scripts/validar_base.py
```

## Organização de documentos da base

Use `docs/` apenas para documentação de apoio à construção, manutenção e curadoria da base, como instruções operacionais, padrões de metadados e aprendizados de curadoria.

Conteúdos destinados à consulta como parte da base de conhecimento devem ficar na coleção temática correspondente, não em `docs/`. Para referências institucionais transversais do IFPR que não sejam cadastro de campus, PPC ou processo seletivo, use `institucional/ifpr/referencias/` e atualize `institucional/ifpr/referencias/index.json`.

Exemplo: uma nota técnica sobre a Matriz Orçamentária da Rede Federal, quando usada como referência institucional para planejamento do IFPR, deve ficar em `institucional/ifpr/referencias/`, e não em `docs/`.

## Cursos nos sites dos campi

Ao pesquisar cursos em páginas de campi do IFPR, prefira fontes oficiais do próprio IFPR e registre no Notion, nas propriedades de evidência/fontes disponíveis na base vigente, as páginas usadas para preencher ou revisar os dados.

Aprendizado a partir do Campus Arapongas:

1. A URL curta ou de subdomínio do campus, como `https://arapongas.ifpr.edu.br/`, pode não ser a melhor rota técnica para coleta automatizada.
2. Quando existir, prefira a origem no multisite oficial: `https://ifpr.edu.br/<slug-do-campus>/`.
3. Para sites WordPress do IFPR, use a REST API para localizar páginas com mais eficiência:
   `https://ifpr.edu.br/<slug-do-campus>/wp-json/wp/v2/pages?per_page=100`
4. Procure a página raiz `Nossos Cursos` e use os campos `id`, `parent`, `title.rendered` e `link` para reconstruir a hierarquia.
5. Use a página pai e o texto oficial da página do curso para classificar `nivel` e `tipo_oferta`.
6. Preserve a semântica técnica de `nivel`; use `tipo_oferta` para diferenciar técnico integrado, técnico subsequente, FIC, programa institucional etc.
7. Não cadastre páginas auxiliares como curso ou oferta formal apenas por aparecerem sob `Nossos Cursos`.
8. Para FIC e outras ofertas temporárias, não presuma que a página ainda representa uma oferta ativa. Muitas páginas antigas permanecem publicadas como histórico.
9. Antes de cadastrar uma oferta temporária como ativa, verifique a página, editais, ano/turma, período de inscrição ou outro indício explícito de vigência atual.
10. Se a página parecer histórica, antiga ou sem indicação clara de oferta vigente, não inclua no cadastro principal de `cursos` como oferta ativa. A base institucional registra apenas o estado atual.
11. Use `modalidade` para distinguir a modalidade da oferta conforme as opções disponíveis no Notion.
12. Use `escopo` para indicar o escopo da oferta conforme as opções disponíveis no Notion.
13. Use `situacao` para registrar a situação operacional da oferta conforme as opções disponíveis no Notion.
14. Quando a oferta estiver vinculada a programa institucional, como Pronacampo, cadastre o programa em `programas` e suas ofertas em `programas[].ofertas`, não misturadas com os cursos regulares do campus.

## Horário das aulas nos sites dos campi

Use a base Notion `Horários de Aula` para registrar a fonte principal de consulta aos horários de aula do campus. Essa informação costuma mudar semestralmente; por isso, registre sempre `Coletado em` com data, hora e fuso da consulta.

1. Use o campo de URL da base `Horários de Aula` para a página, planilha ou sistema principal de horários do campus; confirme o nome da propriedade no Notion.
2. Use o campo de título da fonte com o título observado no menu, no HTML da página, no `h1` ou no documento externo.
3. Use o campo de período de referência quando a própria fonte indicar semestre, ano ou período, como `2026.1`, `2026 - 1º semestre` ou `2025`.
4. Classifique o tipo de fonte e o status de curadoria conforme as opções atuais disponíveis no Notion.
5. Marque como revisado quando houver fonte agregadora atual ou institucionalmente apontada pelo site do campus.
6. Marque como parcial quando só houver páginas por curso, páginas antigas, RDE ou outra fonte que não represente claramente o conjunto do campus.
7. Quando a busca não localizar fonte confiável de horário das aulas, registre essa situação conforme as opções atuais do Notion; nesse caso, omita `url` e registre a evidência em `observacoes`.
8. Aceite links externos, como Google Sheets, Edupage ou aplicativos próprios, somente quando forem apontados pelo site oficial do campus.
9. Registre no Notion as URLs consultadas para preencher ou justificar a fonte de horários, inclusive fontes parciais usadas como evidência, usando as propriedades atuais da base.
10. Não cadastre horário de atendimento, horário de servidores, monitorias, ônibus, laboratórios ou secretaria como substituto de horário das aulas.

Procedimento eficiente para agentes IA:

1. Primeiro consulte a página inicial oficial registrada em `links.site` e, quando diferente, `https://ifpr.edu.br/<campus_id>/`. Extraia links de menu cujo texto ou URL contenha termos como `horário`, `horario`, `horários`, `horarios`, `aulas`, `horário escolar` ou `horários e salas`.
2. Depois consulte a API WordPress do multisite oficial, usando buscas como `https://ifpr.edu.br/<campus_id>/wp-json/wp/v2/pages?per_page=100&search=horario%20aulas`, `horário aulas`, `horarios aula`, `horários aula`, `horario escolar` e `quadro horarios`.
3. Se a busca não retornar candidato confiável, pagine `https://ifpr.edu.br/<campus_id>/wp-json/wp/v2/pages?per_page=100&page=N` e filtre títulos e URLs pelos mesmos termos.
4. Para validar o candidato, faça uma requisição à URL e compare o título HTML, o `h1` e/ou o texto do item de menu. Priorize páginas agregadoras e fontes com indicação de período recente.
5. Quando a página oficial apontar para Google Sheets, Edupage ou outro aplicativo externo, registre esse link externo na propriedade de URL da base `Horários de Aula` e mantenha a página oficial ou inicial nas propriedades atuais de evidência, observações ou fontes do Notion.
6. Evite resultados de notícias, editais de concurso, RDE antigo, páginas de um único curso ou páginas de atendimento. Use esses links apenas em `observacoes` ou como `parcial` quando forem a melhor evidência disponível.

## Metadados do SUAP

Use a base Notion `SUAP Cursos` para registrar metadados administrativos vindos do sistema acadêmico SUAP.

1. Registre o código do curso no sistema na propriedade correspondente da base `SUAP Cursos`, verificando o schema atual no Notion.
2. Registre o ID interno do curso na propriedade correspondente.
3. Registre o número de vagas cadastradas no sistema na propriedade correspondente.
4. `cursos[].suap.vagas` representa o dado administrativo do SUAP, não a quantidade de vagas declarada no PPC.
5. Preserve `cursos[].ppc.metadados.vagas` para vagas extraídas do Projeto Pedagógico de Curso, sempre com contexto e evidência textual.

Para relatórios brutos exportados do SUAP que tragam a coluna `DIRETORIA`, use o mapeamento versionado em `institucional/ifpr/referencias/suap-diretorias.json` como referência local de apoio para associar o código da diretoria ao `campus_id` desta base. Não trate esse mapeamento como coluna obrigatória no Notion e não infira diretorias novas sem evidência nos próprios dados ou sem curadoria explícita.

## Dados SEI dos cursos

Use a base Notion `Movimentações de Cursos` para registrar processos administrativos associados ao histórico do curso, como abertura, ajuste, atualização, suspensão, reversão de suspensão ou extinção.

Quando for necessário localizar, revisar ou confirmar evidências no Sistema Eletrônico de Informações, use o repositório irmão `../sei-cli` conforme `docs/sei-cli-operacao-agentes.md`.

1. Registre processos SEI no nível do curso, não dentro de `ppc`, porque o PPC é apenas uma das informações documentais do curso.
2. Use `sei.processos[]` como lista mesmo quando houver apenas um processo, pois o curso pode acumular processos administrativos ao longo do tempo.
3. Registre o número do processo no campo correspondente, no formato `00000.000000/0000-00`.
4. Classifique a finalidade principal do processo conforme as opções atuais disponíveis no Notion.
5. Quando a situação atual do curso decorrer de processo SEI, atualize também `cursos[].situacao`, por exemplo `suspenso`.
6. Registre etapas como instrução no campus, análise Proens e colegiados em `Movimentações de Cursos.Situação`.
7. Na base Notion `Movimentações de Cursos`, mantenha `Número SEI`, `Link SEI`, `Data de abertura SEI`, `Data Última mov. SEI` e `Última movimentação SEI` atualizadas a cada revisão. `Link SEI` deve usar a URL limpa com `acao=procedimento_trabalhar&id_procedimento=<id>`, sem `infra_hash`; `Data de abertura SEI` é a autuação/criação do processo; `Data Última mov. SEI` é a data mais recente localizada no andamento ou nos documentos e não deve ser tratada como data de conclusão. `Última movimentação SEI` é um resumo textual curto das duas movimentações mais recentes.
8. Quando a data exata de autuação não estiver disponível, use a primeira data documentada somente como aproximação e registre essa limitação em `Observações SEI`.
9. Formate `Observações SEI` em blocos escaneáveis, com quebras de linha e bullets. Em campos textuais do Notion, use datas no formato brasileiro curto `DD/MM/AA`. Comece com uma frase simples no formato `Revisado em DD/MM/AA via <ferramenta ou fonte>.` Em seguida, use blocos como `Contexto`, `Evidências`, `Datas de controle` e `Observação técnica` quando houver conteúdo para eles. Não inclua caminho local de snapshot.
10. Use `status_curadoria`, `revisado_em` e, quando disponível, `trecho_fonte` para registrar a evidência usada na curadoria.

Exemplo:

```json
"sei": {
  "processos": [
    {
      "numero": "23411.005166/2020-38",
      "tipo": "abertura",
      "status_curadoria": "revisado",
      "revisado_em": "2026-05-21"
    },
    {
      "numero": "23411.011730/2025-66",
      "tipo": "suspensão",
      "status_curadoria": "revisado",
      "revisado_em": "2026-05-21"
    }
  ]
}
```

## Processos seletivos

Use as bases Notion `Processos Seletivos`, `Editais de Ingresso` e `Ofertas de Ingresso` para registrar vagas efetivamente ofertadas em editais de ingresso. Os arquivos em `institucional/ifpr/processos-seletivos/` são gerados para publicação.

1. Não registre vagas de processo seletivo dentro do JSON do campus.
2. `cursos[].ppc.metadados.vagas` representa vagas previstas no PPC.
3. `cursos[].suap.vagas` representa vagas cadastradas no sistema acadêmico.
4. `processos-seletivos[].ofertas[].vagas` representa vagas ofertadas no edital daquele ano de ingresso.
5. Quando possível, vincule a oferta ao curso do campus por relação no Notion e preserve `campus_id`/`curso_id` nos artefatos públicos; se ainda não houver correspondência confiável, registre o nome do curso e mantenha o vínculo pendente de curadoria conforme as propriedades atuais.
6. Preserve a fonte oficial do edital ou anexo em `ofertas[].fonte.url` e use `trecho_fonte` para registrar a evidência textual da quantidade de vagas.
7. Quando houver distribuição por cotas, registre o total em `vagas.quantidade` e o detalhamento em `cotas[]`.

## Links para PPC dos cursos

Quando a página oficial do curso indicar o Projeto Pedagógico de Curso, registre os dados no campo opcional `ppc` do item em `cursos`. O PDF oficial fica em `ppc.url`, e o Markdown convertido, quando existir, fica versionado à parte e referenciado no Notion em `Markdown Link`.

1. Use como fonte primária a própria página oficial cadastrada em `cursos[].url`.
2. Aceite links descritos como PPC, Projeto Pedagógico do Curso, Projeto Político Pedagógico do Curso ou Plano de Curso equivalente.
3. Não use matriz curricular, edital, resolução, formulário, manual, notícia ou documento auxiliar como substituto de PPC.
4. Ignore o Projeto Político Pedagógico genérico do campus quando houver documento específico do curso.
5. Quando houver mais de um PPC, registre apenas o documento vigente ou mais recente, priorizando textos como "vigente", "novo", "atualizado", "válido a partir de" ou o ano mais recente.
6. Se não houver link oficial claro para PPC, omita `ppc`; não use `null` nem marcador de pendência no curso.
7. Preserve URLs HTTPS absolutas. Links oficiais em Google Drive podem ser usados quando a página do curso apontar diretamente para eles.
8. `ppc.conversao.status` é derivado na publicação: fica `convertido` quando houver `Markdown Link` e `pendente` enquanto o Markdown ainda não tiver sido gerado. Na publicação JSON, `Markdown Link` é convertido para o caminho relativo `ppc.markdown_path`.
9. Use as propriedades de curadoria atuais do Notion para registrar a confiabilidade dos metadados e a data da conferência manual. Na publicação, os valores são normalizados pelos scripts locais.
10. Metadados extraídos do PPC, como ano do documento e vagas, devem ficar em `ppc.metadados` com contexto e evidência textual. No Notion, registre `Vagas` como texto: número simples para quantidade fixa, como `40`, ou intervalo quando o PPC declarar mínimo e máximo, como `20-40`.
11. A conversão para Markdown é apoio à leitura e extração. A fonte oficial continua sendo o PDF indicado em `ppc.url`.
12. Para converter PDFs em Markdown, use o script opcional `scripts/converter_ppcs_markdown.py`, com dependências instaladas por `uv venv && uv pip install -r requirements-ppc.txt`. O conversor padrão é PyMuPDF4LLM com OCR local disponível.
13. Registre o ano do PPC em `ppc.metadados.ano_documento` quando houver evidência no documento, preferencialmente na capa, folha de rosto, ato de ajuste ou indicação clara de revisão vigente.
14. Depois de converter PPCs ou alterar metadados de cursos com PPC convertido, regenere os índices globais com `python3 scripts/gerar_indice_ppcs.py`.

## Índices globais de PPCs

A coleção `institucional/ifpr/ppcs/` contém os PPCs convertidos para Markdown e dois índices globais derivados:

- `institucional/ifpr/ppcs/index.json`: catálogo estruturado com um item por PPC convertido.
- `institucional/ifpr/ppcs/secoes/*.jsonl`: índices textuais por tipo de seção, com uma linha JSON por seção extraída dos PPCs e `preview` curto para consulta leve. O texto completo fica apenas no Markdown do PPC indicado em `path`.

Esses arquivos são gerados automaticamente a partir dos JSONs de campus e dos Markdown convertidos. Não edite `index.json` ou os arquivos em `secoes/` manualmente; ajuste a origem nos arquivos de campus ou no Markdown convertido e rode novamente:

```bash
python3 scripts/gerar_indice_ppcs.py
python3 scripts/validar_base.py
```

Use os PPCs como referência institucional observada para comparação, repertório e apoio à elaboração de textos. Eles não substituem normas vigentes, resoluções, portarias ou o CNCT quando houver exigência normativa aplicável.

## Exemplo: Arapongas

No Campus Arapongas, a navegação eficiente foi feita por:

- `https://ifpr.edu.br/arapongas/`
- `https://ifpr.edu.br/arapongas/wp-json/wp/v2/pages`

A árvore oficial de cursos foi identificada a partir de:

- `https://ifpr.edu.br/arapongas/nossos-cursos/`
- `https://ifpr.edu.br/arapongas/nossos-cursos/curso-tecnico-integrado-ao-ensino-medio/`
- `https://ifpr.edu.br/arapongas/nossos-cursos/graduacao-em-processos-gerenciais/`
- `https://ifpr.edu.br/arapongas/nossos-cursos/pos-graduacao/`
- `https://ifpr.edu.br/arapongas/nossos-cursos/tecnico-subsequente/`
- `https://ifpr.edu.br/arapongas/nossos-cursos/ead/`

As páginas `Partiu IF` e `Cursos de Formação Inicial e Continuada (FIC)` podem aparecer na árvore de `Nossos Cursos`, mas não devem ser misturadas aos cursos regulares do campus quando forem ofertas de programa institucional ou ofertas temporárias. Nesses casos, use `programas` e registre apenas ofertas com vigência atual confirmada.

Atenção: no caso de Arapongas, a árvore de FIC inclui páginas antigas, como ofertas de anos anteriores. Não cadastre todos os filhos de `Cursos FIC` automaticamente como cursos ativos; primeiro confirme a vigência de cada oferta.
