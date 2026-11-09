from flask import Flask, render_template, session, redirect, url_for, request, g
import os
from werkzeug.middleware.proxy_fix import ProxyFix
import msal
import requests
from dotenv import load_dotenv
from urllib.parse import quote_plus
from flask_session import Session
from app.auth.routes import create_auth_blueprint
from app.auth import get_usuario_logado
from app.database import init_database, db_manager
from app.models import Usuario
from json import JSONEncoder
from decimal import Decimal




class CustomJSONEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


def create_app():

    load_dotenv()
    # O índice de circuitos é carregado sob demanda (lazy) em circuito_geojson.get_index()
    #app_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

    app = Flask(__name__, instance_relative_config=True, template_folder=os.path.join(os.path.dirname(__file__), '..', 'templates'), static_folder="static", static_url_path='/static')
    app.json_encoder = CustomJSONEncoder
    #app = Flask(__name__, instance_relative_config=True, template_folder=os.path.join(os.path.dirname(__file__), '..', 'templates'), static_folder=os.path.join(app_dir, 'static'), static_url_path='/static')

    app.wsgi_app = ProxyFix(
        app.wsgi_app,
        x_for=1,
        x_proto=1,
        x_host=1,
        x_port=1
    )

    # Registrar getattr no Jinja2, para utiliza no template genérico
    app.jinja_env.globals['getattr'] = getattr

    app.config.from_mapping(
        SECRET_KEY=os.getenv("FLASK_SECRET"),
        SESSION_TYPE="filesystem",
        SESSION_PERMANENT=False,
        SESSION_USE_SIGNER=True,
        SESSION_FILE_THRESHOLD=100,
        UPLOAD_FOLDER='uploads',  # ou caminho desejado
        TEMPLATE_FOLDER='templates_docs', # add caminho para os templates dos documentos (OE, EV, ...)
        DATABASE=os.path.join(app.instance_path, 'SQLSERVER'),
        JSON_AS_ASCII=False,
        PREFERRED_URL_SCHEME='https'

    )

    app.config['SESSION_COOKIE_SECURE'] = True
    app.config['REMEMBER_COOKIE_SECURE'] = True
    app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    Session(app)

    # ===== Configs de Autenticação (Microsoft Entra ID) =====
    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")  # PROD: prefira certificado/credencial federada
    tenant_id = os.getenv("TENANT_ID")

    # Caminho/URI de redirecionamento (PRECISAM bater com o App Registration)
    redirect_path = os.getenv("REDIRECT_PATH", "auth/callback")
    #redirect_uri = os.getenv("REDIRECT_URI", f"http://localhost:5000/auth{redirect_path}")
    #redirect_uri = os.getenv("REDIRECT_URI", f"https://172.20.70.54/auth{redirect_path}")
    redirect_uri = os.getenv("REDIRECT_URI", f"https://{os.getenv('HOST', '172.20.70.54')}/auth{redirect_path}")

    # Authority (single-tenant). Para multi-tenant, avalie 'organizations' ou 'common'
    authority = f"https://login.microsoftonline.com/{tenant_id}"

    # Scopes OIDC + Graph (delegado)
    scopes = ["User.Read"]

    if not isinstance(scopes, list):
        scopes = list(scopes)

    app.config.update(
        AUTH_CLIENT_ID=client_id,
        AUTH_CLIENT_SECRET=client_secret,
        AUTH_TENANT_ID=tenant_id,
        AUTH_AUTHORITY=authority,
        AUTH_REDIRECT_PATH=redirect_path,
        AUTH_REDIRECT_URI=redirect_uri,
        AUTH_SCOPES=scopes,
    )

    init_database(app)

    # ===== Registro de blueprints =====
    # Importação tardia para evitar ciclos
    from .routes import main_bp
    from app.cadastro.routes import cadastro_bp
    from app.listar.routes import listar_bp
    from app.api.routes import api_bp
    from app.subestacoes.routes import subestacao_bp
    from app.user.routes import user_bp
    from app.municipios.routes import municipio_bp
    from app.alternativa.routes import alternativa_bp
    from app.circuitos.routes import circuito_bp
    from app.status.routes import status_bp
    from app.deploy.routes import deploy_bp
    from app.gerencial.routes import gestao_bp
    from app.tipo_solicitacao.routes import tipo_solicitacao_bp
    from app.status_tipos.routes import status_tipos_bp
    from app.regionais.routes import regionais_bp
    from app.resp_regioes.routes import resp_regioes_bp
    from app.empresas.routes import empresas_bp
    from app.bot.routes import bot_bp
    from app.admin.routes import admin_bp
    from app.analises_ovs_notas.routes import analises_ovs_notas_bp

    app.register_blueprint(create_auth_blueprint(redirect_path="/callback"), url_prefix="/auth")
    # REDIRECT_URI deve ser http://localhost:5000/auth/callback

    app.register_blueprint(cadastro_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(listar_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(subestacao_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(municipio_bp)
    app.register_blueprint(alternativa_bp)
    app.register_blueprint(circuito_bp)
    app.register_blueprint(status_bp)
    app.register_blueprint(deploy_bp)
    app.register_blueprint(gestao_bp)
    app.register_blueprint(tipo_solicitacao_bp)
    app.register_blueprint(status_tipos_bp)
    app.register_blueprint(regionais_bp)
    app.register_blueprint(resp_regioes_bp)
    app.register_blueprint(empresas_bp)
    app.register_blueprint(bot_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(analises_ovs_notas_bp)


    # with app.app_context():
    #     print("\n[DEBUG] Rotas registradas:")
    #     for rule in app.url_map.iter_rules():
    #         print(f"- {rule.rule} -> {rule.endpoint}")
    @app.before_request
    def before_request():
        from flask import request
        if request.headers.get('X-Forwarded-Proto') == 'https':
            request.environ['wsgi.url_scheme'] = 'https'

    @app.before_request
    def carregar_usuario():

        g.user = get_usuario_logado()
        if g.user:
            g.user.first_name = str(g.user.nome).split(sep=' ')[0]
            g.user.chat_dir = f'app/bot/chats/{g.user.matricula}'

    @app.context_processor
    def inject_user():
        return dict(user=g.user)

    # Pré-aquece o índice de circuitos em background (não bloqueia o startup).
    # No modo debug o reloader cria 2 processos; só o FILHO que atende requests
    # define WERKZEUG_RUN_MAIN='true' -> evita carregar 2x. Em produção (waitress
    # via wsgi.py) o aquecimento é disparado lá, onde a var não existe.
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        aquecer_circuitos()

    return app


def aquecer_circuitos():
    """Carrega o índice de circuitos em uma thread de fundo (não bloqueia)."""
    import threading
    from app.utils.circuito_geojson import get_index
    threading.Thread(target=get_index, daemon=True, name="warmup-circuitos").start()