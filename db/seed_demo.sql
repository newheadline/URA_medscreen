-- DEMO ONLY. UUID должны совпадать с intake/auth.py:DEMO_AUTH_IDS.
-- Применение (PowerShell):
--   cmd /c "docker compose exec -T intake-db psql -U intake_user -d medscreen_intake < db\seed_demo.sql"

-- Врач
INSERT INTO "Authorization" (id, role, email, login, "passwordhash")
VALUES ('11111111-1111-1111-1111-111111111111', 'doctor',
        'doctor@demo.local', 'doctor_demo', 'demo')
ON CONFLICT (id) DO NOTHING;

INSERT INTO "Doctors" (id, specialty, auth_id)
VALUES ('11111111-1111-1111-1111-222222222222', 'Терапевт',
        '11111111-1111-1111-1111-111111111111')
ON CONFLICT (id) DO NOTHING;

-- Пациент
INSERT INTO "Authorization" (id, role, email, login, "passwordhash")
VALUES ('22222222-2222-2222-2222-222222222222', 'patient',
        'patient@demo.local', 'patient_demo', 'demo')
ON CONFLICT (id) DO NOTHING;

INSERT INTO "Patients" (id, age, sex, auth_id, created_at)
VALUES ('22222222-2222-2222-2222-333333333333', 42, 'F',
        '22222222-2222-2222-2222-222222222222', now())
ON CONFLICT (id) DO NOTHING;

-- Админ
INSERT INTO "Authorization" (id, role, email, login, "passwordhash")
VALUES ('33333333-3333-3333-3333-333333333333', 'admin',
        'admin@demo.local', 'admin_demo', 'demo')
ON CONFLICT (id) DO NOTHING;