from __future__ import annotations

import datetime as dt
import importlib.util
import json
import os
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
GUARD_PATH = REPO_ROOT / "skills" / "github-pr-review-policy" / "scripts" / "pr_review_guard.py"


def load_guard():
    spec = importlib.util.spec_from_file_location("pr_review_guard", GUARD_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class ReviewGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.guard = load_guard()
        self.guard.configure_policy(self.guard.DEFAULT_POLICY)
        self.now = dt.datetime.now(dt.timezone.utc)
        self.base_state = {
            "repo": "OWNER/REPO",
            "pr": 123,
            "head_sha": "abcdef1234567890abcdef1234567890abcdef12",
            "head_ref": "feature/example",
            "base_ref": "main",
            "state": "open",
            "draft": False,
            "comments": [],
            "reviews": [],
            "review_comments": [],
            "check_runs": [],
        }

    def comment(self, login: str, body: str, minutes_ago: int = 5, comment_id: int = 1):
        return {
            "id": comment_id,
            "user": {"login": login},
            "body": body,
            "created_at": (self.now - dt.timedelta(minutes=minutes_ago)).isoformat(),
        }

    def test_claude_is_disabled_without_allowed_repos(self) -> None:
        result = self.guard.pre_claude(dict(self.base_state), False, False)

        self.assertFalse(result["allow_trigger"])
        self.assertIn("Claude review provider is disabled by policy", result["reasons"])
        self.assertIn("Claude review has no allowed repositories configured", result["reasons"])

    def test_policy_override_enables_claude_for_configured_repo(self) -> None:
        policy = self.guard.merge_dict(
            self.guard.DEFAULT_POLICY,
            {"providers": {"claude": {"enabled": True, "allowedRepos": ["OWNER/REPO"]}}},
        )
        self.guard.configure_policy(policy)

        result = self.guard.pre_claude(dict(self.base_state), False, True)

        self.assertTrue(result["allow_trigger"])
        self.assertEqual("@claude review once", result["comment_body"].splitlines()[0])

    def test_recent_trigger_is_in_progress_before_timeout(self) -> None:
        state = dict(self.base_state)
        state["comments"] = [self.comment("human", "@codex review", minutes_ago=2)]

        result = self.guard.classify_state(state, "codex", timeout_minutes=30)

        self.assertEqual("in_progress", result["status"])

    def test_old_trigger_without_bot_evidence_is_silent_timeout(self) -> None:
        state = dict(self.base_state)
        state["comments"] = [self.comment("human", "@codex review", minutes_ago=60)]

        result = self.guard.classify_state(state, "codex", timeout_minutes=30)

        self.assertEqual("silent_timeout", result["status"])

    def test_bot_no_findings_with_head_sha_is_verified(self) -> None:
        state = dict(self.base_state)
        state["comments"] = [
            self.comment("human", "@codex review", minutes_ago=10, comment_id=10),
            self.comment(
                "chatgpt-codex-connector[bot]",
                "Codex Review: Didn't find any major issues.\n\nReviewed commit: `abcdef1234`",
                minutes_ago=5,
                comment_id=11,
            ),
        ]

        result = self.guard.classify_state(state, "codex", timeout_minutes=30)

        self.assertEqual("review_completed_no_findings", result["status"])

    def test_generic_bot_comment_without_head_evidence_is_unverified(self) -> None:
        state = dict(self.base_state)
        state["comments"] = [self.comment("chatgpt-codex-connector[bot]", "Looks good.", minutes_ago=5)]

        result = self.guard.classify_state(state, "codex", timeout_minutes=30)

        self.assertEqual("generic_unverified", result["status"])

    def test_policy_json_has_no_enabled_claude_repos_by_default(self) -> None:
        policy_path = REPO_ROOT / "skills" / "github-pr-review-policy" / "references" / "review-policy.json"
        policy = json.loads(policy_path.read_text())

        self.assertFalse(policy["providers"]["claude"]["enabled"])
        self.assertEqual([], policy["providers"]["claude"]["allowedRepos"])

    def test_user_policy_path_precedes_skill_default(self) -> None:
        self.assertTrue(str(self.guard.USER_POLICY_PATH).endswith(".config/github-pr-review-policy/review-policy.json"))

    def test_base_guidance_allows_normal_branch(self) -> None:
        policy = self.guard.merge_dict(
            self.guard.DEFAULT_POLICY,
            {"repositories": {"OWNER/REPO": {"pullRequestBaseGuidance": {"normalBases": ["main"]}}}},
        )
        self.guard.configure_policy(policy)

        guidance = self.guard.base_branch_guidance(dict(self.base_state))

        self.assertEqual("normal", guidance["status"])
        self.assertEqual("none", guidance["severity"])

    def test_vibe_base_is_informational_not_blocking(self) -> None:
        policy = self.guard.merge_dict(
            self.guard.DEFAULT_POLICY,
            {
                "repositories": {
                    "OWNER/REPO": {
                        "pullRequestBaseGuidance": {
                            "normalBases": ["main"],
                            "informationalBases": {
                                "vibe": "Vibe is an optional direct-deploy branch."
                            },
                        }
                    }
                }
            },
        )
        self.guard.configure_policy(policy)
        state = dict(self.base_state)
        state["base_ref"] = "vibe"

        result = self.guard.pre_codex(state, emit_comment_body=False)

        self.assertTrue(result["allow_trigger"])
        self.assertEqual("informational", result["base_branch_guidance"]["status"])
        self.assertEqual("info", result["base_branch_guidance"]["severity"])

    def test_stage_base_is_promotion_only_not_blocking(self) -> None:
        policy = self.guard.merge_dict(
            self.guard.DEFAULT_POLICY,
            {
                "repositories": {
                    "OWNER/REPO": {
                        "pullRequestBaseGuidance": {
                            "normalBases": ["main"],
                            "promotionOnlyBases": {
                                "stage": "Stage is a deployment promotion target."
                            },
                        }
                    }
                }
            },
        )
        self.guard.configure_policy(policy)
        state = dict(self.base_state)
        state["base_ref"] = "stage"

        result = self.guard.pre_codex(state, emit_comment_body=False)

        self.assertTrue(result["allow_trigger"])
        self.assertEqual("promotion_only", result["base_branch_guidance"]["status"])
        self.assertEqual("warning", result["base_branch_guidance"]["severity"])

    def test_public_files_do_not_contain_private_repo_names(self) -> None:
        forbidden = [value.strip() for value in os.environ.get("PR_REVIEW_POLICY_FORBIDDEN_TEXT", "").split(",")]
        forbidden = [value for value in forbidden if value]
        if not forbidden:
            self.skipTest("Set PR_REVIEW_POLICY_FORBIDDEN_TEXT to scan for private terms")

        text = "\n".join(
            path.read_text(errors="ignore")
            for path in REPO_ROOT.rglob("*")
            if path.is_file()
            and ".git" not in path.parts
            and "__pycache__" not in path.parts
            and path.suffix not in {".pyc", ".zip"}
        )

        for value in forbidden:
            self.assertNotIn(value, text)


if __name__ == "__main__":
    unittest.main()
