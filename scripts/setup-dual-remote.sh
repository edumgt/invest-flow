#!/usr/bin/env bash
# =============================================================================
# scripts/setup-dual-remote.sh
#
# GitHub + GitLab 동시 push 설정 스크립트
#
# 이 스크립트는 git remote 를 아래와 같이 구성합니다:
#   - origin      : GitHub (기존)
#   - gitlab      : GitLab (신규)
#   - all-remotes : GitHub + GitLab 동시 push용 가상 remote
#
# 사용법:
#   chmod +x scripts/setup-dual-remote.sh
#   ./scripts/setup-dual-remote.sh \
#       --gitlab-url http://gitlab.local:8080 \
#       --gitlab-project edumgt/Vue_vite_tailwind_tui.calendar
#
# 이후 양쪽에 동시 push:
#   git push all-remotes main
#
# 또는 origin push 시 GitLab도 자동 push (pushurl 활용):
#   git push origin main   # GitHub + GitLab 동시 push
# =============================================================================

set -euo pipefail

# ─── 기본값 ────────────────────────────────────────────────────────────────
GITLAB_URL="http://gitlab.local:8080"
GITLAB_PROJECT=""
GITHUB_REMOTE_NAME="origin"
GITLAB_REMOTE_NAME="gitlab"
ALL_REMOTE_NAME="all-remotes"

# ─── 인자 파싱 ─────────────────────────────────────────────────────────────
usage() {
    cat <<EOF
사용법: $0 [옵션]

옵션:
  --gitlab-url     <url>      GitLab 인스턴스 URL (기본: http://gitlab.local:8080)
  --gitlab-project <path>     GitLab 프로젝트 경로 (예: namespace/project-name)
  --github-remote  <name>     GitHub remote 이름 (기본: origin)
  --gitlab-remote  <name>     GitLab remote 이름 (기본: gitlab)
  --all-remote     <name>     동시 push용 remote 이름 (기본: all-remotes)
  -h, --help                  이 도움말 출력

예시:
  $0 --gitlab-url http://localhost:8080 \\
     --gitlab-project edumgt/Vue_vite_tailwind_tui.calendar
EOF
    exit 1
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --gitlab-url)      GITLAB_URL="$2";      shift 2 ;;
        --gitlab-project)  GITLAB_PROJECT="$2";  shift 2 ;;
        --github-remote)   GITHUB_REMOTE_NAME="$2"; shift 2 ;;
        --gitlab-remote)   GITLAB_REMOTE_NAME="$2"; shift 2 ;;
        --all-remote)      ALL_REMOTE_NAME="$2"; shift 2 ;;
        -h|--help)         usage ;;
        *) echo "알 수 없는 옵션: $1"; usage ;;
    esac
done

# ─── 유효성 검사 ────────────────────────────────────────────────────────────
if [[ -z "$GITLAB_PROJECT" ]]; then
    echo "오류: --gitlab-project 옵션이 필요합니다." >&2
    usage
fi

# git 리포지토리 루트로 이동
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT"

echo "=== GitLab + GitHub 이중 push 설정 ==="
echo "GitHub remote : $(git remote get-url "$GITHUB_REMOTE_NAME" 2>/dev/null || echo '(설정 안됨)')"
echo "GitLab URL    : ${GITLAB_URL}/${GITLAB_PROJECT}.git"
echo ""

# ─── GitHub remote URL 가져오기 ────────────────────────────────────────────
GITHUB_URL="$(git remote get-url "$GITHUB_REMOTE_NAME" 2>/dev/null || true)"
if [[ -z "$GITHUB_URL" ]]; then
    echo "경고: '$GITHUB_REMOTE_NAME' remote를 찾을 수 없습니다. 현재 remote 목록:"
    git remote -v
    echo ""
    echo "GitHub remote URL을 직접 입력하세요 (엔터 시 건너뜀):"
    read -r GITHUB_URL
fi

GITLAB_GIT_URL="${GITLAB_URL}/${GITLAB_PROJECT}.git"

# ─── GitLab remote 추가/업데이트 ───────────────────────────────────────────
if git remote | grep -q "^${GITLAB_REMOTE_NAME}$"; then
    echo "[1/3] GitLab remote 업데이트: $GITLAB_REMOTE_NAME -> $GITLAB_GIT_URL"
    git remote set-url "$GITLAB_REMOTE_NAME" "$GITLAB_GIT_URL"
else
    echo "[1/3] GitLab remote 추가: $GITLAB_REMOTE_NAME -> $GITLAB_GIT_URL"
    git remote add "$GITLAB_REMOTE_NAME" "$GITLAB_GIT_URL"
fi

# ─── 동시 push용 all-remotes remote 설정 ────────────────────────────────────
echo "[2/3] 동시 push remote 설정: $ALL_REMOTE_NAME"
if git remote | grep -q "^${ALL_REMOTE_NAME}$"; then
    git remote remove "$ALL_REMOTE_NAME"
fi

# all-remotes: 첫 번째 URL은 GitHub, 두 번째는 GitLab
git remote add "$ALL_REMOTE_NAME" "$GITHUB_URL"
git remote set-url --add --push "$ALL_REMOTE_NAME" "$GITHUB_URL"
git remote set-url --add --push "$ALL_REMOTE_NAME" "$GITLAB_GIT_URL"

# ─── origin에도 GitLab pushurl 추가 (선택적) ────────────────────────────────
echo "[3/3] origin에 GitLab pushurl 추가 (git push origin → GitHub + GitLab 동시 push)"
# origin의 기존 pushurl 초기화 후 재설정
git remote set-url --delete --push "$GITHUB_REMOTE_NAME" "$GITHUB_URL" 2>/dev/null || true
git remote set-url --add --push "$GITHUB_REMOTE_NAME" "$GITHUB_URL"
git remote set-url --add --push "$GITHUB_REMOTE_NAME" "$GITLAB_GIT_URL"

# ─── 결과 확인 ─────────────────────────────────────────────────────────────
echo ""
echo "=== 설정 완료 ==="
git remote -v
echo ""
echo "사용 방법:"
echo "  git push origin main          # GitHub + GitLab 동시 push"
echo "  git push $ALL_REMOTE_NAME main   # GitHub + GitLab 동시 push (명시적)"
echo "  git push $GITLAB_REMOTE_NAME main  # GitLab 전용 push"
