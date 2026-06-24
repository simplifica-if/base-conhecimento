from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = SKILL_DIR / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from gerar_relatorio_html import ErroResultadosSubagents, gerar_relatorio_html, validar_resultados_rodada
from preparar_documento import _mesclar_identificacao_preferindo_preenchidos, preparar_documento
from cnct_catalogo import comparar_ppc_com_cnct
from analise_ppc import main as analise_ppc_main
from subagents import (
    agrupar_fichas,
    carregar_fichas_ordenadas,
    carregar_validacoes_cruzadas_ordenadas,
    ficha_requer_fundamentacao_normativa,
    ficha_requer_contexto_cnct,
    mesclar_resultados_avulsos,
    montar_grupo_avulso,
    montar_grupos_subagents,
    preparar_prompts_subagents,
)
from common import (
    BASE_ANALISE_DIR,
    FICHAS_DIR,
    extract_identificacao_from_conversion_json,
    infer_identificacao_from_markdown,
    read_json,
    round_paths,
    write_json,
)
from gerar_indice_base_analise import gerar_indice
from validar_base_analise import validar_base_analise


def _markdown_base() -> str:
    return """# Curso Técnico em Informática

Curso: Curso Técnico em Informática
Campus: Assis Chateaubriand
Modalidade: Integrado

## 1. Apresentação

O curso apresenta objetivos, perfil do egresso e justificativa institucional.
"""


def _criar_rodada(tmp_path: Path) -> Path:
    arquivo_md = tmp_path / "PPC.md"
    arquivo_md.write_text(_markdown_base(), encoding="utf-8")
    payload = preparar_documento(arquivo_md, output_base=tmp_path / "output")
    return payload["rodada_dir"]


def _resultado(ficha_id: str, estado: str = "ATENDE", evidencias: int = 3) -> dict[str, object]:
    return {
        "ficha_id": ficha_id,
        "estado": estado,
        "confianca": 0.9,
        "justificativa": f"Justificativa da ficha {ficha_id}.",
        "evidencias": [f"Evidência {indice} de {ficha_id}" for indice in range(1, evidencias + 1)],
        "lacunas": [],
        "revisao_humana_obrigatoria": False,
    }


def _payload_resultados_completos() -> dict[str, object]:
    fichas = carregar_fichas_ordenadas()
    grupos = []
    for grupo in agrupar_fichas(fichas, tamanho_grupo=20):
        grupos.append(
            {
                "grupo_id": grupo["grupo_id"],
                "resultados": [
                    _resultado(ficha["id"], evidencias=int(ficha.get("evidencia_minima", 3)))
                    for ficha in grupo["fichas"]
                ],
            }
        )
    return {
        "metadata": {"origem": "teste"},
        "grupos": grupos,
    }


def test_preparar_documento_cria_rodada_markdown_basica(tmp_path: Path) -> None:
    rodada_dir = _criar_rodada(tmp_path)
    caminhos = round_paths(rodada_dir)

    assert caminhos["ppc"].exists()
    assert caminhos["metadata"].exists()
    assert caminhos["manifesto"].exists()
    metadata = read_json(caminhos["metadata"])
    manifesto = read_json(caminhos["manifesto"])
    assert metadata["curso"] == "Curso Técnico em Informática"
    assert manifesto["execucao"] == "subagents-na-conversa"
    assert set(caminhos) == {
        "rodada_dir",
        "suporte_dir",
        "artefatos_conversao_dir",
        "ppc",
        "ppc_bruto",
        "metadata",
        "manifesto",
        "preparacao_docx",
        "cnct_contexto",
        "contexto_estrutural_subagents",
        "validacoes_cruzadas_contexto",
        "grupos_avulsos_dir",
        "prompts_subagents_dir",
        "prompts_subagents_manifest",
        "resultados_subagents",
        "grupos_subagents",
        "relatorio_html",
    }


def test_inferencia_de_campus_usa_campi_conhecidos_na_capa() -> None:
    identificacao = infer_identificacao_from_markdown(
        """# PROJETO PEDAGÓGICO DO CURSO

### TÉCNICO EM INFORMÁTICA PARA INTERNET

Quedas do Iguaçu

## SUMÁRIO
""",
        fallback_nome="PPC Técnico em Informática",
    )

    assert identificacao["campus"] == "Quedas do Iguaçu"


def test_extracao_de_campus_ignora_chaves_de_inventario() -> None:
    identificacao = extract_identificacao_from_conversion_json(
        {
            "dados_extraidos": {
                "nome_curso": "Curso Técnico em Informática para Internet",
                "unidade_de_fluxo_de_ar": "5",
                "capela_de_fluxo_laminar": "1",
            }
        }
    )

    assert identificacao["campus"] == "Campus não identificado"


def test_mesclagem_identificacao_preserva_campus_inferido_quando_conversao_nao_identifica() -> None:
    mesclada = _mesclar_identificacao_preferindo_preenchidos(
        {
            "curso": "PPC Técnico",
            "campus": "Quedas do Iguaçu",
            "modalidade": "Integrado",
        },
        {
            "curso": "Curso Técnico em Informática para Internet",
            "campus": "Campus não identificado",
            "modalidade": "Integrado ao Ensino Médio",
        },
    )

    assert mesclada["curso"] == "Curso Técnico em Informática para Internet"
    assert mesclada["campus"] == "Quedas do Iguaçu"
    assert mesclada["modalidade"] == "Integrado ao Ensino Médio"


def test_fichas_sao_agrupadas_em_blocos_estaveis_de_20() -> None:
    fichas = carregar_fichas_ordenadas()
    grupos = agrupar_fichas(fichas, tamanho_grupo=20)
    total_fichas = len(fichas)
    intervalos_esperados = [
        f"{inicio}-{min(inicio + 19, total_fichas)}" for inicio in range(1, total_fichas + 1, 20)
    ]
    totais_esperados = [
        min(20, total_fichas - indice) for indice in range(0, total_fichas, 20)
    ]

    assert total_fichas == len(list(FICHAS_DIR.glob("*.json")))
    assert [grupo["intervalo"] for grupo in grupos] == intervalos_esperados
    assert [grupo["total_fichas"] for grupo in grupos] == totais_esperados
    assert grupos[0]["grupo_id"] == "grupo-001"
    assert grupos[-1]["grupo_id"] == f"grupo-{len(grupos):03d}"


def test_indice_base_analise_esta_atualizado() -> None:
    indice_path = BASE_ANALISE_DIR / "indice.json"
    atual = read_json(indice_path)
    esperado = gerar_indice(gerado_em=atual["gerado_em"])

    assert atual == esperado


def test_base_analise_valida_contratos_e_schemas() -> None:
    assert validar_base_analise() == []


def test_montar_grupos_subagents_salva_payload_na_rodada(tmp_path: Path) -> None:
    rodada_dir = _criar_rodada(tmp_path)
    caminhos = round_paths(rodada_dir)

    payload = montar_grupos_subagents(rodada_dir)

    assert caminhos["grupos_subagents"].exists()
    assert payload["grupos_subagents_path"] == str(caminhos["grupos_subagents"])
    assert payload["ppc_markdown"] == str(caminhos["ppc"])
    assert payload["total_fichas"] == len(list(FICHAS_DIR.glob("*.json")))
    assert len(payload["grupos"]) == (payload["total_fichas"] + 19) // 20
    assert caminhos["cnct_contexto"].exists()
    assert caminhos["contexto_estrutural_subagents"].exists()
    assert caminhos["validacoes_cruzadas_contexto"].exists()
    assert payload["cnct_contexto"]["correspondencia"]["denominacao"] == "Técnico em Informática"
    assert "base-conhecimento/catalogos/cnct/index.json" in payload["cnct_contexto"]["fonte_catalogo"]
    assert payload["sintese_transversal_template"].endswith("sintese-transversal.md")
    assert payload["validacoes_cruzadas"]["total"] == len(carregar_validacoes_cruzadas_ordenadas())
    assert payload["validacoes_cruzadas"]["validacoes"][0]["id"].startswith("VC-")
    grupos_com_cnct = [grupo for grupo in payload["grupos"] if grupo["requer_contexto_cnct"]]
    assert grupos_com_cnct
    assert all("contextos" in grupo and "cnct" in grupo["contextos"] for grupo in grupos_com_cnct)
    assert all("estrutura" in grupo["contextos"] for grupo in payload["grupos"])
    grupos_com_fundamentacao = [grupo for grupo in payload["grupos"] if grupo["requer_fundamentacao_normativa"]]
    assert grupos_com_fundamentacao
    assert payload["fundamentacao_normativa"]["protocolo"] == "verificar-fundamentacao-normativa"
    assert all("fundamentacao_normativa" in grupo["contextos"] for grupo in grupos_com_fundamentacao)


def test_cli_montar_grupos_subagents_imprime_resumo_por_padrao(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rodada_dir = _criar_rodada(tmp_path)

    assert analise_ppc_main(["montar-grupos-subagents", "--rodada-dir", str(rodada_dir)]) == 0

    saida = json.loads(capsys.readouterr().out)
    assert saida["total_fichas"] == len(list(FICHAS_DIR.glob("*.json")))
    assert saida["grupos_subagents"].endswith("grupos-subagents.json")
    assert "cnct_contexto" not in saida
    assert "fichas" not in saida["grupos"][0]


def test_preparar_prompts_subagents_gera_pacotes_por_grupo(tmp_path: Path) -> None:
    rodada_dir = _criar_rodada(tmp_path)
    montar_grupos_subagents(rodada_dir, tamanho_grupo=30)

    manifest = preparar_prompts_subagents(rodada_dir)

    assert manifest["total_pacotes"] == 3
    primeiro = Path(manifest["arquivos"][0]["arquivo"])
    assert primeiro.exists()
    texto = primeiro.read_text(encoding="utf-8")
    assert "## Prompt de trabalho" in texto
    assert "## PPC.md" in texto
    assert "## Grupo e contextos" in texto
    assert "Curso Técnico em Informática" in texto


def test_contexto_cnct_inclui_resumo_estruturado_de_estagio() -> None:
    contexto = comparar_ppc_com_cnct(
        {"curso": "Curso Técnico em Informática"},
        {"dados_extraidos": {"carga_horaria_estagio": "0 horas"}},
        {},
    )

    assert contexto["correspondencia"]["denominacao"] == "Técnico em Informática"
    assert "base-conhecimento/catalogos/cnct/index.json" in contexto["fonte_catalogo"]
    assert contexto["correspondencia"]["estagio"]["menciona_estagio"] is True
    assert contexto["correspondencia"]["estagio"]["obrigatoriedade"] == "FACULTADO_A_INSTITUICAO"
    assert contexto["estagio_ppc"]["indicio_estagio_obrigatorio_por_carga"] is False
    assert contexto["comparacoes"]["estagio_cnct"]["status"] == "COMPATIVEL"


def test_catalogo_cnct_interno_foi_substituido_pela_base_unificada() -> None:
    assert not (BASE_ANALISE_DIR / "dados" / "cnct" / "catalogo_cnct.csv").exists()
    assert Path("base-conhecimento/catalogos/cnct/index.json").exists()


def test_ficha_convenios_estagio_declara_hipoteses_da_resolucao_82() -> None:
    ficha = read_json(FICHAS_DIR / "ct-curr-21.json")
    texto = " ".join(
        str(ficha.get(campo, ""))
        for campo in ("pergunta", "rubrica", "boa_evidencia", "ma_evidencia", "escalonar_quando")
    )

    assert "agente de integração" in texto
    assert "UCE pública ou privada" in texto
    assert "10 estudantes simultaneamente" in texto
    assert "Seção de Estágios e Relações Comunitárias" in texto
    assert "Direção" in texto
    assert "Termo de Compromisso de Estágio e Plano de Estágio" in texto


def test_fichas_estagio_tem_escopos_separados() -> None:
    fichas = {
        ficha_id: read_json(FICHAS_DIR / arquivo)
        for ficha_id, arquivo in {
            "CT-CURR-20": "ct-curr-20.json",
            "CT-CURR-21": "ct-curr-21.json",
            "CT-CURR-24": "ct-curr-24.json",
            "CT-CURR-25": "ct-curr-25.json",
        }.items()
    }

    texto_macro = fichas["CT-CURR-20"]["rubrica"]
    texto_convenios = fichas["CT-CURR-21"]["rubrica"]
    texto_orientacao = fichas["CT-CURR-24"]["rubrica"]
    texto_campos = fichas["CT-CURR-25"]["rubrica"]

    assert "aprovação/certificação" in texto_macro
    assert "Termo de Compromisso de Estágio e Plano de Estágio" in texto_convenios
    assert "modalidade de orientação" in texto_orientacao
    assert "componente curricular" in texto_orientacao
    assert "instituições públicas ou privadas" in texto_campos
    assert "equivalência" in texto_campos
    assert "orientação alternativa" not in texto_macro
    assert "instituições públicas ou privadas" not in texto_convenios


def test_ficha_eixo_cnct_nao_exige_area_tecnologica_no_ppc() -> None:
    ficha = read_json(FICHAS_DIR / "ct-ident-13.json")
    texto = " ".join(
        str(ficha.get(campo, ""))
        for campo in ("pergunta", "rubrica", "boa_evidencia", "ma_evidencia", "escalonar_quando")
    )

    assert "ausência de área tecnológica no PPC" in texto
    assert "não constitui lacuna" in texto
    assert "Não escalonar pela simples ausência de área tecnológica no PPC" in texto


def test_ficha_projeto_final_trata_pfi_como_pratica_profissional_articulada() -> None:
    ficha = read_json(FICHAS_DIR / "ct-curr-14.json")
    texto = " ".join(
        str(ficha.get(campo, ""))
        for campo in ("titulo", "pergunta", "rubrica", "boa_evidencia", "ma_evidencia", "escalonar_quando")
    )

    assert "Resolução CONSUP/IFPR nº 64/2022, art. 16" in ficha["referencias_normativas"]
    assert "projeto final interdisciplinar" in [consulta.casefold() for consulta in ficha["consultas"]]
    assert "Projeto Integrador" in texto
    assert "prática profissional articulada" in texto
    assert "TCC acadêmico tradicional" in texto


def test_validacao_cruzada_fecha_aritmetica_de_carga_horaria_com_memoria_de_calculo() -> None:
    validacao = read_json(BASE_ANALISE_DIR / "validacoes-cruzadas" / "vc-05-16.json")
    prompt = (SKILL_DIR / "prompts" / "sintese-transversal.md").read_text(encoding="utf-8")
    texto = " ".join(
        str(validacao.get(campo, ""))
        for campo in ("titulo", "pergunta", "rubrica", "boa_evidencia", "ma_evidencia")
    )

    assert validacao["id"] == "VC-05-16"
    assert validacao["criticidade"] == "BLOQ"
    assert "memória de cálculo passo a passo" in texto
    assert "aulas_totais * minutos_hora_aula / 60" in texto
    assert "dias letivos anuais" in texto
    assert "hora-relógio" in texto
    assert "memória de cálculo" in prompt
    assert "conversão de hora-aula para hora-relógio" in prompt


def test_ficha_formacao_docente_aceita_politica_institucional_verificavel() -> None:
    ficha = read_json(FICHAS_DIR / "ct-sup-17.json")
    texto = " ".join(
        str(ficha.get(campo, ""))
        for campo in ("pergunta", "rubrica", "boa_evidencia", "ma_evidencia", "escalonar_quando")
    )

    assert "Resolução CNE/CP nº 1/2021, art. 53" in ficha["referencias_normativas"]
    assert "Resolução CONSUP/IFPR nº 64/2022, arts. 41 a 43" in ficha["referencias_normativas"]
    assert "política institucional do IFPR" in texto
    assert "Não penalizar a simples presença de docentes bacharéis" in texto
    assert "genérica demais para ser verificável" in texto


def test_ficha_assistencia_estudantil_exige_resolucao_239_e_revogacao_das_antigas() -> None:
    ficha = read_json(FICHAS_DIR / "ct-sup-24.json")
    texto = " ".join(
        str(ficha.get(campo, ""))
        for campo in ("titulo", "pergunta", "rubrica", "boa_evidencia", "ma_evidencia", "escalonar_quando")
    )

    assert "Resolução CONSUP/IFPR nº 239/2025" in ficha["referencias_normativas"]
    assert "Lei nº 14.914/2024" in ficha["referencias_normativas"]
    assert "política institucional de assistência estudantil" in [
        consulta.casefold() for consulta in ficha["consultas"]
    ]
    assert "Resolução nº 11/2009" in texto
    assert "Resolução nº 53/2011" in texto
    assert "normas revogadas" in texto
    assert "ensino, pesquisa, extensão e inovação" in texto


def test_ficha_avaliacao_ppc_exige_periodicidade_registro_e_normas_vigentes() -> None:
    ficha = read_json(FICHAS_DIR / "ct-sup-08.json")
    texto = " ".join(
        str(ficha.get(campo, ""))
        for campo in ("titulo", "pergunta", "rubrica", "boa_evidencia", "ma_evidencia", "escalonar_quando")
    )
    consultas = [consulta.casefold() for consulta in ficha["consultas"]]

    assert "Resolução CONSUP/IFPR nº 64/2022, arts. 31 e 32" in ficha["referencias_normativas"]
    assert "Portaria PROENS/IFPR nº 121/2024, arts. 67 a 69" in ficha["referencias_normativas"]
    assert "avaliação do ppc" in consultas
    assert "avaliação emancipatória" in texto
    assert "participação estudantil" in texto
    assert "registro em atas" in texto
    assert "ações estratégicas de melhoria" in texto
    assert "não substituem a explicitação mínima do processo de avaliação periódica do PPC" in texto


def test_ficha_biblioteca_exige_acessibilidade_fisica_do_espaco() -> None:
    ficha = read_json(FICHAS_DIR / "ct-sup-25.json")
    texto = " ".join(
        str(ficha.get(campo, ""))
        for campo in ("titulo", "pergunta", "rubrica", "boa_evidencia", "ma_evidencia", "escalonar_quando")
    )
    consultas = [consulta.casefold() for consulta in ficha["consultas"]]

    assert "biblioteca" in consultas
    assert "piso térreo" in consultas
    assert "rampa" in consultas
    assert "elevador" in consultas
    assert "Lei nº 13.146/2015" in ficha["referencias_normativas"]
    assert "localização da biblioteca" in texto
    assert "não estiver no térreo" in texto
    assert "circulação interna" in texto
    assert "declaração genérica de acessibilidade do campus" in texto


def test_montar_grupos_subagents_anexa_representacao_grafica_quando_disponivel(tmp_path: Path) -> None:
    rodada_dir = _criar_rodada(tmp_path)
    caminhos = round_paths(rodada_dir)
    artefatos_dir = caminhos["artefatos_conversao_dir"]
    imagem = artefatos_dir / "imagens" / "representacao_grafica.png"
    imagem.parent.mkdir(parents=True)
    imagem.write_bytes(b"imagem")
    dados = artefatos_dir / "dados.json"
    write_json(dados, {"representacao_grafica": {"extraida": True, "caminho": "imagens/representacao_grafica.png"}})
    write_json(caminhos["preparacao_docx"], {"dados": str(dados)})

    payload = montar_grupos_subagents(rodada_dir)
    grupos_com_anexo = [grupo for grupo in payload["grupos"] if grupo["requer_anexos_visuais"]]

    assert grupos_com_anexo
    assert grupos_com_anexo[0]["contextos"]["anexos_visuais"][0]["arquivo"] == str(imagem.resolve())


def test_detector_identifica_fichas_que_dependem_do_cnct() -> None:
    fichas = {ficha["id"]: ficha for ficha in carregar_fichas_ordenadas()}

    assert ficha_requer_contexto_cnct(fichas["CT-IDENT-01"])
    assert not ficha_requer_contexto_cnct(fichas["CT-SUP-01"])


def test_detector_identifica_fichas_que_dependem_de_fundamentacao_normativa() -> None:
    fichas = {ficha["id"]: ficha for ficha in carregar_fichas_ordenadas()}

    assert ficha_requer_fundamentacao_normativa(fichas["CT-IDENT-08"])
    assert ficha_requer_fundamentacao_normativa(fichas["CT-CURR-20"])
    assert not ficha_requer_fundamentacao_normativa(fichas["CT-IDENT-02"])


def test_gerar_relatorio_html_aceita_resultados_validos(tmp_path: Path) -> None:
    rodada_dir = _criar_rodada(tmp_path)
    caminhos = round_paths(rodada_dir)
    resultados_path = caminhos["suporte_dir"] / "resultados-subagents.json"
    write_json(resultados_path, _payload_resultados_completos())

    payload = gerar_relatorio_html(rodada_dir, Path("resultados-subagents.json"))

    assert payload["relatorio_html"] == caminhos["relatorio_html"]
    assert payload["total_fichas"] == len(list(FICHAS_DIR.glob("*.json")))
    assert payload["total_alertas_transversais"] == 0
    html = caminhos["relatorio_html"].read_text(encoding="utf-8")
    assert "Análise de PPC · sub-agentes na conversa" in html
    assert "Curso Técnico em Informática" in html
    assert "CT-IDENT-01" in html
    assert 'id="filtro-busca"' in html
    assert 'id="filtro-feedback"' in html


def test_validar_resultados_rodada_retorna_resumo_sem_gerar_html(tmp_path: Path) -> None:
    rodada_dir = _criar_rodada(tmp_path)
    caminhos = round_paths(rodada_dir)
    write_json(caminhos["suporte_dir"] / "resultados-subagents.json", _payload_resultados_completos())

    payload = validar_resultados_rodada(rodada_dir, Path("resultados-subagents.json"))

    assert payload["valido"] is True
    assert payload["total_fichas"] == len(list(FICHAS_DIR.glob("*.json")))
    assert payload["total_fichas_esperadas"] == payload["total_fichas"]
    assert payload["total_alertas_transversais"] == 0
    assert payload["contagem_estado"] == {"ATENDE": payload["total_fichas"]}
    assert not caminhos["relatorio_html"].exists()


def test_gerar_relatorio_html_renderiza_fundamentacao_normativa(tmp_path: Path) -> None:
    rodada_dir = _criar_rodada(tmp_path)
    caminhos = round_paths(rodada_dir)
    payload = _payload_resultados_completos()
    primeiro = payload["grupos"][0]["resultados"][0]
    primeiro["fundamentacao_normativa"] = [
        {
            "status": "CONFIRMADA_COM_RESSALVA",
            "trecho_ppc": "O PPC afirma atendimento à Resolução CNE/CP nº 1/2021.",
            "norma": "Resolução CNE/CP nº 1/2021",
            "fonte": "base-conhecimento/normas/br/resolucoes/RESOLUCAO_CNE-CP_1-2021_dcnept.md",
            "dispositivo": "Diretrizes gerais da EPT",
            "evidencia": "A norma trata das DCN gerais para a Educação Profissional e Tecnológica.",
            "analise": "A citação é pertinente, mas precisa indicar o alcance específico usado pelo PPC.",
            "recomendacao": "Explicitar quais diretrizes orientam a organização curricular.",
        }
    ]
    write_json(caminhos["suporte_dir"] / "resultados-subagents.json", payload)

    gerar_relatorio_html(rodada_dir, Path("resultados-subagents.json"))

    html = caminhos["relatorio_html"].read_text(encoding="utf-8")
    assert "Fundamentação normativa verificada" in html
    assert "CONFIRMADA_COM_RESSALVA" in html
    assert "RESOLUCAO_CNE-CP_1-2021_dcnept.md" in html


def test_gerar_relatorio_html_renderiza_evidencia_estruturada(tmp_path: Path) -> None:
    rodada_dir = _criar_rodada(tmp_path)
    caminhos = round_paths(rodada_dir)
    payload = _payload_resultados_completos()
    payload["grupos"][0]["resultados"][0]["evidencias"] = [
        {
            "trecho": "O PPC identifica o curso como Técnico em Informática.",
            "secao": "1",
            "localizador": "Quadro de identificação",
            "fonte": "PPC.md",
            "artefato": "",
        },
        {
            "trecho": "A modalidade é integrada.",
            "secao": "1",
            "localizador": "Identificação",
            "fonte": "PPC.md",
            "artefato": "",
        },
    ]
    write_json(caminhos["suporte_dir"] / "resultados-subagents.json", payload)

    gerar_relatorio_html(rodada_dir, Path("resultados-subagents.json"))

    html = caminhos["relatorio_html"].read_text(encoding="utf-8")
    assert "Quadro de identificação" in html
    assert "Fonte:</strong> PPC.md" in html


def test_gerar_relatorio_html_rejeita_ficha_duplicada(tmp_path: Path) -> None:
    rodada_dir = _criar_rodada(tmp_path)
    caminhos = round_paths(rodada_dir)
    payload = _payload_resultados_completos()
    primeiro = payload["grupos"][0]["resultados"][0]
    payload["grupos"][1]["resultados"][0] = dict(primeiro)
    write_json(caminhos["suporte_dir"] / "resultados-subagents.json", payload)

    with pytest.raises(ErroResultadosSubagents, match="duplicadas"):
        gerar_relatorio_html(rodada_dir, Path("resultados-subagents.json"))


def test_gerar_relatorio_html_rejeita_ficha_desconhecida(tmp_path: Path) -> None:
    rodada_dir = _criar_rodada(tmp_path)
    caminhos = round_paths(rodada_dir)
    payload = _payload_resultados_completos()
    payload["grupos"][0]["resultados"][0]["ficha_id"] = "CT-NAO-EXISTE"
    write_json(caminhos["suporte_dir"] / "resultados-subagents.json", payload)

    with pytest.raises(ErroResultadosSubagents, match="desconhecidas"):
        gerar_relatorio_html(rodada_dir, Path("resultados-subagents.json"))


def test_gerar_relatorio_html_rejeita_ficha_faltante(tmp_path: Path) -> None:
    rodada_dir = _criar_rodada(tmp_path)
    caminhos = round_paths(rodada_dir)
    payload = _payload_resultados_completos()
    payload["grupos"][0]["resultados"].pop()
    write_json(caminhos["suporte_dir"] / "resultados-subagents.json", payload)

    with pytest.raises(ErroResultadosSubagents, match="sem resultado"):
        gerar_relatorio_html(rodada_dir, Path("resultados-subagents.json"))


def test_gerar_relatorio_html_rejeita_evidencias_abaixo_do_minimo(tmp_path: Path) -> None:
    rodada_dir = _criar_rodada(tmp_path)
    caminhos = round_paths(rodada_dir)
    payload = _payload_resultados_completos()
    payload["grupos"][0]["resultados"][0]["evidencias"] = []
    write_json(caminhos["suporte_dir"] / "resultados-subagents.json", payload)

    with pytest.raises(ErroResultadosSubagents, match="mínimo exigido"):
        gerar_relatorio_html(rodada_dir, Path("resultados-subagents.json"))


def test_gerar_relatorio_html_renderiza_alertas_transversais(tmp_path: Path) -> None:
    rodada_dir = _criar_rodada(tmp_path)
    caminhos = round_paths(rodada_dir)
    payload = _payload_resultados_completos()
    payload["alertas_transversais"] = [
        {
            "id": "ALERTA-001",
            "validacao_id": carregar_validacoes_cruzadas_ordenadas()[0]["id"],
            "titulo": "Inconsistência transversal",
            "criticidade": "OBRIG",
            "descricao": "Perfil e matriz precisam de revisão conjunta.",
            "fichas_relacionadas": ["CT-IDENT-01"],
            "evidencias": ["Evidência transversal"],
            "revisao_humana_obrigatoria": True,
        }
    ]
    write_json(caminhos["suporte_dir"] / "resultados-subagents.json", payload)

    relatorio = gerar_relatorio_html(rodada_dir, Path("resultados-subagents.json"))

    assert relatorio["total_alertas_transversais"] == 1
    html = caminhos["relatorio_html"].read_text(encoding="utf-8")
    assert "Alertas transversais" in html
    assert "ALERTA-001" in html
    assert "Validação cruzada" in html


def test_gerar_relatorio_html_exige_validacao_id_em_alerta_transversal(tmp_path: Path) -> None:
    rodada_dir = _criar_rodada(tmp_path)
    caminhos = round_paths(rodada_dir)
    payload = _payload_resultados_completos()
    payload["alertas_transversais"] = [
        {
            "id": "ALERTA-001",
            "titulo": "Inconsistência transversal",
            "criticidade": "OBRIG",
            "descricao": "Perfil e matriz precisam de revisão conjunta.",
            "fichas_relacionadas": ["CT-IDENT-01"],
            "evidencias": ["Evidência transversal"],
            "revisao_humana_obrigatoria": True,
        }
    ]
    write_json(caminhos["suporte_dir"] / "resultados-subagents.json", payload)

    with pytest.raises(ErroResultadosSubagents, match="validacao_id"):
        gerar_relatorio_html(rodada_dir, Path("resultados-subagents.json"))


def test_gerar_relatorio_html_exige_feedback_autores_quando_ficha_solicita(tmp_path: Path) -> None:
    rodada_dir = _criar_rodada(tmp_path)
    caminhos = round_paths(rodada_dir)
    payload = _payload_resultados_completos()
    for grupo in payload["grupos"]:
        for resultado in grupo["resultados"]:
            if resultado["ficha_id"] == "CT-TRANS-08":
                resultado["estado"] = "NAO_ATENDE"
                resultado["revisao_humana_obrigatoria"] = True
                resultado.pop("feedback_autores", None)
    write_json(caminhos["suporte_dir"] / "resultados-subagents.json", payload)

    with pytest.raises(ErroResultadosSubagents, match="feedback_autores"):
        gerar_relatorio_html(rodada_dir, Path("resultados-subagents.json"))


def test_gerar_relatorio_html_renderiza_feedback_autores(tmp_path: Path) -> None:
    rodada_dir = _criar_rodada(tmp_path)
    caminhos = round_paths(rodada_dir)
    payload = _payload_resultados_completos()
    texto_feedback = "Recomenda-se explicitar a articulação entre concepção, perfil e matriz."
    for grupo in payload["grupos"]:
        for resultado in grupo["resultados"]:
            if resultado["ficha_id"] == "CT-TRANS-08":
                resultado["estado"] = "NAO_ATENDE"
                resultado["revisao_humana_obrigatoria"] = True
                resultado["feedback_autores"] = texto_feedback
    write_json(caminhos["suporte_dir"] / "resultados-subagents.json", payload)

    relatorio = gerar_relatorio_html(rodada_dir, Path("resultados-subagents.json"))

    assert relatorio["total_fichas"] == len(list(FICHAS_DIR.glob("*.json")))
    html = caminhos["relatorio_html"].read_text(encoding="utf-8")
    assert "Feedback sugerido aos autores" in html
    assert texto_feedback in html
    assert "Feedback aos autores" in html


def test_montar_grupo_avulso_e_mesclar_resultados(tmp_path: Path) -> None:
    rodada_dir = _criar_rodada(tmp_path)
    caminhos = round_paths(rodada_dir)
    base = _payload_resultados_completos()
    write_json(caminhos["resultados_subagents"], base)

    grupo = montar_grupo_avulso(rodada_dir, ["CT-IDENT-01"])
    avulso_path = caminhos["suporte_dir"] / "resultado-avulso.json"
    write_json(
        avulso_path,
        {
            "grupo_id": grupo["grupo"]["grupo_id"],
            "resultados": [_resultado("CT-IDENT-01", estado="INCONCLUSIVO")],
        },
    )
    mesclado = mesclar_resultados_avulsos(
        rodada_dir,
        Path("resultados-subagents.json"),
        Path("resultado-avulso.json"),
    )
    payload_mesclado = read_json(caminhos["resultados_subagents"])
    resultados = [
        item
        for grupo_payload in payload_mesclado["grupos"]
        for item in grupo_payload["resultados"]
        if item["ficha_id"] == "CT-IDENT-01"
    ]

    assert Path(grupo["grupo_avulso_path"]).exists()
    assert mesclado["fichas_substituidas"] == ["CT-IDENT-01"]
    assert len(resultados) == 1
    assert resultados[0]["estado"] == "INCONCLUSIVO"


def test_nao_ha_codigo_de_execucao_por_cli_ou_tokens() -> None:
    textos = []
    for caminho in SCRIPTS_DIR.rglob("*.py"):
        textos.append(caminho.read_text(encoding="utf-8"))
    conteudo = "\n".join(textos)

    proibidos = [
        "codex exec",
        "ANALISE_PPC_CODEX",
        "ANALISE_PPC_GEMINI",
        "executar_prompt",
        "uso_tokens",
        "contabilizar-tokens",
    ]
    for proibido in proibidos:
        assert proibido not in conteudo


def test_prompt_subagent_declara_contrato_de_saida() -> None:
    prompt = (SKILL_DIR / "prompts" / "subagent-lote-fichas.md").read_text(encoding="utf-8")
    for campo in (
        "grupo_id",
        "ficha_id",
        "estado",
        "confianca",
        "justificativa",
        "evidencias",
        "lacunas",
        "revisao_humana_obrigatoria",
        "fundamentacao_normativa",
        "feedback_autores",
    ):
        assert campo in prompt


def test_prompt_sintese_transversal_declara_contrato() -> None:
    prompt = (SKILL_DIR / "prompts" / "sintese-transversal.md").read_text(encoding="utf-8")
    assert "alertas_transversais" in prompt
    assert "validacao_id" in prompt
    assert "fichas_relacionadas" in prompt


def test_fixtures_qualitativas_exercitam_norma_e_estagio(tmp_path: Path) -> None:
    fixture_norma = SKILL_DIR / "tests" / "fixtures" / "ppc_norma_sem_suporte.md"
    fixture_estagio = SKILL_DIR / "tests" / "fixtures" / "ppc_estagio_contraditorio.md"
    assert "dispensa a consulta ao Catálogo Nacional" in fixture_norma.read_text(encoding="utf-8")
    assert "estágio é não obrigatório" in fixture_estagio.read_text(encoding="utf-8")

    payload = preparar_documento(fixture_estagio, output_base=tmp_path / "output")
    grupos = montar_grupos_subagents(payload["rodada_dir"])

    assert grupos["cnct_contexto"]["correspondencia"]["denominacao"] == "Técnico em Informática"
    assert any(grupo["requer_fundamentacao_normativa"] for grupo in grupos["grupos"])
