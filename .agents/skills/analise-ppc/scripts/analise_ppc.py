from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common import round_paths, write_json
from gerar_relatorio_html import gerar_relatorio_html, validar_resultados_rodada
from preparar_documento import preparar_documento
from publicar_surge import dominio_surge_padrao, preparar_site_surge, publicar_site_surge
from subagents import (
    mesclar_resultados_avulsos,
    montar_grupo_avulso,
    montar_grupos_subagents,
    preparar_prompts_subagents,
)


def _print_payload(payload: object) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _relatorio_payload(path: Path, publicacao: dict[str, object] | None = None) -> dict[str, object]:
    relatorio = path.resolve()
    payload: dict[str, object] = {
        "relatorio_html": str(relatorio),
        "relatorio_url": relatorio.as_uri(),
        "mensagem": f"Relatório pronto: {relatorio.as_uri()}",
    }
    if publicacao:
        public_url = str(publicacao.get("public_url") or "")
        payload.update(
            {
                "publicacao_servico": publicacao.get("servico"),
                "publicacao_url": public_url,
                "surge_url": public_url,
                "surge_domain": publicacao.get("domain"),
                "mensagem": f"Relatório pronto: {public_url or relatorio.as_uri()}",
            }
        )
    return payload


def _resumo_grupos_subagents(payload: dict[str, object]) -> dict[str, object]:
    grupos = payload.get("grupos") if isinstance(payload.get("grupos"), list) else []
    cnct = payload.get("cnct_contexto") if isinstance(payload.get("cnct_contexto"), dict) else {}
    correspondencia = cnct.get("correspondencia") if isinstance(cnct.get("correspondencia"), dict) else {}
    return {
        "rodada_dir": payload.get("rodada_dir"),
        "ppc_markdown": payload.get("ppc_markdown"),
        "grupos_subagents": payload.get("grupos_subagents_path") or payload.get("grupos_subagents"),
        "cnct_contexto_path": payload.get("cnct_contexto_path"),
        "contexto_estrutural_path": payload.get("contexto_estrutural_path"),
        "validacoes_cruzadas_path": payload.get("validacoes_cruzadas_path"),
        "curso": payload.get("curso"),
        "total_fichas": payload.get("total_fichas"),
        "tamanho_grupo": payload.get("tamanho_grupo"),
        "total_grupos": len(grupos),
        "grupos": [
            {
                "grupo_id": grupo.get("grupo_id"),
                "intervalo": grupo.get("intervalo"),
                "total_fichas": grupo.get("total_fichas"),
                "requer_contexto_cnct": grupo.get("requer_contexto_cnct", False),
                "requer_fundamentacao_normativa": grupo.get("requer_fundamentacao_normativa", False),
                "requer_anexos_visuais": grupo.get("requer_anexos_visuais", False),
            }
            for grupo in grupos
            if isinstance(grupo, dict)
        ],
        "cnct_correspondencia": {
            "denominacao": correspondencia.get("denominacao"),
            "eixo_tecnologico": correspondencia.get("eixo_tecnologico"),
            "score": correspondencia.get("score"),
            "tipo_correspondencia": correspondencia.get("tipo_correspondencia"),
        },
    }


def cmd_preparar_documento(args: argparse.Namespace) -> int:
    payload = preparar_documento(
        arquivo_entrada=Path(args.arquivo),
        output_base=Path(args.saida_base) if args.saida_base else None,
    )
    _print_payload(payload["resumo"])
    return 0


def cmd_montar_grupos_subagents(args: argparse.Namespace) -> int:
    payload = montar_grupos_subagents(
        rodada_dir=Path(args.rodada_dir),
        tamanho_grupo=args.tamanho_grupo,
    )
    _print_payload(payload if args.detalhado else _resumo_grupos_subagents(payload))
    return 0


def cmd_preparar_prompts_subagents(args: argparse.Namespace) -> int:
    payload = preparar_prompts_subagents(rodada_dir=Path(args.rodada_dir))
    _print_payload(payload)
    return 0


def cmd_gerar_relatorio_html(args: argparse.Namespace) -> int:
    payload = gerar_relatorio_html(
        rodada_dir=Path(args.rodada_dir),
        resultados_path=Path(args.resultados),
    )
    publicacao = None
    if not args.sem_surge:
        caminhos = round_paths(Path(args.rodada_dir))
        site_dir = preparar_site_surge(
            payload["relatorio_html"],
            caminhos["suporte_dir"] / "surge-site",
        )
        publicacao = publicar_site_surge(
            site_dir,
            dominio=args.surge_domain or dominio_surge_padrao(caminhos["rodada_dir"]),
        )
        publicacao["relatorio_html_original"] = str(Path(payload["relatorio_html"]).resolve())
        write_json(caminhos["suporte_dir"] / "surge-publicacao.json", publicacao)
    _print_payload(_relatorio_payload(payload["relatorio_html"], publicacao=publicacao))
    return 0


def cmd_validar_resultados(args: argparse.Namespace) -> int:
    payload = validar_resultados_rodada(
        rodada_dir=Path(args.rodada_dir),
        resultados_path=Path(args.resultados),
    )
    _print_payload(payload)
    return 0


def cmd_montar_grupo_avulso(args: argparse.Namespace) -> int:
    payload = montar_grupo_avulso(
        rodada_dir=Path(args.rodada_dir),
        ficha_ids=list(args.ficha_id or []),
    )
    _print_payload(payload)
    return 0


def cmd_mesclar_resultados_avulsos(args: argparse.Namespace) -> int:
    payload = mesclar_resultados_avulsos(
        rodada_dir=Path(args.rodada_dir),
        resultados_base_path=Path(args.resultados_base),
        resultados_avulsos_path=Path(args.resultados_avulsos),
        saida_path=Path(args.saida) if args.saida else None,
    )
    _print_payload(payload)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Análise de PPC por sub-agentes na conversa")
    subparsers = parser.add_subparsers(dest="subcomando", required=True)

    parser_preparar = subparsers.add_parser("preparar-documento", help="Criar a rodada e o PPC.md canônico")
    parser_preparar.add_argument("arquivo", type=str, help="Arquivo .md ou .docx de entrada")
    parser_preparar.add_argument("--saida-base", type=str, help="Diretório base opcional para a rodada")
    parser_preparar.set_defaults(func=cmd_preparar_documento)

    parser_grupos = subparsers.add_parser(
        "montar-grupos-subagents",
        help="Listar grupos de fichas para sub-agentes e salvar grupos-subagents.json",
    )
    parser_grupos.add_argument("--rodada-dir", type=str, required=True, help="Diretório da rodada")
    parser_grupos.add_argument("--tamanho-grupo", type=int, default=20, help="Quantidade de fichas por grupo")
    parser_grupos.add_argument(
        "--detalhado",
        action="store_true",
        help="Imprimir o JSON completo; por padrão a CLI mostra apenas um resumo e salva o payload completo.",
    )
    parser_grupos.set_defaults(func=cmd_montar_grupos_subagents)

    parser_prompts = subparsers.add_parser(
        "preparar-prompts-subagents",
        help="Gerar pacotes Markdown autocontidos para cada grupo de sub-agente",
    )
    parser_prompts.add_argument("--rodada-dir", type=str, required=True, help="Diretório da rodada")
    parser_prompts.set_defaults(func=cmd_preparar_prompts_subagents)

    parser_avulso = subparsers.add_parser(
        "montar-grupo-avulso",
        help="Montar um grupo avulso de fichas para reavaliação por sub-agente",
    )
    parser_avulso.add_argument("--rodada-dir", type=str, required=True, help="Diretório da rodada")
    parser_avulso.add_argument("--ficha-id", action="append", required=True, help="Ficha a incluir no grupo avulso")
    parser_avulso.set_defaults(func=cmd_montar_grupo_avulso)

    parser_mesclar = subparsers.add_parser(
        "mesclar-resultados-avulsos",
        help="Mesclar respostas avulsas em resultados-subagents.json",
    )
    parser_mesclar.add_argument("--rodada-dir", type=str, required=True, help="Diretório da rodada")
    parser_mesclar.add_argument(
        "--resultados-base",
        type=str,
        default="resultados-subagents.json",
        help="JSON base de resultados; relativo a arquivos-suporte quando não absoluto",
    )
    parser_mesclar.add_argument(
        "--resultados-avulsos",
        type=str,
        required=True,
        help="JSON retornado pelo sub-agente avulso; relativo a arquivos-suporte quando não absoluto",
    )
    parser_mesclar.add_argument(
        "--saida",
        type=str,
        help="Destino do JSON mesclado; padrão: sobrescreve --resultados-base",
    )
    parser_mesclar.set_defaults(func=cmd_mesclar_resultados_avulsos)

    parser_relatorio = subparsers.add_parser("gerar-relatorio-html", help="Gerar o relatório HTML final")
    parser_relatorio.add_argument("--rodada-dir", type=str, required=True, help="Diretório da rodada")
    parser_relatorio.add_argument(
        "--resultados",
        type=str,
        default="resultados-subagents.json",
        help="JSON coletado dos sub-agentes; relativo a arquivos-suporte quando não absoluto",
    )
    parser_relatorio.add_argument(
        "--sem-surge",
        action="store_true",
        help="Gerar apenas o HTML local, sem publicar no Surge.",
    )
    parser_relatorio.add_argument(
        "--surge-domain",
        type=str,
        help="Domínio Surge de publicação; padrão: analise-ppc-<rodada>.surge.sh.",
    )
    parser_relatorio.set_defaults(func=cmd_gerar_relatorio_html)

    parser_validar_resultados = subparsers.add_parser(
        "validar-resultados",
        help="Validar cobertura e contrato do JSON de resultados sem gerar HTML",
    )
    parser_validar_resultados.add_argument("--rodada-dir", type=str, required=True, help="Diretório da rodada")
    parser_validar_resultados.add_argument(
        "--resultados",
        type=str,
        default="resultados-subagents.json",
        help="JSON coletado dos sub-agentes; relativo a arquivos-suporte quando não absoluto",
    )
    parser_validar_resultados.set_defaults(func=cmd_validar_resultados)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
