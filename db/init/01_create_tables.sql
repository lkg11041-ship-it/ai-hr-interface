-- 후보자 기본 정보 테이블 (구조화된 데이터)
CREATE TABLE IF NOT EXISTS candidates (
    applicant_id VARCHAR(20) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    age INTEGER,
    gender VARCHAR(10),
    education TEXT,
    experience_years INTEGER,
    skills TEXT[],  -- 배열로 저장
    industries TEXT[],  -- 배열로 저장
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_candidates_experience ON candidates(experience_years);
CREATE INDEX idx_candidates_age ON candidates(age);
CREATE INDEX idx_candidates_gender ON candidates(gender);
CREATE INDEX idx_candidates_skills ON candidates USING GIN(skills);
CREATE INDEX idx_candidates_industries ON candidates USING GIN(industries);