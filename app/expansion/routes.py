"""Rota que entrega ao Expansion 3D o ticket do usuário logado no Atlas.

Fluxo, todo por redirecionamento no navegador:

    Expansion  ->  GET /api/expansion/ticket?retorno=<url do Expansion>&auto=1
    Atlas      ->  redireciona para <retorno>?ticket=<assinado>   (logado)
                   ou para        <retorno>?ticket=nenhum         (sem sessão)

O parâmetro `retorno` é conferido contra EXPANSION_URL antes de qualquer redirecionamento,
para que a rota não possa ser usada para mandar o usuário (e o ticket) a um site de fora.
"""
import base64
import hashlib
import hmac
import json
import os
import time
from urllib.parse import urlencode, urlparse

from flask import Blueprint, current_app, render_template_string, request, session
from markupsafe import escape

from app.auth import get_usuario_logado

expansion_bp = Blueprint("expansion", __name__)


def _assinar(payload: dict, segredo: str) -> str:
    """Mesmo formato que o Expansion confere: corpo.assinatura, ambos em base64url."""
    corpo = base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()).decode().rstrip("=")
    mac = hmac.new(segredo.encode(), corpo.encode(), hashlib.sha256).digest()
    return f"{corpo}.{base64.urlsafe_b64encode(mac).decode().rstrip('=')}"


def _retorno_confiavel(retorno: str) -> bool:
    """Só aceita voltar para o endereço configurado do Expansion.

    Confere esquema, host e porta. O esquema entra na comparação de propósito: mandar o ticket
    para https numa porta que responde em http devolve "resposta inválida" no navegador, e é
    melhor recusar aqui, com mensagem clara, do que produzir esse endereço quebrado.
    """
    permitido = os.getenv("EXPANSION_URL", "").strip()
    if not retorno or not permitido:
        return False
    alvo, base = urlparse(retorno), urlparse(permitido)
    return bool(alvo.scheme in ("http", "https") and alvo.netloc
                and alvo.netloc == base.netloc and alvo.scheme == base.scheme)


PAGINA_VOLTA = """<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><title>Entrando no Expansion 3D</title>
<meta http-equiv="refresh" content="0;url={{ destino }}"></head>
<body style="font:14px system-ui,sans-serif;color:#555;padding:24px">
<p>Entrando no Expansion 3D&hellip;</p>
<p><a href="{{ destino }}">Continuar</a></p>
<script>location.replace({{ destino|tojson }});</script>
</body></html>"""


def _voltar(retorno: str, **parametros):
    """Volta ao Expansion por uma página, e não pelo cabeçalho Location.

    O nginx à frente do Atlas reescreve `http://` para `https://` no Location (proxy_redirect).
    Como o Expansion responde em HTTP puro na porta 8010, o endereço reescrito dava
    "a conexão com este site não é segura / resposta inválida" no navegador. Uma navegação
    disparada pela própria página não passa por essa reescrita.

    O `retorno` já foi conferido contra EXPANSION_URL antes de chegar aqui, e o Jinja escapa o
    endereço tanto no HTML quanto no JSON do script.
    """
    separador = "&" if "?" in retorno else "?"
    destino = f"{retorno}{separador}{urlencode(parametros)}"
    return render_template_string(PAGINA_VOLTA, destino=destino)


@expansion_bp.route("/api/expansion/ticket")
def ticket():
    retorno = request.args.get("retorno", "")
    auto = request.args.get("auto", "0")
    if not _retorno_confiavel(retorno):
        permitido = os.getenv("EXPANSION_URL", "").strip() or "(não configurado)"
        current_app.logger.warning("Expansion: retorno recusado (%s); EXPANSION_URL=%s",
                                   retorno[:120], permitido)
        # escape(): a mensagem volta como HTML e o retorno vem da URL
        return (f"Endereço de retorno não autorizado.<br>Recebido: {escape(retorno[:200])}"
                f"<br>Esperado começar com: {escape(permitido)}"
                "<br>Acerte EXPANSION_URL no .env do Atlas e url_publica no conf.ini do "
                "Expansion — os dois precisam ter o mesmo esquema, host e porta."), 400

    segredo = os.getenv("EXPANSION_SECRET", "").strip()
    if not segredo:
        current_app.logger.error("Expansion: EXPANSION_SECRET não configurado no .env")
        return _voltar(retorno, ticket="nenhum", auto=auto)

    claims = session.get("user") or {}
    matricula = (claims.get("preferred_username") or "").split("@")[0]
    if not matricula:
        # ninguém logado aqui: o Expansion abre em modo Visualização
        return _voltar(retorno, ticket="nenhum", auto=auto)

    usuario = get_usuario_logado()
    if usuario is not None and getattr(usuario, "bloqueado", False):
        return _voltar(retorno, ticket="nenhum", auto=auto)

    payload = {
        "matricula": matricula,
        "nome": (getattr(usuario, "nome", None) or claims.get("name") or matricula),
        "email": (getattr(usuario, "email", None) or claims.get("preferred_username") or ""),
        "admin": bool(getattr(usuario, "admin", False)),
        "ts": int(time.time()),
    }
    return _voltar(retorno, ticket=_assinar(payload, segredo), auto=auto)
