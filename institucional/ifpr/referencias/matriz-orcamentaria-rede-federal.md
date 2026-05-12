# Matriz orçamentária da Rede Federal

Nota técnica institucional para consulta operacional sobre como a Matriz de Distribuição Orçamentária da Rede Federal de EPCT trata matrículas, carga horária e cursos técnicos integrados ao ensino médio.

Data de referência desta nota: 2026-05-12.

## Resumo executivo

A matriz orçamentária da Rede Federal não define um valor fixo nacional "por aluno". Ela distribui um montante orçamentário anual entre instituições e unidades a partir de indicadores, principalmente a `Matrícula Total` no bloco de Funcionamento.

Para um curso técnico integrado ao ensino médio, o que interessa para a matriz não é apenas a carga horária total do PPC, mas a carga horária usada como `CHM` - carga horária para matriz, ajustada de acordo com o catálogo do MEC.

No caso de `Técnico em Informática` integrado ao ensino médio:

- o CNCT registra carga horária mínima profissional de `1200h`;
- a Portaria SETEC/MEC nº 25/2015, art. 5º, §2º, alínea `b`, usava `3200h` para cursos técnicos integrados quando a habilitação profissional indicada no CNCT era de `1200h`;
- portanto, em planejamento conservador, a `CHM` esperada para matriz é `3200h`, mesmo que o PPC tenha, por exemplo, `2100h` de Formação Geral Básica mais `1200h` de formação técnica, totalizando `3300h`.

Com duração de 3 anos, curso presencial, sem bonificação de agropecuária e peso mínimo de integrado `1,5`, cada estudante ativo durante todo o ano tende a gerar:

```text
FECH = (3200 / 3) / 800 = 1,3333
Matrícula Total por aluno = 1,3333 * 1,5 = 2,0
```

Assim, o curso gera aproximadamente `2,0 matrículas totais por aluno por ano`. O valor em reais depende do valor anual da matrícula total na matriz daquele exercício:

```text
R$ por aluno/ano = 2,0 * valor da matrícula total presencial do exercício
```

## Como a Matrícula Total é calculada

A Portaria MEC nº 646/2022 descreve o cálculo da Matrícula Total em quatro etapas: equalização, ponderação, bonificação e finalização.

### 1. Equalização

O objetivo é equiparar ciclos de cursos com diferentes cargas horárias, usando referência de `800h` anuais e considerando os dias ativos no período analisado.

Variáveis principais:

```text
QTDC = (DTC - DIC) + 1
CHMD = CHM / QTDC
```

Onde:

- `QTDC` = quantidade de dias do ciclo;
- `DTC` = data prevista de término do ciclo;
- `DIC` = data de início do ciclo;
- `CHMD` = carga horária média diária;
- `CHM` = carga horária para matriz, ajustada de acordo com o catálogo do MEC.

Para ciclo com duração maior que 365 dias:

```text
CHA = CHMD * 365
FECH = CHA / 800
```

Onde:

- `CHA` = carga horária anualizada;
- `FECH` = fator de equalização de carga horária.

Depois, a matriz considera os dias ativos no período analisado:

```text
FECHDA = FECH * FEDA
MECHDA = FECHDA * QTM1P
```

Onde:

- `FEDA` = fator de equalização de dias ativos;
- `MECHDA` = matrículas equalizadas por carga horária e dias ativos;
- `QTM1P` = matrículas ativas no período analisado.

Para um aluno ativo durante todo o ano, em um ciclo regular que cobre todo o período, `FEDA` tende a ser `1`.

### 2. Ponderação

A matriz aplica o peso do curso:

```text
MP = MECHDA * PC
```

Onde:

- `MP` = matrículas ponderadas;
- `PC` = peso do curso.

Na Portaria MEC nº 646/2022, os critérios de referência para cursos técnicos usam a infraestrutura profissionalizante prevista no CNCT:

```text
Peso 1,0 = 1 laboratório
Peso 1,5 = 2 laboratórios
Peso 2,0 = 3 laboratórios
Peso 2,5 = 4 ou mais laboratórios
```

Para cursos técnicos integrados ao ensino médio, a portaria também registra peso mínimo `1,5`, em função dos laboratórios propedêuticos.

### 3. Bonificação

Cursos da área de agropecuária recebem bonificação:

```text
BA = MP * 50%
```

Para cursos que não são da área de agropecuária:

```text
BA = 0
```

### 4. Finalização

A Matrícula Total é:

```text
MT = MP + BA
```

## Exemplo: Técnico em Informática integrado ao ensino médio

Hipóteses:

```text
Curso: Técnico em Informática integrado ao ensino médio
Modalidade: presencial
Duração do ciclo: 3 anos
Carga técnica CNCT: 1200h
Formação Geral Básica do desenho curricular: 2100h
Carga total do PPC: 3300h
CHM para matriz: 3200h
Peso do curso: 1,5
Agropecuária: não
Aluno ativo no ano inteiro: sim
FEDA: 1
```

Cálculo conservador da matriz:

```text
CHM = 3200h
CHA = 3200 / 3 = 1066,67h/ano
FECH = 1066,67 / 800 = 1,3333
MECHDA por aluno = 1,3333
MP por aluno = 1,3333 * 1,5 = 2,0
BA = 0
MT por aluno = 2,0
```

Resultado:

```text
1 aluno ativo durante todo o ano = aproximadamente 2,0 matrículas totais
```

Se alguém simulasse usando a carga total do PPC de `3300h`, o resultado seria:

```text
CHA = 3300 / 3 = 1100h/ano
FECH = 1100 / 800 = 1,375
MT por aluno = 1,375 * 1,5 = 2,0625
```

Mas essa conta é menos conservadora, porque a metodologia pública da matriz fala em `CHM` ajustada ao catálogo do MEC, e não simplesmente em toda a carga horária que o PPC eventualmente acrescente acima do mínimo.

## Interpretação para planejamento

Para estimar impacto orçamentário anual de novas vagas em Técnico em Informática integrado ao ensino médio, use:

```text
matriculas_totais_ano = alunos_ativos_no_ano * 2,0
orcamento_estimado = matriculas_totais_ano * valor_matricula_total_presencial_do_exercicio
```

Exemplo com 40 alunos ativos durante o ano inteiro:

```text
matriculas_totais_ano = 40 * 2,0 = 80
orcamento_estimado = 80 * valor_matricula_total_presencial_do_exercicio
```

O valor final em reais não pode ser determinado apenas pelo curso, porque depende do orçamento anual fixado para a Rede Federal, da matriz do exercício, dos dados da PNP, da distribuição entre instituições, dos demais indicadores e de eventuais ajustes metodológicos.

## Cuidados de interpretação

1. `Matrícula Total` não é o mesmo que `Aluno-Equivalente`. A matriz orçamentária vigente usa `Matrícula Total` no bloco Funcionamento; outros indicadores usam conceitos como matrícula equivalente ou aluno-equivalente.
2. `CHC` ou carga horária do ciclo pode aparecer no cadastro acadêmico/PNP, mas o cálculo da matriz usa `CHM` quando anualiza a carga horária de ciclos com duração maior que um ano.
3. Carga horária acima do mínimo do catálogo pode ser pedagogicamente válida, mas não deve ser presumida como integralmente financiada pela matriz.
4. A regra `2100h FGB + 1200h técnico = 3300h` decorre da organização curricular do ensino médio com formação técnica e profissional; a regra da matriz para CHM pode permanecer usando o mínimo ajustado ao catálogo.
5. Para decisão administrativa, conferir sempre a planilha oficial da matriz do exercício e a orientação vigente da SETEC/CONIF.

## Base normativa principal

### Portaria MEC nº 646/2022

Fonte oficial:

- DOU/In.gov: <https://www.in.gov.br/web/dou/-/portaria-n-646-de-25-de-agosto-de-2022-425194865>

Pontos relevantes:

- institui a Matriz de Distribuição Orçamentária da Rede Federal de EPCT;
- define que a matriz tem como base as informações publicadas na Plataforma Nilo Peçanha;
- informa que a matriz de um ano é elaborada com dados da PNP do ano anterior;
- organiza a matriz em quatro blocos: Funcionamento, Reitoria/Direção-geral, Qualidade e Eficiência, e Assistência Estudantil;
- define que, após deduzido o valor da assistência estudantil, o bloco Funcionamento equivale a 80% do orçamento total e os blocos Reitoria e Qualidade equivalem, cada um, a 10%;
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

Essa regra explica por que um curso técnico integrado pode ser desenhado curricularmente com `2100h` de FGB mais `1200h` de formação técnica. Ela não altera, por si só, a metodologia da matriz orçamentária enquanto a matriz continuar usando a carga ajustada ao catálogo.

### CNCT - Catálogo Nacional de Cursos Técnicos

Fonte oficial:

- CNCT/MEC: <https://cnct.mec.gov.br/>
- Página do MEC sobre o CNCT: <https://portal.mec.gov.br/legislacao/30000-uncategorised/52031-catalogo-nacional-de-cursos-tecnicos>
- PDF oficial da 4ª edição: <https://www.gov.br/mec/pt-br/acesso-a-informacao/institucional/estrutura-organizacional/orgaos-especificos-singulares/secretaria-de-educacao-profissional/catalogos-nacionais-de-cursos/CNCT_catalogogerado2022_2023.pdf>
- Na base: [Técnico em Informática](../../../catalogos/cnct/cursos/tecnico-em-informatica.json)

Para `Técnico em Informática`, o CNCT registra:

- eixo tecnológico: Informação e Comunicação;
- área tecnológica: Desenvolvimento de Sistemas;
- carga horária mínima: `1200h`;
- infraestrutura mínima: biblioteca, laboratório de informática com programas específicos e laboratório de montagem e reparação de computadores e periféricos.

## Referências oficiais

- Portaria MEC nº 646/2022, DOU/In.gov: <https://www.in.gov.br/web/dou/-/portaria-n-646-de-25-de-agosto-de-2022-425194865>
- Portaria MEC nº 646/2022, republicação certificada no DOU: <https://pesquisa.in.gov.br/imprensa/servlet/INPDFViewer?captchafield=firstAccess&data=21%2F09%2F2022&jornal=515&pagina=122>
- Portaria SETEC/MEC nº 25/2015, gov.br/MEC: <https://www.gov.br/mec/pt-br/media/seb-1/pdf/rede_federal/legislacao_atos/portaria_n25_2015_setec.pdf>
- Portaria SETEC/MEC nº 25/2015: <https://redefederal.mec.gov.br/images/stories/pdf/port_25.pdf>
- Resolução CNE/CEB nº 6/2012, PDF oficial do MEC: <https://portal.mec.gov.br/component/docman/?Itemid=&gid=11663&task=doc_download>
- Lei nº 14.945/2024: <https://www.planalto.gov.br/ccivil_03/_ato2023-2026/2024/lei/l14945.htm>
- Lei nº 11.892/2008: <https://www.planalto.gov.br/ccivil_03/_ato2007-2010/2008/lei/l11892.htm>
- Decreto nº 7.313/2010: <https://www.planalto.gov.br/ccivil_03/_ato2007-2010/2010/decreto/d7313.htm>
- CNCT/MEC: <https://cnct.mec.gov.br/>
- Página MEC sobre o CNCT: <https://portal.mec.gov.br/legislacao/30000-uncategorised/52031-catalogo-nacional-de-cursos-tecnicos>
