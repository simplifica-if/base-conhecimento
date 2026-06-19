# Matriz orçamentária: carga horária financiada em cursos técnicos integrados

A matriz orçamentária da Rede Federal não repassa um valor fixo por aluno nem financia automaticamente toda a carga horária prevista no PPC. Para o bloco de Funcionamento, a metodologia da Portaria MEC nº 646/2022 usa a `Matrícula Total`, calculada a partir da `CHM` - carga horária para matriz, ajustada de acordo com o catálogo do MEC.

Para cursos técnicos integrados ao ensino médio, a carga horária de referência depende da carga horária mínima da habilitação profissional indicada no CNCT:

| Carga técnica mínima no CNCT | CHM de referência para curso integrado |
|------------------------------|----------------------------------------|
| `800h` | `3000h` |
| `1000h` | `3100h` |
| `1200h` | `3200h` |

Assim, um curso técnico integrado cuja habilitação CNCT seja de `1200h`, como `Técnico em Informática`, tem como referência histórica de matriz `3200h`.

## O que entra no cálculo

Para estimativa simplificada, use:

```text
CHM = carga horária para matriz
Duração = duração do ciclo, em anos
PC = peso do curso
FECH = (CHM / Duração) / 800
Matrícula Total (MT) por aluno/ano = FECH * PC
```

Onde:

- `CHM` é a carga horária reconhecida para matriz, não necessariamente a carga total do PPC;
- `800h` é a referência anual usada no fator de equalização de carga horária;
- `PC` é o peso do curso;
- para cursos técnicos integrados, a Portaria MEC nº 646/2022 registra peso mínimo `1,5`;
- cursos da área de agropecuária recebem bonificação específica; os exemplos abaixo assumem curso sem bonificação.

## Duração do curso: 3 ou 4 anos

A duração do ciclo afeta a matrícula total anual. A matriz anualiza a CHM: quanto maior a duração, menor a carga anualizada por estudante naquele ano.

Exemplo com `CHM = 3200h` e `PC = 1,5`:

```text
Curso de 3 anos:
FECH = (3200 / 3) / 800 = 1,3333
MT por aluno/ano = 1,3333 * 1,5 = 2,0

Curso de 4 anos:
FECH = (3200 / 4) / 800 = 1,0
MT por aluno/ano = 1,0 * 1,5 = 1,5
```

Isso não significa, por si só, que o curso de 4 anos recebe menos ao longo de toda a trajetória do estudante, pois o aluno permanece ativo por mais tempo. A diferença aparece no valor anual por aluno ativo.

Em regime estável, com a mesma entrada anual de estudantes, um curso de 4 anos tende a ter mais coortes simultaneamente ativas do que um curso de 3 anos. Mesmo assim, para planejamento de trabalho docente, infraestrutura e carga horária ofertada, a comparação relevante é entre `carga total do PPC` e `CHM`.

## Quando há carga horária acima do parâmetro de matriz

Compare a carga total do PPC com a CHM de referência:

```text
saldo_acima_da_CHM = carga_total_do_PPC - CHM
```

Interpretação:

- se o saldo for `0h`, a carga do PPC coincide com a CHM de referência;
- se o saldo for positivo, há carga horária acima do parâmetro usado na estimativa de matriz;
- se o saldo for negativo, o PPC está abaixo da CHM de referência, o que exige análise curricular e normativa própria.

Exemplos:

| Situação | CHM de referência | Carga total do PPC | Saldo acima da CHM |
|----------|-------------------|--------------------|--------------------|
| Integrado com habilitação CNCT de `800h` e PPC de `3200h` | `3000h` | `3200h` | `200h` |
| Integrado com habilitação CNCT de `1000h` e PPC de `3200h` | `3100h` | `3200h` | `100h` |
| Integrado com habilitação CNCT de `1200h` e PPC de `3200h` | `3200h` | `3200h` | `0h` |
| Integrado com habilitação CNCT de `1200h` e PPC de `3300h` | `3200h` | `3300h` | `100h` |

## Exemplo: Técnico em Informática integrado

O CNCT registra `Técnico em Informática` com carga horária mínima profissional de `1200h`. Pela correspondência usada historicamente pela SETEC para cursos técnicos integrados:

```text
Carga técnica CNCT = 1200h
CHM de referência = 3200h
```

Se o PPC tiver `3200h`:

```text
saldo_acima_da_CHM = 3200 - 3200 = 0h
```

Se o PPC tiver `3300h`, por exemplo por organizar `2100h` de Formação Geral Básica e `1200h` de formação técnica:

```text
saldo_acima_da_CHM = 3300 - 3200 = 100h
```

Para um ciclo de 3 anos, curso sem bonificação de agropecuária e peso `1,5`:

```text
FECH = (3200 / 3) / 800 = 1,3333
MT por aluno/ano = 1,3333 * 1,5 = 2,0
```

Para um ciclo de 4 anos:

```text
FECH = (3200 / 4) / 800 = 1,0
MT por aluno/ano = 1,0 * 1,5 = 1,5
```

## Cuidados de interpretação

1. A matriz usa dados da Plataforma Nilo Peçanha do ano anterior e pode sofrer ajustes metodológicos em cada exercício.
2. `Matrícula Total` não é o mesmo que `Aluno-Equivalente`, embora ambos usem ideias de equalização de carga horária.
3. A CHM é parâmetro de matriz; ela não substitui a análise pedagógica, curricular ou legal da carga horária mínima do curso.
4. Carga horária acima da CHM pode ser pedagogicamente válida, mas não deve ser presumida como integralmente reconhecida para cálculo orçamentário.
5. Para decisão administrativa, confira a planilha oficial da matriz do exercício e a orientação vigente da SETEC/CONIF.

## Base normativa principal

### Portaria MEC nº 646/2022

Fonte oficial:

- DOU/In.gov: <https://www.in.gov.br/web/dou/-/portaria-n-646-de-25-de-agosto-de-2022-425194865>

Pontos relevantes:

- institui a Matriz de Distribuição Orçamentária da Rede Federal de EPCT;
- define que a matriz tem como base as informações publicadas na Plataforma Nilo Peçanha;
- informa que a matriz de um ano é elaborada com dados da PNP do ano anterior;
- no bloco Funcionamento, usa `Matrícula Total`;
- no cálculo da Matrícula Total, usa `CHM = Carga horária p/ Matriz (ajustada de acordo com o catálogo do MEC)`.

### Portaria SETEC/MEC nº 25/2015

Fonte oficial:

- gov.br/MEC: <https://www.gov.br/mec/pt-br/media/seb-1/pdf/rede_federal/legislacao_atos/portaria_n25_2015_setec.pdf>
- Rede Federal/MEC: <https://redefederal.mec.gov.br/images/stories/pdf/port_25.pdf>

Pontos relevantes para carga horária:

- define conceitos para cálculo de indicadores de gestão da Rede Federal;
- para cursos técnicos subsequentes e concomitantes, usa a carga horária mínima definida no CNCT;
- no art. 5º, §2º, alínea `b`, define que, para efeito da própria portaria, a carga horária mínima dos cursos técnicos integrados ao ensino médio é de `3000h`, `3100h` ou `3200h`, conforme a habilitação profissional indicada no CNCT seja de `800h`, `1000h` ou `1200h`;
- usa referência de `800h` anuais para o fator de equiparação de carga horária.

Essa portaria trata de indicadores como aluno-equivalente, não é a matriz orçamentária vigente em si. Mas ela explicita a regra de carga mínima dos cursos técnicos integrados que ajuda a interpretar a `CHM` ajustada ao catálogo na Portaria MEC nº 646/2022.

### Resolução CNE/CEB nº 6/2012

Fonte oficial:

- Página de legislação da Educação Profissional e Tecnológica no MEC: <https://portal.mec.gov.br/component/content/article/30000-uncategorised/32141-legislacao-e-atos-normativos-da-educacao-profissional-e-tecnologica>
- PDF oficial do MEC: <https://portal.mec.gov.br/component/docman/?Itemid=&gid=11663&task=doc_download>

Pontos relevantes:

- no art. 27, estabelecia que os cursos de Educação Profissional Técnica de Nível Médio, na forma articulada com o Ensino Médio, integrada ou concomitante em instituições distintas com projeto pedagógico unificado, tinham carga horária total mínima de `3000h`, `3100h` ou `3200h`, conforme a habilitação profissional indicada no CNCT fosse de `800h`, `1000h` ou `1200h`;
- essa é a origem normativa curricular anterior da correspondência `800h -> 3000h`, `1000h -> 3100h` e `1200h -> 3200h`.

Observação: esta resolução foi sucedida pelas Diretrizes Curriculares Nacionais Gerais para a Educação Profissional e Tecnológica posteriores. Nesta nota, ela é citada como origem histórica da correspondência usada pela Portaria SETEC/MEC nº 25/2015.

### Lei nº 14.945/2024

Fonte oficial:

- Planalto: <https://www.planalto.gov.br/ccivil_03/_ato2023-2026/2024/lei/l14945.htm>
- Na base: [Lei nº 14.945/2024](../../../normas/br/leis/LEI_BR_14945-2024_ensino-medio.md)

Pontos relevantes:

- altera a LDB para reorganizar o ensino médio;
- estabelece que a Formação Geral Básica tem carga horária mínima de `2400h`;
- no caso da formação técnica e profissional, a Formação Geral Básica mínima passa a ser `2100h`, admitindo que até `300h` dessa carga sejam destinadas ao aprofundamento de estudos de conteúdos da BNCC diretamente relacionados à formação técnica profissional.

Essa regra explica por que um curso técnico integrado pode ser desenhado curricularmente com `2100h` de FGB mais a carga técnica da habilitação profissional. Ela não altera, por si só, a metodologia da matriz orçamentária enquanto a matriz continuar usando a carga ajustada ao catálogo.
