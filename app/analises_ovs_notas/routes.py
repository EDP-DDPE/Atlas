from flask import Blueprint, render_template, request, jsonify, current_app, abort, send_from_directory, session, url_for
from app.models import db, OvsExtraidas, StatusOvs, NotasExtraidas, StatusNotas, DocsNotas, DocsOvs, Estudo, EDP
from app.auth import requires_permission, get_usuario_logado
from datetime import datetime
from collections import defaultdict
import os
import unicodedata
from werkzeug.utils import safe_join

analises_ovs_notas_bp = Blueprint("analises_ovs_notas", __name__, template_folder="templates",static_folder="static",static_url_path="/analises_ovs_notas/static")

# ---------------------------------------------------------------------------
# SITUAÇÕES (filtro "Situação") — avaliadas sobre o status ATUAL
#   finalizado : ENCE, NREJ ou ENCERRADA
#   a_analisar : ABERTA sem estudo vinculado, Grandes Clientes ou Poder Público
#   analisado  : demais casos
# (as chaves são comparadas em minúsculo e sem acento)
# ---------------------------------------------------------------------------
STATUS_FINALIZADO = {"ence", "nrej", "encerrada"}
STATUS_A_ANALISAR = {"grandes clientes", "poder publico"}
STATUS_ABERTA = "aberta"

# Status que, se aparecerem em QUALQUER ponto do histórico, são o status
# atual (sobrepõem os demais, mesmo os posteriores)
STATUS_SOBREPOE = {
    "nota": {"ence", "nrej"},
    "ov": {"encerrada"},
}

STATUS_BADGE = {
    "grandes clientes": {"classe": "warning", "icone": "bi-hourglass-split"},
    "poder publico": {"classe": "warning", "icone": "bi-hourglass-split"},
    "projeto": {"classe": "success", "icone": "bi-check-circle-fill"},
    "loteamento": {"classe": "success", "icone": "bi-check-circle-fill"},
    "em andamento": {"classe": "info", "icone": "bi-arrow-repeat"},
    "ence": {"classe": "secondary", "icone": "bi-check2-all"},
    "encerrada": {"classe": "secondary", "icone": "bi-check2-all"},
    "nrej": {"classe": "danger", "icone": "bi-x-circle-fill"},
}

# Sufixo que identifica o arquivo de descrição dentro da pasta
SUFIXO_DESCRICAO = "_descricao.txt"

# VOLTAR DEPOIS
#def _upload_folder():
#    """ Mesma pasta base usada no blueprint 'listar':
#    os.path.dirname(os.path.dirname(current_app.root_path)).
#    Os CAMINHO_DOC salvos são relativos a esta pasta (ex.: '45006426454/arq.pdf'). """
#    return os.path.join(os.path.dirname(os.path.dirname(current_app.root_path))).replace("\\","/")

# --- TEMPORÁRIO --- #
# TEMPORÁRIO: depois mover para o .env (ex.: DOCS_BASE)
DOCS_BASE_TEMP = r"C:\Users\EX160187\EDP\O365_Planejamento da Expansao - Documentos\Servidores\Servidor SP\GCIWeb\docs_novas_ovs_notas"

SUBPASTAS = {"nota": "docs_notas", "ov": "docs_ovs"}

def _upload_folder(tipo):
    """ Pasta base dos documentos. Os CAMINHO_DOC no banco são relativos a ela
    (ex.: '45006425374/45006425374_descricao.txt'). """
    return os.path.join(DOCS_BASE_TEMP, SUBPASTAS[tipo]).replace("\\", "/")
# --- TEMPORÁRIO --- #


def _caminho_seguro(caminho_rel, tipo):
    """ Resolve CAMINHO_DOC para um caminho absoluto garantindo que fique
    dentro da upload_folder. Retorna None se for inválido."""
    if not caminho_rel:
        return None
    caminho_rel = str(caminho_rel).replace("\\", "/")
    return safe_join(_upload_folder(tipo), caminho_rel)

def _ler_texto(caminho_abs):
    """ Lê o conteúdo de um .txt tentando utf-8 e caindo para latin-1. """
    if not caminho_abs or not os.path.isfile(caminho_abs):
        return None
    for enc in ("utf-8", "latin-1"):
        try:
            with open(caminho_abs, "r", encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    with open(caminho_abs, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def _permissoes():
    u = get_usuario_logado()
    return {
        "criar": bool(getattr(u, "criar", 0)),
        "editar": bool(getattr(u, "editar", 0)),
        "deletar": bool(getattr(u, "deletar", 0)),
    }

def _mapa_estudos(numeros):
    """ Recebe números de OV/Nota e devolve {numero_int: {"id", "num_doc"}}
    buscando pelo campo Estudo.protocolo. Se houver mais de um estudo com o
    mesmo protocolo, usa o mais recente (maior id_estudo). """
    protocolos = {int(str(n).strip()) for n in numeros if n and str(n).strip().isdigit()}
    if not protocolos:
        return {}

    mapa = {}
    lista = list(protocolos)
    # SQL Server limita ~2100 parâmetros por consulta -> busca em lotes
    for i in range(0, len(lista), 1000):
        lote = lista[i:i + 1000]
        rows = (db.session.query(Estudo.protocolo, Estudo.id_estudo, Estudo.num_doc)
                .filter(Estudo.protocolo.in_(lote))
                .order_by(Estudo.id_estudo)   # o maior id sobrescreve -> fica o mais recente
                .all())
        for protocolo, id_estudo, num_doc in rows:
            mapa[int(protocolo)] = {"id": id_estudo, "num_doc": num_doc}
    return mapa


def _estudo(mapa, numero):
    numero = str(numero or "").strip()
    return mapa.get(int(numero)) if numero.isdigit() else None


# ---------------------------------------------------------------------------
# id_edp -> sigla da empresa (atlas.edp)
# ---------------------------------------------------------------------------
def _empresas():
    """ {id_edp: sigla da empresa} a partir de atlas.edp. """
    return {e.id_edp: e.empresa for e in EDP.query.all()}


def _edp_json(id_edp, empresas):
    if id_edp is None:
        return None
    return {"id": id_edp, "empresa": empresas.get(id_edp) or str(id_edp)}


def _sem_acento(texto):
    return "".join(c for c in unicodedata.normalize("NFD", texto)
                   if unicodedata.category(c) != "Mn")


def _valor_status(reg):
    """ Texto do status em minúsculo, sem acento e sem espaços nas pontas. """
    valor = (getattr(reg, "STATUS_OV", None)
             or getattr(reg, "STATUS_NOTA", None) or "").strip().lower()
    return _sem_acento(valor)


def _situacao(chave_status, tem_estudo):
    """ Classifica o item a partir do status atual (já normalizado). """
    if chave_status in STATUS_FINALIZADO:
        return "finalizado"
    if chave_status in STATUS_A_ANALISAR:
        return "a_analisar"
    if chave_status == STATUS_ABERTA and not tem_estudo:
        return "a_analisar"
    return "analisado"


def _id_status(reg):
    """ ID do registro de status (STATUS_OVS ou STATUS_NOTAS). """
    return getattr(reg, "ID_STATUS_OVS", None) or getattr(reg, "ID_STATUS_NOVAS", None) or 0


def status_vigente(historico, tipo):
    """ Registro que vale como status ATUAL (independe da ordem da lista).
    Regra geral: o de maior ID.
    Exceção (STATUS_SOBREPOE): Notas ENCE/NREJ e OVs ENCERRADA sobrepõem todos
    os outros — se existir algum no histórico, vale o de MAIOR ID entre eles
    (ex.: NREJ id 10 e ENCE id 15 -> ENCE), mesmo havendo status posteriores. """
    if not historico:
        return None
    sobrepoe = STATUS_SOBREPOE.get(tipo, set())
    prioritarios = [r for r in historico if _valor_status(r) in sobrepoe]
    return max(prioritarios or historico, key=_id_status)


def montar_status(historico, tipo, tem_estudo=False):
    """ Recebe o histórico de status de um item e monta badge + situação. """
    if not historico:
        return {
            "classe": "secondary", "icone": "bi-hourglass-split",
            "texto": "Pendente", "responsavel": None, "data": None,
            "situacao": _situacao("", tem_estudo),
            "encerrado": False,
        }

    ultimo = status_vigente(historico, tipo)
    chave_ultimo = _valor_status(ultimo)
    situacao = _situacao(chave_ultimo, tem_estudo)

    valor_original = (getattr(ultimo, "STATUS_OV", None)
                      or getattr(ultimo, "STATUS_NOTA", None) or "-")
    estilo = STATUS_BADGE.get(chave_ultimo, {"classe": "dark", "icone": "bi-tag-fill"})

    return {
        "classe": estilo["classe"],
        "icone": estilo["icone"],
        "texto": valor_original,
        "responsavel": ultimo.RESPONSAVEL_STATUS,
        "data": ultimo.DATA_SAP.strftime("%d/%m/%Y") if ultimo.DATA_SAP else None,
        "situacao": situacao,
        "encerrado": situacao == "finalizado",   # finalizados só têm "Visualizar"
    }

@analises_ovs_notas_bp.route("/analises_ovs_notas", methods=["GET"])
@requires_permission("visualizar")
def listar():
    usuario = get_usuario_logado()
    return render_template("listar_analises_ovs_notas.html", usuario=usuario)


@analises_ovs_notas_bp.route("/analises_ovs_notas/api/ovs", methods=["GET"])
@requires_permission("visualizar")
def api_listar_ovs():
    ovs = OvsExtraidas.query.order_by(OvsExtraidas.ID_OVS_EXTRAIDAS.desc()).all()

    historico_map = defaultdict(list)
    for s in StatusOvs.query.order_by(StatusOvs.ID_STATUS_OVS).all():
        historico_map[s.OV].append(s)   # ascendente → o último da lista é o mais recente


    somente_pendentes = request.args.get("pendentes") == "1"
    estudos_map = _mapa_estudos(r.OV for r in ovs)
    empresas = _empresas()

    items = []
    for r in ovs:
        hist = historico_map.get(r.OV, [])
        if somente_pendentes and hist:
            continue
        estudo = _estudo(estudos_map, r.OV)
        items.append({
            "id": r.ID_OVS_EXTRAIDAS,
            "ov": r.OV,
            "data_solicitacao": r.DATA_SOLICITACAO.strftime("%d/%m/%Y") if r.DATA_SOLICITACAO else None,
            "data_planejamento": r.DATA_PLANEJAMENTO.strftime("%d/%m/%Y") if r.DATA_PLANEJAMENTO else None,
            "data_importacao": r.DATELOAD.strftime("%d/%m/%Y") if r.DATELOAD else None,
            "edp": _edp_json(r.id_edp, empresas),
            "status": montar_status(hist, "ov", tem_estudo=estudo is not None),
            "estudo": estudo,
        })

    return jsonify({"items": items, "permissoes": _permissoes()})


@analises_ovs_notas_bp.route("/analises_ovs_notas/ovs/<int:id>/status", methods=["POST"])
@requires_permission("editar")
def registrar_status_ov(id):
    ov = OvsExtraidas.query.get_or_404(id)
    data = request.get_json() if request.is_json else request.form.to_dict()
    novo = (data.get("status") or "").strip()
    if not novo:
        return jsonify({"status": "error", "message": "Informe o status"}), 400

    u = get_usuario_logado()
    novo_status = StatusOvs(
        OV=ov.OV,
        STATUS_OV=novo,
        DATA_SAP=datetime.now().date(),
        RESPONSAVEL_STATUS=getattr(u, "nome", None) or getattr(u, "login", None),
        DATELOAD = datetime.now(),
        id_edp=ov.id_edp,   # herda a empresa da OV
    )
    db.session.add(novo_status)

    try:
        db.session.commit()
        return jsonify({"status": "success", "message": "Status registrado"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500


@analises_ovs_notas_bp.route("/analises_ovs_notas/api/notas", methods=["GET"])
@requires_permission("visualizar")
def api_listar_notas():
    notas = NotasExtraidas.query.order_by(NotasExtraidas.ID_NOTAS_EXTRAIDAS.desc()).all()
    historico_map = defaultdict(list)
    for s in StatusNotas.query.order_by(StatusNotas.ID_STATUS_NOVAS).all():
        historico_map[s.NOTA].append(s)

    somente_pendentes = request.args.get("pendentes") == "1"
    estudos_map = _mapa_estudos(r.NOTA for r in notas)
    empresas = _empresas()

    items = []
    for r in notas:
        hist = historico_map.get(r.NOTA, [])
        if somente_pendentes and hist:
            continue
        estudo = _estudo(estudos_map, r.NOTA)
        items.append({
            "id": r.ID_NOTAS_EXTRAIDAS,
            "nota": r.NOTA,
            "data_solicitacao": r.DATA_SOLICITACAO.strftime("%d/%m/%Y") if r.DATA_SOLICITACAO else None,
            "data_vencimento": r.DATA_VENCIMENTO.strftime("%d/%m/%Y") if r.DATA_VENCIMENTO else None,
            "data_importacao": r.DATELOAD.strftime("%d/%m/%Y") if r.DATELOAD else None,
            "edp": _edp_json(r.id_edp, empresas),
            "status": montar_status(hist, "nota", tem_estudo=estudo is not None),
            "estudo": estudo,
        })

    return jsonify({"items": items, "permissoes": _permissoes()})

@analises_ovs_notas_bp.route("/analises_ovs_notas/notas/<int:id>/encerramento_manual", methods=["POST"])
@requires_permission("editar")
def encerramento_manual_nota(id):
    """ Registra ENCE ou NREJ manualmente (quando o robô falha), com a data
    informada pelo usuário (data em que a nota foi encerrada/rejeitada no SAP). """
    nota = NotasExtraidas.query.get_or_404(id)
    data = request.get_json(silent=True) or {}

    status = (data.get("status") or "").strip().upper()
    if status not in {"ENCE", "NREJ"}:
        return jsonify({"status": "error", "message": "Status inválido. Use ENCE ou NREJ."}), 400

    try:
        data_sap = datetime.strptime((data.get("data_sap") or "").strip(), "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"status": "error", "message": "Informe uma data do SAP válida."}), 400
    if data_sap > datetime.now().date():
        return jsonify({"status": "error", "message": "A data do SAP não pode ser futura."}), 400

    u = get_usuario_logado()
    db.session.add(StatusNotas(
        NOTA=nota.NOTA,
        STATUS_NOTA=status,
        DATA_SAP=data_sap,
        RESPONSAVEL_STATUS=getattr(u, "nome", None) or getattr(u, "login", None),
        DATELOAD=datetime.now(),
        id_edp=nota.id_edp,
    ))
    try:
        db.session.commit()
        rotulo = "encerrada" if status == "ENCE" else "rejeitada"
        return jsonify({"status": "success", "message": f"Nota {nota.NOTA} {rotulo}."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500


@analises_ovs_notas_bp.route("/analises_ovs_notas/notas/<int:id>/status", methods=["POST"])
@requires_permission("editar")
def registrar_status_nota(id):
    nota = NotasExtraidas.query.get_or_404(id)
    data = request.get_json() if request.is_json else request.form.to_dict()
    novo = (data.get("status") or "").strip()
    if not novo:
        return jsonify({"status": "error", "message": "Informe o status."}), 400

    u = get_usuario_logado()
    novo_status = StatusNotas(
        NOTA=nota.NOTA,
        STATUS_NOTA=novo,
        DATA_SAP=datetime.now().date(),
        RESPONSAVEL_STATUS=getattr(u, "nome", None) or getattr(u, "login", None),
        DATELOAD=datetime.now(),
        id_edp=nota.id_edp,   # herda a empresa da Nota
    )
    db.session.add(novo_status)
    try:
        db.session.commit()
        return jsonify({"status": "success", "message": "Status registrado!"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

# ===========================================================================
# DETALHES / ARQUIVOS DA PASTA  (usados pelo modal de "Analisar")
# ===========================================================================

def _serializa_doc(d, id_attr):
    """ Monta o dict de um documento e marca se é o arquivo de descrição. """
    nome = getattr(d, "NOME_DOC", "") or ""
    data = getattr(d, "DATA_CRIACAO", None)
    return {
        "id": getattr(d, id_attr),
        "nome": nome,
        "caminho": getattr(d, "CAMINHO_DOC", None),
        "tipo": getattr(d, "TIPO_DOC", None),
        "data": data.strftime("%d/%m/%Y %H:%M") if data else None,
        "eh_descricao": nome.lower().endswith(SUFIXO_DESCRICAO),
    }

def _serializa_historico(registros, tipo, empresas):
    """ Lista de status (mais recente primeiro) com o estilo do badge.
    Marca com "atual" o registro que vale como status atual (ver status_vigente). """
    vigente = status_vigente(list(reversed(registros)), tipo)

    hist = []
    for s in registros:
        valor = getattr(s, "STATUS_OV", None) or getattr(s, "STATUS_NOTA", None) or "-"
        estilo = STATUS_BADGE.get(_valor_status(s), {"classe": "dark", "icone": "bi-tag-fill"})
        carga = getattr(s, "DATELOAD", None)
        hist.append({
            "status": valor,
            "classe": estilo["classe"],
            "icone": estilo["icone"],
            "data": s.DATA_SAP.strftime("%d/%m/%Y") if s.DATA_SAP else None,
            "registrado_em": carga.strftime("%d/%m/%Y %H:%M") if carga else None,
            "responsavel": s.RESPONSAVEL_STATUS,
            "edp": _edp_json(s.id_edp, empresas),
            "atual": s is vigente,
        })
    return hist


@analises_ovs_notas_bp.route("/analises_ovs_notas/api/notas/<int:id>/detalhes", methods=["GET"])
@requires_permission("visualizar")
def api_detalhes_nota(id):
    if DocsNotas is None:
        return jsonify({"status":"error","message":"Modelo DocsNotas não configurado em app/models.py."}), 500

    nota = NotasExtraidas.query.get_or_404(id)
    empresas = _empresas()
    docs = DocsNotas.query.filter_by(ID_NOTAS_EXTRAIDAS=nota.ID_NOTAS_EXTRAIDAS).order_by(DocsNotas.ID_DOC_NOTAS).all()

    documentos = []
    descricao_texto = None
    for d in docs:
        item = _serializa_doc(d, "ID_DOC_NOTAS")
        documentos.append(item)
        if item["eh_descricao"] and descricao_texto is None:
            descricao_texto = _ler_texto(_caminho_seguro(item["caminho"], "nota"))

    return jsonify({
        "info": {
            "id": nota.ID_NOTAS_EXTRAIDAS,
            "numero": nota.NOTA,
            "data_solicitacao": nota.DATA_SOLICITACAO.strftime("%d/%m/%Y") if nota.DATA_SOLICITACAO else None,
            "data_vencimento": nota.DATA_VENCIMENTO.strftime("%d/%m/%Y") if nota.DATA_VENCIMENTO else None,
            "edp": _edp_json(nota.id_edp, empresas),
        },
        "historico": _serializa_historico(
            StatusNotas.query.filter_by(NOTA=nota.NOTA)
            .order_by(StatusNotas.ID_STATUS_NOVAS.desc()).all(),
            "nota", empresas,
        ),
        "descricao": descricao_texto,
        "documentos": documentos,
        "permissoes": _permissoes(),
    })


@analises_ovs_notas_bp.route("/analises_ovs_notas/api/ovs/<int:id>/detalhes", methods=["GET"])
@requires_permission("visualizar")
def api_detalhes_ov(id):
    if DocsOvs is None:
        return jsonify({"status": "error", "message": "Modelo DocsOvs não configurado em app/models.py."}), 500

    ov = OvsExtraidas.query.get_or_404(id)
    empresas = _empresas()
    docs = DocsOvs.query.filter_by(ID_OVS_EXTRAIDAS=ov.ID_OVS_EXTRAIDAS).order_by(DocsOvs.ID_DOC_OVS).all()

    documentos = []
    descricao_texto = None
    
    for d in docs:
        item = _serializa_doc(d, "ID_DOC_OVS")
        documentos.append(item)

        # --- DEBUG ---
        p = _caminho_seguro(item["caminho"], "ov")
        print("=== DEBUG DETALHES OV ===")
        print("nome            :", repr(item["nome"]))
        print("eh_descricao    :", item["eh_descricao"])
        print("CAMINHO_DOC     :", repr(item["caminho"]))
        print("caminho final   :", repr(p))
        print("base existe?    :", os.path.isdir(_upload_folder("ov")))
        print("arquivo existe? :", os.path.isfile(p) if p else None)
        # --- FIM DEBUG ---

        if item["eh_descricao"] and descricao_texto is None:
            descricao_texto = _ler_texto(_caminho_seguro(item["caminho"], "ov"))

    return jsonify({
        "info": {
            "id": ov.ID_OVS_EXTRAIDAS,
            "numero": ov.OV,
            "data_solicitacao": ov.DATA_SOLICITACAO.strftime("%d/%m/%Y") if ov.DATA_SOLICITACAO else None,
            "data_planejamento": ov.DATA_PLANEJAMENTO.strftime("%d/%m/%Y") if ov.DATA_PLANEJAMENTO else None,
            "edp": _edp_json(ov.id_edp, empresas),
        },
        "historico": _serializa_historico(
            StatusOvs.query.filter_by(OV=ov.OV)
            .order_by(StatusOvs.ID_STATUS_OVS.desc()).all(),
            "ov", empresas,
        ),
        "descricao": descricao_texto,
        "documentos": documentos,
        "permissoes": _permissoes(),
    })

# ---------- DOWNLOAD ----------

def _download_doc(tipo, doc):
    """ Envia o arquivo físico correspondente a um registro de documento. """
    caminho_abs = _caminho_seguro(getattr(doc,"CAMINHO_DOC", None), tipo)
    if not caminho_abs or not os.path.isfile(caminho_abs):
        abort(404)
    directory = os.path.dirname(caminho_abs)
    arquivo = os.path.basename(caminho_abs)
    return send_from_directory(directory, arquivo, as_attachment=True, download_name=getattr(doc, "NOME_DOC", arquivo))

@analises_ovs_notas_bp.route("/analises_ovs_notas/notas/documentos/<int:doc_id>/download", methods=["GET"])
@requires_permission("visualizar")
def download_doc_nota(doc_id):
    if DocsNotas is None:
        abort(500)
    return _download_doc("nota", DocsNotas.query.get_or_404(doc_id))

@analises_ovs_notas_bp.route("/analises_ovs_notas/ovs/documentos/<int:doc_id>/download", methods=["GET"])
@requires_permission("visualizar")
def download_doc_ov(doc_id):
    if DocsOvs is None:
        abort(500)
    return _download_doc("ov", DocsOvs.query.get_or_404(doc_id))

# ---------- EXCLUSÃO ----------

def _apagar_doc(tipo, doc):
    """ Remove o arquivo físico (se existir) e o registro no banco. """
    caminho_abs = _caminho_seguro(getattr(doc, "CAMINHO_DOC", None), tipo)
    try:
        if caminho_abs and os.path.isfile(caminho_abs):
            os.remove(caminho_abs)
        db.session.delete(doc)
        db.session.commit()
        return jsonify({"status": "success", "message": "Arquivo removido."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

@analises_ovs_notas_bp.route("/analises_ovs_notas/notas/documentos/<int:doc_id>", methods=["DELETE"])
@requires_permission("deletar")
def deletar_doc_nota(doc_id):
    if DocsNotas is None:
        return jsonify({"status": "error", "message": "Modelo DocsNotas não configurado."}), 500
    return _apagar_doc("nota", DocsNotas.query.get_or_404(doc_id))

@analises_ovs_notas_bp.route("/analises_ovs_notas/ovs/documentos/<int:doc_id>", methods=["DELETE"])
@requires_permission("deletar")
def deletar_doc_ov(doc_id):
    if DocsOvs is None:
        return jsonify({"status": "error", "message": "Modelo DocsOvs não configurado."}), 500
    return _apagar_doc("ov", DocsOvs.query.get_or_404(doc_id))



# -------------- CRIAR ESTUDO ---------------------- #
def _descricao_do_registro(tipo, docs):
    """Lê o _descricao.txt da pasta (se existir)."""
    for d in docs:
        nome = (getattr(d, "NOME_DOC", "") or "").lower()
        if nome.endswith(SUFIXO_DESCRICAO):
            return _ler_texto(_caminho_seguro(getattr(d, "CAMINHO_DOC", None), tipo))
    return None


def _iso(d):
    return d.strftime("%Y-%m-%d") if d else None


@analises_ovs_notas_bp.route("/analises_ovs_notas/<tipo>/<int:id>/criar_estudo", methods=["POST"])
@requires_permission("criar")
def criar_estudo(tipo, id):
    if tipo == "ov":
        reg = OvsExtraidas.query.get_or_404(id)
        docs = DocsOvs.query.filter_by(ID_OVS_EXTRAIDAS=reg.ID_OVS_EXTRAIDAS).all()
        numero, rotulo = reg.OV, "OV"
        data_venc = None
        data_entrada_ddpe = reg.DATA_PLANEJAMENTO   # -> "Data de Entrada DDPE"
        obs_extra = f"Data de planejamento: {reg.DATA_PLANEJAMENTO.strftime('%d/%m/%Y')}" if reg.DATA_PLANEJAMENTO else ""
    elif tipo == "nota":
        reg = NotasExtraidas.query.get_or_404(id)
        docs = DocsNotas.query.filter_by(ID_NOTAS_EXTRAIDAS=reg.ID_NOTAS_EXTRAIDAS).all()
        numero, rotulo = reg.NOTA, "Nota"
        data_venc = reg.DATA_VENCIMENTO
        data_entrada_ddpe = None
        obs_extra = ""
    else:
        abort(404)

    descricao = _descricao_do_registro(tipo, docs) or ""

    # Cuidado: a session do Flask é um cookie (~4 KB). Não guarde texto grande.
    descricao = descricao[:1200]

    # Protocolo do estudo = número da OV/Nota (o cadastro lê a chave "protocolo")
    numero_str = str(numero or "").strip()
    protocolo = int(numero_str) if numero_str.isdigit() else (numero_str or None)

    session["ia_prefill_estudo"] = {
        "protocolo": protocolo,
        "nome_projeto": f"{rotulo} {numero}",
        "descricao": descricao,
        "observacao": f"Origem: {rotulo} {numero}. {obs_extra}".strip(),
        "data_abertura_cliente": _iso(reg.DATA_SOLICITACAO),     # DATA_SOLICITACAO -> Data Abertura do Cliente
        "data_vencimento_cliente": _iso(data_venc),
        "data_vencimento_ddpe": _iso(data_entrada_ddpe),         # DATA_PLANEJAMENTO -> Data de Entrada DDPE
    }
    session["ia_prefill_nome_pdf"] = f"{rotulo} {numero}"

    return jsonify({
        "status": "success",
        "redirect": url_for("cadastro.cadastro_estudo", ia_prefill=1),
    })