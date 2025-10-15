CREATE SCHEMA IF NOT EXISTS hr;
CREATE TABLE IF NOT EXISTS hr.applicant(
  applicant_id BIGSERIAL PRIMARY KEY,
  full_name TEXT NOT NULL,
  birth_year SMALLINT,
  email TEXT,
  phone TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);
CREATE TABLE IF NOT EXISTS hr.experience(
  exp_id BIGSERIAL PRIMARY KEY,
  applicant_id BIGINT REFERENCES hr.applicant(applicant_id) ON DELETE CASCADE,
  company TEXT, title TEXT,
  role_id INT, industry_id INT,
  start_date DATE, end_date DATE, description TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);
CREATE TABLE IF NOT EXISTS hr.skill_ref(
  skill_id SERIAL PRIMARY KEY,
  name TEXT UNIQUE NOT NULL
);
CREATE TABLE IF NOT EXISTS hr.applicant_skill(
  applicant_id BIGINT REFERENCES hr.applicant(applicant_id) ON DELETE CASCADE,
  skill_id INT REFERENCES hr.skill_ref(skill_id),
  level TEXT, years NUMERIC(4,1),
  evidence JSONB, PRIMARY KEY(applicant_id, skill_id)
);
