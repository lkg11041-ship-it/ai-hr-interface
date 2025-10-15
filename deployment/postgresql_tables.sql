-- =====================================================
-- PostgreSQL Tables for Oracle to PostgreSQL ETL
-- =====================================================
-- 실행 방법: psql -U app -d recruit -f postgresql_tables.sql

-- 1. app 스키마 생성
CREATE SCHEMA IF NOT EXISTS app;

-- 2. 채용 데이터 테이블 (타겟 테이블)
CREATE TABLE IF NOT EXISTS app.recruitment (
  id               BIGINT PRIMARY KEY,
  candidate_id     TEXT,
  full_name        TEXT,
  gender           TEXT,                 -- 필요 시 뷰/권한으로 접근 통제
  birth_year       SMALLINT,
  education_level  TEXT,
  years_experience NUMERIC(5,1),
  industry         TEXT,
  role_title       TEXT,
  resume_text      TEXT,                 -- 필요 시 비식별화 요건 검토
  source_updated_at TIMESTAMPTZ,
  load_date        DATE DEFAULT CURRENT_DATE
);
CREATE INDEX IF NOT EXISTS idx_recruitment_loaddate ON app.recruitment(load_date);

COMMENT ON TABLE app.recruitment IS 'Oracle HR.RECRUITMENT 테이블에서 추출한 채용 데이터';
COMMENT ON COLUMN app.recruitment.load_date IS '데이터 적재 일자 (보존정책 기준)';

-- 3. 채용 데이터 스테이지 테이블 (임시 적재용)
CREATE TABLE IF NOT EXISTS app.recruitment_stage (
  id               BIGINT PRIMARY KEY,
  candidate_id     TEXT,
  full_name        TEXT,
  gender           TEXT,
  birth_year       SMALLINT,
  education_level  TEXT,
  years_experience NUMERIC(5,1),
  industry         TEXT,
  role_title       TEXT,
  resume_text      TEXT,
  source_updated_at TIMESTAMPTZ,
  load_date        DATE DEFAULT CURRENT_DATE
);

COMMENT ON TABLE app.recruitment_stage IS '원자적 교체를 위한 스테이지 테이블';

-- 4. ETL 실행 이력 테이블
CREATE TABLE IF NOT EXISTS app.run_history (
  run_id        BIGSERIAL PRIMARY KEY,
  dag_id        TEXT NOT NULL,
  task_id       TEXT NOT NULL,
  source_table  TEXT,
  target_table  TEXT,
  status        TEXT CHECK (status IN ('IN_PROGRESS','SUCCESS','FAILED')),
  rows_read     BIGINT,
  rows_written  BIGINT,
  started_at    TIMESTAMPTZ NOT NULL,
  finished_at   TIMESTAMPTZ,
  duration_ms   BIGINT,
  message       TEXT,
  created_at    TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_run_history_dag_time ON app.run_history(dag_id, started_at);

COMMENT ON TABLE app.run_history IS 'Airflow DAG 실행 이력 추적';
COMMENT ON COLUMN app.run_history.status IS 'IN_PROGRESS: 실행 중, SUCCESS: 성공, FAILED: 실패';

-- 5. 에러 로그 테이블
CREATE TABLE IF NOT EXISTS app.error_log (
  error_id      BIGSERIAL PRIMARY KEY,
  run_id        BIGINT REFERENCES app.run_history(run_id) ON DELETE SET NULL,
  dag_id        TEXT NOT NULL,
  task_id       TEXT NOT NULL,
  step          TEXT,            -- EXTRACT / LOAD / CLEANUP 등
  error_class   TEXT,
  error_message TEXT,
  stacktrace    TEXT,
  source_table  TEXT,
  target_table  TEXT,
  key_payload   JSONB,           -- 문제 행 키/샘플 페이로드
  error_at      TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_error_log_dag_time ON app.error_log(dag_id, error_at);

COMMENT ON TABLE app.error_log IS 'ETL 실행 중 발생한 에러 상세 기록';
COMMENT ON COLUMN app.error_log.step IS 'EXTRACT: 추출 단계, LOAD: 적재 단계, CLEANUP: 정리 단계';

-- 6. 테이블 목록 확인
SELECT schemaname, tablename
FROM pg_tables
WHERE schemaname = 'app'
ORDER BY tablename;

-- 7. 권한 설정 (필요 시)
-- GRANT ALL PRIVILEGES ON SCHEMA app TO app;
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA app TO app;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA app TO app;
