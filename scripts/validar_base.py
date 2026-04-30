#!/usr/bin/env python3
"""Valida a base pública de conhecimento."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

from base_utils import (
    CAMPI_INDEX_PATH,
    CAMPI_INDEX_SCHEMA_PATH,
    CAMPUS_SCHEMA_PATH,
    INSTITUCIONAL_MANIFEST_PATH,
    INSTITUCIONAL_MANIFEST_SCHEMA_PATH,
    INSTITUCIONAL_ROOT,
    MANIFEST_FIELDS,
    MANIFEST_PATH,
    NORMAS_ROOT,
    README_PATH,
    REQUIRED_FIELDS,
    ROOT,
    TIPO_DIRETORIOS,
    TIPOS_UNIDADE_INSTITUCIONAL,
    frontmatter,
    relative,
)


LOCAL_PATTERNS = ["/" + "Users/", "Down" + "loads/", "file" + "://"]
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def validate_links(path: Path, text: str) -> list[str]:
    errors: list[str] = []
    for match in re.finditer(r"\[[^\]]+\]\(([^)]+)\)", text):
        target = match.group(1)
        if target.startswith(("http://", "https://", "#", "mailto:")):
            continue
        if target.startswith("/"):
            errors.append(f"{relative(path)}: link absoluto local ou de raiz: {target}")
            continue
        clean = target.split("#", 1)[0]
        if clean and not (path.parent / clean).resolve().exists():
            errors.append(f"{relative(path)}: link interno inexistente: {target}")
    return errors


def stale_filename_alias(alias: object) -> bool:
    if not isinstance(alias, str) or not alias.endswith(".md"):
        return False
    return bool(re.match(r"\d{4}-\d{2}-\d{2}_", alias) or re.search(r"[_-]\d{4}.*\.md$", alias))


def validate_markdown(path: Path) -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    for pattern in LOCAL_PATTERNS:
        if pattern in text:
            errors.append(f"{relative(path)}: contém padrão local proibido: {pattern}")

    try:
        meta, body = frontmatter(path)
    except ValueError as exc:
        return [str(exc)]

    missing = sorted(REQUIRED_FIELDS - set(meta))
    if missing:
        errors.append(f"{relative(path)}: campos obrigatórios ausentes: {', '.join(missing)}")
    if not body.lstrip().startswith("## Resumo"):
        errors.append(f"{relative(path)}: corpo não começa com ## Resumo")
    if not isinstance(meta.get("keywords"), list) or not meta.get("keywords"):
        errors.append(f"{relative(path)}: keywords deve ser lista não vazia")
    for alias in meta.get("aliases", []):
        if stale_filename_alias(alias):
            errors.append(f"{relative(path)}: alias parece nome antigo de arquivo: {alias}")

    errors.extend(validate_links(path, text))
    return errors


def comparable(field: str, value: object) -> object:
    if field == "ano" and value is not None:
        return str(value)
    return value


def validate_manifest_item(item: dict[str, object]) -> list[str]:
    errors: list[str] = []
    path_value = item.get("path")
    if not isinstance(path_value, str):
        return ["manifest.json: item sem path textual"]

    path = ROOT / path_value
    if not path.exists():
        return [f"manifest.json aponta para arquivo inexistente: {path_value}"]

    if re.match(r"\d{4}-\d{2}-\d{2}_", path.name):
        errors.append(f"{path_value}: nome do arquivo não deve começar com data")

    key = (str(item.get("jurisdicao")), str(item.get("tipo_documento")))
    expected_dir = TIPO_DIRETORIOS.get(key)
    if expected_dir is None:
        errors.append(f"manifest.json: item com jurisdição/tipo sem diretório configurado: {key}")
    elif str(path.parent.relative_to(ROOT)) != expected_dir:
        errors.append(f"{path_value}: deveria estar em {expected_dir}")

    try:
        meta, _body = frontmatter(path)
    except ValueError as exc:
        errors.append(str(exc))
        return errors

    for field in MANIFEST_FIELDS:
        if comparable(field, item.get(field)) != comparable(field, meta.get(field)):
            errors.append(f"{path_value}: manifest.json diverge do front matter no campo {field}")
    return errors


def validate_local_patterns() -> list[str]:
    errors: list[str] = []
    for path in ROOT.rglob("*"):
        if ".git" in path.parts or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in LOCAL_PATTERNS:
            if pattern in text:
                errors.append(f"{relative(path)} contém padrão local proibido: {pattern}")
    return errors


def load_manifest() -> tuple[list[object], list[str]]:
    try:
        data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return [], [f"manifest.json inválido: {exc}"]
    if not isinstance(data, list):
        return [], ["manifest.json deve conter uma lista"]
    return data, []


def load_json(path: Path, label: str) -> tuple[object | None, list[str]]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), []
    except FileNotFoundError:
        return None, [f"{label} não encontrado: {relative(path)}"]
    except Exception as exc:  # noqa: BLE001
        return None, [f"{label} inválido: {exc}"]


def type_name(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int) and not isinstance(value, bool):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def validate_json_schema(data: object, schema: dict[str, object], label: str, path: str = "$") -> list[str]:
    errors: list[str] = []

    expected_type = schema.get("type")
    if expected_type is not None and type_name(data) != expected_type:
        return [f"{label}: {path} deve ser {expected_type}, recebido {type_name(data)}"]

    if "const" in schema and data != schema["const"]:
        errors.append(f"{label}: {path} deve ser {schema['const']!r}")
    if "enum" in schema and data not in schema["enum"]:
        errors.append(f"{label}: {path} deve ser um de {schema['enum']!r}")

    if isinstance(data, str):
        min_length = schema.get("minLength")
        if isinstance(min_length, int) and len(data) < min_length:
            errors.append(f"{label}: {path} deve ter ao menos {min_length} caractere(s)")
        pattern = schema.get("pattern")
        if isinstance(pattern, str) and not re.search(pattern, data):
            errors.append(f"{label}: {path} não corresponde ao padrão {pattern}")
        if schema.get("format") == "date" and not DATE_RE.fullmatch(data):
            errors.append(f"{label}: {path} deve estar em YYYY-MM-DD")
        if schema.get("format") == "uri":
            parsed = urlparse(data)
            if not parsed.scheme or not parsed.netloc or re.search(r"\s", data):
                errors.append(f"{label}: {path} deve ser URI absoluta válida")

    if isinstance(data, int) and not isinstance(data, bool):
        minimum = schema.get("minimum")
        if isinstance(minimum, int) and data < minimum:
            errors.append(f"{label}: {path} deve ser maior ou igual a {minimum}")

    if isinstance(data, list):
        min_items = schema.get("minItems")
        if isinstance(min_items, int) and len(data) < min_items:
            errors.append(f"{label}: {path} deve ter ao menos {min_items} item(ns)")
        max_items = schema.get("maxItems")
        if isinstance(max_items, int) and len(data) > max_items:
            errors.append(f"{label}: {path} deve ter no máximo {max_items} item(ns)")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(data):
                errors.extend(validate_json_schema(item, item_schema, label, f"{path}[{index}]"))

    if isinstance(data, dict):
        required = schema.get("required")
        if isinstance(required, list):
            for field in required:
                if isinstance(field, str) and field not in data:
                    errors.append(f"{label}: {path}.{field} é obrigatório")

        properties = schema.get("properties")
        properties = properties if isinstance(properties, dict) else {}
        for key, value in data.items():
            child_schema = properties.get(key)
            if isinstance(child_schema, dict):
                errors.extend(validate_json_schema(value, child_schema, label, f"{path}.{key}"))
                continue
            additional = schema.get("additionalProperties", True)
            if additional is False:
                errors.append(f"{label}: {path}.{key} não é permitido")
            elif isinstance(additional, dict):
                errors.extend(validate_json_schema(value, additional, label, f"{path}.{key}"))

    return errors


def validate_with_schema(data: object, schema_path: Path, label: str) -> list[str]:
    schema, errors = load_json(schema_path, f"schema {relative(schema_path)}")
    if errors:
        return errors
    if not isinstance(schema, dict):
        return [f"schema {relative(schema_path)} deve conter um objeto JSON"]
    return validate_json_schema(data, schema, label)


def validate_https_url(value: object, field: str) -> list[str]:
    if not isinstance(value, str) or not value:
        return [f"{field} deve ser URL textual não vazia"]
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc or re.search(r"\s", value):
        return [f"{field} deve ser URL HTTPS absoluta válida"]
    return []


def validate_campus_file(path: Path, index_item: dict[str, object]) -> list[str]:
    errors: list[str] = []
    data, json_errors = load_json(path, f"arquivo de campus {relative(path)}")
    errors.extend(json_errors)
    if errors:
        return errors
    if not isinstance(data, dict):
        return [f"{relative(path)} deve conter um objeto JSON"]
    errors.extend(validate_with_schema(data, CAMPUS_SCHEMA_PATH, relative(path)))

    required = ["id", "nome", "tipo_unidade", "links", "cursos", "curadoria"]
    for field in required:
        if field not in data:
            errors.append(f"{relative(path)}: campo obrigatório ausente: {field}")

    campus_id = data.get("id")
    if not isinstance(campus_id, str) or not SLUG_RE.fullmatch(campus_id):
        errors.append(f"{relative(path)}: id deve ser slug ASCII minúsculo")
    elif path.name != f"{campus_id}.json":
        errors.append(f"{relative(path)}: nome do arquivo diverge do id")

    for field in ["id", "nome", "tipo_unidade"]:
        if data.get(field) != index_item.get(field):
            errors.append(f"{relative(path)}: campo {field} diverge do index.json")

    if data.get("tipo_unidade") not in TIPOS_UNIDADE_INSTITUCIONAL:
        errors.append(f"{relative(path)}: tipo_unidade inválido: {data.get('tipo_unidade')}")

    links = data.get("links")
    if not isinstance(links, dict):
        errors.append(f"{relative(path)}: links deve ser objeto")
    else:
        for field in ["site", "calendario_academico"]:
            if field not in links:
                errors.append(f"{relative(path)}: links.{field} ausente")
            else:
                errors.extend(validate_https_url(links[field], f"{relative(path)}: links.{field}"))

    cursos = data.get("cursos")
    if not isinstance(cursos, list):
        errors.append(f"{relative(path)}: cursos deve ser array")
    else:
        seen_course_ids: set[str] = set()
        for curso in cursos:
            if not isinstance(curso, dict):
                continue
            curso_id = curso.get("id")
            if isinstance(curso_id, str):
                if curso_id in seen_course_ids:
                    errors.append(f"{relative(path)}: curso duplicado: {curso_id}")
                seen_course_ids.add(curso_id)
            if "url" in curso:
                errors.extend(validate_https_url(curso["url"], f"{relative(path)}: cursos[].url"))

    curadoria = data.get("curadoria")
    if not isinstance(curadoria, dict):
        errors.append(f"{relative(path)}: curadoria deve ser objeto")
    else:
        if curadoria.get("status_cursos") not in {"dados_pendentes", "dados_parciais", "dados_curados"}:
            errors.append(f"{relative(path)}: curadoria.status_cursos inválido")
        fontes = curadoria.get("fontes", [])
        if not isinstance(fontes, list):
            errors.append(f"{relative(path)}: curadoria.fontes deve ser array")
        else:
            for fonte in fontes:
                errors.extend(validate_https_url(fonte, f"{relative(path)}: curadoria.fontes[]"))
        if not isinstance(curadoria.get("verificado_em"), str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", curadoria.get("verificado_em", "")):
            errors.append(f"{relative(path)}: curadoria.verificado_em deve estar em YYYY-MM-DD")

    return errors


def validate_institucional() -> list[str]:
    errors: list[str] = []
    manifest, manifest_errors = load_json(INSTITUCIONAL_MANIFEST_PATH, "institucional_manifest.json")
    errors.extend(manifest_errors)
    index, index_errors = load_json(CAMPI_INDEX_PATH, "índice de campi")
    errors.extend(index_errors)
    if errors:
        return errors

    if not isinstance(manifest, dict):
        errors.append("institucional_manifest.json deve conter um objeto JSON")
    else:
        errors.extend(validate_with_schema(manifest, INSTITUCIONAL_MANIFEST_SCHEMA_PATH, "institucional_manifest.json"))
        colecoes = manifest.get("colecoes")
        if not isinstance(colecoes, list) or not colecoes:
            errors.append("institucional_manifest.json: colecoes deve ser lista não vazia")
        else:
            campi_collection = next((item for item in colecoes if isinstance(item, dict) and item.get("id") == "campi-ifpr"), None)
            if campi_collection is None:
                errors.append("institucional_manifest.json: coleção campi-ifpr ausente")
            else:
                if campi_collection.get("path") != relative(CAMPI_INDEX_PATH):
                    errors.append("institucional_manifest.json: path da coleção campi-ifpr diverge do índice")

    if not isinstance(index, dict):
        errors.append(f"{relative(CAMPI_INDEX_PATH)} deve conter um objeto JSON")
        return errors
    errors.extend(validate_with_schema(index, CAMPI_INDEX_SCHEMA_PATH, relative(CAMPI_INDEX_PATH)))

    items = index.get("items")
    if not isinstance(items, list) or not items:
        errors.append(f"{relative(CAMPI_INDEX_PATH)}: items deve ser lista não vazia")
        return errors

    if isinstance(manifest, dict):
        colecoes = manifest.get("colecoes")
        if isinstance(colecoes, list):
            campi_collection = next((item for item in colecoes if isinstance(item, dict) and item.get("id") == "campi-ifpr"), None)
            if isinstance(campi_collection, dict) and campi_collection.get("total_itens") != len(items):
                errors.append("institucional_manifest.json: total_itens diverge do index.json")

    seen_ids: set[str] = set()
    index_paths: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            errors.append(f"{relative(CAMPI_INDEX_PATH)}: item deve ser objeto")
            continue
        campus_id = item.get("id")
        path_value = item.get("path")
        if not isinstance(campus_id, str) or not SLUG_RE.fullmatch(campus_id):
            errors.append(f"{relative(CAMPI_INDEX_PATH)}: id inválido: {campus_id}")
        elif campus_id in seen_ids:
            errors.append(f"{relative(CAMPI_INDEX_PATH)}: id duplicado: {campus_id}")
        else:
            seen_ids.add(campus_id)
        if item.get("tipo_unidade") not in TIPOS_UNIDADE_INSTITUCIONAL:
            errors.append(f"{relative(CAMPI_INDEX_PATH)}: tipo_unidade inválido em {campus_id}")
        if not isinstance(item.get("nome"), str) or not item.get("nome"):
            errors.append(f"{relative(CAMPI_INDEX_PATH)}: nome ausente em {campus_id}")
        if not isinstance(path_value, str):
            errors.append(f"{relative(CAMPI_INDEX_PATH)}: path ausente em {campus_id}")
            continue
        if not path_value.startswith("institucional/ifpr/campi/") or not path_value.endswith(".json"):
            errors.append(f"{relative(CAMPI_INDEX_PATH)}: path inválido em {campus_id}: {path_value}")
            continue
        index_paths.add(path_value)
        errors.extend(validate_campus_file(ROOT / path_value, item))

    campus_paths = {
        relative(path)
        for path in (INSTITUCIONAL_ROOT / "ifpr" / "campi").glob("*.json")
        if path.name != "index.json"
    }
    if index_paths != campus_paths:
        errors.append(
            "index.json não cobre exatamente os arquivos de campi: "
            f"index={sorted(index_paths)} arquivos={sorted(campus_paths)}"
        )

    return errors


def main() -> int:
    errors: list[str] = []
    if any(ROOT.rglob(".DS_Store")):
        errors.append("há arquivos .DS_Store no repositório")
    errors.extend(validate_local_patterns())

    manifest, manifest_errors = load_manifest()
    errors.extend(manifest_errors)

    root_markdown_paths = [path.name for path in ROOT.glob("*.md") if path.name not in {"AGENTS.md", "README.md"}]
    if root_markdown_paths:
        errors.append(f"normas não devem ficar na raiz do repositório: {sorted(root_markdown_paths)}")

    manifest_paths = {item.get("path") for item in manifest if isinstance(item, dict)}
    markdown_paths = {relative(path) for path in NORMAS_ROOT.rglob("*.md")}
    if manifest_paths != markdown_paths:
        errors.append(
            "manifest.json não cobre exatamente as normas publicadas: "
            f"manifest={sorted(manifest_paths)} markdown={sorted(markdown_paths)}"
        )

    readme_text = README_PATH.read_text(encoding="utf-8")
    for pattern in LOCAL_PATTERNS:
        if pattern in readme_text:
            errors.append(f"README.md contém padrão local proibido: {pattern}")
    errors.extend(validate_links(README_PATH, readme_text))
    errors.extend(validate_institucional())

    for path in sorted(NORMAS_ROOT.rglob("*.md")):
        errors.extend(validate_markdown(path))

    for item in manifest:
        if not isinstance(item, dict):
            errors.append("manifest.json contém item que não é objeto")
            continue
        for field in [*MANIFEST_FIELDS, "path"]:
            if field not in item:
                errors.append(f"manifest.json: item sem campo {field}: {item}")
        errors.extend(validate_manifest_item(item))

    if errors:
        for error in errors:
            print(f"ERRO: {error}", file=sys.stderr)
        return 1
    print(f"Base válida: {len(manifest)} normas publicadas e metadados institucionais conferidos.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
