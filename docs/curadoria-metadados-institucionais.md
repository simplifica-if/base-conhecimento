# Curadoria de metadados institucionais

Este documento registra práticas para manter metadados institucionais do IFPR em JSON, com foco em consumo por agentes IA.

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
10. Se a página parecer histórica, antiga ou sem indicação clara de oferta vigente, não inclua no cadastro principal de `cursos` como oferta ativa. Registre apenas depois que houver campo próprio para histórico, se necessário.

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

As páginas `Partiu IF` e `Cursos de Formação Inicial e Continuada (FIC)` aparecem na árvore de `Nossos Cursos`. Use `tipo_oferta: "programa institucional"` para Partiu IF e `tipo_oferta: "FIC"` para cursos FIC, mantendo `nivel` como nível educacional.

Atenção: no caso de Arapongas, a árvore de FIC inclui páginas antigas, como ofertas de anos anteriores. Não cadastre todos os filhos de `Cursos FIC` automaticamente como cursos ativos; primeiro confirme a vigência de cada oferta.
