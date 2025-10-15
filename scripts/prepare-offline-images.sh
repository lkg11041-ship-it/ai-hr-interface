#!/bin/bash
# ============================================================================
# Offline Deployment - Image Preparation Script
# ============================================================================
#
# 이 스크립트는 인터넷 연결된 환경에서 실행하여 폐쇄망 배포에 필요한
# 모든 Docker 이미지를 빌드하고 tar 파일로 저장합니다.
#
# 사용 방법:
#   chmod +x scripts/prepare-offline-images.sh
#   ./scripts/prepare-offline-images.sh
#
# 출력:
#   offline-images/ 디렉토리에 모든 이미지 tar 파일 생성
# ============================================================================

set -e  # 에러 발생 시 즉시 종료
set -u  # 정의되지 않은 변수 사용 시 에러

# ============================================================================
# 설정
# ============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
OUTPUT_DIR="$PROJECT_ROOT/offline-images"
DATE=$(date +%Y%m%d_%H%M%S)

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================================================
# 함수 정의
# ============================================================================
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_command() {
    if ! command -v $1 &> /dev/null; then
        log_error "$1 command not found. Please install $1 first."
        exit 1
    fi
}

# ============================================================================
# 사전 검사
# ============================================================================
log_info "Starting offline image preparation..."
log_info "Project root: $PROJECT_ROOT"
log_info "Output directory: $OUTPUT_DIR"

# Docker 설치 확인
check_command docker

# 인터넷 연결 확인
log_info "Checking internet connectivity..."
if ! curl -s --head --request GET https://www.google.com | grep "200 OK" > /dev/null; then
    log_error "No internet connection. This script must run in an online environment."
    exit 1
fi
log_success "Internet connection verified"

# 출력 디렉토리 생성
mkdir -p "$OUTPUT_DIR"
cd "$PROJECT_ROOT"

# ============================================================================
# Step 1: Base Images Pull
# ============================================================================
log_info "Step 1/6: Pulling base images..."

BASE_IMAGES=(
    "apache/airflow:2.9.2-python3.11"
    "postgres:16"
    "opensearchproject/opensearch:2.13.0"
    "opensearchproject/opensearch-dashboards:2.13.0"
)

for image in "${BASE_IMAGES[@]}"; do
    log_info "Pulling $image..."
    docker pull "$image"

    # 이미지 이름에서 ':' 를 '_' 로 변경하여 파일명 생성
    filename=$(echo "$image" | tr '/:' '_')
    log_info "Saving $image to ${filename}.tar..."
    docker save "$image" -o "$OUTPUT_DIR/${filename}.tar"
    log_success "Saved: ${filename}.tar ($(du -h "$OUTPUT_DIR/${filename}.tar" | cut -f1))"
done

# ============================================================================
# Step 2: Build Airflow Offline Image
# ============================================================================
log_info "Step 2/6: Building Airflow offline image..."

if [ ! -f "$PROJECT_ROOT/airflow/Dockerfile.offline" ]; then
    log_error "airflow/Dockerfile.offline not found!"
    exit 1
fi

log_info "Building recruit-airflow:offline..."
docker build \
    -f "$PROJECT_ROOT/airflow/Dockerfile.offline" \
    -t recruit-airflow:offline \
    "$PROJECT_ROOT/airflow"

log_success "Airflow image built successfully"

log_info "Saving recruit-airflow:offline image..."
docker save recruit-airflow:offline -o "$OUTPUT_DIR/recruit-airflow-offline.tar"
log_success "Saved: recruit-airflow-offline.tar ($(du -h "$OUTPUT_DIR/recruit-airflow-offline.tar" | cut -f1))"

# ============================================================================
# Step 3: Build Backend Image (Optional)
# ============================================================================
log_info "Step 3/6: Building Backend image..."

if [ -f "$PROJECT_ROOT/backend/Dockerfile" ]; then
    log_info "Building recruit-backend:offline..."
    docker build \
        -f "$PROJECT_ROOT/backend/Dockerfile" \
        -t recruit-backend:offline \
        "$PROJECT_ROOT/backend"

    log_info "Saving recruit-backend:offline image..."
    docker save recruit-backend:offline -o "$OUTPUT_DIR/recruit-backend-offline.tar"
    log_success "Saved: recruit-backend-offline.tar ($(du -h "$OUTPUT_DIR/recruit-backend-offline.tar" | cut -f1))"
else
    log_warn "backend/Dockerfile not found, skipping backend image"
fi

# ============================================================================
# Step 4: Build Frontend Image (Optional)
# ============================================================================
log_info "Step 4/6: Building Frontend image..."

if [ -f "$PROJECT_ROOT/frontend/Dockerfile" ]; then
    log_info "Building recruit-frontend:offline..."
    docker build \
        -f "$PROJECT_ROOT/frontend/Dockerfile" \
        -t recruit-frontend:offline \
        "$PROJECT_ROOT/frontend"

    log_info "Saving recruit-frontend:offline image..."
    docker save recruit-frontend:offline -o "$OUTPUT_DIR/recruit-frontend-offline.tar"
    log_success "Saved: recruit-frontend-offline.tar ($(du -h "$OUTPUT_DIR/recruit-frontend-offline.tar" | cut -f1))"
else
    log_warn "frontend/Dockerfile not found, skipping frontend image"
fi

# ============================================================================
# Step 5: Create Image List
# ============================================================================
log_info "Step 5/6: Creating image list..."

cat > "$OUTPUT_DIR/image-list.txt" << EOF
# Docker Images for Offline Deployment
# Generated: $(date)

Base Images:
$(for image in "${BASE_IMAGES[@]}"; do echo "  - $image"; done)

Custom Images:
  - recruit-airflow:offline
  - recruit-backend:offline
  - recruit-frontend:offline

Total Images: $(ls -1 "$OUTPUT_DIR"/*.tar | wc -l)
Total Size: $(du -sh "$OUTPUT_DIR" | cut -f1)
EOF

log_success "Image list created: $OUTPUT_DIR/image-list.txt"

# ============================================================================
# Step 6: Create Load Script
# ============================================================================
log_info "Step 6/6: Creating load script for offline environment..."

cat > "$OUTPUT_DIR/load-images.sh" << 'EOF'
#!/bin/bash
# ============================================================================
# Load Docker Images in Offline Environment
# ============================================================================
#
# 이 스크립트는 폐쇄망 환경에서 실행하여 tar 파일을 Docker 이미지로 로드합니다.
#
# 사용 방법:
#   chmod +x load-images.sh
#   ./load-images.sh
# ============================================================================

set -e

# 색상 정의
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

log_info "Loading Docker images from tar files..."

# 모든 tar 파일 로드
for tar_file in *.tar; do
    if [ -f "$tar_file" ]; then
        log_info "Loading $tar_file..."
        docker load -i "$tar_file"
        log_success "Loaded: $tar_file"
    fi
done

log_info "Verifying loaded images..."
docker images | grep -E "recruit|airflow|postgres|opensearch"

log_success "All images loaded successfully!"
log_info "You can now run: docker compose -f docker-compose.yml -f docker-compose.offline.yml up -d"
EOF

chmod +x "$OUTPUT_DIR/load-images.sh"
log_success "Load script created: $OUTPUT_DIR/load-images.sh"

# ============================================================================
# Step 7: Create Deployment Guide
# ============================================================================
log_info "Creating deployment guide..."

cat > "$OUTPUT_DIR/README.md" << EOF
# Offline Deployment Package

생성 날짜: $(date)
생성 위치: $(hostname)

## 📦 패키지 내용

\`\`\`
$(ls -lh *.tar 2>/dev/null | awk '{print $9, "-", $5}')
\`\`\`

**총 크기**: $(du -sh . | cut -f1)

## 📋 배포 절차

### 1. 파일 전송

이 디렉토리 전체를 폐쇄망 서버로 전송:

\`\`\`bash
# 예시: scp로 전송
scp -r offline-images/ user@offline-server:/opt/recruit-ai/

# 또는 USB, 내부망 파일 공유 등 사용
\`\`\`

### 2. 이미지 로드

폐쇄망 서버에서 실행:

\`\`\`bash
cd /opt/recruit-ai/offline-images/
chmod +x load-images.sh
./load-images.sh
\`\`\`

### 3. 이미지 확인

\`\`\`bash
docker images | grep recruit
\`\`\`

예상 출력:
\`\`\`
recruit-airflow       offline    ...    ...    ...
recruit-backend       offline    ...    ...    ...
recruit-frontend      offline    ...    ...    ...
\`\`\`

### 4. 배포 실행

프로젝트 루트 디렉토리로 이동 후:

\`\`\`bash
cd /opt/recruit-ai/

# .env 파일 설정
cp .env.prod.example .env
nano .env

# Offline 모드로 실행
docker compose -f docker-compose.yml -f docker-compose.offline.yml --env-file .env up -d
\`\`\`

### 5. 서비스 확인

\`\`\`bash
# 컨테이너 상태 확인
docker compose ps

# Airflow 접속
curl http://localhost:8081
\`\`\`

## ⚠️ 주의사항

1. **이미지 pull 정책**: 모든 서비스는 \`pull_policy: never\` 설정되어 있어 인터넷에서 이미지를 다운로드하지 않습니다.

2. **임베딩 모델**: SentenceTransformers 모델이 이미지에 포함되어 있습니다 (약 80MB).

3. **외부 DB 필수**: 폐쇄망 환경에서는 외부 PostgreSQL과 OpenSearch를 사용하는 것을 권장합니다.

4. **버전 고정**: 모든 Python 패키지 버전이 requirements-offline.txt에 고정되어 있습니다.

## 🔧 트러블슈팅

### 이미지 로드 실패
\`\`\`bash
# tar 파일 무결성 확인
tar -tzf recruit-airflow-offline.tar | head

# 수동 로드
docker load -i recruit-airflow-offline.tar
\`\`\`

### 디스크 공간 부족
\`\`\`bash
# 현재 디스크 사용량 확인
df -h

# Docker 정리
docker system prune -a
\`\`\`

## 📞 지원

문제 발생 시 다음 정보와 함께 문의:
- 에러 로그: \`docker compose logs\`
- 시스템 정보: \`docker info\`
- 이미지 목록: \`docker images\`
EOF

log_success "Deployment guide created: $OUTPUT_DIR/README.md"

# ============================================================================
# 완료 메시지
# ============================================================================
echo ""
echo "============================================================================"
log_success "Offline image preparation completed!"
echo "============================================================================"
echo ""
log_info "Output directory: $OUTPUT_DIR"
log_info "Total images: $(ls -1 "$OUTPUT_DIR"/*.tar | wc -l)"
log_info "Total size: $(du -sh "$OUTPUT_DIR" | cut -f1)"
echo ""
log_info "Next steps:"
echo "  1. Transfer the '$OUTPUT_DIR' directory to your offline server"
echo "  2. Run 'load-images.sh' on the offline server"
echo "  3. Deploy using 'docker-compose.offline.yml'"
echo ""
log_info "For detailed instructions, see: $OUTPUT_DIR/README.md"
echo "============================================================================"
