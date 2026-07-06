from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from common import BASE_ANALISE_DIR, FICHAS_DIR, TOPICOS_FICHAS_PATH, read_json, write_text


MAPA_FICHAS_PATH = BASE_ANALISE_DIR / "mapa-fichas.md"


def _fichas_por_id() -> dict[str, dict[str, Any]]:
    return {
        str(payload["id"]): payload
        for payload in (
            read_json(path)
            for path in sorted(FICHAS_DIR.glob("*.json"))
        )
    }


def _carregar_topicos() -> list[dict[str, Any]]:
    payload = read_json(TOPICOS_FICHAS_PATH)
    return list(payload.get("topicos", []))


def _linha_ficha(ficha: dict[str, Any]) -> str:
    criticidade = ficha.get("criticidade", "")
    dominio = ficha.get("dominio", "")
    return f"- `{ficha['id']}` ({criticidade}, {dominio}) - {ficha['titulo']}"


def gerar_mapa_fichas(gerado_em: str | None = None) -> str:
    fichas_por_id = _fichas_por_id()
    topicos = _carregar_topicos()
    topicos_por_grupo: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for topico in topicos:
        topicos_por_grupo[str(topico.get("grupo") or "Outros")].append(topico)

    linhas = [
        "# Mapa de fichas da análise de PPC",
        "",
        "Este mapa organiza as fichas por tópicos semânticos, sem depender da numeração das seções do PPC.",
        "A numeração observada em um PPC específico deve ser detectada na rodada de análise, não codificada na ficha.",
        "",
        f"Gerado em: {gerado_em or datetime.now(UTC).replace(microsecond=0).isoformat()}",
        "",
        "## Como usar",
        "",
        "- Use os tópicos para localizar rapidamente quais fichas tratam de estágio, avaliação, AEE, infraestrutura, referências e outros temas.",
        "- Use `aliases_titulo` e `termos_busca` de `topicos-fichas.json` para localizar a seção correspondente mesmo quando o PPC usar outro título ou outra numeração.",
        "- Fichas transversais aparecem em tópicos próprios ou em mais de um tópico quando ajudam a cruzar seções.",
        "",
    ]

    for grupo in sorted(topicos_por_grupo):
        linhas.extend([f"## {grupo}", ""])
        for topico in sorted(topicos_por_grupo[grupo], key=lambda item: str(item.get("titulo") or "")):
            linhas.extend(
                [
                    f"### {topico['titulo']}",
                    "",
                    str(topico.get("descricao") or "").strip(),
                    "",
                    f"- Tipo de escopo: `{topico.get('tipo_escopo', '')}`",
                    "- Aliases de título: " + ", ".join(f"`{valor}`" for valor in topico.get("aliases_titulo", [])),
                    "- Termos de busca: " + ", ".join(f"`{valor}`" for valor in topico.get("termos_busca", [])),
                    "",
                ]
            )
            for ficha_id in topico.get("fichas", []):
                ficha = fichas_por_id.get(str(ficha_id))
                if ficha:
                    linhas.append(_linha_ficha(ficha))
                else:
                    linhas.append(f"- `{ficha_id}` - ficha não encontrada")
            linhas.append("")

    return "\n".join(linhas).rstrip() + "\n"


def escrever_mapa(path: Path = MAPA_FICHAS_PATH) -> str:
    mapa = gerar_mapa_fichas()
    write_text(path, mapa)
    return mapa


def mapa_atualizado(path: Path = MAPA_FICHAS_PATH) -> bool:
    if not path.exists():
        return False
    atual = path.read_text(encoding="utf-8")
    gerado_em = ""
    for linha in atual.splitlines():
        if linha.startswith("Gerado em: "):
            gerado_em = linha.removeprefix("Gerado em: ")
            break
    return atual == gerar_mapa_fichas(gerado_em=gerado_em)


def main() -> int:
    escrever_mapa()
    print(f"Mapa de fichas gerado em {MAPA_FICHAS_PATH}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
