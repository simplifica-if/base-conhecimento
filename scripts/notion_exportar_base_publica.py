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


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        raise NotionError("config/notion.json não encontrado. Configure os IDs da base Notion operacional.")
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


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


def first_prop(props: dict[str, Any], *names: str) -> dict[str, Any] | None:
    for name in names:
        prop = props.get(name)
        if prop:
            return prop
    return None


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
        campi = self.build_campi()
        processos = self.build_processos_seletivos()

        for campus in campi:
            write_json(CAMPI_ROOT / f"{campus['id']}.json", campus, dry_run)
        write_json(CAMPI_INDEX_PATH, self.build_campi_index(campi), dry_run)

        for processo in processos:
            write_json(PROCESSOS_SELETIVOS_ROOT / f"{processo['id']}.json", processo, dry_run)
        write_json(PROCESSOS_SELETIVOS_INDEX_PATH, self.build_processos_index(processos), dry_run)

        return {
            "campi": len(campi),
            "cursos": sum(len(campus.get("cursos", [])) for campus in campi),
            "processos_seletivos": len(processos),
            "editais": sum(len(processo.get("editais", [])) for processo in processos),
            "ofertas": sum(len(processo.get("ofertas", [])) for processo in processos),
        }

    def build_campi(self) -> list[dict[str, Any]]:
        campus_pages = self.query_all("campi")
        course_pages = self.query_all("cursos")
        document_pages = self.query_all("documentos")
        suap_pages = self.query_all("suap_cursos")
        horario_pages = self.query_all("horarios_aula")
        movimentacao_pages = self.query_all("movimentacoes_cursos")

        campuses_by_page = {page["id"]: self.campus_ref(page) for page in campus_pages}
        courses_by_page = {page["id"]: self.course_ref(page) for page in course_pages}

        courses_by_campus: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for page in course_pages:
            for campus_page_id in relation_ids(page, "Campus"):
                courses_by_campus[campus_page_id].append(page)

        docs_by_course: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for page in document_pages:
            for course_page_id in relation_ids(page, "Curso"):
                docs_by_course[course_page_id].append(page)

        suap_by_course: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for page in suap_pages:
            for course_page_id in relation_ids(page, "Curso"):
                suap_by_course[course_page_id].append(page)

        horarios_by_campus: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for page in horario_pages:
            for campus_page_id in relation_ids(page, "Campus"):
                horarios_by_campus[campus_page_id].append(page)

        movimentacoes_by_course: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for page in movimentacao_pages:
            for course_page_id in relation_ids(page, "Curso"):
                movimentacoes_by_course[course_page_id].append(page)

        campi: list[dict[str, Any]] = []
        for page in campus_pages:
            campus = self.campus_json(page)
            horario = self.pick_horario(horarios_by_campus.get(page["id"], []))
            if horario:
                campus["horario_aulas"] = horario
            courses = [
                self.course_json(
                    course_page,
                    docs_by_course.get(course_page["id"], []),
                    suap_by_course.get(course_page["id"], []),
                    movimentacoes_by_course.get(course_page["id"], []),
                )
                for course_page in courses_by_campus.get(page["id"], [])
            ]
            campus["cursos"] = sorted(courses, key=lambda item: str(item["id"]))
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
            "id": plain_text(props.get("curso_id")),
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
        return campus

    def pick_horario(self, pages: list[dict[str, Any]]) -> dict[str, Any] | None:
        if not pages:
            return None
        ordered = sorted(
            pages,
            key=lambda page: (
                not checkbox_value(page["properties"].get("Fonte ativa?")),
                select_name(page["properties"].get("Status de curadoria")) != "revisado",
                plain_text(page["properties"].get("Nome")),
            ),
        )
        props = ordered[0]["properties"]
        status = select_name(props.get("Status de curadoria"))
        collected_at = json_datetime(date_start(props.get("Coletado em")))
        if not status or not collected_at:
            return None
        horario: dict[str, Any] = {
            "coletado_em": collected_at,
            "status_curadoria": status,
        }
        add_if_text(horario, "url", url_value(props.get("URL")))
        add_if_text(horario, "titulo_fonte", plain_text(props.get("Título da fonte")))
        add_if_text(horario, "periodo_referencia", plain_text(props.get("Período de referência")))
        add_if_text(horario, "tipo_fonte", select_name(props.get("Tipo de fonte")))
        add_if_text(horario, "observacoes", plain_text(props.get("Observações")))
        return horario

    def course_json(
        self,
        page: dict[str, Any],
        documents: list[dict[str, Any]],
        suap_pages: list[dict[str, Any]],
        movimentacoes: list[dict[str, Any]],
    ) -> dict[str, Any]:
        props = page["properties"]
        course: dict[str, Any] = {
            "id": plain_text(props.get("curso_id")),
            "notion_page_id": page["id"],
            "nome": plain_text(props.get("Nome")),
            "nivel": select_name(props.get("Nível")),
            "tipo_oferta": select_name(props.get("Forma de oferta") or props.get("Tipo de oferta")),
            "url": url_value(props.get("URL oficial")),
        }
        add_if_text(course, "modalidade", select_name(props.get("Modalidade")))
        add_if_text(course, "situacao", select_name(props.get("Situação")))
        add_if_text(course, "escopo", select_name(props.get("Escopo")))

        suap = self.pick_suap(suap_pages)
        if suap:
            course["suap"] = suap

        ppc = self.pick_ppc(documents)
        if ppc:
            course["ppc"] = ppc

        processos = self.movimentacao_processes(movimentacoes)
        if processos:
            course["sei"] = {"processos": processos}

        return course

    def pick_suap(self, pages: list[dict[str, Any]]) -> dict[str, Any] | None:
        if not pages:
            return None
        page = sorted(
            pages,
            key=lambda item: (
                number_value(item["properties"].get("SUAP ID")) or 0,
                plain_text(item["properties"].get("Código SUAP")),
                item["id"],
            ),
        )[0]
        props = page["properties"]
        suap: dict[str, Any] = {"notion_page_id": page["id"]}
        add_if_number(suap, "id", number_value(props.get("SUAP ID")))
        add_if_text(suap, "codigo", plain_text(props.get("Código SUAP")))
        add_if_number(suap, "vagas", number_value(props.get("Vagas SUAP")))
        return suap or None

    def pick_ppc(self, pages: list[dict[str, Any]]) -> dict[str, Any] | None:
        candidates = [
            page
            for page in pages
            if url_value(page["properties"].get("URL oficial"))
        ]
        if not candidates:
            return None
        page = sorted(
            candidates,
            key=lambda item: (
                select_name(item["properties"].get("Status")) != "Vigente",
                plain_text(item["properties"].get("Título")),
            ),
        )[0]
        props = page["properties"]
        markdown_path = markdown_path_from_link(props.get("Markdown Link") or props.get("Markdown path"))

        ppc: dict[str, Any] = {
            "notion_page_id": page["id"],
            "url": url_value(props.get("URL oficial")),
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
        ano = number_value(props.get("Ano do documento"))
        if ano is None:
            return None
        reviewed_at = json_date(date_start(first_prop(props, "Data curadoria", "Revisado em")))
        status = curadoria_status(first_prop(props, "Curadoria", "Status curadoria"), reviewed_at)
        item: dict[str, Any] = {
            "ano": ano,
            "trecho_fonte": f"Ano do documento registrado no Notion: {ano}",
            "status_curadoria": status,
        }
        add_if_text(item, "revisado_em", reviewed_at)
        return item

    def ppc_vagas(self, props: dict[str, Any]) -> dict[str, Any] | None:
        quantidade, minimo, maximo = parse_vagas_interval(vagas_text(props.get("Vagas")))
        trecho = plain_text(props.get("Trecho fonte das vagas"))
        if quantidade is None or not trecho:
            return None
        reviewed_at = json_date(date_start(first_prop(props, "Data curadoria", "Revisado em")))
        status = curadoria_status(first_prop(props, "Curadoria", "Status curadoria"), reviewed_at)
        vagas: dict[str, Any] = {
            "quantidade": quantidade,
            "trecho_fonte": trecho,
            "status_curadoria": status,
        }
        add_if_number(vagas, "minimo", minimo)
        add_if_number(vagas, "maximo", maximo)
        add_if_text(vagas, "periodicidade", plain_text(props.get("Periodicidade vagas")))
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
            numero = plain_text(props.get("Número SEI"))
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

        curso_id = plain_text(props.get("curso_id_original"))
        for course_page_id in relation_ids(page, "Curso"):
            curso_id = courses_by_page.get(course_page_id, {}).get("id") or curso_id

        oferta: dict[str, Any] = {
            "id": plain_text(props.get("oferta_id")),
            "campus_id": campus_id,
            "curso_nome": plain_text(props.get("Curso nome no edital")),
            "tipo_oferta": select_name(props.get("Tipo de oferta")),
            "vagas": self.oferta_vagas(props),
            "fonte": self.oferta_fonte(page, editais_by_page),
        }
        add_if_text(oferta, "curso_id", curso_id)
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
    args = parse_args()
    config = load_config()
    client = NotionClient.from_env()
    counts = Exporter(client, config.get("databases", {})).export(dry_run=args.dry_run)
    print("\nResumo:")
    print(json.dumps(counts, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
