#!/usr/bin/env python3
"""Atualiza campos SEI de Movimentações de Cursos no Notion.

Por padrão roda em dry-run. Use --apply para gravar no Notion.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from datetime import date, datetime
from pathlib import Path
from typing import Any

from notion_client import NotionClient
from notion_exportar_base_publica import date_start, plain_text, select_name


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "base-conhecimento" / "config" / "notion.json"
DEFAULT_SEI_CLI = PROJECT_ROOT.parent / "sei-cli"
PROCESSO_RE = re.compile(r"\d{5}\.\d{6}/\d{4}-\d{2}")
ACTIVE_STATUSES = {
    "Não iniciada",
    "A fazer",
    "Em instrução no campus",
    "Em análise Proens",
    "CONSEP",
    "CONSUP",
    "Aguardando ato/publicação",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="grava as alterações no Notion")
    parser.add_argument("--ultimos", type=int, default=4, help="quantidade de eventos recentes no resumo")
    parser.add_argument("--limit", type=int, help="limita a quantidade de movimentações do escopo")
    parser.add_argument("--processo", action="append", default=[], help="filtra por processo SEI; pode repetir")
    parser.add_argument("--page-id", action="append", default=[], help="filtra por página Notion; pode repetir")
    parser.add_argument("--include-finalizadas", action="store_true", help="inclui Concluído e Arquivado")
    parser.add_argument("--sei-cli", type=Path, default=DEFAULT_SEI_CLI, help="caminho do checkout sei-cli")
    parser.add_argument(
        "--report",
        type=Path,
        default=PROJECT_ROOT / "tmp" / "movimentacoes_sei_atualizacao.jsonl",
        help="arquivo JSONL de relatório",
    )
    return parser.parse_args()


def load_config() -> dict[str, Any]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def norm_process(value: str) -> str:
    match = PROCESSO_RE.search(value or "")
    return match.group(0) if match else ""


def query_all(client: NotionClient, data_source_id: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    cursor: str | None = None
    while True:
        payload: dict[str, Any] = {"page_size": 100}
        if cursor:
            payload["start_cursor"] = cursor
        response = client.request("POST", f"/data_sources/{data_source_id}/query", payload)
        results.extend(response.get("results", []))
        if not response.get("has_more"):
            return results
        cursor = response.get("next_cursor")


def collect_scope(pages: list[dict[str, Any]], args: argparse.Namespace) -> list[dict[str, Any]]:
    wanted_processes = {norm_process(item) for item in args.processo}
    wanted_processes.discard("")
    wanted_pages = set(args.page_id)
    statuses = set(ACTIVE_STATUSES)
    if args.include_finalizadas:
        statuses.update({"Concluído", "Arquivado"})

    scope: list[dict[str, Any]] = []
    for page in pages:
        props = page["properties"]
        processo = norm_process(plain_text(props.get("SEI Processo")))
        situacao = select_name(props.get("Situação"))
        if not processo or situacao not in statuses:
            continue
        if wanted_processes and processo not in wanted_processes:
            continue
        if wanted_pages and page["id"] not in wanted_pages:
            continue
        scope.append(
            {
                "page": page,
                "page_id": page["id"],
                "processo": processo,
                "titulo": plain_text(props.get("Movimentação")),
                "situacao": situacao,
                "data_ultima_mov_atual": date_start(props.get("SEI data Última mov.")),
            }
        )

    scope.sort(key=lambda item: (item["processo"], item["titulo"], item["page_id"]))
    return scope[: args.limit] if args.limit else scope


def run_sei_lote(processos: list[str], args: argparse.Namespace) -> dict[str, dict[str, Any]]:
    if not args.sei_cli.exists():
        raise RuntimeError(f"Checkout sei-cli não encontrado: {args.sei_cli}")
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".txt", delete=False) as handle:
        for processo in processos:
            handle.write(f"{processo}\n")
        processos_path = Path(handle.name)

    command = [
        "bun",
        "run",
        "sei",
        "extrair",
        "ultimas-movimentacoes",
        "lote",
        str(processos_path),
        "--ultimos",
        str(args.ultimos),
        "--jsonl",
        "--quiet",
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=args.sei_cli,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=max(120, 90 * len(processos)),
        )
    finally:
        processos_path.unlink(missing_ok=True)

    summaries: dict[str, dict[str, Any]] = {}
    for raw_line in completed.stdout.splitlines():
        line = raw_line.strip()
        if not line.startswith("{"):
            continue
        item = json.loads(line)
        summaries[item["numero_processo"]] = item

    if completed.returncode != 0:
        erro = completed.stderr.strip() or completed.stdout.strip()
        if not summaries:
            raise RuntimeError(f"sei-cli falhou sem JSONL aproveitável: {erro}")
    return summaries


def rich_text_chunks(text: str) -> dict[str, Any]:
    if not text:
        return {"rich_text": []}
    chunks = []
    remaining = text
    while remaining:
        chunk = remaining[:1800]
        if len(remaining) > 1800:
            cut = chunk.rfind("\n")
            if cut > 500:
                chunk = chunk[:cut]
        chunks.append({"type": "text", "text": {"content": chunk}})
        remaining = remaining[len(chunk) :]
    return {"rich_text": chunks}


def date_prop(value: str) -> dict[str, Any]:
    return {"date": {"start": value} if value else None}


def linked_process(processo: str, link: str | None) -> dict[str, Any]:
    text: dict[str, Any] = {"content": processo}
    if link:
        text["link"] = {"url": link}
    return {"rich_text": [{"type": "text", "text": text}]}


def br_date(value: str | None) -> str:
    if not value:
        return ""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00")).date() if "T" in value else date.fromisoformat(value[:10])
        return parsed.strftime("%d/%m/%y")
    except ValueError:
        return value[:10]


def preserved_notes(text: str) -> str:
    text = text.strip()
    marker = "Notas anteriores preservadas"
    if marker in text:
        return text.split(marker, 1)[1].strip()
    if text.startswith("Revisado em ") and "via sei-cli" in text.splitlines()[0]:
        lines = text.splitlines()[1:]
        while lines and not lines[0].strip():
            lines.pop(0)
        return "\n".join(lines).strip()
    return text


def make_observacoes(existing: str, resumo: dict[str, Any], today_br: str) -> str:
    historico = resumo.get("historico_usado") or []
    parts = [f"Revisado em {today_br} via sei-cli.", "", "Evidências de andamento remoto"]
    for item in historico[:4]:
        unidade = f" ({item.get('unidade')})" if item.get("unidade") else ""
        parts.append(f"- Histórico em {br_date(item.get('ocorrido_em'))}: {item.get('descricao', '').strip()}{unidade}.")
    parts.extend(["", "Datas de controle"])
    if resumo.get("data_abertura_sei"):
        parts.append(f"- Data de abertura SEI: {br_date(resumo.get('data_abertura_sei'))}.")
    parts.append(f"- Data Última mov. SEI: {br_date(resumo.get('data_ultima_mov_sei'))}.")
    parts.append("- Última movimentação SEI: resumo das quatro movimentações recentes registrado no campo próprio.")
    parts.extend(
        [
            "",
            "Observação técnica",
            "- Dados atualizados por consulta remota ao histórico do SEI com `sei-cli extrair ultimas-movimentacoes lote`.",
        ]
    )
    if resumo.get("consultado_remotamente_em"):
        parts.append(f"- Consulta remota realizada em {br_date(resumo.get('consultado_remotamente_em'))}.")
    previous = preserved_notes(existing)
    if previous:
        parts.extend(["", "Notas anteriores preservadas", previous])
    return "\n".join(parts).strip()


def build_payload(item: dict[str, Any], resumo: dict[str, Any], today: str) -> dict[str, Any]:
    processo = item["processo"]
    page = item["page"]
    props = page["properties"]
    data_ultima = resumo.get("data_ultima_mov_sei") or ""
    if not data_ultima:
        raise ValueError(f"{processo}: sei-cli não retornou data_ultima_mov_sei; mantendo Notion inalterado.")
    return {
        "properties": {
            "SEI Processo": linked_process(processo, resumo.get("sei_link_processo")),
            "SEI Data de abertura": date_prop(resumo.get("data_abertura_sei") or ""),
            "SEI data Última mov.": date_prop(data_ultima),
            "SEI Última movimentação": rich_text_chunks((resumo.get("ultima_movimentacao_sei_texto") or "").strip()),
            "SEI Observações": rich_text_chunks(make_observacoes(plain_text(props.get("SEI Observações")), resumo, br_date(today))),
            "Verificado em": date_prop(today),
        }
    }


def main() -> int:
    args = parse_args()
    client = NotionClient.from_env()
    config = load_config()
    data_source_id = config["databases"]["movimentacoes_cursos"]["data_source_id"]
    scope = collect_scope(query_all(client, data_source_id), args)
    if not scope:
        print("Nenhuma movimentação encontrada no escopo.")
        return 0

    processes = sorted({item["processo"] for item in scope})
    summaries = run_sei_lote(processes, args)
    today = date.today().isoformat()
    args.report.parent.mkdir(parents=True, exist_ok=True)
    changed = 0
    ok = 0
    errors = 0

    with args.report.open("w", encoding="utf-8") as report:
        for item in scope:
            processo = item["processo"]
            lote_item = summaries.get(processo)
            record = {
                "processo": processo,
                "page_id": item["page_id"],
                "titulo": item["titulo"],
                "situacao": item["situacao"],
                "apply": bool(args.apply),
            }
            try:
                if not lote_item:
                    raise ValueError("processo ausente na saída JSONL do sei-cli")
                if not lote_item.get("ok"):
                    raise ValueError(lote_item.get("erro") or "sei-cli retornou ok=false")
                resumo = lote_item.get("resumo_movimentacao") or {}
                payload = build_payload(item, resumo, today)
                data_nova = resumo.get("data_ultima_mov_sei") or ""
                mudou = item["data_ultima_mov_atual"] != data_nova
                record.update(
                    {
                        "ok": True,
                        "data_ultima_mov_anterior": item["data_ultima_mov_atual"],
                        "data_ultima_mov_sei": data_nova,
                        "mudou_data": mudou,
                    }
                )
                if args.apply:
                    client.request("PATCH", f"/pages/{item['page_id']}", payload)
                ok += 1
                changed += int(mudou)
                status = "MUDARIA" if mudou and not args.apply else "MUDOU" if mudou else "igual"
                print(f"{status}: {item['data_ultima_mov_atual'] or '∅'} -> {data_nova} | {processo} | {item['titulo']}")
            except Exception as exc:
                errors += 1
                record.update({"ok": False, "erro": str(exc)})
                print(f"ERRO: {processo} | {item['titulo']} | {exc}", file=sys.stderr)
            report.write(json.dumps(record, ensure_ascii=False) + "\n")

    modo = "apply" if args.apply else "dry-run"
    print(json.dumps({"modo": modo, "registros": len(scope), "ok": ok, "datas_alteradas": changed, "erros": errors, "relatorio": str(args.report)}, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
