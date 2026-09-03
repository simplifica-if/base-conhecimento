# Simplifica IF

Projeto unificado que reúne a Base de Conhecimento do IFPR e as skills operacionais usadas por agentes IA.

A base em `base-conhecimento/` é a fonte de verdade para normas, legislação, resoluções, portarias, metadados institucionais, PPCs, catálogos e documentos de referência. As skills em `.agents/skills/` transformam tarefas recorrentes em fluxos reprodutíveis que consultam essa base localmente.

## Estrutura

- `base-conhecimento/`: fonte publicável da base, com caminhos internos preservados como `normas/`, `institucional/`, `catalogos/`, `manifest.json`, `llms.txt` e `README.md`.
- `site/`: saída gerada para publicação estática, ignorada pelo Git e reconstruída a partir de `base-conhecimento/`.
- `.agents/skills/`: skills operacionais para agentes IA, uma pasta versionada por skill e sem symlinks internos.
- `scripts/`: geração, validação e exportação da base.
- `base-conhecimento/docs/`: documentação de apoio à curadoria da base e ao desenvolvimento das skills.

## Base de Conhecimento

Use os manifestos em `base-conhecimento/` como ponto de entrada:

- `base-conhecimento/manifest.json`: normas, legislação, resoluções, portarias e notas técnicas.
- `base-conhecimento/institucional_manifest.json`: coleções institucionais do IFPR.
- `base-conhecimento/catalogos_manifest.json`: catálogos publicados, incluindo o CNCT.
- `base-conhecimento/institucional/ifpr/ppcs/index.json`: índice dos PPCs convertidos.

Os campos `path` dos manifestos são relativos a `base-conhecimento/`. Para publicar a base preservando URLs como `normas/...` e `institucional/...`, gere `site/`:

```bash
python3 scripts/gerar_site.py
python3 scripts/gerar_site.py --check
```

## Skills

As skills deste projeto ficam diretamente no diretório padrão de descoberta do repositório:

```bash
.agents/skills/
```

Skills disponíveis:

- `analise-ppc/`: análise IA-first de Projetos Pedagógicos de Curso técnico do IFPR.
- `ifpr-design/`: identidade visual do IFPR para materiais e interfaces.
- `revisar-processo-ppc/`: revisão de processos SEI de PPC.
- `suap-ifpr/`: consulta e navegação no SUAP do IFPR com apoio dos tutoriais oficiais, incluindo busca rápida de cargo, cursos e disciplinas de docentes.
- `verificar-fundamentacao-normativa/`: conferência de citações e alegações baseadas em leis, resoluções, portarias, CNCT e regulamentos.
- `verificar-calendario/`: verificação de calendários acadêmicos do IFPR.

Ao desenvolver uma skill, consulte primeiro os dados locais em `base-conhecimento/` por manifesto. Só empacote cópias de normas, catálogos ou metadados quando houver motivo claro de portabilidade.

## Manutenção

```bash
python3 scripts/gerar_base.py --check
python3 scripts/gerar_indice_ppcs.py --check
python3 scripts/validar_base.py
python3 scripts/gerar_site.py --check
python3 -m pytest .agents/skills/analise-ppc/tests
```

Para detalhes de desenvolvimento das skills, veja `base-conhecimento/docs/desenvolvimento-skills.md`.

## Licença

Conteúdo curatorial publicado sob CC BY 4.0. Textos normativos oficiais podem estar sujeitos ao regime próprio de documentos públicos; mantenha atribuição e consulte as fontes oficiais.
