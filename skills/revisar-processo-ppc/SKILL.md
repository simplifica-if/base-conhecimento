---
name: revisar-processo-ppc
description: Revisar processos SEI de PPC do IFPR quanto à conformidade com os fluxos da Portaria PROENS/IFPR nº 121/2024, incluindo abertura de curso, PAC, PPC, atualização, ajuste curricular, suspensão, reversão de suspensão, extinção e acompanhamento/avaliação de PPC. Use quando o usuário pedir auditoria, revisão, parecer de conformidade, checagem documental ou análise de obediência ao fluxo normativo de processo SEI relacionado a PPC, curso técnico, graduação, abertura, suspensão, reversão, extinção, ajuste ou atualização curricular.
argument-hint: [numero-processo|runDir]
---

# Revisar Processo PPC

Revise processos SEI de PPC do IFPR contra a Portaria PROENS/IFPR nº 121/2024. Gere relatório Markdown padronizado, em texto corrido com headings, sempre citando provas documentais por número SEI e trechos-fonte específicos.

## Fontes Obrigatórias

Leia antes de concluir:

```text
/Users/gustavo/code/simplifica-if-base-conhecimento/normas/ifpr/portarias/PORTARIA_PROENS-IFPR_121-2024_abertura-suspensao-extincao-cursos.md
```

Leia também o mapa operacional quando precisar selecionar fluxo, itens e condicionantes:

```text
/Users/gustavo/code/simplifica-if-skills/revisar-processo-ppc/references/fluxos-portaria-121.md
```

Use o mapa como checklist auxiliar. A decisão final deve estar ancorada no texto vigente da portaria.

## SEI CLI

Use o `sei-cli` em `../sei-cli` a partir da raiz deste repositório.

Quando o usuário informar apenas número de processo:

1. Localize o snapshot local mais recente em `../sei-cli/dados/sei/<numero-normalizado>/`, se existir.
2. Se houver snapshot, verifique atualização remota antes de usar:

```bash
cd ../sei-cli
bun run sei verificar atualizacao processo <numero-processo> --snapshot dados/sei/<numero-normalizado>/<execucao> --json
```

3. Se `precisa_extrair` for `true`, extraia novamente:

```bash
cd ../sei-cli
bun run sei extrair processo <numero-processo> --json
```

4. Se não houver snapshot, extraia o processo.
5. Se a verificação remota ou extração falhar por credencial, acesso, 2FA ou indisponibilidade, informe o bloqueio. Use snapshot local desatualizado somente se o usuário pedir análise histórica ou aceitar explicitamente a fotografia disponível.

Quando o usuário fornecer um `runDir`, trate-o como fotografia deliberada, não reextraia automaticamente, e declare a data de extração.

## Fluxo De Revisão

1. Leia `processo.json` e o `AGENTS.md` dentro do snapshot SEI.
2. Identifique o fluxo aplicável por `tipo_processo`, `especificacao`, títulos de documentos, histórico e termos fortes nos documentos. Se o usuário indicou um fluxo, use como hipótese inicial e confirme nas evidências.
3. Leia a portaria original e o mapa de fluxos.
4. Defina o escopo: fluxo principal + condicionantes expressas chamadas pela portaria. Exemplo: reversão de suspensão pode exigir Art. 52 §3º e trâmites de ajuste do Título III quando houver PPC atualizado obrigatório.
5. Para cada artigo, inciso ou parágrafo aplicável, procure documentos candidatos no índice e no histórico.
6. Leia o conteúdo dos documentos. A presença de documento no índice nunca basta para `ATENDE`.
7. Para PDFs, use `pdftotext` primeiro. Se a extração for ruim, informe a limitação e recorra a inspeção visual/OCR quando disponível.
8. Gere relatório Markdown fora do snapshot SEI, no diretório original de trabalho do usuário ou em `relatorios/revisar-processo-ppc/`, com nome como:

```text
relatorio-revisao-processo-ppc-<numero-normalizado>-<AAAAMMDDHHMMSS>.md
```

## Evidência

Para marcar `ATENDE`, cite:

- número SEI;
- título do documento;
- caminho relativo no snapshot;
- trecho-fonte forte e específico;
- data do documento ou andamento quando relevante.

Use `INCONCLUSIVO` quando houver documento candidato, mas o trecho não comprovar o requisito, quando o PDF não puder ser lido com confiança, ou quando a aplicabilidade depender de informação ausente. Use `NÃO ATENDE` quando o requisito aplicável não estiver comprovado no processo após busca razoável, ou quando houver evidência contrária.

## Relatório Markdown

Não use tabela. Use headings.

Estrutura obrigatória:

```markdown
# Revisão de processo PPC - <número SEI>

## Síntese

## Processo e snapshot

## Fluxo normativo identificado

## Conclusão geral

## Art. <nº> - <tema>

### Art. <nº>, <inciso/parágrafo> - <exigência resumida>

**Conclusão:** ATENDE | NÃO ATENDE | INCONCLUSIVO

**Evidências:** cite documentos SEI e trechos.

**Análise:** explique por que a prova satisfaz, não satisfaz ou é insuficiente.
```

Inclua um heading para cada item aplicável da portaria. Quando um artigo tiver vários incisos, crie subheadings por inciso. Quando um artigo for conceitual ou condicionante, registre a aplicabilidade e as consequências para o fluxo.

## Busca Recomendada

Comece pelo índice:

```bash
jq '.documentos[] | {ordem_no_processo, numero_sei, titulo, tipo_documento, criado_em, unidade_sei, caminho_relativo}' processo.json
jq '.historico[] | {ocorrido_em, unidade, usuario, descricao}' processo.json
```

Busque termos nos documentos:

```bash
rg -n "reversão|suspensão|extinção|ajuste|atualização|aprovação|deliberou|CGPC|Codic|Consepe|Consup|Proens|justificativa|dados técnicos|PPC" documentos
```

Extraia PDFs candidatos para texto em área de apoio, sem alterar o snapshot:

```bash
mkdir -p /tmp/revisao-processo-ppc
pdftotext -layout "documentos/[07]-4193521_Ata.pdf" "/tmp/revisao-processo-ppc/4193521.txt"
rg -n "CGPC|reversão|suspensão|aprova|favorável|delibera" /tmp/revisao-processo-ppc/4193521.txt
```

## Cuidados

- Não edite arquivos do snapshot SEI.
- Não invente documentos ausentes nem conclua por inferência institucional sem prova documental.
- Diferencie documento existente, conteúdo lido e conclusão normativa.
- Cite a Portaria 121/2024 como base normativa usada, incluindo o caminho local.
