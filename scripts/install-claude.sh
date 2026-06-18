#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
skill_src="${repo_root}/skills/github-pr-review-policy"
skill_dest="${CLAUDE_HOME:-${HOME}/.claude}/skills/github-pr-review-policy"

mkdir -p "$(dirname "${skill_dest}")"
ln -sfn "${skill_src}" "${skill_dest}"

printf 'Installed Claude skill: %s -> %s\n' "${skill_dest}" "${skill_src}"
