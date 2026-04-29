## Resumo

Padrão oficial de `front matter` para arquivos Markdown de legislação em `normas/` neste repositório. Define campos mínimos, campos opcionais, convenções de preenchimento e regras de compatibilidade legada para permitir consumo automático por skills, LLMs e ferramentas de indexação.

---

## Objetivo

O `front matter` existe para:

- identificar a norma de forma canônica;
- padronizar metadados entre leis, resoluções, portarias, pareceres e documentos equivalentes;
- permitir busca estruturada por número, ano, órgão, ementa e palavras-chave;
- registrar relações normativas relevantes, como alteração, revogação e regulamentação;
- apoiar consumo automático por ferramentas, inclusive a skill `analise-ppc`.

---

## Padrão oficial

### Campos obrigatórios

| Campo | Tipo | Regra |
|-------|------|-------|
| `title` | string | Forma canônica curta da norma |
| `tipo_documento` | string | Ex.: `Lei`, `Resolução`, `Portaria`, `Parecer`, `Decreto` |
| `numero` | string ou número | Número do ato, sem o ano embutido quando possível |
| `ano` | inteiro | Ano da norma |
| `data_publicacao` | data ISO | Formato `AAAA-MM-DD` |
| `ementa` | string | Ementa oficial ou resumo normativo reconhecível |
| `status_vigencia` | string | Preferir: `vigente`, `alterada`, `revogada`, `parcialmente revogada`, `desconhecido` |
| `keywords` | lista | Palavras-chave curtas e úteis para recuperação |

### Campos recomendados

| Campo | Tipo | Uso |
|-------|------|-----|
| `orgao` | string | Ex.: `CONSUP/IFPR`, `CNE/CP`, `Presidência da República` |
| `jurisdicao` | string | Ex.: `BR`, `IFPR`, `MEC`, `CNE` |
| `aliases` | lista | Formas alternativas úteis de citação |
| `fonte` | string | URL ou referência da fonte oficial ou base confiável |

### Campos opcionais para relações normativas

| Campo | Tipo |
|-------|------|
| `altera` | lista |
| `alterada_por` | lista |
| `revoga` | lista |
| `revogada_por` | lista |
| `regulamenta` | lista |
| `regulamentada_por` | lista |
| `relaciona_se_a` | lista |

---

## Template oficial

```yaml
---
title: Resolução CONSUP/IFPR nº 159/2023
tipo_documento: Resolução
numero: 159
ano: 2023
data_publicacao: 2023-12-12
orgao: CONSUP/IFPR
jurisdicao: IFPR
ementa: "Dispõe sobre as diretrizes do trabalho do Docente de Educação Especial no IFPR."
status_vigencia: vigente
keywords: [educação especial, AEE, AICE, inclusão, PPC, IFPR]
aliases:
  - Resolução IFPR nº 159/2023
  - Resolução CONSUP/IFPR 159/2023
fonte: "URL ou referência oficial"
relaciona_se_a:
  - Resolução CONSUP/IFPR nº 148/2023
---
```

---

## Regras de preenchimento

- `title` deve ser curto, canônico e suficiente para identificação isolada.
- `numero` deve conter apenas o número do ato. Quando o documento já usa a forma `55/2011` de maneira institucionalmente mais estável, isso pode ser mantido apenas em legado, mas o padrão novo prefere `numero: 55` e `ano: 2011`.
- `data_publicacao` deve usar sempre ISO `AAAA-MM-DD`.
- `keywords` deve conter termos de domínio, não frases longas.
- `aliases` deve conter formas pelas quais o texto costuma ser citado em PPCs e pareceres.
- O corpo do arquivo continua começando com `## Resumo`.
- Os arquivos devem ficar em `normas/<jurisdicao>/<tipo-plural>/`.
- O nome do arquivo não deve usar prefixo de data. A data oficial deve ficar em `data_publicacao`.

---

## Compatibilidade legada

Durante a migração, ferramentas podem aceitar os seguintes aliases de campo:

| Campo legado | Campo padrão |
|-------------|--------------|
| `tipo` | `tipo_documento` |
| `data` | `data_publicacao` |
| `numero_lei` | `numero` |
| `lei_numero` | `numero` |
| `lei_ano` | `ano` |
| `lei_data` | `data_publicacao` |
| `lei_titulo` | `title` |
| `lei_ementa` | `ementa` |
| `status` | `status_vigencia` |
| `lei_status` | `status_vigencia` |
| `apelidos` | `aliases` |

Esses nomes legados devem ser considerados transitórios. Novos arquivos e arquivos revisados devem adotar o padrão oficial.

---

## Prioridade de migração

Migrar primeiro:

1. normas usadas diretamente pela skill `analise-ppc`;
2. normas obrigatórias na seção de referências;
3. normas com maior recorrência em PPCs;
4. normas que estabelecem relações com outras normas da base.
