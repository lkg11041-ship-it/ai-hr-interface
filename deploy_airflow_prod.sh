#!/bin/bash
set -e

###############################################################################
# Airflow 운영 배포 스크립트
# 용도: Airflow webserver/scheduler만 운영 서버에 배포
###############################################################################

echo "=========================================="
echo "Airflow Production Deployment Script"
echo "=========================================="

# 환경 변수 파일 확인
if [ ! -f .env.prod ]; then
    echo "ERROR: .env.prod 파일이 없습니다."
    echo ".env.prod.example을 복사하여 .env.prod를 생성하고 운영 정보를 입력하세요."
    exit 1
fi

# .env.prod 로드
export $(grep -v '^#' .env.prod | xargs)

echo ""
echo "1. 운영 환경 변수 확인..."
echo "   - POSTGRES_HOST: ${POSTGRES_HOST}"
echo "   - POSTGRES_DB: ${POSTGRES_DB}"
echo "   - ORACLE_HOST: ${ORACLE_HOST}"
echo "   - TZ: ${TZ}"

read -p "운영 환경 변수가 올바릅니까? (y/n): " confirm
if [ "$confirm" != "y" ]; then
    echo "배포를 중단합니다. .env.prod 파일을 수정하세요."
    exit 1
fi

echo ""
echo "2. 기존 Airflow 컨테이너 중지 및 제거..."
docker compose -f docker-compose.prod.yml --env-file .env.prod stop airflow-webserver airflow-scheduler || true
docker compose -f docker-compose.prod.yml --env-file .env.prod rm -f airflow-webserver airflow-scheduler || true

echo ""
echo "3. Airflow 이미지 빌드..."
docker compose -f docker-compose.prod.yml --env-file .env.prod build airflow-webserver

echo ""
echo "4. Airflow DB 마이그레이션 실행..."
docker compose -f docker-compose.prod.yml --env-file .env.prod run --rm airflow-webserver airflow db migrate

echo ""
echo "5. Airflow Admin 계정 생성 (이미 존재하면 스킵)..."
read -p "Airflow Admin Username (기본값: admin): " ADMIN_USER
ADMIN_USER=${ADMIN_USER:-admin}
read -sp "Airflow Admin Password: " ADMIN_PASS
echo ""

if [ -z "$ADMIN_PASS" ]; then
    echo "ERROR: Password는 필수입니다."
    exit 1
fi

docker compose -f docker-compose.prod.yml --env-file .env.prod run --rm airflow-webserver \
    airflow users create \
    --role Admin \
    --username "$ADMIN_USER" \
    --password "$ADMIN_PASS" \
    --firstname Admin \
    --lastname User \
    --email admin@example.com || echo "사용자가 이미 존재하거나 생성 중 오류 발생 (무시 가능)"

echo ""
echo "6. Airflow 컨테이너 시작..."
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d airflow-webserver airflow-scheduler

echo ""
echo "7. 배포 완료! 컨테이너 상태 확인..."
docker compose -f docker-compose.prod.yml --env-file .env.prod ps

echo ""
echo "=========================================="
echo "Airflow 배포 완료"
echo "=========================================="
echo "Webserver URL: http://<서버IP>:8081"
echo "Username: $ADMIN_USER"
echo ""
echo "로그 확인:"
echo "  docker compose -f docker-compose.prod.yml --env-file .env.prod logs -f airflow-webserver"
echo "  docker compose -f docker-compose.prod.yml --env-file .env.prod logs -f airflow-scheduler"
echo ""
