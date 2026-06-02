#!/usr/bin/env python3
"""Exporta a base operacional do Notion para os JSONs públicos."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

from base_utils import CAMPI_INDEX_PATH, PROCESSOS_SELETIVOS_INDEX_PATH, PROCESSOS_SELETIVOS_ROOT, ROOT, relative
from notion_client import NotionClient, NotionError


CONFIG_PATH = ROOT / "config" / "notion.json"
CAMPI_ROOT = ROOT / "institucional" / "ifpr" / "campi"
PUBLIC_BASE_URL = "https://simplifica-if.github.io/base-conhecimento/"
CURADORIA_STATUS_ALIASES = {
    "precisa de revisão": "precisa_revisao",
    "precisa de revisao": "precisa_revisao",
    "precisa_revisao": "precisa_revisao",
    "sugerido": "precisa_revisao",
    "revisado": "revisado",
    "inconsistente": "inconsistente",
    "pendente": "pendente",
}
VALID_CURADORIA_STATUS = {"dados_pendentes", "dados_parciais", "dados_curados"}
REQUIRED_DATABASES = {
    "campi",
    "cursos",
    "movimentacoes_cursos",
    "tarefas",
    "processos_seletivos",
    "editais_ingresso",
    "ofertas_ingresso",
}
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
HTTPS_RE = re.compile(r"^https://")


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        raise NotionError("config/notion.json não encontrado. Configure os IDs da base Notion operacional.")
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def validate_config(config: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    parent_page_id = config.get("parent_page_id")
    if not isinstance(parent_page_id, str) or not parent_page_id.strip():
        errors.append("config/notion.json: parent_page_id ausente")
    databases = config.get("databases")
    if not isinstance(databases, dict):
        return ["config/notion.json: databases deve ser objeto"]
    for key in sorted(REQUIRED_DATABASES):
        item = databases.get(key)
        if not isinstance(item, dict):
            errors.append(f"config/notion.json: base ausente: {key}")
            continue
        for field in ["id", "data_source_id", "title"]:
            if not isinstance(item.get(field), str) or not item[field].strip():
                errors.append(f"config/notion.json: databases.{key}.{field} ausente")
    return errors


def write_json(path: Path, data: object, dry_run: bool) -> None:
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    if dry_run:
        print(f"planejado: {relative(path)} ({len(text)} bytes)")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    print(f"exportado: {relative(path)}")


def plain_text(prop: dict[str, Any] | None) -> str:
    if not prop:
        return ""
    prop_type = prop.get("type")
    if prop_type not in {"title", "rich_text"}:
        return ""
    return "".join(part.get("plain_text", "") for part in prop.get(prop_type, []))


def plain_text_from_first_existing(props: dict[str, Any], *names: str) -> str:
    for name in names:
        value = plain_text(props.get(name)).strip()
        if value:
            return value
    return ""


def select_name(prop: dict[str, Any] | None) -> str:
    if not prop:
        return ""
    selected = prop.get("select") or prop.get("status")
    return selected.get("name", "") if selected else ""


def property_label(prop: dict[str, Any] | None) -> str:
    return select_name(prop) or plain_text(prop)


def curadoria_status(prop: dict[str, Any] | None, reviewed_at: str) -> str:
    label = property_label(prop).strip().lower()
    status = CURADORIA_STATUS_ALIASES.get(label)
    if status:
        return status
    return "revisado" if reviewed_at else "precisa_revisao"


def number_value(prop: dict[str, Any] | None) -> int | None:
    if not prop:
        return None
    value = prop.get("number")
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return None


def url_value(prop: dict[str, Any] | None) -> str:
    if not prop:
        return ""
    return prop.get("url") or ""


def url_from_first_existing(props: dict[str, Any], *names: str) -> str:
    for name in names:
        value = url_value(props.get(name)).strip()
        if value:
            return value
    return ""


def checkbox_value(prop: dict[str, Any] | None) -> bool:
    return bool(prop and prop.get("checkbox"))


def date_start(prop: dict[str, Any] | None) -> str:
    if not prop:
        return ""
    value = prop.get("date")
    return value.get("start", "") if value else ""


def json_date(value: str) -> str:
    if not value:
        return ""
    return value[:10]


def json_datetime(value: str) -> str:
    if not value:
        return ""
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return f"{value}T00:00:00-03:00"
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$", value):
        return f"{value}:00-03:00"
    value = re.sub(r"(\d{2}:\d{2}:\d{2})\.\d+", r"\1", value)
    return value


def relation_ids(page: dict[str, Any], property_name: str) -> list[str]:
    prop = page.get("properties", {}).get(property_name, {})
    return [item["id"] for item in prop.get("relation", [])]


def add_if_text(target: dict[str, Any], key: str, value: str) -> None:
    if value:
        target[key] = value


def add_if_number(target: dict[str, Any], key: str, value: int | None) -> None:
    if value is not None:
        target[key] = value


def vagas_text(prop: dict[str, Any] | None) -> str:
    value = plain_text(prop)
    if value:
        return value.strip()
    number = number_value(prop)
    return str(number) if number is not None else ""


def parse_vagas_interval(value: str) -> tuple[int | None, int | None, int | None]:
    text = value.strip()
    match = re.fullmatch(r"(\d{1,4})\s*[-–]\s*(\d{1,4})", text)
    if match:
        minimo, maximo = sorted((int(match.group(1)), int(match.group(2))))
        return maximo, minimo, maximo
    if re.fullmatch(r"\d{1,4}", text):
        quantidade = int(text)
        return quantidade, None, None
    return None, None, None


def markdown_path_from_link(prop: dict[str, Any] | None) -> str:
    value = url_value(prop) or plain_text(prop)
    if value.startswith(PUBLIC_BASE_URL):
        value = value[len(PUBLIC_BASE_URL) :]
    if value.startswith("institucional/ifpr/ppcs/") and value.endswith(".md"):
        return value
    return ""


def page_title(page: dict[str, Any]) -> str:
    props = page.get("properties", {})
    for name in ["Nome", "Título", "Movimentação"]:
        value = plain_text(props.get(name)).strip()
        if value:
            return value
    return page.get("id", "sem-id")


def page_label(kind: str, page: dict[str, Any]) -> str:
    return f"{kind} '{page_title(page)}' ({page.get('id', 'sem-id')})"


def is_slug(value: object) -> bool:
    return isinstance(value, str) and bool(SLUG_RE.fullmatch(value))


def is_https(value: object) -> bool:
    return isinstance(value, str) and bool(HTTPS_RE.match(value))


class Exporter:
    def __init__(self, client: NotionClient, databases: dict[str, Any]) -> None:
        self.client = client
        self.databases = databases
        self.pages: dict[str, list[dict[str, Any]]] = {}

    def data_source_id(self, key: str) -> str:
        try:
            return self.databases[key]["data_source_id"]
        except KeyError as exc:
            raise NotionError(f"Base ausente em config/notion.json: {key}") from exc

    def query_all(self, key: str) -> list[dict[str, Any]]:
        if key in self.pages:
            return self.pages[key]
        data_source_id = self.data_source_id(key)
        results: list[dict[str, Any]] = []
        cursor: str | None = None
        while True:
            payload: dict[str, Any] = {"page_size": 100}
            if cursor:
                payload["start_cursor"] = cursor
            response = self.client.request("POST", f"/data_sources/{data_source_id}/query", payload)
            results.extend(response.get("results", []))
            if not response.get("has_more"):
                self.pages[key] = results
                return results
            cursor = response.get("next_cursor")

    def export(self, dry_run: bool) -> dict[str, int]:
        self.load_all()
        notion_counts = {key: len(value) for key, value in sorted(self.pages.items())}
        print("\nRegistros lidos do Notion:")
        print(json.dumps(notion_counts, ensure_ascii=False, indent=2))

        audit_errors = self.audit_pages()
        if audit_errors:
            print("\nAuditoria do Notion encontrou problemas que impedem exportação confiável:")
            for error in audit_errors:
                print(f"- {error}")
            raise NotionError(f"Auditoria falhou com {len(audit_errors)} problema(s).")

        campi = self.build_campi()
        processos = self.build_processos_seletivos()

        for campus in campi:
            write_json(CAMPI_ROOT / f"{campus['id']}.json", campus, dry_run)
        write_json(CAMPI_INDEX_PATH, self.build_campi_index(campi), dry_run)

        for processo in processos:
            write_json(PROCESSOS_SELETIVOS_ROOT / f"{processo['id']}.json", processo, dry_run)
        write_json(PROCESSOS_SELETIVOS_INDEX_PATH, self.build_processos_index(processos), dry_run)

        return {
            "notion_lidos": notion_counts,
            "campi": len(campi),
            "cursos": sum(len(campus.get("cursos", [])) for campus in campi),
            "processos_seletivos": len(processos),
            "editais": sum(len(processo.get("editais", [])) for processo in processos),
            "ofertas": sum(len(processo.get("ofertas", [])) for processo in processos),
        }

    def load_all(self) -> None:
        for key in sorted(REQUIRED_DATABASES):
            self.query_all(key)

    def audit_pages(self) -> list[str]:
        errors: list[str] = []
        campus_pages = self.pages.get("campi", [])
        course_pages = self.pages.get("cursos", [])
        movimentacao_pages = self.pages.get("movimentacoes_cursos", [])
        processo_pages = self.pages.get("processos_seletivos", [])
        edital_pages = self.pages.get("editais_ingresso", [])
        oferta_pages = self.pages.get("ofertas_ingresso", [])

        campus_ids_by_page = {page["id"]: plain_text(page["properties"].get("campus_id")) for page in campus_pages}
        course_slugs_by_page = {page["id"]: plain_text(page["properties"].get("curso_slug")) for page in course_pages}
        processo_ids_by_page = {
            page["id"]: plain_text(page["properties"].get("processo_seletivo_id")) for page in processo_pages
        }
        edital_ids_by_page = {page["id"]: plain_text(page["properties"].get("edital_id")) for page in edital_pages}

        errors.extend(self.audit_campi(campus_pages))
        errors.extend(self.audit_cursos(course_pages, campus_ids_by_page))
        errors.extend(self.audit_movimentacoes(movimentacao_pages, course_slugs_by_page))
        errors.extend(self.audit_processos_seletivos(processo_pages))
        errors.extend(self.audit_editais(edital_pages, processo_ids_by_page))
        errors.extend(
            self.audit_ofertas(
                oferta_pages,
                campus_ids_by_page,
                course_slugs_by_page,
                processo_ids_by_page,
                edital_ids_by_page,
            )
        )
        return errors

    def audit_campi(self, pages: list[dict[str, Any]]) -> list[str]:
        errors: list[str] = []
        seen: dict[str, str] = {}
        for page in pages:
            props = page["properties"]
            label = page_label("Campus", page)
            campus_id = plain_text(props.get("campus_id"))
            if not is_slug(campus_id):
                errors.append(f"{label}: campus_id ausente ou inválido")
            elif campus_id in seen:
                errors.append(f"{label}: campus_id duplicado com {seen[campus_id]}: {campus_id}")
            else:
                seen[campus_id] = label
            if not plain_text(props.get("Nome")):
                errors.append(f"{label}: Nome ausente")
            for prop_name in ["Site", "Calendário acadêmico"]:
                value = url_value(props.get(prop_name))
                if not is_https(value):
                    errors.append(f"{label}: {prop_name} ausente ou não HTTPS")
        return errors

    def audit_cursos(self, pages: list[dict[str, Any]], campus_ids_by_page: dict[str, str]) -> list[str]:
        errors: list[str] = []
        seen_by_campus: dict[tuple[str, str], str] = {}
        for page in pages:
            props = page["properties"]
            label = page_label("Curso", page)
            slug = plain_text(props.get("curso_slug"))
            if not is_slug(slug):
                errors.append(f"{label}: curso_slug ausente ou inválido")
            if not plain_text(props.get("Nome")):
                errors.append(f"{label}: Nome ausente")
            if not select_name(props.get("Nível")):
                errors.append(f"{label}: Nível ausente")
            if not select_name(props.get("Forma de oferta") or props.get("Tipo de oferta")):
                errors.append(f"{label}: Forma de oferta/Tipo de oferta ausente")

            campus_relations = relation_ids(page, "Campus")
            if len(campus_relations) != 1:
                errors.append(f"{label}: relação Campus deve conter exatamente 1 página")
                continue
            campus_page_id = campus_relations[0]
            campus_id = campus_ids_by_page.get(campus_page_id)
            if not campus_id:
                errors.append(f"{label}: relação Campus aponta para página desconhecida ou sem campus_id: {campus_page_id}")
                continue
            if is_slug(slug):
                key = (campus_id, slug)
                if key in seen_by_campus:
                    errors.append(f"{label}: curso_slug duplicado no campus {campus_id} com {seen_by_campus[key]}: {slug}")
                else:
                    seen_by_campus[key] = label

            ppc_url = url_value(props.get("PPC URL oficial"))
            markdown_path = markdown_path_from_link(props.get("PPC Markdown Link"))
            if ppc_url and not is_https(ppc_url):
                errors.append(f"{label}: PPC URL oficial não HTTPS")
            if markdown_path and is_slug(slug):
                expected = f"institucional/ifpr/ppcs/{campus_id}/{slug}.md"
                if markdown_path != expected:
                    errors.append(f"{label}: PPC Markdown Link esperado {expected}, encontrado {markdown_path}")
        return errors

    def audit_movimentacoes(self, pages: list[dict[str, Any]], course_slugs_by_page: dict[str, str]) -> list[str]:
        errors: list[str] = []
        for page in pages:
            label = page_label("Movimentação de curso", page)
            course_relations = relation_ids(page, "Curso")
            if len(course_relations) > 1:
                errors.append(f"{label}: relação Curso deve conter no máximo 1 página")
            for course_page_id in course_relations:
                if course_page_id not in course_slugs_by_page:
                    errors.append(f"{label}: relação Curso aponta para página desconhecida: {course_page_id}")
            props = page["properties"]
            has_sei = plain_text_from_first_existing(props, "SEI Processo", "Número SEI")
            if has_sei and not course_relations:
                errors.append(f"{label}: SEI Processo informado sem relação Curso")
        return errors

    def audit_processos_seletivos(self, pages: list[dict[str, Any]]) -> list[str]:
        errors: list[str] = []
        seen_ids: dict[str, str] = {}
        seen_years: dict[int, str] = {}
        for page in pages:
            props = page["properties"]
            label = page_label("Processo seletivo", page)
            processo_id = plain_text(props.get("processo_seletivo_id"))
            if not is_slug(processo_id):
                errors.append(f"{label}: processo_seletivo_id ausente ou inválido")
            elif processo_id in seen_ids:
                errors.append(f"{label}: processo_seletivo_id duplicado com {seen_ids[processo_id]}: {processo_id}")
            else:
                seen_ids[processo_id] = label
            if not plain_text(props.get("Nome")):
                errors.append(f"{label}: Nome ausente")
            year = number_value(props.get("Ano de ingresso"))
            if year is None or year < 1900:
                errors.append(f"{label}: Ano de ingresso ausente ou inválido")
            elif year in seen_years:
                errors.append(f"{label}: Ano de ingresso duplicado com {seen_years[year]}: {year}")
            else:
                seen_years[year] = label
            fontes = [line.strip() for line in plain_text(props.get("Fontes")).splitlines() if line.strip()]
            if not fontes:
                errors.append(f"{label}: Fontes ausente")
            for fonte in fontes:
                if not is_https(fonte):
                    errors.append(f"{label}: Fontes contém URL não HTTPS: {fonte}")
        return errors

    def audit_editais(self, pages: list[dict[str, Any]], processo_ids_by_page: dict[str, str]) -> list[str]:
        errors: list[str] = []
        seen: dict[str, str] = {}
        for page in pages:
            props = page["properties"]
            label = page_label("Edital de ingresso", page)
            edital_id = plain_text(props.get("edital_id"))
            if not is_slug(edital_id):
                errors.append(f"{label}: edital_id ausente ou inválido")
            elif edital_id in seen:
                errors.append(f"{label}: edital_id duplicado com {seen[edital_id]}: {edital_id}")
            else:
                seen[edital_id] = label
            if not plain_text(props.get("Título")):
                errors.append(f"{label}: Título ausente")
            if not is_https(url_value(props.get("URL"))):
                errors.append(f"{label}: URL ausente ou não HTTPS")
            processo_relations = relation_ids(page, "Processo Seletivo")
            if not processo_relations:
                errors.append(f"{label}: relação Processo Seletivo ausente")
            for processo_page_id in processo_relations:
                if processo_page_id not in processo_ids_by_page:
                    errors.append(f"{label}: relação Processo Seletivo aponta para página desconhecida: {processo_page_id}")
        return errors

    def audit_ofertas(
        self,
        pages: list[dict[str, Any]],
        campus_ids_by_page: dict[str, str],
        course_slugs_by_page: dict[str, str],
        processo_ids_by_page: dict[str, str],
        edital_ids_by_page: dict[str, str],
    ) -> list[str]:
        errors: list[str] = []
        seen_by_process: dict[tuple[str, str], str] = {}
        for page in pages:
            props = page["properties"]
            label = page_label("Oferta de ingresso", page)
            oferta_id = plain_text(props.get("oferta_id"))
            if not is_slug(oferta_id):
                errors.append(f"{label}: oferta_id ausente ou inválido")
            if not plain_text(props.get("Curso nome no edital")):
                errors.append(f"{label}: Curso nome no edital ausente")
            if not select_name(props.get("Tipo de oferta")):
                errors.append(f"{label}: Tipo de oferta ausente")
            if number_value(props.get("Vagas")) is None:
                errors.append(f"{label}: Vagas ausente ou inválida")
            if not is_https(url_value(props.get("URL fonte"))):
                errors.append(f"{label}: URL fonte ausente ou não HTTPS")

            processo_relations = relation_ids(page, "Processo Seletivo")
            if not processo_relations:
                errors.append(f"{label}: relação Processo Seletivo ausente")
            for processo_page_id in processo_relations:
                processo_id = processo_ids_by_page.get(processo_page_id)
                if not processo_id:
                    errors.append(f"{label}: relação Processo Seletivo aponta para página desconhecida: {processo_page_id}")
                    continue
                if is_slug(oferta_id):
                    key = (processo_id, oferta_id)
                    if key in seen_by_process:
                        errors.append(f"{label}: oferta_id duplicado no processo {processo_id} com {seen_by_process[key]}: {oferta_id}")
                    else:
                        seen_by_process[key] = label

            campus_relations = relation_ids(page, "Campus")
            campus_id_original = plain_text(props.get("campus_id_original"))
            if not campus_relations and not is_slug(campus_id_original):
                errors.append(f"{label}: informe relação Campus ou campus_id_original válido")
            for campus_page_id in campus_relations:
                if campus_page_id not in campus_ids_by_page:
                    errors.append(f"{label}: relação Campus aponta para página desconhecida: {campus_page_id}")

            for course_page_id in relation_ids(page, "Curso"):
                if course_page_id not in course_slugs_by_page:
                    errors.append(f"{label}: relação Curso aponta para página desconhecida: {course_page_id}")
            for edital_page_id in relation_ids(page, "Edital"):
                if edital_page_id not in edital_ids_by_page:
                    errors.append(f"{label}: relação Edital aponta para página desconhecida: {edital_page_id}")
        return errors

    def build_campi(self) -> list[dict[str, Any]]:
        campus_pages = self.query_all("campi")
        course_pages = self.query_all("cursos")
        movimentacao_pages = self.query_all("movimentacoes_cursos")

        campuses_by_page = {page["id"]: self.campus_ref(page) for page in campus_pages}
        courses_by_page = {page["id"]: self.course_ref(page) for page in course_pages}

        courses_by_campus: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for page in course_pages:
            for campus_page_id in relation_ids(page, "Campus"):
                courses_by_campus[campus_page_id].append(page)

        movimentacoes_by_course: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for page in movimentacao_pages:
            for course_page_id in relation_ids(page, "Curso"):
                movimentacoes_by_course[course_page_id].append(page)

        campi: list[dict[str, Any]] = []
        for page in campus_pages:
            campus = self.campus_json(page)
            courses = [
                self.course_json(
                    course_page,
                    movimentacoes_by_course.get(course_page["id"], []),
                )
                for course_page in courses_by_campus.get(page["id"], [])
            ]
            campus["cursos"] = sorted(courses, key=lambda item: str(item["curso_slug"]))
            campi.append(campus)

        return sorted(campi, key=lambda item: str(item["id"]))

    def campus_ref(self, page: dict[str, Any]) -> dict[str, str]:
        props = page["properties"]
        return {
            "id": plain_text(props.get("campus_id")),
            "nome": plain_text(props.get("Nome")),
        }

    def course_ref(self, page: dict[str, Any]) -> dict[str, str]:
        props = page["properties"]
        return {
            "slug": plain_text(props.get("curso_slug")),
            "nome": plain_text(props.get("Nome")),
            "notion_page_id": page["id"],
        }

    def campus_json(self, page: dict[str, Any]) -> dict[str, Any]:
        props = page["properties"]
        campus_id = plain_text(props.get("campus_id"))
        campus: dict[str, Any] = {
            "id": campus_id,
            "nome": plain_text(props.get("Nome")),
            "links": {
                "site": url_value(props.get("Site")),
                "calendario_academico": url_value(props.get("Calendário acadêmico")),
            },
        }
        horario = self.campus_horario(props)
        if horario:
            campus["horario_aulas"] = horario
        return campus

    def campus_horario(self, props: dict[str, Any]) -> dict[str, Any] | None:
        collected_at = json_datetime(date_start(props.get("Horários Coletado em")))
        if not collected_at:
            return None
        horario: dict[str, Any] = {
            "coletado_em": collected_at,
        }
        add_if_text(horario, "url", url_value(props.get("Horários URL")))
        return horario

    def course_json(
        self,
        page: dict[str, Any],
        movimentacoes: list[dict[str, Any]],
    ) -> dict[str, Any]:
        props = page["properties"]
        course: dict[str, Any] = {
            "curso_slug": plain_text(props.get("curso_slug")),
            "notion_page_id": page["id"],
            "nome": plain_text(props.get("Nome")),
            "nivel": select_name(props.get("Nível")),
            "tipo_oferta": select_name(props.get("Forma de oferta") or props.get("Tipo de oferta")),
        }
        add_if_text(course, "url", url_from_first_existing(props, "Página oficial", "URL oficial"))
        add_if_text(course, "modalidade", select_name(props.get("Modalidade")))
        add_if_text(course, "situacao", select_name(props.get("Situação")))

        suap = self.course_suap(props)
        if suap:
            course["suap"] = suap

        ppc = self.course_ppc(props)
        if ppc:
            course["ppc"] = ppc

        processos = self.movimentacao_processes(movimentacoes)
        if processos:
            course["sei"] = {"processos": processos}

        return course

    def course_suap(self, props: dict[str, Any]) -> dict[str, Any] | None:
        suap: dict[str, Any] = {}
        add_if_number(suap, "id", number_value(props.get("SUAP ID")))
        add_if_text(suap, "codigo", plain_text(props.get("SUAP Código")))
        add_if_number(suap, "vagas", number_value(props.get("SUAP Vagas")))
        add_if_text(suap, "coletado_em", json_datetime(date_start(props.get("SUAP Coletado em"))))
        add_if_text(suap, "atualizado_em", json_datetime(date_start(props.get("SUAP Atualizado em"))))
        return suap or None

    def course_ppc(self, props: dict[str, Any]) -> dict[str, Any] | None:
        ppc_url = url_value(props.get("PPC URL oficial"))
        if not ppc_url:
            return None
        markdown_path = markdown_path_from_link(props.get("PPC Markdown Link"))

        ppc: dict[str, Any] = {
            "url": ppc_url,
            "conversao": {
                "status": "convertido" if markdown_path else "pendente",
            },
        }
        add_if_text(ppc, "markdown_path", markdown_path)

        metadados: dict[str, Any] = {}
        ano_documento = self.ppc_ano_documento(props)
        if ano_documento:
            metadados["ano_documento"] = ano_documento
        vagas = self.ppc_vagas(props)
        if vagas:
            metadados["vagas"] = vagas
        if metadados:
            ppc["metadados"] = metadados
        return ppc

    def ppc_ano_documento(self, props: dict[str, Any]) -> dict[str, Any] | None:
        ano = number_value(props.get("PPC Ano do documento"))
        if ano is None:
            return None
        reviewed_at = json_date(date_start(props.get("PPC Data curadoria")))
        status = curadoria_status(props.get("PPC Curadoria"), reviewed_at)
        item: dict[str, Any] = {
            "ano": ano,
            "trecho_fonte": f"Ano do documento registrado no Notion: {ano}",
            "status_curadoria": status,
        }
        add_if_text(item, "revisado_em", reviewed_at)
        return item

    def ppc_vagas(self, props: dict[str, Any]) -> dict[str, Any] | None:
        quantidade, minimo, maximo = parse_vagas_interval(vagas_text(props.get("PPC Vagas")))
        trecho = plain_text(props.get("PPC Trecho fonte das vagas"))
        if quantidade is None or not trecho:
            return None
        reviewed_at = json_date(date_start(props.get("PPC Data curadoria")))
        status = curadoria_status(props.get("PPC Curadoria"), reviewed_at)
        vagas: dict[str, Any] = {
            "quantidade": quantidade,
            "trecho_fonte": trecho,
            "status_curadoria": status,
        }
        add_if_number(vagas, "minimo", minimo)
        add_if_number(vagas, "maximo", maximo)
        add_if_text(vagas, "periodicidade", plain_text(props.get("PPC Periodicidade vagas")))
        add_if_text(vagas, "forma_oferta", plain_text(props.get("Forma de oferta")))
        add_if_text(vagas, "revisado_em", reviewed_at)
        return vagas

    def movimentacao_processes(self, movimentacoes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen: set[tuple[str, str]] = set()
        processos: list[dict[str, Any]] = []
        for page in sorted(movimentacoes, key=self.movimentacao_sort_key):
            props = page["properties"]
            tipo = select_name(props.get("Tipo")) or "outro"
            anotacoes = plain_text(props.get("Anotações"))
            numero = plain_text_from_first_existing(props, "SEI Processo", "Número SEI")
            if not numero or (numero, tipo) in seen:
                continue
            item = {"numero": numero, "tipo": tipo}
            add_if_text(item, "trecho_fonte", anotacoes)
            processos.append(item)
            seen.add((numero, tipo))
        return processos

    def movimentacao_sort_key(self, page: dict[str, Any]) -> tuple[str, str, str, str]:
        props = page["properties"]
        return (
            json_date(date_start(props.get("Data do ato"))) or json_date(date_start(props.get("Início da vigência"))),
            select_name(props.get("Tipo")),
            plain_text(props.get("Título")),
            page.get("id", ""),
        )

    def build_campi_index(self, campi: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "id": "campi-ifpr",
            "title": "Campi do IFPR",
            "descricao": "Índice de campi e campi avançados do Instituto Federal do Paraná.",
            "tipo_item": "campus",
            "atualizado_em": str(date.today()),
            "items": [
                {
                    "id": campus["id"],
                    "nome": campus["nome"],
                    "path": f"institucional/ifpr/campi/{campus['id']}.json",
                }
                for campus in campi
            ],
        }

    def build_processos_seletivos(self) -> list[dict[str, Any]]:
        processo_pages = self.query_all("processos_seletivos")
        edital_pages = self.query_all("editais_ingresso")
        oferta_pages = self.query_all("ofertas_ingresso")
        campus_pages = self.query_all("campi")
        course_pages = self.query_all("cursos")

        campuses_by_page = {page["id"]: self.campus_ref(page) for page in campus_pages}
        courses_by_page = {page["id"]: self.course_ref(page) for page in course_pages}
        editais_by_page = {page["id"]: self.edital_ref(page) for page in edital_pages}

        editais_by_processo: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for page in edital_pages:
            for processo_page_id in relation_ids(page, "Processo Seletivo"):
                editais_by_processo[processo_page_id].append(page)

        ofertas_by_processo: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for page in oferta_pages:
            for processo_page_id in relation_ids(page, "Processo Seletivo"):
                ofertas_by_processo[processo_page_id].append(page)

        processos = [
            self.processo_seletivo_json(
                page,
                editais_by_processo.get(page["id"], []),
                ofertas_by_processo.get(page["id"], []),
                campuses_by_page,
                courses_by_page,
                editais_by_page,
            )
            for page in processo_pages
        ]
        return sorted(processos, key=lambda item: int(item["ano_ingresso"]))

    def edital_ref(self, page: dict[str, Any]) -> dict[str, str]:
        props = page["properties"]
        return {
            "id": plain_text(props.get("edital_id")),
            "edital_ingresso_id": plain_text(props.get("edital_ingresso_id")),
        }

    def processo_seletivo_json(
        self,
        page: dict[str, Any],
        editais: list[dict[str, Any]],
        ofertas: list[dict[str, Any]],
        campuses_by_page: dict[str, dict[str, str]],
        courses_by_page: dict[str, dict[str, str]],
        editais_by_page: dict[str, dict[str, str]],
    ) -> dict[str, Any]:
        props = page["properties"]
        fontes = [line.strip() for line in plain_text(props.get("Fontes")).splitlines() if line.strip()]
        status = select_name(props.get("Status de curadoria"))
        if status not in VALID_CURADORIA_STATUS:
            status = "dados_parciais"
        processo: dict[str, Any] = {
            "id": plain_text(props.get("processo_seletivo_id")),
            "nome": plain_text(props.get("Nome")),
            "ano_ingresso": number_value(props.get("Ano de ingresso")),
            "instituicao": plain_text(props.get("Instituição")) or "IFPR",
            "fontes": fontes,
            "editais": sorted([self.edital_json(edital) for edital in editais], key=lambda item: str(item["id"])),
            "ofertas": sorted(
                [
                    self.oferta_json(oferta, campuses_by_page, courses_by_page, editais_by_page)
                    for oferta in ofertas
                ],
                key=lambda item: str(item["id"]),
            ),
            "curadoria": {
                "status_ofertas": status,
                "verificado_em": json_date(date_start(props.get("Verificado em"))) or str(date.today()),
            },
        }
        add_if_text(processo["curadoria"], "observacoes", plain_text(props.get("Observações")))
        return processo

    def edital_json(self, page: dict[str, Any]) -> dict[str, Any]:
        props = page["properties"]
        edital: dict[str, Any] = {
            "id": plain_text(props.get("edital_id")),
            "titulo": plain_text(props.get("Título")),
            "url": url_value(props.get("URL")),
        }
        add_if_text(edital, "numero", plain_text(props.get("Número")))
        add_if_number(edital, "ano", number_value(props.get("Ano do edital")))
        add_if_text(edital, "tipo", select_name(props.get("Tipo")))
        return edital

    def oferta_json(
        self,
        page: dict[str, Any],
        campuses_by_page: dict[str, dict[str, str]],
        courses_by_page: dict[str, dict[str, str]],
        editais_by_page: dict[str, dict[str, str]],
    ) -> dict[str, Any]:
        props = page["properties"]
        campus_id = plain_text(props.get("campus_id_original"))
        for campus_page_id in relation_ids(page, "Campus"):
            campus_id = campuses_by_page.get(campus_page_id, {}).get("id") or campus_id

        curso_slug = plain_text(props.get("curso_slug_original"))
        for course_page_id in relation_ids(page, "Curso"):
            curso_slug = courses_by_page.get(course_page_id, {}).get("slug") or curso_slug

        oferta: dict[str, Any] = {
            "id": plain_text(props.get("oferta_id")),
            "campus_id": campus_id,
            "curso_nome": plain_text(props.get("Curso nome no edital")),
            "tipo_oferta": select_name(props.get("Tipo de oferta")),
            "vagas": self.oferta_vagas(props),
            "fonte": self.oferta_fonte(page, editais_by_page),
        }
        add_if_text(oferta, "curso_slug", curso_slug)
        add_if_text(oferta, "modalidade", select_name(props.get("Modalidade")))
        add_if_text(oferta, "turno", plain_text(props.get("Turno")))
        return oferta

    def oferta_vagas(self, props: dict[str, Any]) -> dict[str, Any]:
        reviewed_at = json_date(date_start(props.get("Revisado em")))
        status = curadoria_status(props.get("Status de curadoria"), reviewed_at)
        vagas: dict[str, Any] = {
            "quantidade": number_value(props.get("Vagas")) or 0,
            "trecho_fonte": plain_text(props.get("Trecho fonte")) or "Informação migrada do cadastro operacional.",
            "status_curadoria": status,
        }
        add_if_text(vagas, "forma_oferta", plain_text(props.get("Forma de oferta")))
        add_if_number(vagas, "pagina", number_value(props.get("Página fonte")))
        add_if_text(vagas, "revisado_em", reviewed_at)
        return vagas

    def oferta_fonte(self, page: dict[str, Any], editais_by_page: dict[str, dict[str, str]]) -> dict[str, Any]:
        props = page["properties"]
        fonte: dict[str, Any] = {"url": url_value(props.get("URL fonte"))}
        for edital_page_id in relation_ids(page, "Edital"):
            edital_id = editais_by_page.get(edital_page_id, {}).get("id")
            if edital_id:
                fonte["edital_id"] = edital_id
                break
        add_if_number(fonte, "pagina", number_value(props.get("Página fonte")))
        return fonte

    def build_processos_index(self, processos: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "title": "Processos seletivos do IFPR",
            "total_itens": len(processos),
            "items": [
                {
                    "id": processo["id"],
                    "ano_ingresso": processo["ano_ingresso"],
                    "nome": processo["nome"],
                    "path": f"institucional/ifpr/processos-seletivos/{processo['id']}.json",
                }
                for processo in processos
            ],
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Não escreve arquivos; apenas informa o que seria gerado.")
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        config = load_config()
        config_errors = validate_config(config)
        if config_errors:
            for error in config_errors:
                print(f"- {error}")
            raise NotionError(f"Configuração Notion inválida: {len(config_errors)} problema(s).")
        client = NotionClient.from_env()
        counts = Exporter(client, config.get("databases", {})).export(dry_run=args.dry_run)
        print("\nResumo:")
        print(json.dumps(counts, ensure_ascii=False, indent=2))
        return 0
    except NotionError as exc:
        print(f"\nErro: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
