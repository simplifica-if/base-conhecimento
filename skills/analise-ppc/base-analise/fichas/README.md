## Resumo

Catálogo canônico das fichas de análise por lote do `analise-ppc`.

Cada arquivo JSON descreve uma verificação individual aplicada ao PPC completo, com pergunta, rubrica, evidência mínima, referências normativas e estados permitidos.

Cada ficha deve declarar:

- `topicos_tematicos`: IDs de tópicos existentes em `../topicos-fichas.json`.
- `tipo_escopo`: `tematico`, `multitematico`, `transversal` ou `condicional`.
- `ancoras_semanticas`: títulos, aliases e termos que ajudam a localizar o conteúdo no PPC real.

Não codifique números de seção nem mantenha campos antigos de localização. A mesma ficha deve funcionar quando o tema aparecer em outro capítulo, item ou título.
