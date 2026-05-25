#!/usr/bin/env python3
"""Cria o esqueleto Notion para gestão do lifecycle de cursos."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from base_utils import ROOT
from notion_client import NotionClient, NotionError


CONFIG_PATH = ROOT / "config" / "notion.json"


SELECTS = {
    "tipo_unidade": ["campus", "campus_avancado"],
    "status_cursos": ["dados_pendentes", "dados_parciais", "dados_curados"],
    "nivel": ["fundamental", "médio", "superior", "pós-graduação", "formação inicial e continuada"],
    "tipo_oferta": [
        "técnico integrado",
        "técnico subsequente",
        "graduação tecnológica",
        "bacharelado",
        "licenciatura",
        "especialização",
        "mestrado",
        "FIC",
        "programa institucional",
    ],
    "modalidade": ["presencial", "ead", "semipresencial"],
    "situacao": ["ativo", "em_oferta", "suspenso", "incerto", "extinto"],
    "escopo": ["campus", "rede", "programa", "polo"],
    "documento_tipo": ["PPC", "matriz curricular", "portaria", "resolução", "parecer", "despacho", "edital", "outro"],
    "documento_status": ["Vigente", "Substituído", "Em elaboração", "Em revisão", "Pendente de validação", "Histórico"],
    "conversao_status": ["pendente", "convertido", "erro"],
    "lifecycle_classe": ["Ato administrativo", "Curadoria de cadastro", "Sincronização/publicação"],
    "lifecycle_tipo": [
        "abertura",
        "ajuste",
        "atualização",
        "suspensão",
        "reversão de suspensão",
        "extinção",
        "revisão de PPC vigente",
        "atualização SUAP",
        "correção de cadastro",
        "outro",
    ],
    "lifecycle_fase": [
        "Triagem",
        "Em instrução no campus",
        "Em análise Proens",
        "Em colegiados/conselhos",
        "Aguardando ato/publicação",
        "Efetivado",
        "Cancelado",
        "Arquivado",
    ],
    "lifecycle_modo": ["Histórico", "Operacional"],
    "processo_tipo": [
        "Abertura de Curso",
        "Ajuste de PPC",
        "atualização",
        "suspensão",
        "reversão de suspensão",
        "extinção",
        "revisão de PPC vigente",
        "atualização SUAP",
        "correção de cadastro",
        "outro",
    ],
    "processo_status": ["A localizar", "Em instrução", "Em análise", "Concluído", "Arquivado", "Cancelado"],
    "edital_tipo": [
        "técnico integrado",
        "técnico subsequente",
        "técnico ead",
        "graduação",
        "vagas remanescentes",
        "outro",
    ],
    "edital_status": ["Publicado", "Retificado", "Encerrado", "Arquivado"],
    "vinculo_curso_status": ["vinculado", "pendente", "divergente", "não aplicável"],
    "suap_vinculo_status": ["vinculado", "pendente", "divergente"],
    "suap_fonte": ["Relatório SUAP", "API SUAP", "Planilha", "Curadoria manual"],
    "horario_tipo_fonte": ["pagina_ifpr", "google_sheets", "edupage", "app_externo"],
    "horario_status": ["revisado", "parcial", "nao_encontrado"],
    "tarefa_status": ["Inbox", "A fazer", "Em andamento", "Aguardando", "Concluída", "Cancelada"],
    "prioridade": ["Baixa", "Média", "Alta", "Urgente"],
}


def select_schema(options: list[str]) -> dict[str, Any]:
    return {"select": {"options": [{"name": option} for option in options]}}


def multi_select_schema(options: list[str]) -> dict[str, Any]:
    return {"multi_select": {"options": [{"name": option} for option in options]}}


def relation_schema(data_source_id: str) -> dict[str, Any]:
    return {"relation": {"data_source_id": data_source_id, "type": "single_property", "single_property": {}}}


def base_schemas() -> dict[str, dict[str, Any]]:
    return {
        "campi": {
            "title": "Campi",
            "properties": {
                "Nome": {"title": {}},
                "campus_id": {"rich_text": {}},
                "Tipo de unidade": select_schema(SELECTS["tipo_unidade"]),
                "Site": {"url": {}},
                "Calendário acadêmico": {"url": {}},
                "Status de curadoria": select_schema(SELECTS["status_cursos"]),
                "Verificado em": {"date": {}},
            },
        },
        "cursos": {
            "title": "Cursos",
            "properties": {
                "Nome": {"title": {}},
                "curso_id": {"rich_text": {}},
                "id_composto": {"rich_text": {}},
                "Nível": select_schema(SELECTS["nivel"]),
                "Tipo de oferta": select_schema(SELECTS["tipo_oferta"]),
                "Modalidade": select_schema(SELECTS["modalidade"]),
                "Situação": select_schema(SELECTS["situacao"]),
                "Escopo": select_schema(SELECTS["escopo"]),
                "URL oficial": {"url": {}},
            },
        },
        "documentos": {
            "title": "Documentos de Curso",
            "properties": {
                "Título": {"title": {}},
                "documento_id": {"rich_text": {}},
                "Tipo": select_schema(SELECTS["documento_tipo"]),
                "Status": select_schema(SELECTS["documento_status"]),
                "URL oficial": {"url": {}},
                "Markdown path": {"rich_text": {}},
                "Ano do documento": {"number": {}},
                "Vagas": {"number": {}},
                "Periodicidade vagas": {"rich_text": {}},
                "Forma de oferta": {"rich_text": {}},
                "Trecho fonte das vagas": {"rich_text": {}},
                "Seção das vagas": {"rich_text": {}},
                "Status conversão": select_schema(SELECTS["conversao_status"]),
                "Ferramenta conversão": {"rich_text": {}},
                "Versão ferramenta": {"rich_text": {}},
                "Convertido em": {"date": {}},
                "Status curadoria": {"rich_text": {}},
                "Revisado em": {"date": {}},
            },
        },
        "lifecycle": {
            "title": "Lifecycle de Cursos",
            "properties": {
                "Título": {"title": {}},
                "lifecycle_id": {"rich_text": {}},
                "Classe": select_schema(SELECTS["lifecycle_classe"]),
                "Tipo": select_schema(SELECTS["lifecycle_tipo"]),
                "Fase": select_schema(SELECTS["lifecycle_fase"]),
                "Modo": select_schema(SELECTS["lifecycle_modo"]),
                "Situação anterior": select_schema(SELECTS["situacao"]),
                "Situação resultante": select_schema(SELECTS["situacao"]),
                "Campos afetados": multi_select_schema(["situação", "PPC", "vagas", "modalidade", "URL", "SUAP", "escopo", "nome"]),
                "Resumo da mudança": {"rich_text": {}},
                "Data de início": {"date": {}},
                "Data do ato": {"date": {}},
                "Data efetiva": {"date": {}},
                "Aplicado ao cadastro?": {"checkbox": {}},
                "Aplicado em": {"date": {}},
                "Planilha origem": {"rich_text": {}},
                "Linhas origem": {"rich_text": {}},
                "Notas da planilha": {"rich_text": {}},
                "Acompanhamento": {"rich_text": {}},
                "Processos SEI citados": {"rich_text": {}},
            },
        },
        "processos_sei": {
            "title": "Processos SEI",
            "properties": {
                "Número SEI": {"title": {}},
                "Tipo principal": select_schema(SELECTS["processo_tipo"]),
                "Status": select_schema(SELECTS["processo_status"]),
                "Data de abertura": {"date": {}},
                "Última movimentação": {"date": {}},
                "Unidade responsável": {"rich_text": {}},
                "Observações": {"rich_text": {}},
                "Planilha origem": {"rich_text": {}},
                "Linhas origem": {"rich_text": {}},
            },
        },
        "processos_seletivos": {
            "title": "Processos Seletivos",
            "properties": {
                "Nome": {"title": {}},
                "processo_seletivo_id": {"rich_text": {}},
                "Ano de ingresso": {"number": {}},
                "Instituição": {"rich_text": {}},
                "Fontes": {"rich_text": {}},
                "Status de curadoria": select_schema(SELECTS["status_cursos"]),
                "Verificado em": {"date": {}},
                "Observações": {"rich_text": {}},
            },
        },
        "suap_cursos": {
            "title": "SUAP Cursos",
            "properties": {
                "Nome": {"title": {}},
                "suap_curso_id": {"rich_text": {}},
                "SUAP ID": {"number": {}},
                "Código SUAP": {"rich_text": {}},
                "Vagas SUAP": {"number": {}},
                "Diretoria SUAP": {"rich_text": {}},
                "campus_id inferido": {"rich_text": {}},
                "Status de vínculo": select_schema(SELECTS["suap_vinculo_status"]),
                "Fonte": select_schema(SELECTS["suap_fonte"]),
                "Coletado em": {"date": {}},
                "Atualizado em": {"date": {}},
            },
        },
        "horarios_aula": {
            "title": "Horários de Aula",
            "properties": {
                "Nome": {"title": {}},
                "horario_aula_id": {"rich_text": {}},
                "campus_id_original": {"rich_text": {}},
                "URL": {"url": {}},
                "Título da fonte": {"rich_text": {}},
                "Tipo de fonte": select_schema(SELECTS["horario_tipo_fonte"]),
                "Período de referência": {"rich_text": {}},
                "Status de curadoria": select_schema(SELECTS["horario_status"]),
                "Fonte ativa?": {"checkbox": {}},
                "Coletado em": {"date": {}},
                "Observações": {"rich_text": {}},
            },
        },
        "editais_ingresso": {
            "title": "Editais de Ingresso",
            "properties": {
                "Título": {"title": {}},
                "edital_ingresso_id": {"rich_text": {}},
                "edital_id": {"rich_text": {}},
                "Número": {"rich_text": {}},
                "Ano do edital": {"number": {}},
                "Tipo": select_schema(SELECTS["edital_tipo"]),
                "Status": select_schema(SELECTS["edital_status"]),
                "URL": {"url": {}},
            },
        },
        "ofertas_ingresso": {
            "title": "Ofertas de Ingresso",
            "properties": {
                "Nome": {"title": {}},
                "oferta_ingresso_id": {"rich_text": {}},
                "oferta_id": {"rich_text": {}},
                "campus_id_original": {"rich_text": {}},
                "curso_id_original": {"rich_text": {}},
                "Curso nome no edital": {"rich_text": {}},
                "Tipo de oferta": select_schema(SELECTS["tipo_oferta"] + ["outro"]),
                "Modalidade": select_schema(SELECTS["modalidade"]),
                "Turno": {"rich_text": {}},
                "Vagas": {"number": {}},
                "Forma de oferta": {"rich_text": {}},
                "Trecho fonte": {"rich_text": {}},
                "Página fonte": {"number": {}},
                "URL fonte": {"url": {}},
                "Status de curadoria": {"rich_text": {}},
                "Revisado em": {"date": {}},
                "Status de vínculo com curso": select_schema(SELECTS["vinculo_curso_status"]),
            },
        },
        "tarefas": {
            "title": "Tarefas",
            "properties": {
                "Nome": {"title": {}},
                "Status": select_schema(SELECTS["tarefa_status"]),
                "Prioridade": select_schema(SELECTS["prioridade"]),
                "Responsável": {"people": {}},
                "Prazo": {"date": {}},
                "Área/Domínio": multi_select_schema(["cursos", "PPC", "processo seletivo", "base de conhecimento", "painel", "atendimento"]),
                "Tipo de tarefa": {"rich_text": {}},
                "Bloqueada?": {"checkbox": {}},
                "Próxima ação": {"rich_text": {}},
            },
        },
    }


RELATIONS = {
    "cursos": {"Campus": "campi"},
    "documentos": {"Curso": "cursos", "Campus": "campi", "Lifecycle relacionado": "lifecycle"},
    "lifecycle": {
        "Cursos": "cursos",
        "Campi": "campi",
        "Processo SEI": "processos_sei",
        "Documentos relacionados": "documentos",
        "Tarefas relacionadas": "tarefas",
    },
    "processos_sei": {"Cursos": "cursos", "Campi": "campi"},
    "suap_cursos": {"Curso": "cursos", "Tarefas relacionadas": "tarefas"},
    "horarios_aula": {"Campus": "campi", "Tarefas relacionadas": "tarefas"},
    "processos_seletivos": {"Tarefas relacionadas": "tarefas"},
    "editais_ingresso": {"Processo Seletivo": "processos_seletivos", "Tarefas relacionadas": "tarefas"},
    "ofertas_ingresso": {
        "Processo Seletivo": "processos_seletivos",
        "Edital": "editais_ingresso",
        "Campus": "campi",
        "Curso": "cursos",
        "Tarefas relacionadas": "tarefas",
    },
    "tarefas": {
        "Cursos relacionados": "cursos",
        "Campi relacionados": "campi",
        "Lifecycle relacionado": "lifecycle",
        "Processos SEI relacionados": "processos_sei",
        "Processos Seletivos relacionados": "processos_seletivos",
        "SUAP Cursos relacionados": "suap_cursos",
        "Horários de Aula relacionados": "horarios_aula",
        "Editais de Ingresso relacionados": "editais_ingresso",
        "Ofertas de Ingresso relacionadas": "ofertas_ingresso",
    },
}


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {}
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def save_config(config: dict[str, Any]) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def page_title(text: str) -> list[dict[str, Any]]:
    return [{"type": "text", "text": {"content": text}}]


def find_child_database(client: NotionClient, parent_page_id: str, title: str) -> str | None:
    children = client.paginate("GET", f"/blocks/{parent_page_id}/children")
    for child in children:
        if child.get("type") != "child_database":
            continue
        if child.get("child_database", {}).get("title") == title:
            return child.get("id")
    return None


def first_data_source_id(database: dict[str, Any]) -> str:
    data_sources = database.get("data_sources") or []
    if data_sources:
        return data_sources[0]["id"]
    initial_data_source = database.get("initial_data_source")
    if isinstance(initial_data_source, dict) and initial_data_source.get("id"):
        return initial_data_source["id"]
    raise NotionError(f"Não foi possível localizar data source na resposta da base {database.get('id')}.")


def retrieve_database(client: NotionClient, database_id: str) -> dict[str, Any]:
    return client.request("GET", f"/databases/{database_id}")


def create_database(
    client: NotionClient,
    parent_page_id: str,
    title_text: str,
    properties: dict[str, Any],
) -> tuple[str, str]:
    response = client.request(
        "POST",
        "/databases",
        {
            "parent": {"type": "page_id", "page_id": parent_page_id},
            "title": page_title(title_text),
            "initial_data_source": {
                "title": page_title(title_text),
                "properties": properties,
            },
        },
    )
    return response["id"], first_data_source_id(response)


def update_relations(client: NotionClient, data_source_id: str, relation_properties: dict[str, Any]) -> None:
    client.request("PATCH", f"/data_sources/{data_source_id}", {"properties": relation_properties})


def sync_base_properties(client: NotionClient, data_source_id: str, properties: dict[str, Any]) -> None:
    data_source = client.request("GET", f"/data_sources/{data_source_id}")
    current = data_source.get("properties", {})
    updates: dict[str, Any] = {}
    for property_name, schema in properties.items():
        if "title" in schema:
            continue
        if property_name not in current:
            updates[property_name] = schema
            continue
        # Keep select option sets current as the model evolves.
        if "select" in schema or "multi_select" in schema:
            updates[property_name] = schema
    if updates:
        client.request("PATCH", f"/data_sources/{data_source_id}", {"properties": updates})


def bootstrap(parent_page_id: str, dry_run: bool) -> dict[str, Any]:
    schemas = base_schemas()
    config = load_config()
    config.setdefault("parent_page_id", parent_page_id)
    config.setdefault("databases", {})

    if dry_run:
        print("Bootstrap Notion planejado:")
        for key, schema in schemas.items():
            print(f"- {schema['title']} ({key}): {len(schema['properties'])} propriedades base")
        print("- relações serão adicionadas após a criação das bases")
        return config

    client = NotionClient.from_env()
    for key, schema in schemas.items():
        database_id = config["databases"].get(key, {}).get("id")
        data_source_id = config["databases"].get(key, {}).get("data_source_id")
        if not database_id:
            database_id = find_child_database(client, parent_page_id, schema["title"])
        if database_id:
            database = retrieve_database(client, database_id)
            data_source_id = data_source_id or first_data_source_id(database)
            print(f"Base existente: {schema['title']} -> {database_id}")
        else:
            database_id, data_source_id = create_database(client, parent_page_id, schema["title"], schema["properties"])
            print(f"Base criada: {schema['title']} -> {database_id} / data source {data_source_id}")
        config["databases"][key] = {"id": database_id, "data_source_id": data_source_id, "title": schema["title"]}
        save_config(config)

    for key, schema in schemas.items():
        sync_base_properties(client, config["databases"][key]["data_source_id"], schema["properties"])
        print(f"Propriedades sincronizadas: {schema['title']}")

    for source_key, properties in RELATIONS.items():
        relation_properties = {
            property_name: relation_schema(config["databases"][target_key]["data_source_id"])
            for property_name, target_key in properties.items()
        }
        update_relations(client, config["databases"][source_key]["data_source_id"], relation_properties)
        print(f"Relações atualizadas: {config['databases'][source_key]['title']}")

    save_config(config)
    return config


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent-page-id", default=os.environ.get("NOTION_PARENT_PAGE_ID"))
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.parent_page_id:
        raise NotionError("Defina --parent-page-id ou NOTION_PARENT_PAGE_ID.")
    bootstrap(args.parent_page_id, args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
