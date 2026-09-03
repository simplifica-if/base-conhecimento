from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from common import BASE_ANALISE_DIR, FICHAS_DIR, SCHEMAS_DIR, TOPICOS_FICHAS_PATH, VALIDACOES_CRUZADAS_DIR, read_json


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


TIPOS_ESCOPO_TOPICO = {"tematico", "multitematico", "transversal", "condicional"}


def _validar_topicos_fichas(fichas_por_id: dict[str, dict[str, Any]]) -> list[str]:
    erros: list[str] = []
    ids_fichas = set(fichas_por_id)
    if not TOPICOS_FICHAS_PATH.exists():
        return [f"{TOPICOS_FICHAS_PATH}: arquivo de taxonomia não encontrado"]
    try:
        payload = read_json(TOPICOS_FICHAS_PATH)
    except json.JSONDecodeError as exc:
        return [f"{TOPICOS_FICHAS_PATH}: JSON inválido: {exc}"]
    if not isinstance(payload, dict):
        return [f"{TOPICOS_FICHAS_PATH}: payload deve ser objeto JSON"]
    topicos = payload.get("topicos")
    if not isinstance(topicos, list) or not topicos:
        return [f"{TOPICOS_FICHAS_PATH}: campo `topicos` deve ser lista não vazia"]

    ids_topicos: set[str] = set()
    fichas_cobertas: set[str] = set()
    for indice, topico in enumerate(topicos, start=1):
        if not isinstance(topico, dict):
            erros.append(f"{TOPICOS_FICHAS_PATH}: tópico {indice} deve ser objeto JSON")
            continue
        topico_id = str(topico.get("id") or "").strip()
        if not topico_id:
            erros.append(f"{TOPICOS_FICHAS_PATH}: tópico {indice} sem id")
        elif topico_id in ids_topicos:
            erros.append(f"{TOPICOS_FICHAS_PATH}: tópico duplicado: {topico_id}")
        ids_topicos.add(topico_id)
        for campo in ("titulo", "descricao", "tipo_escopo"):
            if not str(topico.get(campo) or "").strip():
                erros.append(f"{TOPICOS_FICHAS_PATH}: tópico {topico_id or indice} sem `{campo}`")
        tipo_escopo = str(topico.get("tipo_escopo") or "")
        if tipo_escopo and tipo_escopo not in TIPOS_ESCOPO_TOPICO:
            erros.append(f"{TOPICOS_FICHAS_PATH}: tópico {topico_id or indice} tem tipo_escopo inválido: {tipo_escopo}")
        for campo in ("aliases_titulo", "termos_busca", "fichas"):
            valores = topico.get(campo)
            if not isinstance(valores, list):
                erros.append(f"{TOPICOS_FICHAS_PATH}: tópico {topico_id or indice} deve ter `{campo}` como lista")
                continue
            if campo in {"aliases_titulo", "termos_busca"} and not valores:
                erros.append(f"{TOPICOS_FICHAS_PATH}: tópico {topico_id or indice} deve ter `{campo}` não vazio")
            if campo == "fichas":
                if not valores:
                    erros.append(f"{TOPICOS_FICHAS_PATH}: tópico {topico_id or indice} deve citar ao menos uma ficha")
                for ficha_id in valores:
                    ficha_id = str(ficha_id)
                    if ficha_id not in ids_fichas:
                        erros.append(f"{TOPICOS_FICHAS_PATH}: tópico {topico_id or indice} cita ficha desconhecida: {ficha_id}")
                    fichas_cobertas.add(ficha_id)

    faltantes = sorted(ids_fichas - fichas_cobertas)
    if faltantes:
        erros.append(f"{TOPICOS_FICHAS_PATH}: fichas sem tópico temático: {', '.join(faltantes)}")
    for ficha_id, ficha in sorted(fichas_por_id.items()):
        topicos_ficha = ficha.get("topicos_tematicos")
        if "secoes_preferenciais" in ficha:
            erros.append(f"{ficha_id}: campo legado `secoes_preferenciais` não é aceito")
        if not isinstance(topicos_ficha, list) or not topicos_ficha:
            erros.append(f"{ficha_id}: `topicos_tematicos` deve ser lista não vazia")
            continue
        declarados = {str(valor) for valor in topicos_ficha}
        desconhecidos = sorted(declarados - ids_topicos)
        if desconhecidos:
            erros.append(f"{ficha_id}: tópicos desconhecidos: {', '.join(desconhecidos)}")
        esperados = {
            str(topico.get("id"))
            for topico in topicos
            if ficha_id in {str(valor) for valor in topico.get("fichas", [])}
        }
        if declarados != esperados:
            erros.append(
                f"{ficha_id}: topicos_tematicos divergente da taxonomia "
                f"(ficha={sorted(declarados)}, taxonomia={sorted(esperados)})"
            )
        ancoras = ficha.get("ancoras_semanticas")
        if not isinstance(ancoras, list) or not any(str(valor).strip() for valor in ancoras):
            erros.append(f"{ficha_id}: `ancoras_semanticas` deve ser lista não vazia")
    return erros


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

    fichas_por_id: dict[str, dict[str, Any]] = {}
    for ficha_path in sorted(FICHAS_DIR.glob("*.json")):
        erros.extend(_validar_arquivo_json(ficha_path, schema_ficha))
        payload = read_json(ficha_path)
        ficha_id = str(payload.get("id") or "")
        if ficha_id in fichas_por_id:
            erros.append(f"{ficha_path}: ficha duplicada: {ficha_id}")
        fichas_por_id[ficha_id] = payload
    erros.extend(_validar_topicos_fichas(fichas_por_id))

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
