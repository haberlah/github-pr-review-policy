#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
skill_src="${repo_root}/skills/github-pr-review-policy"
skill_dest="${CLAUDE_HOME:-${HOME}/.claude}/skills/github-pr-review-policy"

mkdir -p "$(dirname "${skill_dest}")"
if [ -L "${skill_dest}" ]; then
  rm "${skill_dest}"
elif [ -e "${skill_dest}" ]; then
  printf 'Refusing to replace existing non-symlink path: %s\n' "${skill_dest}" >&2
  printf 'Move it aside first, then rerun this installer.\n' >&2
  exit 1
fi

ln -s "${skill_src}" "${skill_dest}"

printf 'Installed Claude skill: %s -> %s\n' "${skill_dest}" "${skill_src}"
