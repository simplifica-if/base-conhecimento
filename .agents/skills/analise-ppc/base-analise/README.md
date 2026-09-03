## Resumo

Centro canônico da base de análise do `analise-ppc`. Reúne, em um único lugar, as fontes estruturadas que orientam a leitura do PPC.

## Estrutura

- `fichas/` — verificações analíticas executadas por lote sobre o PPC completo.
- `topicos-fichas.json` — taxonomia semântica que organiza as fichas por tema, sem depender da numeração do PPC.
- `mapa-fichas.md` — visão legível da taxonomia para consulta rápida.
- `validacoes-cruzadas/` — verificações transversais de coerência entre seções e achados.
- `contratos/` — exemplos mínimos de payload e formatos de referência.
- `schemas/` — contratos JSON Schema para fichas, validações cruzadas e respostas.
- `indice.json` — índice consolidado da base de análise, gerado a partir dos JSONs reais.

O CNCT usado pela skill vem da base unificada em `base-conhecimento/catalogos/cnct/`.

## Tópicos das fichas

As fichas usam `topicos_tematicos`, `tipo_escopo` e `ancoras_semanticas`.

Esses campos apontam para tópicos semânticos, como estágio, avaliação da aprendizagem, AEE, infraestrutura, matriz curricular ou referências normativas. Não use números fixos nem nomes de seções como contrato da ficha: a numeração e os títulos reais devem ser inferidos durante a rodada de análise a partir das âncoras.

Use `topicos-fichas.json` como fonte canônica e `mapa-fichas.md` para consulta humana.

Ao criar ou editar uma ficha, mantenha a ficha e a taxonomia sincronizadas:

1. A ficha deve citar tópicos existentes em `topicos-fichas.json`.
2. Cada tópico deve citar todas as fichas que pertencem a ele.
3. `mapa-fichas.md` e `indice.json` são gerados; não edite manualmente.

## Uso recomendado

1. Consulte `mapa-fichas.md` quando quiser saber quais fichas avaliam cada tema.
2. Consulte `indice.json` quando quiser localizar rapidamente itens por ID, categoria, domínio, criticidade ou tópico.
3. Abra `fichas/` quando a pergunta for sobre cobertura analítica por item.
4. Abra `validacoes-cruzadas/` quando a pergunta for sobre coerência transversal.
5. Abra `contratos/` quando a dúvida for sobre formato de entrada ou saída.

## Manutenção

Rode a partir da raiz do repositório sempre que alterar fichas, tópicos, validações cruzadas, contratos ou schemas:

```bash
python3 -B .agents/skills/analise-ppc/scripts/validar_base_analise.py
python3 -B .agents/skills/analise-ppc/scripts/gerar_mapa_fichas.py
python3 -B .agents/skills/analise-ppc/scripts/gerar_indice_base_analise.py
python3 -B .agents/skills/analise-ppc/scripts/validar_base_analise.py
python3 -m pytest .agents/skills/analise-ppc/tests
```
