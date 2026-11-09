# import json
# import re
#
# import matplotlib
# matplotlib.use("Agg")
#
# import time
# import matplotlib.pyplot as plt
# import pandas as pd
# import uuid
# from flask import g
# import os
#
# from datetime import datetime
# from openai import OpenAI
# from sqlalchemy import text
# from app.models import db
#
#
# class AtlasAgent:
#
#     def __init__(self, llm_url, llm_token):
#         self.url = llm_url
#         self.token = llm_token
#         self.model = os.getenv("LLM_MODEL", "system.ai.claude-opus-4-8")
#         self.client = OpenAI(
#             api_key=llm_token,
#             base_url=llm_url
#         )
#
#     # ---------------------------
#     # 1. Classificar intenção
#     # ---------------------------
#     def classify_intent(self, user_message, hist):
#
#         system_prompt = f'''
#         Você é o CLASSIFICADOR OFICIAL DE INTENÇÃO do Atlas. Seu nome é Atlas GPT, alguns pode te chamar de CHATlas também em tom de piada.
#
#         Seu trabalho é identificar exatamente qual tipo de tarefa o usuário solicitou.
#
#         O Atlas é o sistema de gerenciamento de estudos do Planejamento da Expansão da EDP.
#         Um estudo pode ser chamado de processo, anteprojeto, carta, documento.
#         Um estudo pode ter várias alternativas.
#
#         Você SEMPRE retorna apenas um JSON com:
#
#         {{
#           "intent": "<tipo>",
#           "confidence": <número entre 0 e 1>,
#           "reason": "<explicação curta>"
#         }}
#
#         -----------------------------------------
#         LISTA OFICIAL DE INTENTS:
#         -----------------------------------------
#         1. general_question
#            - Pergunta sobre qualquer assunto geral: história, cultura, ciência, explicações de conceitos.
#            - Exemplos: “quem é Einstein?”, “explique o que é carga elétrica”.
#
#         2. atlas_system_question
#            - Perguntas sobre obras, estudos, alternativas, transformadores, circuitos, perdas, BDGD.
#            - NÃO pede SQL diretamente.
#            - Exemplos: “como funciona o status de um estudo?”, “como a EDP calcula perdas?”.
#
#         3. sql_query
#            - Quando o usuário pediu dados do banco que não seja uma tabela, lista, ou que utilize um group by.
#            - Exemplos: “conte as alternativas do estudo 123”, “analise o estudo XXX”, "faça um resumo sobre as alternativas do estudo XXX".
#
#         4. sql_table
#            - Quando o usuário pede uma TABELA, uma LISTA ou alguma análise que agrupe por algum campo.
#            - Exemplos: “mostre uma tabela com…”, “retorne uma tabela com…”, "conte quantos estudos por responsável", "liste todos estudos com custo acima de X mil".
#
#         5. sql_plot
#            - Quando o usuário pede GRÁFICO.
#            - Exemplos: “faça um gráfico de barras da carga por dia”.
#
#         6. sql_count_summary
#            - Quando o usuário pede apenas uma contagem simples ou resumo.
#            - Exemplos: “quantas alternativas existem?”, “qual o total de estudos em 2024?”.
#
#         7. tech_help
#            - Perguntas sobre programação: Python, SQL, HTML, CSS, R, Flask, Spark.
#            - Exemplos: “como alterar meu CSS?”, “como fazer join no PySpark?”.
#
#         8. pdf_query
#            - Perguntas sobre o conteúdo de um arquivo PDF/Word anexado.
#            - Exemplos: “o que diz o PDF que anexei?”, “resuma o PDF”.
#
#         9. document_question
#            - Perguntas sobre arquivos já carregados no chat (tabelas, gráficos, anexos).
#            - Exemplos: “explique esse gráfico que você gerou”, “reescreva o texto do Word”.
#
#         10. ambiguous
#             - Usuário escreveu algo impossível de entender.
#
#         11. blocked
#             - Usuário pede algo proibido: deletar do banco, sobrescrever dados, dados sensíveis.
#
#         -----------------------------------------
#         REGRAS IMPORTANTES
#         -----------------------------------------
#         - SEMPRE retorne um JSON. Nunca texto solto.
#         - Nunca invente informações. Classifique apenas pelo texto.
#         - Use “confidence” realista entre 0.50 e 1.00.
#         - Se o usuário pedir algo de SQL + gráfico → sql_plot.
#         - Se pedir SQL + tabela → sql_table.
#         - Se pedir contagem → sql_count_summary.
#         - Se disser “analise o estudo 123” sem formato → sql_query.
#         - Se pedir ajuda técnica → tech_help.
#         - Se mencionar PDF ou “arquivo” → pdf_query.
#         - Se mencionar anexos anteriores → document_question.
#
#         -----------------------------------------
#         EXEMPLOS:
#         -----------------------------------------
#
#         Usuário: “quantas alternativas o estudo 210 possui?”
#         →
#         {{
#          "intent": "sql_count_summary",
#          "confidence": 0.98,
#          "reason": "usuário pede contagem do banco"
#         }}
#
#         Usuário: “faça um gráfico de barras da carga por alimentador”
#         →
#         {{
#          "intent": "sql_plot",
#          "confidence": 0.97,
#          "reason": "usuário pede gráfico baseado em dados"
#         }}
#
#         Usuário: “explique o que é transformador abaixador”
#         →
#         {{
#          "intent": "atlas_system_question",
#          "confidence": 0.91,
#          "reason": "pergunta técnica do setor elétrico"
#         }}
#
#         Usuário: “resuma o PDF que anexei”
#         →
#         {{
#          "intent": "pdf_query",
#          "confidence": 0.95,
#          "reason": "usuário menciona arquivo PDF"
#         }}
#
#         --------------------------------------
#         DADOS DO USUÁRIO:
#         --------------------------------------
#         Você esta falando com o {g.user.first_name}
#         matrícula: {g.user.matricula}
#         id_usuario: {g.user.id_usuario}
#         nome inteiro: {g.user.nome}
#
#         --------------------------------------
#         HISTÓRICO DA CONVERSA:
#         --------------------------------------
#         Talvez esta não seja a primeira conversa com o usuário, SEMPRE utilize esse histórico de conversa com ele para entender o contexto:
#         {json.dumps(hist, ensure_ascii=False, indent=2)}
#
#         -----------------------------------------
#         AGORA CLASSIFIQUE O TEXTO:
#         -----------------------------------------
#
#         '''
#         response = self._chat_completion([
#             {"role": "system", "content": system_prompt},
#             {"role": "user", "content": user_message}
#         ])
#         return json.loads(response)
#
#     # ---------------------------
#     # 2. Gerar SQL
#     # ---------------------------
#     def generate_sql(self, question, schema, hist):
#         system_prompt = f"""
#         Você é o Especialista Oficial de SQL do Atlas (sistema da EDP).
#
#         Seu papel é transformar perguntas do usuário em SQL válido, seguro e otimizado.
#         Nunca responda nada além de JSON. Nunca explique fora do JSON.
#
#         O Atlas é o sistema de gerenciamento de estudos do Planejamento da Expansão da EDP.
#         Um estudo pode ser chamado de processo, carta, documento.
#         Um estudo pode ter várias alternativas.
#
#         --------------------------------------
#         REGRAS GERAIS (OBRIGATÓRIAS)
#         --------------------------------------
#         1. Gere SEMPRE um JSON com os campos:
#            {{
#              "sql": "<string SQL>",
#              "comment": "<NÃO explique o que você fez, responda em primeira pessoa, diretamente, tentando criar um entrosamento com o usuário>"
#            }}
#
#         2. A query SQL DEVE ser compatível com SQL Server.
#
#         3. É PROIBIDO executar:
#            - DELETE
#            - UPDATE
#            - INSERT
#            - DROP
#            - TRUNCATE
#            - ALTER
#            - CREATE TABLE
#            Qualquer comando destrutivo.
#            Caso o usuário peça isso, retorne no campo "sql" um SELECT seguro
#            e explique no campo "comment" que operações destrutivas são proibidas.
#
#         4. Nunca invente colunas, tabelas ou relacionamentos.
#            Utilize SOMENTE o schema oficial abaixo.
#
#         5. No comentário NUNCA cite a query, ou que você fez uma query, sempre seja sucinto na resposta respondendo diretamente que você atendeu o que o usuário pediu.
#
#         --------------------------------------
#         SCHEMA OFICIAL DO ATLAS
#         --------------------------------------
#         {schema}
#
#         --------------------------------------
#         EXPLICAÇÃO SOBRE O SCHEMA (BANCO DE DADOS)
#         --------------------------------------
#         - A tabela Estudo possui os registros principais.
#         - A tabela Alternativas possui as alternativas de cada Estudo, a coluna custo_modular possui o custo da alternativa
#         - Ignore a tabela Obras e Kits
#         - Sempre dê preferencia para o responsável da região, e não por quem foi criado.
#         - A tabela resp_regioes possui o id_usuario do Engenheiro responsável por aquela região.
#         - A tabela tipo_solicitacao possui a classificação do Estudo, se o usuário pedir alguma query sobre Orçamento de Conexão ou Estimado, Plano de Obras, DAL ele está falando de viabilidade.
#         - Caso seja de Carga, MMGD (também chamado de Geração, mas utilize MMGD), AutoProdutor, Produtor Independente, Anteprojeto, ANEEL, ONS ele esta falando da coluna analise, se falar sobre Ligação Nova, Aumento ou redução de Demanda, Linhas, redes e subestações esta falando da coluna pedido.
#         - SEMPRE deixe o nome das colunas que irá retornar ao usuário legível e compreensível, evite underlines e abreviações.
#         - Para perguntas com datas dê preferência para utilizar data_registro. Utilize outra caso o usuário peça diretamente.
#         - Nunca use colunas do tipo TEXT ou NTEXT em GROUP BY ou ORDER BY.
#         - Se precisar agrupar ou ordenar por essas colunas, faça CAST para NVARCHAR(MAX).
#         - Exemplos:
#           CAST(coluna AS NVARCHAR(MAX))
#
#         --------------------------------------
#         REGRAS DE JOINS
#         --------------------------------------
#         Sempre use:
#         - atlas.estudos como 'e'
#         - atlas.alternativas como 'a'
#         - atlas.status_tipo como 'st'
#         - atlas.resp_regioes como 'rr'
#         - atlas.usuarios como 'usr'
#         - atlas.tipo_solicitacao como 'ts'
#
#         Exemplos:
#         JOIN atlas.estudos e ON e.id_estudo = a.id_estudo
#         JOIN atlas.tipo_solicitacao ts ON ts.id_tipo_solicitacao = e.id_tipo_solicitacao
#         JOIN atlas.status_tipo st ON st.id_status = a.id_status
#         JOIN atlas.resp_regioes rr ON rr.id_resp_regiao = e.id_resp_regiao
#         join atlas.usuarios usr on usr.id_usuario = rr.id_usuario
#
#         --------------------------------------
#         QUANDO O USUÁRIO PEDIR GRÁFICO
#         --------------------------------------
#         Apenas e SEMPRE gere o SQL normal. No comentário diga que você irá criar o gráfico conforme pedido.
#         ATENÇÃO - TODO SQL para gráfico só pode ter duas colunas, onde a última coluna são os dados numéricos.
#         --------------------------------------
#         FORMATO FINAL (OBRIGATÓRIO)
#         --------------------------------------
#         Retorne APENAS um JSON puro:
#         {{
#           "sql": "...",
#           "comment": "..."
#         }}
#         Sem markdown. Sem explicações fora do JSON.
#
#         --------------------------------------
#         DADOS DO USUÁRIO:
#         --------------------------------------
#         Você esta falando com o {g.user.first_name}
#         matrícula: {g.user.matricula}
#         id_usuario: {g.user.id_usuario}
#         nome inteiro: {g.user.nome}
#
#         --------------------------------------
#         HISTÓRICO DA CONVERSA:
#         --------------------------------------
#         Talvez esta não seja a primeira conversa com o usuário, utilize esse histórico de conversa com ele:
#         {json.dumps(hist, ensure_ascii=False, indent=2)}
#
#          --------------------------------------
#         O USUÁRIO PERGUNTOU:
#         --------------------------------------
#         """
#
#         response = self._chat_completion([
#             {"role": "system", "content": system_prompt},
#             {"role": "user", "content": question}
#         ])
#         # Remove bordas de markdown, se houver
#         clean = response.strip()
#         clean = clean.replace("```json", "").replace("```", "").strip()
#
#         # Se começar com "{\n" ou "{\r\n", o LLM devolveu JSON-STRING
#         if clean.startswith("{\\n") or "\\n" in clean:
#             # O modelo devolveu JSON com \n escapado. Transformamos só isso.
#             clean = clean.replace("\\n", "\n").replace("\\t", "\t")
#
#         # Agora corrige quebras de linha reais dentro das strings
#         clean = re.sub(r'(?<!\\)\n', r' ', clean)
#         return json.loads(clean)
#
#
#     def parse_pdf(self, pdf_text):
#         system_prompt = f"""
#                 Você é um extrator de documentos DDPE da EDP. O usuário esta tentando cadastrar automaticamente um novo estudo.
#                 Extraia as informações do texto e devolva SOMENTE um JSON válido no seguinte formato abaixo:
#
#                 {{
#                     "nome_projeto": ,
#                     "descricao": "",
#                     "protocolo": "",
#                     "classe": "Esta será 1 (para AT) ou 2 (para MT) dependendo do nível de tensão do cliente, abaixo de 69kV é MT.",
#                     "instalacao": "Nos formulários é representado como UC (Unidade Consumidora) do cliente)
#                     "cnpj": "",
#                     "empresa_nome": "",
#                     "dem_carga_solicit_fp": "Demanda de carga solicitada pelo cliente no horário Fora Ponta",
#                     "dem_carga_solicit_p": "Demanda de carga solicitada pelo cliente no horário de Ponta",
#                     "dem_ger_solicit_fp": "Demanda de geração solicitada pelo cliente no horário Fora Ponta",
#                     "dem_ger_solicit_p": "Demanda de geração solicitada pelo cliente no horário Ponta (Fotovoltaica não gera em horário de Ponta, deve ser 0.)",
#                     "edp": "Deve ser 1 para SP e 2 para ES dependendo da localização do cliente.",
#                     "municipio": "",
#                     "tipo_viab": "decida entre 'Orçamento de Conexão' ou 'Orçamento Estimado'. Atenção: Orçamento Estimado pode aparecer como 'consulta de acesso' no formulário",
#                     "tipo_analise": "decida entre 'Carga', 'MMGD', 'Autoprodutor', 'Produtor Independente', 'BESS', 'Carga e Autoprodutor' ou 'Carga e MMGD'",
#                     "tipo_pedido": "decida entre 'Aumento de Demanda', 'Ligação Nova', 'Decréscimo de Demanda' ou 'Reserva de Capacidade'",
#                     "tipo_geracao": "decida entre 'Fotovoltaica', 'Hidrelétrica', 'Termoelétrica' ou 'Eólica'",
#                     "latitude_cliente": "",
#                     "longitude_cliente": "",
#                     "data_abertura_cliente": "Considere a data de assinatura do formulário",
#                     "data_vencimento_cliente": "Some 30 dias à data de abertura",
#                     "data_desejada_cliente": "Verifique se há em algum arquivo a data final que o cliente gostaria de estar conectado",
#                     "observacao": ""
#                 }}
#
#                 Se não encontrar algum campo, deixe vazio.
#                 --------------------------------------
#                 FORMATO FINAL (OBRIGATÓRIO)
#                 --------------------------------------
#                 Retorne APENAS um JSON puro:
#                 Sem markdown. Sem explicações fora do JSON.
#
#                 --------------------------------------
#                 DADOS DO USUÁRIO:
#                 --------------------------------------
#                 Você esta falando com o {g.user.first_name}
#                 matrícula: {g.user.matricula}
#                 id_usuario: {g.user.id_usuario}
#                 nome inteiro: {g.user.nome}
#
#
#                  --------------------------------------
#                 O TEXTO NO ARQUIVO É:
#                 --------------------------------------
#                 """
#
#         response = self._chat_completion([
#             {"role": "system", "content": system_prompt},
#             {"role": "user", "content": pdf_text}
#         ])
#         # Remove bordas de markdown, se houver
#         clean = response.strip()
#         clean = clean.replace("```json", "").replace("```", "").strip()
#
#         # Se começar com "{\n" ou "{\r\n", o LLM devolveu JSON-STRING
#         if clean.startswith("{\\n") or "\\n" in clean:
#             # O modelo devolveu JSON com \n escapado. Transformamos só isso.
#             clean = clean.replace("\\n", "\n").replace("\\t", "\t")
#
#         # Agora corrige quebras de linha reais dentro das strings
#         clean = re.sub(r'(?<!\\)\n', r' ', clean)
#         return json.loads(clean)
#
#
#     # ---------------------------
#     # 3. Chamar LLM
#     # ---------------------------
#     def _chat_completion(self, messages, max_tokens=4096, max_attempts=3):
#         for attempt in range(max_attempts):
#             try:
#                 print(f"LLM: tentativa {attempt}")
#                 chat_completion = self.client.chat.completions.create(
#                     messages=messages,
#                     model=self.model,
#                     max_tokens=max_tokens,
#                     timeout=60
#                 )
#
#                 content = chat_completion.choices[0].message.content
#                 content = content.replace("```json", "").replace("```", "").strip()
#                 return content
#
#             except Exception as e:
#                 print(f"LLM: {e}")
#                 time.sleep(1)
#
#         raise Exception("Falha ao chamar LLM")
#
#     # Mantido por compatibilidade com chamadas externas que passam {"messages": [...]}
#     def _call_llm(self, body, max_attempts=3):
#         return self._chat_completion(body["messages"], max_attempts=max_attempts)
#
#     # ---------------------------
#     # 4. Executar query SQL
#     # ---------------------------
#     def run_sql(self, sql):
#         result = db.session.execute(text(sql))
#         df = pd.DataFrame(result.mappings().all())
#         return df
#
#     # ---------------------------
#     # 5. Gerar gráfico
#     # ---------------------------
#     def create_plot(self, df, x, y, chat_id):
#         fig_id = f"chart_{uuid.uuid4().hex[:8]}.png"
#         base_dir = os.path.abspath(os.path.dirname(__file__))
#         path = os.path.join(base_dir, 'chats', g.user.matricula, chat_id, "charts")
#         os.makedirs(path, exist_ok=True)
#         filepath = os.path.join(path, fig_id)
#
#         plt.figure(figsize=(8, 5))
#         plt.bar(df[x], df[y])
#         plt.tight_layout()
#         plt.savefig(filepath)
#         plt.close()
#
#         return fig_id


"""
AtlasAgent — endpoint remoto (Claude Opus via gateway OpenAI-compatível da EDP).

Melhorias em relação à versão anterior
--------------------------------------
1. System prompts estáticos. g.user e histórico saem do system e viram
   mensagens. Reduz tokens cobrados por chamada, mantém o prefixo estável
   para cache do gateway e evita que o nome do usuário vaze para dentro
   de campos extraídos.

2. Histórico como turnos reais e truncado. O json.dumps(hist) anterior
   crescia sem teto e degradava cada mensagem da conversa.

3. Saída estruturada: tenta response_format com json_schema; se o gateway
   não suportar, cai para schema-como-instrução, uma única vez (a
   capacidade fica memorizada).

4. Extração de JSON por casamento de chaves, não por regex. O
   re.sub(r'(?<!\\)\n', ' ') anterior passava um rolo de compressor por
   dentro das strings — inaceitável agora que descricao e observacao
   carregam texto livre.

5. Enums validados em Python. Sem gramática, o modelo pode devolver
   "Orçamento estimado" ou "Ligação nova"; a coerção resolve.

6. classe / edp / data_vencimento calculados em Python.

7. Guarda de SQL determinística, independente do que o prompt pede.

8. Timeouts por tarefa. 60s era curto para extrair 3 páginas com resumo.
"""

import json
import os
import re
import time
import uuid
from datetime import datetime, timedelta

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from flask import g
from openai import OpenAI
from sqlalchemy import text

from app.models import db


DEFAULT_MODEL = os.getenv("LLM_MODEL", "system.ai.claude-opus-4-8")

# Os modelos de raciocínio removeram os parâmetros de amostragem: mandar
# temperature devolve 400 ("Model ... does not support the temperature
# parameter"). Nessa família já saímos sem o parâmetro; nos demais modelos
# temperature=0 continua valendo, pela resposta determinística.
_MODELOS_SEM_AMOSTRAGEM = re.compile(
    r"claude-(?:opus-(?:4-7|4-8|5)|sonnet-5|fable-5|mythos-5)", re.IGNORECASE)

_SEM_TEMPERATURE = re.compile(
    r"temperature[^.]*(?:not support|unsupported|n[aã]o suporta)"
    r"|(?:not support|unsupported|n[aã]o suporta)[^.]*temperature",
    re.IGNORECASE)

TASKS = {
    "intent": {"timeout": 60,  "max_tokens": 300},
    "sql":    {"timeout": 120, "max_tokens": 2000},
    "ddpe":   {"timeout": 240, "max_tokens": 4096},
}


# =====================================================================
# ENUMS E SCHEMAS
# =====================================================================

INTENTS = [
    "general_question", "atlas_system_question", "sql_query", "sql_table",
    "sql_plot", "sql_count_summary", "tech_help", "pdf_query",
    "document_question", "ambiguous", "blocked",
]

TIPO_VIAB = ["Orçamento de Conexão", "Orçamento Estimado"]
TIPO_ANALISE = ["Carga", "MMGD", "Autoprodutor", "Produtor Independente",
                "BESS", "Carga e Autoprodutor", "Carga e MMGD"]
TIPO_PEDIDO = ["Aumento de Demanda", "Ligação Nova",
               "Decréscimo de Demanda", "Reserva de Capacidade"]
TIPO_GERACAO = ["Fotovoltaica", "Hidrelétrica", "Termoelétrica", "Eólica"]

# reason antes de intent: a justificativa gerada primeiro condiciona a escolha.
INTENT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "reason": {"type": "string", "description": "Uma frase curta justificando."},
        "intent": {"type": "string", "enum": INTENTS},
        "confidence": {"type": "number"},
    },
    "required": ["reason", "intent", "confidence"],
}

SQL_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "sql": {"type": "string",
                "description": "Uma única instrução SELECT para SQL Server."},
        "comment": {"type": "string",
                    "description": "Resposta curta em primeira pessoa. Não cite a "
                                   "query nem mencione consulta ao banco."},
    },
    "required": ["sql", "comment"],
}

# descricao e observacao POR ÚLTIMO: geração é autorregressiva, então o resumo
# sai condicionado a todos os campos que o modelo acabou de extrair.
DDPE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "nome_projeto": {"type": "string",
            "description": "Nome ou título do empreendimento como no formulário."},
        "protocolo": {"type": "string", "description": "Vazio se ausente."},
        "instalacao": {"type": "string",
            "description": "Código da UC (Unidade Consumidora) do cliente."},
        "cnpj": {"type": "string", "description": "Apenas dígitos, sem pontuação."},
        "empresa_nome": {"type": "string"},
        "municipio": {"type": "string", "description": "Sem a sigla do estado."},
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
        "tipo_geracao": {"type": "string", "enum": TIPO_GERACAO + [""],
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
# SYSTEM PROMPTS — ESTÁTICOS. Não interpole nada aqui.
# =====================================================================

SYS_INTENT = """Você é o classificador de intenção do Atlas, sistema de \
gerenciamento de estudos do Planejamento da Expansão da EDP. Um estudo também \
pode ser chamado de processo, anteprojeto, carta ou documento, e pode ter \
várias alternativas.

Classifique a última mensagem do usuário em uma destas intenções:

general_question       — assunto geral: história, ciência, conceitos.
atlas_system_question  — obras, estudos, alternativas, transformadores,
                         circuitos, perdas, BDGD. Não pede SQL.
sql_query              — pede dados do banco que não sejam tabela nem lista,
                         ou análise que envolva agregação.
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

Classifique apenas pelo texto. Nunca invente informação.
Use confidence realista entre 0.50 e 1.00."""


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
# PARSING DE JSON — robusto
# =====================================================================

def _fatiar_json(texto):
    """Recorta o primeiro objeto JSON completo, casando chaves e respeitando
    strings e escapes. Substitui o regex que corrompia texto livre."""
    ini = texto.find("{")
    if ini == -1:
        raise ValueError("Nenhum objeto JSON encontrado na resposta.")

    nivel, dentro_str, escapado = 0, False, False
    for i, ch in enumerate(texto[ini:], start=ini):
        if dentro_str:
            if escapado:
                escapado = False
            elif ch == "\\":
                escapado = True
            elif ch == '"':
                dentro_str = False
            continue
        if ch == '"':
            dentro_str = True
        elif ch == "{":
            nivel += 1
        elif ch == "}":
            nivel -= 1
            if nivel == 0:
                return texto[ini:i + 1]
    raise ValueError("Objeto JSON truncado — provável estouro de max_tokens.")


def carregar_json(bruto):
    texto = bruto.replace("```json", "").replace("```", "").strip()
    bloco = _fatiar_json(texto)
    try:
        return json.loads(bloco)
    except json.JSONDecodeError:
        # Único reparo tolerado: quebras de linha cruas dentro de strings,
        # que são inválidas em JSON. Aplicado só quando o parse falha.
        reparado = re.sub(r'(?<!\\)[\r\n]+', r'\\n', bloco)
        return json.loads(reparado)


# =====================================================================
# VALIDAÇÃO
# =====================================================================

_SQL_PROIBIDO = re.compile(
    r"\b(delete|update|insert|drop|truncate|alter|create|merge|grant|revoke|"
    r"exec|execute|sp_\w+|xp_\w+|into\s+\w+)\b", re.IGNORECASE)


class SqlInseguro(Exception):
    pass


def validar_sql(sql):
    s = (sql or "").strip().rstrip(";").strip()
    if not s:
        raise SqlInseguro("SQL vazio.")
    if ";" in s:
        raise SqlInseguro("Múltiplas instruções não são permitidas.")
    if not re.match(r"^\s*(select|with)\b", s, re.IGNORECASE):
        raise SqlInseguro("Apenas SELECT é permitido.")
    if _SQL_PROIBIDO.search(s):
        raise SqlInseguro("Comando destrutivo detectado.")
    return s


def _coagir_enum(valor, permitidos, padrao=""):
    """Sem gramática, o modelo devolve variações de caixa e acento."""
    if not valor:
        return padrao
    alvo = str(valor).strip().casefold()
    for p in permitidos:
        if p.casefold() == alvo:
            return p
    for p in permitidos:                      # tolera prefixo/substring
        if alvo in p.casefold() or p.casefold() in alvo:
            return p
    return padrao


# =====================================================================
# AGENTE
# =====================================================================

class AtlasAgent:

    def __init__(self, llm_url, llm_token, model=None):
        self.model = model or DEFAULT_MODEL
        self.client = OpenAI(api_key=llm_token, base_url=llm_url)
        # None = ainda não testado; True/False = capacidade do gateway
        self._suporta_json_schema = None
        self._suporta_temperature = (
            False if _MODELOS_SEM_AMOSTRAGEM.search(self.model) else None)

    # ---------- chamada unificada ----------

    def _chat_json(self, task, system, messages, schema, nome_schema,
                   max_attempts=3):
        cfg = TASKS[task]
        erro = None

        for tentativa in range(max_attempts):
            try:
                bruto = self._completar(cfg, system, messages, schema, nome_schema)
                return carregar_json(bruto)
            except Exception as e:
                erro = e
                print(f"[LLM:{task}] tentativa {tentativa + 1}/{max_attempts}: {e}")
                time.sleep(2 ** tentativa)

        raise RuntimeError(f"Falha ao chamar LLM na tarefa '{task}': {erro}")

    def _criar(self, **kwargs):
        """Uma chamada ao gateway, repetida sem temperature se ele recusar.

        O tratamento fica aqui, antes da detecção de json_schema: um 400 de
        temperature chegando lá desligaria o json_schema por engano.
        """
        try:
            return self.client.chat.completions.create(**kwargs)
        except Exception as e:
            if "temperature" not in kwargs or not _SEM_TEMPERATURE.search(str(e)):
                raise

            print(f"[LLM] {self.model} não aceita temperature; repetindo sem ela")
            self._suporta_temperature = False
            kwargs.pop("temperature")
            return self.client.chat.completions.create(**kwargs)

    def _completar(self, cfg, system, messages, schema, nome_schema):
        full = [{"role": "system", "content": system}] + messages
        kwargs = dict(model=self.model, max_tokens=cfg["max_tokens"],
                      timeout=cfg["timeout"])

        if self._suporta_temperature is not False:
            kwargs["temperature"] = 0

        if self._suporta_json_schema is not False:
            try:
                r = self._criar(
                    messages=full,
                    response_format={
                        "type": "json_schema",
                        "json_schema": {"name": nome_schema, "strict": True,
                                        "schema": schema},
                    },
                    **kwargs)
                self._suporta_json_schema = True
                return r.choices[0].message.content
            except Exception as e:
                if self._suporta_json_schema is None:
                    print(f"[LLM] gateway sem json_schema, usando instrução: {e}")
                    self._suporta_json_schema = False
                else:
                    raise

        # Fallback: schema como instrução no fim do system
        full[0] = {"role": "system", "content": full[0]["content"] + f"""

--------------------------------------
FORMATO DA RESPOSTA (OBRIGATÓRIO)
--------------------------------------
Responda APENAS com um objeto JSON puro, sem markdown e sem texto fora dele,
aderente a este JSON Schema (respeite a ORDEM das chaves):

{json.dumps(schema, ensure_ascii=False, indent=2)}"""}

        r = self._criar(messages=full, **kwargs)
        return r.choices[0].message.content

    # ---------- contexto dinâmico ----------

    @staticmethod
    def _contexto_usuario():
        return {"role": "user",
                "content": (f"[contexto] Usuário: {g.user.nome} "
                            f"({g.user.first_name}), matrícula {g.user.matricula}, "
                            f"id_usuario {g.user.id_usuario}.")}

    @staticmethod
    def _historico(hist, limite=8, corte=2000):
        """Turnos reais, truncados. O json.dumps(hist) anterior crescia sem
        teto e encarecia cada mensagem da conversa."""
        turnos = []
        for h in (hist or [])[-limite:]:
            role = h.get("role") or ("user" if h.get("user") else "assistant")
            conteudo = h.get("content") or h.get("user") or h.get("assistant") or ""
            if conteudo:
                turnos.append({"role": role, "content": str(conteudo)[:corte]})
        return turnos

    # ---------- 1. intenção ----------

    def classify_intent(self, user_message, hist):
        messages = ([self._contexto_usuario()]
                    + self._historico(hist)
                    + [{"role": "user", "content": user_message}])

        out = self._chat_json("intent", SYS_INTENT, messages,
                              INTENT_SCHEMA, "intent")
        out["intent"] = _coagir_enum(out.get("intent"), INTENTS, "ambiguous")
        try:
            out["confidence"] = min(1.0, max(0.0, float(out.get("confidence", 0.5))))
        except (TypeError, ValueError):
            out["confidence"] = 0.5
        return out

    # ---------- 2. SQL ----------

    def generate_sql(self, question, schema, hist):
        messages = ([self._contexto_usuario()]
                    + [{"role": "user", "content": f"[schema do banco]\n{schema}"}]
                    + self._historico(hist)
                    + [{"role": "user", "content": question}])

        out = self._chat_json("sql", SYS_SQL, messages, SQL_SCHEMA, "sql")
        out["sql"] = validar_sql(out.get("sql"))    # levanta SqlInseguro
        return out

    # ---------- 3. DDPE ----------

    def parse_ddpe(self, pdf_text):
        # Sem contexto de usuário: em extração ele só adiciona ruído e cria
        # risco do nome do engenheiro aparecer dentro de observacao.
        messages = [{"role": "user", "content": pdf_text}]
        d = self._chat_json("ddpe", SYS_DDPE, messages, DDPE_SCHEMA, "ddpe")
        return self._pos_processar_ddpe(d)

    parse_pdf = parse_ddpe      # alias de compatibilidade

    @staticmethod
    def _pos_processar_ddpe(d):
        """Tudo que é determinístico sai do LLM e é decidido aqui."""
        d["tipo_viab"] = _coagir_enum(d.get("tipo_viab"), TIPO_VIAB)
        d["tipo_analise"] = _coagir_enum(d.get("tipo_analise"), TIPO_ANALISE)
        d["tipo_pedido"] = _coagir_enum(d.get("tipo_pedido"), TIPO_PEDIDO)
        d["tipo_geracao"] = _coagir_enum(d.get("tipo_geracao"), TIPO_GERACAO)

        try:
            tensao = float(d.get("tensao_kv") or 0)
        except (TypeError, ValueError):
            tensao = 0.0
        d["tensao_kv"] = tensao
        d["classe"] = 2 if 0 < tensao < 69 else 1          # 1=AT, 2=MT

        uf = UF_POR_MUNICIPIO.get((d.get("municipio") or "").strip())
        d["edp"] = {"SP": 1, "ES": 2}.get(uf)              # None se desconhecido

        d["data_vencimento_cliente"] = ""
        abertura = d.get("data_abertura_cliente") or ""
        if abertura:
            try:
                base = datetime.strptime(abertura, "%Y-%m-%d")
                d["data_vencimento_cliente"] = (base + timedelta(days=30)
                                                ).strftime("%Y-%m-%d")
            except ValueError:
                pass

        # marcação para a UI: gerados por IA, não verificáveis contra o formulário
        d["_campos_gerados"] = ["descricao", "observacao"]
        return d

    # ---------- 4. execução ----------

    def run_sql(self, sql):
        sql = validar_sql(sql)      # segunda barreira
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