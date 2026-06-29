---
name: analise-ppc
description: Analisar Projetos Pedagógicos de Curso técnico do IFPR em Word DOCX ou Markdown, preparando o PPC.md, coordenando sub-agentes na conversa com fichas canônicas e gerando PPC HTML anotado determinístico. Use quando o usuário solicitar análise de PPC, revisão de PPC, conformidade de Projeto Pedagógico de Curso, matriz curricular, ementário, CNCT ou parecer técnico-pedagógico sobre PPC.
---

# Análise de PPC

Skill autocontida para analisar PPCs de cursos técnicos do IFPR em Word (`.docx`) ou Markdown (`.md`). A execução de IA ocorre apenas por sub-agentes na conversa atual. Os scripts Python fazem somente a preparação do documento, a organização dos grupos de fichas e a geração determinística do PPC HTML anotado.

## Uso rápido

Para orientação de uso por uma pessoa, leia também:

```text
Read .agents/skills/analise-ppc/README.md
```

Antes de executar uma análise, leia as instruções completas:

```text
Read .agents/skills/analise-ppc/instrucoes.md
```

Se a skill estiver instalada em `.claude/skills`, use o caminho equivalente:

```text
Read .claude/skills/analise-ppc/instrucoes.md
```

## Fluxo principal

1. Preparar o documento para criar a rodada e o `PPC.md`.
2. Montar os grupos de fichas canônicas para sub-agentes, incluindo contexto CNCT da base unificada, contexto estrutural, validações cruzadas e anexos visuais quando disponíveis.
3. Incluir contexto de fundamentação normativa para grupos com fichas que citam ou dependem de base legal, usando a base local e o protocolo da skill `verificar-fundamentacao-normativa`.
4. Gerar pacotes de prompt por grupo com `preparar-prompts-subagents`.
5. Spawnar um sub-agente por grupo na conversa atual.
6. Coletar as respostas em `arquivos-suporte/resultados-subagents.json`, incluindo evidências estruturadas e achados opcionais em `fundamentacao_normativa`.
7. Executar síntese transversal por sub-agente usando `validacoes_cruzadas`; cada alerta deve trazer `validacao_id`.
8. Gerar o PPC HTML anotado determinístico com busca/filtros e publicar no Surge por padrão.

Ao final, informe explicitamente o link de abertura do relatório retornado pelo comando, preferencialmente `surge_url` ou `publicacao_url`. O relatório local fica em `output/<rodada>/relatorio-analise.html`; os assets ficam em `output/<rodada>/assets/`; a pasta enviada ao Surge fica em `arquivos-suporte/surge-site/`; os metadados da publicação ficam em `arquivos-suporte/surge-publicacao.json`; e os demais arquivos de suporte da rodada ficam em `output/<rodada>/arquivos-suporte/`. Use `--sem-surge` apenas quando a publicação externa não for desejada.

## Ponto de entrada

Execute os comandos a partir da raiz do projeto onde a skill está instalada:

```bash
python3 -B .agents/skills/analise-ppc/scripts/analise_ppc.py --help
```

Ou, se instalada para Claude:

```bash
python3 -B .claude/skills/analise-ppc/scripts/analise_ppc.py --help
```
