"""Tela de Novidades do Atlas.

Divulga o que há de novo no sistema (nesta leva, o Expansion 3D) e guarda,
por usuário, a opção "não exibir novamente". A preferência fica num JSON em
``data/`` porque acompanha a versão das novidades (que vem do código), e não
o cadastro do usuário no banco.
"""

import json
import os
import threading
from datetime import datetime

from flask import (Blueprint, g, jsonify, redirect, render_template, request,
                   session, url_for)

from app.auth import get_usuario_logado

novidades_bp = Blueprint("novidades", __name__, template_folder="templates")

# Identifica a leva atual de novidades. Ao publicar novidades novas, troque a
# versão: quem já marcou "não exibir novamente" volta a ver a tela uma vez.
NOVIDADES_VERSAO = "2026-09-expansion-3d"

# Endereço do Expansion 3D (roda no mesmo desktop-servidor do Atlas, porta 8010)
EXPANSION_URL = "http://172.20.70.54:8010/"

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
PREFS_PATH = os.path.join(_ROOT, 'data', 'novidades_prefs.json')

_lock = threading.Lock()
_cache = {"mtime": None, "dados": {}}


def _carregar_prefs():
    """Lê o JSON de preferências, reaproveitando o cache enquanto o arquivo não mudar."""
    try:
        mtime = os.path.getmtime(PREFS_PATH)
    except OSError:
        return {}

    if _cache["mtime"] != mtime:
        try:
            with open(PREFS_PATH, encoding='utf-8') as f:
                _cache["dados"] = json.load(f)
            _cache["mtime"] = mtime
        except (OSError, ValueError) as e:
            print(f'Erro ao ler preferências de novidades: {e}')
            return {}

    return _cache["dados"]


def _salvar_pref(matricula, nao_exibir):
    """Grava (ou remove) a marcação de "não exibir novamente" do usuário."""
    with _lock:
        dados = dict(_carregar_prefs())

        if nao_exibir:
            dados[str(matricula)] = {
                "versao": NOVIDADES_VERSAO,
                "em": datetime.now().isoformat(timespec='seconds'),
            }
        else:
            dados.pop(str(matricula), None)

        os.makedirs(os.path.dirname(PREFS_PATH), exist_ok=True)
        tmp = f'{PREFS_PATH}.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
        os.replace(tmp, PREFS_PATH)

        _cache["dados"] = dados
        _cache["mtime"] = os.path.getmtime(PREFS_PATH)


def novidades_pendente(usuario):
    """True quando o usuário ainda não pediu para ocultar a leva atual."""
    if not usuario:
        return False

    pref = _carregar_prefs().get(str(usuario.matricula))
    return not (pref and pref.get('versao') == NOVIDADES_VERSAO)


@novidades_bp.app_context_processor
def injetar_novidades():
    """Disponibiliza para o base.html o estado das novidades do usuário logado."""
    usuario = getattr(g, 'user', None)
    return dict(
        novidades_versao=NOVIDADES_VERSAO,
        novidades_pendente=novidades_pendente(usuario),
        expansion_url=EXPANSION_URL,
    )


@novidades_bp.route('/novidades')
def novidades():
    if 'user' not in session:
        return redirect(url_for('auth.public'))

    return render_template('novidades/novidades.html', usuario=get_usuario_logado())


@novidades_bp.route('/novidades/preferencia', methods=['POST'])
def preferencia():
    """Salva a escolha de não exibir mais as novidades desta versão."""
    usuario = getattr(g, 'user', None) or get_usuario_logado()
    if not usuario:
        return jsonify({'ok': False, 'erro': 'Usuário não identificado.'}), 401

    dados = request.get_json(silent=True) or {}
    nao_exibir = bool(dados.get('nao_exibir'))

    try:
        _salvar_pref(usuario.matricula, nao_exibir)
    except OSError as e:
        print(f'Erro ao salvar preferência de novidades: {e}')
        return jsonify({'ok': False, 'erro': 'Não foi possível salvar a preferência.'}), 500

    return jsonify({'ok': True, 'nao_exibir': nao_exibir})
