#!/usr/bin/env python3
"""Gera a base pública de legislação a partir dos arquivos em normas/."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "normas"
USER_PATH_PATTERN = "/" + "Users/"
DOWNLOADS_PATTERN = "Down" + "loads"
TIPO_DIRETORIOS = {
    ("BR", "Lei"): "normas/br/leis",
    ("BR", "Resolução"): "normas/br/resolucoes",
    ("BR", "Compilação"): "normas/br/compilacoes",
    ("IFPR", "Resolução"): "normas/ifpr/resolucoes",
    ("IFPR", "Portaria"): "normas/ifpr/portarias",
    ("IFPR", "Nota Técnica"): "normas/ifpr/notas-tecnicas",
}


NORMAS = [
    {
        "source": "1996-12-20_LEI_BR_9394-1996_ldb.md",
        "target": "1996-12-20_LEI_BR_9394-1996_ldb.md",
        "title": "Lei nº 9.394/1996",
        "tipo_documento": "Lei",
        "numero": "9394",
        "ano": 1996,
        "data_publicacao": "1996-12-20",
        "orgao": "Presidência da República",
        "jurisdicao": "BR",
        "ementa": "Estabelece as diretrizes e bases da educação nacional.",
        "status_vigencia": "vigente",
        "keywords": ["LDB", "educação básica", "ensino médio", "educação profissional", "legislação educacional"],
        "aliases": ["Lei nº 9.394/1996", "Lei 9.394/1996", "LDB"],
        "fonte": "https://www.planalto.gov.br/ccivil_03/leis/l9394.htm",
    },
    {
        "source": "1996-12-20_LEI_BR_9394-1996_ldb-trechos-relevantes.md",
        "target": "1996-12-20_LEI_BR_9394-1996_ldb-trechos-relevantes.md",
        "title": "Lei nº 9.394/1996 - trechos relevantes",
        "tipo_documento": "Compilação",
        "numero": "9394",
        "ano": 1996,
        "data_publicacao": "1996-12-20",
        "orgao": "Presidência da República",
        "jurisdicao": "BR",
        "ementa": "Compilação de dispositivos da Lei de Diretrizes e Bases da Educação Nacional relevantes para PPCs.",
        "status_vigencia": "compilação",
        "keywords": ["LDB", "PPC", "ensino médio", "educação profissional", "trechos relevantes"],
        "aliases": ["LDB - trechos relevantes", "Lei nº 9.394/1996 - trechos relevantes"],
        "fonte": "https://www.planalto.gov.br/ccivil_03/leis/L9394compilado.htm",
        "relaciona_se_a": ["Lei nº 9.394/1996", "Lei nº 14.945/2024"],
    },
    {
        "source": "2003-01-09_LEI_BR_10639-2003_ensino-historia-cultura-afro-brasileira.md",
        "target": "2003-01-09_LEI_BR_10639-2003_ensino-historia-cultura-afro-brasileira.md",
        "title": "Lei nº 10.639/2003",
        "tipo_documento": "Lei",
        "numero": "10639",
        "ano": 2003,
        "data_publicacao": "2003-01-09",
        "orgao": "Presidência da República",
        "jurisdicao": "BR",
        "ementa": "Altera a LDB para incluir a obrigatoriedade da temática História e Cultura Afro-Brasileira.",
        "status_vigencia": "alterada",
        "keywords": ["história", "cultura afro-brasileira", "educação", "currículo", "África", "consciência negra"],
        "aliases": ["Lei nº 10.639/2003", "Lei 10.639/2003"],
        "fonte": "https://www.planalto.gov.br/ccivil_03/leis/2003/l10.639.htm",
        "altera": ["Lei nº 9.394/1996"],
        "alterada_por": ["Lei nº 11.645/2008"],
    },
    {
        "source": "2008-03-10_LEI_BR_11645-2008_ensino-historia-cultura-afro-brasileira-indigena.md",
        "target": "2008-03-10_LEI_BR_11645-2008_ensino-historia-cultura-afro-brasileira-indigena.md",
        "title": "Lei nº 11.645/2008",
        "tipo_documento": "Lei",
        "numero": "11645",
        "ano": 2008,
        "data_publicacao": "2008-03-10",
        "orgao": "Presidência da República",
        "jurisdicao": "BR",
        "ementa": "Altera a LDB para incluir a obrigatoriedade da temática História e Cultura Afro-Brasileira e Indígena.",
        "status_vigencia": "vigente",
        "keywords": ["história", "cultura afro-brasileira", "cultura indígena", "educação", "currículo", "povos indígenas"],
        "aliases": ["Lei nº 11.645/2008", "Lei 11.645/2008"],
        "fonte": "https://www.planalto.gov.br/ccivil_03/_ato2007-2010/2008/lei/l11645.htm",
        "altera": ["Lei nº 9.394/1996", "Lei nº 10.639/2003"],
    },
    {
        "source": "2008-09-25_LEI_BR_11788-2008_lei-estagio.md",
        "target": "2008-09-25_LEI_BR_11788-2008_lei-estagio.md",
        "title": "Lei nº 11.788/2008",
        "tipo_documento": "Lei",
        "numero": "11788",
        "ano": 2008,
        "data_publicacao": "2008-09-25",
        "orgao": "Presidência da República",
        "jurisdicao": "BR",
        "ementa": "Dispõe sobre o estágio de estudantes.",
        "status_vigencia": "vigente",
        "keywords": ["estágio", "educação profissional", "CLT", "educação", "trabalho", "estagiário"],
        "aliases": ["Lei nº 11.788/2008", "Lei 11.788/2008", "Lei do Estágio"],
        "fonte": "https://www.planalto.gov.br/ccivil_03/_ato2007-2010/2008/lei/l11788.htm",
    },
    {
        "source": "2008-12-29_LEI_BR_11892-2008_criacao-ifs.md",
        "target": "2008-12-29_LEI_BR_11892-2008_criacao-ifs.md",
        "title": "Lei nº 11.892/2008",
        "tipo_documento": "Lei",
        "numero": "11892",
        "ano": 2008,
        "data_publicacao": "2008-12-29",
        "orgao": "Presidência da República",
        "jurisdicao": "BR",
        "ementa": "Institui a Rede Federal de Educação Profissional, Científica e Tecnológica e cria os Institutos Federais.",
        "status_vigencia": "vigente",
        "keywords": ["Rede Federal", "Institutos Federais", "EPT", "IFPR", "educação profissional"],
        "aliases": ["Lei nº 11.892/2008", "Lei 11.892/2008", "Lei de criação dos Institutos Federais"],
        "fonte": "https://www.planalto.gov.br/ccivil_03/_ato2007-2010/2008/lei/l11892.htm",
    },
    {
        "source": "2011-12-21_RESOLUCAO_CONSUP-IFPR_55-2011.md",
        "target": "2011-12-21_RESOLUCAO_CONSUP-IFPR_55-2011_odp-educacao-superior.md",
        "title": "Resolução CONSUP/IFPR nº 55/2011",
        "tipo_documento": "Resolução",
        "numero": "55",
        "ano": 2011,
        "data_publicacao": "2011-12-21",
        "orgao": "CONSUP/IFPR",
        "jurisdicao": "IFPR",
        "ementa": "Dispõe sobre a Organização Didático-Pedagógica da Educação Superior no âmbito do IFPR.",
        "status_vigencia": "alterada",
        "keywords": ["educação superior", "organização didático-pedagógica", "IFPR", "calendário acadêmico", "PPC"],
        "aliases": ["Resolução nº 55/2011", "Resolução CONSUP/IFPR 55/2011", "2011-12-21_RESOLUCAO_CONSUP-IFPR_55-2011.md"],
        "fonte": "https://ifpr.edu.br/resolucao-no-552011/",
        "alterada_por": ["Resolução CONSUP/IFPR nº 14/2014", "Resolução CONSUP/IFPR nº 2/2017"],
    },
    {
        "source": "2012-08-29_LEI_BR_12711-2012_cotas.md",
        "target": "2012-08-29_LEI_BR_12711-2012_cotas.md",
        "title": "Lei nº 12.711/2012",
        "tipo_documento": "Lei",
        "numero": "12711",
        "ano": 2012,
        "data_publicacao": "2012-08-29",
        "orgao": "Presidência da República",
        "jurisdicao": "BR",
        "ementa": "Dispõe sobre o ingresso nas universidades federais e nas instituições federais de ensino técnico de nível médio.",
        "status_vigencia": "vigente",
        "keywords": ["cotas", "reserva de vagas", "ações afirmativas", "instituições federais", "ensino técnico"],
        "aliases": ["Lei nº 12.711/2012", "Lei 12.711/2012", "Lei de Cotas"],
        "fonte": "https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2012/lei/l12711.htm",
    },
    {
        "source": "2014-04-30_RESOLUCAO_CONSUP-IFPR_8-2014_regimento-interno-comum-campi.md",
        "target": "2014-04-30_RESOLUCAO_CONSUP-IFPR_8-2014_regimento-interno-comum-campi.md",
        "title": "Resolução CONSUP/IFPR nº 8/2014",
        "tipo_documento": "Resolução",
        "numero": "8",
        "ano": 2014,
        "data_publicacao": "2014-04-30",
        "orgao": "CONSUP/IFPR",
        "jurisdicao": "IFPR",
        "ementa": "Regulamenta o Regimento Interno Comum aos Câmpus do Instituto Federal do Paraná.",
        "status_vigencia": "alterada",
        "keywords": ["regimento interno", "campi", "colegiado de curso", "CODIC", "funcionamento institucional", "PPC"],
        "aliases": ["Resolução IFPR nº 08/2014", "Resolução 08/2014", "Resolução CONSUP/IFPR 8/2014"],
        "fonte": "https://ifpr.edu.br/resolucao-082014/",
        "alterada_por": ["Resolução CONSUP/IFPR nº 222/2024", "Resolução CONSUP/IFPR nº 242/2025"],
        "revoga": ["Resolução CONSUP nº 08/2010", "Resolução CONSUP nº 41/2013"],
    },
    {
        "source": "2015-07-06_LEI_BR_13146-2015_estatuto-pcd.md",
        "target": "2015-07-06_LEI_BR_13146-2015_estatuto-pcd.md",
        "title": "Lei nº 13.146/2015",
        "tipo_documento": "Lei",
        "numero": "13146",
        "ano": 2015,
        "data_publicacao": "2015-07-06",
        "orgao": "Presidência da República",
        "jurisdicao": "BR",
        "ementa": "Institui a Lei Brasileira de Inclusão da Pessoa com Deficiência.",
        "status_vigencia": "vigente",
        "keywords": ["pessoa com deficiência", "acessibilidade", "inclusão", "educação especial", "LBI"],
        "aliases": ["Lei nº 13.146/2015", "Lei 13.146/2015", "Estatuto da Pessoa com Deficiência", "LBI"],
        "fonte": "https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2015/lei/l13146.htm",
    },
    {
        "source": "2017-07-14_RESOLUCAO_CONSUP-IFPR_50-2017_avaliacao.md",
        "target": "2017-07-14_RESOLUCAO_CONSUP-IFPR_50-2017_avaliacao.md",
        "title": "Resolução CONSUP/IFPR nº 50/2017",
        "tipo_documento": "Resolução",
        "numero": "50",
        "ano": 2017,
        "data_publicacao": "2017-07-14",
        "orgao": "CONSUP/IFPR",
        "jurisdicao": "IFPR",
        "ementa": "Estabelece as normas de avaliação dos processos de ensino-aprendizagem no âmbito do IFPR.",
        "status_vigencia": "vigente",
        "keywords": ["avaliação", "conceitos", "recuperação", "progressão", "ensino-aprendizagem", "IFPR"],
        "aliases": ["Resolução nº 50/2017", "Resolução CONSUP/IFPR 50/2017"],
        "fonte": "https://ifpr.edu.br/resolucao-no-50-de-14-de-julho-de-2017/",
    },
    {
        "source": "2021-01-05_RESOLUCAO_CNE-CP_1-2021_dcnept.md",
        "target": "2021-01-05_RESOLUCAO_CNE-CP_1-2021_dcnept.md",
        "title": "Resolução CNE/CP nº 1/2021",
        "tipo_documento": "Resolução",
        "numero": "1",
        "ano": 2021,
        "data_publicacao": "2021-01-05",
        "orgao": "CNE/CP",
        "jurisdicao": "BR",
        "ementa": "Define as Diretrizes Curriculares Nacionais Gerais para a Educação Profissional e Tecnológica.",
        "status_vigencia": "vigente",
        "keywords": ["DCNEPT", "educação profissional", "EPT", "diretrizes curriculares", "CNE"],
        "aliases": ["Resolução CNE/CP nº 1/2021", "DCNEPT"],
        "fonte": "https://www.in.gov.br/en/web/dou/-/resolucao-cne/cp-n-1-de-5-de-janeiro-de-2021-297767578",
    },
    {
        "source": "2022-03-23_RESOLUCAO_CONSUP-IFPR_64-2022_cursos-integrados.md",
        "target": "2022-03-23_RESOLUCAO_CONSUP-IFPR_64-2022_cursos-integrados.md",
        "title": "Resolução CONSUP/IFPR nº 64/2022",
        "tipo_documento": "Resolução",
        "numero": "64",
        "ano": 2022,
        "data_publicacao": "2022-03-23",
        "orgao": "CONSUP/IFPR",
        "jurisdicao": "IFPR",
        "ementa": "Estabelece as diretrizes para a oferta de cursos técnicos integrados ao ensino médio do IFPR.",
        "status_vigencia": "vigente",
        "keywords": ["curso técnico integrado", "ensino médio", "PPC", "IFPR", "EPT"],
        "aliases": ["Resolução CONSUP/IFPR nº 64/2022", "Resolução IFPR 64/2022"],
        "fonte": "https://sei.ifpr.edu.br/sei/publicacoes/controlador_publicacoes.php?acao=publicacao_visualizar&id_documento=1736791&id_orgao_publicacao=0",
    },
    {
        "source": "2023-10-11_RESOLUCAO_CONSUP-IFPR_148-2023_adaptacao-flexibilizacao-curricular.md",
        "target": "2023-10-11_RESOLUCAO_CONSUP-IFPR_148-2023_adaptacao-flexibilizacao-curricular.md",
        "title": "Resolução CONSUP/IFPR nº 148/2023",
        "tipo_documento": "Resolução",
        "numero": "148",
        "ano": 2023,
        "data_publicacao": "2023-10-11",
        "orgao": "CONSUP/IFPR",
        "jurisdicao": "IFPR",
        "ementa": "Dispõe sobre adaptação de materiais e atividades e flexibilização curricular para estudantes com necessidades educacionais específicas.",
        "status_vigencia": "vigente",
        "keywords": ["adaptação curricular", "flexibilização curricular", "NEE", "educação especial", "inclusão"],
        "aliases": ["Resolução CONSUP/IFPR nº 148/2023", "Resolução IFPR 148/2023"],
        "fonte": "https://sei.ifpr.edu.br/sei/publicacoes/controlador_publicacoes.php?acao=publicacao_visualizar&id_documento=2730182&id_orgao_publicacao=0",
    },
    {
        "source": "2023-12-12_RESOLUCAO_CONSUP-IFPR_159-2023_docente-educacao-especial.md",
        "target": "2023-12-12_RESOLUCAO_CONSUP-IFPR_159-2023_docente-educacao-especial.md",
        "title": "Resolução CONSUP/IFPR nº 159/2023",
        "tipo_documento": "Resolução",
        "numero": "159",
        "ano": 2023,
        "data_publicacao": "2023-12-12",
        "orgao": "CONSUP/IFPR",
        "jurisdicao": "IFPR",
        "ementa": "Dispõe sobre as diretrizes do trabalho do Docente de Educação Especial no IFPR.",
        "status_vigencia": "vigente",
        "keywords": ["educação especial", "AEE", "AICE", "inclusão", "PPC", "IFPR"],
        "aliases": ["Resolução CONSUP/IFPR nº 159/2023", "Resolução CONSUP/IFPR 159/2023", "Resolução IFPR 159/2023"],
        "fonte": "Fonte oficial pendente de confirmação pública",
        "relaciona_se_a": ["Resolução CONSUP/IFPR nº 148/2023", "Nota Técnica PROENS/IFPR nº 1/2025"],
    },
    {
        "source": "2024-04-30_RESOLUCAO_CONSUP-IFPR_190-2024_odp.md",
        "target": "2024-04-30_RESOLUCAO_CONSUP-IFPR_190-2024_odp-cursos-tecnicos.md",
        "title": "Resolução CONSUP/IFPR nº 190/2024",
        "tipo_documento": "Resolução",
        "numero": "190",
        "ano": 2024,
        "data_publicacao": "2024-04-30",
        "orgao": "CONSUP/IFPR",
        "jurisdicao": "IFPR",
        "ementa": "Dispõe sobre a Organização Didático-Pedagógica dos Cursos Técnicos de Nível Médio no âmbito do IFPR.",
        "status_vigencia": "vigente",
        "keywords": ["ODP", "cursos técnicos", "PPC", "IFPR", "organização didático-pedagógica"],
        "aliases": ["Resolução CONSUP/IFPR nº 190/2024", "Resolução IFPR 190/2024", "2024-04-30_RESOLUCAO_CONSUP-IFPR_190-2024_odp.md"],
        "fonte": "https://sei.ifpr.edu.br/sei/publicacoes/controlador_publicacoes.php?acao=publicacao_visualizar&id_documento=3110625&id_orgao_publicacao=0",
        "revoga": ["Resolução IFPR nº 54/2011"],
    },
    {
        "source": "2024-06-12_PORTARIA_PROENS-IFPR_121-2024_abertura-cursos.md",
        "target": "2024-06-12_PORTARIA_PROENS-IFPR_121-2024_abertura-suspensao-extincao-cursos.md",
        "title": "Portaria PROENS/IFPR nº 121/2024",
        "tipo_documento": "Portaria",
        "numero": "121",
        "ano": 2024,
        "data_publicacao": "2024-06-12",
        "orgao": "PROENS/IFPR",
        "jurisdicao": "IFPR",
        "ementa": "Institui diretrizes e procedimentos de abertura, suspensão, reversão de suspensão, extinção e ajuste de cursos no IFPR.",
        "status_vigencia": "vigente",
        "keywords": ["abertura de curso", "suspensão de curso", "extinção de curso", "PPC", "PROENS"],
        "aliases": ["Portaria PROENS/IFPR nº 121/2024", "Portaria PROENS 121/2024", "2024-06-12_PORTARIA_PROENS-IFPR_121-2024_abertura-cursos.md"],
        "fonte": "Fonte oficial pendente de confirmação pública",
    },
    {
        "source": "2024-07-31_LEI_BR_14945-2024_ensino-medio.md",
        "target": "2024-07-31_LEI_BR_14945-2024_ensino-medio.md",
        "title": "Lei nº 14.945/2024",
        "tipo_documento": "Lei",
        "numero": "14945",
        "ano": 2024,
        "data_publicacao": "2024-07-31",
        "orgao": "Presidência da República",
        "jurisdicao": "BR",
        "ementa": "Altera a LDB para instituir a Política Nacional de Ensino Médio.",
        "status_vigencia": "vigente",
        "keywords": ["ensino médio", "formação geral básica", "itinerários formativos", "EPT", "LDB"],
        "aliases": ["Lei nº 14.945/2024", "Lei 14.945/2024", "Novo Ensino Médio 2024"],
        "fonte": "https://www.planalto.gov.br/ccivil_03/_ato2023-2026/2024/lei/l14945.htm",
        "altera": ["Lei nº 9.394/1996"],
    },
    {
        "source": "2024-11-13_RESOLUCAO_CNE-CEB_2-2024_dcnem.md",
        "target": "2024-11-13_RESOLUCAO_CNE-CEB_2-2024_dcnem.md",
        "title": "Resolução CNE/CEB nº 2/2024",
        "tipo_documento": "Resolução",
        "numero": "2",
        "ano": 2024,
        "data_publicacao": "2024-11-13",
        "orgao": "CNE/CEB",
        "jurisdicao": "BR",
        "ementa": "Institui as Diretrizes Curriculares Nacionais para o Ensino Médio.",
        "status_vigencia": "vigente",
        "keywords": ["DCNEM", "ensino médio", "diretrizes curriculares", "itinerários formativos", "CNE"],
        "aliases": ["Resolução CNE/CEB nº 2/2024", "DCNEM 2024"],
        "fonte": "https://www.in.gov.br/en/web/dou/-/resolucao-cne/ceb-n-2-de-13-de-novembro-de-2024-596497964",
    },
    {
        "source": "2024-12-27_RESOLUCAO_CONSUP-IFPR_222-2024_altera-regimento-interno-comum-campi.md",
        "target": "2024-12-27_RESOLUCAO_CONSUP-IFPR_222-2024_altera-regimento-interno-comum-campi.md",
        "title": "Resolução CONSUP/IFPR nº 222/2024",
        "tipo_documento": "Resolução",
        "numero": "222",
        "ano": 2024,
        "data_publicacao": "2024-12-27",
        "orgao": "CONSUP/IFPR",
        "jurisdicao": "IFPR",
        "ementa": "Altera dispositivo da Resolução nº 08/2014, que regulamenta o Regimento Interno Comum aos Câmpus do IFPR.",
        "status_vigencia": "vigente",
        "keywords": ["regimento interno", "campi", "CODIC", "alteração normativa", "composição colegiada"],
        "aliases": ["Resolução IFPR nº 222/2024", "Resolução CONSUP/IFPR 222/2024"],
        "fonte": "https://sei.ifpr.edu.br/sei/publicacoes/controlador_publicacoes.php?acao=publicacao_visualizar&id_documento=3510159&id_orgao_publicacao=0",
        "altera": ["Resolução CONSUP/IFPR nº 8/2014"],
    },
    {
        "source": "2025-06-10_RESOLUCAO_CONSUP-IFPR_239-2025_assistencia-estudantil.md",
        "target": "2025-06-10_RESOLUCAO_CONSUP-IFPR_239-2025_assistencia-estudantil.md",
        "title": "Resolução CONSUP/IFPR nº 239/2025",
        "tipo_documento": "Resolução",
        "numero": "239",
        "ano": 2025,
        "data_publicacao": "2025-06-10",
        "orgao": "CONSUP/IFPR",
        "jurisdicao": "IFPR",
        "ementa": "Dispõe sobre a Política Institucional de Assistência Estudantil no IFPR.",
        "status_vigencia": "vigente",
        "keywords": ["assistência estudantil", "permanência", "PNAES", "IFPR", "política institucional"],
        "aliases": ["Resolução CONSUP/IFPR nº 239/2025", "Resolução IFPR 239/2025"],
        "fonte": "Fonte oficial pendente de confirmação pública",
        "revoga": ["Resolução nº 11/2009", "Resolução nº 53/2011"],
    },
    {
        "source": "2025-06-13_RESOLUCAO_CONSUP-IFPR_242-2025_altera-regimento-interno-comum-campi.md",
        "target": "2025-06-13_RESOLUCAO_CONSUP-IFPR_242-2025_altera-regimento-interno-comum-campi.md",
        "title": "Resolução CONSUP/IFPR nº 242/2025",
        "tipo_documento": "Resolução",
        "numero": "242",
        "ano": 2025,
        "data_publicacao": "2025-06-13",
        "orgao": "CONSUP/IFPR",
        "jurisdicao": "IFPR",
        "ementa": "Altera dispositivos da Resolução nº 08/2014, que regulamenta o Regimento Interno Comum aos Câmpus do IFPR.",
        "status_vigencia": "vigente",
        "keywords": ["regimento interno", "campi", "CODIC", "alteração normativa", "composição colegiada"],
        "aliases": ["Resolução IFPR nº 242/2025", "Resolução CONSUP/IFPR 242/2025"],
        "fonte": "https://sei.ifpr.edu.br/sei/publicacoes/controlador_publicacoes.php?acao=publicacao_visualizar&id_documento=3797141&id_orgao_publicacao=0",
        "altera": ["Resolução CONSUP/IFPR nº 8/2014"],
    },
    {
        "source": "2025-08-01_RESOLUCAO_CNE-CEB_7-2025_tempo-integral.md",
        "target": "2025-08-01_RESOLUCAO_CNE-CEB_7-2025_tempo-integral.md",
        "title": "Resolução CNE/CEB nº 7/2025",
        "tipo_documento": "Resolução",
        "numero": "7",
        "ano": 2025,
        "data_publicacao": "2025-08-01",
        "orgao": "CNE/CEB",
        "jurisdicao": "BR",
        "ementa": "Institui as Diretrizes Operacionais Nacionais para a Educação Integral em Tempo Integral na Educação Básica.",
        "status_vigencia": "vigente",
        "keywords": ["tempo integral", "educação integral", "educação básica", "diretrizes operacionais", "CNE"],
        "aliases": ["Resolução CNE/CEB nº 7/2025", "Educação Integral em Tempo Integral"],
        "fonte": "https://www.in.gov.br/en/web/dou/-/resolucao-cne/ceb-n-7-de-1-de-agosto-de-2025-646951446",
    },
    {
        "source": "2025-10-29_NOTA-TECNICA_PROENS-IFPR_1-2025_aee-nao-componente-curricular.md",
        "target": "2025-10-29_NOTA-TECNICA_PROENS-IFPR_1-2025_aee-nao-componente-curricular.md",
        "title": "Nota Técnica PROENS/IFPR nº 1/2025",
        "tipo_documento": "Nota Técnica",
        "numero": "1",
        "ano": 2025,
        "data_publicacao": "2025-10-29",
        "orgao": "PROENS/IFPR",
        "jurisdicao": "IFPR",
        "ementa": "Esclarece que processos de abertura, elaboração, ajuste e atualização de PPCs não devem incorporar o AEE como componente curricular.",
        "status_vigencia": "vigente",
        "keywords": ["educação especial", "AEE", "PPC", "matriz curricular", "histórico escolar", "PROENS", "IFPR"],
        "aliases": ["Nota Técnica PROENS/IFPR nº 1/2025", "Nota Técnica 1/2025", "SEI nº 3881287"],
        "fonte": "SEI/IFPR nº 3881287",
        "relaciona_se_a": ["Resolução CONSUP/IFPR nº 159/2023", "Resolução CONSUP/IFPR nº 148/2023"],
    },
    {
        "source": "resolucao-259-2025-calendario.md",
        "target": "2025-11-27_RESOLUCAO_CONSUP-IFPR_259-2025_calendario-academico.md",
        "title": "Resolução CONSUP/IFPR nº 259/2025",
        "tipo_documento": "Resolução",
        "numero": "259",
        "ano": 2025,
        "data_publicacao": "2025-11-27",
        "orgao": "CONSUP/IFPR",
        "jurisdicao": "IFPR",
        "ementa": "Define diretrizes para elaboração dos calendários acadêmicos dos campi do IFPR.",
        "status_vigencia": "vigente",
        "keywords": ["calendário acadêmico", "dias letivos", "férias docentes", "campi", "IFPR"],
        "aliases": ["Resolução CONSUP/IFPR nº 259/2025", "Resolução IFPR 259/2025", "resolucao-259-2025-calendario.md"],
        "fonte": "Fonte oficial pendente de confirmação pública",
    },
]


def yaml_scalar(value: object) -> str:
    if isinstance(value, int):
        return str(value)
    text = str(value)
    if re.fullmatch(r"[A-Za-z0-9_./:-]+", text) and not re.match(r"\d{4}-\d{2}-\d{2}$", text):
        return text
    return json.dumps(text, ensure_ascii=False)


def nome_publico(meta: dict) -> str:
    return re.sub(r"^\d{4}-\d{2}-\d{2}_", "", str(meta["target"]))


def caminho_publico(meta: dict) -> str:
    key = (str(meta["jurisdicao"]), str(meta["tipo_documento"]))
    try:
        diretorio = TIPO_DIRETORIOS[key]
    except KeyError as exc:
        raise ValueError(f"tipo sem diretório configurado: {key}") from exc
    return f"{diretorio}/{nome_publico(meta)}"


def caminho_fonte(meta: dict) -> Path:
    return ROOT / caminho_publico(meta)


def frontmatter(meta: dict) -> str:
    order = [
        "title",
        "tipo_documento",
        "numero",
        "ano",
        "data_publicacao",
        "orgao",
        "jurisdicao",
        "ementa",
        "status_vigencia",
        "keywords",
        "aliases",
        "fonte",
        "altera",
        "alterada_por",
        "revoga",
        "revogada_por",
        "relaciona_se_a",
    ]
    lines = ["---"]
    for key in order:
        if key not in meta:
            continue
        value = meta[key]
        if isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                lines.append(f"  - {yaml_scalar(item)}")
        else:
            lines.append(f"{key}: {yaml_scalar(value)}")
    lines.append("---")
    return "\n".join(lines) + "\n\n"


def strip_frontmatter(text: str) -> str:
    if not text.startswith("---\n"):
        return text
    end = text.find("\n---", 4)
    if end == -1:
        return text
    after = text.find("\n", end + 4)
    return text[after + 1 :] if after != -1 else ""


def body_from_resumo(text: str) -> str:
    text = strip_frontmatter(text).lstrip()
    idx = text.find("## Resumo")
    if idx != -1:
        text = text[idx:]
    text = re.sub(re.escape(USER_PATH_PATTERN) + r"[^ \n)]+/alfred4ifpr/knowledge/legislacao/", "", text)
    text = re.sub(re.escape(USER_PATH_PATTERN) + r"[^ \n)]+/alfred4ifpr/knowledge/", "", text)
    text = re.sub(re.escape(USER_PATH_PATTERN) + r"[^ \n)]+/" + DOWNLOADS_PATTERN + r"/SEI_3881287_Nota_Tecnica_1\.pdf", "SEI/IFPR nº 3881287", text)
    return text.strip() + "\n"


def fix_resolucao_259(text: str) -> str:
    replacements = {
        "Resolucao": "Resolução",
        "resolucao": "resolução",
        "Republica": "República",
        "republica": "república",
        "Calendario": "Calendário",
        "calendario": "calendário",
        "Academico": "Acadêmico",
        "academico": "acadêmico",
        "elaboracao": "elaboração",
        "calendarios": "calendários",
        "Parana": "Paraná",
        "Minimo": "Mínimo",
        "minimo": "mínimo",
        "Art. 2o": "Art. 2º",
        "Art. 7o": "Art. 7º",
        "periodo": "período",
        "periodos": "períodos",
        "ferias": "férias",
        "Ferias": "Férias",
        "matricula": "matrícula",
        "graduacao": "graduação",
        "solicitacao": "solicitação",
        "solicitacoes": "solicitações",
        "certificacao": "certificação",
        "estagio": "estágio",
        "transferencia": "transferência",
        "equivalencia": "equivalência",
        "publicacao": "publicação",
        "lancarem": "lançarem",
        "lancamento": "lançamento",
        "frequencia": "frequência",
        "diarios": "diários",
        "submissao": "submissão",
        "Direcao": "Direção",
        "Extensao": "Extensão",
        "extensao": "extensão",
        "inovacao": "inovação",
        "reunioes": "reuniões",
        "apos": "após",
        "Descricao": "Descrição",
        "Especificos": "Específicos",
        "Inicio": "Início",
        "inicio": "início",
        "termino": "término",
        "letivo": "letivo",
        "docentes": "docentes",
        "Apos": "Após",
        "Maximo": "Máximo",
        "maximo": "máximo",
        "obrigatorias": "obrigatórias",
        "Periodos": "Períodos",
        "periodos": "períodos",
        "pedagogicos": "pedagógicos",
        "extraordinarios": "extraordinários",
        "analise": "análise",
        "revisao": "revisão",
        "responsaveis": "responsáveis",
        "nao": "não",
        "tematica": "temática",
        "Olimpiada": "Olimpíada",
        "Robotica": "Robótica",
        "formacao": "formação",
        "pedagogica": "pedagógica",
        "Valorizacao": "Valorização",
        "Historia": "História",
        "marco": "março",
        "Mes": "Mês",
        "Confraternizacao": "Confraternização",
        "Paixao": "Paixão",
        "Independencia": "Independência",
        "Publico": "Público",
        "Consciencia": "Consciência",
        "Vespera": "Véspera",
        "Comemorativas": "Comemorativas",
        "Referencia": "Referência",
        "Educacao": "Educação",
        "Imunizacao": "Imunização",
        "Inclusao": "Inclusão",
        "Deficiencia": "Deficiência",
        "Criacao": "Criação",
        "Observacoes": "Observações",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    word_replacements = {
        "ate": "até",
        "sao": "são",
        "NAO": "NÃO",
        "havera": "haverá",
        "convocacao": "convocação",
        "ocorrerao": "ocorrerão",
        "voluntaria": "voluntária",
        "participacao": "participação",
        "Manifestacao": "Manifestação",
        "adesao": "adesão",
        "condicao": "condição",
        "Documentacao": "Documentação",
        "documentacao": "documentação",
        "obrigatoria": "obrigatória",
        "obrigatorios": "obrigatórios",
        "Obrigatorios": "Obrigatórios",
        "especificas": "específicas",
        "civicos": "cívicos",
        "variavel": "variável",
        "Unico": "Único",
        "Ciencia": "Ciência",
        "mes": "mês",
        "tematico": "temático",
        "Termino": "Término",
        "Periodo": "Período",
        "Formacao": "Formação",
    }
    for old, new in word_replacements.items():
        text = re.sub(rf"\b{old}\b", new, text)
    text = text.replace("Confraternizacao", "Confraternização")
    text = text.replace("Proclamacao", "Proclamação")
    text = text.replace(" -- ", " — ")
    text = text.replace(" no 259/2025", " nº 259/2025")
    text = text.replace("Art. 3o par. 1o", "Art. 3º, § 1º")
    text = text.replace("Art. 3o par. 3o", "Art. 3º, § 3º")
    text = text.replace("Quando um feriado nacional e utilizado", "Quando um feriado nacional é utilizado")
    text = text.replace("realizadas em feriados nacionais e **exclusivamente", "realizadas em feriados nacionais é **exclusivamente")
    text = text.replace("Nao pode haver", "Não pode haver")
    text = text.replace(" 1x/", " 1 vez/")
    text = text.replace(" 2x/", " 2 vezes/")
    return text


def write_readme(manifest: list[dict]) -> None:
    rows = "\n".join(
        f"| [{item['title']}]({item['path']}) | {item['tipo_documento']} | {item['ano']} | {item['ementa']} |"
        for item in manifest
    )
    readme = f"""# Base de Conhecimento Normativa do IFPR

## Como usar

Esta é uma base pública de consulta sobre normas, legislação, resoluções, portarias e outros documentos de referência usados em análises relacionadas ao IFPR.

Você pode usar esta base de duas formas:

1. **Consultar manualmente:** veja a lista em [Normas publicadas](#normas-publicadas), clique no documento desejado e leia o conteúdo.
2. **Usar com um agente IA:** copie o prompt abaixo e cole no ChatGPT, Claude, Codex, Cursor ou outro agente que consiga acessar links da internet.

> Aviso: esta base é uma curadoria operacional. Para decisões administrativas, jurídicas ou acadêmicas, confira sempre a publicação oficial indicada no campo `fonte` de cada documento.

Basta colar o texto abaixo no agente IA e, em seguida, fazer sua pergunta.

```text
Você tem acesso a uma base pública de conhecimento normativo do IFPR em Markdown.

Use primeiro o manifesto:
https://raw.githubusercontent.com/simplifica-if/base-conhecimento/refs/heads/main/manifest.json

Procedimento:
1. Consulte o manifest.json para identificar documentos por title, aliases, keywords, ementa, órgão, ano e status_vigencia.
2. Quando um documento for relevante, baixe o Markdown correspondente usando o campo path:
   https://raw.githubusercontent.com/simplifica-if/base-conhecimento/refs/heads/main/<path>
3. Use os arquivos Markdown como base de consulta normativa e cite sempre o title, a fonte oficial indicada em fonte e o trecho ou seção usada.
4. Não invente normas, números, datas ou obrigações. Se a base não contiver o documento necessário, diga isso e recomende consultar a fonte oficial.
5. Trate esta base como curadoria operacional. Para decisões administrativas, jurídicas ou acadêmicas, confira sempre a publicação oficial indicada em fonte.
```

Exemplos de perguntas que você pode fazer depois de colar o prompt:

- Quais normas da base tratam de PPC de cursos técnicos?
- O que a base traz sobre adaptação e flexibilização curricular?
- Quais documentos devo consultar sobre ensino médio integrado?
- Existe alguma norma do IFPR sobre assistência estudantil?

## Normas publicadas

| Documento | Tipo | Ano | Assunto |
|-----------|------|-----|---------|
{rows}

## Manutenção

```bash
python3 scripts/gerar_base.py
python3 scripts/validar_base.py
```

## Estrutura

- `normas/`: leis, resoluções, portarias, notas técnicas e compilações, organizadas por jurisdição e tipo documental.
- `manifest.json`: índice estruturado para consumo automático.
- `docs/padrao-front-matter-legislacao.md`: contrato de metadados.
- `scripts/`: geração e validação local da base.

## Licença

Conteúdo curatorial publicado sob CC BY 4.0. Textos normativos oficiais podem estar sujeitos ao regime próprio de documentos públicos; mantenha atribuição e consulte as fontes oficiais.
"""
    (ROOT / "README.md").write_text(readme, encoding="utf-8")


def write_static_files() -> None:
    (ROOT / ".gitignore").write_text(".DS_Store\n__pycache__/\n*.pyc\n", encoding="utf-8")
    (ROOT / "LICENSE").write_text(
        "Creative Commons Attribution 4.0 International\n\n"
        "Esta base curatorial é disponibilizada sob a licença CC BY 4.0.\n"
        "Texto completo: https://creativecommons.org/licenses/by/4.0/legalcode\n\n"
        "Você pode compartilhar e adaptar o material, inclusive para fins comerciais, desde que atribua a fonte.\n"
        "Textos normativos oficiais devem ser conferidos nas publicações oficiais indicadas em cada arquivo.\n",
        encoding="utf-8",
    )
    docs = ROOT / "docs"
    docs.mkdir(exist_ok=True)
    doc_path = docs / "padrao-front-matter-legislacao.md"
    if doc_path.exists():
        text = doc_path.read_text(encoding="utf-8")
    else:
        text = "## Resumo\n\nPadrão oficial de `front matter` para arquivos Markdown de legislação em `normas/` neste repositório.\n"
    text = re.sub(r"\[knowledge/legislacao\]\(" + re.escape(USER_PATH_PATTERN) + r"[^)]+/alfred4ifpr/knowledge/legislacao\)", "arquivos Markdown de legislação em `normas/` neste repositório", text)
    text = text.replace(
        "na raiz deste repositório",
        "em `normas/` neste repositório",
    )
    if "`normas/<jurisdicao>/<tipo-plural>/`" not in text:
        text = text.replace(
            "- O corpo do arquivo continua começando com `## Resumo`.",
            "- O corpo do arquivo continua começando com `## Resumo`.\n"
            "- Os arquivos devem ficar em `normas/<jurisdicao>/<tipo-plural>/`.\n"
            "- O nome do arquivo não deve usar prefixo de data. A data oficial deve ficar em `data_publicacao`.",
        )
    doc_path.write_text(text, encoding="utf-8")


def main() -> None:
    if not SOURCE.exists():
        raise SystemExit(f"Fonte não encontrada: {SOURCE}")
    write_static_files()
    manifest = []
    targets = {caminho_publico(item) for item in NORMAS}
    for stale in ROOT.glob("*.md"):
        if stale.name != "README.md":
            stale.unlink()
    normas_root = ROOT / "normas"
    if normas_root.exists():
        for stale in normas_root.rglob("*.md"):
            if str(stale.relative_to(ROOT)) not in targets:
                stale.unlink()
    for meta in NORMAS:
        public_path = caminho_publico(meta)
        source_path = caminho_fonte(meta)
        if not source_path.exists():
            raise SystemExit(f"Fonte local não encontrada: {source_path}")
        body = body_from_resumo(source_path.read_text(encoding="utf-8"))
        if meta["source"] == "resolucao-259-2025-calendario.md":
            body = fix_resolucao_259(body)
        output = frontmatter(meta) + body
        output_path = ROOT / public_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output, encoding="utf-8")
        item = {key: meta.get(key, "") for key in [
            "title",
            "tipo_documento",
            "numero",
            "ano",
            "data_publicacao",
            "orgao",
            "jurisdicao",
            "ementa",
            "status_vigencia",
            "keywords",
            "aliases",
            "fonte",
        ]}
        item["path"] = public_path
        manifest.append(item)
    manifest.sort(key=lambda item: (str(item["data_publicacao"]), item["title"]))
    (ROOT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_readme(manifest)


if __name__ == "__main__":
    main()
