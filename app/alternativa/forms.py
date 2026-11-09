import re
from decimal import Decimal, InvalidOperation

from flask_wtf import FlaskForm
from wtforms import (
    StringField, TextAreaField, DecimalField, BooleanField,
    SelectField, FloatField, IntegerField, FileField
)
from wtforms.validators import DataRequired, Optional, NumberRange, InputRequired
from wtforms.widgets import TextArea
from app.models import Estudo, Circuito, FatorK


class DecimalBRField(DecimalField):
    """DecimalField que aceita o número no formato brasileiro.

    Aceita "1.234,56", "1234,56", "R$ 1.234,56" e também "1234.56". Com
    milhar=False (coordenadas) o ponto é sempre separador decimal, para que
    -46.633 não vire -46633.
    """

    def __init__(self, *args, milhar=True, **kwargs):
        super().__init__(*args, **kwargs)
        self.milhar = milhar

    @staticmethod
    def _normalizar(texto, milhar):
        limpo = re.sub(r'[R$%\s]', '', texto)

        if ',' in limpo:
            # vírgula é o separador decimal; o ponto, se houver, é de milhar
            limpo = limpo.replace('.', '').replace(',', '.')
        elif milhar and re.fullmatch(r'[+-]?\d{1,3}(\.\d{3})+', limpo):
            # só pontos, em grupos de três dígitos: separador de milhar
            limpo = limpo.replace('.', '')

        return limpo

    def process_formdata(self, valuelist):
        if not valuelist:
            return

        texto = self._normalizar(str(valuelist[0]), self.milhar)

        if not texto:
            self.data = None
            return

        try:
            self.data = Decimal(texto)
        except InvalidOperation:
            self.data = None
            raise ValueError(
                'Informe um número válido. A casa decimal pode ser vírgula ou ponto (ex.: 1.234,56).'
            )


class AlternativaForm(FlaskForm):
    """Formulário para criar/editar alternativas"""

    imagem_blob = FileField('Imagem da Alternativa')

    # Relacionamentos obrigatórios
    id_estudo = IntegerField('Estudo', validators=[DataRequired()], render_kw={"readonly": True})

    id_circuito = SelectField(
        'Circuito',
        validators=[InputRequired('Selecione um circuito')],
        coerce=int,
        choices=[]
    )

    # Informações básicas
    descricao = TextAreaField(
        'Descrição',
        render_kw={
            'placeholder': 'Descreva a alternativa...',
            'rows': 3
        }
    )

    custo_modular = DecimalBRField(
        'Custo Modular (R$)',
        validators=[
            #DataRequired('O custo modular é obrigatório'),
            NumberRange(min=0, message='O custo deve ser maior ou igual a zero')
        ], default=0,
        places=2,
        render_kw={
            'placeholder': '0.00',
            'step': '0.01',
            'min': '0'
        }
    )

    # Demandas obrigatórias
    dem_fp_ant = DecimalBRField(
        'Demanda FP Anterior (kW)',
        validators=[
            Optional(),
            NumberRange(min=0, message='A demanda deve ser maior ou igual a zero')

        ], default=0,
        places=2,
        render_kw={
            'placeholder': '0.00',
            'step': '0.01',
            'min': '0'
        }
    )

    dem_p_ant = DecimalBRField(
        'Demanda P Anterior (kW)',
        validators=[
            Optional(),
            NumberRange(min=0, message='A demanda deve ser maior ou igual a zero')
        ],default=0,
        places=2,
        render_kw={
            'placeholder': '0.00',
            'step': '0.01',
            'min': '0'
        }
    )

    dem_fp_dep = DecimalBRField(
        'Demanda FP Depois (kW)',
        validators=[
            Optional(),
            NumberRange(min=0, message='A demanda deve ser maior ou igual a zero')
        ],default=0,
        places=2,
        render_kw={
            'placeholder': '0.00',
            'step': '0.01',
            'min': '0'
        }
    )

    dem_p_dep = DecimalBRField(
        'Demanda P Depois (kW)',
        validators=[
            Optional(),
            NumberRange(min=0, message='A demanda deve ser maior ou igual a zero')
        ],default=0,
        places=2,
        render_kw={
            'placeholder': '0.00',
            'step': '0.01',
            'min': '0'
        }
    )

    # Campos opcionais
    latitude_ponto_conexao = DecimalBRField(
        'Latitude do Ponto de Conexão',
        validators=[
            Optional(),
            NumberRange(min=-90, max=90, message='Latitude deve estar entre -90 e 90')
        ],
        places=8,
        milhar=False,
        render_kw={
            'placeholder': 'Ex: -23.5505199',
            'step': '0.00000001'
        }
    )

    longitude_ponto_conexao = DecimalBRField(
        'Longitude do Ponto de Conexão',
        validators=[
            Optional(),
            NumberRange(min=-180, max=180, message='Longitude deve estar entre -180 e 180')
        ],
        places=8,
        milhar=False,
        render_kw={
            'placeholder': 'Ex: -46.6333094',
            'step': '0.00000001'
        }
    )

    demanda_disponivel_ponto = DecimalBRField(
        'Demanda Disponível no Ponto (kW)',
        validators=[
            Optional(),
            NumberRange(min=0, message='A demanda deve ser maior ou igual a zero')
        ],default=0,
        places=2,
        render_kw={
            'placeholder': '0.00',
            'step': '0.01',
            'min': '0'
        }
    )

    ERD = DecimalBRField(
        'ERD',
        validators=[
            Optional(),
        ],
        places=3,
        render_kw={
            'placeholder': '0,00',
        }
    )

    # Flags
    flag_menor_custo_global = BooleanField(
        'Menor Custo Global',
        default=False,
        render_kw={
            'class': 'form-check-input'
        }
    )

    flag_alternativa_escolhida = BooleanField(
        'Alternativa Escolhida',
        default=False,
        render_kw={
            'class': 'form-check-input'
        }
    )

    flag_carga = BooleanField(
        'Carga',
        default=False,
        render_kw={
            'class': 'form-check-input'
        }
    )

    flag_geracao = BooleanField(
        'Geração',
        default=False,
        render_kw={
            'class': 'form-check-input'
        }
    )

    flag_fluxo_reverso = BooleanField(
        'Fluxo Reverso',
        default=False,
        render_kw={
            'class': 'form-check-input'
        }
    )

    proporcionalidade = DecimalBRField(
        'Proporcionalidade',
        places=2,
        render_kw={
            'placeholder': '0.00',
            'step': '0.01',
            'min': '0',
            'max': '1'
        }
    )

    letra_alternativa = SelectField(
        'Alternativa',
        validators=[DataRequired('Selecione uma letra')],
        choices=[('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D'), ('E', 'E'), ('F', 'F')]
    )

    etapa = SelectField(
        'Escalonamento',
        validators=[DataRequired('Selecione uma letra')],
        choices=[(1, '1ª Etapa/única'), (2, '2ª Etapa'), (3, '3ª Etapa'), (4, '4ª Etapa'), (5, '5ª Etapa'), (6, '6ª Etapa')]
    )

    subgrupo_tarif = SelectField(
        'Subgrupo Tarifário',
        validators=[Optional()],
        choices=[('A4', 'A4'), ('A3a', 'A3a'), ('A3', 'A3'), ('A2', 'A2')]
    )

    # Observações
    observacao = TextAreaField(
        'Observações',
        validators=[Optional()],
        render_kw={
            'placeholder': 'Observações adicionais sobre a alternativa...',
            'rows': 3
        }
    )

    def __init__(self, *args, **kwargs):
        """Inicializar formulário e popular choices"""
        super(AlternativaForm, self).__init__(*args, **kwargs)

        # Popular choices para circuitos
        self.id_circuito.choices = [(0, 'Selecione um circuito')] + \
                                   [(circuito.id_circuito, f"{circuito.circuito}") for circuito in Circuito.query.all()]

    def atualizar_circuitos(self, regiao: int, classe:str):

        if classe == "A2":
            circuitos = Circuito.query.filter_by(id_edp=regiao).filter(Circuito.tensao > 69).order_by(Circuito.circuito).all()
        elif classe == 'A3':
            circuitos = Circuito.query.filter_by(id_edp=regiao).filter(Circuito.tensao == 69).order_by(
                Circuito.circuito).all()
        elif classe == 'A3a':
            circuitos = Circuito.query.filter_by(id_edp=regiao).filter(Circuito.tensao == 34.5).order_by(
                Circuito.circuito).all()
        else:
            circuitos = Circuito.query.filter_by(id_edp=regiao).filter(Circuito.tensao < 30).order_by(
                Circuito.circuito).all()

        self.id_circuito.choices = [(0, 'Selecione um circuito')] + \
                                   [(circuito.id_circuito, f"{circuito.circuito}") for circuito in circuitos]

    def validate_flags(self):
        """Validação customizada para flags"""
        errors = []

        # Se uma alternativa é escolhida, deve ter menor custo global ou justificativa
        if (self.flag_alternativa_escolhida.data and
                not self.flag_menor_custo_global.data and
                not self.observacao.data):
            errors.append(
                'Alternativas escolhidas que não possuem menor custo global devem ter observações explicativas.'
            )

        return errors

    def validate_localizacao(self):
        """Validação customizada para localização"""
        errors = []

        # Se uma coordenada foi fornecida, a outra também deve ser
        lat = self.latitude_ponto_conexao.data
        lon = self.longitude_ponto_conexao.data

        if (lat is not None and lon is None) or (lat is None and lon is not None):
            errors.append('Latitude e longitude devem ser fornecidas juntas.')

        return errors


class FiltroAlternativaForm(FlaskForm):
    """Formulário para filtros de alternativas"""

    estudo = SelectField(
        'Estudo',
        validators=[Optional()],
        coerce=int,
        choices=[]
    )

    circuito = SelectField(
        'Circuito',
        validators=[Optional()],
        coerce=int,
        choices=[]
    )

    menor_custo_global = SelectField(
        'Menor Custo Global',
        validators=[Optional()],
        choices=[
            ('', 'Todos'),
            ('1', 'Sim'),
            ('0', 'Não')
        ]
    )

    alternativa_escolhida = SelectField(
        'Alternativa Escolhida',
        validators=[Optional()],
        choices=[
            ('', 'Todos'),
            ('1', 'Sim'),
            ('0', 'Não')
        ]
    )

    custo_min = DecimalBRField(
        'Custo Mínimo (R$)',
        validators=[
            Optional(),
            NumberRange(min=0, message='O custo deve ser maior ou igual a zero')
        ],
        places=2,
        render_kw={
            'placeholder': '0.00',
            'step': '0.01',
            'min': '0'
        }
    )

    custo_max = DecimalBRField(
        'Custo Máximo (R$)',
        validators=[
            Optional(),
            NumberRange(min=0, message='O custo deve ser maior ou igual a zero')
        ],
        places=2,
        render_kw={
            'placeholder': '0.00',
            'step': '0.01',
            'min': '0'
        }
    )

    def __init__(self, *args, **kwargs):
        """Inicializar formulário e popular choices"""
        super(FiltroAlternativaForm, self).__init__(*args, **kwargs)

        # # Popular choices para estudos
        # self.estudo.choices = [('', 'Todos os estudos')] + [
        #     (estudo.id_estudo, estudo.nome)
        #     for estudo in Estudo.query.order_by(Estudo.nome).all()
        # ]
        #
        # # Popular choices para circuitos
        # self.circuito.choices = [('', 'Todos os circuitos')] + [
        #     (circuito.id_circuito, f"{circuito.nome} ({circuito.estudo.nome if circuito.estudo else 'Sem estudo'})")
        #     for circuito in Circuito.query.join(Estudo).order_by(Estudo.nome, Circuito.nome).all()
        # ]

    def validate_custos(self):
        """Validação customizada para range de custos"""
        errors = []

        if (self.custo_min.data is not None and
                self.custo_max.data is not None and
                self.custo_min.data > self.custo_max.data):
            errors.append('O custo mínimo não pode ser maior que o custo máximo.')

        return errors
