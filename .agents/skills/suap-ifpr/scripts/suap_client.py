#!/usr/bin/env python3
"""Cliente HTTP mínimo e seguro para páginas autenticadas do SUAP/IFPR."""

from __future__ import annotations

import html
import os
import re
from http.cookiejar import CookieJar
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin, urlparse
from urllib.request import HTTPCookieProcessor, Request, build_opener


SUAP_ORIGIN = "https://suap.ifpr.edu.br"
LOGIN_PATH = "/accounts/login/?next=/"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 Chrome/140 Safari/537.36"
)
REQUIRED_CONFIG = ("SUAP_USUARIO", "SUAP_SENHA")


class SkillError(RuntimeError):
    """Erro esperado, adequado para exibição sem traceback."""


class SuapHTTPError(SkillError):
    """Falha HTTP do SUAP com código disponível para tratamento seguro."""

    def __init__(self, status: int, path: str):
        self.status = status
        self.path = path
        super().__init__(f"O SUAP respondeu HTTP {status} ao acessar {path}.")


def clean_text(value: str) -> str:
    return " ".join(html.unescape(value).split())


def find_env_file(start: Path | None = None) -> Path | None:
    current = (start or Path.cwd()).resolve()
    for directory in (current, *current.parents):
        candidate = directory / ".env.local"
        if candidate.is_file():
            return candidate
    return None


def parse_env_file(path: Path | None) -> dict[str, str]:
    if path is None:
        return {}
    result: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        result[key] = value
    return result


def resolve_config(
    env_file: Path | None = None, environ: dict[str, str] | None = None
) -> dict[str, str]:
    file_values = parse_env_file(env_file if env_file is not None else find_env_file())
    process_values = os.environ if environ is None else environ
    return {key: process_values.get(key, file_values.get(key, "")) for key in REQUIRED_CONFIG}


def require_config(
    env_file: Path | None = None, environ: dict[str, str] | None = None
) -> dict[str, str]:
    values = resolve_config(env_file, environ)
    missing = [key for key, value in values.items() if not value]
    if missing:
        raise SkillError("Configuração SUAP incompleta. Variáveis ausentes: " + ", ".join(missing))
    return values


def extract_input_value(document: str, name: str) -> str | None:
    pattern = (
        rf'<input\b(?=[^>]*\bname=["\']{re.escape(name)}["\'])'
        rf'(?=[^>]*\bvalue=["\']([^"\']*)["\'])[^>]*>'
    )
    match = re.search(pattern, document, flags=re.IGNORECASE)
    return html.unescape(match.group(1)) if match else None


def extract_title(document: str) -> str:
    match = re.search(r"<title[^>]*>(.*?)</title>", document, flags=re.IGNORECASE | re.DOTALL)
    return clean_text(re.sub(r"<[^>]+>", " ", match.group(1))) if match else "título indisponível"


def safe_suap_url(path: str) -> str:
    url = urljoin(f"{SUAP_ORIGIN}/", path)
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != "suap.ifpr.edu.br":
        raise SkillError("O acesso deve permanecer em https://suap.ifpr.edu.br/.")
    return url


class SuapClient:
    """Sessão autenticada cujos cookies existem somente em memória."""

    def __init__(self, usuario: str, senha: str, timeout: int = 30):
        self._usuario = usuario
        self._senha = senha
        self.timeout = timeout
        self._opener = build_opener(HTTPCookieProcessor(CookieJar()))
        self._authenticated = False

    @classmethod
    def from_config(cls, env_file: Path | None = None, timeout: int = 30) -> "SuapClient":
        config = require_config(env_file)
        return cls(config["SUAP_USUARIO"], config["SUAP_SENHA"], timeout=timeout)

    def _open(self, request: Request) -> tuple[str, str]:
        try:
            with self._opener.open(request, timeout=self.timeout) as response:
                final_url = response.geturl()
                parsed = urlparse(final_url)
                if parsed.scheme != "https" or parsed.netloc != "suap.ifpr.edu.br":
                    raise SkillError("O SUAP redirecionou a sessão para uma origem não autorizada.")
                charset = response.headers.get_content_charset() or "utf-8"
                return final_url, response.read().decode(charset, errors="replace")
        except HTTPError as exc:
            raise SuapHTTPError(exc.code, urlparse(request.full_url).path) from exc
        except (URLError, TimeoutError) as exc:
            raise SkillError(f"Falha ao acessar o SUAP: {exc}") from exc

    def authenticate(self) -> None:
        if self._authenticated:
            return
        login_url = safe_suap_url(LOGIN_PATH)
        headers = {"User-Agent": USER_AGENT, "Accept": "text/html"}
        _, login_document = self._open(Request(login_url, headers=headers))
        csrf_token = extract_input_value(login_document, "csrfmiddlewaretoken")
        if not csrf_token:
            raise SkillError("Não foi possível localizar o token de login do SUAP.")

        payload = urlencode(
            {
                "csrfmiddlewaretoken": csrf_token,
                "username": self._usuario,
                "password": self._senha,
                "this_is_the_login_form": "1",
                "next": "/",
            }
        ).encode("utf-8")
        final_url, document = self._open(
            Request(
                login_url,
                data=payload,
                headers={
                    **headers,
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Origin": SUAP_ORIGIN,
                    "Referer": login_url,
                },
            )
        )
        if "/accounts/login/" in urlparse(final_url).path or 'name="username"' in document:
            raise SkillError(
                "O SUAP não concluiu o login. Verifique as credenciais ou assuma manualmente "
                "se houver 2FA, CAPTCHA ou troca de senha."
            )
        self._authenticated = True

    def get_text(
        self, path: str, params: dict[str, str] | list[tuple[str, str]] | None = None
    ) -> tuple[str, str]:
        self.authenticate()
        url = safe_suap_url(path)
        if params:
            separator = "&" if "?" in url else "?"
            url = f"{url}{separator}{urlencode(params)}"
        final_url, document = self._open(
            Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html"})
        )
        if "/accounts/login/" in urlparse(final_url).path:
            self._authenticated = False
            raise SkillError("A sessão autenticada não foi mantida pelo SUAP.")
        return final_url, document
