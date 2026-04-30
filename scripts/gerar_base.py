#!/usr/bin/env python3
"""Gera manifest.json e a tabela do README a partir de normas/*.md."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NORMAS_ROOT = ROOT / "normas"
MANIFEST_PATH = ROOT / "manifest.json"
README_PATH = ROOT / "README.md"

MANIFEST_FIELDS = [
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
]


def yaml_value(value: str, key: str | None = None) -> object:
    value = value.strip()
    if not value:
        return ""
    if value.startswith('"') and value.endswith('"'):
        return json.loads(value)
    if value.startswith("[") and value.endswith("]"):
        items = [item.strip() for item in value[1:-1].split(",") if item.strip()]
        return [yaml_value(item) for item in items]
    if key == "ano" and value.isdigit():
        return int(value)
    return value


def parse_frontmatter(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"{path.relative_to(ROOT)}: arquivo sem front matter")
    end = text.find("\n---", 4)
    if end == -1:
        raise ValueError(f"{path.relative_to(ROOT)}: front matter sem fechamento")

    data: dict[str, object] = {}
    current: str | None = None
    for line in text[4:end].strip().splitlines():
        if not line.strip():
            continue
        if line.startswith("  - "):
            if current is None:
                raise ValueError(f"{path.relative_to(ROOT)}: item de lista sem campo")
            data.setdefault(current, [])
            if not isinstance(data[current], list):
                raise ValueError(f"{path.relative_to(ROOT)}: campo {current} mistura escalar e lista")
            data[current].append(yaml_value(line[4:]))
            continue
        if ":" not in line:
            raise ValueError(f"{path.relative_to(ROOT)}: linha inválida no front matter: {line}")
        key, value = line.split(":", 1)
        current = key.strip()
        data[current] = [] if not value.strip() else yaml_value(value, current)
    return data


def manifest_item(path: Path) -> dict[str, object]:
    meta = parse_frontmatter(path)
    missing = [field for field in MANIFEST_FIELDS if field not in meta]
    if missing:
        raise ValueError(
            f"{path.relative_to(ROOT)}: campos ausentes para manifest.json: {', '.join(missing)}"
        )
    item = {field: meta[field] for field in MANIFEST_FIELDS}
    item["path"] = str(path.relative_to(ROOT))
    return item


def build_manifest() -> list[dict[str, object]]:
    manifest = [manifest_item(path) for path in sorted(NORMAS_ROOT.rglob("*.md"))]
    manifest.sort(key=lambda item: (str(item["data_publicacao"]), str(item["title"])))
    return manifest


def write_manifest(manifest: list[dict[str, object]]) -> None:
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def readme_table(manifest: list[dict[str, object]]) -> str:
    rows = "\n".join(
        f"| [{item['title']}]({item['path']}) | {item['tipo_documento']} | {item['ano']} | {item['ementa']} |"
        for item in manifest
    )
    return "\n".join(
        [
            "| Documento | Tipo | Ano | Assunto |",
            "|-----------|------|-----|---------|",
            rows,
        ]
    )


def write_readme(manifest: list[dict[str, object]]) -> None:
    text = README_PATH.read_text(encoding="utf-8")
    start = text.index("| Documento | Tipo | Ano | Assunto |")
    end = text.index("\n\n## Manutenção", start)
    updated = text[:start] + readme_table(manifest) + text[end:]
    README_PATH.write_text(updated, encoding="utf-8")


def main() -> None:
    if not NORMAS_ROOT.exists():
        raise SystemExit(f"Diretório de normas não encontrado: {NORMAS_ROOT}")
    manifest = build_manifest()
    write_manifest(manifest)
    write_readme(manifest)
    print(f"Base gerada: {len(manifest)} normas publicadas.")


if __name__ == "__main__":
    main()
