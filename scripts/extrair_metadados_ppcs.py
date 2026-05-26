#!/usr/bin/env python3
"""Extrai metadados básicos de PPCs convertidos para Markdown."""

from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path

from base_utils import INSTITUCIONAL_ROOT, ROOT


YEAR_RE = re.compile(r"\b(20\d{2}|19\d{2})\b")
CURRENT_RE = re.compile(r"\b20(?:2[3-9]|[3-9]\d)\b")
NUMBER_WORDS = {
    "dez": 10,
    "quinze": 15,
    "vinte": 20,
    "trinta": 30,
    "quarenta": 40,
    "cinquenta": 50,
    "sessenta": 60,
    "setenta": 70,
    "oitenta": 80,
}


def clean_text(text: str) -> str:
    text = text.replace("\x00", "")
    text = re.sub(r"<br\s*/?>", " ", text)
    text = re.sub(r"[*#>`_]+", "", text)
    text = re.sub(r"\|+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def clean_source(text: str) -> str:
    text = clean_text(text)
    return text[:280].strip(" -;:.")


def parse_pt_number(value: str | None) -> int | None:
    if not value:
        return None
    if value.isdigit():
        return int(value)
    return NUMBER_WORDS.get(value.lower())


def first_lines(text: str, limit: int = 140) -> list[str]:
    lines: list[str] = []
    for raw in text.splitlines():
        line = clean_text(raw)
        if line:
            lines.append(line)
        if len(lines) >= limit:
            break
    return lines


def extract_year(markdown: str) -> dict[str, object] | None:
    lines = first_lines(markdown)
    preferred: list[tuple[int, str]] = []
    fallback: list[tuple[int, str]] = []
    for line in lines:
        years = [int(match.group(1)) for match in YEAR_RE.finditer(line)]
        if not years:
            continue
        candidate = max(years)
        lower = line.lower()
        if any(marker in lower for marker in ["campus", "curitiba", "colombo", "arapongas", "palmas", "ifpr"]):
            preferred.append((candidate, line))
        elif len(line) <= 80 or "autorizado" in lower or "atualizado" in lower or "resolução" in lower:
            fallback.append((candidate, line))

    selected = preferred[0] if preferred else (fallback[0] if fallback else None)
    if selected is None:
        years = [int(match.group(1)) for match in YEAR_RE.finditer(clean_text(markdown[:6000]))]
        if not years:
            return None
        selected = (max(years), f"Ano inferido a partir das primeiras páginas: {max(years)}")

    return {
        "ano": selected[0],
        "trecho_fonte": clean_source(selected[1]),
        "secao": "Capa / folha inicial",
        "status_curadoria": "precisa_revisao",
    }


def extract_vagas(markdown: str) -> dict[str, object] | None:
    text = clean_text(markdown[:50000])
    patterns = [
        (
            re.compile(
                r"(N[uú]mero\s+m[aá]ximo\s+de\s+vagas(?:\s+do\s+curso|\s+por\s+curso|\s+por\s+ingresso\s*\(anual\))?)"
                r"\s*:?\s*(\d{1,4})\s*(?:vagas?)?"
                r".{0,220}?(?:N[uú]mero\s+m[ií]nimo\s+de\s+vagas(?:\s+do\s+curso|\s+por\s+curso|\s+por\s+ingresso\s*\(anual\))?)"
                r"\s*:?\s*(\d{1,4})",
                re.I,
            ),
            "max_min",
        ),
        (
            re.compile(
                r"(N[uú]mero\s+m[ií]nimo\s+de\s+vagas(?:\s+do\s+curso|\s+por\s+curso|\s+por\s+turno|\s+por\s+ingresso\s*\(anual\))?)"
                r"\s*:?\s*(\d{1,4})\s*(?:vagas?)?"
                r".{0,220}?(?:N[uú]mero\s+m[aá]ximo\s+de\s+vagas(?:\s+do\s+curso|\s+por\s+curso|\s+por\s+turno|\s+por\s+ingresso\s*\(anual\))?)"
                r"\s*:?\s*(\d{1,4})",
                re.I,
            ),
            "min_max",
        ),
        (
            re.compile(
                r"(N[uú]mero\s+de\s+vagas|Vagas\s+totais(?:\s*\(anua(?:l|is)\))?)"
                r".{0,160}?(?:M[ií]nimo|mínimo)\D{0,40}(\d{1,4})\D{0,80}"
                r"(?:M[aá]ximo|máximo)\D{0,40}(\d{1,4})",
                re.I,
            ),
            "min_max",
        ),
        (
            re.compile(
                r"(N[uú]mero\s+de\s+vagas)"
                r".{0,120}?(?:M[ií]nimo|mínimo)\s+(?:M[aá]ximo|máximo)\s+(\d{1,4})\s+(\d{1,4})",
                re.I,
            ),
            "min_max",
        ),
        (
            re.compile(
                r"(N[uú]mero\s+de\s+vagas\s+ofertadas)"
                r"\s*:?\s*m[ií]nimo\s+(\d{1,4}).{0,80}?m[aá]ximo,?\s*(\d{1,4})",
                re.I,
            ),
            "min_max",
        ),
        (
            re.compile(
                r"(Vagas\s+ofertadas|Vagas\s+totais(?:\s*\(anual\))?|Quantidade\s+de\s+Vagas|"
                r"N[uú]mero\s+m[aá]ximo\s+de\s+vagas(?:\s+do\s+curso|\s+por\s+ingresso\s*\(anual\))?)"
                r".{0,220}?(?:M[aá]ximo|máximo|N[uú]mero\s+m[aá]ximo\s+de\s+vagas(?:\s+do\s+curso|\s+por\s+ingresso\s*\(anual\))?)"
                r"\s*:?\s*(\d{1,4})\s*(?:vagas?)?"
                r".{0,220}?(?:M[ií]nimo|mínimo|N[uú]mero\s+m[ií]nimo\s+de\s+vagas(?:\s+do\s+curso|\s+por\s+ingresso\s*\(anual\))?)"
                r"\s*:?\s*(\d{1,4})",
                re.I,
            ),
            "max_min",
        ),
        (
            re.compile(
                r"(Vagas\s+ofertadas|Vagas\s+totais(?:\s*\(anual\))?|Quantidade\s+de\s+Vagas)"
                r".{0,220}?(?:M[ií]nimo|mínimo)\s*:?\s*(\d{1,4})\s*(?:vagas?)?"
                r".{0,220}?(?:M[aá]ximo|máximo)\s*:?\s*(\d{1,4})",
                re.I,
            ),
            "min_max",
        ),
        (
            re.compile(
                r"(Vagas\s+totais(?:\s*\(anual\))?|Vagas\s+totais)"
                r"\s*:?\s*(\d{1,4})\s*(?:a|-|até)\s*(\d{1,4})\s*vagas?",
                re.I,
            ),
            "range",
        ),
        (
            re.compile(
                r"(Vagas\s+totais(?:\s*\(anua(?:l|is)\))?|Vagas\s+ofertadas|Quantidade\s+de\s+Vagas)"
                r"\s*:?\s*(\d{1,4})\s*(?:vagas?)?",
                re.I,
            ),
            "single",
        ),
        (
            re.compile(r"(Vagas)\s*:?\s*(\d{1,4})\s*vagas?", re.I),
            "single",
        ),
        (
            re.compile(
                r"(Vagas\s+totais(?:\s*\(anua(?:l|is)\))?|Total\s+de\s+vagas\s+anuais)"
                r".{0,80}?(?:at[eé]\s+|uma\s+turma\s+de\s+)?(\d{1,4}|dez|quinze|vinte|trinta|quarenta|cinquenta|sessenta|setenta|oitenta)"
                r"(?:\s*\([^)]*\))?\s*vagas?",
                re.I,
            ),
            "single",
        ),
        (
            re.compile(
                r"(Vagas\s+totais(?:\s*\(anua(?:l|is)\))?)"
                r"\s*:?\s*(\d{1,4})\s*(?:\([^)]*\))?\s*vagas?",
                re.I,
            ),
            "single",
        ),
        (
            re.compile(
                r"(S[aã]o\s+disponibilizadas|S[aã]o\s+ofertadas|Oferta(?:m|das)?)"
                r".{0,120}?(?:total\s+de\s+)?(\d{1,4})\s+vagas",
                re.I,
            ),
            "single",
        ),
    ]
    for pattern, kind in patterns:
        for match in pattern.finditer(text):
            numbers = [number for group in match.groups()[1:] if (number := parse_pt_number(group)) is not None]
            if not numbers:
                continue
            quantidade = max(numbers)
            if quantidade < 10:
                continue
            trecho = text[max(0, match.start() - 20) : min(len(text), match.end() + 80)]
            vagas: dict[str, object] = {
                "quantidade": quantidade,
                "trecho_fonte": clean_source(trecho),
                "secao": clean_source(match.group(1)),
                "status_curadoria": "precisa_revisao",
            }
            if "anual" in match.group(0).lower():
                vagas["periodicidade"] = "anual"
            if kind in {"max_min", "min_max", "range"} and len(numbers) >= 2:
                vagas["forma_oferta"] = f"máximo de {max(numbers)} vagas e mínimo de {min(numbers)} vagas"
            return vagas
    return None


def iter_campus_paths(campus_filter: str | None) -> list[Path]:
    campi_root = INSTITUCIONAL_ROOT / "ifpr" / "campi"
    if campus_filter:
        return [campi_root / f"{campus_filter}.json"]
    return sorted(path for path in campi_root.glob("*.json") if path.name != "index.json")


def update_campus(path: Path, overwrite: bool) -> int:
    data = json.loads(path.read_text(encoding="utf-8"))
    changed = 0
    for curso in data.get("cursos", []):
        if not isinstance(curso, dict):
            continue
        ppc = curso.get("ppc")
        if not isinstance(ppc, dict) or ppc.get("conversao", {}).get("status") != "convertido":
            continue
        markdown_path = ppc.get("markdown_path")
        if not isinstance(markdown_path, str):
            continue
        markdown_file = ROOT / markdown_path
        if not markdown_file.exists():
            continue
        markdown = markdown_file.read_text(encoding="utf-8", errors="ignore")
        metadados = ppc.setdefault("metadados", {})
        if not isinstance(metadados, dict):
            continue

        year = extract_year(markdown)
        if year and (overwrite or "ano_documento" not in metadados):
            metadados["ano_documento"] = year
            changed += 1

        vagas = extract_vagas(markdown)
        if vagas and (overwrite or "vagas" not in metadados):
            metadados["vagas"] = vagas
            changed += 1

    if changed:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campus", help="Filtra por id do campus")
    parser.add_argument("--overwrite", action="store_true", help="Sobrescreve metadados já existentes")
    args = parser.parse_args()

    total = 0
    for path in iter_campus_paths(args.campus):
        if path.exists():
            count = update_campus(path, args.overwrite)
            if count:
                print(f"{path.name}: {count} metadado(s) atualizado(s)")
            total += count
    print(f"Metadados atualizados: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
