from __future__ import annotations

import csv
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from common import APP_DIR, read_json, round_paths, sha256_file, write_json

CNCT_CATALOGO_PATH = APP_DIR / "base-analise" / "dados" / "cnct" / "catalogo_cnct.csv"
CNCT_CAMPOS = (
    ("Eixo Tecnológico", "eixo_tecnologico"),
    ("Área Tecnológica", "area_tecnologica"),
    ("Denominação do Curso", "denominacao"),
    ("Perfil Profissional de Conclusão", "perfil_profissional"),
    ("Carga Horária Mínima", "carga_horaria_minima"),
    ("Descrição Carga Horária Mínima", "descricao_carga_horaria_minima"),
    ("Pré-Requisitos para Ingresso", "pre_requisitos_ingresso"),
    ("Itinerários Formativos", "itinerarios_formativos"),
    ("Campo de Atuação", "campo_atuacao"),
    ("Ocupações CBO Associadas", "ocupacoes_cbo"),
    ("Infraestrutura Mínima", "infraestrutura_minima"),
    ("Legislação Profissional", "legislacao_profissional"),
)


def normalizar_texto_cnct(texto: Any) -> str:
    normalizado = unicodedata.normalize("NFD", str(texto or ""))
    normalizado = "".join(char for char in normalizado if unicodedata.category(char) != "Mn")
    normalizado = normalizado.casefold()
    normalizado = re.sub(r"[^a-z0-9]+", " ", normalizado)
    return " ".join(normalizado.split())


def normalizar_denominacao_cnct(texto: Any) -> str:
    normalizado = normalizar_texto_cnct(texto)
    return re.sub(r"^curso\s+", "", normalizado).strip()


def extrair_numero_horas(valor: Any) -> int | None:
    match = re.search(r"\d[\d.]*", str(valor or ""))
    if not match:
        return None
    digitos = re.sub(r"\D", "", match.group(0))
    return int(digitos) if digitos else None


def _texto_limpo(valor: Any) -> str:
    return " ".join(str(valor or "").split())


def _normalizar_linha_csv(linha: dict[str, str]) -> dict[str, str]:
    return {str(chave or "").lstrip("\ufeff").strip(): valor for chave, valor in linha.items()}


def _janelas_termo(texto_normalizado: str, termo: str, raio: int = 160) -> list[str]:
    return [
        texto_normalizado[max(0, match.start() - raio) : match.end() + raio]
        for match in re.finditer(re.escape(termo), texto_normalizado)
    ]


def resumir_estagio_cnct(curso: dict[str, Any]) -> dict[str, Any]:
    descricao = _texto_limpo(curso.get("descricao_carga_horaria_minima"))
    legislacao = _texto_limpo(curso.get("legislacao_profissional"))
    texto_normalizado = normalizar_texto_cnct(descricao)
    menciona_estagio = "estagio" in texto_normalizado
    janelas_estagio = _janelas_termo(texto_normalizado, "estagio")
    contexto_estagio = " ".join(janelas_estagio)
    menciona_obrigatorio = "obrigatorio" in contexto_estagio
    menciona_faculdade = "podera" in contexto_estagio
    menciona_dever = any(termo in contexto_estagio for termo in ("devera", "deve", "exige", "obrigatorio conforme"))

    if not menciona_estagio:
        obrigatoriedade = "NAO_MENCIONADO"
        sintese = "A descrição de carga horária mínima do CNCT não menciona estágio."
    elif menciona_faculdade and menciona_obrigatorio:
        obrigatoriedade = "FACULTADO_A_INSTITUICAO"
        sintese = "O CNCT faculta estágio curricular supervisionado obrigatório à instituição ofertante."
    elif menciona_dever and menciona_obrigatorio:
        obrigatoriedade = "OBRIGATORIO"
        sintese = "O CNCT indica estágio curricular supervisionado obrigatório."
    elif menciona_obrigatorio:
        obrigatoriedade = "OBRIGATORIO_OU_CONDICIONADO"
        sintese = "O CNCT menciona estágio obrigatório, mas a condição precisa ser conferida no texto do catálogo."
    else:
        obrigatoriedade = "MENCIONA_SEM_OBRIGATORIEDADE_CLARA"
        sintese = "O CNCT menciona estágio, sem obrigatoriedade clara na descrição."

    return {
        "fonte_campo": "Descrição Carga Horária Mínima",
        "menciona_estagio": menciona_estagio,
        "obrigatoriedade": obrigatoriedade,
        "sintese": sintese,
        "exige_presencialidade_em_ead": bool(menciona_estagio and "ead" in texto_normalizado and "presencial" in texto_normalizado),
        "menciona_normas_especificas": bool(
            any(
                termo in texto_normalizado
                for termo in (
                    "legislacoes normativas especificas",
                    "legislacao especifica",
                    "normativas especificas",
                    "normas especificas",
                )
            )
            or legislacao
        ),
        "legislacao_profissional_cnct": legislacao,
        "trecho_descricao_carga_horaria": descricao[:900] if menciona_estagio else "",
    }


def carregar_catalogo_cnct(catalogo_path: Path | None = None) -> list[dict[str, Any]]:
    caminho = catalogo_path or CNCT_CATALOGO_PATH
    cursos: list[dict[str, Any]] = []
    with caminho.open(encoding="utf-8-sig", newline="") as arquivo:
        reader = csv.DictReader(arquivo, delimiter=";")
        for indice, linha_bruta in enumerate(reader, start=1):
            linha = _normalizar_linha_csv(linha_bruta)
            denominacao = str(linha.get("Denominação do Curso") or "").strip()
            if not denominacao:
                continue
            campos_csv = {campo_csv: str(linha.get(campo_csv) or "").strip() for campo_csv, _ in CNCT_CAMPOS}
            curso = {
                "indice": indice,
                "campos_csv": campos_csv,
            }
            for campo_csv, campo_normalizado in CNCT_CAMPOS:
                curso[campo_normalizado] = campos_csv[campo_csv]
            curso.update(
                {
                    "denominacao_normalizada": normalizar_denominacao_cnct(denominacao),
                    "carga_horaria_minima_horas": extrair_numero_horas(campos_csv["Carga Horária Mínima"]),
                }
            )
            cursos.append(curso)
    return cursos


def _score_denominacao(consulta_normalizada: str, denominacao_normalizada: str) -> float:
    if not consulta_normalizada or not denominacao_normalizada:
        return 0.0
    if consulta_normalizada == denominacao_normalizada:
        return 1.0
    sequence_score = SequenceMatcher(None, consulta_normalizada, denominacao_normalizada).ratio()
    tokens_consulta = set(consulta_normalizada.split())
    tokens_denominacao = set(denominacao_normalizada.split())
    if not tokens_consulta or not tokens_denominacao:
        return sequence_score
    intersecao = tokens_consulta & tokens_denominacao
    token_score = (2 * len(intersecao)) / (len(tokens_consulta) + len(tokens_denominacao))
    if consulta_normalizada in denominacao_normalizada or denominacao_normalizada in consulta_normalizada:
        token_score = max(token_score, 0.9)
    return max(sequence_score, token_score)


def _tipo_correspondencia(score: float) -> str:
    if score >= 1:
        return "EXATA"
    if score >= 0.86:
        return "ALTA_CONFIANCA"
    if score >= 0.72:
        return "POSSIVEL"
    return "BAIXA_CONFIANCA"


def _resumir_curso(curso: dict[str, Any], score: float, completo: bool = False) -> dict[str, Any]:
    resumo = {
        "indice": curso["indice"],
        "score": round(score, 4),
        "denominacao": curso["denominacao"],
        "eixo_tecnologico": curso["eixo_tecnologico"],
        "area_tecnologica": curso["area_tecnologica"],
        "carga_horaria_minima": curso["carga_horaria_minima"],
        "carga_horaria_minima_horas": curso["carga_horaria_minima_horas"],
        "ocupacoes_cbo": curso["ocupacoes_cbo"],
        "infraestrutura_minima": curso["infraestrutura_minima"],
        "legislacao_profissional": curso["legislacao_profissional"],
        "estagio": resumir_estagio_cnct(curso),
    }
    if completo:
        for _, campo_normalizado in CNCT_CAMPOS:
            resumo[campo_normalizado] = curso[campo_normalizado]
        resumo["campos_csv"] = curso["campos_csv"]
    return resumo


def buscar_cursos_cnct(
    consulta: str,
    catalogo_path: Path | None = None,
    limite: int = 5,
    completo: bool = False,
) -> list[dict[str, Any]]:
    consulta_normalizada = normalizar_denominacao_cnct(consulta)
    if not consulta_normalizada:
        return []
    candidatos = []
    for curso in carregar_catalogo_cnct(catalogo_path):
        score = _score_denominacao(consulta_normalizada, curso["denominacao_normalizada"])
        if score >= 0.55:
            candidatos.append(_resumir_curso(curso, score, completo=completo))
    candidatos.sort(key=lambda item: (-item["score"], item["denominacao"]))
    return candidatos[:limite]


def _dados_extraidos(dados_conversao: dict[str, Any]) -> dict[str, Any]:
    dados = dados_conversao.get("dados_extraidos", {}) if isinstance(dados_conversao, dict) else {}
    return dados if isinstance(dados, dict) else {}


def _primeiro_valor_preenchido(*valores: Any) -> Any:
    for valor in valores:
        if str(valor or "").strip():
            return valor
    return None


def _read_json_if_exists(path_value: Any) -> dict[str, Any]:
    if not path_value:
        return {}
    path = Path(str(path_value))
    if not path.exists():
        return {}
    payload = read_json(path)
    return payload if isinstance(payload, dict) else {}


def _carga_horaria_ppc(dados: dict[str, Any], matriz_payload: dict[str, Any]) -> dict[str, Any]:
    candidatos = [
        ("dados_extraidos.carga_horaria_total", dados.get("carga_horaria_total")),
        ("dados_extraidos.carga_horaria_total_curso", dados.get("carga_horaria_total_curso")),
        ("dados_extraidos.carga_horaria_minima", dados.get("carga_horaria_minima")),
        ("dados_extraidos.carga_horaria_minima_cnct", dados.get("carga_horaria_minima_cnct")),
    ]
    totais = matriz_payload.get("totais") if isinstance(matriz_payload, dict) else {}
    if isinstance(totais, dict):
        candidatos.extend(
            [
                ("matriz_curricular.totais.ch_total_hora_relogio", totais.get("ch_total_hora_relogio")),
                ("matriz_curricular.totais.ch_total_hora_aula", totais.get("ch_total_hora_aula")),
            ]
        )
    for fonte, valor in candidatos:
        horas = extrair_numero_horas(valor)
        if horas is not None:
            return {"valor_horas": horas, "fonte": fonte, "valor_original": valor}
    return {"valor_horas": None, "fonte": None, "valor_original": None}


def _iter_componentes_matriz(matriz_payload: dict[str, Any]) -> list[dict[str, Any]]:
    componentes: list[dict[str, Any]] = []
    componentes_raiz = matriz_payload.get("componentes") if isinstance(matriz_payload, dict) else None
    if isinstance(componentes_raiz, list):
        componentes.extend(item for item in componentes_raiz if isinstance(item, dict))
    for chave_grupo in ("anos", "series"):
        grupos = matriz_payload.get(chave_grupo) if isinstance(matriz_payload, dict) else None
        if not isinstance(grupos, list):
            continue
        for grupo in grupos:
            if not isinstance(grupo, dict):
                continue
            itens = grupo.get("componentes")
            if isinstance(itens, list):
                componentes.extend(item for item in itens if isinstance(item, dict))
    return componentes


def _carga_horaria_componente(componente: dict[str, Any]) -> int | None:
    candidatos = (
        componente.get("ch_hora_relogio_cnct"),
        componente.get("ch_hora_relogio"),
        componente.get("ch_hora_aula"),
        componente.get("carga_horaria"),
    )
    horas = [valor for candidato in candidatos if (valor := extrair_numero_horas(candidato)) is not None]
    return max(horas) if horas else None


def _linhas_estagio_matriz(matriz_payload: dict[str, Any]) -> list[dict[str, Any]]:
    linhas: list[dict[str, Any]] = []
    for componente in _iter_componentes_matriz(matriz_payload):
        nome = _texto_limpo(componente.get("nome") or componente.get("componente") or componente.get("titulo"))
        if "estagio" not in normalizar_texto_cnct(nome):
            continue
        linhas.append(
            {
                "nome": nome,
                "carga_horaria_efetiva": _carga_horaria_componente(componente),
            }
        )
    return linhas


def _estagio_ppc(dados: dict[str, Any], matriz_payload: dict[str, Any]) -> dict[str, Any]:
    candidatos = [
        ("dados_extraidos.carga_horaria_estagio", dados.get("carga_horaria_estagio")),
        ("dados_extraidos.estagio", dados.get("estagio")),
    ]
    carga_declarada = {"valor_horas": None, "fonte": None, "valor_original": None}
    for fonte, valor in candidatos:
        horas = extrair_numero_horas(valor)
        if horas is not None:
            carga_declarada = {"valor_horas": horas, "fonte": fonte, "valor_original": valor}
            break

    linhas_matriz = _linhas_estagio_matriz(matriz_payload)
    cargas_matriz = [
        linha["carga_horaria_efetiva"]
        for linha in linhas_matriz
        if isinstance(linha.get("carga_horaria_efetiva"), int)
    ]
    maior_carga_matriz = max(cargas_matriz) if cargas_matriz else None
    indicio_obrigatorio = any(
        isinstance(valor, int) and valor > 0
        for valor in (carga_declarada["valor_horas"], maior_carga_matriz)
    )
    return {
        "carga_horaria_declarada": carga_declarada,
        "linhas_estagio_matriz": linhas_matriz,
        "maior_carga_horaria_matriz": maior_carga_matriz,
        "indicio_estagio_obrigatorio_por_carga": indicio_obrigatorio,
        "observacao": (
            "Carga de estágio maior que zero em dados estruturados ou matriz é tratada como indício "
            "de estágio obrigatório; a confirmação depende da leitura do PPC completo."
        ),
    }


def _comparar_estagio_cnct(estagio_cnct: dict[str, Any], estagio_ppc: dict[str, Any]) -> dict[str, Any]:
    obrigatoriedade = str(estagio_cnct.get("obrigatoriedade") or "")
    tem_carga_ppc = bool(estagio_ppc.get("indicio_estagio_obrigatorio_por_carga"))
    if obrigatoriedade == "OBRIGATORIO":
        return {
            "status": "COMPATIVEL" if tem_carga_ppc else "DIVERGENTE",
            "obrigatoriedade_cnct": obrigatoriedade,
            "indicio_estagio_obrigatorio_ppc": tem_carga_ppc,
            "motivo": (
                "CNCT indica estágio obrigatório e há carga de estágio no PPC estruturado."
                if tem_carga_ppc
                else "CNCT indica estágio obrigatório, mas o PPC estruturado não trouxe carga de estágio."
            ),
        }
    if obrigatoriedade == "FACULTADO_A_INSTITUICAO":
        return {
            "status": "COMPATIVEL",
            "obrigatoriedade_cnct": obrigatoriedade,
            "indicio_estagio_obrigatorio_ppc": tem_carga_ppc,
            "exige_justificativa_no_ppc_se_obrigatorio": tem_carga_ppc,
            "motivo": "CNCT faculta a decisão à instituição; se houver estágio obrigatório, o PPC deve justificar e organizar a oferta.",
        }
    return {
        "status": "INCONCLUSIVO" if tem_carga_ppc else "NAO_APLICAVEL",
        "obrigatoriedade_cnct": obrigatoriedade,
        "indicio_estagio_obrigatorio_ppc": tem_carga_ppc,
        "motivo": "O texto estruturado do CNCT não permite uma comparação automática conclusiva sobre estágio.",
    }


def comparar_ppc_com_cnct(
    metadata: dict[str, Any],
    dados_conversao: dict[str, Any],
    matriz_payload: dict[str, Any],
    catalogo_path: Path | None = None,
) -> dict[str, Any]:
    caminho_catalogo = catalogo_path or CNCT_CATALOGO_PATH
    dados = _dados_extraidos(dados_conversao)
    curso_declarado = _primeiro_valor_preenchido(dados.get("curso_cnct"), metadata.get("curso"), dados.get("nome_curso"))
    eixo_declarado = _primeiro_valor_preenchido(dados.get("eixo_tecnologico"), metadata.get("eixo_tecnologico"))
    carga_ppc = _carga_horaria_ppc(dados, matriz_payload)
    estagio_ppc = _estagio_ppc(dados, matriz_payload)

    if not caminho_catalogo.exists():
        return {
            "disponivel": False,
            "fonte_catalogo": str(caminho_catalogo),
            "motivo": "Catálogo CNCT não encontrado.",
            "curso_declarado": curso_declarado,
            "eixo_declarado": eixo_declarado,
            "carga_horaria_ppc": carga_ppc,
            "estagio_ppc": estagio_ppc,
            "candidatos": [],
            "correspondencia": None,
            "comparacoes": {},
        }

    candidatos = buscar_cursos_cnct(str(curso_declarado or ""), caminho_catalogo)
    candidatos_completos = buscar_cursos_cnct(str(curso_declarado or ""), caminho_catalogo, limite=5, completo=True)
    correspondencia = candidatos[0] if candidatos and candidatos[0]["score"] >= 0.72 else None
    correspondencia_completa = candidatos_completos[0] if candidatos_completos and candidatos_completos[0]["score"] >= 0.72 else None
    comparacoes: dict[str, Any] = {}
    if correspondencia:
        tipo = _tipo_correspondencia(float(correspondencia["score"]))
        comparacoes["denominacao"] = {
            "status": "COMPATIVEL" if tipo in {"EXATA", "ALTA_CONFIANCA"} else "INCONCLUSIVO",
            "tipo_correspondencia": tipo,
            "valor_ppc": curso_declarado,
            "valor_cnct": correspondencia["denominacao"],
            "score": correspondencia["score"],
        }
        eixo_cnct = correspondencia.get("eixo_tecnologico")
        if eixo_declarado:
            comparacoes["eixo_tecnologico"] = {
                "status": "COMPATIVEL"
                if normalizar_texto_cnct(eixo_declarado) == normalizar_texto_cnct(eixo_cnct)
                else "DIVERGENTE",
                "valor_ppc": eixo_declarado,
                "valor_cnct": eixo_cnct,
            }
        carga_minima = correspondencia.get("carga_horaria_minima_horas")
        if carga_minima is not None and carga_ppc["valor_horas"] is not None:
            comparacoes["carga_horaria_minima"] = {
                "status": "COMPATIVEL" if carga_ppc["valor_horas"] >= carga_minima else "DIVERGENTE",
                "valor_ppc_horas": carga_ppc["valor_horas"],
                "valor_cnct_minimo_horas": carga_minima,
                "fonte_ppc": carga_ppc["fonte"],
            }
        estagio_cnct = correspondencia.get("estagio")
        if isinstance(estagio_cnct, dict):
            comparacoes["estagio_cnct"] = _comparar_estagio_cnct(estagio_cnct, estagio_ppc)

    return {
        "disponivel": True,
        "fonte_catalogo": str(caminho_catalogo),
        "catalogo_sha256": sha256_file(caminho_catalogo),
        "curso_declarado": curso_declarado,
        "eixo_declarado": eixo_declarado,
        "carga_horaria_ppc": carga_ppc,
        "estagio_ppc": estagio_ppc,
        "candidatos": candidatos,
        "correspondencia": {
            **correspondencia_completa,
            "tipo_correspondencia": _tipo_correspondencia(float(correspondencia_completa["score"])),
        }
        if correspondencia_completa
        else None,
        "comparacoes": comparacoes,
    }


def gerar_contexto_cnct_rodada(rodada_dir: Path, catalogo_path: Path | None = None) -> dict[str, Any]:
    caminhos = round_paths(rodada_dir)
    metadata = read_json(caminhos["metadata"]) if caminhos["metadata"].exists() else {}
    preparacao = read_json(caminhos["preparacao_docx"]) if caminhos["preparacao_docx"].exists() else {}
    dados_conversao = _read_json_if_exists(preparacao.get("dados"))
    matriz_payload = _read_json_if_exists(preparacao.get("matriz_curricular"))
    contexto = comparar_ppc_com_cnct(metadata, dados_conversao, matriz_payload, catalogo_path=catalogo_path)
    write_json(caminhos["cnct_contexto"], contexto)
    return contexto
