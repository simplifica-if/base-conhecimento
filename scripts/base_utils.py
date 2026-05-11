"""Utilitários compartilhados para geração e validação da base."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NORMAS_ROOT = ROOT / "normas"
INSTITUCIONAL_ROOT = ROOT / "institucional"
PPCS_ROOT = INSTITUCIONAL_ROOT / "ifpr" / "ppcs"
CATALOGOS_ROOT = ROOT / "catalogos"
INSTITUCIONAL_MANIFEST_PATH = ROOT / "institucional_manifest.json"
CATALOGOS_MANIFEST_PATH = ROOT / "catalogos_manifest.json"
CAMPI_INDEX_PATH = INSTITUCIONAL_ROOT / "ifpr" / "campi" / "index.json"
CNCT_MANIFEST_PATH = CATALOGOS_ROOT / "cnct" / "manifest.json"
CNCT_INDEX_PATH = CATALOGOS_ROOT / "cnct" / "index.json"
CNCT_CURSOS_ROOT = CATALOGOS_ROOT / "cnct" / "cursos"
SCHEMAS_ROOT = ROOT / "schemas"
INSTITUCIONAL_MANIFEST_SCHEMA_PATH = SCHEMAS_ROOT / "institucional_manifest.schema.json"
CATALOGOS_MANIFEST_SCHEMA_PATH = SCHEMAS_ROOT / "catalogos_manifest.schema.json"
CAMPI_INDEX_SCHEMA_PATH = SCHEMAS_ROOT / "campi_index.schema.json"
CAMPUS_SCHEMA_PATH = SCHEMAS_ROOT / "campus.schema.json"
CNCT_MANIFEST_SCHEMA_PATH = SCHEMAS_ROOT / "cnct_manifest.schema.json"
CNCT_INDEX_SCHEMA_PATH = SCHEMAS_ROOT / "cnct_index.schema.json"
CNCT_CURSO_SCHEMA_PATH = SCHEMAS_ROOT / "cnct_curso.schema.json"
MANIFEST_PATH = ROOT / "manifest.json"
README_PATH = ROOT / "README.md"

REQUIRED_FIELDS = {
    "title",
    "tipo_documento",
    "numero",
    "ano",
    "data_publicacao",
    "ementa",
    "status_vigencia",
    "keywords",
}
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
TIPO_DIRETORIOS = {
    ("BR", "Lei"): "normas/br/leis",
    ("BR", "Resolução"): "normas/br/resolucoes",
    ("BR", "Compilação"): "normas/br/compilacoes",
    ("IFPR", "Resolução"): "normas/ifpr/resolucoes",
    ("IFPR", "Portaria"): "normas/ifpr/portarias",
    ("IFPR", "Nota Técnica"): "normas/ifpr/notas-tecnicas",
}
TIPOS_UNIDADE_INSTITUCIONAL = {"campus", "campus_avancado"}


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT))


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


def frontmatter(path: Path) -> tuple[dict[str, object], str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"{relative(path)}: arquivo sem front matter")
    end = text.find("\n---", 4)
    if end == -1:
        raise ValueError(f"{relative(path)}: front matter sem fechamento")

    data: dict[str, object] = {}
    current: str | None = None
    for line in text[4:end].strip().splitlines():
        if not line.strip():
            continue
        if line.startswith("  - "):
            if current is None:
                raise ValueError(f"{relative(path)}: item de lista sem campo")
            data.setdefault(current, [])
            if not isinstance(data[current], list):
                raise ValueError(f"{relative(path)}: campo {current} mistura escalar e lista")
            data[current].append(yaml_value(line[4:]))
            continue
        if ":" not in line:
            raise ValueError(f"{relative(path)}: linha inválida no front matter: {line}")
        key, value = line.split(":", 1)
        current = key.strip()
        data[current] = [] if not value.strip() else yaml_value(value, current)

    body_start = text.find("\n", end + 4)
    body = text[body_start + 1 :] if body_start != -1 else ""
    return data, body


def manifest_item(path: Path) -> dict[str, object]:
    meta, _body = frontmatter(path)
    missing = [field for field in MANIFEST_FIELDS if field not in meta]
    if missing:
        raise ValueError(f"{relative(path)}: campos ausentes para manifest.json: {', '.join(missing)}")
    item = {field: meta[field] for field in MANIFEST_FIELDS}
    item["path"] = relative(path)
    return item


def build_manifest() -> list[dict[str, object]]:
    manifest = [manifest_item(path) for path in sorted(NORMAS_ROOT.rglob("*.md"))]
    manifest.sort(key=lambda item: (str(item["data_publicacao"]), str(item["title"])))
    return manifest


def manifest_json(manifest: list[dict[str, object]]) -> str:
    return json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
