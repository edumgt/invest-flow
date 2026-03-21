#!/usr/bin/env bash
# =============================================================================
# scripts/register-gitlab-runner.sh
#
# GitLab Runner를 GitLab 인스턴스에 등록하는 헬퍼 스크립트
#
# 사전 요구사항:
#   - docker-compose.gitlab.yml 로 GitLab + Runner 컨테이너가 실행 중이어야 합니다
#   - GitLab UI에서 Runner 등록 토큰을 발급받아야 합니다
#     (Admin > Runners > New instance runner)
#
# 사용법:
#   chmod +x scripts/register-gitlab-runner.sh
#   ./scripts/register-gitlab-runner.sh --token <REGISTRATION_TOKEN>
#
# =============================================================================

set -euo pipefail

# ─── 기본값 ────────────────────────────────────────────────────────────────
GITLAB_URL="http://gitlab.local:8080"
REGISTRATION_TOKEN=""
RUNNER_NAME="calendar-app-runner"
RUNNER_TAGS="docker,node,vue"
RUNNER_EXECUTOR="docker"
RUNNER_DOCKER_IMAGE="node:20-alpine"
CONTAINER_NAME="gitlab-runner"

# ─── 인자 파싱 ─────────────────────────────────────────────────────────────
usage() {
    cat <<EOF
사용법: $0 [옵션]

옵션:
  --token         <token>   GitLab Runner 등록 토큰 (필수)
  --gitlab-url    <url>     GitLab 인스턴스 URL (기본: http://gitlab.local:8080)
  --name          <name>    Runner 이름 (기본: calendar-app-runner)
  --tags          <tags>    Runner 태그 (쉼표 구분, 기본: docker,node,vue)
  --executor      <type>    실행기 타입 (기본: docker)
  --docker-image  <image>   기본 Docker 이미지 (기본: node:20-alpine)
  --container     <name>    Runner 컨테이너 이름 (기본: gitlab-runner)
  -h, --help               이 도움말 출력

예시:
  $0 --token glrt-xxxxxxxxxxxx
  $0 --token glrt-xxxxxxxxxxxx --gitlab-url http://localhost:8080
EOF
    exit 1
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --token)         REGISTRATION_TOKEN="$2"; shift 2 ;;
        --gitlab-url)    GITLAB_URL="$2";          shift 2 ;;
        --name)          RUNNER_NAME="$2";         shift 2 ;;
        --tags)          RUNNER_TAGS="$2";         shift 2 ;;
        --executor)      RUNNER_EXECUTOR="$2";     shift 2 ;;
        --docker-image)  RUNNER_DOCKER_IMAGE="$2"; shift 2 ;;
        --container)     CONTAINER_NAME="$2";      shift 2 ;;
        -h|--help)       usage ;;
        *) echo "알 수 없는 옵션: $1"; usage ;;
    esac
done

if [[ -z "$REGISTRATION_TOKEN" ]]; then
    echo "오류: --token 옵션이 필요합니다." >&2
    echo ""
    echo "GitLab Runner 등록 토큰 발급 방법:"
    echo "  1. GitLab UI 접속: $GITLAB_URL"
    echo "  2. Admin Area > CI/CD > Runners > New instance runner"
    echo "  3. 생성된 토큰을 복사하여 --token 옵션에 사용"
    echo ""
    usage
fi

# ─── Runner 컨테이너 실행 확인 ────────────────────────────────────────────
if ! docker ps --filter "name=${CONTAINER_NAME}" --format "{{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
    echo "오류: '${CONTAINER_NAME}' 컨테이너가 실행 중이지 않습니다."
    echo "먼저 GitLab 스택을 시작하세요:"
    echo "  docker compose -f docker-compose.gitlab.yml up -d"
    exit 1
fi

echo "=== GitLab Runner 등록 ==="
echo "GitLab URL   : $GITLAB_URL"
echo "Runner 이름  : $RUNNER_NAME"
echo "Runner 태그  : $RUNNER_TAGS"
echo "실행기       : $RUNNER_EXECUTOR"
echo ""

# ─── Runner 등록 ─────────────────────────────────────────────────────────
docker exec "$CONTAINER_NAME" gitlab-runner register \
    --non-interactive \
    --url "$GITLAB_URL" \
    --registration-token "$REGISTRATION_TOKEN" \
    --name "$RUNNER_NAME" \
    --tag-list "$RUNNER_TAGS" \
    --executor "$RUNNER_EXECUTOR" \
    --docker-image "$RUNNER_DOCKER_IMAGE" \
    --docker-volumes "/var/run/docker.sock:/var/run/docker.sock" \
    --docker-network-mode "bridge"

echo ""
echo "Runner 등록 완료!"
echo "GitLab Runners 페이지에서 확인: ${GITLAB_URL}/admin/runners"
