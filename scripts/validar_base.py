#!/usr/bin/env python3
"""Valida a base pública de legislação."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from base_utils import (
    MANIFEST_FIELDS,
    MANIFEST_PATH,
    NORMAS_ROOT,
    README_PATH,
    REQUIRED_FIELDS,
    ROOT,
    TIPO_DIRETORIOS,
    frontmatter,
    relative,
)


LOCAL_PATTERNS = ["/" + "Users/", "Down" + "loads/", "file" + "://"]


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


def main() -> int:
    errors: list[str] = []
    if any(ROOT.rglob(".DS_Store")):
        errors.append("há arquivos .DS_Store no repositório")
    errors.extend(validate_local_patterns())

    manifest, manifest_errors = load_manifest()
    errors.extend(manifest_errors)

    root_markdown_paths = [path.name for path in ROOT.glob("*.md") if path.name != "README.md"]
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
    print(f"Base válida: {len(manifest)} normas publicadas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
