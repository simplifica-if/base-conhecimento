from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from common import BASE_ANALISE_DIR, FICHAS_DIR, SCHEMAS_DIR, VALIDACOES_CRUZADAS_DIR, read_json


class ErroValidacaoBaseAnalise(ValueError):
    pass


def _tipo_json(valor: Any) -> str:
    if isinstance(valor, bool):
        return "boolean"
    if isinstance(valor, int) and not isinstance(valor, bool):
        return "integer"
    if isinstance(valor, float):
        return "number"
    if isinstance(valor, str):
        return "string"
    if isinstance(valor, list):
        return "array"
    if isinstance(valor, dict):
        return "object"
    if valor is None:
        return "null"
    return type(valor).__name__


def _tipo_compativel(valor: Any, esperado: str | list[str]) -> bool:
    tipos = esperado if isinstance(esperado, list) else [esperado]
    tipo = _tipo_json(valor)
    return tipo in tipos or (tipo == "integer" and "number" in tipos)


def _validar_schema(valor: Any, schema: dict[str, Any], caminho: str = "$") -> list[str]:
    erros: list[str] = []
    alternativas = schema.get("anyOf")
    if isinstance(alternativas, list):
        if any(not _validar_schema(valor, alternativa, caminho) for alternativa in alternativas if isinstance(alternativa, dict)):
            return []
        return [f"{caminho}: não corresponde a nenhuma alternativa de anyOf"]

    esperado = schema.get("type")
    if esperado is not None and not _tipo_compativel(valor, esperado):
        return [f"{caminho}: tipo {_tipo_json(valor)}; esperado {esperado}"]

    enum = schema.get("enum")
    if isinstance(enum, list) and valor not in enum:
        erros.append(f"{caminho}: valor {valor!r} fora do enum")

    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        minimo = schema.get("minimum")
        maximo = schema.get("maximum")
        if isinstance(minimo, (int, float)) and valor < minimo:
            erros.append(f"{caminho}: valor {valor} menor que {minimo}")
        if isinstance(maximo, (int, float)) and valor > maximo:
            erros.append(f"{caminho}: valor {valor} maior que {maximo}")

    if isinstance(valor, dict):
        required = schema.get("required")
        if isinstance(required, list):
            for campo in required:
                if campo not in valor:
                    erros.append(f"{caminho}: campo obrigatório ausente: {campo}")
        properties = schema.get("properties")
        if isinstance(properties, dict):
            for campo, sub_schema in properties.items():
                if campo in valor and isinstance(sub_schema, dict):
                    erros.extend(_validar_schema(valor[campo], sub_schema, f"{caminho}.{campo}"))

    if isinstance(valor, list):
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for indice, item in enumerate(valor):
                erros.extend(_validar_schema(item, item_schema, f"{caminho}[{indice}]"))

    return erros


def _carregar_schema(nome: str) -> dict[str, Any]:
    payload = read_json(SCHEMAS_DIR / nome)
    if not isinstance(payload, dict):
        raise ErroValidacaoBaseAnalise(f"Schema inválido: {nome}")
    return payload


def _validar_arquivo_json(path: Path, schema: dict[str, Any]) -> list[str]:
    try:
        payload = read_json(path)
    except json.JSONDecodeError as exc:
        return [f"{path}: JSON inválido: {exc}"]
    return [f"{path}: {erro}" for erro in _validar_schema(payload, schema)]


def validar_base_analise() -> list[str]:
    erros: list[str] = []
    schema_ficha = _carregar_schema("ficha.schema.json")
    schema_validacao = _carregar_schema("validacao-cruzada.schema.json")
    schema_resultado = _carregar_schema("resultado-lote.schema.json")
    schema_alertas = _carregar_schema("alertas-transversais.schema.json")

    for schema_path in sorted(SCHEMAS_DIR.glob("*.schema.json")):
        payload = read_json(schema_path)
        if not isinstance(payload, dict) or payload.get("type") != "object":
            erros.append(f"{schema_path}: schema deve ser objeto com type=object")

    ids_fichas: set[str] = set()
    for ficha_path in sorted(FICHAS_DIR.glob("*.json")):
        erros.extend(_validar_arquivo_json(ficha_path, schema_ficha))
        payload = read_json(ficha_path)
        ficha_id = str(payload.get("id") or "")
        if ficha_id in ids_fichas:
            erros.append(f"{ficha_path}: ficha duplicada: {ficha_id}")
        ids_fichas.add(ficha_id)

    ids_validacoes: set[str] = set()
    for validacao_path in sorted(VALIDACOES_CRUZADAS_DIR.glob("*.json")):
        erros.extend(_validar_arquivo_json(validacao_path, schema_validacao))
        payload = read_json(validacao_path)
        validacao_id = str(payload.get("id") or "")
        if validacao_id in ids_validacoes:
            erros.append(f"{validacao_path}: validação cruzada duplicada: {validacao_id}")
        ids_validacoes.add(validacao_id)

    erros.extend(_validar_arquivo_json(BASE_ANALISE_DIR / "contratos" / "resposta_lote.exemplo.json", schema_resultado))
    erros.extend(
        _validar_schema(
            {
                "alertas_transversais": [
                    {
                        "id": "ALERTA-001",
                        "validacao_id": "VC-EXEMPLO",
                        "titulo": "Alerta transversal",
                        "criticidade": "OBRIG",
                        "descricao": "Descrição objetiva.",
                        "fichas_relacionadas": ["CT-IDENT-01"],
                        "evidencias": ["Evidência textual."],
                        "revisao_humana_obrigatoria": True,
                    }
                ]
            },
            schema_alertas,
        )
    )
    return erros


def main() -> int:
    erros = validar_base_analise()
    if erros:
        for erro in erros:
            print(erro)
        return 1
    print("Base de análise válida.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
