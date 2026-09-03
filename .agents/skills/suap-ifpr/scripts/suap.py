#!/usr/bin/env python3
"""Consultas rápidas, somente leitura, ao SUAP/IFPR."""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse

from suap_client import SkillError, SuapClient, SuapHTTPError, clean_text


PROFESSOR_LIST_PATH = "/admin/edu/professor/"
TUTORIAL_TITLE = "9 – Secretarias Acadêmicas: Pesquisa dados docentes"
TUTORIAL_URL = (
    "https://ifpr.edu.br/tutoriais/base-conhecimento/"
    "9-secretarias-academicas-pesquisa-dados-docentes-dga-adilson-23-10-2024/"
)
MENU_PATH = "Ensino > Alunos e Professores > Professores > Visualizar > Diários e Cursos Lecionados"
VOID_TAGS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}


def normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    without_marks = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(without_marks.casefold().split())


@dataclass
class Node:
    tag: str
    attrs: dict[str, str] = field(default_factory=dict)
    children: list["Node | str"] = field(default_factory=list)

    def text(self) -> str:
        parts: list[str] = []

        def visit(node: Node) -> None:
            for child in node.children:
                if isinstance(child, str):
                    parts.append(child)
                else:
                    visit(child)

        visit(self)
        return clean_text(" ".join(parts))

    def descendants(self, tag: str | None = None) -> Iterable["Node"]:
        for child in self.children:
            if not isinstance(child, Node):
                continue
            if tag is None or child.tag == tag:
                yield child
            yield from child.descendants(tag)

    def first(self, tag: str | None = None, **attrs: str) -> "Node | None":
        for node in self.descendants(tag):
            if all(node.attrs.get(key) == value for key, value in attrs.items()):
                return node
        return None


class TreeParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = Node("document")
        self.stack = [self.root]

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        node = Node(tag.casefold(), {key: value or "" for key, value in attrs})
        self.stack[-1].children.append(node)
        if node.tag not in VOID_TAGS:
            self.stack.append(node)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag.casefold() not in VOID_TAGS:
            self.stack.pop()

    def handle_endtag(self, tag: str) -> None:
        tag = tag.casefold()
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                return

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.stack[-1].children.append(data)


def parse_html(document: str) -> Node:
    parser = TreeParser()
    parser.feed(document)
    parser.close()
    return parser.root


def direct_cells(row: Node) -> list[Node]:
    return [child for child in row.children if isinstance(child, Node) and child.tag in {"th", "td"}]


def links(node: Node) -> list[str]:
    return [anchor.attrs["href"] for anchor in node.descendants("a") if anchor.attrs.get("href")]


def labeled_value(text: str, label: str, following_labels: Iterable[str]) -> str | None:
    stops = "|".join(re.escape(value) for value in following_labels)
    pattern = rf"\b{re.escape(label)}:\s*(.*?)(?=\s+(?:{stops}):|$)"
    match = re.search(pattern, text, flags=re.IGNORECASE)
    return clean_text(match.group(1)) if match else None


def parse_professor_candidates(document: str) -> list[dict[str, str]]:
    root = parse_html(document)
    candidates: list[dict[str, str]] = []
    for row in root.descendants("tr"):
        profile_path = next(
            (
                urlparse(href).path
                for href in links(row)
                if re.fullmatch(r"/edu/professor/\d+/", urlparse(href).path)
            ),
            None,
        )
        if profile_path is None:
            continue
        cells = direct_cells(row)
        row_text = row.text()
        nome = labeled_value(row_text, "Nome", ("CPF", "Setor", "E-mail"))
        if not nome:
            continue
        setor = labeled_value(row_text, "Setor", ("E-mail",))
        campus = cells[-1].text() if cells and cells[-1].tag == "td" else None
        candidates.append(
            {
                "nome": nome,
                "setor_suap": setor or "",
                "campus": campus or "",
                "profile_path": profile_path,
            }
        )
    return candidates


def select_exact_candidate(
    candidates: list[dict[str, str]], requested_name: str, campus: str | None = None
) -> dict[str, str]:
    exact = [item for item in candidates if normalize(item["nome"]) == normalize(requested_name)]
    if campus and len(exact) > 1:
        unit = normalize(campus)
        exact = [
            item
            for item in exact
            if unit in normalize(f"{item['campus']} {item['setor_suap']}")
        ]
    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        descriptions = "; ".join(
            f"{item['nome']} ({item['campus'] or item['setor_suap'] or 'unidade não informada'})"
            for item in exact[:8]
        )
        raise SkillError(
            "Há mais de um docente com esse nome. Refine a unidade antes de consultar: " + descriptions
        )
    if campus:
        raise SkillError(f"Nenhum homônimo corresponde à unidade informada: {campus}.")
    if candidates:
        names = ", ".join(item["nome"] for item in candidates[:8])
        raise SkillError(f"Nenhuma correspondência exata. Resultados próximos: {names}.")
    raise SkillError("Nenhum docente foi localizado para o nome informado.")


def available_periods(root: Node) -> list[str]:
    selector = root.first("select", name="ano-periodo")
    if selector is None:
        return []
    periods = [option.text() for option in selector.descendants("option")]
    valid = {value for value in periods if re.fullmatch(r"\d{4}\.[12]", value)}
    return sorted(valid, key=lambda value: tuple(map(int, value.split("."))), reverse=True)


def choose_period(periods: list[str], ano: int | None, periodo: int | None) -> tuple[str, str]:
    if (ano is None) != (periodo is None):
        raise SkillError("Informe --ano e --periodo juntos, ou omita ambos.")
    if ano is not None and periodo is not None:
        requested = f"{ano}.{periodo}"
        if periods and requested not in periods:
            raise SkillError(
                f"O período {requested} não está disponível na ficha. Opções: {', '.join(periods)}."
            )
        return requested, "informado pelo usuário"
    if not periods:
        raise SkillError("O SUAP não informou períodos letivos disponíveis para esse docente.")
    return periods[0], "mais recente disponível na ficha"


def field_pairs(root: Node) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for dl in root.descendants("dl"):
        terms = list(dl.descendants("dt"))
        definitions = list(dl.descendants("dd"))
        pairs.extend((term.text().rstrip(":"), definition.text()) for term, definition in zip(terms, definitions))
    return pairs


def first_field(pairs: list[tuple[str, str]], names: Iterable[str]) -> str | None:
    normalized = {normalize(name) for name in names}
    for key, value in pairs:
        if normalize(key) in normalized and value and value != "-":
            return value
    return None


def parse_courses(root: Node) -> list[str]:
    section = root.first("div", id="cursos-lecionados")
    if section is None:
        return []
    values = [item.text() for item in section.descendants("li") if item.text()]
    if not values:
        values = [cell.text() for cell in section.descendants("td") if cell.text()]
    return list(dict.fromkeys(values))


def discipline_name(description: str) -> str:
    parts = [part.strip() for part in description.split(" - ") if part.strip()]
    return parts[-2] if len(parts) >= 3 else description


def course_for_diary(description: str, turma: str, courses: list[str]) -> str | None:
    turma_parts = turma.split(".")
    if len(turma_parts) >= 3:
        course_code = turma_parts[2]
        matched = next((course for course in courses if course.startswith(f"{course_code} - ")), None)
        if matched:
            return matched
    parts = [part.strip() for part in description.split(" - ") if part.strip()]
    if len(parts) < 2:
        return None
    code = parts[1].split(".", 1)[0]
    return next((course for course in courses if course.startswith(f"{code} - ")), code or None)


def parse_disciplines(root: Node, courses: list[str]) -> list[dict[str, str]]:
    section = root.first("div", id="diarios")
    if section is None:
        return []
    disciplines: list[dict[str, str]] = []
    for table in section.descendants("table"):
        rows = list(table.descendants("tr"))
        if not rows:
            continue
        headers = [normalize(cell.text()) for cell in direct_cells(rows[0])]
        if "diario" not in headers or "turma" not in headers:
            continue
        for row in rows[1:]:
            cells = direct_cells(row)
            if len(cells) != len(headers):
                continue
            values = dict(zip(headers, (cell.text() for cell in cells)))
            if normalize(values.get("ativo", "sim")) != "sim":
                continue
            description = values.get("diario", "")
            turma = values.get("turma", "")
            item = {
                "disciplina": discipline_name(description),
                "curso": course_for_diary(description, turma, courses) or "não identificado",
            }
            if item not in disciplines:
                disciplines.append(item)
    return disciplines


def employee_profile_path(root: Node) -> str | None:
    content = root.first("main", id="content")
    if content is None:
        return None
    paths = list(
        dict.fromkeys(
            urlparse(href).path
            for href in links(content)
            if re.fullmatch(r"/rh/servidor/\d+/", urlparse(href).path)
        )
    )
    return paths[0] if len(paths) == 1 else None


def employee_profile_name(document: str) -> str | None:
    root = parse_html(document)
    content = root.first("main", id="content")
    if content is None:
        return None
    name = first_field(field_pairs(content), ("Nome", "Nome Completo"))
    if name:
        return name
    for heading in content.descendants("h2"):
        match = re.fullmatch(r"(.+?)\s+\([^()]+\)", heading.text())
        if match:
            return clean_text(match.group(1))
    return None


def parse_employment(document: str) -> dict[str, str | None]:
    root = parse_html(document)
    content = root.first("main", id="content")
    pairs = field_pairs(content or root)
    cargo = first_field(pairs, ("Cargo",))
    if cargo:
        cargo = re.sub(r"\s+-\s+\d+\s*$", "", cargo)
    return {
        "cargo": cargo,
        "funcao": first_field(pairs, ("Função", "Função Atual")),
        "lotacao": first_field(pairs, ("Lotação SIAPE", "Lotação")),
        "setor_exercicio": first_field(pairs, ("Setor de Exercício", "Setor SUAP")),
    }


def consultar_professor(
    nome: str,
    ano: int | None = None,
    periodo: int | None = None,
    campus: str | None = None,
    *,
    client: SuapClient,
) -> dict[str, object]:
    _, listing = client.get_text(PROFESSOR_LIST_PATH, {"q": nome})
    candidate = select_exact_candidate(parse_professor_candidates(listing), nome, campus)

    _, initial_document = client.get_text(candidate["profile_path"])
    initial_root = parse_html(initial_document)
    selected_period, period_reason = choose_period(available_periods(initial_root), ano, periodo)
    _, profile_document = client.get_text(candidate["profile_path"], {"ano-periodo": selected_period})
    profile_root = parse_html(profile_document)

    courses = parse_courses(profile_root)
    warnings: list[str] = []
    employment: dict[str, str | None] = {
        "cargo": None,
        "funcao": None,
        "lotacao": None,
        "setor_exercicio": None,
    }
    employee_path = employee_profile_path(profile_root)
    if employee_path:
        try:
            _, employee_document = client.get_text(employee_path)
            employee_name = employee_profile_name(employee_document)
            if employee_name and normalize(employee_name) == normalize(candidate["nome"]):
                employment = parse_employment(employee_document)
            else:
                warnings.append(
                    "Os dados funcionais foram descartados porque o SUAP não comprovou que a "
                    "página funcional pertence à pessoa pesquisada."
                )
        except SuapHTTPError as exc:
            if exc.status not in {401, 403}:
                raise
            warnings.append(
                "O perfil atual não tem permissão para consultar os dados funcionais; "
                "isso não significa que o docente não possua cargo ou função."
            )
    else:
        warnings.append(
            "A ficha docente não apresentou um vínculo funcional único dentro do conteúdo da pessoa pesquisada."
        )

    disciplines = parse_disciplines(profile_root, courses)
    if not disciplines:
        warnings.append(
            f"Nenhum diário ativo foi encontrado em {selected_period}; isso pode refletir ausência "
            "de oferta ou limitação de permissão."
        )

    return {
        "nome": candidate["nome"],
        "cargo": employment["cargo"],
        "funcao": employment["funcao"],
        "lotacao": employment["lotacao"],
        "setor_exercicio": employment["setor_exercicio"],
        "setor_suap": candidate["setor_suap"] or None,
        "campus_cadastrado": candidate["campus"] or None,
        "periodo_letivo": selected_period,
        "criterio_periodo": period_reason,
        "cursos_lecionados": courses,
        "escopo_cursos": "relação exibida na ficha docente do SUAP, sem filtro de período",
        "disciplinas_ativas": disciplines,
        "avisos": warnings,
        "fonte": {
            "tutorial": TUTORIAL_TITLE,
            "tutorial_url": TUTORIAL_URL,
            "menu": MENU_PATH,
            "paginas_suap": [
                "/admin/edu/professor/",
                "/edu/professor/<id>/",
                "/rh/servidor/<id>/ (quando permitido)",
            ],
        },
    }


def render_text(result: dict[str, object]) -> str:
    lines = [
        f"Professor(a): {result['nome']}",
        f"Cargo: {result['cargo'] or 'não disponível para o perfil atual'}",
        f"Função: {result['funcao'] or 'não informada'}",
        f"Lotação: {result['lotacao'] or result['setor_suap'] or 'não informada'}",
        f"Setor de exercício: {result['setor_exercicio'] or result['setor_suap'] or 'não informado'}",
        f"Campus cadastrado: {result['campus_cadastrado'] or 'não informado'}",
        f"Período letivo das disciplinas: {result['periodo_letivo']} ({result['criterio_periodo']})",
        "",
        "Cursos lecionados (relação da ficha, sem filtro de período):",
    ]
    courses = result["cursos_lecionados"]
    if courses:
        lines.extend(f"- {course}" for course in courses)  # type: ignore[union-attr]
    else:
        lines.append("- nenhum curso visível")

    lines.extend(["", f"Disciplinas ativas em {result['periodo_letivo']}:"])
    disciplines = result["disciplinas_ativas"]
    if disciplines:
        for discipline in disciplines:  # type: ignore[union-attr]
            lines.append(f"- {discipline['disciplina']} — {discipline['curso']}")
    else:
        lines.append("- nenhuma disciplina ativa visível")

    warnings = result["avisos"]
    if warnings:
        lines.extend(["", "Avisos:"])
        lines.extend(f"- {warning}" for warning in warnings)  # type: ignore[union-attr]

    source = result["fonte"]  # type: ignore[assignment]
    lines.extend(
        [
            "",
            f"Tutorial oficial: {source['tutorial']} — {source['tutorial_url']}",
            f"Caminho observado: {source['menu']}",
        ]
    )
    return "\n".join(lines)


def command_professor(args: argparse.Namespace) -> int:
    client = SuapClient.from_config(args.env_file)
    result = consultar_professor(
        args.nome,
        args.ano,
        args.periodo,
        args.campus,
        client=client,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(render_text(result))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=None, help="arquivo .env.local alternativo")
    subparsers = parser.add_subparsers(dest="command", required=True)
    professor = subparsers.add_parser("professor", help="consulta cargo, cursos e disciplinas")
    professor.add_argument("nome", help="nome completo do docente")
    professor.add_argument("--ano", type=int, help="ano letivo; use junto com --periodo")
    professor.add_argument("--periodo", type=int, choices=(1, 2), help="período letivo")
    professor.add_argument("--campus", help="unidade para desambiguar docentes homônimos")
    professor.add_argument("--json", action="store_true", help="emite saída estruturada em JSON")
    professor.set_defaults(handler=command_professor)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "professor" and not args.nome.strip():
        parser.error("o nome não pode ser vazio")
    try:
        return int(args.handler(args))
    except SkillError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
