#!/usr/bin/env python3
"""Valida a base pública de conhecimento."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

from base_utils import (
    CATALOGOS_MANIFEST_PATH,
    CATALOGOS_MANIFEST_SCHEMA_PATH,
    CATALOGOS_ROOT,
    CAMPI_INDEX_PATH,
    CAMPI_INDEX_SCHEMA_PATH,
    CAMPUS_SCHEMA_PATH,
    CNCT_CURSO_SCHEMA_PATH,
    CNCT_CURSOS_ROOT,
    CNCT_INDEX_PATH,
    CNCT_INDEX_SCHEMA_PATH,
    CNCT_MANIFEST_PATH,
    CNCT_MANIFEST_SCHEMA_PATH,
    INSTITUCIONAL_MANIFEST_PATH,
    INSTITUCIONAL_MANIFEST_SCHEMA_PATH,
    INSTITUCIONAL_ROOT,
    MANIFEST_FIELDS,
    MANIFEST_PATH,
    NORMAS_ROOT,
    PROCESSO_SELETIVO_SCHEMA_PATH,
    PROCESSOS_SELETIVOS_INDEX_PATH,
    PROCESSOS_SELETIVOS_INDEX_SCHEMA_PATH,
    PROCESSOS_SELETIVOS_ROOT,
    PPCS_INDEX_PATH,
    PPCS_INDEX_SCHEMA_PATH,
    PPCS_SECOES_PATH,
    README_PATH,
    REQUIRED_FIELDS,
    ROOT,
    TIPO_DIRETORIOS,
    TIPOS_UNIDADE_INSTITUCIONAL,
    frontmatter,
    relative,
)


LOCAL_PATTERNS = ["/" + "Users/", "Down" + "loads/", "file" + "://"]
PPC_CONVERSION_ARTIFACTS = [
    (
        "placeholder de imagem omitida",
        re.compile(r"picture \[[0-9]+ x [0-9]+\] intentionally omitted"),
    ),
    (
        "marcador de início/fim de texto de imagem",
        re.compile(r"Start of picture text|End of picture text"),
    ),
    (
        "OCR residual isolado",
        re.compile(r"^\s*eme<br>\s*$", re.MULTILINE),
    ),
    (
        "rodapé PROENS de conversão",
        re.compile(r"INSTITUTO FEDERAL DO PARANÁ.*Pró-Reitoria de Ensino - \*\*PROENS\*\*"),
    ),
]
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
CNCT_COURSE_FIELDS = [
    "id",
    "indice",
    "denominacao",
    "denominacao_normalizada",
    "eixo_tecnologico",
    "area_tecnologica",
    "carga_horaria_minima_horas",
    "descricao_carga_horaria_minima",
    "perfil_profissional",
    "pre_requisitos_ingresso",
    "itinerarios_formativos",
    "campo_atuacao",
    "ocupacoes_cbo",
    "codigos_cbo",
    "infraestrutura_minima",
    "legislacao_profissional",
]
PPC_SECTION_KINDS = {
    "identificacao",
    "justificativa",
    "objetivos",
    "perfil_egresso",
    "concepcao_pedagogica",
    "organizacao_curricular",
    "matriz_curricular",
    "ementas",
    "avaliacao",
    "estagio_praticas",
    "infraestrutura",
    "corpo_docente",
    "referencias",
    "outros",
}


def validate_links(path: Path, text: str) -> list[str]:
    errors: list[str] = []
    for match in re.finditer(r"\[[^\]]+\]\(([^)]+)\)", text):
        target = match.group(1)
        if target.startswith(("http://", "https://", "#", "mailto:")):
            continue
        if target.startswith("/"):
            errors.append(f"{relative(path)}: link absoluto local ou de raiz: {target}")
            continue
        clean = target.split("#", 1)[0]
        if clean and not (path.parent / clean).resolve().exists():
            errors.append(f"{relative(path)}: link interno inexistente: {target}")
    return errors


def stale_filename_alias(alias: object) -> bool:
    if not isinstance(alias, str) or not alias.endswith(".md"):
        return False
    return bool(re.match(r"\d{4}-\d{2}-\d{2}_", alias) or re.search(r"[_-]\d{4}.*\.md$", alias))


def validate_markdown(path: Path) -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    for pattern in LOCAL_PATTERNS:
        if pattern in text:
            errors.append(f"{relative(path)}: contém padrão local proibido: {pattern}")

    try:
        meta, body = frontmatter(path)
    except ValueError as exc:
        return [str(exc)]

    missing = sorted(REQUIRED_FIELDS - set(meta))
    if missing:
        errors.append(f"{relative(path)}: campos obrigatórios ausentes: {', '.join(missing)}")
    if not body.lstrip().startswith("## Resumo"):
        errors.append(f"{relative(path)}: corpo não começa com ## Resumo")
    if not isinstance(meta.get("keywords"), list) or not meta.get("keywords"):
        errors.append(f"{relative(path)}: keywords deve ser lista não vazia")
    for alias in meta.get("aliases", []):
        if stale_filename_alias(alias):
            errors.append(f"{relative(path)}: alias parece nome antigo de arquivo: {alias}")

    errors.extend(validate_links(path, text))
    return errors


def validate_ppc_conversion_artifacts() -> list[str]:
    errors: list[str] = []
    for path in sorted((INSTITUCIONAL_ROOT / "ifpr" / "ppcs").glob("*/*.md")):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for label, pattern in PPC_CONVERSION_ARTIFACTS:
            if pattern.search(text):
                errors.append(f"{relative(path)}: contém artefato de conversão: {label}")
    return errors


def comparable(field: str, value: object) -> object:
    if field == "ano" and value is not None:
        return str(value)
    return value


def validate_manifest_item(item: dict[str, object]) -> list[str]:
    errors: list[str] = []
    path_value = item.get("path")
    if not isinstance(path_value, str):
        return ["manifest.json: item sem path textual"]

    path = ROOT / path_value
    if not path.exists():
        return [f"manifest.json aponta para arquivo inexistente: {path_value}"]

    if re.match(r"\d{4}-\d{2}-\d{2}_", path.name):
        errors.append(f"{path_value}: nome do arquivo não deve começar com data")

    key = (str(item.get("jurisdicao")), str(item.get("tipo_documento")))
    expected_dir = TIPO_DIRETORIOS.get(key)
    if expected_dir is None:
        errors.append(f"manifest.json: item com jurisdição/tipo sem diretório configurado: {key}")
    elif str(path.parent.relative_to(ROOT)) != expected_dir:
        errors.append(f"{path_value}: deveria estar em {expected_dir}")

    try:
        meta, _body = frontmatter(path)
    except ValueError as exc:
        errors.append(str(exc))
        return errors

    for field in MANIFEST_FIELDS:
        if comparable(field, item.get(field)) != comparable(field, meta.get(field)):
            errors.append(f"{path_value}: manifest.json diverge do front matter no campo {field}")
    return errors


def validate_local_patterns() -> list[str]:
    errors: list[str] = []
    for path in ROOT.rglob("*"):
        if any(part in {".git", ".venv"} for part in path.parts) or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in LOCAL_PATTERNS:
            if pattern in text:
                errors.append(f"{relative(path)} contém padrão local proibido: {pattern}")
    return errors


def load_manifest() -> tuple[list[object], list[str]]:
    try:
        data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return [], [f"manifest.json inválido: {exc}"]
    if not isinstance(data, list):
        return [], ["manifest.json deve conter uma lista"]
    return data, []


def load_json(path: Path, label: str) -> tuple[object | None, list[str]]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), []
    except FileNotFoundError:
        return None, [f"{label} não encontrado: {relative(path)}"]
    except Exception as exc:  # noqa: BLE001
        return None, [f"{label} inválido: {exc}"]


def type_name(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int) and not isinstance(value, bool):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def validate_json_schema(data: object, schema: dict[str, object], label: str, path: str = "$") -> list[str]:
    errors: list[str] = []

    expected_type = schema.get("type")
    if expected_type is not None and type_name(data) != expected_type:
        return [f"{label}: {path} deve ser {expected_type}, recebido {type_name(data)}"]

    if "const" in schema and data != schema["const"]:
        errors.append(f"{label}: {path} deve ser {schema['const']!r}")
    if "enum" in schema and data not in schema["enum"]:
        errors.append(f"{label}: {path} deve ser um de {schema['enum']!r}")

    if isinstance(data, str):
        min_length = schema.get("minLength")
        if isinstance(min_length, int) and len(data) < min_length:
            errors.append(f"{label}: {path} deve ter ao menos {min_length} caractere(s)")
        pattern = schema.get("pattern")
        if isinstance(pattern, str) and not re.search(pattern, data):
            errors.append(f"{label}: {path} não corresponde ao padrão {pattern}")
        if schema.get("format") == "date" and not DATE_RE.fullmatch(data):
            errors.append(f"{label}: {path} deve estar em YYYY-MM-DD")
        if schema.get("format") == "uri":
            parsed = urlparse(data)
            if not parsed.scheme or not parsed.netloc or re.search(r"\s", data):
                errors.append(f"{label}: {path} deve ser URI absoluta válida")

    if isinstance(data, int) and not isinstance(data, bool):
        minimum = schema.get("minimum")
        if isinstance(minimum, int) and data < minimum:
            errors.append(f"{label}: {path} deve ser maior ou igual a {minimum}")

    if isinstance(data, list):
        min_items = schema.get("minItems")
        if isinstance(min_items, int) and len(data) < min_items:
            errors.append(f"{label}: {path} deve ter ao menos {min_items} item(ns)")
        max_items = schema.get("maxItems")
        if isinstance(max_items, int) and len(data) > max_items:
            errors.append(f"{label}: {path} deve ter no máximo {max_items} item(ns)")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(data):
                errors.extend(validate_json_schema(item, item_schema, label, f"{path}[{index}]"))

    if isinstance(data, dict):
        required = schema.get("required")
        if isinstance(required, list):
            for field in required:
                if isinstance(field, str) and field not in data:
                    errors.append(f"{label}: {path}.{field} é obrigatório")

        properties = schema.get("properties")
        properties = properties if isinstance(properties, dict) else {}
        for key, value in data.items():
            child_schema = properties.get(key)
            if isinstance(child_schema, dict):
                errors.extend(validate_json_schema(value, child_schema, label, f"{path}.{key}"))
                continue
            additional = schema.get("additionalProperties", True)
            if additional is False:
                errors.append(f"{label}: {path}.{key} não é permitido")
            elif isinstance(additional, dict):
                errors.extend(validate_json_schema(value, additional, label, f"{path}.{key}"))

    return errors


def validate_with_schema(data: object, schema_path: Path, label: str) -> list[str]:
    schema, errors = load_json(schema_path, f"schema {relative(schema_path)}")
    if errors:
        return errors
    if not isinstance(schema, dict):
        return [f"schema {relative(schema_path)} deve conter um objeto JSON"]
    return validate_json_schema(data, schema, label)


def validate_https_url(value: object, field: str) -> list[str]:
    if not isinstance(value, str) or not value:
        return [f"{field} deve ser URL textual não vazia"]
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc or re.search(r"\s", value):
        return [f"{field} deve ser URL HTTPS absoluta válida"]
    return []


def validate_campus_file(path: Path, index_item: dict[str, object]) -> list[str]:
    errors: list[str] = []
    data, json_errors = load_json(path, f"arquivo de campus {relative(path)}")
    errors.extend(json_errors)
    if errors:
        return errors
    if not isinstance(data, dict):
        return [f"{relative(path)} deve conter um objeto JSON"]
    errors.extend(validate_with_schema(data, CAMPUS_SCHEMA_PATH, relative(path)))

    required = ["id", "nome", "tipo_unidade", "links", "cursos", "curadoria"]
    for field in required:
        if field not in data:
            errors.append(f"{relative(path)}: campo obrigatório ausente: {field}")

    campus_id = data.get("id")
    if not isinstance(campus_id, str) or not SLUG_RE.fullmatch(campus_id):
        errors.append(f"{relative(path)}: id deve ser slug ASCII minúsculo")
    elif path.name != f"{campus_id}.json":
        errors.append(f"{relative(path)}: nome do arquivo diverge do id")

    for field in ["id", "nome", "tipo_unidade"]:
        if data.get(field) != index_item.get(field):
            errors.append(f"{relative(path)}: campo {field} diverge do index.json")

    if data.get("tipo_unidade") not in TIPOS_UNIDADE_INSTITUCIONAL:
        errors.append(f"{relative(path)}: tipo_unidade inválido: {data.get('tipo_unidade')}")

    links = data.get("links")
    if not isinstance(links, dict):
        errors.append(f"{relative(path)}: links deve ser objeto")
    else:
        for field in ["site", "calendario_academico"]:
            if field not in links:
                errors.append(f"{relative(path)}: links.{field} ausente")
            else:
                errors.extend(validate_https_url(links[field], f"{relative(path)}: links.{field}"))

    cursos = data.get("cursos")
    if not isinstance(cursos, list):
        errors.append(f"{relative(path)}: cursos deve ser array")
    else:
        seen_course_ids: set[str] = set()
        for curso in cursos:
            if not isinstance(curso, dict):
                continue
            curso_id = curso.get("id")
            if isinstance(curso_id, str):
                if curso_id in seen_course_ids:
                    errors.append(f"{relative(path)}: curso duplicado: {curso_id}")
                seen_course_ids.add(curso_id)
            if "url" in curso:
                errors.extend(validate_https_url(curso["url"], f"{relative(path)}: cursos[].url"))
            if "ppc_url" in curso:
                errors.append(f"{relative(path)}: cursos[].ppc_url foi substituído por cursos[].ppc.url")
            ppc = curso.get("ppc")
            if ppc is not None:
                if not isinstance(ppc, dict):
                    errors.append(f"{relative(path)}: cursos[].ppc deve ser objeto")
                    continue
                errors.extend(validate_https_url(ppc.get("url"), f"{relative(path)}: cursos[].ppc.url"))

                markdown_path = ppc.get("markdown_path")
                if not isinstance(markdown_path, str):
                    errors.append(f"{relative(path)}: cursos[].ppc.markdown_path deve ser texto")
                elif not markdown_path.startswith("institucional/ifpr/ppcs/") or not markdown_path.endswith(".md"):
                    errors.append(f"{relative(path)}: cursos[].ppc.markdown_path deve apontar para institucional/ifpr/ppcs/*.md")
                elif isinstance(campus_id, str) and isinstance(curso_id, str):
                    expected = f"institucional/ifpr/ppcs/{campus_id}/{curso_id}.md"
                    if markdown_path != expected:
                        errors.append(f"{relative(path)}: cursos[].ppc.markdown_path esperado para {curso_id}: {expected}")

                conversao = ppc.get("conversao")
                if not isinstance(conversao, dict):
                    errors.append(f"{relative(path)}: cursos[].ppc.conversao deve ser objeto")
                elif conversao.get("status") == "convertido":
                    if isinstance(markdown_path, str) and not (ROOT / markdown_path).exists():
                        errors.append(f"{relative(path)}: markdown convertido inexistente: {markdown_path}")

                metadados = ppc.get("metadados")
                if isinstance(metadados, dict):
                    vagas = metadados.get("vagas")
                    if vagas is not None and not isinstance(vagas, dict):
                        errors.append(f"{relative(path)}: cursos[].ppc.metadados.vagas deve ser objeto contextual")

    programas = data.get("programas", [])
    if not isinstance(programas, list):
        errors.append(f"{relative(path)}: programas deve ser array")
    else:
        seen_program_ids: set[str] = set()
        for programa in programas:
            if not isinstance(programa, dict):
                continue
            programa_id = programa.get("id")
            if isinstance(programa_id, str):
                if programa_id in seen_program_ids:
                    errors.append(f"{relative(path)}: programa duplicado: {programa_id}")
                seen_program_ids.add(programa_id)
            if "url" in programa:
                errors.extend(validate_https_url(programa["url"], f"{relative(path)}: programas[].url"))

            ofertas = programa.get("ofertas")
            if not isinstance(ofertas, list):
                errors.append(f"{relative(path)}: programas[].ofertas deve ser array")
                continue
            seen_offer_ids: set[str] = set()
            for oferta in ofertas:
                if not isinstance(oferta, dict):
                    continue
                oferta_id = oferta.get("id")
                if isinstance(oferta_id, str):
                    if oferta_id in seen_offer_ids:
                        errors.append(f"{relative(path)}: oferta duplicada em programa {programa_id}: {oferta_id}")
                    seen_offer_ids.add(oferta_id)
                if "url" in oferta:
                    errors.extend(validate_https_url(oferta["url"], f"{relative(path)}: programas[].ofertas[].url"))

    curadoria = data.get("curadoria")
    if not isinstance(curadoria, dict):
        errors.append(f"{relative(path)}: curadoria deve ser objeto")
    else:
        if curadoria.get("status_cursos") not in {"dados_pendentes", "dados_parciais", "dados_curados"}:
            errors.append(f"{relative(path)}: curadoria.status_cursos inválido")
        fontes = curadoria.get("fontes", [])
        if not isinstance(fontes, list):
            errors.append(f"{relative(path)}: curadoria.fontes deve ser array")
        else:
            for fonte in fontes:
                errors.extend(validate_https_url(fonte, f"{relative(path)}: curadoria.fontes[]"))
        if not isinstance(curadoria.get("verificado_em"), str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", curadoria.get("verificado_em", "")):
            errors.append(f"{relative(path)}: curadoria.verificado_em deve estar em YYYY-MM-DD")

    return errors


def validate_institucional() -> list[str]:
    errors: list[str] = []
    manifest, manifest_errors = load_json(INSTITUCIONAL_MANIFEST_PATH, "institucional_manifest.json")
    errors.extend(manifest_errors)
    index, index_errors = load_json(CAMPI_INDEX_PATH, "índice de campi")
    errors.extend(index_errors)
    if errors:
        return errors

    if not isinstance(manifest, dict):
        errors.append("institucional_manifest.json deve conter um objeto JSON")
    else:
        errors.extend(validate_with_schema(manifest, INSTITUCIONAL_MANIFEST_SCHEMA_PATH, "institucional_manifest.json"))
        colecoes = manifest.get("colecoes")
        if not isinstance(colecoes, list) or not colecoes:
            errors.append("institucional_manifest.json: colecoes deve ser lista não vazia")
        else:
            campi_collection = next((item for item in colecoes if isinstance(item, dict) and item.get("id") == "campi-ifpr"), None)
            if campi_collection is None:
                errors.append("institucional_manifest.json: coleção campi-ifpr ausente")
            else:
                if campi_collection.get("path") != relative(CAMPI_INDEX_PATH):
                    errors.append("institucional_manifest.json: path da coleção campi-ifpr diverge do índice")
            processos_collection = next((item for item in colecoes if isinstance(item, dict) and item.get("id") == "processos-seletivos-ifpr"), None)
            if processos_collection is not None and processos_collection.get("path") != relative(PROCESSOS_SELETIVOS_INDEX_PATH):
                errors.append("institucional_manifest.json: path da coleção processos-seletivos-ifpr diverge do índice")
            ppcs_collection = next((item for item in colecoes if isinstance(item, dict) and item.get("id") == "ppcs-ifpr"), None)
            if ppcs_collection is not None and ppcs_collection.get("path") != relative(PPCS_INDEX_PATH):
                errors.append("institucional_manifest.json: path da coleção ppcs-ifpr diverge do índice")

    if not isinstance(index, dict):
        errors.append(f"{relative(CAMPI_INDEX_PATH)} deve conter um objeto JSON")
        return errors
    errors.extend(validate_with_schema(index, CAMPI_INDEX_SCHEMA_PATH, relative(CAMPI_INDEX_PATH)))

    items = index.get("items")
    if not isinstance(items, list) or not items:
        errors.append(f"{relative(CAMPI_INDEX_PATH)}: items deve ser lista não vazia")
        return errors

    if isinstance(manifest, dict):
        colecoes = manifest.get("colecoes")
        if isinstance(colecoes, list):
            campi_collection = next((item for item in colecoes if isinstance(item, dict) and item.get("id") == "campi-ifpr"), None)
            if isinstance(campi_collection, dict) and campi_collection.get("total_itens") != len(items):
                errors.append("institucional_manifest.json: total_itens diverge do index.json")

    seen_ids: set[str] = set()
    index_paths: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            errors.append(f"{relative(CAMPI_INDEX_PATH)}: item deve ser objeto")
            continue
        campus_id = item.get("id")
        path_value = item.get("path")
        if not isinstance(campus_id, str) or not SLUG_RE.fullmatch(campus_id):
            errors.append(f"{relative(CAMPI_INDEX_PATH)}: id inválido: {campus_id}")
        elif campus_id in seen_ids:
            errors.append(f"{relative(CAMPI_INDEX_PATH)}: id duplicado: {campus_id}")
        else:
            seen_ids.add(campus_id)
        if item.get("tipo_unidade") not in TIPOS_UNIDADE_INSTITUCIONAL:
            errors.append(f"{relative(CAMPI_INDEX_PATH)}: tipo_unidade inválido em {campus_id}")
        if not isinstance(item.get("nome"), str) or not item.get("nome"):
            errors.append(f"{relative(CAMPI_INDEX_PATH)}: nome ausente em {campus_id}")
        if not isinstance(path_value, str):
            errors.append(f"{relative(CAMPI_INDEX_PATH)}: path ausente em {campus_id}")
            continue
        if not path_value.startswith("institucional/ifpr/campi/") or not path_value.endswith(".json"):
            errors.append(f"{relative(CAMPI_INDEX_PATH)}: path inválido em {campus_id}: {path_value}")
            continue
        index_paths.add(path_value)
        errors.extend(validate_campus_file(ROOT / path_value, item))

    campus_paths = {
        relative(path)
        for path in (INSTITUCIONAL_ROOT / "ifpr" / "campi").glob("*.json")
        if path.name != "index.json"
    }
    if index_paths != campus_paths:
        errors.append(
            "index.json não cobre exatamente os arquivos de campi: "
            f"index={sorted(index_paths)} arquivos={sorted(campus_paths)}"
        )

    errors.extend(validate_ppcs(manifest))
    errors.extend(validate_processos_seletivos(manifest))

    return errors


def converted_ppcs_from_campi() -> dict[str, str]:
    ppcs: dict[str, str] = {}
    for campus_path in sorted((INSTITUCIONAL_ROOT / "ifpr" / "campi").glob("*.json")):
        if campus_path.name == "index.json":
            continue
        data, errors = load_json(campus_path, f"campus {relative(campus_path)}")
        if errors or not isinstance(data, dict):
            continue
        campus_id = data.get("id")
        if not isinstance(campus_id, str):
            continue
        for curso in data.get("cursos", []):
            if not isinstance(curso, dict):
                continue
            curso_id = curso.get("id")
            ppc = curso.get("ppc")
            if not isinstance(curso_id, str) or not isinstance(ppc, dict):
                continue
            conversao = ppc.get("conversao")
            markdown_path = ppc.get("markdown_path")
            if (
                isinstance(conversao, dict)
                and conversao.get("status") == "convertido"
                and isinstance(markdown_path, str)
                and (ROOT / markdown_path).exists()
            ):
                ppcs[f"{campus_id}/{curso_id}"] = markdown_path
    return ppcs


def validate_ppc_sections(index_items_by_id: dict[str, dict[str, object]]) -> list[str]:
    errors: list[str] = []
    if not PPCS_SECOES_PATH.exists():
        return [f"{relative(PPCS_SECOES_PATH)} não encontrado"]

    required = {"id", "ppc_id", "campus_id", "curso_id", "curso_nome", "section_kind", "heading", "path", "texto"}
    seen_ids: set[str] = set()
    with PPCS_SECOES_PATH.open(encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()
            if not line:
                errors.append(f"{relative(PPCS_SECOES_PATH)}:{line_number}: linha vazia")
                continue
            try:
                item = json.loads(line)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{relative(PPCS_SECOES_PATH)}:{line_number}: JSON inválido: {exc}")
                continue
            if not isinstance(item, dict):
                errors.append(f"{relative(PPCS_SECOES_PATH)}:{line_number}: item deve ser objeto")
                continue
            missing = sorted(required - set(item))
            if missing:
                errors.append(f"{relative(PPCS_SECOES_PATH)}:{line_number}: campos ausentes: {', '.join(missing)}")
                continue
            section_id = item.get("id")
            ppc_id = item.get("ppc_id")
            if not isinstance(section_id, str) or not isinstance(ppc_id, str):
                errors.append(f"{relative(PPCS_SECOES_PATH)}:{line_number}: id e ppc_id devem ser texto")
                continue
            if section_id in seen_ids:
                errors.append(f"{relative(PPCS_SECOES_PATH)}:{line_number}: id duplicado: {section_id}")
            seen_ids.add(section_id)
            if not section_id.startswith(f"{ppc_id}#"):
                errors.append(f"{relative(PPCS_SECOES_PATH)}:{line_number}: id não deriva de ppc_id: {section_id}")
            ppc_item = index_items_by_id.get(ppc_id)
            if ppc_item is None:
                errors.append(f"{relative(PPCS_SECOES_PATH)}:{line_number}: ppc_id inexistente no índice: {ppc_id}")
                continue
            for field in ["campus_id", "curso_id", "curso_nome", "path"]:
                if item.get(field) != ppc_item.get(field):
                    errors.append(f"{relative(PPCS_SECOES_PATH)}:{line_number}: campo {field} diverge do índice para {ppc_id}")
            if item.get("section_kind") not in PPC_SECTION_KINDS:
                errors.append(f"{relative(PPCS_SECOES_PATH)}:{line_number}: section_kind inválido: {item.get('section_kind')}")
            for field in ["heading", "texto"]:
                value = item.get(field)
                if not isinstance(value, str) or not value.strip():
                    errors.append(f"{relative(PPCS_SECOES_PATH)}:{line_number}: {field} deve ser texto não vazio")
            texto = item.get("texto")
            if isinstance(texto, str) and len(texto) > 8000:
                errors.append(f"{relative(PPCS_SECOES_PATH)}:{line_number}: texto excede 8000 caracteres")

    if not seen_ids:
        errors.append(f"{relative(PPCS_SECOES_PATH)}: deve conter ao menos uma seção")
    return errors


def validate_ppcs(manifest: object) -> list[str]:
    errors: list[str] = []
    index, index_errors = load_json(PPCS_INDEX_PATH, "índice de PPCs")
    errors.extend(index_errors)
    if errors:
        return errors
    if not isinstance(index, dict):
        return [f"{relative(PPCS_INDEX_PATH)} deve conter um objeto JSON"]

    errors.extend(validate_with_schema(index, PPCS_INDEX_SCHEMA_PATH, relative(PPCS_INDEX_PATH)))
    if index.get("secoes_path") != relative(PPCS_SECOES_PATH):
        errors.append(f"{relative(PPCS_INDEX_PATH)}: secoes_path diverge do caminho esperado")

    items = index.get("items")
    if not isinstance(items, list) or not items:
        errors.append(f"{relative(PPCS_INDEX_PATH)}: items deve ser lista não vazia")
        return errors
    if index.get("total_itens") != len(items):
        errors.append(f"{relative(PPCS_INDEX_PATH)}: total_itens diverge de items")

    if isinstance(manifest, dict):
        colecoes = manifest.get("colecoes")
        if isinstance(colecoes, list):
            ppcs_collection = next((item for item in colecoes if isinstance(item, dict) and item.get("id") == "ppcs-ifpr"), None)
            if ppcs_collection is None:
                errors.append("institucional_manifest.json: coleção ppcs-ifpr ausente")
            elif ppcs_collection.get("total_itens") != len(items):
                errors.append("institucional_manifest.json: total_itens de ppcs-ifpr diverge do index.json")

    expected_ppcs = converted_ppcs_from_campi()
    seen_ids: set[str] = set()
    index_items_by_id: dict[str, dict[str, object]] = {}
    for item in items:
        if not isinstance(item, dict):
            errors.append(f"{relative(PPCS_INDEX_PATH)}: item deve ser objeto")
            continue
        ppc_id = item.get("id")
        campus_id = item.get("campus_id")
        curso_id = item.get("curso_id")
        path_value = item.get("path")
        if not isinstance(ppc_id, str):
            errors.append(f"{relative(PPCS_INDEX_PATH)}: item sem id textual")
            continue
        if ppc_id in seen_ids:
            errors.append(f"{relative(PPCS_INDEX_PATH)}: id duplicado: {ppc_id}")
        seen_ids.add(ppc_id)
        index_items_by_id[ppc_id] = item
        if isinstance(campus_id, str) and isinstance(curso_id, str) and ppc_id != f"{campus_id}/{curso_id}":
            errors.append(f"{relative(PPCS_INDEX_PATH)}: id diverge de campus_id/curso_id: {ppc_id}")
        if not isinstance(path_value, str):
            errors.append(f"{relative(PPCS_INDEX_PATH)}: path ausente em {ppc_id}")
            continue
        if not (ROOT / path_value).exists():
            errors.append(f"{relative(PPCS_INDEX_PATH)}: path inexistente em {ppc_id}: {path_value}")
        expected_path = expected_ppcs.get(ppc_id)
        if expected_path is not None and path_value != expected_path:
            errors.append(f"{relative(PPCS_INDEX_PATH)}: path diverge do campus JSON em {ppc_id}: {path_value}")

    if seen_ids != set(expected_ppcs):
        errors.append(
            "índice de PPCs não cobre exatamente os PPCs convertidos dos campi: "
            f"index={sorted(seen_ids)} campi={sorted(expected_ppcs)}"
        )

    errors.extend(validate_ppc_sections(index_items_by_id))
    return errors


def validate_processos_seletivos(manifest: object) -> list[str]:
    errors: list[str] = []
    index, index_errors = load_json(PROCESSOS_SELETIVOS_INDEX_PATH, "índice de processos seletivos")
    errors.extend(index_errors)
    if errors:
        return errors
    if not isinstance(index, dict):
        return [f"{relative(PROCESSOS_SELETIVOS_INDEX_PATH)} deve conter um objeto JSON"]

    errors.extend(validate_with_schema(index, PROCESSOS_SELETIVOS_INDEX_SCHEMA_PATH, relative(PROCESSOS_SELETIVOS_INDEX_PATH)))
    items = index.get("items")
    if not isinstance(items, list) or not items:
        errors.append(f"{relative(PROCESSOS_SELETIVOS_INDEX_PATH)}: items deve ser lista não vazia")
        return errors

    if isinstance(manifest, dict):
        colecoes = manifest.get("colecoes")
        if isinstance(colecoes, list):
            processos_collection = next(
                (item for item in colecoes if isinstance(item, dict) and item.get("id") == "processos-seletivos-ifpr"),
                None,
            )
            if isinstance(processos_collection, dict) and processos_collection.get("total_itens") != len(items):
                errors.append("institucional_manifest.json: total_itens de processos-seletivos-ifpr diverge do index.json")

    if index.get("total_itens") != len(items):
        errors.append(f"{relative(PROCESSOS_SELETIVOS_INDEX_PATH)}: total_itens diverge de items")

    seen_ids: set[str] = set()
    seen_years: set[int] = set()
    index_paths: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            errors.append(f"{relative(PROCESSOS_SELETIVOS_INDEX_PATH)}: item deve ser objeto")
            continue
        process_id = item.get("id")
        year = item.get("ano_ingresso")
        path_value = item.get("path")
        if not isinstance(process_id, str) or not SLUG_RE.fullmatch(process_id):
            errors.append(f"{relative(PROCESSOS_SELETIVOS_INDEX_PATH)}: id inválido: {process_id}")
        elif process_id in seen_ids:
            errors.append(f"{relative(PROCESSOS_SELETIVOS_INDEX_PATH)}: id duplicado: {process_id}")
        else:
            seen_ids.add(process_id)
        if isinstance(year, int):
            if year in seen_years:
                errors.append(f"{relative(PROCESSOS_SELETIVOS_INDEX_PATH)}: ano_ingresso duplicado: {year}")
            seen_years.add(year)
        if not isinstance(path_value, str):
            errors.append(f"{relative(PROCESSOS_SELETIVOS_INDEX_PATH)}: path ausente em {process_id}")
            continue
        if not path_value.startswith("institucional/ifpr/processos-seletivos/") or not path_value.endswith(".json"):
            errors.append(f"{relative(PROCESSOS_SELETIVOS_INDEX_PATH)}: path inválido em {process_id}: {path_value}")
            continue
        index_paths.add(path_value)

        process_path = ROOT / path_value
        data, json_errors = load_json(process_path, f"processo seletivo {path_value}")
        errors.extend(json_errors)
        if not isinstance(data, dict):
            continue
        errors.extend(validate_with_schema(data, PROCESSO_SELETIVO_SCHEMA_PATH, path_value))
        if data.get("id") != process_id:
            errors.append(f"{path_value}: id diverge do index.json")
        if data.get("ano_ingresso") != year:
            errors.append(f"{path_value}: ano_ingresso diverge do index.json")
        if data.get("nome") != item.get("nome"):
            errors.append(f"{path_value}: nome diverge do index.json")
        if process_path.name != f"{process_id}.json":
            errors.append(f"{path_value}: nome do arquivo diverge do id")
        for fonte in data.get("fontes", []):
            errors.extend(validate_https_url(fonte, f"{path_value}: fontes[]"))
        for edital in data.get("editais", []):
            if isinstance(edital, dict):
                errors.extend(validate_https_url(edital.get("url"), f"{path_value}: editais[].url"))
        for oferta in data.get("ofertas", []):
            if not isinstance(oferta, dict):
                continue
            fonte = oferta.get("fonte")
            if isinstance(fonte, dict):
                errors.extend(validate_https_url(fonte.get("url"), f"{path_value}: ofertas[].fonte.url"))

    process_paths = {
        relative(path)
        for path in PROCESSOS_SELETIVOS_ROOT.glob("*.json")
        if path.name != "index.json"
    }
    if index_paths != process_paths:
        errors.append(
            "index.json de processos seletivos não cobre exatamente os arquivos: "
            f"index={sorted(index_paths)} arquivos={sorted(process_paths)}"
        )

    return errors


def validate_cnct_course_file(path: Path, index_item: dict[str, object]) -> list[str]:
    errors: list[str] = []
    data, json_errors = load_json(path, f"curso CNCT {relative(path)}")
    errors.extend(json_errors)
    if errors:
        return errors
    if not isinstance(data, dict):
        return [f"{relative(path)} deve conter um objeto JSON"]
    errors.extend(validate_with_schema(data, CNCT_CURSO_SCHEMA_PATH, relative(path)))

    course_id = data.get("id")
    if not isinstance(course_id, str) or not SLUG_RE.fullmatch(course_id):
        errors.append(f"{relative(path)}: id deve ser slug ASCII minúsculo")
    elif path.name != f"{course_id}.json":
        errors.append(f"{relative(path)}: nome do arquivo diverge do id")

    for field in [
        "id",
        "denominacao",
        "denominacao_normalizada",
        "eixo_tecnologico",
        "area_tecnologica",
        "carga_horaria_minima_horas",
        "codigos_cbo",
    ]:
        if data.get(field) != index_item.get(field):
            errors.append(f"{relative(path)}: campo {field} diverge do index.json")

    codigos_cbo = data.get("codigos_cbo")
    if isinstance(codigos_cbo, list):
        seen_codes: set[str] = set()
        for codigo in codigos_cbo:
            if not isinstance(codigo, str):
                continue
            if codigo in seen_codes:
                errors.append(f"{relative(path)}: codigos_cbo duplicado: {codigo}")
            seen_codes.add(codigo)
            if codigo not in str(data.get("ocupacoes_cbo", "")):
                errors.append(f"{relative(path)}: codigos_cbo não aparece em ocupacoes_cbo: {codigo}")

    return errors


def validate_catalogos() -> list[str]:
    errors: list[str] = []
    catalogos_manifest, manifest_errors = load_json(CATALOGOS_MANIFEST_PATH, "catalogos_manifest.json")
    errors.extend(manifest_errors)
    cnct_manifest, cnct_manifest_errors = load_json(CNCT_MANIFEST_PATH, "manifesto CNCT")
    errors.extend(cnct_manifest_errors)
    cnct_index, cnct_index_errors = load_json(CNCT_INDEX_PATH, "índice CNCT")
    errors.extend(cnct_index_errors)
    if errors:
        return errors

    if not isinstance(catalogos_manifest, dict):
        errors.append("catalogos_manifest.json deve conter um objeto JSON")
    else:
        errors.extend(validate_with_schema(catalogos_manifest, CATALOGOS_MANIFEST_SCHEMA_PATH, "catalogos_manifest.json"))
        catalogos = catalogos_manifest.get("catalogos")
        if not isinstance(catalogos, list) or not catalogos:
            errors.append("catalogos_manifest.json: catalogos deve ser lista não vazia")
        else:
            cnct_collection = next((item for item in catalogos if isinstance(item, dict) and item.get("id") == "cnct"), None)
            if cnct_collection is None:
                errors.append("catalogos_manifest.json: catálogo cnct ausente")
            else:
                if cnct_collection.get("path") != relative(CNCT_MANIFEST_PATH):
                    errors.append("catalogos_manifest.json: path do catálogo cnct diverge do manifesto CNCT")

    if not isinstance(cnct_manifest, dict):
        errors.append(f"{relative(CNCT_MANIFEST_PATH)} deve conter um objeto JSON")
    else:
        errors.extend(validate_with_schema(cnct_manifest, CNCT_MANIFEST_SCHEMA_PATH, relative(CNCT_MANIFEST_PATH)))
        if cnct_manifest.get("index_path") != relative(CNCT_INDEX_PATH):
            errors.append(f"{relative(CNCT_MANIFEST_PATH)}: index_path diverge do índice CNCT")
        if cnct_manifest.get("campos_curso") != CNCT_COURSE_FIELDS:
            errors.append(f"{relative(CNCT_MANIFEST_PATH)}: campos_curso diverge do contrato esperado")
        for field in ["fonte_url", "atos_normativos_url", "catalogo_pdf_url"]:
            errors.extend(validate_https_url(cnct_manifest.get(field), f"{relative(CNCT_MANIFEST_PATH)}: {field}"))

    if not isinstance(cnct_index, dict):
        errors.append(f"{relative(CNCT_INDEX_PATH)} deve conter um objeto JSON")
        return errors
    errors.extend(validate_with_schema(cnct_index, CNCT_INDEX_SCHEMA_PATH, relative(CNCT_INDEX_PATH)))

    items = cnct_index.get("items")
    if not isinstance(items, list) or not items:
        errors.append(f"{relative(CNCT_INDEX_PATH)}: items deve ser lista não vazia")
        return errors

    if isinstance(catalogos_manifest, dict):
        catalogos = catalogos_manifest.get("catalogos")
        if isinstance(catalogos, list):
            cnct_collection = next((item for item in catalogos if isinstance(item, dict) and item.get("id") == "cnct"), None)
            if isinstance(cnct_collection, dict) and cnct_collection.get("total_itens") != len(items):
                errors.append("catalogos_manifest.json: total_itens do CNCT diverge do index.json")
    if isinstance(cnct_manifest, dict) and cnct_manifest.get("total_cursos") != len(items):
        errors.append(f"{relative(CNCT_MANIFEST_PATH)}: total_cursos diverge do index.json")
    if cnct_index.get("total_cursos") != len(items):
        errors.append(f"{relative(CNCT_INDEX_PATH)}: total_cursos diverge de items")

    seen_ids: set[str] = set()
    seen_indices: set[int] = set()
    index_paths: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            errors.append(f"{relative(CNCT_INDEX_PATH)}: item deve ser objeto")
            continue
        course_id = item.get("id")
        path_value = item.get("path")
        if not isinstance(course_id, str) or not SLUG_RE.fullmatch(course_id):
            errors.append(f"{relative(CNCT_INDEX_PATH)}: id inválido: {course_id}")
        elif course_id in seen_ids:
            errors.append(f"{relative(CNCT_INDEX_PATH)}: id duplicado: {course_id}")
        else:
            seen_ids.add(course_id)
        if not isinstance(path_value, str):
            errors.append(f"{relative(CNCT_INDEX_PATH)}: path ausente em {course_id}")
            continue
        expected_path = f"catalogos/cnct/cursos/{course_id}.json"
        if path_value != expected_path:
            errors.append(f"{relative(CNCT_INDEX_PATH)}: path inválido em {course_id}: {path_value}")
            continue
        if path_value in index_paths:
            errors.append(f"{relative(CNCT_INDEX_PATH)}: path duplicado: {path_value}")
        index_paths.add(path_value)

        course_errors_before = len(errors)
        errors.extend(validate_cnct_course_file(ROOT / path_value, item))
        if len(errors) == course_errors_before:
            course_data, _json_errors = load_json(ROOT / path_value, f"curso CNCT {path_value}")
            if isinstance(course_data, dict):
                indice = course_data.get("indice")
                if isinstance(indice, int):
                    if indice in seen_indices:
                        errors.append(f"{path_value}: indice duplicado: {indice}")
                    seen_indices.add(indice)

    course_paths = {relative(path) for path in CNCT_CURSOS_ROOT.glob("*.json")}
    if index_paths != course_paths:
        errors.append(
            "index.json não cobre exatamente os arquivos de cursos CNCT: "
            f"index={sorted(index_paths)} arquivos={sorted(course_paths)}"
        )

    expected_catalog_files = {
        relative(CNCT_MANIFEST_PATH),
        relative(CNCT_INDEX_PATH),
        *course_paths,
    }
    actual_catalog_files = {relative(path) for path in CATALOGOS_ROOT.rglob("*.json")}
    actual_catalog_files.discard("catalogos_manifest.json")
    if actual_catalog_files != expected_catalog_files:
        errors.append(
            "catalogos/ contém arquivos JSON fora do contrato esperado: "
            f"esperado={sorted(expected_catalog_files)} arquivos={sorted(actual_catalog_files)}"
        )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check-ppc-artifacts",
        action="store_true",
        help="Também acusa artefatos conhecidos de conversão nos PPCs em Markdown.",
    )
    args = parser.parse_args()

    errors: list[str] = []
    if any(ROOT.rglob(".DS_Store")):
        errors.append("há arquivos .DS_Store no repositório")
    errors.extend(validate_local_patterns())

    manifest, manifest_errors = load_manifest()
    errors.extend(manifest_errors)

    root_markdown_paths = [path.name for path in ROOT.glob("*.md") if path.name not in {"AGENTS.md", "README.md"}]
    if root_markdown_paths:
        errors.append(f"normas não devem ficar na raiz do repositório: {sorted(root_markdown_paths)}")

    manifest_paths = {item.get("path") for item in manifest if isinstance(item, dict)}
    markdown_paths = {relative(path) for path in NORMAS_ROOT.rglob("*.md")}
    if manifest_paths != markdown_paths:
        errors.append(
            "manifest.json não cobre exatamente as normas publicadas: "
            f"manifest={sorted(manifest_paths)} markdown={sorted(markdown_paths)}"
        )

    readme_text = README_PATH.read_text(encoding="utf-8")
    for pattern in LOCAL_PATTERNS:
        if pattern in readme_text:
            errors.append(f"README.md contém padrão local proibido: {pattern}")
    errors.extend(validate_links(README_PATH, readme_text))
    errors.extend(validate_institucional())
    errors.extend(validate_catalogos())
    if args.check_ppc_artifacts:
        errors.extend(validate_ppc_conversion_artifacts())

    for path in sorted(NORMAS_ROOT.rglob("*.md")):
        errors.extend(validate_markdown(path))

    for item in manifest:
        if not isinstance(item, dict):
            errors.append("manifest.json contém item que não é objeto")
            continue
        for field in [*MANIFEST_FIELDS, "path"]:
            if field not in item:
                errors.append(f"manifest.json: item sem campo {field}: {item}")
        errors.extend(validate_manifest_item(item))

    if errors:
        for error in errors:
            print(f"ERRO: {error}", file=sys.stderr)
        return 1
    print(f"Base válida: {len(manifest)} normas publicadas, metadados institucionais e catálogos conferidos.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
