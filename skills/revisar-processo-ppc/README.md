# Revisar Processo PPC

Esta skill revisa processos SEI de PPC do IFPR quanto à conformidade com os fluxos da Portaria PROENS/IFPR nº 121/2024.

## Como pedir

```text
Use a skill revisar-processo-ppc para revisar o processo SEI 23411.011619/2025-70 quanto ao fluxo de reversão de suspensão.
```

Também é possível informar apenas o número do processo; a skill deve usar o `sei-cli` em `../sei-cli`, verificar se o snapshot local está atualizado e extrair novamente quando necessário.

## Saída esperada

A saída principal é um relatório Markdown com headings, sem tabela. Cada item aplicável da portaria deve trazer:

- conclusão: `ATENDE`, `NÃO ATENDE` ou `INCONCLUSIVO`;
- prova documental por número SEI;
- trecho-fonte específico;
- análise do requisito frente à Portaria 121/2024.

## Dependência

O fluxo depende do comando:

```bash
cd ../sei-cli
bun run sei verificar atualizacao processo <numero> --snapshot <runDir> --json
```

Se o snapshot estiver desatualizado, a skill deve extrair nova fotografia com:

```bash
bun run sei extrair processo <numero> --json
```

## Manutenção e validação

Esta skill não possui base gerada ou índice consolidado próprio. Ao alterar o checklist operacional ou o prompt:

1. confirme que a portaria local existe em `/Users/gustavo/code/simplifica-if-base-conhecimento/normas/ifpr/portarias/PORTARIA_PROENS-IFPR_121-2024_abertura-suspensao-extincao-cursos.md`;
2. revise `references/fluxos-portaria-121.md` contra os artigos correspondentes da portaria;
3. valide a sintaxe de `agents/openai.yaml`;
4. faça uma leitura final de `SKILL.md` para garantir que a saída continue exigindo evidência por número SEI, trecho-fonte e análise normativa.

Quando houver alteração futura na Portaria 121/2024 ou em norma anual relacionada, atualize primeiro a fonte normativa na base de conhecimento e depois ajuste o mapa desta skill.
