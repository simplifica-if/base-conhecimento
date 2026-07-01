## Resumo

Centro canônico da base de análise do `analise-ppc`. Reúne, em um único lugar, as fontes estruturadas que orientam a leitura do PPC.

## Estrutura

- `fichas/` — verificações analíticas executadas por lote sobre o PPC completo.
- `validacoes-cruzadas/` — verificações transversais de coerência entre seções e achados.
- `contratos/` — exemplos mínimos de payload e formatos de referência.
- `schemas/` — contratos JSON Schema para fichas, validações cruzadas e respostas.
- `indice.json` — índice consolidado da base de análise, gerado a partir dos JSONs reais.

O CNCT usado pela skill vem da base unificada em `base-conhecimento/catalogos/cnct/`.

## Áreas pretendidas do PPC

Os campos `secoes_preferenciais` das fichas e `secoes_relacionadas` das validações cruzadas usam áreas pretendidas do PPC, não números literais de seção. A numeração varia entre PPCs, por isso os valores aceitos são:

- `identificacao_curso`
- `justificativa_objetivos`
- `concepcao_metodologia`
- `perfil_egresso`
- `organizacao_curricular`
- `avaliacao_aprendizagem`
- `atendimento_estudante`
- `corpo_docente_gestao`
- `infraestrutura`
- `avaliacao_ppc_egressos`
- `referencias_normativas`

## Uso recomendado

1. Consulte `indice.json` quando quiser localizar rapidamente itens por ID, categoria, domínio, criticidade ou seção.
2. Abra `fichas/` quando a pergunta for sobre cobertura analítica por item.
3. Abra `validacoes-cruzadas/` quando a pergunta for sobre coerência transversal.
4. Abra `contratos/` quando a dúvida for sobre formato de entrada ou saída.

## Manutenção

- Para regenerar o índice consolidado:

```bash
python3 -B scripts/gerar_indice_base_analise.py
```

- Para validar fichas, validações cruzadas, contratos e schemas:

```bash
python3 -B scripts/validar_base_analise.py
```
