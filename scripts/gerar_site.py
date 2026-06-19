#!/usr/bin/env python3
"""Gera a saída publicável em site/ a partir de base-conhecimento/."""

from __future__ import annotations

import argparse
import filecmp
import shutil
import sys
import tempfile
from pathlib import Path

from base_utils import BASE_ROOT, SITE_ROOT


IGNORED_NAMES = {".DS_Store", "__pycache__", ".pytest_cache"}


def ignore_names(_directory: str, names: list[str]) -> set[str]:
    return {name for name in names if name in IGNORED_NAMES or name.endswith(".pyc")}


def render_site(destination: Path) -> None:
    if not BASE_ROOT.exists():
        raise FileNotFoundError(f"Diretório da base não encontrado: {BASE_ROOT}")
    if destination.resolve() == BASE_ROOT.resolve():
        raise ValueError("Destino do site não pode ser o mesmo diretório da base")
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(BASE_ROOT, destination, ignore=ignore_names)


def compare_dirs(expected: Path, actual: Path) -> list[str]:
    errors: list[str] = []
    comparison = filecmp.dircmp(expected, actual)
    for name in comparison.left_only:
        errors.append(f"ausente em site/: {expected.joinpath(name).relative_to(expected)}")
    for name in comparison.right_only:
        errors.append(f"extra em site/: {actual.joinpath(name).relative_to(actual)}")
    for name in comparison.diff_files:
        errors.append(f"conteúdo divergente: {name}")
    for subdir in comparison.common_dirs:
        child_expected = expected / subdir
        child_actual = actual / subdir
        for error in compare_dirs(child_expected, child_actual):
            errors.append(f"{subdir}/{error}")
    return errors


def check_site() -> list[str]:
    if not SITE_ROOT.exists():
        return [f"site/ não existe; gere com {Path('python3 scripts/gerar_site.py')}"]
    with tempfile.TemporaryDirectory() as tmp:
        expected = Path(tmp) / "site"
        render_site(expected)
        return compare_dirs(expected, SITE_ROOT)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="verifica se site/ está atualizado")
    args = parser.parse_args()

    if args.check:
        errors = check_site()
        if errors:
            for error in errors:
                print(f"ERRO: {error}", file=sys.stderr)
            return 1
        print(f"site/ atualizado a partir de {BASE_ROOT.name}/.")
        return 0

    render_site(SITE_ROOT)
    print(f"site/ gerado a partir de {BASE_ROOT.name}/.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
