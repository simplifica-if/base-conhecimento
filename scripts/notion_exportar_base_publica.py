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
VALID_VAGAS_STATUS = {"sugerido", "revisado"}
VALID_CURADORIA_STATUS = {"dados_pendentes", "dados_parciais", "dados_curados"}


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        raise NotionError("config/notion.json não encontrado. Rode scripts/notion_bootstrap.py primeiro.")
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


def add_if_text(target: dict[str, Any], key: str, value: str) -> None:
    if value:
        target[key] = value


def add_if_number(target: dict[str, Any], key: str, value: int | None) -> None:
    if value is not None:
        target[key] = value


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
        lifecycle_pages = self.query_all("lifecycle")
        processo_pages = self.query_all("processos_sei")

        campuses_by_page = {page["id"]: self.campus_ref(page) for page in campus_pages}
        courses_by_page = {page["id"]: self.course_ref(page) for page in course_pages}
        processos_by_page = {page["id"]: plain_text(page["properties"].get("Número SEI")) for page in processo_pages}

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

        lifecycle_by_course: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for page in lifecycle_pages:
            for course_page_id in relation_ids(page, "Cursos"):
                lifecycle_by_course[course_page_id].append(page)

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
                    lifecycle_by_course.get(course_page["id"], []),
                    processos_by_page,
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
            "tipo_unidade": select_name(props.get("Tipo de unidade")),
        }

    def course_ref(self, page: dict[str, Any]) -> dict[str, str]:
        props = page["properties"]
        return {
            "id": plain_text(props.get("curso_id")),
            "nome": plain_text(props.get("Nome")),
            "id_composto": plain_text(props.get("id_composto")),
        }

    def campus_json(self, page: dict[str, Any]) -> dict[str, Any]:
        props = page["properties"]
        campus_id = plain_text(props.get("campus_id"))
        campus: dict[str, Any] = {
            "id": campus_id,
            "nome": plain_text(props.get("Nome")),
            "tipo_unidade": select_name(props.get("Tipo de unidade")),
            "links": {
                "site": url_value(props.get("Site")),
                "calendario_academico": url_value(props.get("Calendário acadêmico")),
            },
            "curadoria": {
                "status_cursos": select_name(props.get("Status de curadoria")) or "dados_parciais",
                "verificado_em": json_date(date_start(props.get("Verificado em"))) or str(date.today()),
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
        lifecycles: list[dict[str, Any]],
        processos_by_page: dict[str, str],
    ) -> dict[str, Any]:
        props = page["properties"]
        course: dict[str, Any] = {
            "id": plain_text(props.get("curso_id")),
            "nome": plain_text(props.get("Nome")),
            "nivel": select_name(props.get("Nível")),
            "tipo_oferta": select_name(props.get("Tipo de oferta")),
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

        processos = self.lifecycle_processes(lifecycles, processos_by_page)
        if processos:
            course["sei"] = {"processos": processos}

        return course

    def pick_suap(self, pages: list[dict[str, Any]]) -> dict[str, Any] | None:
        if not pages:
            return None
        props = sorted(pages, key=lambda page: plain_text(page["properties"].get("suap_curso_id")))[0]["properties"]
        suap: dict[str, Any] = {}
        add_if_number(suap, "id", number_value(props.get("SUAP ID")))
        add_if_text(suap, "codigo", plain_text(props.get("Código SUAP")))
        add_if_number(suap, "vagas", number_value(props.get("Vagas SUAP")))
        return suap or None

    def pick_ppc(self, pages: list[dict[str, Any]]) -> dict[str, Any] | None:
        candidates = [
            page
            for page in pages
            if select_name(page["properties"].get("Tipo")) == "PPC"
            and url_value(page["properties"].get("URL oficial"))
            and plain_text(page["properties"].get("Markdown path"))
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
        conversion: dict[str, Any] = {
            "status": select_name(props.get("Status conversão")) or "pendente",
        }
        add_if_text(conversion, "ferramenta", plain_text(props.get("Ferramenta conversão")))
        add_if_text(conversion, "versao_ferramenta", plain_text(props.get("Versão ferramenta")))
        add_if_text(conversion, "convertido_em", json_date(date_start(props.get("Convertido em"))))

        ppc: dict[str, Any] = {
            "url": url_value(props.get("URL oficial")),
            "markdown_path": plain_text(props.get("Markdown path")),
            "conversao": conversion,
        }

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
        status = plain_text(props.get("Status curadoria"))
        if status not in VALID_VAGAS_STATUS:
            status = "revisado" if date_start(props.get("Revisado em")) else "sugerido"
        item: dict[str, Any] = {
            "ano": ano,
            "trecho_fonte": f"Ano do documento registrado no Notion: {ano}",
            "status_curadoria": status,
        }
        add_if_text(item, "revisado_em", json_date(date_start(props.get("Revisado em"))))
        return item

    def ppc_vagas(self, props: dict[str, Any]) -> dict[str, Any] | None:
        quantidade = number_value(props.get("Vagas"))
        trecho = plain_text(props.get("Trecho fonte das vagas"))
        status = plain_text(props.get("Status curadoria"))
        if quantidade is None or not trecho:
            return None
        if status not in VALID_VAGAS_STATUS:
            status = "revisado" if date_start(props.get("Revisado em")) else "sugerido"
        vagas: dict[str, Any] = {
            "quantidade": quantidade,
            "trecho_fonte": trecho,
            "status_curadoria": status,
        }
        add_if_text(vagas, "periodicidade", plain_text(props.get("Periodicidade vagas")))
        add_if_text(vagas, "forma_oferta", plain_text(props.get("Forma de oferta")))
        add_if_text(vagas, "secao", plain_text(props.get("Seção das vagas")))
        add_if_text(vagas, "revisado_em", json_date(date_start(props.get("Revisado em"))))
        return vagas

    def lifecycle_processes(self, lifecycles: list[dict[str, Any]], processos_by_page: dict[str, str]) -> list[dict[str, Any]]:
        seen: set[tuple[str, str]] = set()
        processos: list[dict[str, Any]] = []
        for page in sorted(lifecycles, key=self.lifecycle_sort_key):
            props = page["properties"]
            tipo = select_name(props.get("Tipo")) or "outro"
            anotacoes = plain_text(props.get("Anotações"))
            for process_page_id in relation_ids(page, "Processo SEI"):
                numero = processos_by_page.get(process_page_id, "")
                if not numero or (numero, tipo) in seen:
                    continue
                item = {"numero": numero, "tipo": tipo}
                add_if_text(item, "trecho_fonte", anotacoes)
                processos.append(item)
                seen.add((numero, tipo))
        return processos

    def lifecycle_sort_key(self, page: dict[str, Any]) -> tuple[str, str, str, str]:
        props = page["properties"]
        return (
            json_date(date_start(props.get("Data do ato"))) or json_date(date_start(props.get("Data efetiva"))),
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
                    "tipo_unidade": campus["tipo_unidade"],
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
        status = plain_text(props.get("Status de curadoria"))
        if status not in VALID_VAGAS_STATUS:
            status = "revisado" if date_start(props.get("Revisado em")) else "sugerido"
        vagas: dict[str, Any] = {
            "quantidade": number_value(props.get("Vagas")) or 0,
            "trecho_fonte": plain_text(props.get("Trecho fonte")) or "Informação migrada do cadastro operacional.",
            "status_curadoria": status,
        }
        add_if_text(vagas, "forma_oferta", plain_text(props.get("Forma de oferta")))
        add_if_number(vagas, "pagina", number_value(props.get("Página fonte")))
        add_if_text(vagas, "revisado_em", json_date(date_start(props.get("Revisado em"))))
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
