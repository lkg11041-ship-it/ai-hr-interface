import os
import requests
from datetime import datetime

API_BASE = os.getenv("API_BASE", "http://localhost:8000")

# 20명의 샘플 지원자 데이터
sample_candidates = [
    {
        "applicant_id": "A001",
        "name": "김태현",
        "age": 32,
        "gender": "남",
        "education": "서울대학교 컴퓨터공학과 학사",
        "experience_years": 8,
        "passage_text": "삼성전자에서 5년간 백엔드 개발 경험. Python, Java, Spring Boot 전문. 대규모 트래픽 처리 시스템 설계 및 구축. AWS 클라우드 아키텍처 설계 경험 3년. MSA 전환 프로젝트 리드.",
        "skills": ["Python", "Java", "Spring Boot", "AWS", "MSA", "Kubernetes"],
        "industries": ["IT", "전자"],
        "years": 8.0
    },
    {
        "applicant_id": "A002",
        "name": "이지은",
        "age": 28,
        "gender": "여",
        "education": "연세대학교 경영학과 학사",
        "experience_years": 5,
        "passage_text": "신한은행 디지털금융부서 5년 근무. 모바일뱅킹 서비스 기획 및 운영. 고객 데이터 분석을 통한 맞춤형 금융상품 개발. Fintech 스타트업과의 협업 프로젝트 다수 진행.",
        "skills": ["금융", "데이터분석", "서비스기획", "Fintech"],
        "industries": ["금융", "은행"],
        "years": 5.0
    },
    {
        "applicant_id": "A003",
        "name": "박민수",
        "age": 35,
        "gender": "남",
        "education": "KAIST 전산학과 석사",
        "experience_years": 10,
        "passage_text": "네이버 AI Lab에서 7년간 머신러닝 엔지니어로 근무. 추천시스템, 자연어처리 프로젝트 리드. TensorFlow, PyTorch 전문가. 딥러닝 모델 최적화 및 배포 경험 풍부. 논문 5편 게재.",
        "skills": ["Python", "Machine Learning", "TensorFlow", "PyTorch", "NLP", "추천시스템"],
        "industries": ["IT", "AI"],
        "years": 10.0
    },
    {
        "applicant_id": "A004",
        "name": "최수진",
        "age": 26,
        "gender": "여",
        "education": "이화여대 디자인학과 학사",
        "experience_years": 3,
        "passage_text": "카카오 UX/UI 디자이너 3년 경력. 모바일 앱 디자인 전문. 사용자 리서치 기반 인터페이스 설계. Figma, Sketch, Adobe XD 능숙. 디자인 시스템 구축 경험.",
        "skills": ["UI/UX", "Figma", "사용자리서치", "디자인시스템"],
        "industries": ["IT", "디자인"],
        "years": 3.0
    },
    {
        "applicant_id": "A005",
        "name": "정우성",
        "age": 40,
        "gender": "남",
        "education": "고려대학교 경영학과 MBA",
        "experience_years": 15,
        "passage_text": "삼성증권 자산관리부서 15년 경력. PB(Private Banker) 업무 수행. 고액 자산가 포트폴리오 관리. 연평균 수익률 15% 달성. 리더십 우수상 3회 수상. 팀장 경험 5년.",
        "skills": ["자산관리", "금융상품", "포트폴리오관리", "리더십"],
        "industries": ["금융", "증권"],
        "years": 15.0
    },
    {
        "applicant_id": "A006",
        "name": "강하늘",
        "age": 29,
        "gender": "남",
        "education": "성균관대학교 소프트웨어학과 학사",
        "experience_years": 4,
        "passage_text": "쿠팡 프론트엔드 개발자 4년. React, TypeScript, Next.js 전문. 대규모 이커머스 플랫폼 개발 및 운영. 성능 최적화로 로딩속도 40% 개선. 반응형 웹 디자인 구현 경험 풍부.",
        "skills": ["React", "TypeScript", "Next.js", "JavaScript", "성능최적화"],
        "industries": ["IT", "이커머스"],
        "years": 4.0
    },
    {
        "applicant_id": "A007",
        "name": "윤서아",
        "age": 31,
        "gender": "여",
        "education": "서강대학교 컴퓨터공학과 학사",
        "experience_years": 7,
        "passage_text": "라인 플러스 데이터 엔지니어 7년. 대용량 데이터 파이프라인 구축. Spark, Hadoop, Kafka 전문가. 실시간 데이터 처리 시스템 설계. 데이터 웨어하우스 최적화로 쿼리 성능 60% 향상.",
        "skills": ["데이터엔지니어링", "Spark", "Hadoop", "Kafka", "SQL"],
        "industries": ["IT", "빅데이터"],
        "years": 7.0
    },
    {
        "applicant_id": "A008",
        "name": "한지민",
        "age": 27,
        "gender": "여",
        "education": "한양대학교 경영정보학과 학사",
        "experience_years": 3,
        "passage_text": "토스 프로덕트 매니저 3년. 금융 서비스 기획 및 출시. 사용자 페르소나 분석 전문. A/B 테스팅으로 전환율 25% 향상. 애자일 방법론 실무 적용 경험.",
        "skills": ["프로덕트매니저", "서비스기획", "데이터분석", "애자일"],
        "industries": ["Fintech", "금융"],
        "years": 3.0
    },
    {
        "applicant_id": "A009",
        "name": "오재환",
        "age": 38,
        "gender": "남",
        "education": "포항공대 컴퓨터공학과 박사",
        "experience_years": 12,
        "passage_text": "삼성SDS 블록체인 연구소 수석 연구원. 블록체인 기반 금융 플랫폼 개발. 하이퍼레저 패브릭 전문가. 특허 3건 보유. 국제 학회 발표 10회. 기술 표준화 위원회 참여.",
        "skills": ["블록체인", "암호학", "하이퍼레저", "금융IT", "연구개발"],
        "industries": ["IT", "블록체인", "금융"],
        "years": 12.0
    },
    {
        "applicant_id": "A010",
        "name": "송혜교",
        "age": 30,
        "gender": "여",
        "education": "중앙대학교 미디어커뮤니케이션학과 학사",
        "experience_years": 6,
        "passage_text": "넷플릭스 코리아 콘텐츠 마케팅 매니저 6년. 디지털 마케팅 캠페인 기획 및 실행. SNS 마케팅 전문가. 바이럴 캠페인으로 조회수 500만 달성. 크리에이티브 전략 수립.",
        "skills": ["디지털마케팅", "콘텐츠기획", "SNS마케팅", "브랜딩"],
        "industries": ["미디어", "엔터테인먼트"],
        "years": 6.0
    },
    {
        "applicant_id": "A011",
        "name": "김현우",
        "age": 33,
        "gender": "남",
        "education": "서울대학교 전기정보공학부 석사",
        "experience_years": 9,
        "passage_text": "LG전자 스마트홈 IoT 개발팀 9년. 임베디드 시스템 개발 전문. C/C++, RTOS 전문가. 무선 통신 프로토콜(Zigbee, BLE) 구현. 제품 양산 경험 5건 이상.",
        "skills": ["임베디드", "IoT", "C/C++", "무선통신", "펌웨어"],
        "industries": ["전자", "IoT"],
        "years": 9.0
    },
    {
        "applicant_id": "A012",
        "name": "이나영",
        "age": 28,
        "gender": "여",
        "education": "이화여대 통계학과 석사",
        "experience_years": 4,
        "passage_text": "카카오뱅크 데이터 사이언티스트 4년. 신용평가 모델 개발. Python, R 전문가. 머신러닝 기반 이상거래 탐지 시스템 구축. 고객 이탈 예측 모델로 정확도 92% 달성.",
        "skills": ["데이터사이언스", "Python", "R", "Machine Learning", "통계분석"],
        "industries": ["금융", "Fintech"],
        "years": 4.0
    },
    {
        "applicant_id": "A013",
        "name": "박서준",
        "age": 34,
        "gender": "남",
        "education": "연세대학교 건축학과 학사",
        "experience_years": 10,
        "passage_text": "현대건설 스마트시티 사업부 10년. BIM(Building Information Modeling) 전문가. 대형 건축 프로젝트 PM 경험 5건. 3D 모델링 및 시뮬레이션. 친환경 건축 설계 전문.",
        "skills": ["BIM", "건축설계", "프로젝트관리", "3D모델링"],
        "industries": ["건설", "스마트시티"],
        "years": 10.0
    },
    {
        "applicant_id": "A014",
        "name": "전지현",
        "age": 29,
        "gender": "여",
        "education": "한국외대 통번역학과 학사",
        "experience_years": 5,
        "passage_text": "아마존 코리아 글로벌 커뮤니케이션 매니저 5년. 영어, 일본어, 중국어 능통. 다국적 기업 협상 경험 풍부. 글로벌 프로젝트 코디네이션. 문화 간 커뮤니케이션 전문.",
        "skills": ["영어", "일본어", "중국어", "글로벌커뮤니케이션", "협상"],
        "industries": ["IT", "글로벌"],
        "years": 5.0
    },
    {
        "applicant_id": "A015",
        "name": "최우식",
        "age": 26,
        "gender": "남",
        "education": "서울대학교 컴퓨터공학과 학사",
        "experience_years": 2,
        "passage_text": "배민 신입 백엔드 개발자 2년. Node.js, Express 기반 API 개발. MongoDB, Redis 활용 경험. MSA 환경에서 마이크로서비스 개발. 테스트 주도 개발(TDD) 실천.",
        "skills": ["Node.js", "Express", "MongoDB", "Redis", "JavaScript"],
        "industries": ["IT", "푸드테크"],
        "years": 2.0
    },
    {
        "applicant_id": "A016",
        "name": "김고은",
        "age": 31,
        "gender": "여",
        "education": "이화여대 심리학과 석사",
        "experience_years": 7,
        "passage_text": "네이버웹툰 UX 리서처 7년. 사용자 행동 분석 전문가. 정성/정량 리서치 설계 및 수행. 페르소나 및 고객여정지도 작성. 리서치 인사이트 기반 서비스 개선으로 만족도 30% 향상.",
        "skills": ["UX리서치", "사용자분석", "정성조사", "데이터분석"],
        "industries": ["IT", "콘텐츠"],
        "years": 7.0
    },
    {
        "applicant_id": "A017",
        "name": "유아인",
        "age": 36,
        "gender": "남",
        "education": "서울대학교 경제학과 학사, MBA",
        "experience_years": 12,
        "passage_text": "BCG(보스턴컨설팅그룹) 시니어 컨설턴트 12년. 디지털 트랜스포메이션 프로젝트 30건 이상 수행. 전략 수립 및 실행 지원. 금융, 제조, 유통 산업 전문. 고객사 매출 평균 25% 증대.",
        "skills": ["전략컨설팅", "디지털전환", "비즈니스분석", "프로젝트관리"],
        "industries": ["컨설팅", "전략"],
        "years": 12.0
    },
    {
        "applicant_id": "A018",
        "name": "신민아",
        "age": 27,
        "gender": "여",
        "education": "서울대학교 인공지능학과 학사",
        "experience_years": 3,
        "passage_text": "구글 코리아 머신러닝 엔지니어 3년. 컴퓨터 비전 프로젝트 참여. TensorFlow, Keras 전문. 이미지 분류 및 객체 탐지 모델 개발. 모델 경량화로 추론 속도 50% 개선.",
        "skills": ["Machine Learning", "컴퓨터비전", "TensorFlow", "Python", "딥러닝"],
        "industries": ["IT", "AI"],
        "years": 3.0
    },
    {
        "applicant_id": "A019",
        "name": "조인성",
        "age": 39,
        "gender": "남",
        "education": "고려대학교 법학과 학사",
        "experience_years": 14,
        "passage_text": "법무법인 율촌 변호사 14년. IT, 지식재산권 전문. 스타트업 법률 자문 다수. M&A, 계약 검토 전문가. 기업 법률 리스크 관리. 법률 세미나 강연 경험 풍부.",
        "skills": ["법률자문", "지식재산권", "계약법", "M&A"],
        "industries": ["법률", "IT"],
        "years": 14.0
    },
    {
        "applicant_id": "A020",
        "name": "수지",
        "age": 25,
        "gender": "여",
        "education": "홍익대학교 시각디자인과 학사",
        "experience_years": 2,
        "passage_text": "카카오 그래픽 디자이너 2년. 브랜딩 및 시각 아이덴티티 디자인. 일러스트레이션 전문. Adobe Creative Suite 능숙. 모션 그래픽 제작 경험. 디자인 어워드 수상 2회.",
        "skills": ["그래픽디자인", "브랜딩", "일러스트", "모션그래픽"],
        "industries": ["IT", "디자인"],
        "years": 2.0
    }
]

def insert_candidates():
    success_count = 0
    failed_count = 0

    for candidate in sample_candidates:
        try:
            response = requests.post(
                f"{API_BASE}/search/index/candidate",
                json=candidate,
                headers={"Content-Type": "application/json"}
            )

            if response.status_code == 200:
                success_count += 1
                print(f"✅ {candidate['name']} ({candidate['applicant_id']}) 추가 성공")
            else:
                failed_count += 1
                print(f"❌ {candidate['name']} 추가 실패: {response.text}")
        except Exception as e:
            failed_count += 1
            print(f"❌ {candidate['name']} 추가 오류: {str(e)}")

    print(f"\n📊 결과: 성공 {success_count}건, 실패 {failed_count}건")

if __name__ == "__main__":
    print("📥 샘플 데이터 삽입 시작...\n")
    insert_candidates()
    print("\n✨ 완료!")