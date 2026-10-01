import json
from pathlib import Path
import tempfile
import unittest

import openai_responses_adapter as oa
import provider_budget as pb


class ResponsesAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Path(self.temp.name) / "store"
        self.profile = {"schema": "occ.openai-responses-profile.v1",
                        "model": "gpt-test", "api_key_env": "OCC_OPENAI_API_KEY",
                        "timeout_seconds": 10, "max_response_bytes": 100_000}
        self.request = {"schema": "occ.openai-responses-request.v1",
                        "input": "hello", "instructions": "answer briefly",
                        "max_output_tokens": 50, "store": False}
        self.plan = {"schema": "occ.provider-budget.v1", "budget_id": "run-1",
                     "currency": "USD_MICRO", "hard_cap_microunits": 100,
                     "max_attempts": 2}
        pb.initialize_budget_store(self.store)

    def tearDown(self):
        self.temp.cleanup()

    def response(self):
        return {"id": "resp_fixture", "object": "response", "status": "completed",
                "model": "gpt-test", "output": [{"type": "message", "content": [
                    {"type": "output_text", "text": "hello back"}]}],
                "usage": {"input_tokens": 2, "output_tokens": 3, "total_tokens": 5}}

    def invoke(self, transport, **extra):
        return oa.execute(self.profile, self.request, store=self.store,
                          budget_plan=self.plan, op_key=extra.pop("op_key", "call-1"),
                          reserve_microunits=50,
                          environ=extra.pop("environ", {"OCC_OPENAI_API_KEY": "secret"}),
                          transport=transport, **extra)

    def test_native_request_backend_secret_and_success_needs_cost_reconciliation(self):
        observed = {}

        def transport(url, headers, payload, timeout, maximum, cancelled):
            observed.update(url=url, headers=headers, body=json.loads(payload),
                            timeout=timeout, maximum=maximum, cancelled=cancelled())
            return 200, {}, json.dumps(self.response()).encode()

        result = self.invoke(transport)
        self.assertEqual(observed["url"], "https://api.openai.com/v1/responses")
        self.assertEqual(observed["body"], {"model": "gpt-test", "input": "hello",
                         "instructions": "answer briefly", "max_output_tokens": 50,
                         "store": False})
        self.assertEqual(observed["headers"]["Authorization"], "Bearer secret")
        self.assertEqual(result["state"], "DONE_REQUIRES_COST_RECONCILIATION")
        self.assertEqual(result["output_text"], "hello back")
        self.assertEqual(result["budget"]["state"], "NEEDS_RECONCILIATION")
        self.assertNotIn("secret", json.dumps(result))

    def test_zero_budget_blocks_before_secret_or_transport(self):
        class Guard(dict):
            def get(self, key, default=None):  # noqa: ARG002
                raise AssertionError("secret environment read")
        self.plan["hard_cap_microunits"] = 0
        with self.assertRaisesRegex(ValueError, "ZERO_BUDGET"):
            self.invoke(lambda *args: self.fail("transport called"), environ=Guard())

    def test_missing_secret_releases_without_send(self):
        result = self.invoke(lambda *args: self.fail("transport called"), environ={})
        self.assertEqual((result["state"], result["reason"], result["request_sent"]),
                         ("BLOCKED", "OPENAI_API_KEY_MISSING", False))
        self.assertEqual(result["budget"]["state"], "RELEASED")
        self.assertEqual(pb.budget_status(self.store, "run-1")["reserved_microunits"], 0)

    def test_401_is_terminal_zero_settlement_without_error_text(self):
        body = {"error": {"type": "invalid_request_error", "code": "invalid_api_key",
                          "message": "private provider detail"}}
        result = self.invoke(lambda *args: (401, {}, json.dumps(body).encode()))
        self.assertEqual((result["reason"], result["retryable"]),
                         ("AUTHENTICATION_FAILED", False))
        self.assertEqual(result["budget"]["actual_microunits"], 0)
        self.assertNotIn("private provider detail", json.dumps(result))

    def test_429_distinguishes_retryable_rate_limit_from_permanent_quota(self):
        rate = {"error": {"type": "rate_limit_error", "code": "slow_down"}}
        first = self.invoke(lambda *args: (429, {"Retry-After": "17"},
                                           json.dumps(rate).encode()), op_key="rate")
        self.assertEqual((first["retryable"], first["retry_after_seconds"]), (True, 17))
        quota = {"error": {"type": "insufficient_quota",
                           "code": "project_spend_limit_exceeded"}}
        second = self.invoke(lambda *args: (429, {}, json.dumps(quota).encode()),
                             op_key="quota")
        self.assertEqual((second["retryable"], second["retry_after_seconds"]),
                         (False, None))

    def test_cancel_before_and_after_send_have_different_budget_states(self):
        before = self.invoke(lambda *args: (_ for _ in ()).throw(
            oa.TransportCancelled(request_sent=False)), op_key="before")
        self.assertEqual((before["state"], before["budget"]["state"]),
                         ("CANCELLED", "RELEASED"))
        after = self.invoke(lambda *args: (_ for _ in ()).throw(
            oa.TransportCancelled(request_sent=True)), op_key="after")
        self.assertEqual((after["state"], after["budget"]["state"]),
                         ("CANCELLED", "NEEDS_RECONCILIATION"))

    def test_reservation_replay_never_dispatches_twice(self):
        pb.reserve_budget(self.store, self.plan, "call-1", 50)
        result = self.invoke(lambda *args: self.fail("replayed transport called"))
        self.assertEqual(result["reason"], "RESERVATION_REPLAY_BLOCKED")
        self.assertEqual(result["budget"]["state"], "NEEDS_RECONCILIATION")

    def test_strict_schemas_and_invalid_success_fail_closed(self):
        for profile in ({**self.profile, "api_key_env": "OPENAI_API_KEY"},
                        {**self.profile, "endpoint": "https://evil.invalid"}):
            with self.assertRaises(oa.AdapterBlocked):
                oa.build_request(profile, self.request)
        for request in ({**self.request, "store": True},
                        {**self.request, "tools": []},
                        {**self.request, "max_output_tokens": True}):
            with self.assertRaises(oa.AdapterBlocked):
                oa.build_request(self.profile, request)
        invalid = self.response()
        invalid["model"] = "foreign-model"
        with self.assertRaisesRegex(oa.AdapterBlocked, "RESPONSE_SCHEMA"):
            self.invoke(lambda *args: (200, {}, json.dumps(invalid).encode()))
        self.assertEqual(pb.budget_status(self.store, "run-1")["reserved_microunits"], 50)

    def test_malformed_json_and_unexpected_transport_are_quarantined(self):
        with self.assertRaisesRegex(oa.AdapterBlocked, "JSON_INVALID"):
            self.invoke(lambda *args: (200, {}, b"not-json"), op_key="json")
        with self.assertRaisesRegex(oa.AdapterBlocked, "TRANSPORT_FAILED"):
            self.invoke(lambda *args: (_ for _ in ()).throw(RuntimeError("private")),
                        op_key="transport")
        states = {item["op_key"]: item["state"] for item in
                  pb.budget_status(self.store, "run-1")["operations"]}
        self.assertEqual(states, {"json": "NEEDS_RECONCILIATION",
                                  "transport": "NEEDS_RECONCILIATION"})


if __name__ == "__main__":
    unittest.main()
