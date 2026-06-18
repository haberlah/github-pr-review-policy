#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
skill_name="github-pr-review-policy"
skill_dir="${repo_root}/skills/${skill_name}"
dist_dir="${repo_root}/dist"
zip_path="${dist_dir}/${skill_name}.zip"
policy_path=""

usage() {
  cat <<'EOF'
Usage: scripts/package-claude-zip.sh [options]

Create a Claude-compatible skill zip.

Options:
  --policy PATH   Replace references/review-policy.json in the zip with PATH.
  --output PATH   Write the zip to PATH.
  --suffix TEXT   Write dist/github-pr-review-policy-TEXT.zip. TEXT may contain
                  only letters, digits, dot, underscore, and hyphen.
  -h, --help      Show this help.

Examples:
  scripts/package-claude-zip.sh
  scripts/package-claude-zip.sh --policy ~/.config/github-pr-review-policy/review-policy.json --suffix bellamed
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --policy)
      if [ "$#" -lt 2 ]; then
        printf 'Missing value for --policy\n' >&2
        exit 1
      fi
      policy_path="$2"
      shift 2
      ;;
    --output)
      if [ "$#" -lt 2 ]; then
        printf 'Missing value for --output\n' >&2
        exit 1
      fi
      zip_path="$2"
      shift 2
      ;;
    --suffix)
      if [ "$#" -lt 2 ]; then
        printf 'Missing value for --suffix\n' >&2
        exit 1
      fi
      suffix="$2"
      case "${suffix}" in
        *[!a-zA-Z0-9._-]*|'')
          printf 'Invalid --suffix value: %s\n' "${suffix}" >&2
          printf 'Use only letters, digits, dot, underscore, and hyphen.\n' >&2
          exit 1
          ;;
      esac
      zip_path="${dist_dir}/${skill_name}-${suffix}.zip"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'Unknown option: %s\n' "$1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [ ! -d "${skill_dir}" ]; then
  printf 'Skill directory not found: %s\n' "${skill_dir}" >&2
  exit 1
fi

if [ -n "${policy_path}" ]; then
  if [ ! -f "${policy_path}" ]; then
    printf 'Policy file not found: %s\n' "${policy_path}" >&2
    exit 1
  fi
  python3 - "${policy_path}" <<'PY'
import json
import sys
from pathlib import Path

policy_path = Path(sys.argv[1]).expanduser()
with policy_path.open("r", encoding="utf-8") as fh:
    json.load(fh)
PY
fi

mkdir -p "$(dirname "${zip_path}")"
rm -f "${zip_path}"

tmp_dir="$(mktemp -d "${TMPDIR:-/tmp}/${skill_name}.XXXXXX")"
trap 'rm -rf "${tmp_dir}"' EXIT

mkdir -p "${tmp_dir}/${skill_name}"
rsync -a \
  --exclude '__pycache__/' \
  --exclude '*.pyc' \
  --exclude '.DS_Store' \
  "${skill_dir}/" \
  "${tmp_dir}/${skill_name}/"

if [ -n "${policy_path}" ]; then
  cp "${policy_path}" "${tmp_dir}/${skill_name}/references/review-policy.json"
fi

(
  cd "${tmp_dir}"
  zip -r "${zip_path}" "${skill_name}" \
    -x '*/__pycache__/*' \
    -x '*.pyc' \
    -x '*.DS_Store'
)

printf 'Created Claude skill zip: %s\n' "${zip_path}"
if [ -n "${policy_path}" ]; then
  printf 'Packaged policy: %s\n' "${policy_path}"
fi
