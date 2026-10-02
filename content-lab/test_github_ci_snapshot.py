import json
import os
from pathlib import Path
import tempfile
import unittest

import github_ci_snapshot as ci


class GitHubCISnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.snapshot = self.root / "ci.json"
        self.head = "a" * 40
        self.policy = {"repos": {"occ": {"ci": {
            "snapshot_file": str(self.snapshot),
            "required_checks": ["core (ubuntu-latest)", "core (windows-latest)"],
            "transport": {
                "kind": "github_check_runs_v1",
                "repository": "BobIvans/scaling-chrome-extensions",
                "token_env": "OCC_GITHUB_TOKEN",
                "timeout_seconds": 7,
                "max_pages": 2,
            },
        }}}}

    def tearDown(self):
        self.temp.cleanup()

    def check(self, name, number, *, head=None, status="completed", conclusion="success", app="github-actions"):
        return {"name": name, "id": number, "status": status, "conclusion": conclusion,
                "check_suite": {"head_sha": head or self.head}, "app": {"slug": app}}

    def test_exact_actions_checks_are_atomically_written_without_token(self):
        seen = []

        def requester(url, token, timeout):
            seen.append((url, token, timeout))
            runs = [
                self.check("core (ubuntu-latest)", 20),
                self.check("core (ubuntu-latest)", 30, conclusion="failure"),
                self.check("core (windows-latest)", 21),
                self.check("core (ubuntu-latest)", 40, head="b" * 40),
                self.check("core (windows-latest)", 41, app="other-app"),
                self.check("unregistered", 42),
            ]
            return {"total_count": len(runs), "check_runs": runs}

        result = ci.refresh(self.policy, "occ", self.head,
                            environ={"OCC_GITHUB_TOKEN": "private-token"}, requester=requester)
        value = json.loads(self.snapshot.read_text(encoding="utf-8"))
        self.assertEqual(result["state"], "DONE")
        self.assertEqual([check["run_id"] for check in value["checks"]], [20, 30, 21])
        self.assertEqual(value["origin"], "authenticated_github_check_runs_v1")
        self.assertEqual(value["transport_status"], "OBSERVED")
        self.assertNotIn("private-token", self.snapshot.read_text(encoding="utf-8"))
        self.assertIn(f"/commits/{self.head}/check-runs?filter=all&per_page=100&page=1", seen[0][0])
        self.assertEqual(seen[0][1:], ("private-token", 7))
        if os.name != "nt":
            self.assertEqual(self.snapshot.stat().st_mode & 0o777, 0o600)

    def test_missing_token_replaces_stale_green_with_blocked_snapshot(self):
        self.snapshot.write_text('{"stale":"green"}', encoding="utf-8")
        with self.assertRaisesRegex(ci.TransportBlocked, "GITHUB_TOKEN_MISSING"):
            ci.refresh(self.policy, "occ", self.head, environ={})
        value = json.loads(self.snapshot.read_text(encoding="utf-8"))
        self.assertEqual(value["transport_status"], "BLOCKED")
        self.assertEqual(value["transport_error"], "GITHUB_TOKEN_MISSING")
        self.assertEqual(value["checks"], [])
        self.assertNotIn("stale", value)

    def test_revoked_access_fails_closed_without_response_or_credential(self):
        def denied(url, token, timeout):  # noqa: ARG001
            raise ci.TransportBlocked("GITHUB_AUTH_FAILED")

        with self.assertRaisesRegex(ci.TransportBlocked, "GITHUB_AUTH_FAILED"):
            ci.refresh(self.policy, "occ", self.head,
                       environ={"OCC_GITHUB_TOKEN": "do-not-store"}, requester=denied)
        raw = self.snapshot.read_text(encoding="utf-8")
        self.assertNotIn("do-not-store", raw)
        self.assertEqual(json.loads(raw)["transport_error"], "GITHUB_AUTH_FAILED")

    def test_bounded_pagination_reaches_required_checks(self):
        pages = []

        def requester(url, token, timeout):  # noqa: ARG001
            page = int(url.rsplit("=", 1)[1])
            pages.append(page)
            if page == 1:
                runs = [self.check("unregistered", number) for number in range(1, 101)]
            else:
                runs = [self.check("core (ubuntu-latest)", 101),
                        self.check("core (windows-latest)", 102)]
            return {"total_count": 102, "check_runs": runs}

        ci.refresh(self.policy, "occ", self.head,
                   environ={"OCC_GITHUB_TOKEN": "token"}, requester=requester)
        self.assertEqual(pages, [1, 2])
        self.assertEqual(len(json.loads(self.snapshot.read_text())["checks"]), 2)

    def test_page_limit_fails_closed(self):
        self.policy["repos"]["occ"]["ci"]["transport"]["max_pages"] = 1

        def requester(url, token, timeout):  # noqa: ARG001
            return {"total_count": 101,
                    "check_runs": [self.check("unregistered", number) for number in range(1, 101)]}

        with self.assertRaisesRegex(ci.TransportBlocked, "PAGE_LIMIT"):
            ci.refresh(self.policy, "occ", self.head,
                       environ={"OCC_GITHUB_TOKEN": "token"}, requester=requester)
        value = json.loads(self.snapshot.read_text())
        self.assertEqual(value["transport_status"], "BLOCKED")
        self.assertEqual(value["checks"], [])

    def test_wrong_head_and_foreign_app_cannot_satisfy_required_set(self):
        def requester(url, token, timeout):  # noqa: ARG001
            runs = [self.check("core (ubuntu-latest)", 1, head="f" * 40),
                    self.check("core (windows-latest)", 2, app="foreign")]
            return {"total_count": 2, "check_runs": runs}

        ci.refresh(self.policy, "occ", self.head,
                   environ={"OCC_GITHUB_TOKEN": "token"}, requester=requester)
        value = json.loads(self.snapshot.read_text())
        self.assertEqual(value["transport_status"], "OBSERVED")
        self.assertEqual(value["checks"], [])

    def test_transport_rejects_unregistered_host_and_generic_secret_env(self):
        transport = self.policy["repos"]["occ"]["ci"]["transport"]
        transport["repository"] = "https://evil.invalid/repo"
        with self.assertRaisesRegex(ci.TransportBlocked, "REPOSITORY"):
            ci.refresh(self.policy, "occ", self.head, environ={})
        transport["repository"] = "owner/repo"
        transport["token_env"] = "AWS_SECRET_ACCESS_KEY"
        with self.assertRaisesRegex(ci.TransportBlocked, "TOKEN_ENV"):
            ci.refresh(self.policy, "occ", self.head, environ={})


if __name__ == "__main__":
    unittest.main()
