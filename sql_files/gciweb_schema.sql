-- =====================================================================
-- GCIWeb / ATLAS - Schema SQL Server
-- Sincronizado com app/models.py (SQLAlchemy) e sql_files/views.sql
-- =====================================================================
-- Schema otimizado para SQL SERVER com BIGINT IDENTITY
-- Todos os tipos de dados sao nativos do SQL Server 2016+
-- Sistema centralizado, BIGINT e mais adequado que UNIQUEIDENTIFIER
-- =====================================================================

CREATE SCHEMA atlas;
GO

-- =====================================================================
-- TABELAS DE DOMINIO / APOIO
-- =====================================================================

CREATE TABLE "atlas"."edp"(
    "id_edp" BIGINT IDENTITY(1,1) NOT NULL,
    "empresa" VARCHAR(2) NOT NULL
);
ALTER TABLE "atlas"."edp" ADD CONSTRAINT "atlas_edp_id_edp_primary" PRIMARY KEY("id_edp");
GO

-- Tensoes de atendimento disponiveis (models.Tensao)
CREATE TABLE "atlas"."tensao"(
    "id_tensao" BIGINT IDENTITY(1,1) NOT NULL,
    "tensao" VARCHAR(2) NOT NULL
);
ALTER TABLE "atlas"."tensao" ADD CONSTRAINT "atlas_tensao_id_tensao_primary" PRIMARY KEY("id_tensao");
GO

CREATE TABLE "atlas"."FATOR_K"(
    "id_k" BIGINT IDENTITY(1,1) NOT NULL,
    "k" DECIMAL(6,2) NULL,
    "kg" DECIMAL(6,2) NULL,
    "subgrupo_tarif" VARCHAR(3) NOT NULL,
    "data_ref" DATE NULL,
    "id_edp" BIGINT NOT NULL
);
ALTER TABLE "atlas"."FATOR_K" ADD CONSTRAINT "atlas_fator_k_id_primary" PRIMARY KEY("id_k");
GO

CREATE TABLE "atlas"."status_tipos"(
    "id_status_tipo" BIGINT IDENTITY(1,1) NOT NULL,
    "status" VARCHAR(100) NOT NULL,
    "descricao" TEXT NULL,
    "ativo" BIT NOT NULL DEFAULT 1
);
ALTER TABLE "atlas"."status_tipos" ADD CONSTRAINT "atlas_status_tipos_id_primary" PRIMARY KEY("id_status_tipo");
GO

CREATE TABLE "atlas"."kits"(
    "id_kit" BIGINT IDENTITY(1,1) NOT NULL,
    "kit" VARCHAR(255) NOT NULL,
    "tipo" VARCHAR(100) NOT NULL,
    "descricao" VARCHAR(500) NOT NULL,
    "valor_unit" DECIMAL(15,2) NOT NULL, -- Melhor para valores monetarios
    "ano_ref" INT NOT NULL,
    "ativo" BIT NOT NULL DEFAULT 1 -- Campo para controle
);
ALTER TABLE "atlas"."kits" ADD CONSTRAINT "atlas_kits_id_kit_primary" PRIMARY KEY("id_kit");
GO

-- Substitui tipo_analise, tipo_pedido e tipo_viabilidade em uma unica tabela.
CREATE TABLE "atlas"."tipo_solicitacao"(
    "id_tipo_solicitacao" BIGINT IDENTITY(1,1) NOT NULL,
    "viabilidade" VARCHAR(255) NOT NULL,
    "analise" VARCHAR(255) NOT NULL,
    "pedido" VARCHAR(255) NOT NULL,
    "viabilidade_abrev" VARCHAR(255) NULL,
    "analise_abrev" VARCHAR(255) NULL,
    "pedido_abrev" VARCHAR(255) NULL
);
ALTER TABLE "atlas"."tipo_solicitacao" ADD CONSTRAINT "atlas_tipo_solicitacao_id_tipo_solicitacao_primary" PRIMARY KEY("id_tipo_solicitacao");
ALTER TABLE "atlas"."tipo_solicitacao" ADD CONSTRAINT "UQ_tipo_solicitacao_combinacao" UNIQUE("viabilidade","analise","pedido");
GO

CREATE TABLE "atlas"."doc_padronizados" (
    "id_doc_padronizado" BIGINT IDENTITY(1,1) NOT NULL,
    "nome_doc" VARCHAR(255) NOT NULL,
    "caminho_doc" VARCHAR(500) NOT NULL,
    "tipo_doc" VARCHAR(100) NOT NULL,
    "data_criacao" DATETIME NOT NULL,
    "data_atualizacao" DATETIME NULL,
    "versao" INT NULL,
    "fluxo_reverso" BIT NULL,
    "id_tipo_solicitacao" BIGINT NOT NULL
);
ALTER TABLE "atlas"."doc_padronizados" ADD CONSTRAINT "atlas_doc_padronizados_id_primary" PRIMARY KEY("id_doc_padronizado");
GO

-- =====================================================================
-- USUARIOS E RESPONSABILIDADES
-- =====================================================================

CREATE TABLE "atlas"."usuarios"(
    "id_usuario" BIGINT IDENTITY(1,1) NOT NULL,
    "matricula" VARCHAR(255) NOT NULL UNIQUE,
    "nome" TEXT NOT NULL,
    "email" TEXT NULL,
    "admin" BIT NOT NULL,
    "visualizar" BIT NOT NULL,
    "criar" BIT NOT NULL,
    "editar" BIT NOT NULL,
    "deletar" BIT NOT NULL,
    "aprovar" BIT NOT NULL DEFAULT 0,
    "bloqueado" BIT NOT NULL DEFAULT 0,
    "id_edp" BIGINT NOT NULL DEFAULT 1
);
ALTER TABLE "atlas"."usuarios" ADD CONSTRAINT "atlas_usuarios_id_usuario_primary" PRIMARY KEY("id_usuario");
GO

CREATE TABLE "atlas"."resp_regioes"(
    "id_resp_regiao" BIGINT IDENTITY(1,1) NOT NULL,
    "id_regional" BIGINT NOT NULL,
    "id_usuario" BIGINT NOT NULL,
    "ano_ref" INT NOT NULL
);
ALTER TABLE "atlas"."resp_regioes" ADD CONSTRAINT "atlas_resp_regioes_id_resp_regiao_primary" PRIMARY KEY("id_resp_regiao");
GO

-- =====================================================================
-- ESTRUTURA GEOGRAFICA / ELETRICA
-- =====================================================================

CREATE TABLE "atlas"."regionais"(
    "id_regional" BIGINT IDENTITY(1,1) NOT NULL,
    "regional" VARCHAR(255) NOT NULL,
    "id_edp" BIGINT NOT NULL
);
ALTER TABLE "atlas"."regionais" ADD CONSTRAINT "atlas_regionais_id_regional_primary" PRIMARY KEY("id_regional");
GO

CREATE TABLE "atlas"."municipios"(
    "id_municipio" BIGINT IDENTITY(1,1) NOT NULL,
    "municipio" VARCHAR(255) NOT NULL,
    "id_edp" BIGINT NOT NULL,
    "id_regional" BIGINT NULL
);
ALTER TABLE "atlas"."municipios" ADD CONSTRAINT "atlas_municipios_id_municipio_primary" PRIMARY KEY("id_municipio");
GO

CREATE TABLE "atlas"."subestacoes"(
    "id_subestacao" BIGINT IDENTITY(1,1) NOT NULL,
    "nome" VARCHAR(255) NOT NULL,
    "sigla" VARCHAR(10) NOT NULL,
    "lat" DECIMAL(10,2) NULL,
    "long" DECIMAL(10,2) NULL,
    "fronteira" BIT NOT NULL DEFAULT 0,
    "id_municipio" BIGINT NOT NULL,
    "id_edp" BIGINT NOT NULL
);
ALTER TABLE "atlas"."subestacoes" ADD CONSTRAINT "atlas_subestacoes_id_subestacao_primary" PRIMARY KEY("id_subestacao");
GO

CREATE TABLE "atlas"."circuitos"(
    "id_circuito" BIGINT IDENTITY(1,1) NOT NULL,
    "circuito" VARCHAR(255) NOT NULL,
    "id_subestacao" BIGINT NULL,
    "id_edp" BIGINT NOT NULL,
    "tensao" VARCHAR(20) NOT NULL
);
ALTER TABLE "atlas"."circuitos" ADD CONSTRAINT "atlas_circuitos_id_circuito_primary" PRIMARY KEY("id_circuito");
GO

-- =====================================================================
-- CLIENTES / EMPRESAS
-- =====================================================================

CREATE TABLE "atlas"."empresas"(
    "id_empresa" BIGINT IDENTITY(1,1) NOT NULL,
    "nome_empresa" VARCHAR(255) NOT NULL,
    "cnpj" VARCHAR(14) NOT NULL UNIQUE, -- Tamanho fixo do CNPJ
    "abertura" DATE NULL,
    "situacao" VARCHAR(255) NULL,
    "tipo" VARCHAR(255) NULL,
    "porte" VARCHAR(255) NULL,
    "natureza_juridica" VARCHAR(255) NULL,
    "logradouro" VARCHAR(255) NULL,
    "numero" VARCHAR(10) NULL,
    "complemento" VARCHAR(255) NULL,
    "municipio" VARCHAR(255) NULL,
    "bairro" VARCHAR(255) NULL,
    "uf" VARCHAR(2) NULL,
    "cep" VARCHAR(8) NULL,
    "email" VARCHAR(255) NULL,
    "telefone" VARCHAR(20) NULL,
    "data_situacao" DATE NULL,
    "ultima_atualizacao" DATETIME NULL,
    "status" VARCHAR(255) NULL,
    "fantasia" VARCHAR(255) NULL,
    "efr" VARCHAR(255) NULL,
    "motivo_situacao" VARCHAR(255) NULL,
    "situacao_especial" VARCHAR(255) NULL,
    "data_situacao_especial" DATE NULL
);
ALTER TABLE "atlas"."empresas" ADD CONSTRAINT "atlas_empresas_id_empresa_primary" PRIMARY KEY("id_empresa");
GO

CREATE TABLE "atlas"."socios"(
    "id_socios" BIGINT IDENTITY(1,1) NOT NULL,
    "nome" VARCHAR(255) NOT NULL,
    "cargo" VARCHAR(255) NULL,
    "id_empresa" BIGINT NOT NULL
);
ALTER TABLE "atlas"."socios" ADD CONSTRAINT "atlas_socios_id_socios_primary" PRIMARY KEY("id_socios");
GO

-- Base de instalacoes/clientes carregada a partir do sistema comercial (models.Instalacao).
-- Somente leitura pela aplicacao; a chave primaria e a propria INSTALACAO.
CREATE TABLE "atlas"."INSTALACOES"(
    "EMPRESA" VARCHAR(255) NULL,
    "INSTALACAO" VARCHAR(30) NOT NULL,
    "CNPJ" VARCHAR(20) NULL,
    "STATUS_INSTALACAO" VARCHAR(255) NULL,
    "DESCRICAO_STATUS" VARCHAR(255) NULL,
    "DESCRICAO_CLASSE" VARCHAR(255) NULL,
    "TARIFA" VARCHAR(255) NULL,
    "CARGA" DECIMAL(10,2) NULL,
    "TIPO_CLIENTE" VARCHAR(255) NULL,
    "NOME_PARCEIRO" VARCHAR(255) NULL,
    "CEP" VARCHAR(20) NULL
);
ALTER TABLE "atlas"."INSTALACOES" ADD CONSTRAINT "atlas_instalacoes_instalacao_primary" PRIMARY KEY("INSTALACAO");
GO

-- =====================================================================
-- ESTUDOS
-- =====================================================================

CREATE TABLE "atlas"."estudos"(
    "id_estudo" BIGINT IDENTITY(1,1) NOT NULL,
    "num_doc" VARCHAR(255) NOT NULL,
    "protocolo" BIGINT NULL,
    "nome_projeto" VARCHAR(255) NOT NULL,
    "descricao" TEXT NULL,
    "instalacao" BIGINT NULL,
    "n_alternativas" INT NOT NULL DEFAULT 0,
    -- Demandas atual e solicitada pelo cliente
    "dem_carga_atual_fp" DECIMAL(10,2) NOT NULL DEFAULT 0,
    "dem_carga_atual_p" DECIMAL(10,2) NOT NULL DEFAULT 0,
    "dem_carga_solicit_fp" DECIMAL(10,2) NOT NULL DEFAULT 0,
    "dem_carga_solicit_p" DECIMAL(10,2) NOT NULL DEFAULT 0,
    "dem_ger_atual_fp" DECIMAL(10,2) NOT NULL DEFAULT 0,
    "dem_ger_atual_p" DECIMAL(10,2) NOT NULL DEFAULT 0,
    "dem_ger_solicit_fp" DECIMAL(10,2) NOT NULL DEFAULT 0,
    "dem_ger_solicit_p" DECIMAL(10,2) NOT NULL DEFAULT 0,
    "latitude_cliente" DECIMAL(10,8) NULL, -- Melhor para coordenadas
    "longitude_cliente" DECIMAL(11,8) NULL, -- Melhor para coordenadas
    "observacao" TEXT NULL,
    "tipo_geracao" VARCHAR(255) NULL,
    "id_edp" BIGINT NOT NULL,
    "id_regional" BIGINT NOT NULL,
    "id_criado_por" BIGINT NOT NULL,
    "id_resp_alteracao" BIGINT NOT NULL,
    "id_resp_regiao" BIGINT NULL,
    "id_empresa" BIGINT NULL,
    "id_municipio" BIGINT NOT NULL,
    "id_tensao" BIGINT NOT NULL,
    "id_tipo_solicitacao" BIGINT NOT NULL,
    "data_registro" DATE NOT NULL DEFAULT GETDATE(),
    "data_abertura_cliente" DATE NOT NULL,
    "data_desejada_cliente" DATE NOT NULL,
    "data_vencimento_cliente" DATE NOT NULL,
    "data_prevista_conexao" DATE NOT NULL,
    "data_vencimento_ddpe" DATE NOT NULL,
    "data_alteracao" DATE NULL
);
ALTER TABLE "atlas"."estudos" ADD CONSTRAINT "atlas_estudos_id_estudo_primary" PRIMARY KEY("id_estudo");
CREATE INDEX "atlas_estudos_num_doc_index" ON "atlas"."estudos"("num_doc");
CREATE INDEX "atlas_estudos_data_registro_index" ON "atlas"."estudos"("data_registro");
GO

CREATE TABLE "atlas"."anexos"(
    "id_anexo" BIGINT IDENTITY(1,1) NOT NULL,
    "nome_arquivo" VARCHAR(255) NOT NULL,
    "endereco" VARCHAR(500) NOT NULL,
    "tamanho_arquivo" BIGINT NULL, -- Adicionado campo util
    "tipo_mime" VARCHAR(100) NULL, -- Adicionado campo util
    "data_upload" DATETIME NOT NULL DEFAULT GETDATE(),
    "id_estudo" BIGINT NOT NULL
);
ALTER TABLE "atlas"."anexos" ADD CONSTRAINT "atlas_anexos_id_anexo_primary" PRIMARY KEY("id_anexo");
GO

CREATE TABLE "atlas"."status_estudo"(
    "id_status" BIGINT IDENTITY(1,1) NOT NULL,
    "data" DATETIME NOT NULL DEFAULT GETDATE(),          -- data de cadastro do registro
    "data_ocorrencia" DATE NULL,                          -- data informada pelo usuario
    "id_status_tipo" BIGINT NOT NULL,
    "observacao" TEXT NULL,
    "id_estudo" BIGINT NOT NULL,
    "id_criado_por" BIGINT NOT NULL
);
ALTER TABLE "atlas"."status_estudo" ADD CONSTRAINT "atlas_status_estudo_id_status_primary" PRIMARY KEY("id_status");
GO

CREATE TABLE "atlas"."alternativas"(
    "id_alternativa" BIGINT IDENTITY(1,1) NOT NULL,
    "id_circuito" BIGINT NOT NULL,
    "descricao" TEXT NOT NULL,
    -- Demanda no ponto antes (ant) e depois (dep) da conexao, ponta (p) e fora de ponta (fp)
    "dem_fp_ant" DECIMAL(10,2) NOT NULL,
    "dem_p_ant" DECIMAL(10,2) NOT NULL,
    "dem_fp_dep" DECIMAL(10,2) NOT NULL,
    "dem_p_dep" DECIMAL(10,2) NOT NULL,
    "latitude_ponto_conexao" DECIMAL(10,8) NULL,
    "longitude_ponto_conexao" DECIMAL(11,8) NULL,
    "flag_menor_custo_global" BIT NOT NULL DEFAULT 0,
    "flag_alternativa_escolhida" BIT NOT NULL DEFAULT 0,
    "flag_carga" BIT NULL DEFAULT 0,
    "flag_geracao" BIT NULL DEFAULT 0,
    "flag_fluxo_reverso" BIT NULL DEFAULT 0,
    "custo_modular" DECIMAL(15,2) NOT NULL,
    "id_estudo" BIGINT NOT NULL,
    "blob_image" VARBINARY(MAX) NULL,
    "observacao" TEXT NULL,
    "ERD" DECIMAL(10,3) NULL,
    "demanda_disponivel_ponto" DECIMAL(10,2) NULL,
    "letra_alternativa" VARCHAR(1) NULL,
    "proporcionalidade" DECIMAL(3,2) NULL,
    "subgrupo_tarifario" VARCHAR(3) NULL,
    "etapa" BIGINT NOT NULL DEFAULT 1,
    "id_k" BIGINT NULL,
    "id_img_anexo" BIGINT NULL
);
ALTER TABLE "atlas"."alternativas" ADD CONSTRAINT "atlas_alternativas_id_alternativa_primary" PRIMARY KEY("id_alternativa");
GO

CREATE TABLE "atlas"."obras"(
    "id_obra" BIGINT IDENTITY(1,1) NOT NULL,
    "quantidade" DECIMAL(10,3) NOT NULL,
    "descricao" VARCHAR(500) NOT NULL,
    "valor" DECIMAL(15,2) NOT NULL,
    "id_regional" BIGINT NOT NULL,
    "id_kit" BIGINT NOT NULL,
    "id_alternativa" BIGINT NOT NULL
);
ALTER TABLE "atlas"."obras" ADD CONSTRAINT "atlas_obras_id_obra_primary" PRIMARY KEY("id_obra");
GO

-- =====================================================================
-- FOREIGN KEY CONSTRAINTS
-- =====================================================================

ALTER TABLE "atlas"."usuarios" ADD CONSTRAINT "atlas_usuarios_id_edp_foreign" FOREIGN KEY("id_edp") REFERENCES "atlas"."edp"("id_edp");

ALTER TABLE "atlas"."FATOR_K" ADD CONSTRAINT "atlas_fator_k_id_edp_foreign" FOREIGN KEY("id_edp") REFERENCES "atlas"."edp"("id_edp");

ALTER TABLE "atlas"."regionais" ADD CONSTRAINT "atlas_regionais_id_edp_foreign" FOREIGN KEY("id_edp") REFERENCES "atlas"."edp"("id_edp");
ALTER TABLE "atlas"."municipios" ADD CONSTRAINT "atlas_municipios_id_edp_foreign" FOREIGN KEY("id_edp") REFERENCES "atlas"."edp"("id_edp");
ALTER TABLE "atlas"."municipios" ADD CONSTRAINT "atlas_municipios_id_regional_foreign" FOREIGN KEY("id_regional") REFERENCES "atlas"."regionais"("id_regional");
ALTER TABLE "atlas"."subestacoes" ADD CONSTRAINT "atlas_subestacoes_id_edp_foreign" FOREIGN KEY("id_edp") REFERENCES "atlas"."edp"("id_edp");
ALTER TABLE "atlas"."subestacoes" ADD CONSTRAINT "atlas_subestacoes_id_municipio_foreign" FOREIGN KEY("id_municipio") REFERENCES "atlas"."municipios"("id_municipio");
ALTER TABLE "atlas"."circuitos" ADD CONSTRAINT "atlas_circuitos_id_subestacao_foreign" FOREIGN KEY("id_subestacao") REFERENCES "atlas"."subestacoes"("id_subestacao");
ALTER TABLE "atlas"."circuitos" ADD CONSTRAINT "atlas_circuitos_id_edp_foreign" FOREIGN KEY("id_edp") REFERENCES "atlas"."edp"("id_edp");

ALTER TABLE "atlas"."resp_regioes" ADD CONSTRAINT "atlas_resp_regioes_id_usuario_foreign" FOREIGN KEY("id_usuario") REFERENCES "atlas"."usuarios"("id_usuario");
ALTER TABLE "atlas"."resp_regioes" ADD CONSTRAINT "atlas_regioes_id_regional_foreign" FOREIGN KEY("id_regional") REFERENCES "atlas"."regionais"("id_regional");

ALTER TABLE "atlas"."estudos" ADD CONSTRAINT "atlas_estudos_id_edp_foreign" FOREIGN KEY("id_edp") REFERENCES "atlas"."edp"("id_edp");
ALTER TABLE "atlas"."estudos" ADD CONSTRAINT "atlas_estudos_id_regional_foreign" FOREIGN KEY("id_regional") REFERENCES "atlas"."regionais"("id_regional");
ALTER TABLE "atlas"."estudos" ADD CONSTRAINT "atlas_estudos_id_criado_por_foreign" FOREIGN KEY("id_criado_por") REFERENCES "atlas"."usuarios"("id_usuario");
ALTER TABLE "atlas"."estudos" ADD CONSTRAINT "atlas_estudos_id_resp_alteracao_foreign" FOREIGN KEY("id_resp_alteracao") REFERENCES "atlas"."usuarios"("id_usuario");
ALTER TABLE "atlas"."estudos" ADD CONSTRAINT "atlas_estudos_id_eng_responsavel_foreign" FOREIGN KEY("id_resp_regiao") REFERENCES "atlas"."resp_regioes"("id_resp_regiao");
ALTER TABLE "atlas"."estudos" ADD CONSTRAINT "atlas_estudos_id_empresa_foreign" FOREIGN KEY("id_empresa") REFERENCES "atlas"."empresas"("id_empresa");
ALTER TABLE "atlas"."estudos" ADD CONSTRAINT "atlas_estudos_id_municipio_foreign" FOREIGN KEY("id_municipio") REFERENCES "atlas"."municipios"("id_municipio");
ALTER TABLE "atlas"."estudos" ADD CONSTRAINT "atlas_estudos_id_tensao_foreign" FOREIGN KEY("id_tensao") REFERENCES "atlas"."tensao"("id_tensao");
ALTER TABLE "atlas"."estudos" ADD CONSTRAINT "atlas_estudos_id_tipo_solicitacao_foreign" FOREIGN KEY("id_tipo_solicitacao") REFERENCES "atlas"."tipo_solicitacao"("id_tipo_solicitacao");

ALTER TABLE "atlas"."anexos" ADD CONSTRAINT "atlas_anexos_id_estudo_foreign" FOREIGN KEY("id_estudo") REFERENCES "atlas"."estudos"("id_estudo");
ALTER TABLE "atlas"."socios" ADD CONSTRAINT "atlas_socios_id_empresa_foreign" FOREIGN KEY("id_empresa") REFERENCES "atlas"."empresas"("id_empresa");

ALTER TABLE "atlas"."status_estudo" ADD CONSTRAINT "atlas_status_estudo_id_estudo_foreign" FOREIGN KEY("id_estudo") REFERENCES "atlas"."estudos"("id_estudo");
ALTER TABLE "atlas"."status_estudo" ADD CONSTRAINT "atlas_status_estudo_id_criado_por_foreign" FOREIGN KEY("id_criado_por") REFERENCES "atlas"."usuarios"("id_usuario");
ALTER TABLE "atlas"."status_estudo" ADD CONSTRAINT "atlas_status_estudo_id_status_tipo_foreign" FOREIGN KEY("id_status_tipo") REFERENCES "atlas"."status_tipos"("id_status_tipo");

ALTER TABLE "atlas"."alternativas" ADD CONSTRAINT "atlas_alternativas_id_circuito_foreign" FOREIGN KEY("id_circuito") REFERENCES "atlas"."circuitos"("id_circuito");
ALTER TABLE "atlas"."alternativas" ADD CONSTRAINT "atlas_alternativas_id_estudo_foreign" FOREIGN KEY("id_estudo") REFERENCES "atlas"."estudos"("id_estudo");
ALTER TABLE "atlas"."alternativas" ADD CONSTRAINT "atlas_alternativas_id_anexo_foreign" FOREIGN KEY("id_img_anexo") REFERENCES "atlas"."anexos"("id_anexo");
ALTER TABLE "atlas"."alternativas" ADD CONSTRAINT "atlas_alternativas_id_k_foreign" FOREIGN KEY("id_k") REFERENCES "atlas"."FATOR_K"("id_k");

ALTER TABLE "atlas"."obras" ADD CONSTRAINT "atlas_obras_id_regional_foreign" FOREIGN KEY("id_regional") REFERENCES "atlas"."regionais"("id_regional");
ALTER TABLE "atlas"."obras" ADD CONSTRAINT "atlas_obras_id_kit_foreign" FOREIGN KEY("id_kit") REFERENCES "atlas"."kits"("id_kit");
ALTER TABLE "atlas"."obras" ADD CONSTRAINT "atlas_obras_id_alternativa_foreign" FOREIGN KEY("id_alternativa") REFERENCES "atlas"."alternativas"("id_alternativa");

ALTER TABLE "atlas"."doc_padronizados" ADD CONSTRAINT "atlas_doc_padronizados_id_tipo_solicitacao_foreign" FOREIGN KEY("id_tipo_solicitacao") REFERENCES "atlas"."tipo_solicitacao"("id_tipo_solicitacao");
GO

-- =====================================================================
-- INDICES ADICIONAIS PARA PERFORMANCE
-- (ver tambem sql_files/index.sql para os indices cobertos usados nas telas)
-- =====================================================================

CREATE INDEX "idx_estudos_empresa" ON "atlas"."estudos"("id_empresa");
CREATE INDEX "idx_estudos_eng_responsavel" ON "atlas"."estudos"("id_resp_regiao");
CREATE INDEX "idx_estudos_regional" ON "atlas"."estudos"("id_regional");
CREATE INDEX "idx_estudos_tensao" ON "atlas"."estudos"("id_tensao");
CREATE INDEX "idx_alternativas_estudo" ON "atlas"."alternativas"("id_estudo");
CREATE INDEX "idx_status_estudo_data" ON "atlas"."status_estudo"("data");
CREATE INDEX "idx_status_estudo_tipo" ON "atlas"."status_estudo"("id_status_tipo");
CREATE INDEX "idx_anexos_estudo" ON "atlas"."anexos"("id_estudo");
CREATE INDEX "idx_municipios_regional" ON "atlas"."municipios"("id_regional");
GO
