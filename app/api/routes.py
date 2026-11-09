from flask import Blueprint, jsonify, flash, Response, request
from app.models import db, Estudo, get_dashboard_stats, listar_estudos, obter_estudo, Municipio, TipoSolicitacao, \
    Regional, Circuito, RespRegiao, Usuario, Subestacao, Instalacao, Empresa, Socio, FatorK, Alternativa
import requests
import re
import os
import subprocess
from datetime import datetime, timedelta
from sqlalchemy import and_
import base64

from app.utils.circuito_geojson import get_index, GEOJSON_PATH
from app.auth import requires_permission
from app.utils.activity_log import registrar_log

api_bp = Blueprint("api", __name__)


def convert_date(data_str: str):
    """Converte 'dd/mm/aaaa' da ReceitaWS em date, ou None se vazio.

    Devolve o objeto date em vez de string: o pyodbc convertia string para
    DATE implicitamente, o driver do Databricks não.
    """
    if not data_str:
        return None
    return datetime.strptime(data_str, "%d/%m/%Y").date()


def iso_para_sql_datetime(iso_str: str):
    """Converte ISO 8601 '2025-08-19T14:11:57.464Z' em datetime, ou None.

    Mesmo motivo de convert_date: o valor precisa chegar tipado ao banco.
    """
    if not iso_str:
        return None
    return datetime.strptime(iso_str, "%Y-%m-%dT%H:%M:%S.%fZ")


def only_digits(s: str) -> str:
    """Remove tudo que não for número"""
    return re.sub(r'\D', '', s)


def get_cnpj(c: str) -> dict:
    """
    Consulta o CNPJ na API da ReceitaWS
    Retorna um dicionário (JSON).
    """
    cnpj = only_digits(c)
    url = f"https://www.receitaws.com.br/v1/cnpj/{cnpj}"

    response = requests.get(url, timeout=10)

    if response.status_code == 200:
        try:
            return response.json()
        except Exception as e:
            return {"erro": f"Falha ao converter JSON: {e}"}
    else:
        return {"erro": f"Falha na requisição: {response.status_code}"}


@api_bp.route('/api/alternativa/estudo/<int:id_estudo>')
def api_dados_estudo(id_estudo):

    estudo = Estudo.query.get_or_404(id_estudo)

    return jsonify({
        "dem_fp_ant": max(estudo.dem_carga_atual_fp, estudo.dem_ger_atual_fp),
        "dem_p_ant": max(estudo.dem_carga_atual_p, estudo.dem_ger_atual_p),
        "dem_fp_dep": max(estudo.dem_carga_solicit_fp, estudo.dem_ger_solicit_fp),
        "dem_p_dep": max(estudo.dem_carga_solicit_p, estudo.dem_ger_solicit_p),
        "latitude": estudo.latitude_cliente,
        "longitude": estudo.longitude_cliente,
        "tensao": estudo.tensao.tensao

    })

@api_bp.route('/api/estudos/<int:estudo_id>')
def api_obter_estudo(estudo_id):
    return obter_estudo(estudo_id)


@api_bp.route("/api/tipo_analises/<viabilidade>")
def get_analises(viabilidade):
    analises = (
        db.session.query(TipoSolicitacao.analise)
        .filter_by(viabilidade=viabilidade)
        .distinct()
        .order_by(TipoSolicitacao.analise)
        .all()
    )
    return jsonify([a[0] for a in analises])


@api_bp.route("/api/cliente/<instalacao>")
def get_cliente_by_instalacao(instalacao):
    try:
        cliente = Instalacao.query.filter(Instalacao.INSTALACAO.contains(instalacao)).first()
        return jsonify({
            'regiao': cliente.EMPRESA,
            'instalacao': cliente.INSTALACAO,
            'cnpj': cliente.CNPJ,
            #'CPF': cliente.CPF,
            'nivel_tensao': cliente.TIPO_CLIENTE,
            'carga': cliente.CARGA,
            'nome': cliente.NOME_PARCEIRO,
            'cep': cliente.CEP
        })
    except Exception as e:
        return Response(status=204)


@api_bp.route("/api/cliente/cnpj/<cnpj>")
def get_cliente_by_cnpj(cnpj):
    try:
        cliente = Instalacao.query.filter(Instalacao.CNPJ.contains(cnpj)).first()
        return jsonify({
            'regiao': cliente.EMPRESA,
            'instalacao': cliente.INSTALACAO,
            'cnpj': cliente.CNPJ,
            #'CPF': cliente.CPF,
            'nivel_tensao': cliente.TIPO_CLIENTE,
            'carga': cliente.CARGA,
            'nome': cliente.NOME_PARCEIRO,
            'cep': cliente.CEP
        })
    except Exception as e:
        return Response(status=204)



@api_bp.route("/api/consulta/<cnpj>")
def cadastra_cnpj(cnpj):
    empresa = Empresa.query.filter(Empresa.cnpj.contains(cnpj)).first()
    if not empresa:
        try:
            data = get_cnpj(cnpj)
            nova_empresa = Empresa(
                nome_empresa=data['nome'],
                cnpj=only_digits(data['cnpj']),
                abertura=convert_date(data['abertura']),
                situacao=data['situacao'],
                tipo=data['tipo'],
                porte=data['porte'],
                natureza_juridica=data['natureza_juridica'],
                logradouro=data['logradouro'],
                numero=data['numero'],
                complemento=data['complemento'],
                municipio=data['municipio'],
                bairro=data['bairro'],
                uf=data['uf'],
                cep=only_digits(data['cep']),
                email=data['email'],
                telefone=data['telefone'],
                data_situacao=convert_date(data['data_situacao']),
                ultima_atualizacao=iso_para_sql_datetime(data['ultima_atualizacao']),
                status=data['status'],
                fantasia=data['fantasia'],
                efr=data['efr'],
                motivo_situacao=data['motivo_situacao'],
                situacao_especial=data['situacao_especial'],
                data_situacao_especial=convert_date(data['data_situacao_especial'])
            )
            db.session.add(nova_empresa)
            db.session.flush()

            for socio in data['qsa']:
                novo_socio = Socio(
                    nome=socio['nome'],
                    cargo=socio['qual'],
                    id_empresa=nova_empresa.id_empresa
                )
                db.session.add(novo_socio)
            db.session.commit()
            return jsonify({'id_empresa': nova_empresa.id_empresa, 'nome': data['nome']})
        except Exception as e:
            print(str(e))
            db.session.rollback()
            flash("Houve um erro ao cadastrar a empresa, vamos cadastrar uma empresa fictícia. Após a correção do "
                  "erro por favor edite o estudo e coloque a empresa desejada.")
            return jsonify({'id_empresa': 1})
    else:
        return jsonify({
            'id_empresa': empresa.id_empresa,
            'nome': empresa.nome_empresa
        })


@api_bp.route("/api/tipo_pedidos/<viabilidade>/<analise>")
def get_pedidos(viabilidade, analise):
    solicitacoes = (
        db.session.query(TipoSolicitacao.id_tipo_solicitacao, TipoSolicitacao.pedido)
        .filter_by(viabilidade=viabilidade, analise=analise)
        .order_by(TipoSolicitacao.pedido)
        .all()
    )
    return jsonify([{"id": s.id_tipo_solicitacao, "pedido": s.pedido} for s in solicitacoes])

@api_bp.route("/api/id_tipo_solicitacao/<viabilidade>/<analise>/<pedido>")
def get_id_tipo_solicitacao(viabilidade, analise, pedido):
    item = (
        db.session.query(TipoSolicitacao.id_tipo_solicitacao)
        .filter_by(viabilidade=viabilidade, analise=analise, pedido=pedido)
        .first()
    )
    return jsonify({"id": item.id_tipo_solicitacao})

    pass


@api_bp.route('/api/dashboard/stats')
def dashboard_stats():
    """Estatísticas para o dashboard - queries otimizadas"""

    try:
        stats = get_dashboard_stats()

        return jsonify({
            'total_estudos': stats['total_estudos'],
            'estudos_por_regional': [
                {'regional': regional, 'total': total}
                for regional, total in stats['estudos_por_regional']
            ],
            'estudos_por_status': [
                {'status': status, 'total': total}
                for status, total in stats['estudos_por_status']
            ]
        })

    except Exception as e:
        return jsonify({
            'error': 'Erro ao obter estatísticas',
            'message': str(e)
        }), 500


@api_bp.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({'error': 'Erro interno do servidor'}), 500


@api_bp.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint não encontrado'}), 404

@api_bp.route("/api/municipio/<municipio>/<int:id_edp>")
def search_municipio_by_edp(municipio, id_edp):
    municipio = municipio.upper()
    municipio = Municipio.query.filter_by(id_edp=id_edp, municipio=municipio).first()
    return {'id': municipio.id_municipio, 'id_regional':municipio.id_regional}

# Rotas AJAX para filtros dinâmicos no forms Cadastrar
@api_bp.route("/api/municipios/<int:id_edp>")
def get_municipios_by_edp(id_edp):
    """API para buscar municípios por EDP"""
    municipios = Municipio.query.filter_by(id_edp=id_edp).all()
    return {'municipios': [{'id': m.id_municipio, 'nome': m.municipio} for m in municipios]}
@api_bp.route("/api/municipios_by_regional/<int:id_regional>")
def get_municipios_by_regional(id_regional):
    regional = Regional.query.get_or_404(id_regional)
    municipios = Municipio.query.filter_by(id_regional=id_regional).all()
    if len(municipios) == 0:
        municipios = Municipio.query.filter_by(id_edp=regional.id_edp).all()

    return {'municipios': [{'id': m.id_municipio, 'nome': m.municipio} for m in municipios]}

@api_bp.route("/api/regionais/<int:id_edp>")
def get_regionais_by_edp(id_edp):
    """API para buscar regionais por EDP"""
    regionais = Regional.query.filter_by(id_edp=id_edp).all()
    return {'regionais': [{'id': r.id_regional, 'nome': r.regional} for r in regionais]}


@api_bp.route("/api/circuitos/<int:id_edp>")
def get_circuitos_by_edp(id_edp):
    """API para buscar circuitos por EDP"""
    circuitos = Circuito.query.filter_by(id_edp=id_edp).join(Subestacao).all()
    return {'circuitos': [{'id': c.id_circuito, 'nome': f"{c.circuito} - {c.subestacao.nome}"}
                          for c in circuitos]}


@api_bp.route("/api/circuitos/<int:id_edp>/<subgrupo>")
def get_circuitos_by_edp_and_subgrupo(id_edp, subgrupo):
    """API para buscar circuitos por EDP"""
    if subgrupo == "A2":
        circuitos = Circuito.query.filter_by(id_edp=id_edp).filter(Circuito.tensao > 69).join(Subestacao).all()
    elif subgrupo == 'A4':
        circuitos = Circuito.query.filter_by(id_edp=id_edp).filter(Circuito.tensao < 20).join(Subestacao).all()
    elif subgrupo == 'A3a':
        circuitos = Circuito.query.filter_by(id_edp=id_edp).filter(Circuito.tensao > 20).filter(Circuito.tensao < 69).join(Subestacao).all()
    elif subgrupo == 'A3':
        circuitos = Circuito.query.filter_by(id_edp=id_edp, tensao=69).join(Subestacao).all()
    else:
        return jsonify({'error': 'Circuitos não encontrados'}), 404

    return {'circuitos': [{'id': c.id_circuito, 'nome': f"{c.circuito}"}
                          for c in circuitos]}


@api_bp.route("/api/resp_regioes/<int:id_regional>")
def get_resp_by_regional(id_regional):
    """API para buscar responsáveis por regional"""
    responsaveis = RespRegiao.query.filter_by(id_regional=id_regional).join(Usuario).all()
    return {'responsaveis': [{'id': r.id_resp_regiao, 'nome': f"{r.usuario.nome} ({r.ano_ref})"}
                             for r in responsaveis]}


@api_bp.route("/api/fator_k/<int:id_edp>/<subgrupo>/<data_ref>/<carga>")
def get_fator_k(id_edp, subgrupo, data_ref, carga):
    # data_ref pode chegar como 'None'/'undefined' quando o estudo ainda não
    # tem data de abertura definida. Sem data válida não há fator aplicável.
    try:
        data_ref_dt = datetime.strptime(data_ref, "%Y-%m-%d")
    except (ValueError, TypeError):
        return jsonify({"k": 0})

    k = (
        FatorK.query.filter(
            and_(
                FatorK.id_edp == id_edp,
                FatorK.subgrupo_tarif == subgrupo,
                FatorK.data_ref <= data_ref_dt,
                # equivale a DATEADD(day, 365, data_ref) >= data_ref_dt, sem
                # depender do dialeto (T-SQL DATEADD nao existe no Databricks)
                FatorK.data_ref >= data_ref_dt - timedelta(days=365),
            )
        )
        .order_by(FatorK.data_ref.desc())
        .first()
    )

    if not k:
        return jsonify({"k": 0})

    if carga == "1":
        return jsonify({"k": k.k})
    else:
        return jsonify({"k": k.kg})

@api_bp.route('/api/imagem_alternativa/<int:id_alt>')
def imagem_alternativa(id_alt):
    alt = Alternativa.query.get_or_404(id_alt)
    if not alt.blob_image:
        return jsonify({'error': 'Sem imagem'}), 404

    # converte o blob em base64
    base64_img = base64.b64encode(alt.blob_image).decode('utf-8')
    mime_type = "image/png"  # ou "image/jpeg" conforme o tipo real
    return jsonify({'imagem': f"data:{mime_type};base64,{base64_img}"})


@api_bp.route("/circuitos-proximos")
def proximos():
    lat = float(request.args["lat"])
    lon = float(request.args["lon"])
    regional = request.args.get("regional")
    idx = get_index()
    res = idx.mais_proximos(lat, lon, k=3, regional=regional)

    # cor distinta por circuito (do mais próximo ao mais distante)
    CORES = ["#2563eb", "#f59e0b", "#7c3aed"]   # azul, laranja, roxo

    # devolve uma FeatureCollection só com os 3, com distância/cor/ordem nas properties
    feats = []
    for ordem, (i, dist) in enumerate(res):
        f = dict(idx.features[i])               # cópia rasa da feature
        f["properties"] = {
            **idx.features[i]["properties"],
            "distancia_m": round(dist, 1),
            "ordem": ordem,
            "cor": CORES[ordem % len(CORES)],
        }
        feats.append(f)

    return jsonify({"type": "FeatureCollection", "features": feats})


def _redigir_sas(texto):
    """Remove valores de parâmetros do SAS (sig, se, st, ...) da saída do azcopy
    para não vazar o token nos logs / na resposta."""
    if not texto:
        return ""
    return re.sub(r'(?i)\b(sig|se|st|sp|spr|sv|sr|sk[a-z]+)=[^&\s"\']+', r'\1=***', texto)


@api_bp.route("/admin/circuitos/atualizar", methods=["POST"])
@requires_permission('admin')
def atualizar_circuitos_geojson():
    """Admin: sincroniza o circuitos.geojson do Azure (download) via azcopy e
    recarrega o índice em memória."""
    dest_url = os.getenv("CIRCUITOS_SAS_URL")
    if not dest_url:
        return jsonify({"status": "error",
                        "message": "CIRCUITOS_SAS_URL não configurada no ambiente (.env)."}), 500

    azcopy = os.getenv("AZCOPY_PATH", "azcopy")
    local_dir = os.path.dirname(os.path.abspath(GEOJSON_PATH))   # pasta data/

    # Download: Azure (origem) -> local (destino). delete-destination=false p/ não
    # apagar arquivos locais que não existam no container.
    cmd = [azcopy, "sync", dest_url, local_dir,
           "--recursive", "--delete-destination=false"]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    except FileNotFoundError:
        return jsonify({"status": "error",
                        "message": f"azcopy não encontrado em '{azcopy}'. "
                                   f"Instale o azcopy ou ajuste AZCOPY_PATH."}), 500
    except subprocess.TimeoutExpired:
        return jsonify({"status": "error",
                        "message": "azcopy excedeu o tempo limite (10 min)."}), 504

    saida = _redigir_sas((proc.stdout or "") + "\n" + (proc.stderr or "")).strip()

    if proc.returncode != 0:
        registrar_log('atualizar_circuitos', 'circuitos', None,
                      f'Falha no azcopy sync (rc={proc.returncode}).')
        return jsonify({"status": "error",
                        "message": "Falha no azcopy sync.",
                        "saida": saida[-4000:]}), 500

    # Recarrega o índice em memória com o arquivo recém-baixado.
    idx = get_index(force=True)

    registrar_log('atualizar_circuitos', 'circuitos', None,
                  f'circuitos.geojson sincronizado via azcopy ({len(idx.features)} circuitos).')
    return jsonify({"status": "success",
                    "message": "circuitos.geojson atualizado com sucesso.",
                    "circuitos": len(idx.features),
                    "saida": saida[-4000:]})