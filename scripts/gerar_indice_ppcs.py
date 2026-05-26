#!/usr/bin/env python3
"""Gera índices globais dos PPCs convertidos para Markdown."""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import defaultdict
from datetime import date
from pathlib import Path

from base_utils import INSTITUCIONAL_ROOT, PPCS_INDEX_PATH, PPCS_SECOES_PATH, ROOT, relative


SECTION_TEXT_LIMIT = 8000
SECTION_KINDS = {
    "identificacao",
    "justificativa",
    "objetivos",
    "perfil_egresso",
    "concepcao_pedagogica",
    "organizacao_curricular",
    "matriz_curricular",
    "ementas",
    "avaliacao",
    "estagio_praticas",
    "infraestrutura",
    "corpo_docente",
    "referencias",
    "outros",
}


def strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def clean_text(text: str) -> str:
    text = text.replace("\x00", "")
    text = re.sub(r"<br\s*/?>", " ", text)
    text = re.sub(r"[*#>`_]+", "", text)
    text = re.sub(r"\|+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def clean_heading(text: str) -> str:
    text = clean_text(text)
    text = re.sub(r"^\d+(?:\.\d+)*\s*[-–.]?\s*", lambda match: match.group(0).strip() + " ", text)
    return re.sub(r"\s+", " ", text).strip(" -")


def heading_from_line(line: str) -> str | None:
    stripped = line.strip()
    if not stripped:
        return None

    markdown_heading = re.match(r"^#{2,6}\s+(.+?)\s*#*$", stripped)
    if markdown_heading:
        return clean_heading(markdown_heading.group(1))

    bold_heading = re.match(r"^\*\*(.+?)\*\*$", stripped)
    if bold_heading:
        candidate = clean_heading(bold_heading.group(1))
        normalized = strip_accents(candidate).lower()
        if len(candidate) <= 180 and any(
            marker in normalized
            for marker in [
                "identificacao",
                "justificativa",
                "objetivo",
                "perfil",
                "organizacao",
                "matriz",
                "ementa",
                "avaliacao",
                "infraestrutura",
                "referencia",
                "projeto pedagogico",
            ]
        ):
            return candidate

    return None


def section_kind(heading: str) -> str:
    normalized = strip_accents(heading).lower()
    normalized = re.sub(r"\s+", " ", normalized)

    if "identificacao" in normalized or "caracteristicas do curso" in normalized:
        return "identificacao"
    if "justificativa" in normalized:
        return "justificativa"
    if "objetivo" in normalized:
        return "objetivos"
    if "perfil" in normalized and (
        "egresso" in normalized or "conclusao" in normalized or "profissional" in normalized
    ):
        return "perfil_egresso"
    if (
        "concepcao" in normalized
        or "pressupostos pedagogicos" in normalized
        or "orientacao metodologica" in normalized
    ):
        return "concepcao_pedagogica"
    if "organizacao curricular" in normalized:
        return "organizacao_curricular"
    if "matriz curricular" in normalized:
        return "matriz_curricular"
    if "ementa" in normalized:
        return "ementas"
    if "avaliacao" in normalized:
        return "avaliacao"
    if "estagio" in normalized or "pratica profissional" in normalized or "praticas profissionais" in normalized:
        return "estagio_praticas"
    if "infraestrutura" in normalized:
        return "infraestrutura"
    if "corpo docente" in normalized or "pessoal docente" in normalized or "perfil do pessoal" in normalized:
        return "corpo_docente"
    if "referencia" in normalized:
        return "referencias"
    return "outros"


def iter_campus_paths() -> list[Path]:
    campi_root = INSTITUCIONAL_ROOT / "ifpr" / "campi"
    return sorted(path for path in campi_root.glob("*.json") if path.name != "index.json")


def ppc_metadata_value(ppc: dict[str, object], key: str, nested_key: str) -> object | None:
    metadados = ppc.get("metadados")
    if not isinstance(metadados, dict):
        return None
    value = metadados.get(key)
    if not isinstance(value, dict):
        return None
    return value.get(nested_key)


def build_ppc_item(campus: dict[str, object], curso: dict[str, object], ppc: dict[str, object]) -> dict[str, object]:
    campus_id = str(campus["id"])
    curso_id = str(curso["id"])
    item: dict[str, object] = {
        "id": f"{campus_id}/{curso_id}",
        "campus_id": campus_id,
        "campus_nome": campus["nome"],
        "curso_id": curso_id,
        "curso_nome": curso["nome"],
        "notion_page_id": ppc["notion_page_id"],
        "nivel": curso["nivel"],
        "tipo_oferta": curso["tipo_oferta"],
        "curso_url": curso["url"],
        "fonte_pdf": ppc["url"],
        "path": ppc["markdown_path"],
    }
    for key in ["modalidade", "situacao", "escopo"]:
        value = curso.get(key)
        if isinstance(value, str) and value:
            item[key] = value

    ano = ppc_metadata_value(ppc, "ano_documento", "ano")
    if isinstance(ano, int):
        item["ano_documento"] = ano

    vagas = ppc_metadata_value(ppc, "vagas", "quantidade")
    if isinstance(vagas, int):
        item["vagas"] = vagas

    return item


def collect_ppc_items() -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for campus_path in iter_campus_paths():
        campus = json.loads(campus_path.read_text(encoding="utf-8"))
        if not isinstance(campus, dict):
            continue
        for curso in campus.get("cursos", []):
            if not isinstance(curso, dict):
                continue
            ppc = curso.get("ppc")
            if not isinstance(ppc, dict):
                continue
            conversao = ppc.get("conversao")
            markdown_path = ppc.get("markdown_path")
            if (
                not isinstance(conversao, dict)
                or conversao.get("status") != "convertido"
                or not isinstance(markdown_path, str)
                or not (ROOT / markdown_path).exists()
            ):
                continue
            required = [campus.get("id"), campus.get("nome"), curso.get("id"), curso.get("nome")]
            required.extend([curso.get("nivel"), curso.get("tipo_oferta"), curso.get("url"), ppc.get("url")])
            if not all(isinstance(value, str) and value for value in required):
                continue
            items.append(build_ppc_item(campus, curso, ppc))
    return sorted(items, key=lambda item: (str(item["campus_id"]), str(item["curso_nome"])))


def split_sections(markdown: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []
    current_heading: str | None = None
    current_lines: list[str] = []

    for line in markdown.splitlines():
        heading = heading_from_line(line)
        if heading:
            if current_heading is not None:
                text = clean_text("\n".join(current_lines))
                if len(text) >= 40:
                    sections.append((current_heading, text[:SECTION_TEXT_LIMIT]))
            current_heading = heading
            current_lines = []
            continue
        if current_heading is not None:
            current_lines.append(line)

    if current_heading is not None:
        text = clean_text("\n".join(current_lines))
        if len(text) >= 40:
            sections.append((current_heading, text[:SECTION_TEXT_LIMIT]))

    return sections


def build_section_items(ppc_items: list[dict[str, object]]) -> list[dict[str, object]]:
    section_items: list[dict[str, object]] = []
    for ppc_item in ppc_items:
        markdown = (ROOT / str(ppc_item["path"])).read_text(encoding="utf-8", errors="ignore")
        counters: defaultdict[str, int] = defaultdict(int)
        for heading, text in split_sections(markdown):
            kind = section_kind(heading)
            if kind not in SECTION_KINDS:
                kind = "outros"
            counters[kind] += 1
            section_items.append(
                {
                    "id": f"{ppc_item['id']}#{kind}-{counters[kind]}",
                    "ppc_id": ppc_item["id"],
                    "campus_id": ppc_item["campus_id"],
                    "curso_id": ppc_item["curso_id"],
                    "curso_nome": ppc_item["curso_nome"],
                    "section_kind": kind,
                    "heading": heading,
                    "path": ppc_item["path"],
                    "texto": text,
                }
            )
    return section_items


def current_index_date() -> str:
    if PPCS_INDEX_PATH.exists():
        try:
            data = json.loads(PPCS_INDEX_PATH.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return date.today().isoformat()
        if isinstance(data, dict) and isinstance(data.get("atualizado_em"), str):
            return data["atualizado_em"]
    return date.today().isoformat()


def build_index(items: list[dict[str, object]], atualizado_em: str) -> dict[str, object]:
    return {
        "title": "Projetos Pedagógicos de Curso do IFPR",
        "tipo": "indice_ppcs",
        "versao": 1,
        "atualizado_em": atualizado_em,
        "total_itens": len(items),
        "secoes_path": relative(PPCS_SECOES_PATH),
        "items": items,
    }


def index_json(index: dict[str, object]) -> str:
    return json.dumps(index, ensure_ascii=False, indent=2) + "\n"


def secoes_jsonl(section_items: list[dict[str, object]]) -> str:
    return "".join(json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n" for item in section_items)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verifica se os índices de PPCs estão atualizados")
    args = parser.parse_args()

    ppc_items = collect_ppc_items()
    section_items = build_section_items(ppc_items)
    atualizado_em = current_index_date() if args.check else date.today().isoformat()
    expected_index = index_json(build_index(ppc_items, atualizado_em))
    expected_sections = secoes_jsonl(section_items)

    if args.check:
        errors: list[str] = []
        if not PPCS_INDEX_PATH.exists() or PPCS_INDEX_PATH.read_text(encoding="utf-8") != expected_index:
            errors.append(f"{relative(PPCS_INDEX_PATH)} está desatualizado")
        if not PPCS_SECOES_PATH.exists() or PPCS_SECOES_PATH.read_text(encoding="utf-8") != expected_sections:
            errors.append(f"{relative(PPCS_SECOES_PATH)} está desatualizado")
        if errors:
            for error in errors:
                print(f"ERRO: {error}", file=sys.stderr)
            return 1
        print(f"Índices de PPCs atualizados: {len(ppc_items)} PPCs, {len(section_items)} seções.")
        return 0

    PPCS_INDEX_PATH.write_text(expected_index, encoding="utf-8")
    PPCS_SECOES_PATH.write_text(expected_sections, encoding="utf-8")
    print(f"Índices de PPCs gerados: {len(ppc_items)} PPCs, {len(section_items)} seções.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
