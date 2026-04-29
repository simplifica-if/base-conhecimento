# Base de Conhecimento Legislativa IFPR

## Resumo

Base pública em Markdown para consulta de legislação, resoluções, portarias e documentos normativos usados por skills e fluxos de análise do IFPR.

> Aviso: esta base é uma curadoria operacional. Para decisões administrativas, jurídicas ou acadêmicas, confira sempre a publicação oficial indicada no campo `fonte` de cada documento.

## Consumo por GitHub raw

Depois de publicar este repositório no GitHub, outras skills podem consultar:

- `manifest.json` para descobrir documentos por metadados, aliases e palavras-chave.
- o campo `path` de cada item do manifesto para buscar o Markdown correspondente via GitHub raw.

Exemplo de URL raw, após definir o remoto público:

```text
https://raw.githubusercontent.com/<owner>/simplifica-if-base-conhecimento/main/manifest.json
https://raw.githubusercontent.com/<owner>/simplifica-if-base-conhecimento/main/<path>
```

## Estrutura

- Arquivos `*.md` na raiz: normas e compilações legislativas.
- `manifest.json`: índice estruturado para consumo automático.
- `docs/padrao-front-matter-legislacao.md`: contrato de metadados.
- `scripts/`: geração e validação local da base.

## Legislação publicada

| Documento | Tipo | Ano | Assunto |
|-----------|------|-----|---------|
| [Lei nº 9.394/1996](1996-12-20_LEI_BR_9394-1996_ldb.md) | Lei | 1996 | Estabelece as diretrizes e bases da educação nacional. |
| [Lei nº 9.394/1996 - trechos relevantes](1996-12-20_LEI_BR_9394-1996_ldb-trechos-relevantes.md) | Compilação | 1996 | Compilação de dispositivos da Lei de Diretrizes e Bases da Educação Nacional relevantes para PPCs. |
| [Lei nº 10.639/2003](2003-01-09_LEI_BR_10639-2003_ensino-historia-cultura-afro-brasileira.md) | Lei | 2003 | Altera a LDB para incluir a obrigatoriedade da temática História e Cultura Afro-Brasileira. |
| [Lei nº 11.645/2008](2008-03-10_LEI_BR_11645-2008_ensino-historia-cultura-afro-brasileira-indigena.md) | Lei | 2008 | Altera a LDB para incluir a obrigatoriedade da temática História e Cultura Afro-Brasileira e Indígena. |
| [Lei nº 11.788/2008](2008-09-25_LEI_BR_11788-2008_lei-estagio.md) | Lei | 2008 | Dispõe sobre o estágio de estudantes. |
| [Lei nº 11.892/2008](2008-12-29_LEI_BR_11892-2008_criacao-ifs.md) | Lei | 2008 | Institui a Rede Federal de Educação Profissional, Científica e Tecnológica e cria os Institutos Federais. |
| [Resolução CONSUP/IFPR nº 55/2011](2011-12-21_RESOLUCAO_CONSUP-IFPR_55-2011_odp-educacao-superior.md) | Resolução | 2011 | Dispõe sobre a Organização Didático-Pedagógica da Educação Superior no âmbito do IFPR. |
| [Lei nº 12.711/2012](2012-08-29_LEI_BR_12711-2012_cotas.md) | Lei | 2012 | Dispõe sobre o ingresso nas universidades federais e nas instituições federais de ensino técnico de nível médio. |
| [Resolução CONSUP/IFPR nº 8/2014](2014-04-30_RESOLUCAO_CONSUP-IFPR_8-2014_regimento-interno-comum-campi.md) | Resolução | 2014 | Regulamenta o Regimento Interno Comum aos Câmpus do Instituto Federal do Paraná. |
| [Lei nº 13.146/2015](2015-07-06_LEI_BR_13146-2015_estatuto-pcd.md) | Lei | 2015 | Institui a Lei Brasileira de Inclusão da Pessoa com Deficiência. |
| [Resolução CONSUP/IFPR nº 50/2017](2017-07-14_RESOLUCAO_CONSUP-IFPR_50-2017_avaliacao.md) | Resolução | 2017 | Estabelece as normas de avaliação dos processos de ensino-aprendizagem no âmbito do IFPR. |
| [Resolução CNE/CP nº 1/2021](2021-01-05_RESOLUCAO_CNE-CP_1-2021_dcnept.md) | Resolução | 2021 | Define as Diretrizes Curriculares Nacionais Gerais para a Educação Profissional e Tecnológica. |
| [Resolução CONSUP/IFPR nº 64/2022](2022-03-23_RESOLUCAO_CONSUP-IFPR_64-2022_cursos-integrados.md) | Resolução | 2022 | Estabelece as diretrizes para a oferta de cursos técnicos integrados ao ensino médio do IFPR. |
| [Resolução CONSUP/IFPR nº 148/2023](2023-10-11_RESOLUCAO_CONSUP-IFPR_148-2023_adaptacao-flexibilizacao-curricular.md) | Resolução | 2023 | Dispõe sobre adaptação de materiais e atividades e flexibilização curricular para estudantes com necessidades educacionais específicas. |
| [Resolução CONSUP/IFPR nº 159/2023](2023-12-12_RESOLUCAO_CONSUP-IFPR_159-2023_docente-educacao-especial.md) | Resolução | 2023 | Dispõe sobre as diretrizes do trabalho do Docente de Educação Especial no IFPR. |
| [Resolução CONSUP/IFPR nº 190/2024](2024-04-30_RESOLUCAO_CONSUP-IFPR_190-2024_odp-cursos-tecnicos.md) | Resolução | 2024 | Dispõe sobre a Organização Didático-Pedagógica dos Cursos Técnicos de Nível Médio no âmbito do IFPR. |
| [Portaria PROENS/IFPR nº 121/2024](2024-06-12_PORTARIA_PROENS-IFPR_121-2024_abertura-suspensao-extincao-cursos.md) | Portaria | 2024 | Institui diretrizes e procedimentos de abertura, suspensão, reversão de suspensão, extinção e ajuste de cursos no IFPR. |
| [Lei nº 14.945/2024](2024-07-31_LEI_BR_14945-2024_ensino-medio.md) | Lei | 2024 | Altera a LDB para instituir a Política Nacional de Ensino Médio. |
| [Resolução CNE/CEB nº 2/2024](2024-11-13_RESOLUCAO_CNE-CEB_2-2024_dcnem.md) | Resolução | 2024 | Institui as Diretrizes Curriculares Nacionais para o Ensino Médio. |
| [Resolução CONSUP/IFPR nº 222/2024](2024-12-27_RESOLUCAO_CONSUP-IFPR_222-2024_altera-regimento-interno-comum-campi.md) | Resolução | 2024 | Altera dispositivo da Resolução nº 08/2014, que regulamenta o Regimento Interno Comum aos Câmpus do IFPR. |
| [Resolução CONSUP/IFPR nº 239/2025](2025-06-10_RESOLUCAO_CONSUP-IFPR_239-2025_assistencia-estudantil.md) | Resolução | 2025 | Dispõe sobre a Política Institucional de Assistência Estudantil no IFPR. |
| [Resolução CONSUP/IFPR nº 242/2025](2025-06-13_RESOLUCAO_CONSUP-IFPR_242-2025_altera-regimento-interno-comum-campi.md) | Resolução | 2025 | Altera dispositivos da Resolução nº 08/2014, que regulamenta o Regimento Interno Comum aos Câmpus do IFPR. |
| [Resolução CNE/CEB nº 7/2025](2025-08-01_RESOLUCAO_CNE-CEB_7-2025_tempo-integral.md) | Resolução | 2025 | Institui as Diretrizes Operacionais Nacionais para a Educação Integral em Tempo Integral na Educação Básica. |
| [Nota Técnica PROENS/IFPR nº 1/2025](2025-10-29_NOTA-TECNICA_PROENS-IFPR_1-2025_aee-nao-componente-curricular.md) | Nota Técnica | 2025 | Esclarece que processos de abertura, elaboração, ajuste e atualização de PPCs não devem incorporar o AEE como componente curricular. |
| [Resolução CONSUP/IFPR nº 259/2025](2025-11-27_RESOLUCAO_CONSUP-IFPR_259-2025_calendario-academico.md) | Resolução | 2025 | Define diretrizes para elaboração dos calendários acadêmicos dos campi do IFPR. |

## Manutenção

```bash
python3 scripts/gerar_base.py
python3 scripts/validar_base.py
```

## Licença

Conteúdo curatorial publicado sob CC BY 4.0. Textos normativos oficiais podem estar sujeitos ao regime próprio de documentos públicos; mantenha atribuição e consulte as fontes oficiais.
