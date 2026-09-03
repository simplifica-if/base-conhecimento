#!/usr/bin/env python3
"""Indexa tutoriais oficiais do SUAP/IFPR e valida a configuração local."""

from __future__ import annotations

import argparse
import json
import os
import sys
import unicodedata
from pathlib import Path
from typing import Any, Callable, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from suap_client import (
    SkillError,
    SuapClient,
    clean_text,
    extract_title,
    require_config,
    resolve_config,
)


SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_INDEX = SKILL_DIR / "references" / "tutoriais.json"
DOCS_PREFIX = "https://ifpr.edu.br/tutoriais/"
DOCS_API = f"{DOCS_PREFIX}wp-json/wp/v2"
DOCS_CATEGORY_URL = f"{DOCS_PREFIX}base-conhecimento/categoria/suap/"
ROOT_CATEGORY_ID = 311
DEFAULT_AUTH_CHECK_PATH = "/edu/cursocampus/1/?tab=dados_gerais"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 Chrome/140 Safari/537.36"
)
def normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    without_marks = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(without_marks.casefold().split())


def request_json(url: str, timeout: int = 30) -> Any:
    request = Request(url, headers={"Accept": "application/json", "User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise SkillError(f"Falha ao consultar a documentação oficial: {exc}") from exc


def fetch_paginated(
    page_loader: Callable[[int, int], list[dict[str, Any]]], per_page: int = 100
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    page = 1
    while True:
        batch = page_loader(page, per_page)
        if not isinstance(batch, list):
            raise SkillError("A API oficial retornou uma coleção inválida.")
        items.extend(batch)
        if len(batch) < per_page:
            return items
        page += 1


def fetch_collection(endpoint: str, params: dict[str, str] | None = None) -> list[dict[str, Any]]:
    base_params = dict(params or {})

    def load_page(page: int, per_page: int) -> list[dict[str, Any]]:
        query = dict(base_params)
        query.update({"page": str(page), "per_page": str(per_page)})
        result = request_json(f"{DOCS_API}/{endpoint}?{urlencode(query)}")
        if not isinstance(result, list):
            raise SkillError("A API oficial retornou uma resposta inválida.")
        return result

    return fetch_paginated(load_page)


def descendant_ids(categories: Iterable[dict[str, Any]], root_id: int) -> set[int]:
    children: dict[int, list[int]] = {}
    for category in categories:
        children.setdefault(int(category["parent"]), []).append(int(category["id"]))

    found = {root_id}
    pending = [root_id]
    while pending:
        parent = pending.pop()
        for child in children.get(parent, []):
            if child not in found:
                found.add(child)
                pending.append(child)
    return found


def category_path(category_id: int, by_id: dict[int, dict[str, Any]], root_id: int) -> list[str]:
    path: list[str] = []
    seen: set[int] = set()
    current = category_id
    while current:
        if current in seen:
            raise SkillError(f"Ciclo detectado na categoria {current}.")
        seen.add(current)
        category = by_id.get(current)
        if category is None:
            raise SkillError(f"Categoria referenciada não encontrada: {current}.")
        path.append(clean_text(str(category["name"])))
        if current == root_id:
            return list(reversed(path))
        current = int(category["parent"])
    raise SkillError(f"Categoria {category_id} não pertence à árvore SUAP.")


def build_index(
    categories: list[dict[str, Any]], posts: list[dict[str, Any]], root_id: int = ROOT_CATEGORY_ID
) -> dict[str, Any]:
    subtree = descendant_ids(categories, root_id)
    by_id = {int(category["id"]): category for category in categories if int(category["id"]) in subtree}
    if root_id not in by_id:
        raise SkillError("A categoria raiz SUAP não foi encontrada.")

    indexed_categories = []
    for category_id, category in by_id.items():
        indexed_categories.append(
            {
                "id": category_id,
                "parent_id": int(category["parent"]),
                "name": clean_text(str(category["name"])),
                "slug": str(category["slug"]),
                "path": category_path(category_id, by_id, root_id),
            }
        )
    indexed_categories.sort(key=lambda item: (normalize(" > ".join(item["path"])), item["id"]))

    tutorials = []
    for post in posts:
        post_category_ids = sorted(
            {int(value) for value in post.get("epkb_post_type_1_category", []) if int(value) in subtree}
        )
        paths = sorted(
            {tuple(category_path(category_id, by_id, root_id)) for category_id in post_category_ids},
            key=lambda value: normalize(" > ".join(value)),
        )
        tutorials.append(
            {
                "id": int(post["id"]),
                "title": clean_text(str(post["title"]["rendered"])),
                "slug": str(post["slug"]),
                "url": str(post["link"]),
                "modified": str(post["modified"]),
                "category_ids": post_category_ids,
                "paths": [list(path) for path in paths],
            }
        )
    tutorials.sort(key=lambda item: (normalize(item["title"]), item["id"]))

    modified_values = [item["modified"] for item in tutorials]
    return {
        "schema_version": 1,
        "source": {
            "category_url": DOCS_CATEGORY_URL,
            "api_url": DOCS_API,
            "root_category_id": root_id,
            "source_updated_at": max(modified_values, default=None),
            "category_count": len(indexed_categories),
            "tutorial_count": len(tutorials),
        },
        "categories": indexed_categories,
        "tutorials": tutorials,
    }


def collect_live_index() -> dict[str, Any]:
    categories = fetch_collection("epkb_post_type_1_category")
    subtree = descendant_ids(categories, ROOT_CATEGORY_ID)
    posts = fetch_collection(
        "epkb_post_type_1",
        {
            "_fields": "id,slug,title,link,modified,epkb_post_type_1_category",
            "epkb_post_type_1_category": ",".join(str(value) for value in sorted(subtree)),
        },
    )
    return build_index(categories, posts)


def load_index(path: Path) -> dict[str, Any]:
    try:
        result = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SkillError(f"Índice não encontrado: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SkillError(f"Índice JSON inválido: {exc}") from exc
    if not isinstance(result, dict):
        raise SkillError("Índice JSON inválido.")
    return result


def validation_errors(index: dict[str, Any], secrets: Iterable[str] = ()) -> list[str]:
    errors: list[str] = []
    expected_top = {"schema_version", "source", "categories", "tutorials"}
    if set(index) != expected_top:
        errors.append("chaves de primeiro nível inválidas")
    if index.get("schema_version") != 1:
        errors.append("schema_version deve ser 1")

    source = index.get("source")
    categories = index.get("categories")
    tutorials = index.get("tutorials")
    if not isinstance(source, dict) or not isinstance(categories, list) or not isinstance(tutorials, list):
        return errors + ["source, categories ou tutorials possuem tipo inválido"]

    expected_source = {
        "category_url",
        "api_url",
        "root_category_id",
        "source_updated_at",
        "category_count",
        "tutorial_count",
    }
    if set(source) != expected_source:
        errors.append("metadados de source inválidos")
    if source.get("category_url") != DOCS_CATEGORY_URL or source.get("api_url") != DOCS_API:
        errors.append("fonte oficial inválida")
    if source.get("root_category_id") != ROOT_CATEGORY_ID:
        errors.append("categoria raiz inválida")
    if source.get("category_count") != len(categories):
        errors.append("category_count divergente")
    if source.get("tutorial_count") != len(tutorials):
        errors.append("tutorial_count divergente")

    category_ids: set[int] = set()
    expected_category_keys = {"id", "parent_id", "name", "slug", "path"}
    for category in categories:
        if not isinstance(category, dict) or set(category) != expected_category_keys:
            errors.append("categoria com estrutura inválida")
            continue
        category_id = category.get("id")
        if not isinstance(category_id, int) or category_id in category_ids:
            errors.append("ID de categoria inválido ou duplicado")
        else:
            category_ids.add(category_id)
        path = category.get("path")
        if not isinstance(path, list) or not path or path[0] != "SUAP":
            errors.append(f"caminho inválido na categoria {category_id}")

    expected_tutorial_keys = {"id", "title", "slug", "url", "modified", "category_ids", "paths"}
    tutorial_ids: set[int] = set()
    for tutorial in tutorials:
        if not isinstance(tutorial, dict) or set(tutorial) != expected_tutorial_keys:
            errors.append("tutorial com estrutura inválida ou conteúdo indevido")
            continue
        tutorial_id = tutorial.get("id")
        if not isinstance(tutorial_id, int) or tutorial_id in tutorial_ids:
            errors.append("ID de tutorial inválido ou duplicado")
        else:
            tutorial_ids.add(tutorial_id)
        url = tutorial.get("url")
        if not isinstance(url, str) or not url.startswith(DOCS_PREFIX):
            errors.append(f"URL externa no tutorial {tutorial_id}")
        ids = tutorial.get("category_ids")
        if not isinstance(ids, list) or any(value not in category_ids for value in ids):
            errors.append(f"categoria desconhecida no tutorial {tutorial_id}")
        paths = tutorial.get("paths")
        if not isinstance(paths, list) or any(not path or path[0] != "SUAP" for path in paths):
            errors.append(f"caminho inválido no tutorial {tutorial_id}")

    if categories != sorted(categories, key=lambda item: (normalize(" > ".join(item["path"])), item["id"])):
        errors.append("categorias fora da ordenação determinística")
    if tutorials != sorted(tutorials, key=lambda item: (normalize(item["title"]), item["id"])):
        errors.append("tutoriais fora da ordenação determinística")

    serialized = json.dumps(index, ensure_ascii=False)
    for secret in secrets:
        if secret and secret in serialized:
            errors.append("o índice contém um valor de credencial")
            break
    return errors


def auth_check(path: str, env_file: Path | None = None) -> tuple[str, str]:
    client = SuapClient.from_config(env_file)
    final_url, document = client.get_text(path)
    return urlparse(final_url).path, extract_title(document)


def write_index(path: Path, index: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(index, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    os.replace(temporary, path)


def command_update(args: argparse.Namespace) -> int:
    index = collect_live_index()
    secrets = require_config(args.env_file).values() if args.check_secrets else ()
    errors = validation_errors(index, secrets)
    if errors:
        raise SkillError("Índice obtido da fonte falhou na validação: " + "; ".join(errors))
    write_index(args.index, index)
    print(
        f"Índice atualizado: {index['source']['tutorial_count']} tutoriais em "
        f"{index['source']['category_count']} categorias."
    )
    return 0


def search_tutorials(index: dict[str, Any], terms: Iterable[str]) -> list[dict[str, Any]]:
    query = normalize(" ".join(terms))
    tokens = query.split()
    ranked: list[tuple[int, dict[str, Any]]] = []
    for tutorial in index["tutorials"]:
        haystack = normalize(
            " ".join(
                [tutorial["title"], tutorial["slug"]]
                + [" ".join(path) for path in tutorial["paths"]]
            )
        )
        matched_tokens = sum(token in haystack for token in tokens)
        if matched_tokens:
            exact_bonus = 100 if query and query in haystack else 0
            ranked.append((exact_bonus + matched_tokens, tutorial))
    ranked.sort(key=lambda item: (-item[0], normalize(item[1]["title"]), item[1]["id"]))
    return [tutorial for _, tutorial in ranked]


def command_search(args: argparse.Namespace) -> int:
    index = load_index(args.index)
    errors = validation_errors(index)
    if errors:
        raise SkillError("Índice inválido: " + "; ".join(errors))
    matches = search_tutorials(index, args.terms)
    limited = matches[: args.limit]
    if args.json:
        print(json.dumps(limited, ensure_ascii=False, indent=2))
    elif not limited:
        print("Nenhum tutorial encontrado no índice local.")
    else:
        for tutorial in limited:
            paths = " | ".join(" > ".join(path) for path in tutorial["paths"])
            print(f"{tutorial['title']}\n  {paths}\n  {tutorial['url']}\n  Atualizado: {tutorial['modified']}")
    return 0 if matches else 1


def command_validate(args: argparse.Namespace) -> int:
    index = load_index(args.index)
    config = resolve_config(args.env_file)
    errors = validation_errors(index, config.values())
    if errors:
        raise SkillError("Falha na validação: " + "; ".join(errors))
    print(
        f"Índice válido: {len(index['tutorials'])} tutoriais em "
        f"{len(index['categories'])} categorias; nenhum valor de credencial detectado."
    )
    return 0


def command_config(args: argparse.Namespace) -> int:
    require_config(args.env_file)
    print("Configuração SUAP pronta: SUAP_USUARIO e SUAP_SENHA estão definidos.")
    return 0


def command_auth_check(args: argparse.Namespace) -> int:
    path, title = auth_check(args.path, args.env_file)
    print("Autenticação SUAP confirmada; cookies mantidos somente em memória.")
    print(f"Página consultada: {title} ({path})")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX, help="caminho do índice JSON")
    parser.add_argument("--env-file", type=Path, default=None, help="arquivo .env.local alternativo")
    subparsers = parser.add_subparsers(dest="command", required=True)

    update = subparsers.add_parser("atualizar", help="regenera o índice pela fonte oficial")
    update.add_argument(
        "--check-secrets",
        action="store_true",
        help="também confirma que os valores configurados não aparecem no índice",
    )
    update.set_defaults(handler=command_update)

    search = subparsers.add_parser("buscar", help="pesquisa o índice local")
    search.add_argument("terms", nargs="+", help="termos de busca")
    search.add_argument("--json", action="store_true", help="emite resultados em JSON")
    search.add_argument("--limit", type=int, default=20, help="máximo de resultados")
    search.set_defaults(handler=command_search)

    validate = subparsers.add_parser("validar", help="valida o índice local")
    validate.set_defaults(handler=command_validate)

    config = subparsers.add_parser("config", help="confere a presença das credenciais")
    config.set_defaults(handler=command_config)

    auth = subparsers.add_parser("auth-check", help="faz smoke test autenticado somente leitura")
    auth.add_argument("--path", default=DEFAULT_AUTH_CHECK_PATH, help="caminho HTTPS dentro do SUAP")
    auth.set_defaults(handler=command_auth_check)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "buscar" and args.limit < 1:
        parser.error("--limit deve ser maior que zero")
    try:
        return int(args.handler(args))
    except SkillError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
