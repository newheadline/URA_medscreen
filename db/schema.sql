-- Основная БД MedScreen (контур приёма). Свежая установка: psql "$DATABASE_URL" -f db/schema.sql
-- Для уже созданной БД: db/migrations/002_registry_and_audit.sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS "Authorization" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role VARCHAR(32) NOT NULL,
    email VARCHAR(320) NOT NULL UNIQUE,
    login VARCHAR(128) NOT NULL UNIQUE,
    passwordHash VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS "Patients" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    age INTEGER NOT NULL CHECK (age >= 18 AND age <= 120),
    sex VARCHAR(1) NOT NULL CHECK (sex IN ('M', 'F')),
    -- NULL: пациент зарегистрирован врачом/администратором, учётной записи ещё нет
    auth_id UUID UNIQUE,
    -- Идентифицирующие данные хранятся ТОЛЬКО шифртекстом (Fernet, ключ у приложения):
    -- дамп БД без ключа не раскрывает, кто пациент.
    full_name_enc BYTEA,
    oms_enc BYTEA,
    -- HMAC-SHA256 нормализованного номера ОМС: запрет дублей и точный поиск без расшифровки
    oms_hash CHAR(64),
    contacts_enc BYTEA,
    created_by UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT fk_patient_auth
        FOREIGN KEY (auth_id) REFERENCES "Authorization" (id)
        ON DELETE RESTRICT,
    CONSTRAINT fk_patient_created_by
        FOREIGN KEY (created_by) REFERENCES "Authorization" (id)
        ON DELETE RESTRICT
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_patients_oms_hash
    ON "Patients" (oms_hash)
    WHERE oms_hash IS NOT NULL;

CREATE TABLE IF NOT EXISTS "Doctors" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    specialty VARCHAR(255) NOT NULL,
    auth_id UUID NOT NULL UNIQUE,
    CONSTRAINT fk_doctor_auth
        FOREIGN KEY (auth_id) REFERENCES "Authorization" (id)
        ON DELETE RESTRICT
);

-- ABAC: врач видит только пациентов из этой таблицы
CREATE TABLE IF NOT EXISTS "Doctor_n_patients" (
    doctor_id UUID NOT NULL,
    patient_id UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (doctor_id, patient_id),
    CONSTRAINT fk_doctor_patient_doctor
        FOREIGN KEY (doctor_id) REFERENCES "Doctors" (id)
        ON DELETE CASCADE,
    CONSTRAINT fk_doctor_patient_patient
        FOREIGN KEY (patient_id) REFERENCES "Patients" (id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_doctor_patients_patient
    ON "Doctor_n_patients" (patient_id);

CREATE TABLE IF NOT EXISTS "Analyses" (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    biomarkers JSONB NOT NULL,
    predictions JSONB,
    user_id UUID NOT NULL,
    doctor_id UUID,
    status VARCHAR(32) NOT NULL DEFAULT 'RECEIVED',
    error_code VARCHAR(64),
    case_token VARCHAR(64),
    model_version VARCHAR(128),
    -- Триаж по последнему результату: anemia | latent | normal (заполняет воркер)
    triage_status VARCHAR(16),
    patient_age INTEGER NOT NULL CHECK (patient_age >= 18 AND patient_age <= 120),
    patient_sex VARCHAR(1) NOT NULL CHECK (patient_sex IN ('M', 'F')),
    pregnant BOOLEAN,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT fk_analysis_patient
        FOREIGN KEY (user_id) REFERENCES "Patients" (id)
        ON DELETE RESTRICT,
    CONSTRAINT fk_analysis_doctor
        FOREIGN KEY (doctor_id) REFERENCES "Doctors" (id)
        ON DELETE RESTRICT,
    CONSTRAINT chk_analysis_status
        CHECK (status IN ('RECEIVED', 'PROCESSING', 'DONE', 'FAILED')),
    CONSTRAINT chk_analysis_triage
        CHECK (triage_status IS NULL OR triage_status IN ('anemia', 'latent', 'normal')),
    -- pregnant=false допустимо для любого пола (флаг по умолчанию), true — только для F
    CONSTRAINT chk_analysis_pregnancy
        CHECK (pregnant IS NOT TRUE OR patient_sex = 'F')
);

CREATE INDEX IF NOT EXISTS idx_analysis_user_created
    ON "Analyses" (user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_analysis_user_status_created
    ON "Analyses" (user_id, status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_analysis_doctor_created
    ON "Analyses" (doctor_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_analysis_status_updated
    ON "Analyses" (status, updated_at);

CREATE UNIQUE INDEX IF NOT EXISTS uq_analysis_case_token
    ON "Analyses" (case_token)
    WHERE case_token IS NOT NULL;

-- ───────────────────────── Журнал аудита (WORM) ─────────────────────────
-- Запись только добавляется. Каждая запись несёт HMAC-SHA256 от (prev_hash + её поля):
-- цепочка делает любое изменение/удаление/вставку «задним числом» обнаружимым
-- (scripts/verify_audit.py). Ключ HMAC есть только у приложения.
CREATE TABLE IF NOT EXISTS "Audit_log" (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    timestamp_utc TIMESTAMPTZ NOT NULL,
    user_id UUID,                          -- NULL: до аутентификации / системное действие
    role VARCHAR(32),
    client_ip VARCHAR(45),
    action_type VARCHAR(48) NOT NULL,
    resource_id VARCHAR(64),
    execution_status VARCHAR(16) NOT NULL,
    prev_hash CHAR(64) NOT NULL,
    digital_signature_hash CHAR(64) NOT NULL,
    CONSTRAINT chk_audit_status
        CHECK (execution_status IN ('SUCCESS', 'DENIED', 'ERROR')),
    CONSTRAINT uq_audit_prev_hash UNIQUE (prev_hash),            -- цепочка линейна: без ветвлений
    CONSTRAINT uq_audit_signature UNIQUE (digital_signature_hash)
);

CREATE INDEX IF NOT EXISTS idx_audit_ts ON "Audit_log" (timestamp_utc);
CREATE INDEX IF NOT EXISTS idx_audit_user_ts ON "Audit_log" (user_id, timestamp_utc);
CREATE INDEX IF NOT EXISTS idx_audit_resource ON "Audit_log" (resource_id);

CREATE OR REPLACE FUNCTION audit_log_is_write_once() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'Audit_log is write-once: % is forbidden', TG_OP
        USING ERRCODE = 'insufficient_privilege';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_audit_no_update_delete ON "Audit_log";
CREATE TRIGGER trg_audit_no_update_delete
    BEFORE UPDATE OR DELETE ON "Audit_log"
    FOR EACH ROW EXECUTE FUNCTION audit_log_is_write_once();

DROP TRIGGER IF EXISTS trg_audit_no_truncate ON "Audit_log";
CREATE TRIGGER trg_audit_no_truncate
    BEFORE TRUNCATE ON "Audit_log"
    FOR EACH STATEMENT EXECUTE FUNCTION audit_log_is_write_once();

REVOKE UPDATE, DELETE, TRUNCATE ON "Audit_log" FROM PUBLIC;