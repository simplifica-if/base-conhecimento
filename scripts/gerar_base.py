#!/usr/bin/env python3
"""Gera manifest.json e a tabela do README a partir de normas/*.md."""

from __future__ import annotations

import argparse
import sys

from base_utils import MANIFEST_PATH, NORMAS_ROOT, README_PATH, build_manifest, manifest_json


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


def readme_text(manifest: list[dict[str, object]]) -> str:
    text = README_PATH.read_text(encoding="utf-8")
    start = text.index("| Documento | Tipo | Ano | Assunto |")
    end = text.index("\n\n## Manutenção", start)
    return text[:start] + readme_table(manifest) + text[end:]


def check_current(manifest: list[dict[str, object]]) -> list[str]:
    errors: list[str] = []
    expected_manifest = manifest_json(manifest)
    if MANIFEST_PATH.read_text(encoding="utf-8") != expected_manifest:
        errors.append("manifest.json está desatualizado")
    if README_PATH.read_text(encoding="utf-8") != readme_text(manifest):
        errors.append("README.md está desatualizado")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="verifica se os arquivos gerados estão atualizados")
    args = parser.parse_args()

    if not NORMAS_ROOT.exists():
        print(f"Diretório de normas não encontrado: {NORMAS_ROOT}", file=sys.stderr)
        return 1

    manifest = build_manifest()
    if args.check:
        errors = check_current(manifest)
        if errors:
            for error in errors:
                print(f"ERRO: {error}", file=sys.stderr)
            return 1
        print(f"Base atualizada: {len(manifest)} normas publicadas.")
        return 0

    MANIFEST_PATH.write_text(manifest_json(manifest), encoding="utf-8")
    README_PATH.write_text(readme_text(manifest), encoding="utf-8")
    print(f"Base gerada: {len(manifest)} normas publicadas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
