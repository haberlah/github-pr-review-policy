#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
skill_dir="${repo_root}/skills/github-pr-review-policy"
dist_dir="${repo_root}/dist"
zip_path="${dist_dir}/github-pr-review-policy.zip"

mkdir -p "${dist_dir}"
rm -f "${zip_path}"

(
  cd "${repo_root}/skills"
  zip -r "${zip_path}" github-pr-review-policy \
    -x '*/__pycache__/*' \
    -x '*.pyc' \
    -x '*.DS_Store'
)

printf 'Created Claude skill zip: %s\n' "${zip_path}"
