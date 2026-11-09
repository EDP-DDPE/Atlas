"""
AtlasAgent — refatorado para operar com LLM local (Ollama) em CPU,
com fallback opcional para o endpoint remoto da EDP.

Decisões de arquitetura desta versão
------------------------------------
1. SYSTEM PROMPTS ESTÁTICOS. Nada de g.user nem histórico interpolado dentro
   do system. O llama.cpp cacheia o prefixo KV entre chamadas; interpolar
   dados variáveis no início invalida o cache e você paga o prefill inteiro
   toda vez. Contexto dinâmico vai como mensagens depois do system.

2. HISTÓRICO COMO TURNOS REAIS, não como um json.dumps() colado no prompt.
   Melhor para o modelo e mantém o prefixo estável.

3. STRUCTURED OUTPUTS via `format` (gramática). Elimina todo o bloco de
   limpeza de markdown e o re.sub() nas quebras de linha.

4. ROTEAMENTO POR TAREFA. classify_intent e generate_sql são interativos
   (usuário esperando). parse_ddpe é batch. Modelos e timeouts diferentes.

5. GUARDA DE SQL EM PYTHON. O prompt pede para não gerar DELETE/DROP; um
   modelo local de 8B obedece bem menos que o Opus. A validação real é
   determinística, antes de tocar o banco.
"""

import json
import os
import re
import threading
import uuid
from datetime import datetime, timedelta

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from flask import g
from sqlalchemy import text

from app.models import db


# =====================================================================
# CONFIGURAÇÃO DE TAREFAS
# =====================================================================
# backend: "ollama" (local) ou "openai" (endpoint remoto da EDP)
#
# Sugestão de partida — ajuste depois de medir no seu corpus real:
#   intent  -> modelo pequeno: 11 classes é tarefa fácil
#   sql     -> a tarefa mais arriscada localmente; considere manter remoto
#   ddpe    -> local sempre: é batch e os dados do cliente não saem da rede

TASKS = {
    "intent": {
        "backend": os.getenv("LLM_BACKEND_INTENT", "ollama"),
        "model": os.getenv("LLM_MODEL_INTENT", "granite4.1:3b"),
        "num_ctx": 8192,
        "timeout": 180,
    },
    "sql": {
        "backend": os.getenv("LLM_BACKEND_SQL", "ollama"),
        "model": os.getenv("LLM_MODEL_SQL", "granite4.1:8b"),
        "num_ctx": 16384,          # o schema do banco ocupa espaço
        "timeout": 300,
    },
    "ddpe": {
        "backend": os.getenv("LLM_BACKEND_DDPE", "ollama"),
        "model": os.getenv("LLM_MODEL_DDPE", "gemma4:26b"),
        "num_ctx": 8192,
        "timeout": 900,            # batch: 2-3 páginas em CPU levam minutos
    },
}

NUM_THREAD = int(os.getenv("LLM_NUM_THREAD", "8"))   # núcleos físicos


# =====================================================================
# SCHEMAS
# =====================================================================

INTENTS = [
    "general_question", "atlas_system_question", "sql_query", "sql_table",
    "sql_plot", "sql_count_summary", "tech_help", "pdf_query",
    "document_question", "ambiguous", "blocked",
]

# reason ANTES de intent: com decodificação por gramática a geração continua
# autorregressiva, então escrever a justificativa primeiro funciona como um
# raciocínio curto que condiciona a classificação. Custa ~20 tokens.
INTENT_SCHEMA = {
    "type": "object",
    "properties": {
        "reason": {"type": "string",
                   "description": "Uma frase curta justificando a escolha."},
        "intent": {"type": "string", "enum": INTENTS},
        "confidence": {"type": "number", "minimum": 0.5, "maximum": 1.0},
    },
    "required": ["reason", "intent", "confidence"],
}

SQL_SCHEMA = {
    "type": "object",
    "properties": {
        "sql": {"type": "string",
                "description": "Uma única instrução SELECT compatível com SQL Server."},
        "comment": {"type": "string",
                    "description": "Resposta curta em primeira pessoa ao usuário. "
                                   "Não cite a query nem o fato de ter consultado o banco."},
    },
    "required": ["sql", "comment"],
}

TIPO_VIAB = ["Orçamento de Conexão", "Orçamento Estimado"]
TIPO_ANALISE = ["Carga", "MMGD", "Autoprodutor", "Produtor Independente",
                "BESS", "Carga e Autoprodutor", "Carga e MMGD"]
TIPO_PEDIDO = ["Aumento de Demanda", "Ligação Nova",
               "Decréscimo de Demanda", "Reserva de Capacidade"]
TIPO_GERACAO = ["Fotovoltaica", "Hidrelétrica", "Termoelétrica", "Eólica", ""]

# descricao/observacao por último: o resumo sai condicionado a todos os
# campos que o modelo acabou de extrair.
DDPE_SCHEMA = {
    "type": "object",
    "properties": {
        "nome_projeto": {"type": "string",
            "description": "Nome ou título do empreendimento como aparece no formulário."},
        "protocolo": {"type": "string",
            "description": "Número de protocolo do pedido. Vazio se ausente."},
        "instalacao": {"type": "string",
            "description": "Código da UC (Unidade Consumidora) do cliente."},
        "cnpj": {"type": "string", "description": "Apenas dígitos, sem pontuação."},
        "empresa_nome": {"type": "string"},
        "municipio": {"type": "string",
            "description": "Município da instalação, sem a sigla do estado."},
        "tensao_kv": {"type": "number",
            "description": "Tensão de conexão do cliente em kV. 0 se não informada."},
        "latitude_cliente": {"type": "string"},
        "longitude_cliente": {"type": "string"},

        "dem_carga_solicit_fp": {"type": "number",
            "description": "Demanda de carga solicitada Fora Ponta, em kW. 0 se ausente."},
        "dem_carga_solicit_p": {"type": "number",
            "description": "Demanda de carga solicitada na Ponta, em kW. 0 se ausente."},
        "dem_ger_solicit_fp": {"type": "number",
            "description": "Demanda de geração solicitada Fora Ponta, em kW. 0 se ausente."},
        "dem_ger_solicit_p": {"type": "number",
            "description": "Demanda de geração solicitada na Ponta, em kW. "
                           "Geração fotovoltaica não gera na Ponta: use 0."},

        "tipo_viab": {"type": "string", "enum": TIPO_VIAB,
            "description": "'Consulta de acesso' equivale a Orçamento Estimado."},
        "tipo_analise": {"type": "string", "enum": TIPO_ANALISE},
        "tipo_pedido": {"type": "string", "enum": TIPO_PEDIDO},
        "tipo_geracao": {"type": "string", "enum": TIPO_GERACAO,
            "description": "Vazio quando o pedido não envolve geração."},

        "data_abertura_cliente": {"type": "string",
            "description": "Data de assinatura do formulário, formato AAAA-MM-DD."},
        "data_desejada_cliente": {"type": "string",
            "description": "Data desejada de conexão, AAAA-MM-DD. Vazio se não constar."},

        "descricao": {"type": "string",
            "description": "Resumo de 2 a 4 frases do processo, em português técnico. "
                           "Diga o que o cliente pede, o porte da carga ou geração, "
                           "onde fica e em que tensão. Não repita rótulos de campo."},
        "observacao": {"type": "string",
            "description": "Pontos de atenção para o engenheiro: inconsistências, "
                           "campos ausentes, condições incomuns, prazos apertados. "
                           "Vazio se não houver nada relevante."},
    },
    "required": ["nome_projeto", "instalacao", "municipio", "tensao_kv",
                 "tipo_viab", "tipo_analise", "tipo_pedido",
                 "data_abertura_cliente", "descricao", "observacao"],
}


# =====================================================================
# SYSTEM PROMPTS — ESTÁTICOS. Nunca interpole nada aqui.
# =====================================================================

SYS_INTENT = """Você é o classificador de intenção do Atlas, o sistema de \
gerenciamento de estudos do Planejamento da Expansão da EDP. Um estudo também \
pode ser chamado de processo, anteprojeto, carta ou documento, e pode ter \
várias alternativas.

Classifique a última mensagem do usuário em uma das intenções:

general_question       — assunto geral: história, ciência, conceitos.
atlas_system_question  — obras, estudos, alternativas, transformadores,
                         circuitos, perdas, BDGD. Não pede SQL.
sql_query              — pede dados do banco que não sejam tabela nem lista,
                         ou que envolvam agregação analítica.
sql_table              — pede explicitamente TABELA ou LISTA, ou análise
                         agrupada por algum campo.
sql_plot               — pede GRÁFICO.
sql_count_summary      — pede apenas contagem simples ou total.
tech_help              — programação: Python, SQL, HTML, CSS, R, Flask, Spark.
pdf_query              — pergunta sobre PDF ou Word anexado agora.
document_question      — pergunta sobre arquivo, tabela ou gráfico já
                         produzido antes no chat.
ambiguous              — impossível entender o pedido.
blocked                — pede algo proibido: apagar ou sobrescrever dados,
                         ou acessar dados sensíveis.

Desempate: SQL + gráfico -> sql_plot. SQL + tabela -> sql_table.
Contagem -> sql_count_summary. "Analise o estudo 123" sem formato -> sql_query.

Classifique apenas pelo texto. Nunca invente informação."""


SYS_SQL = """Você é o especialista em SQL do Atlas, sistema de gerenciamento de \
estudos do Planejamento da Expansão da EDP. Transforme a pergunta do usuário em \
SQL válido para SQL Server.

REGRAS
- Gere exatamente uma instrução SELECT. Nunca DELETE, UPDATE, INSERT, DROP,
  TRUNCATE, ALTER ou CREATE. Se o usuário pedir isso, devolva um SELECT inócuo
  e explique no comment que operações destrutivas não são permitidas.
- Use somente tabelas e colunas do schema fornecido. Nunca invente nada.
- Nomes de colunas retornados devem ser legíveis: sem underline, sem abreviação.
- Nunca use colunas TEXT ou NTEXT em GROUP BY ou ORDER BY. Faça
  CAST(coluna AS NVARCHAR(MAX)).
- Para filtros de data prefira data_registro, salvo pedido explícito de outra.
- No comment, nunca cite a query nem mencione que consultou o banco. Responda
  em primeira pessoa, direto, como se já tivesse entregue o resultado.

MODELO DE DADOS
- atlas.estudos guarda os registros principais.
- atlas.alternativas guarda as alternativas de cada estudo; custo_modular é o
  custo da alternativa.
- Ignore as tabelas Obras e Kits.
- Prefira sempre o responsável da região, não o criador do registro.
  atlas.resp_regioes tem o id_usuario do engenheiro responsável pela região.
- atlas.tipo_solicitacao classifica o estudo:
    coluna viabilidade — Orçamento de Conexão, Orçamento Estimado,
                         Plano de Obras, DAL
    coluna analise     — Carga, MMGD (também dita "geração"; use MMGD),
                         AutoProdutor, Produtor Independente, Anteprojeto,
                         ANEEL, ONS
    coluna pedido      — Ligação Nova, Aumento ou Redução de Demanda,
                         Linhas, Redes, Subestações

ALIASES OBRIGATÓRIOS
  atlas.estudos e | atlas.alternativas a | atlas.status_tipo st
  atlas.resp_regioes rr | atlas.usuarios usr | atlas.tipo_solicitacao ts

  JOIN atlas.estudos e            ON e.id_estudo = a.id_estudo
  JOIN atlas.tipo_solicitacao ts  ON ts.id_tipo_solicitacao = e.id_tipo_solicitacao
  JOIN atlas.status_tipo st       ON st.id_status = a.id_status
  JOIN atlas.resp_regioes rr      ON rr.id_resp_regiao = e.id_resp_regiao
  JOIN atlas.usuarios usr         ON usr.id_usuario = rr.id_usuario

GRÁFICOS
Quando a intenção for gráfico, gere o SELECT normalmente com EXATAMENTE duas
colunas, sendo a última numérica. No comment, diga que vai montar o gráfico."""


SYS_DDPE = """Você extrai dados de formulários DDPE de acesso à rede da EDP.

Leia o documento e preencha o schema. Regras:
- Use apenas o que está escrito no documento. Nunca invente valores.
- Campo ausente: string vazia, ou 0 para numéricos.
- Nos resumos, escreva em português técnico do setor elétrico, na terceira
  pessoa, sem preâmbulo e sem repetir os campos já estruturados."""


# =====================================================================
# GUARDA DE SQL — determinística, não confia no prompt
# =====================================================================

_SQL_PROIBIDO = re.compile(
    r"\b(delete|update|insert|drop|truncate|alter|create|merge|grant|revoke|"
    r"exec|execute|sp_\w+|xp_\w+|into\s+\w+)\b",
    re.IGNORECASE,
)


class SqlInseguro(Exception):
    pass


def validar_sql(sql: str) -> str:
    s = sql.strip().rstrip(";").strip()
    if not s:
        raise SqlInseguro("SQL vazio.")
    if ";" in s:
        raise SqlInseguro("Múltiplas instruções não são permitidas.")
    if not re.match(r"^\s*(select|with)\b", s, re.IGNORECASE):
        raise SqlInseguro("Apenas SELECT é permitido.")
    if _SQL_PROIBIDO.search(s):
        raise SqlInseguro("Comando destrutivo detectado.")
    return s


# =====================================================================
# AGENTE
# =====================================================================

class AtlasAgent:

    def __init__(self, llm_url=None, llm_token=None, ollama_host=None):
        self.ollama_host = ollama_host or os.getenv("OLLAMA_HOST",
                                                    "http://localhost:11434")
        self.llm_url = llm_url
        self.llm_token = llm_token

        # Em CPU a inferência é limitada por banda de memória: duas requisições
        # simultâneas não rodam em paralelo, cada uma fica na metade da
        # velocidade. Serializar dá latência previsível e evita timeout em
        # cascata. Mantenha também OLLAMA_NUM_PARALLEL=1 no serviço.
        self._lock = threading.Lock()

        self._ollama_clients = {}
        self._oai = None

    # ---------- backends ----------

    def _ollama(self, timeout):
        from ollama import Client
        if timeout not in self._ollama_clients:
            self._ollama_clients[timeout] = Client(host=self.ollama_host,
                                                   timeout=timeout)
        return self._ollama_clients[timeout]

    def _openai(self):
        if self._oai is None:
            from openai import OpenAI
            self._oai = OpenAI(api_key=self.llm_token, base_url=self.llm_url)
        return self._oai

    # ---------- chamada unificada ----------

    def _chat_json(self, task, system, messages, schema, max_attempts=2):
        """Retorna dict. `messages` são só os turnos dinâmicos."""
        cfg = TASKS[task]
        full = [{"role": "system", "content": system}] + messages
        last_err = None

        for attempt in range(max_attempts):
            try:
                with self._lock:
                    if cfg["backend"] == "ollama":
                        raw = self._call_ollama(cfg, full, schema)
                    else:
                        raw = self._call_openai(cfg, full, schema)
                return json.loads(raw)
            except Exception as e:
                last_err = e
                print(f"[LLM:{task}] tentativa {attempt + 1} falhou: {e}")

        raise RuntimeError(f"Falha ao chamar LLM na tarefa '{task}': {last_err}")

    def _call_ollama(self, cfg, messages, schema):
        resp = self._ollama(cfg["timeout"]).chat(
            model=cfg["model"],
            messages=messages,
            format=schema,          # gramática: JSON válido por construção
            think=False,            # sem isso o modelo raciocina por minutos
            keep_alive=-1,          # não descarregar: recarregar do HDD custa minutos
            options={
                "temperature": 0,
                "num_ctx": cfg["num_ctx"],
                "num_thread": NUM_THREAD,
            },
        )
        return resp.message.content

    def _call_openai(self, cfg, messages, schema):
        # O gateway da EDP pode não suportar response_format com json_schema,
        # então o schema vai como instrução e a saída é limpa na mão.
        msgs = list(messages)
        msgs[0] = {
            "role": "system",
            "content": msgs[0]["content"]
                       + "\n\nResponda APENAS com um JSON puro, sem markdown, "
                         "aderente a este JSON Schema:\n"
                       + json.dumps(schema, ensure_ascii=False),
        }
        r = self._openai().chat.completions.create(
            messages=msgs, model=cfg["model"],
            max_tokens=4096, temperature=0, timeout=cfg["timeout"],
        )
        return r.choices[0].message.content.replace("```json", "").replace("```", "").strip()

    # ---------- contexto dinâmico ----------

    @staticmethod
    def _contexto_usuario():
        return {
            "role": "user",
            "content": (f"[contexto] Usuário: {g.user.nome} "
                        f"({g.user.first_name}), matrícula {g.user.matricula}, "
                        f"id_usuario {g.user.id_usuario}."),
        }

    @staticmethod
    def _historico(hist, limite=8):
        """Converte o histórico em turnos reais, truncado.

        O histórico ilimitado do código antigo fazia o prompt crescer sem teto —
        em CPU isso significa prefill crescendo a cada mensagem da conversa.
        """
        turnos = []
        for h in (hist or [])[-limite:]:
            role = h.get("role") or ("user" if h.get("user") else "assistant")
            content = h.get("content") or h.get("user") or h.get("assistant") or ""
            if content:
                turnos.append({"role": role, "content": str(content)[:2000]})
        return turnos

    # ---------- 1. intenção ----------

    def classify_intent(self, user_message, hist):
        messages = ([self._contexto_usuario()]
                    + self._historico(hist)
                    + [{"role": "user", "content": user_message}])
        return self._chat_json("intent", SYS_INTENT, messages, INTENT_SCHEMA)

    # ---------- 2. SQL ----------

    def generate_sql(self, question, schema, hist):
        messages = ([self._contexto_usuario()]
                    + [{"role": "user",
                        "content": f"[schema do banco]\n{schema}"}]
                    + self._historico(hist)
                    + [{"role": "user", "content": question}])

        out = self._chat_json("sql", SYS_SQL, messages, SQL_SCHEMA)
        out["sql"] = validar_sql(out.get("sql", ""))   # levanta SqlInseguro
        return out

    # ---------- 3. DDPE ----------

    def parse_ddpe(self, pdf_text):
        messages = [{"role": "user", "content": pdf_text}]
        d = self._chat_json("ddpe", SYS_DDPE, messages, DDPE_SCHEMA)
        return self._pos_processar_ddpe(d)

    # alias para não quebrar chamadas existentes
    parse_pdf = parse_ddpe

    @staticmethod
    def _pos_processar_ddpe(d):
        """O que é determinístico sai do LLM e vem para cá."""
        tensao = d.pop("tensao_kv", 0) or 0
        d["classe"] = 2 if 0 < tensao < 69 else 1        # 1=AT, 2=MT
        d["tensao_kv"] = tensao

        uf = UF_POR_MUNICIPIO.get((d.get("municipio") or "").strip())
        d["edp"] = {"SP": 1, "ES": 2}.get(uf)            # None se desconhecido

        d["data_vencimento_cliente"] = ""
        abertura = d.get("data_abertura_cliente") or ""
        if abertura:
            try:
                base = datetime.strptime(abertura, "%Y-%m-%d")
                d["data_vencimento_cliente"] = (base + timedelta(days=30)
                                                ).strftime("%Y-%m-%d")
            except ValueError:
                pass

        # marcação para a UI: campos gerados por IA e não verificáveis
        d["_campos_gerados"] = ["descricao", "observacao"]
        return d

    # ---------- 4. execução ----------

    def run_sql(self, sql):
        sql = validar_sql(sql)     # segunda barreira, caso venha de outro caminho
        result = db.session.execute(text(sql))
        return pd.DataFrame(result.mappings().all())

    # ---------- 5. gráfico ----------

    def create_plot(self, df, x, y, chat_id):
        fig_id = f"chart_{uuid.uuid4().hex[:8]}.png"
        base_dir = os.path.abspath(os.path.dirname(__file__))
        path = os.path.join(base_dir, "chats", g.user.matricula, chat_id, "charts")
        os.makedirs(path, exist_ok=True)

        plt.figure(figsize=(8, 5))
        plt.bar(df[x], df[y])
        plt.tight_layout()
        plt.savefig(os.path.join(path, fig_id))
        plt.close()
        return fig_id


# Substitua por um lookup real — você já tem as malhas do IBGE
UF_POR_MUNICIPIO = {"São Paulo": "SP", "Vitória": "ES"}