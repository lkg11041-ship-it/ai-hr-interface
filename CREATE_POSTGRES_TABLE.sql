-- ============================================================================
-- PostgreSQL 테이블 생성 스크립트
-- ============================================================================
-- 새 스키마: rsaiif.applicant_info (155개 컬럼)
-- Oracle SREC.APPLICANT_INFO_TEMP → PostgreSQL rsaiif.applicant_info
-- ============================================================================

-- 기존 테이블 삭제 (주의: 데이터 손실)
-- DROP TABLE IF EXISTS rsaiif.applicant_info CASCADE;

-- 새 테이블 생성
CREATE TABLE IF NOT EXISTS rsaiif.applicant_info
(
    pk_key                VARCHAR(4000) NOT NULL PRIMARY KEY,
    notiyy                VARCHAR(4000),
    balno                 VARCHAR(10),
    notino                VARCHAR(50),
    resno                 VARCHAR(500),
    scrcompcd             VARCHAR(10),
    company_nm            VARCHAR(4000),
    name                  VARCHAR(50),
    job_nm                VARCHAR(4000),
    loc_nm                VARCHAR(4000),
    birdt                 VARCHAR(8),
    adress                VARCHAR(100),
    nation                VARCHAR(4000),
    apply_path            VARCHAR(4000),
    bohun_yn              VARCHAR(8),
    bohun_relation        VARCHAR(20),
    disabled_nm           VARCHAR(4000),
    disabled              VARCHAR(4000),
    hobby                 VARCHAR(50),
    highschool            VARCHAR(80),
    high_flag1            VARCHAR(4000),
    high_flag2            VARCHAR(50),
    high_g_ym             VARCHAR(9),
    high_g_flag           VARCHAR(4000),
    high_loc              VARCHAR(4000),
    junior_college        VARCHAR(50),
    junior_college_flag1  VARCHAR(4000),
    junior_college_flag2  VARCHAR(4000),
    junior_colleage_spec  VARCHAR(50),
    junior_enter_ym       VARCHAR(15),
    junior_enter_flag     VARCHAR(4000),
    junior_g_ym           VARCHAR(50),
    junior_g_flag         VARCHAR(4000),
    junior_loc            VARCHAR(4000),
    university            VARCHAR(70),
    university_flag1      VARCHAR(4000),
    university_flag2      VARCHAR(4000),
    university_spec       VARCHAR(70),
    university_spec_sub   VARCHAR(70),
    university_enter_ym   VARCHAR(30),
    university_enter_flag VARCHAR(4000),
    university_g_ym       VARCHAR(6),
    university_g_flag     VARCHAR(4000),
    university_loc        VARCHAR(4000),
    gra_school            VARCHAR(70),
    gra_school_flag1      VARCHAR(4000),
    gra_school_flag2      VARCHAR(4000),
    gra_school_spec       VARCHAR(70),
    gra_school_g_ym       VARCHAR(30),
    gra_schooly_g_flag    VARCHAR(4000),
    gra_school_loc        VARCHAR(4000),
    arm_nm                VARCHAR(4000),
    arm_sta_ymd           VARCHAR(20),
    arm_end_ymd           VARCHAR(15),
    arm_gubun             VARCHAR(4000),
    arm_ranks             VARCHAR(4000),
    lang1                 VARCHAR(4000),
    lang1_ex              VARCHAR(4000),
    lang1_score           NUMERIC(38),
    lang1_lv              VARCHAR(4000),
    lang1_ju              VARCHAR(50),
    lang2                 VARCHAR(4000),
    lang2_ex              VARCHAR(4000),
    lang2_score           NUMERIC(38),
    lang2_lv              VARCHAR(4000),
    lang2_ju              VARCHAR(50),
    lang3                 VARCHAR(4000),
    lang3_ex              VARCHAR(4000),
    lang3_score           NUMERIC(38),
    lang3_lv              VARCHAR(4000),
    lang3_ju              VARCHAR(50),
    lang4                 VARCHAR(4000),
    lang4_ex              VARCHAR(4000),
    lang4_score           NUMERIC(38),
    lang4_lv              VARCHAR(4000),
    lang4_ju              VARCHAR(50),
    lice1_nm              VARCHAR(4000),
    lice1_grade           VARCHAR(4000),
    lice1_ju              VARCHAR(50),
    lice2_nm              VARCHAR(4000),
    lice2_grade           VARCHAR(4000),
    lice2_ju              VARCHAR(50),
    lice3_nm              VARCHAR(4000),
    lice3_grade           VARCHAR(4000),
    lice3_ju              VARCHAR(50),
    car_sta_ym_1          VARCHAR(8),
    car_end_ym_1          VARCHAR(8),
    car_nm_1              VARCHAR(50),
    car_jik_1             VARCHAR(50),
    car_job_1             VARCHAR(50),
    car_retire_1          VARCHAR(50),
    car_sta_ym_2          VARCHAR(8),
    car_end_ym_2          VARCHAR(8),
    car_nm_2              VARCHAR(50),
    car_jik_2             VARCHAR(50),
    car_job_2             VARCHAR(50),
    car_retire_2          VARCHAR(50),
    car_sta_ym_3          VARCHAR(8),
    car_end_ym_3          VARCHAR(8),
    car_nm_3              VARCHAR(50),
    car_jik_3             VARCHAR(50),
    car_job_3             VARCHAR(50),
    car_retire_3          VARCHAR(50),
    car_sta_ym_4          VARCHAR(8),
    car_end_ym_4          VARCHAR(8),
    car_nm_4              VARCHAR(50),
    car_jik_4             VARCHAR(50),
    car_job_4             VARCHAR(50),
    car_retire_4          VARCHAR(50),
    prizeorg_1            VARCHAR(20),
    prizecon_1            VARCHAR(40),
    prizedt_1             VARCHAR(8),
    prizeorg_2            VARCHAR(20),
    prizecon_2            VARCHAR(40),
    prizedt_2             VARCHAR(8),
    prizeorg_3            VARCHAR(20),
    prizecon_3            VARCHAR(40),
    prizedt_3             VARCHAR(8),
    prizeorg_4            VARCHAR(20),
    prizecon_4            VARCHAR(40),
    prizedt_4             VARCHAR(8),
    service_nm_1          VARCHAR(50),
    service_period_1      VARCHAR(4000),
    service_detail_1      VARCHAR(100),
    service_nm_2          VARCHAR(50),
    service_period_2      VARCHAR(4000),
    service_detail_2      VARCHAR(100),
    club_nm_1             VARCHAR(50),
    club_period_1         VARCHAR(4000),
    club_detail_1         VARCHAR(150),
    club_nm_2             VARCHAR(50),
    club_period_2         VARCHAR(4000),
    club_detail_2         VARCHAR(150),
    club_nm_3             VARCHAR(50),
    club_period_3         VARCHAR(4000),
    club_detail_3         VARCHAR(150),
    train_nm_1            VARCHAR(50),
    train_period_1        VARCHAR(4000),
    train_detail_1        VARCHAR(150),
    train_nm_2            VARCHAR(50),
    train_period_2        VARCHAR(4000),
    train_detail_2        VARCHAR(150),
    train_nm_3            VARCHAR(50),
    train_period_3        VARCHAR(4000),
    train_detail_3        VARCHAR(150),
    trip_nm_1             VARCHAR(50),
    trip_period_1         VARCHAR(4000),
    trip_detail_1         VARCHAR(100),
    trip_nm_2             VARCHAR(50),
    trip_period_2         VARCHAR(4000),
    trip_detail_2         VARCHAR(100),
    reason                VARCHAR(4000),
    experience            VARCHAR(4000),
    skill                 VARCHAR(4000)
);

-- 주석 추가
COMMENT ON TABLE rsaiif.applicant_info IS 'Oracle SREC.APPLICANT_INFO_TEMP에서 이관된 지원자 정보 테이블 (155개 컬럼)';
COMMENT ON COLUMN rsaiif.applicant_info.pk_key IS 'Primary Key (기존 APPLICANT_INFO_ID 대체)';
COMMENT ON COLUMN rsaiif.applicant_info.notiyy IS '공고년도 (새 컬럼)';
COMMENT ON COLUMN rsaiif.applicant_info.balno IS '발령번호 (새 컬럼)';
COMMENT ON COLUMN rsaiif.applicant_info.notino IS '공고번호 (새 컬럼)';
COMMENT ON COLUMN rsaiif.applicant_info.resno IS '주민번호 (새 컬럼)';
COMMENT ON COLUMN rsaiif.applicant_info.scrcompcd IS '심사회사코드 (새 컬럼)';

-- 권한 부여 (필요시)
GRANT SELECT, INSERT, UPDATE, DELETE ON rsaiif.applicant_info TO rs_ai_user;

-- 인덱스 생성 (성능 최적화)
CREATE INDEX IF NOT EXISTS idx_applicant_pk_key ON rsaiif.applicant_info(pk_key);
CREATE INDEX IF NOT EXISTS idx_applicant_notiyy ON rsaiif.applicant_info(notiyy);
CREATE INDEX IF NOT EXISTS idx_applicant_name ON rsaiif.applicant_info(name);

-- 테이블 확인
SELECT
    table_name,
    column_name,
    data_type,
    character_maximum_length
FROM information_schema.columns
WHERE table_schema = 'rsaiif'
  AND table_name = 'applicant_info'
ORDER BY ordinal_position;
