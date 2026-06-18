# GitHub PR Review Policy Skill

A configurable Codex and Claude Code skill for routing GitHub pull request reviews, preventing duplicate bot reviews, and verifying that generic "looks good" or thumbs-up responses actually came from a review run.

The skill is intentionally generic. Repository access, branch protection, required checks, and CODEOWNERS stay in GitHub. This skill controls agent behavior before review comments are posted and classifies the evidence afterward.

## What It Does

- Defaults new PR reviews to Codex with `@codex review`.
- Supports Claude Code Review only when enabled in policy and limited to explicit `allowedRepos`.
- Keeps Claude manual-only and first-cycle-only when configured that way.
- Routes re-review after fix commits back to the configured rerun provider, usually Codex.
- Classifies review state from GitHub comments, PR reviews, inline comments, and check runs.
- Treats generic no-findings responses as unverified unless there is current-head evidence.
- The guard script never posts comments, changes GitHub configuration, or merges PRs by itself. It only prints JSON, and `--emit-comment-body` prints the exact comment body an agent or human may choose to post after checking `allow_trigger`.

## Repository Layout

```text
skills/github-pr-review-policy/
  SKILL.md
  agents/openai.yaml
  references/
    review-policy.json
    review-policy.example.json
    *.md
  scripts/pr_review_guard.py
scripts/
  install-claude.sh
  install-codex.sh
  package-claude-zip.sh
tests/
```

## Requirements

- Python 3.10+
- GitHub CLI: `gh`
- GitHub CLI authenticated for the repositories being inspected

Check auth:

```bash
gh auth status
```

## Install For Codex

```bash
git clone https://github.com/haberlah/github-pr-review-policy.git
cd github-pr-review-policy
./scripts/install-codex.sh
```

The script symlinks:

```text
skills/github-pr-review-policy -> ~/.codex/skills/github-pr-review-policy
```

## Install For Claude Code

```bash
git clone https://github.com/haberlah/github-pr-review-policy.git
cd github-pr-review-policy
./scripts/install-claude.sh
```

The script symlinks:

```text
skills/github-pr-review-policy -> ~/.claude/skills/github-pr-review-policy
```

For Claude Team/org distribution, package a zip:

```bash
./scripts/package-claude-zip.sh
```

The zip contains the skill folder itself, suitable for org-level skill distribution workflows that accept a skill archive.

## Configure Policy

The bundled `references/review-policy.json` is safe by default:

- Codex enabled.
- Claude disabled.
- Claude allowed repos empty.

To enable Claude for a team, copy `review-policy.example.json` into `review-policy.json` and set:

```json
{
  "providers": {
    "claude": {
      "enabled": true,
      "allowedRepos": ["OWNER/REPO"]
    }
  }
}
```

The guard loads policy in this order:

1. `--policy /path/to/review-policy.json`
2. `PR_REVIEW_POLICY_PATH`
3. `~/.config/github-pr-review-policy/review-policy.json`
4. `skills/github-pr-review-policy/references/review-policy.json`
5. built-in conservative defaults

Inspect the active policy:

```bash
python3 skills/github-pr-review-policy/scripts/pr_review_guard.py policy
```

## GitHub-Side Controls

Use GitHub for hard enforcement:

- GitHub App repository access decides which repos Codex or Claude can reach.
- Branch protection/rulesets decide merge eligibility.
- CODEOWNERS and required reviews decide human approval.
- Required status checks decide CI gates.

Use this skill for deterministic agent behavior:

- whether to request Codex or Claude,
- whether Claude is allowed on a repo,
- whether a review cycle already exists,
- whether generic no-findings text is verified,
- whether review evidence is stale or missing.

Keep GitHub App access and `review-policy.json` aligned. If GitHub gives a bot broader access than the policy allows, treat that as configuration drift and fix GitHub or policy before triggering reviews.

## Guard Examples

Snapshot PR state:

```bash
python3 skills/github-pr-review-policy/scripts/pr_review_guard.py \
  snapshot --repo OWNER/REPO --pr 123
```

Check whether Codex may be triggered:

```bash
python3 skills/github-pr-review-policy/scripts/pr_review_guard.py \
  pre-codex --repo OWNER/REPO --pr 123 --emit-comment-body
```

Check whether Claude may be triggered:

```bash
python3 skills/github-pr-review-policy/scripts/pr_review_guard.py \
  pre-claude --repo OWNER/REPO --pr 123 --emit-comment-body
```

Classify a no-findings response:

```bash
python3 skills/github-pr-review-policy/scripts/pr_review_guard.py \
  classify --bot codex --repo OWNER/REPO --pr 123
```

## PR Workflow For This Repo

This repo has no production runtime or deployment environment. Changes should go through normal GitHub PRs targeting `main`.

Recommended protection for teams using this in production workflows:

- Require at least one human approval for `references/review-policy.json`.
- Require at least one human approval for `scripts/pr_review_guard.py`.
- Run the test suite before merging.

Those files define policy and enforcement logic; bot-only approval is not enough for a policy change.

## Test

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile skills/github-pr-review-policy/scripts/pr_review_guard.py
```

The tests avoid live GitHub calls. Live guard commands require `gh` auth and a real PR.

## License

MIT
