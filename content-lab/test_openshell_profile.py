import copy
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

import openshell_profile as osp


class OpenShellProfileTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parent
        self.profile = json.loads((root / "openshell-openai-profile.example.json").read_text())
        self.review = json.loads((root / "openshell-review.example.json").read_text())

    def test_review_is_explicitly_static_and_wsl2_experimental(self):
        result = osp.qualify(self.profile, self.review)
        self.assertEqual(result["state"], "STATICALLY_REVIEWED_RUNTIME_UNQUALIFIED")
        self.assertFalse(result["runnable"])
        self.assertEqual(result["support_status"],
                         "EXPERIMENTAL_NOT_RUNTIME_QUALIFIED")
        self.assertEqual(result["runtime_smoke"], "NOT_RUN")
        self.assertEqual(result["provider_api_budget"], 0)

    def test_wrong_native_endpoint_is_denied(self):
        for field, value in (("host", "proxy.example"), ("port", 8443),
                             ("path", "/v1/chat/completions"),
                             ("protocol", "tcp")):
            profile = copy.deepcopy(self.profile)
            profile["endpoints"][0][field] = value
            with self.assertRaisesRegex(osp.ProfileBlocked, "ENDPOINT_BINDING"):
                osp.qualify(profile, self.review)

    def test_review_cannot_claim_a_different_endpoint(self):
        review = copy.deepcopy(self.review)
        review["native_request_url"] = "https://api.openai.com/v1/chat/completions"
        with self.assertRaisesRegex(osp.ProfileBlocked, "ENDPOINT_MISMATCH"):
            osp.qualify(self.profile, review)

    def test_binary_is_exact_and_wildcards_are_denied(self):
        for binary in ("/**", "/opt/occ/bin/*", "/usr/bin/python3", "python3"):
            profile = copy.deepcopy(self.profile)
            profile["binaries"] = [binary]
            with self.assertRaisesRegex(osp.ProfileBlocked, "BINARY_BINDING"):
                osp.qualify(profile, self.review)

    def test_rest_rule_cannot_be_relaxed(self):
        variants = []
        for key, value in (("enforcement", "audit"),
                           ("allow_uninspected_credentials", True)):
            item = copy.deepcopy(self.profile)
            item["endpoints"][0][key] = value
            variants.append(item)
        for method, path in (("*", "/v1/**"), ("GET", "/v1/responses"),
                             ("POST", "/v1/**")):
            item = copy.deepcopy(self.profile)
            item["endpoints"][0]["rules"][0]["allow"] = {
                "method": method, "path": path}
            variants.append(item)
        for profile in variants:
            with self.assertRaisesRegex(osp.ProfileBlocked, "ENDPOINT_BINDING"):
                osp.qualify(profile, self.review)

    def test_attachment_and_platform_status_are_required(self):
        for key, value in (("provider_attachment_required", False),
                           ("support_status", "SUPPORTED"),
                           ("runtime_smoke", "PASS"),
                           ("platform", "windows-native-x86_64")):
            review = copy.deepcopy(self.review)
            review[key] = value
            with self.assertRaises(osp.ProfileBlocked):
                osp.qualify(self.profile, review)

    def test_profile_has_declarations_not_secret_values(self):
        credential = self.profile["credentials"][0]
        self.assertEqual(set(credential),
                         {"name", "env_vars", "required", "auth_style"})
        profile = copy.deepcopy(self.profile)
        profile["credentials"][0]["value"] = "secret"
        with self.assertRaisesRegex(osp.ProfileBlocked, "CREDENTIAL_DECLARATION"):
            osp.qualify(profile, self.review)

    def test_cli_emits_sanitized_result_and_fail_closed_code(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            profile_path, review_path = root / "profile.json", root / "review.json"
            profile_path.write_text(json.dumps(self.profile))
            review_path.write_text(json.dumps(self.review))
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = osp.main(["--profile", str(profile_path),
                                 "--review", str(review_path)])
            self.assertEqual(code, 0)
            self.assertTrue(json.loads(output.getvalue())["ok"])
            bad = copy.deepcopy(self.profile)
            bad["endpoints"][0]["host"] = "wrong.example"
            profile_path.write_text(json.dumps(bad))
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = osp.main(["--profile", str(profile_path),
                                 "--review", str(review_path)])
            self.assertEqual(code, 2)
            self.assertEqual(json.loads(output.getvalue()),
                             {"ok": False,
                              "error": "OPENSHELL_NATIVE_ENDPOINT_BINDING"})


if __name__ == "__main__":
    unittest.main()
