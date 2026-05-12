# Curadoria de metadados institucionais

Este documento registra práticas para manter metadados institucionais do IFPR em JSON, com foco em consumo por agentes IA.

## Organização de documentos da base

Use `docs/` apenas para documentação de apoio à construção, manutenção e curadoria da base, como instruções operacionais, padrões de metadados e aprendizados de curadoria.

Conteúdos destinados à consulta como parte da base de conhecimento devem ficar na coleção temática correspondente, não em `docs/`. Para referências institucionais transversais do IFPR que não sejam cadastro de campus, PPC ou processo seletivo, use `institucional/ifpr/referencias/` e atualize `institucional/ifpr/referencias/index.json`.

Exemplo: uma nota técnica sobre a Matriz Orçamentária da Rede Federal, quando usada como referência institucional para planejamento do IFPR, deve ficar em `institucional/ifpr/referencias/`, e não em `docs/`.

## Cursos nos sites dos campi

Ao pesquisar cursos em páginas de campi do IFPR, prefira fontes oficiais do próprio IFPR e registre em `curadoria.fontes` as páginas usadas para preencher ou revisar os dados.

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
11. Use `modalidade` para distinguir `presencial`, `ead` e `semipresencial`.
12. Use `escopo` para indicar se a oferta é própria do `campus`, de `rede`, de `programa` ou de `polo`.
13. Use `situacao` para registrar a vigência atual da oferta: `ativo`, `em_oferta`, `suspenso` ou `incerto`.
14. Quando a oferta estiver vinculada a programa institucional, como Pronacampo, cadastre o programa em `programas` e suas ofertas em `programas[].ofertas`, não misturadas com os cursos regulares do campus.

## Metadados do SUAP

Use o campo opcional `cursos[].suap` para registrar metadados administrativos vindos do sistema acadêmico SUAP.

1. Registre o código do curso no sistema em `cursos[].suap.codigo`.
2. Registre o número de vagas cadastradas no sistema em `cursos[].suap.vagas`.
3. `cursos[].suap.vagas` representa o dado administrativo do SUAP, não a quantidade de vagas declarada no PPC.
4. Preserve `cursos[].ppc.metadados.vagas` para vagas extraídas do Projeto Pedagógico de Curso, sempre com contexto e evidência textual.

## Processos seletivos

Use a coleção `institucional/ifpr/processos-seletivos/` para registrar vagas efetivamente ofertadas em editais de ingresso. Cada arquivo representa um ano de ingresso e pode conter múltiplos editais e ofertas.

1. Não registre vagas de processo seletivo dentro do JSON do campus.
2. `cursos[].ppc.metadados.vagas` representa vagas previstas no PPC.
3. `cursos[].suap.vagas` representa vagas cadastradas no sistema acadêmico.
4. `processos-seletivos[].ofertas[].vagas` representa vagas ofertadas no edital daquele ano de ingresso.
5. Quando possível, vincule a oferta ao curso do campus por `campus_id` e `curso_id`; se ainda não houver correspondência confiável, registre `curso_nome` e mantenha o vínculo pendente de curadoria.
6. Preserve a fonte oficial do edital ou anexo em `ofertas[].fonte.url` e use `trecho_fonte` para registrar a evidência textual da quantidade de vagas.
7. Quando houver distribuição por cotas, registre o total em `vagas.quantidade` e o detalhamento em `cotas[]`.

## Links para PPC dos cursos

Quando a página oficial do curso indicar o Projeto Pedagógico de Curso, registre os dados no campo opcional `ppc` do item em `cursos`. O PDF oficial fica em `ppc.url`, e o Markdown convertido, quando existir, fica versionado à parte e referenciado em `ppc.markdown_path`.

1. Use como fonte primária a própria página oficial cadastrada em `cursos[].url`.
2. Aceite links descritos como PPC, Projeto Pedagógico do Curso, Projeto Político Pedagógico do Curso ou Plano de Curso equivalente.
3. Não use matriz curricular, edital, resolução, formulário, manual, notícia ou documento auxiliar como substituto de PPC.
4. Ignore o Projeto Político Pedagógico genérico do campus quando houver documento específico do curso.
5. Quando houver mais de um PPC, registre apenas o documento vigente ou mais recente, priorizando textos como "vigente", "novo", "atualizado", "válido a partir de" ou o ano mais recente.
6. Se não houver link oficial claro para PPC, omita `ppc`; não use `null` nem marcador de pendência no curso.
7. Preserve URLs HTTPS absolutas. Links oficiais em Google Drive podem ser usados quando a página do curso apontar diretamente para eles.
8. Use `ppc.conversao.status` como `pendente` enquanto o Markdown ainda não tiver sido gerado.
9. Metadados extraídos do PPC, como ano do documento e vagas, devem ficar em `ppc.metadados` com contexto e evidência textual; não registre apenas um número solto.
10. A conversão para Markdown é apoio à leitura e extração. A fonte oficial continua sendo o PDF indicado em `ppc.url`.
11. Para converter PDFs em Markdown, use o script opcional `scripts/converter_ppcs_markdown.py`, com dependências instaladas por `uv venv && uv pip install -r requirements-ppc.txt`. O conversor padrão é PyMuPDF4LLM com OCR local disponível.
12. Registre o ano do PPC em `ppc.metadados.ano_documento` quando houver evidência no documento, preferencialmente na capa, folha de rosto, ato de ajuste ou indicação clara de revisão vigente.

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
