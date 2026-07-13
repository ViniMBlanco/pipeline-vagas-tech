-- Tabela: vagas
-- Armazena os dados principais de cada vaga, já validados
-- e transformados (etapa final do ELT).
-- ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS vagas (
    id                  SERIAL PRIMARY KEY,
    id_externo          VARCHAR(100) NOT NULL UNIQUE, -- id da vaga na API RemoteOK (evita duplicidade)
    cargo               VARCHAR(255) NOT NULL,
    empresa             VARCHAR(255) NOT NULL,
    localizacao         VARCHAR(255),
    tipo_vaga           VARCHAR(100),                 -- ex: full-time, contract
    salario_min         NUMERIC(12, 2),
    salario_max         NUMERIC(12, 2),
    moeda               VARCHAR(10) DEFAULT 'USD',
    data_publicacao     TIMESTAMP,
    url_vaga            TEXT,
    data_coleta         TIMESTAMP NOT NULL DEFAULT NOW(), -- quando o pipeline coletou o registro
    criado_em           TIMESTAMP NOT NULL DEFAULT NOW(),
    atualizado_em       TIMESTAMP NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE vagas IS 'Vagas de tecnologia processadas e validadas, prontas para análise';
COMMENT ON COLUMN vagas.id_externo IS 'Identificador original da vaga na API RemoteOK';

-- ---------------------------------------------------------
-- Tabela: tecnologias
-- Lista única de tecnologias/skills mencionadas nas vagas.
CREATE TABLE IF NOT EXISTS tecnologias (
    id                  SERIAL PRIMARY KEY,
    nome                VARCHAR(100) NOT NULL UNIQUE
);

-- ---------------------------------------------------------
-- Tabela: vaga_tecnologias
-- Associação N:N entre vagas e tecnologias.
CREATE TABLE IF NOT EXISTS vaga_tecnologias (
    vaga_id             INTEGER NOT NULL REFERENCES vagas(id) ON DELETE CASCADE,
    tecnologia_id       INTEGER NOT NULL REFERENCES tecnologias(id) ON DELETE CASCADE,
    PRIMARY KEY (vaga_id, tecnologia_id)
);

-- ---------------------------------------------------------
-- Tabela: log_execucao
-- Registra cada execução do pipeline.
CREATE TABLE IF NOT EXISTS log_execucao (
    id                  SERIAL PRIMARY KEY,
    etapa               VARCHAR(50) NOT NULL,   -- extract, validate, transform, load
    status              VARCHAR(20) NOT NULL,   -- sucesso, erro, alerta
    mensagem            TEXT,
    qtd_registros       INTEGER,
    executado_em        TIMESTAMP NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE log_execucao IS 'Log de execução de cada etapa do pipeline ELT';

-- ---------------------------------------------------------
-- Índices para consultas mais comuns
CREATE INDEX IF NOT EXISTS idx_vagas_cargo        ON vagas(cargo);
CREATE INDEX IF NOT EXISTS idx_vagas_empresa       ON vagas(empresa);
CREATE INDEX IF NOT EXISTS idx_vagas_data_pub       ON vagas(data_publicacao);
CREATE INDEX IF NOT EXISTS idx_tecnologias_nome     ON tecnologias(nome);

-- ---------------------------------------------------------
-- Trigger para manter "atualizado_em" sempre corrente
CREATE OR REPLACE FUNCTION atualizar_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.atualizado_em = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_atualizar_vagas ON vagas;
CREATE TRIGGER trg_atualizar_vagas
    BEFORE UPDATE ON vagas
    FOR EACH ROW
    EXECUTE FUNCTION atualizar_timestamp();
