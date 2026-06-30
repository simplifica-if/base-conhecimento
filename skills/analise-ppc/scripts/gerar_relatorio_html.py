from __future__ import annotations

import re
import shutil
import textwrap
import unicodedata
from collections import Counter
from dataclasses import dataclass
from html.parser import HTMLParser
from html import escape
from pathlib import Path
from typing import Any

from common import APP_DIR, FICHAS_DIR, VALIDACOES_CRUZADAS_DIR, load_fichas, read_json, round_paths

ESTADOS_PERMITIDOS = {"ATENDE", "NAO_ATENDE", "INCONCLUSIVO", "NAO_APLICAVEL"}
STATUS_FUNDAMENTACAO_NORMATIVA = {
    "CONFIRMADA",
    "CONFIRMADA_COM_RESSALVA",
    "IMPRECISA",
    "SEM_SUPORTE_NA_FONTE",
    "CONTRADITORIA",
    "FONTE_AUSENTE_OU_NAO_CONSULTADA",
    "NAO_NORMATIVA",
}
STATUS_NORMATIVOS_ACIONAVEIS = {
    "CONFIRMADA_COM_RESSALVA",
    "IMPRECISA",
    "SEM_SUPORTE_NA_FONTE",
    "CONTRADITORIA",
    "FONTE_AUSENTE_OU_NAO_CONSULTADA",
}


class ErroResultadosSubagents(ValueError):
    pass


class _HTMLPrettyPrinter(HTMLParser):
    _INLINE_TAGS = {"abbr", "b", "br", "code", "em", "small", "span", "strong"}
    _VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
    _PRESERVE_TAGS = {"script", "style", "textarea", "pre"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.parts: list[str] = []
        self.level = 0
        self.inline_depth = 0
        self.preserve_depth = 0

    def _attrs(self, attrs: list[tuple[str, str | None]]) -> str:
        if not attrs:
            return ""
        rendered = []
        for name, value in attrs:
            if value is None:
                rendered.append(name)
            else:
                rendered.append(f'{name}="{escape(value, quote=True)}"')
        return " " + " ".join(rendered)

    def _newline(self) -> None:
        if self.inline_depth or self.preserve_depth:
            return
        if self.parts and not self.parts[-1].endswith("\n"):
            self.parts.append("\n")
        self.parts.append("  " * self.level)

    def handle_decl(self, decl: str) -> None:
        self.parts.append(f"<!{decl}>\n")

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag_lower = tag.lower()
        if tag_lower not in self._INLINE_TAGS:
            self._newline()
        self.parts.append(f"<{tag}{self._attrs(attrs)}>")
        if tag_lower in self._PRESERVE_TAGS:
            self.preserve_depth += 1
        if tag_lower in self._VOID_TAGS:
            return
        if tag_lower in self._INLINE_TAGS or tag_lower in self._PRESERVE_TAGS:
            self.inline_depth += 1
        elif tag_lower not in self._VOID_TAGS:
            self.level += 1

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._newline()
        self.parts.append(f"<{tag}{self._attrs(attrs)}>")

    def handle_endtag(self, tag: str) -> None:
        tag_lower = tag.lower()
        if tag_lower in self._INLINE_TAGS or tag_lower in self._PRESERVE_TAGS:
            self.parts.append(f"</{tag}>")
            self.inline_depth = max(0, self.inline_depth - 1)
            if tag_lower in self._PRESERVE_TAGS:
                self.preserve_depth = max(0, self.preserve_depth - 1)
            return
        self.level = max(0, self.level - 1)
        self._newline()
        self.parts.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        if self.preserve_depth or self.inline_depth:
            self.parts.append(data)
            return
        texto = data.strip()
        if texto:
            linhas = textwrap.wrap(texto, width=110, break_long_words=False, break_on_hyphens=False)
            if not linhas:
                return
            self.parts.append(linhas[0])
            for linha in linhas[1:]:
                self.parts.append("\n")
                self.parts.append("  " * self.level)
                self.parts.append(linha)

    def handle_entityref(self, name: str) -> None:
        self.parts.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        self.parts.append(f"&#{name};")

    def handle_comment(self, data: str) -> None:
        self._newline()
        self.parts.append(f"<!--{data}-->")

    def pretty(self, html: str) -> str:
        self.feed(html)
        self.close()
        return _quebrar_linhas_longas_fonte("".join(self.parts).strip()) + "\n"


def _quebrar_linhas_longas_fonte(html: str, largura: int = 180) -> str:
    linhas_formatadas: list[str] = []
    for linha in html.splitlines():
        if len(linha) <= largura:
            linhas_formatadas.append(linha)
            continue
        indent = re.match(r"^\s*", linha).group(0)
        partes = re.split(r"(<[^>]+>)", linha.strip())
        atual = indent
        for parte in partes:
            if not parte:
                continue
            if parte.startswith("<") and parte.endswith(">"):
                if atual.strip() and len(atual) + len(parte) > largura:
                    linhas_formatadas.append(atual.rstrip())
                    atual = indent + parte
                else:
                    atual += parte
                continue
            for trecho in textwrap.wrap(parte.strip(), width=max(40, largura - len(indent)), break_long_words=False, break_on_hyphens=False):
                if not trecho:
                    continue
                if atual.strip() and len(atual) + len(trecho) + 1 > largura:
                    linhas_formatadas.append(atual.rstrip())
                    atual = indent + trecho
                else:
                    if atual.strip() and not atual.endswith((">", " ")):
                        atual += " "
                    atual += trecho
        if atual.strip():
            linhas_formatadas.append(atual.rstrip())
    return "\n".join(linhas_formatadas)


@dataclass(frozen=True)
class PPCBlock:
    id: str
    kind: str
    text: str
    html: str
    level: int = 0


def _resolver_resultados_path(rodada_dir: Path, resultados_path: Path) -> Path:
    if resultados_path.is_absolute():
        return resultados_path
    caminhos = round_paths(rodada_dir)
    candidato_suporte = caminhos["suporte_dir"] / resultados_path
    if candidato_suporte.exists():
        return candidato_suporte
    return rodada_dir / resultados_path


def _catalogo_fichas(fichas_dir: Path | None = None) -> dict[str, dict[str, Any]]:
    fichas = sorted(load_fichas(fichas_dir or FICHAS_DIR), key=lambda ficha: str(ficha.get("id", "")))
    return {str(ficha["id"]): ficha for ficha in fichas}


def _catalogo_validacoes(validacoes_dir: Path | None = None) -> dict[str, dict[str, Any]]:
    diretorio = validacoes_dir or VALIDACOES_CRUZADAS_DIR
    validacoes = []
    for caminho in sorted(diretorio.glob("*.json")):
        payload = read_json(caminho)
        if isinstance(payload, dict):
            validacoes.append(payload)
    return {str(item["id"]): item for item in validacoes}


def _blocos_resultados(payload: dict[str, Any]) -> list[dict[str, Any]]:
    grupos = payload.get("grupos")
    if isinstance(grupos, list):
        return grupos
    resultados = payload.get("resultados")
    if isinstance(resultados, list):
        return [{"grupo_id": str(payload.get("grupo_id") or "grupo-unico"), "resultados": resultados}]
    raise ErroResultadosSubagents("O JSON precisa conter `grupos[]` ou `resultados[]`.")


def _normalizar_fundamentacao_normativa(ficha_id: str, item: dict[str, Any]) -> list[dict[str, str]]:
    bruto = item.get("fundamentacao_normativa")
    if bruto is None:
        return []
    if not isinstance(bruto, list):
        raise ErroResultadosSubagents(f"`fundamentacao_normativa` precisa ser lista para {ficha_id}.")
    normalizados: list[dict[str, str]] = []
    for indice, achado in enumerate(bruto, start=1):
        if not isinstance(achado, dict):
            raise ErroResultadosSubagents(f"Achado normativo {indice} de {ficha_id} precisa ser objeto JSON.")
        status = str(achado.get("status") or "").strip()
        if status not in STATUS_FUNDAMENTACAO_NORMATIVA:
            raise ErroResultadosSubagents(f"Status de fundamentação normativa inválido para {ficha_id}: {status}")
        normalizado = {
            "status": status,
            "trecho_ppc": str(achado.get("trecho_ppc") or achado.get("trecho") or "").strip(),
            "norma": str(achado.get("norma") or "").strip(),
            "fonte": str(achado.get("fonte") or achado.get("fonte_consultada") or "").strip(),
            "dispositivo": str(achado.get("dispositivo") or "").strip(),
            "evidencia": str(achado.get("evidencia") or achado.get("evidência") or "").strip(),
            "analise": str(achado.get("analise") or achado.get("análise") or "").strip(),
            "recomendacao": str(achado.get("recomendacao") or achado.get("recomendação") or "").strip(),
        }
        if not any(valor for chave, valor in normalizado.items() if chave != "status"):
            raise ErroResultadosSubagents(f"Achado normativo {indice} de {ficha_id} não traz conteúdo verificável.")
        normalizados.append(normalizado)
    return normalizados


def _normalizar_anchor(valor: Any) -> dict[str, str]:
    if not isinstance(valor, dict):
        return {}
    block_id = str(valor.get("block_id") or valor.get("id") or "").strip()
    quote = str(valor.get("quote") or valor.get("trecho") or "").strip()
    if not block_id and not quote:
        return {}
    return {"block_id": block_id, "quote": quote}


def _normalizar_evidencia(ficha_id: str, valor: Any, indice: int) -> dict[str, Any]:
    if isinstance(valor, dict):
        normalizada: dict[str, Any] = {
            "trecho": str(valor.get("trecho") or valor.get("texto") or valor.get("evidencia") or "").strip(),
            "secao": str(valor.get("secao") or valor.get("seção") or "").strip(),
            "localizador": str(valor.get("localizador") or valor.get("pagina") or valor.get("linha") or "").strip(),
            "fonte": str(valor.get("fonte") or "PPC.md").strip(),
            "artefato": str(valor.get("artefato") or "").strip(),
        }
        anchor = _normalizar_anchor(valor.get("anchor"))
        if anchor:
            normalizada["anchor"] = anchor
    else:
        normalizada = {
            "trecho": str(valor or "").strip(),
            "secao": "",
            "localizador": "",
            "fonte": "PPC.md",
            "artefato": "",
        }
    tem_conteudo = any(
        normalizada.get(chave)
        for chave in ("trecho", "secao", "localizador", "artefato", "anchor")
    ) or normalizada.get("fonte") not in {"", "PPC.md"}
    if not tem_conteudo:
        raise ErroResultadosSubagents(f"Evidência {indice} de {ficha_id} não traz conteúdo verificável.")
    return normalizada


def _normalizar_evidencias(ficha_id: str, evidencias: Any) -> list[dict[str, Any]]:
    if not isinstance(evidencias, list):
        raise ErroResultadosSubagents(f"`evidencias` precisa ser lista para {ficha_id}.")
    return [
        normalizada
        for indice, valor in enumerate(evidencias, start=1)
        if any((normalizada := _normalizar_evidencia(ficha_id, valor, indice)).values())
    ]


def _normalizar_evidencia_transversal(alerta_id: str, valor: Any, indice: int) -> dict[str, Any]:
    if isinstance(valor, dict):
        normalizada: dict[str, Any] = {
            "trecho": str(valor.get("trecho") or valor.get("texto") or valor.get("evidencia") or "").strip(),
            "secao": str(valor.get("secao") or valor.get("seção") or "").strip(),
            "localizador": str(valor.get("localizador") or valor.get("pagina") or valor.get("linha") or "").strip(),
            "papel": str(valor.get("papel") or "").strip(),
            "fonte": str(valor.get("fonte") or "PPC.md").strip(),
        }
        anchor = _normalizar_anchor(valor.get("anchor"))
        if anchor:
            normalizada["anchor"] = anchor
    else:
        normalizada = {
            "trecho": str(valor or "").strip(),
            "secao": "",
            "localizador": "",
            "papel": "",
            "fonte": "PPC.md",
        }
    if not any(normalizada.get(chave) for chave in ("trecho", "secao", "localizador", "papel", "anchor")):
        raise ErroResultadosSubagents(f"Evidência transversal {indice} de {alerta_id} não traz conteúdo verificável.")
    return normalizada


def _normalizar_evidencias_transversais(alerta_id: str, evidencias: Any) -> list[dict[str, Any]]:
    if not isinstance(evidencias, list):
        raise ErroResultadosSubagents(f"`evidencias` precisa ser lista para {alerta_id}.")
    return [
        _normalizar_evidencia_transversal(alerta_id, valor, indice)
        for indice, valor in enumerate(evidencias, start=1)
    ]


def validar_resultados_subagents(
    payload: dict[str, Any],
    fichas_por_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    vistos: set[str] = set()
    normalizados: list[dict[str, Any]] = []
    duplicados: list[str] = []
    desconhecidos: list[str] = []

    for bloco in _blocos_resultados(payload):
        grupo_id = str(bloco.get("grupo_id") or "").strip()
        resultados = bloco.get("resultados")
        if not grupo_id:
            raise ErroResultadosSubagents("Um bloco de resultados não contém `grupo_id`.")
        if not isinstance(resultados, list):
            raise ErroResultadosSubagents(f"O bloco {grupo_id} não contém `resultados[]`.")
        for item in resultados:
            if not isinstance(item, dict):
                raise ErroResultadosSubagents(f"O bloco {grupo_id} contém item que não é objeto JSON.")
            ficha_id = str(item.get("ficha_id") or "").strip()
            if not ficha_id:
                raise ErroResultadosSubagents(f"O bloco {grupo_id} contém item sem `ficha_id`.")
            if ficha_id in vistos:
                duplicados.append(ficha_id)
                continue
            vistos.add(ficha_id)
            if ficha_id not in fichas_por_id:
                desconhecidos.append(ficha_id)
                continue
            ficha = fichas_por_id[ficha_id]
            estado = str(item.get("estado") or "").strip()
            if estado not in ESTADOS_PERMITIDOS:
                raise ErroResultadosSubagents(f"Estado inválido para {ficha_id}: {estado}")
            confianca = item.get("confianca")
            if not isinstance(confianca, (int, float)) or not (0 <= float(confianca) <= 1):
                raise ErroResultadosSubagents(f"Confiança inválida para {ficha_id}: {confianca}")
            justificativa = str(item.get("justificativa") or "").strip()
            if not justificativa:
                raise ErroResultadosSubagents(f"`justificativa` ausente para {ficha_id}.")
            feedback_autores = str(item.get("feedback_autores") or "").strip()
            feedback_config = ficha.get("feedback_autores")
            if isinstance(feedback_config, dict):
                estados_com_feedback = {
                    str(valor)
                    for valor in feedback_config.get("obrigatorio_quando_estado", [])
                }
                if estado in estados_com_feedback and not feedback_autores:
                    raise ErroResultadosSubagents(
                        f"`feedback_autores` ausente para {ficha_id}; obrigatório quando estado={estado}."
                    )
            evidencias_normalizadas = _normalizar_evidencias(ficha_id, item.get("evidencias"))
            evidencia_minima = int(fichas_por_id[ficha_id].get("evidencia_minima", 1))
            if len(evidencias_normalizadas) < evidencia_minima:
                raise ErroResultadosSubagents(
                    f"{ficha_id} trouxe {len(evidencias_normalizadas)} evidências; mínimo exigido: {evidencia_minima}."
                )
            lacunas = item.get("lacunas")
            revisao = item.get("revisao_humana_obrigatoria")
            if not isinstance(lacunas, list):
                raise ErroResultadosSubagents(f"`lacunas` precisa ser lista para {ficha_id}.")
            if not isinstance(revisao, bool):
                raise ErroResultadosSubagents(f"`revisao_humana_obrigatoria` precisa ser booleano para {ficha_id}.")
            normalizados.append(
                {
                    "grupo_id": grupo_id,
                    "ficha_id": ficha_id,
                    "titulo": str(ficha.get("titulo") or ficha_id),
                    "dominio": str(ficha.get("dominio") or ""),
                    "criticidade": str(ficha.get("criticidade") or ""),
                    "secoes_preferenciais": list(ficha.get("secoes_preferenciais") or []),
                    "estado": estado,
                    "confianca": float(confianca),
                    "justificativa": justificativa,
                    "evidencias": evidencias_normalizadas,
                    "lacunas": [str(valor).strip() for valor in lacunas if str(valor).strip()],
                    "revisao_humana_obrigatoria": revisao,
                    "feedback_autores": feedback_autores,
                    "fundamentacao_normativa": _normalizar_fundamentacao_normativa(ficha_id, item),
                }
            )

    if duplicados:
        raise ErroResultadosSubagents("Fichas duplicadas: " + ", ".join(sorted(set(duplicados))))
    if desconhecidos:
        raise ErroResultadosSubagents("Fichas desconhecidas: " + ", ".join(sorted(set(desconhecidos))))
    faltantes = sorted(set(fichas_por_id) - vistos)
    if faltantes:
        raise ErroResultadosSubagents("Fichas sem resultado: " + ", ".join(faltantes))
    return sorted(normalizados, key=lambda item: item["ficha_id"])


def validar_alertas_transversais(
    payload: dict[str, Any],
    fichas_por_id: dict[str, dict[str, Any]],
    validacoes_por_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    bruto = payload.get("alertas_transversais")
    if bruto is None and isinstance(payload.get("sintese_transversal"), dict):
        bruto = payload["sintese_transversal"].get("alertas_transversais")
    if bruto is None:
        return []
    if not isinstance(bruto, list):
        raise ErroResultadosSubagents("`alertas_transversais` precisa ser uma lista.")
    alertas: list[dict[str, Any]] = []
    vistos: set[str] = set()
    for indice, item in enumerate(bruto, start=1):
        if not isinstance(item, dict):
            raise ErroResultadosSubagents("Cada alerta transversal precisa ser objeto JSON.")
        alerta_id = str(item.get("id") or f"ALERTA-{indice:03d}").strip()
        if alerta_id in vistos:
            raise ErroResultadosSubagents(f"Alerta transversal duplicado: {alerta_id}")
        vistos.add(alerta_id)
        titulo = str(item.get("titulo") or "").strip()
        validacao_id = str(item.get("validacao_id") or "").strip()
        descricao = str(item.get("descricao") or "").strip()
        criticidade = str(item.get("criticidade") or "OBRIG").strip()
        fichas_relacionadas = item.get("fichas_relacionadas") or []
        evidencias = item.get("evidencias") or []
        revisao = item.get("revisao_humana_obrigatoria")
        if not titulo or not descricao:
            raise ErroResultadosSubagents(f"Alerta transversal {alerta_id} precisa de título e descrição.")
        if not validacao_id:
            raise ErroResultadosSubagents(f"Alerta transversal {alerta_id} precisa de `validacao_id`.")
        if validacao_id not in validacoes_por_id:
            raise ErroResultadosSubagents(f"Alerta {alerta_id} referencia validação cruzada desconhecida: {validacao_id}")
        if criticidade not in {"BLOQ", "OBRIG", "REC"}:
            raise ErroResultadosSubagents(f"Criticidade inválida para {alerta_id}: {criticidade}")
        if not isinstance(fichas_relacionadas, list):
            raise ErroResultadosSubagents(f"`fichas_relacionadas` precisa ser lista para {alerta_id}.")
        desconhecidas = [ficha_id for ficha_id in fichas_relacionadas if str(ficha_id) not in fichas_por_id]
        if desconhecidas:
            raise ErroResultadosSubagents(
                f"Alerta {alerta_id} referencia fichas desconhecidas: " + ", ".join(map(str, desconhecidas))
            )
        evidencias_normalizadas = _normalizar_evidencias_transversais(alerta_id, evidencias)
        if not isinstance(revisao, bool):
            raise ErroResultadosSubagents(f"`revisao_humana_obrigatoria` precisa ser booleano para {alerta_id}.")
        alertas.append(
            {
                "id": alerta_id,
                "validacao_id": validacao_id,
                "validacao_titulo": str(validacoes_por_id[validacao_id].get("titulo") or validacao_id),
                "titulo": titulo,
                "criticidade": criticidade,
                "descricao": descricao,
                "fichas_relacionadas": [str(ficha_id) for ficha_id in fichas_relacionadas],
                "evidencias": evidencias_normalizadas,
                "revisao_humana_obrigatoria": revisao,
            }
        )
    return alertas


def _situacao(resultados: list[dict[str, Any]]) -> str:
    bloqueantes = [item for item in resultados if item["criticidade"] == "BLOQ" and item["estado"] == "NAO_ATENDE"]
    obrigatorios = [item for item in resultados if item["criticidade"] == "OBRIG" and item["estado"] == "NAO_ATENDE"]
    inconclusivos = [item for item in resultados if item["estado"] == "INCONCLUSIVO"]
    revisoes = [item for item in resultados if item["revisao_humana_obrigatoria"]]
    if bloqueantes:
        return "NAO_APROVADO"
    if obrigatorios:
        return "DILIGENCIA"
    if inconclusivos or revisoes:
        return "COM_RESSALVAS"
    return "APROVADO"


def validar_resultados_rodada(rodada_dir: Path, resultados_path: Path) -> dict[str, Any]:
    caminhos = round_paths(rodada_dir)
    caminho_resultados = _resolver_resultados_path(caminhos["rodada_dir"], resultados_path)
    payload = read_json(caminho_resultados)
    fichas_por_id = _catalogo_fichas()
    validacoes_por_id = _catalogo_validacoes()
    resultados = validar_resultados_subagents(payload, fichas_por_id)
    alertas = validar_alertas_transversais(payload, fichas_por_id, validacoes_por_id)
    contagem_estado = Counter(item["estado"] for item in resultados)
    contagem_criticidade = Counter(item["criticidade"] for item in resultados)
    grupos = _blocos_resultados(payload)
    return {
        "resultados_path": str(caminho_resultados),
        "valido": True,
        "total_fichas": len(resultados),
        "total_fichas_esperadas": len(fichas_por_id),
        "total_grupos": len(grupos),
        "total_alertas_transversais": len(alertas),
        "situacao": _situacao(resultados),
        "contagem_estado": dict(sorted(contagem_estado.items())),
        "contagem_criticidade": dict(sorted(contagem_criticidade.items())),
        "grupos": [
            {
                "grupo_id": str(grupo.get("grupo_id") or ""),
                "total_resultados": len(grupo.get("resultados") or []),
            }
            for grupo in grupos
        ],
    }


def _normalizar_texto(texto: str) -> str:
    normalizado = unicodedata.normalize("NFD", texto or "")
    normalizado = "".join(char for char in normalizado if unicodedata.category(char) != "Mn")
    normalizado = normalizado.casefold()
    normalizado = re.sub(r"[^a-z0-9]+", " ", normalizado)
    return " ".join(normalizado.split())


def _css_slug(valor: str) -> str:
    return valor.lower().replace("_", "-")


def _classe_estado(valor: str) -> str:
    return "transversal" if valor == "TRANSVERSAL" else _css_slug(valor)


def _inline_markdown(texto: str) -> str:
    marcador_br = "\u0000BR\u0000"
    texto = re.sub(r"<br\s*/?>", marcador_br, texto, flags=re.IGNORECASE)
    html = escape(texto).replace(marcador_br, "<br>")
    html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)
    html = re.sub(r"\*(.+?)\*", r"<em>\1</em>", html)
    return html


def _render_markdown_table(linhas: list[str]) -> str:
    rows = []
    for linha in linhas:
        cells = [cell.strip() for cell in linha.strip().strip("|").split("|")]
        if cells and all(re.fullmatch(r":?-{3,}:?", cell or "") for cell in cells):
            continue
        rows.append(cells)
    if not rows:
        return ""
    largura = max(len(row) for row in rows)
    rows = [row + [""] * (largura - len(row)) for row in rows]
    header, *body = rows
    thead = "".join(f"<th scope=\"col\">{_inline_markdown(cell)}</th>" for cell in header)
    tbody = "".join(
        "<tr>" + "".join(f"<td>{_inline_markdown(cell)}</td>" for cell in row) + "</tr>"
        for row in body
    )
    return f"<table><thead><tr>{thead}</tr></thead><tbody>{tbody}</tbody></table>"


def _render_block_html(kind: str, text: str, level: int = 0) -> str:
    if kind == "heading":
        nivel = min(max(level, 1), 6)
        return f"<h{nivel}>{_inline_markdown(text)}</h{nivel}>"
    if kind == "table":
        return _render_markdown_table(text.splitlines())
    if kind == "list":
        itens = []
        for linha in text.splitlines():
            item = re.sub(r"^\s*(?:[-*+]|\d+[.)])\s+", "", linha).strip()
            if item:
                itens.append(f"<li>{_inline_markdown(item)}</li>")
        return f"<ul>{''.join(itens)}</ul>"
    paragrafos = [parte.strip() for parte in text.split("\n") if parte.strip()]
    return "".join(f"<p>{_inline_markdown(paragrafo)}</p>" for paragrafo in paragrafos)


def gerar_blocos_ppc(markdown: str) -> list[PPCBlock]:
    linhas = markdown.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    blocos: list[PPCBlock] = []
    indice = 0
    atual: list[str] = []
    kind_atual = "paragraph"

    def tipo_linha(linha: str) -> tuple[str, int]:
        stripped = linha.strip()
        if not stripped:
            return ("blank", 0)
        heading = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if heading:
            return ("heading", len(heading.group(1)))
        if "|" in stripped and stripped.startswith("|"):
            return ("table", 0)
        if re.match(r"^\s*(?:[-*+]|\d+[.)])\s+", linha):
            return ("list", 0)
        return ("paragraph", 0)

    def flush(level: int = 0) -> None:
        nonlocal atual, kind_atual, indice
        texto = "\n".join(linha.rstrip() for linha in atual).strip()
        if not texto:
            atual = []
            return
        indice += 1
        if kind_atual == "heading":
            texto = re.sub(r"^#{1,6}\s+", "", texto).strip()
        bloco_id = f"ppc-b{indice:05d}"
        blocos.append(PPCBlock(bloco_id, kind_atual, texto, _render_block_html(kind_atual, texto, level), level))
        atual = []

    level_atual = 0
    for linha in linhas:
        kind, level = tipo_linha(linha)
        if kind == "blank":
            flush(level_atual)
            level_atual = 0
            kind_atual = "paragraph"
            continue
        if not atual:
            atual = [linha]
            kind_atual = kind
            level_atual = level
            continue
        if kind != kind_atual or kind == "heading":
            flush(level_atual)
            atual = [linha]
            kind_atual = kind
            level_atual = level
        else:
            atual.append(linha)
    flush(level_atual)
    return blocos


def _evidencia_texto(evidencia: dict[str, Any]) -> str:
    partes: list[str] = []
    for chave, valor in evidencia.items():
        if chave == "anchor" and isinstance(valor, dict):
            partes.extend(str(item) for item in valor.values() if item)
        elif valor:
            partes.append(str(valor))
    return " ".join(partes)


def _titulo_sem_numero(texto: str) -> str:
    return re.sub(r"^\s*\d+(?:\.\d+)*\s+", "", texto or "").strip()


def _bloco_secao_por_titulo(secao: str, blocos: list[PPCBlock]) -> PPCBlock | None:
    secao_normalizada = _normalizar_texto(_titulo_sem_numero(secao))
    if not secao_normalizada:
        return None
    for bloco in blocos:
        if bloco.kind != "heading":
            continue
        titulo_normalizado = _normalizar_texto(_titulo_sem_numero(bloco.text))
        if secao_normalizada == titulo_normalizado or secao_normalizada in titulo_normalizado:
            return bloco
    return None


def _blocos_da_secao(heading: PPCBlock, blocos: list[PPCBlock]) -> list[PPCBlock]:
    try:
        indice = blocos.index(heading)
    except ValueError:
        return []
    relacionados = [heading]
    for bloco in blocos[indice + 1 :]:
        if bloco.kind == "heading" and bloco.level <= heading.level:
            break
        relacionados.append(bloco)
    return relacionados


def _resolver_anchor_evidencia(evidencia: dict[str, Any], blocos: list[PPCBlock]) -> tuple[str, str]:
    por_id = {bloco.id: bloco for bloco in blocos}
    anchor = evidencia.get("anchor") if isinstance(evidencia.get("anchor"), dict) else {}
    block_id = str(anchor.get("block_id") or "").strip() if isinstance(anchor, dict) else ""
    quote = str(anchor.get("quote") or "").strip() if isinstance(anchor, dict) else ""
    if block_id in por_id:
        return block_id, quote or str(evidencia.get("trecho") or "")

    secao = str(evidencia.get("secao") or "")
    bloco_secao = _bloco_secao_por_titulo(secao, blocos)
    if bloco_secao:
        trecho_normalizado = _normalizar_texto(str(evidencia.get("trecho") or quote))
        if trecho_normalizado:
            for bloco in _blocos_da_secao(bloco_secao, blocos):
                if trecho_normalizado in _normalizar_texto(bloco.text):
                    return bloco.id, quote or str(evidencia.get("trecho") or "")
        return bloco_secao.id, quote or str(evidencia.get("trecho") or bloco_secao.text)

    candidatos = [
        quote,
        str(evidencia.get("trecho") or ""),
        str(evidencia.get("localizador") or ""),
        secao,
    ]
    for candidato in candidatos:
        normalizado = _normalizar_texto(candidato)
        if not normalizado:
            continue
        for bloco in blocos:
            if normalizado in _normalizar_texto(bloco.text):
                return bloco.id, quote or str(evidencia.get("trecho") or candidato)
    return "", quote or str(evidencia.get("trecho") or "")


def _item_acionavel(item: dict[str, Any]) -> bool:
    if item["estado"] in {"NAO_ATENDE", "INCONCLUSIVO"}:
        return True
    if item["revisao_humana_obrigatoria"] or item.get("lacunas") or item.get("feedback_autores"):
        return True
    return any(
        achado.get("status") in STATUS_NORMATIVOS_ACIONAVEIS
        for achado in item.get("fundamentacao_normativa", [])
    )


def _posicao_quote_no_bloco(quote: str, bloco: PPCBlock | None) -> int:
    if not quote or not bloco:
        return 0
    posicao = bloco.text.find(quote)
    if posicao >= 0:
        return posicao
    bloco_normalizado = _normalizar_texto(bloco.text)
    quote_normalizado = _normalizar_texto(quote)
    if not quote_normalizado:
        return 0
    posicao_normalizada = bloco_normalizado.find(quote_normalizado)
    return posicao_normalizada if posicao_normalizada >= 0 else 0


def _preparar_anotacoes(resultados: list[dict[str, Any]], blocos: list[PPCBlock]) -> dict[str, Any]:
    por_bloco: dict[str, list[dict[str, Any]]] = {}
    soltas: list[dict[str, Any]] = []
    blocos_por_id = {bloco.id: bloco for bloco in blocos}
    ordem_blocos = {bloco.id: indice for indice, bloco in enumerate(blocos)}
    preparadas: list[dict[str, Any]] = []
    for indice_original, item in enumerate(resultados, start=1):
        anchor_id = ""
        quote = ""
        evidencias_preparadas = []
        for evidencia in item["evidencias"]:
            evidencia_anchor_id, evidencia_quote = _resolver_anchor_evidencia(evidencia, blocos)
            evidencias_preparadas.append(
                {
                    **evidencia,
                    "anchor_id": evidencia_anchor_id,
                    "quote": evidencia_quote,
                }
            )
            if evidencia_anchor_id and not anchor_id:
                anchor_id = evidencia_anchor_id
                quote = evidencia_quote
        bloco = blocos_por_id.get(anchor_id)
        preparadas.append(
            {
                **item,
                "evidencias": evidencias_preparadas,
                "anchor_id": anchor_id,
                "quote": quote,
                "acionavel": _item_acionavel(item),
                "_ordem_bloco": ordem_blocos.get(anchor_id, len(blocos) + indice_original),
                "_ordem_quote": _posicao_quote_no_bloco(quote, bloco),
                "_ordem_original": indice_original,
            }
        )

    preparadas.sort(
        key=lambda item: (
            0 if item["anchor_id"] else 1,
            item["_ordem_bloco"],
            item["_ordem_quote"],
            item["ficha_id"],
            item["_ordem_original"],
        )
    )

    anotacoes: list[dict[str, Any]] = []
    for indice, item in enumerate(preparadas, start=1):
        anotacao = {
            chave: valor
            for chave, valor in item.items()
            if not str(chave).startswith("_ordem_")
        }
        anotacao["annotation_id"] = f"ann-{indice:03d}"
        anotacoes.append(anotacao)
        if anotacao["anchor_id"]:
            por_bloco.setdefault(anotacao["anchor_id"], []).append(anotacao)
        else:
            soltas.append(anotacao)
    return {"anotacoes": anotacoes, "por_bloco": por_bloco, "soltas": soltas}


def _preparar_alertas_transversais(alertas: list[dict[str, Any]], blocos: list[PPCBlock]) -> dict[str, Any]:
    por_bloco: dict[str, list[dict[str, Any]]] = {}
    preparados: list[dict[str, Any]] = []
    for indice_alerta, alerta in enumerate(alertas, start=1):
        ocorrencias = []
        for indice_evidencia, evidencia in enumerate(alerta["evidencias"], start=1):
            anchor_id, quote = _resolver_anchor_evidencia(evidencia, blocos)
            ocorrencia = {
                **evidencia,
                "occurrence_id": f"trans-{indice_alerta:03d}-{indice_evidencia:02d}",
                "anchor_id": anchor_id,
                "quote": quote,
            }
            ocorrencias.append(ocorrencia)
            if anchor_id:
                por_bloco.setdefault(anchor_id, []).append(
                    {
                        **alerta,
                        "annotation_id": alerta["id"],
                        "ficha_id": alerta["id"],
                        "estado": "TRANSVERSAL",
                        "occurrence_id": ocorrencia["occurrence_id"],
                        "anchor_id": anchor_id,
                        "quote": quote,
                    }
                )
        preparados.append({**alerta, "annotation_id": alerta["id"], "ocorrencias": ocorrencias})
    return {"alertas": preparados, "por_bloco": por_bloco}


def _render_lista(valores: list[str]) -> str:
    if not valores:
        return "<span class=\"muted\">Não informado</span>"
    itens = "".join(f"<li>{escape(valor)}</li>" for valor in valores)
    return f"<ul>{itens}</ul>"


def _rotulo_link_evidencia(evidencia: dict[str, Any]) -> str:
    if str(evidencia.get("secao") or "").strip():
        return "Ir para seção"
    if str(evidencia.get("quote") or evidencia.get("trecho") or "").strip():
        return "Ir para trecho"
    return "Ir para ponto no PPC"


def _render_link_evidencia(evidencia: dict[str, Any]) -> str:
    anchor_id = str(evidencia.get("anchor_id") or "").strip()
    if not anchor_id:
        return ""
    return (
        f"<a class=\"backlink evidence-jump\" href=\"#{escape(anchor_id)}\">"
        f"{escape(_rotulo_link_evidencia(evidencia))}</a>"
    )


def _render_evidencias(evidencias: list[dict[str, Any]]) -> str:
    if not evidencias:
        return "<span class=\"muted\">Não informado</span>"
    itens = []
    for evidencia in evidencias:
        detalhes = []
        if evidencia.get("secao"):
            detalhes.append(f"<span><strong>Seção:</strong> {escape(str(evidencia['secao']))}</span>")
        detalhes_html = f"<div class=\"evidence-meta\">{' · '.join(detalhes)}</div>" if detalhes else ""
        itens.append(
            "<li>"
            f"<p>{escape(str(evidencia.get('trecho') or ''))}</p>"
            f"{detalhes_html}"
            f"{_render_link_evidencia(evidencia)}"
            "</li>"
        )
    return f"<ul class=\"evidence-list\">{''.join(itens)}</ul>"


def _render_feedback_autores(texto: str) -> str:
    if not texto:
        return ""
    paragrafos = [
        f"<p>{escape(paragrafo)}</p>"
        for paragrafo in texto.split("\n\n")
        if paragrafo.strip()
    ]
    return (
        "<section class=\"author-feedback\">"
        "<h4>Feedback sugerido aos autores</h4>"
        f"{''.join(paragrafos)}"
        "</section>"
    )


def _render_fundamentacao_normativa(achados: list[dict[str, str]]) -> str:
    if not achados:
        return ""
    cards = []
    status_classes = [
        "normative-section",
        *[
            f"normative-{_css_slug(achado['status'])}"
            for achado in achados
            if achado.get("status")
        ],
    ]
    for achado in achados:
        detalhes = [
            ("Trecho do PPC", achado["trecho_ppc"]),
            ("Norma", achado["norma"]),
            ("Fonte consultada", achado["fonte"]),
            ("Dispositivo", achado["dispositivo"]),
            ("Evidência", achado["evidencia"]),
            ("Análise", achado["analise"]),
            ("Recomendação", achado["recomendacao"]),
        ]
        itens = "".join(
            f"<p><strong>{escape(rotulo)}:</strong> {escape(valor)}</p>"
            for rotulo, valor in detalhes
            if valor
        )
        cards.append(
            "<article class=\"normative-finding\">"
            f"<h5><span class=\"badge norma-{escape(_css_slug(achado['status']))}\">{escape(achado['status'])}</span></h5>"
            f"{itens}"
            "</article>"
        )
    return (
        f"<section class=\"{escape(' '.join(status_classes))}\">"
        "<h4>Fundamentação normativa verificada</h4>"
        f"{''.join(cards)}"
        "</section>"
    )


def _rotulo_ocorrencia(ocorrencia: dict[str, Any], indice: int) -> str:
    for chave in ("secao", "localizador", "papel"):
        if ocorrencia.get(chave):
            return str(ocorrencia[chave])
    return f"Ponto {indice}"


def _render_pontos_transversais(ocorrencias: list[dict[str, Any]]) -> str:
    if not ocorrencias:
        return "<p class=\"muted\">Nenhum ponto específico informado.</p>"
    itens = []
    for indice, ocorrencia in enumerate(ocorrencias, start=1):
        rotulo = _rotulo_ocorrencia(ocorrencia, indice)
        trecho = str(ocorrencia.get("trecho") or ocorrencia.get("quote") or "").strip()
        papel = str(ocorrencia.get("papel") or "").strip()
        destino = str(ocorrencia.get("anchor_id") or "").strip()
        botao = (
            f"<a class=\"backlink alert-point-link\" href=\"#{escape(destino)}\">{escape(rotulo)}</a>"
            if destino
            else f"<span class=\"alert-point-label\">{escape(rotulo)}</span>"
        )
        detalhes = f"<p>{escape(trecho)}</p>" if trecho else ""
        papel_html = f"<p class=\"annotation-meta\"><strong>Papel:</strong> {escape(papel)}</p>" if papel else ""
        itens.append(f"<li>{botao}{detalhes}{papel_html}</li>")
    return f"<ol class=\"alert-points\">{''.join(itens)}</ol>"


def _render_alertas(alertas: list[dict[str, Any]]) -> str:
    if not alertas:
        return "<p class=\"muted\">Nenhum alerta transversal registrado.</p>"
    cards = []
    for alerta in alertas:
        fichas = ", ".join(alerta["fichas_relacionadas"]) or "Sem fichas específicas"
        cards.append(
            f"<article class=\"alert-card\" id=\"{escape(alerta['id'])}\">"
            f"<div class=\"finding-heading\"><h3>{escape(alerta['id'])} · {escape(alerta['titulo'])}</h3>"
            f"<span class=\"badge criticidade-{escape(alerta['criticidade'].lower())}\">{escape(alerta['criticidade'])}</span></div>"
            f"<p><strong>Validação cruzada:</strong> {escape(alerta['validacao_id'])} · {escape(alerta['validacao_titulo'])}</p>"
            f"<p>{escape(alerta['descricao'])}</p>"
            f"<p><strong>Fichas relacionadas:</strong> {escape(fichas)}</p>"
            f"<section><h4>Pontos no PPC</h4>{_render_pontos_transversais(alerta.get('ocorrencias') or alerta['evidencias'])}</section>"
            f"<p><strong>Revisão humana obrigatória:</strong> {'Sim' if alerta['revisao_humana_obrigatoria'] else 'Não'}</p>"
            "</article>"
        )
    return "".join(cards)


def _render_marcadores(anotacoes: list[dict[str, Any]]) -> str:
    if not anotacoes:
        return ""
    links = []
    for anotacao in anotacoes:
        estado = str(anotacao.get("estado") or "")
        classe_estado = _classe_estado(estado)
        rotulo = str(anotacao.get("ficha_id") or anotacao.get("id") or "")
        links.append(
            f"<a class=\"annotation-marker estado-{escape(classe_estado)}\" "
            f"href=\"#{escape(anotacao['annotation_id'])}\" "
            f"data-annotation-ref=\"{escape(anotacao['annotation_id'])}\" "
            f"aria-label=\"Anotação {escape(rotulo)}\">{escape(rotulo)}</a>"
        )
    return f"<div class=\"annotation-markers\" aria-label=\"Anotações do bloco\">\n{chr(10).join(links)}\n</div>"


def _aplicar_destaques(html: str, anotacoes: list[dict[str, Any]]) -> str:
    renderizado = html
    for anotacao in anotacoes:
        quote = str(anotacao.get("quote") or "")
        texto = quote.strip()
        if not texto:
            continue
        alvo = escape(texto)
        if alvo in renderizado:
            annotation_id = escape(str(anotacao.get("annotation_id") or ""))
            ficha_id = escape(str(anotacao.get("ficha_id") or annotation_id))
            titulo = escape(str(anotacao.get("titulo") or ficha_id), quote=True)
            estado = str(anotacao.get("estado") or "")
            classe_estado = _classe_estado(estado)
            renderizado = renderizado.replace(
                alvo,
                (
                    f"<a class=\"evidence-link evidence-state-{escape(classe_estado)}\" href=\"#{annotation_id}\" "
                    f"data-evidence-ref=\"{annotation_id}\" "
                    f"title=\"Evidência de {ficha_id}: {titulo}\" "
                    f"aria-label=\"Trecho usado como evidência de {ficha_id}\">"
                    f"<mark class=\"evidence-highlight\">{alvo}</mark>"
                    f"<span class=\"evidence-ref\" aria-hidden=\"true\">{ficha_id}</span>"
                    "</a>"
                ),
                1,
            )
    return renderizado


def _render_ppc(blocos: list[PPCBlock], anotacoes_por_bloco: dict[str, list[dict[str, Any]]]) -> str:
    rendered = []
    for bloco in blocos:
        anotacoes = anotacoes_por_bloco.get(bloco.id, [])
        bloco_html = _aplicar_destaques(bloco.html, anotacoes)
        rendered.append(
            f"<section id=\"{escape(bloco.id)}\" class=\"ppc-block ppc-block-{escape(bloco.kind)}\" "
            f"data-block-id=\"{escape(bloco.id)}\" data-annotations=\"{len(anotacoes)}\">"
            f"<div class=\"block-content\">{bloco_html}</div>"
            f"{_render_marcadores(anotacoes)}"
            "</section>"
        )
    return "".join(rendered)


def _render_anotacao(item: dict[str, Any], compacta: bool = True) -> str:
    quote = str(item.get("quote") or "").strip()
    quote_html = f"<blockquote>{escape(quote)}</blockquote>" if quote else ""
    lacunas = f"<section><h4>Lacunas</h4>{_render_lista(item['lacunas'])}</section>" if item.get("lacunas") else ""
    evidencia = ""
    if not compacta:
        evidencia = f"<section><h4>Evidências</h4>{_render_evidencias(item['evidencias'])}</section>"
    return (
        "<article class=\"annotation-card finding\" "
        f"id=\"{escape(item['annotation_id'])}\" "
        f"data-estado=\"{escape(item['estado'])}\" "
        f"data-criticidade=\"{escape(item['criticidade'])}\" "
        f"data-revisao=\"{'sim' if item['revisao_humana_obrigatoria'] else 'nao'}\" "
        f"data-acionavel=\"{'sim' if item['acionavel'] else 'nao'}\">"
        "<header>"
        f"<p class=\"annotation-kicker\">{escape(item['ficha_id'])} · {escape(item['criticidade'])}</p>"
        f"<h3>{escape(item['titulo'])}</h3>"
        f"<span class=\"badge estado-{escape(_css_slug(item['estado']))}\">{escape(item['estado'])}</span>"
        "</header>"
        f"{quote_html}"
        f"<p>{escape(item['justificativa'])}</p>"
        f"{lacunas}"
        f"{evidencia}"
        f"{_render_feedback_autores(str(item.get('feedback_autores') or '')) if not compacta else ''}"
        f"{_render_fundamentacao_normativa(item.get('fundamentacao_normativa') or []) if not compacta else ''}"
        f"<p class=\"annotation-meta\"><strong>Confiança:</strong> {item['confianca']:.2f} · "
        f"<strong>Grupo:</strong> {escape(item['grupo_id'])} · "
        f"<strong>Revisão humana:</strong> {'Sim' if item['revisao_humana_obrigatoria'] else 'Não'}</p>"
        "</article>"
    )


def _render_anotacoes_laterais(
    anotacoes: list[dict[str, Any]],
    soltas: list[dict[str, Any]],
    alertas: list[dict[str, Any]],
) -> str:
    cards = "".join(_render_anotacao(item, compacta=False) for item in anotacoes if item.get("anchor_id"))
    if soltas:
        cards += (
            "<section class=\"unanchored-notes\">"
            "<h3>Anotações sem âncora precisa</h3>"
            + "".join(_render_anotacao(item, compacta=False) for item in soltas)
            + "</section>"
        )
    if alertas:
        cards += (
            "<section class=\"transversal-notes\">"
            "<h3>Alertas transversais</h3>"
            f"{_render_alertas(alertas)}"
            "</section>"
        )
    return cards


def _render_html(
    metadata: dict[str, Any],
    resultados: list[dict[str, Any]],
    alertas: list[dict[str, Any]],
    ppc_markdown: str,
) -> str:
    blocos = gerar_blocos_ppc(ppc_markdown)
    contexto_anotacoes = _preparar_anotacoes(resultados, blocos)
    contexto_alertas = _preparar_alertas_transversais(alertas, blocos)
    anotacoes = contexto_anotacoes["anotacoes"]
    anotacoes_por_bloco = contexto_anotacoes["por_bloco"]
    for block_id, alertas_do_bloco in contexto_alertas["por_bloco"].items():
        anotacoes_por_bloco.setdefault(block_id, []).extend(alertas_do_bloco)
    alertas_renderizados = contexto_alertas["alertas"]
    soltas = contexto_anotacoes["soltas"]

    contagem_estado = Counter(item["estado"] for item in resultados)
    contagem_criticidade = Counter(item["criticidade"] for item in resultados)
    situacao = _situacao(resultados)
    revisao_humana = sum(1 for item in resultados if item["revisao_humana_obrigatoria"])
    feedbacks_autores = sum(1 for item in resultados if item.get("feedback_autores"))
    fundamentacoes_normativas = sum(len(item.get("fundamentacao_normativa") or []) for item in resultados)
    nao_atende = sum(1 for item in resultados if item["estado"] == "NAO_ATENDE")
    inconclusivos = sum(1 for item in resultados if item["estado"] == "INCONCLUSIVO")
    acionaveis = sum(1 for item in anotacoes if item["acionavel"])

    estados_html = "".join(
        f"<tr><th scope=\"row\">{escape(estado)}</th><td>{quantidade}</td></tr>"
        for estado, quantidade in sorted(contagem_estado.items())
    )
    criticidade_html = "".join(
        f"<tr><th scope=\"row\">{escape(criticidade)}</th><td>{quantidade}</td></tr>"
        for criticidade, quantidade in sorted(contagem_criticidade.items())
    )
    resumo = (
        f"A análise revisou {len(resultados)} fichas. "
        f"Foram identificados {nao_atende} itens não atendidos, {inconclusivos} inconclusivos "
        f"e {revisao_humana} itens com revisão humana obrigatória."
    )
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>PPC anotado · {escape(str(metadata.get('curso') or 'PPC'))}</title>
  <link rel="stylesheet" href="assets/analise-ppc.css">
  <script src="assets/analise-ppc.js" defer></script>
</head>
<body data-annotation-mode="acionaveis">
  <main class="review-shell">
    <header class="review-header">
      <p class="eyebrow">PPC anotado · revisão técnico-pedagógica</p>
      <h1>{escape(str(metadata.get('curso') or 'Curso não identificado'))}</h1>
      <p class="lead">{escape(resumo)}</p>
      <div class="status-row">
        <span><strong>Situação:</strong> <span class="badge estado-{escape(_css_slug(situacao))}">{escape(situacao)}</span></span>
        <span><strong>Campus:</strong> {escape(str(metadata.get('campus') or 'Não informado'))}</span>
        <span><strong>Modalidade:</strong> {escape(str(metadata.get('modalidade') or 'Não informada'))}</span>
      </div>
    </header>

    <section class="summary-panel" id="resumo">
      <h2>Resumo executivo</h2>
      <div class="metrics">
        <div class="metric"><span>Total de fichas</span><strong>{len(resultados)}</strong></div>
        <div class="metric"><span>Acionáveis</span><strong>{acionaveis}</strong></div>
        <div class="metric"><span>Não atendidas</span><strong>{nao_atende}</strong></div>
        <div class="metric"><span>Inconclusivas</span><strong>{inconclusivos}</strong></div>
        <div class="metric"><span>Revisão humana</span><strong>{revisao_humana}</strong></div>
        <div class="metric"><span>Alertas</span><strong>{len(alertas)}</strong></div>
        <div class="metric"><span>Feedback aos autores</span><strong>{feedbacks_autores}</strong></div>
        <div class="metric"><span>Fundamentações</span><strong>{fundamentacoes_normativas}</strong></div>
      </div>
    </section>

    <section class="section">
      <h2>Contagens</h2>
      <div class="finding-grid">
        <section><h3>Por estado</h3><table><tbody>{estados_html}</tbody></table></section>
        <section><h3>Por criticidade</h3><table><tbody>{criticidade_html}</tbody></table></section>
      </div>
    </section>

    <section class="control-panel" id="filtros" aria-label="Filtros da revisão">
      <label class="search-control">Busca
        <input id="filtro-busca" type="search" placeholder="Ficha, justificativa, evidência ou lacuna">
      </label>
      <label>Modo
        <select id="filtro-modo">
          <option value="acionaveis" selected>Acionáveis</option>
          <option value="todos">Todos os achados</option>
        </select>
      </label>
      <label>Estado
        <select id="filtro-estado">
          <option value="">Todos</option>
          <option value="ATENDE">ATENDE</option>
          <option value="NAO_ATENDE">NAO_ATENDE</option>
          <option value="INCONCLUSIVO">INCONCLUSIVO</option>
          <option value="NAO_APLICAVEL">NAO_APLICAVEL</option>
        </select>
      </label>
      <label>Criticidade
        <select id="filtro-criticidade">
          <option value="">Todas</option>
          <option value="BLOQ">BLOQ</option>
          <option value="OBRIG">OBRIG</option>
          <option value="REC">REC</option>
        </select>
      </label>
      <label>Revisão humana
        <select id="filtro-revisao">
          <option value="">Todas</option>
          <option value="sim">Sim</option>
          <option value="nao">Não</option>
        </select>
      </label>
      <p class="visible-count">Anotações visíveis: <strong id="contador-visivel">{acionaveis}</strong></p>
    </section>

    <section class="reader-layout" id="ppc-anotado" aria-label="PPC com anotações de revisão">
      <article class="ppc-document" aria-label="Conteúdo do PPC">
        {_render_ppc(blocos, anotacoes_por_bloco)}
      </article>
      <aside class="review-margin" aria-label="Anotações da revisão">
        <div class="margin-heading">
          <p class="eyebrow">Margem de revisão</p>
          <h2>Anotações</h2>
        </div>
        {_render_anotacoes_laterais(anotacoes, soltas, alertas_renderizados)}
      </aside>
    </section>

  </main>
</body>
</html>
"""


def _copiar_assets(destino_dir: Path) -> list[str]:
    origem = APP_DIR / "assets"
    destino = destino_dir / "assets"
    destino.mkdir(parents=True, exist_ok=True)
    copiados: list[str] = []
    for nome in ("analise-ppc.css", "analise-ppc.js"):
        origem_arquivo = origem / nome
        destino_arquivo = destino / nome
        shutil.copyfile(origem_arquivo, destino_arquivo)
        copiados.append(str(destino_arquivo))
    return copiados


def gerar_relatorio_html(rodada_dir: Path, resultados_path: Path) -> dict[str, Any]:
    caminhos = round_paths(rodada_dir)
    metadata = read_json(caminhos["metadata"])
    caminho_resultados = _resolver_resultados_path(caminhos["rodada_dir"], resultados_path)
    payload = read_json(caminho_resultados)
    fichas_por_id = _catalogo_fichas()
    validacoes_por_id = _catalogo_validacoes()
    resultados = validar_resultados_subagents(payload, fichas_por_id)
    alertas = validar_alertas_transversais(payload, fichas_por_id, validacoes_por_id)
    ppc_markdown = caminhos["ppc"].read_text(encoding="utf-8")
    html = _HTMLPrettyPrinter().pretty(_render_html(metadata, resultados, alertas, ppc_markdown))
    destino = caminhos["relatorio_html"]
    destino.write_text(html, encoding="utf-8")
    assets = _copiar_assets(caminhos["rodada_dir"])
    return {
        "relatorio_html": destino,
        "assets": assets,
        "total_fichas": len(resultados),
        "total_alertas_transversais": len(alertas),
        "situacao": _situacao(resultados),
    }
