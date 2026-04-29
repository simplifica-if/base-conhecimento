#!/usr/bin/env python3
"""Valida a base pública de legislação."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED = {
    "title",
    "tipo_documento",
    "numero",
    "ano",
    "data_publicacao",
    "ementa",
    "status_vigencia",
    "keywords",
}
LOCAL_PATTERNS = ["/" + "Users/", "Down" + "loads/", "file" + "://"]


def frontmatter(text: str) -> tuple[dict[str, object], str]:
    if not text.startswith("---\n"):
        raise ValueError("arquivo sem front matter")
    end = text.find("\n---", 4)
    if end == -1:
        raise ValueError("front matter sem fechamento")
    raw = text[4:end].strip().splitlines()
    body = text[text.find("\n", end + 4) + 1 :]
    data: dict[str, object] = {}
    current: str | None = None
    for line in raw:
        if not line.strip():
            continue
        if line.startswith("  - "):
            if current is None:
                raise ValueError(f"item de lista sem campo: {line}")
            data.setdefault(current, [])
            assert isinstance(data[current], list)
            data[current].append(line[4:].strip().strip('"'))
            continue
        if ":" not in line:
            raise ValueError(f"linha inválida no front matter: {line}")
        key, value = line.split(":", 1)
        current = key.strip()
        value = value.strip()
        data[current] = [] if value == "" else value.strip('"')
    return data, body


def validate_links(path: Path, text: str) -> list[str]:
    errors: list[str] = []
    for match in re.finditer(r"\[[^\]]+\]\(([^)]+)\)", text):
        target = match.group(1)
        if target.startswith(("http://", "https://", "#", "mailto:")):
            continue
        if target.startswith("/"):
            errors.append(f"{path.name}: link absoluto local ou de raiz: {target}")
            continue
        clean = target.split("#", 1)[0]
        if clean and not (path.parent / clean).resolve().exists():
            errors.append(f"{path.name}: link interno inexistente: {target}")
    return errors


def validate_markdown(path: Path) -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    for pattern in LOCAL_PATTERNS:
        if pattern in text:
            errors.append(f"{path.name}: contém padrão local proibido: {pattern}")
    try:
        meta, body = frontmatter(text)
    except ValueError as exc:
        return [f"{path.name}: {exc}"]
    missing = sorted(REQUIRED - set(meta))
    if missing:
        errors.append(f"{path.name}: campos obrigatórios ausentes: {', '.join(missing)}")
    if not body.lstrip().startswith("## Resumo"):
        errors.append(f"{path.name}: corpo não começa com ## Resumo")
    if not isinstance(meta.get("keywords"), list) or not meta.get("keywords"):
        errors.append(f"{path.name}: keywords deve ser lista não vazia")
    errors.extend(validate_links(path, text))
    return errors


def main() -> int:
    errors: list[str] = []
    if any(ROOT.rglob(".DS_Store")):
        errors.append("há arquivos .DS_Store no repositório")
    for path in ROOT.rglob("*"):
        if ".git" in path.parts or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in LOCAL_PATTERNS:
            if pattern in text:
                errors.append(f"{path.relative_to(ROOT)} contém padrão local proibido: {pattern}")

    manifest_path = ROOT / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        errors.append(f"manifest.json inválido: {exc}")
        manifest = []

    manifest_paths = {item.get("path") for item in manifest if isinstance(item, dict)}
    markdown_paths = {
        path.name
        for path in ROOT.glob("*.md")
        if path.name != "README.md"
    }
    if manifest_paths != markdown_paths:
        errors.append(
            "manifest.json não cobre exatamente as normas publicadas: "
            f"manifest={sorted(manifest_paths)} markdown={sorted(markdown_paths)}"
        )

    for path in sorted(ROOT.glob("*.md")):
        if path.name == "README.md":
            text = path.read_text(encoding="utf-8")
            for pattern in LOCAL_PATTERNS:
                if pattern in text:
                    errors.append(f"README.md contém padrão local proibido: {pattern}")
            errors.extend(validate_links(path, text))
            continue
        errors.extend(validate_markdown(path))

    for item in manifest:
        if not isinstance(item, dict):
            errors.append("manifest.json contém item que não é objeto")
            continue
        for field in ["title", "tipo_documento", "numero", "ano", "data_publicacao", "orgao", "jurisdicao", "ementa", "status_vigencia", "keywords", "aliases", "fonte", "path"]:
            if field not in item:
                errors.append(f"manifest.json: item sem campo {field}: {item}")
        if item.get("path") and not (ROOT / str(item["path"])).exists():
            errors.append(f"manifest.json aponta para arquivo inexistente: {item['path']}")

    if errors:
        for error in errors:
            print(f"ERRO: {error}", file=sys.stderr)
        return 1
    print(f"Base válida: {len(manifest)} normas publicadas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
