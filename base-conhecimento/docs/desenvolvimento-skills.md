# Desenvolvimento de Skills

## Papel das Skills

As skills em `skills/` são procedimentos operacionais para agentes IA. Elas devem transformar uma tarefa recorrente em fluxo reprodutível, com prompts, scripts, testes e artefatos de apoio.

A Base de Conhecimento local em `base-conhecimento/` continua sendo a fonte de verdade para normas, metadados institucionais, PPCs de referência e catálogos. Antes de duplicar conteúdo normativo dentro de uma skill, verifique se o dado já existe em:

- `base-conhecimento/manifest.json`
- `base-conhecimento/institucional_manifest.json`
- `base-conhecimento/catalogos_manifest.json`
- `base-conhecimento/normas/`
- `base-conhecimento/institucional/`
- `base-conhecimento/catalogos/`

## Integração Com a Base

Ao criar ou revisar uma skill:

1. Defina quais manifestos e coleções da base a skill deve consultar.
2. Prefira referências por `path` e metadados estruturados em vez de texto copiado.
3. Quando a skill precisar funcionar instalada em outro projeto sem a base completa, documente quais dados foram empacotados e qual é a origem.
4. Inclua testes ou validações que indiquem quando uma base gerada, índice ou cópia empacotada ficou desatualizada.

## Convenções

- Cada skill deve ter `SKILL.md`.
- Cada skill com fluxo próprio deve ter `README.md`.
- Scripts de skill devem ficar dentro da própria pasta da skill.
- Dados canônicos compartilhados devem ficar na base, não dentro da skill, salvo quando houver motivo de portabilidade.
- Prompts devem orientar o agente a declarar lacuna ou `INCONCLUSIVO` quando uma norma necessária não estiver disponível na base ou no contexto enviado.

## Validação

Depois de alterar a base:

```bash
python3 scripts/validar_base.py
python3 scripts/gerar_site.py --check
```

Depois de alterar `analise-ppc`:

```bash
python3 -m pytest skills/analise-ppc/tests
```
