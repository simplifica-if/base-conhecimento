from __future__ import annotations

import os
import re
import shutil
import shlex
import subprocess
import unicodedata
from pathlib import Path
from typing import Any


class ErroPublicacaoSurge(RuntimeError):
    pass


def _slug(valor: str, limite: int = 48) -> str:
    normalizado = unicodedata.normalize("NFKD", valor)
    ascii_texto = normalizado.encode("ascii", "ignore").decode("ascii").lower()
    slug_completo = re.sub(r"[^a-z0-9]+", "-", ascii_texto).strip("-")
    slug = (slug_completo or "relatorio")[:limite].strip("-")
    if len(slug_completo) > limite and "-" in slug and len(slug.rsplit("-", 1)[-1]) < 3:
        slug = slug.rsplit("-", 1)[0]
    return slug or "relatorio"


def dominio_surge_padrao(rodada_dir: Path) -> str:
    configurado = os.environ.get("ANALISE_PPC_SURGE_DOMAIN")
    if configurado:
        return configurado
    return f"analise-ppc-{_slug(rodada_dir.name)}.surge.sh"


def preparar_site_surge(relatorio_html: Path, destino_dir: Path) -> Path:
    destino_dir.mkdir(parents=True, exist_ok=True)
    destino = destino_dir / "index.html"
    shutil.copyfile(relatorio_html, destino)
    return destino_dir


def _comando_base(comando: list[str] | None = None) -> list[str]:
    if comando:
        return comando
    configurado = os.environ.get("ANALISE_PPC_SURGE_CMD")
    if configurado:
        return shlex.split(configurado)
    return ["npx", "--yes", "surge"]


def _normalizar_url(dominio: str) -> str:
    valor = dominio.strip().rstrip("/")
    if re.match(r"^https?://", valor, flags=re.IGNORECASE):
        return valor
    return f"https://{valor}"


def publicar_site_surge(
    site_dir: Path,
    *,
    dominio: str,
    comando: list[str] | None = None,
) -> dict[str, Any]:
    site = site_dir.resolve()
    cmd = [*_comando_base(comando), str(site), dominio]
    processo = subprocess.run(
        cmd,
        check=False,
        capture_output=True,
        input="",
        text=True,
    )
    stdout = processo.stdout.strip()
    stderr = processo.stderr.strip()
    saida = "\n".join(parte for parte in (stdout, stderr) if parte)

    if processo.returncode != 0:
        detalhes = f"\n{saida}" if saida else ""
        raise ErroPublicacaoSurge(f"Falha ao publicar relatório no Surge.{detalhes}")
    if re.search(r"\bLogin or create surge account\b|\bemail:\s*$", saida, flags=re.IGNORECASE):
        raise ErroPublicacaoSurge(
            "Falha ao publicar relatório no Surge: a CLI solicitou autenticação interativa. "
            "Execute `npx surge login` ou configure credenciais de automação do Surge no ambiente."
        )
    if "success" not in saida.casefold():
        detalhes = f"\n{saida}" if saida else ""
        raise ErroPublicacaoSurge(f"Surge não retornou confirmação de publicação reconhecível.{detalhes}")

    return {
        "servico": "surge",
        "site_dir": str(site),
        "domain": dominio,
        "public_url": _normalizar_url(dominio),
        "stdout": stdout,
        "stderr": stderr,
    }
