from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileRequired
from wtforms import StringField, FloatField, SelectField, DateField, TextAreaField, IntegerField, MultipleFileField
from wtforms.validators import DataRequired, Optional, NumberRange, InputRequired
from datetime import date

ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'jpg', 'jpeg', 'png', 'dwg', 'kmz', 'kml'}


class EstudoForm(FlaskForm):
    # Campos básicos do estudo
    num_doc = StringField('Número do Documento', validators=[DataRequired()], render_kw={"readonly": True})
    protocolo = IntegerField('Protocolo', validators=[Optional()])
    nome_projeto = StringField('Nome do Projeto', validators=[InputRequired()])
    descricao = TextAreaField('Descrição', validators=[Optional()])

    tensao = SelectField('Classe', choices=[], coerce=int, validators=[InputRequired()])

    # Campo instalação (pode ser um número ou texto dependendo do uso)
    instalacao = IntegerField('Unidade Consumidora', validators=[Optional()])
    CNPJ = StringField('CNPJ', validators=[Optional()])
    #CPF = IntegerField('CPF', validators=[Optional()])
    nome_empresa = StringField('Empresa', validators=[Optional()], render_kw={"readonly": True})
    demanda = FloatField('Demanda Contratual', validators=[Optional()], render_kw={"readonly": True})
    id_empresa = IntegerField('id_empresa', validators=[Optional()], render_kw={'style': 'display: none;'})


    # Número de alternativas
    n_alternativas = IntegerField('Número de Alternativas',
                                  validators=[Optional(), NumberRange(min=0)],
                                  default=0, render_kw={"readonly": True})

    # Demandas solicitadas
    dem_carga_atual_fp = FloatField('Demanda Carga atual FP',
                                    validators=[InputRequired(), NumberRange(min=0, max=1000000)], default=0)
    dem_carga_atual_p = FloatField('Demanda Carga atual P',
                                   validators=[InputRequired(), NumberRange(min=0, max=1000000)], default=0)
    dem_carga_solicit_fp = FloatField('Demanda Carga Solicitada FP',
                                      validators=[InputRequired(), NumberRange(min=0, max=1000000)], default=0)
    dem_carga_solicit_p = FloatField('Demanda Carga Solicitada P',
                                     validators=[InputRequired(), NumberRange(min=0, max=1000000)], default=0)
    dem_ger_atual_fp = FloatField('Demanda Geração atual FP',
                                  validators=[InputRequired(), NumberRange(min=0, max=1000000)], default=0)
    dem_ger_atual_p = FloatField('Demanda Geração atual P',
                                 validators=[InputRequired(), NumberRange(min=0, max=1000000)], default=0)
    dem_ger_solicit_fp = FloatField('Demanda Geração Solicitada FP',
                                    validators=[InputRequired(), NumberRange(min=0, max=1000000)], default=0)
    dem_ger_solicit_p = FloatField('Demanda Geração Solicitada P',
                                   validators=[InputRequired(), NumberRange(min=0, max=1000000)], default=0)

    # Coordenadas do cliente
    latitude_cliente = FloatField('Latitude do Cliente',
                                  validators=[Optional(), NumberRange(min=-90, max=90)])
    longitude_cliente = FloatField('Longitude do Cliente',
                                   validators=[Optional(), NumberRange(min=-180, max=180)])

    # Observações
    observacao = TextAreaField('Observações', validators=[Optional()])

    # Datas

    data_registro = DateField('Data de Registro',
                              validators=[DataRequired()],
                              default=date.today)
    data_abertura_cliente = DateField('Data de Abertura do Cliente', validators=[Optional()],)
    data_desejada_cliente = DateField('Data desejada do Cliente', validators=[Optional()])
    data_vencimento_cliente = DateField('Data de Vencimento Cliente', validators=[Optional()])
    data_prevista_conexao = DateField('Data prevista de Conexão', validators=[Optional()])
    data_vencimento_ddpe = DateField('Data de Entrada DDPE', validators=[DataRequired()])

    # data_transgressao = DateField('Data de Transgressão', validators=[Optional()])
    # data_vencimento = DateField('Data de Vencimento', validators=[Optional()])

    # SelectFields para relacionamentos
    edp = SelectField('EDP', coerce=int, validators=[InputRequired()])
    empresa = SelectField('Empresa', coerce=int, validators=[Optional()])
    regional = SelectField('Regional', coerce=int, validators=[InputRequired()])
    municipio = SelectField('Município', coerce=int, validators=[InputRequired()])
    resp_regiao = SelectField('Responsável da Região', coerce=int, validators=[InputRequired()])

    # Tipos
    tipo_viab = SelectField('Tipo de Viabilidade', choices=[], coerce=str, validators=[InputRequired()])
    tipo_analise = SelectField('Tipo de Análise', choices=[], coerce=str, validators=[InputRequired()], validate_choice=False)
    tipo_pedido = SelectField('Tipo de Pedido', choices=[], coerce=str, validators=[InputRequired()], validate_choice=False)
    tipo_geracao = SelectField('Tipo de Geração', choices=[('', ''), ('Fotovoltaica', 'Fotovoltaica'), ('Hidrelétrica', 'Hidrelétrica'), ('Termoelétrica', 'Termoelétrica'), ('Eólica', 'Eólica')], coerce=str)

    # Arquivo anexo (opcional no cadastro inicial)
    arquivos = MultipleFileField('Anexar Documentos',
                        validators=[FileAllowed(ALLOWED_EXTENSIONS, 'Tipo de arquivo não permitido!')])

    def __init__(self, *args, **kwargs):
        super(EstudoForm, self).__init__(*args, **kwargs)
        # Adicionar opção vazia para campos opcionais
        self.empresa.choices = [(0, 'Selecione uma empresa...')]

        self.tensao.choices = [(1, 'Selecione uma classe de tensão...')]
        self.edp.choices = [(1, 'Selecione uma EDP...')]
        self.regional.choices = [(0, 'Selecione uma regional...')]
        self.municipio.choices = [(0, 'Selecione um município...')]
        self.resp_regiao.choices = [(0, 'Selecione um responsável...')]
        self.tipo_viab.choices = [(0, 'Selecione um tipo...')]
        self.tipo_analise.choices = [(0, 'Selecione um tipo...')]
        self.tipo_pedido.choices = [(0, 'Selecione um tipo...')]


class AlternativaForm(FlaskForm):
    """Formulário para cadastro de alternativas de um estudo"""
    descricao = TextAreaField('Descrição da Alternativa', validators=[DataRequired()])

    # Demandas antes e depois
    dem_fp_ant = FloatField('Demanda FP Anterior (kW)',
                            validators=[DataRequired(), NumberRange(min=0)])
    dem_p_ant = FloatField('Demanda P Anterior (kW)',
                           validators=[DataRequired(), NumberRange(min=0)])
    dem_fp_dep = FloatField('Demanda FP Depois (kW)',
                            validators=[DataRequired(), NumberRange(min=0)])
    dem_p_dep = FloatField('Demanda P Depois (kW)',
                           validators=[DataRequired(), NumberRange(min=0)])

    # Coordenadas do ponto de conexão
    latitude_ponto_conexao = FloatField('Latitude Ponto de Conexão',
                                        validators=[Optional(), NumberRange(min=-90, max=90)])
    longitude_ponto_conexao = FloatField('Longitude Ponto de Conexão',
                                         validators=[Optional(), NumberRange(min=-180, max=180)])

    # Custo modular
    custo_modular = FloatField('Custo Modular (R$)',
                               validators=[DataRequired(), NumberRange(min=0)])

    # Campos opcionais
    ERD = FloatField('ERD', validators=[Optional(), NumberRange(min=0)])
    demanda_disponivel_ponto = FloatField('Demanda Disponível no Ponto (kW)',
                                          validators=[Optional(), NumberRange(min=0)])
    observacao = TextAreaField('Observações', validators=[Optional()])

    # Relacionamentos
    circuito = SelectField('Circuito', coerce=int, validators=[InputRequired()])

    def __init__(self, *args, **kwargs):
        super(AlternativaForm, self).__init__(*args, **kwargs)
        self.circuito.choices = [(0, 'Selecione um circuito...')]


class AnexoForm(FlaskForm):
    """Formulário para upload de anexos"""
    arquivos = MultipleFileField('Selecionar Arquivos',
                        validators=[DataRequired(),
                                    FileAllowed(ALLOWED_EXTENSIONS, 'Tipo de arquivo não permitido!')])

    descricao = StringField('Descrição do Arquivo', validators=[Optional()])
