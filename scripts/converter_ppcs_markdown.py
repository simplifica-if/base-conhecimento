#!/usr/bin/env python3
"""Converte PPCs referenciados nos JSONs de campus para Markdown.

Dependência opcional:
    uv venv
    uv pip install -r requirements-ppc.txt
"""

from __future__ import annotations

import argparse
import json
import re
import tempfile
from datetime import date
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen

from base_utils import INSTITUCIONAL_ROOT, ROOT


USER_AGENT = "simplifica-if-ppc-converter/1.0"


def google_drive_download_url(url: str) -> str:
    match = re.search(r"/file/d/([^/]+)/", url)
    if not match:
        return url
    return f"https://drive.google.com/uc?export=download&id={match.group(1)}"


def suffix_for_url(url: str, content_type: str | None) -> str:
    parsed = urlparse(url)
    path = unquote(parsed.path)
    suffix = Path(path).suffix
    if suffix:
        return suffix
    if content_type and "pdf" in content_type.lower():
        return ".pdf"
    return ".bin"


def download_source(url: str, tmpdir: Path) -> Path:
    source_url = google_drive_download_url(url)
    request = Request(source_url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=60) as response:
        content = response.read()
        suffix = suffix_for_url(response.geturl(), response.headers.get("Content-Type"))
    source_path = tmpdir / f"ppc{suffix}"
    source_path.write_bytes(content)
    return source_path


def convert_file(source_path: Path, force_ocr: bool = False) -> str:
    try:
        import pymupdf4llm
    except ImportError as exc:
        raise SystemExit("Instale as dependências opcionais com: uv venv && uv pip install -r requirements-ppc.txt") from exc

    return pymupdf4llm.to_markdown(str(source_path), force_ocr=force_ocr, use_ocr=True)


def converter_version() -> str | None:
    try:
        return version("pymupdf4llm")
    except PackageNotFoundError:
        return None


def iter_campus_paths(campus_filter: str | None) -> list[Path]:
    campi_root = INSTITUCIONAL_ROOT / "ifpr" / "campi"
    if campus_filter:
        return [campi_root / f"{campus_filter}.json"]
    return sorted(path for path in campi_root.glob("*.json") if path.name != "index.json")


def should_convert(curso: dict[str, object], curso_filter: str | None, force: bool) -> bool:
    if curso_filter and curso.get("id") != curso_filter:
        return False
    ppc = curso.get("ppc")
    if not isinstance(ppc, dict):
        return False
    conversao = ppc.get("conversao")
    if force:
        return True
    return not isinstance(conversao, dict) or conversao.get("status") != "convertido"


def convert_ppcs(campus_path: Path, curso_filter: str | None, force: bool, force_ocr: bool, dry_run: bool) -> int:
    data = json.loads(campus_path.read_text(encoding="utf-8"))
    campus_id = data.get("id")
    if not isinstance(campus_id, str):
        return 0

    changed = False
    converted = 0
    for curso in data.get("cursos", []):
        if not isinstance(curso, dict) or not should_convert(curso, curso_filter, force):
            continue
        ppc = curso["ppc"]
        if not isinstance(ppc, dict):
            continue
        url = ppc.get("url")
        markdown_path = ppc.get("markdown_path")
        if not isinstance(url, str) or not isinstance(markdown_path, str):
            continue

        target = ROOT / markdown_path
        print(f"{campus_id}/{curso.get('id')}: {url} -> {markdown_path}", flush=True)
        if dry_run:
            converted += 1
            continue

        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory() as tmp:
            source_path = download_source(url, Path(tmp))
            markdown = convert_file(source_path, force_ocr=force_ocr)
        if not markdown.strip():
            if target.exists():
                target.unlink()
            ppc["conversao"] = {
                "ferramenta": "pymupdf4llm",
                "versao_ferramenta": converter_version() or "desconhecida",
                "convertido_em": date.today().isoformat(),
                "status": "erro",
                "mensagem_erro": "Conversão sem texto extraído; provável PDF digitalizado ou baseado em imagens que exige OCR.",
            }
            campus_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"{campus_id}/{curso.get('id')}: sem texto extraído", flush=True)
            converted += 1
            continue
        target.write_text(markdown, encoding="utf-8")
        ppc["conversao"] = {
            "ferramenta": "pymupdf4llm",
            "versao_ferramenta": converter_version() or "desconhecida",
            "convertido_em": date.today().isoformat(),
            "status": "convertido",
        }
        campus_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"{campus_id}/{curso.get('id')}: convertido", flush=True)
        changed = True
        converted += 1

    if changed:
        campus_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return converted


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campus", help="Filtra por id do campus, ex.: colombo")
    parser.add_argument("--curso", help="Filtra por id do curso")
    parser.add_argument("--force", action="store_true", help="Reconverte PPCs já marcados como convertidos")
    parser.add_argument("--force-ocr", action="store_true", help="Força OCR em todas as páginas")
    parser.add_argument("--dry-run", action="store_true", help="Mostra o que seria convertido sem escrever arquivos")
    args = parser.parse_args()

    total = 0
    for campus_path in iter_campus_paths(args.campus):
        if campus_path.exists():
            total += convert_ppcs(campus_path, args.curso, args.force, args.force_ocr, args.dry_run)
    print(f"PPCs processados: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
