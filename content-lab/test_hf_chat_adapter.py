import json
from pathlib import Path
import tempfile
import unittest

import hf_chat_adapter as hf
import provider_budget as pb


class HFChatAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Path(self.temp.name) / "store"
        self.profile = {"schema": "occ.hf-chat-profile.v1",
                        "api_token_env": "OCC_HF_TOKEN",
                        "models": [{"alias": "writer",
                                    "route": "Example/Model:fixed-provider",
                                    "response_model": "Example/Model"}],
                        "timeout_seconds": 10, "max_response_bytes": 100_000}
        self.request = {"schema": "occ.hf-chat-request.v1",
                        "model_alias": "writer",
                        "messages": [{"role": "user", "content": "hello"}],
                        "max_tokens": 50, "stream": False}
        self.plan = {"schema": "occ.provider-budget.v1", "budget_id": "run-hf",
                     "currency": "USD_MICRO", "hard_cap_microunits": 200,
                     "max_attempts": 2}
        pb.initialize_budget_store(self.store)

    def tearDown(self):
        self.temp.cleanup()

    def response(self):
        return {"id": "chatcmpl-fixture", "object": "chat.completion",
                "model": "Example/Model", "choices": [{"index": 0,
                "message": {"role": "assistant", "content": "hello back"},
                "finish_reason": "stop"}], "usage": {"prompt_tokens": 2,
                "completion_tokens": 3, "total_tokens": 5}}

    def invoke(self, transport, **extra):
        return hf.execute(self.profile, self.request, store=self.store,
                          budget_plan=self.plan, op_key=extra.pop("op_key", "call-1"),
                          reserve_microunits=50,
                          environ=extra.pop("environ", {"OCC_HF_TOKEN": "secret"}),
                          transport=transport, **extra)

    def test_registry_pins_endpoint_provider_and_native_chat_schema(self):
        observed = {}

        def transport(url, headers, payload, timeout, maximum, cancelled):
            observed.update(url=url, headers=headers, body=json.loads(payload),
                            timeout=timeout, maximum=maximum, cancelled=cancelled())
            return 200, {}, json.dumps(self.response()).encode()

        result = self.invoke(transport)
        self.assertEqual(observed["url"], hf.API_URL)
        self.assertEqual(observed["body"]["model"], "Example/Model:fixed-provider")
        self.assertEqual(observed["body"]["stream"], False)
        self.assertEqual(observed["headers"]["Authorization"], "Bearer secret")
        self.assertNotIn("X-HF-Bill-To", observed["headers"])
        self.assertEqual(result["state"], "DONE_REQUIRES_COST_RECONCILIATION")
        self.assertEqual(result["output_text"], "hello back")
        self.assertEqual(result["budget"]["state"], "NEEDS_RECONCILIATION")
        self.assertFalse(result["fallback_attempted"])
        self.assertNotIn("secret", json.dumps(result))

    def test_registry_rejects_auto_routes_unknown_alias_and_schema_drift(self):
        for route in ("Example/Model", "Example/Model:fastest",
                      "Example/Model:cheapest", "Example/Model:auto"):
            profile = {**self.profile, "models": [{"alias": "writer", "route": route,
                       "response_model": "Example/Model"}]}
            with self.assertRaises(hf.AdapterBlocked):
                hf.build_request(profile, self.request)
        with self.assertRaisesRegex(hf.AdapterBlocked, "UNREGISTERED"):
            hf.build_request(self.profile, {**self.request, "model_alias": "other"})
        for request in ({**self.request, "stream": True},
                        {**self.request, "tools": []},
                        {**self.request, "max_tokens": True}):
            with self.assertRaises(hf.AdapterBlocked):
                hf.build_request(self.profile, request)

    def test_zero_budget_blocks_before_token_or_transport(self):
        class Guard(dict):
            def get(self, key, default=None):  # noqa: ARG002
                raise AssertionError("token environment read")
        self.plan["hard_cap_microunits"] = 0
        with self.assertRaisesRegex(ValueError, "ZERO_BUDGET"):
            self.invoke(lambda *args: self.fail("transport called"), environ=Guard())

    def test_missing_token_releases_without_send(self):
        result = self.invoke(lambda *args: self.fail("transport called"), environ={})
        self.assertEqual((result["reason"], result["request_sent"],
                          result["budget"]["state"]),
                         ("HF_TOKEN_MISSING", False, "RELEASED"))

    def test_quota_exhaustion_stops_without_retry_or_fallback(self):
        calls = []

        def transport(*args):
            calls.append(args[0])
            return 402, {}, json.dumps({"error": {"type": "payment_required",
                                                  "message": "private"}}).encode()

        result = self.invoke(transport)
        self.assertEqual(calls, [hf.API_URL])
        self.assertEqual((result["reason"], result["retryable"],
                          result["fallback_attempted"]),
                         ("HF_QUOTA_OR_RATE_LIMIT_STOP", False, False))
        self.assertEqual(result["budget"]["actual_microunits"], 0)
        self.assertNotIn("private", json.dumps(result))

    def test_401_and_429_are_terminal_without_model_fallback(self):
        auth = self.invoke(lambda *args: (401, {}, json.dumps(
            {"error": "private auth detail"}).encode()), op_key="auth")
        limited = self.invoke(lambda *args: (429, {"Retry-After": "1"}, json.dumps(
            {"error": {"type": "rate_limit", "code": "quota"}}).encode()),
            op_key="limited")
        self.assertEqual(auth["reason"], "AUTHENTICATION_FAILED")
        self.assertEqual(limited["reason"], "HF_QUOTA_OR_RATE_LIMIT_STOP")
        self.assertFalse(limited["retryable"])
        self.assertFalse(limited["fallback_attempted"])

    def test_cancel_before_and_after_send_have_different_budget_states(self):
        before = self.invoke(lambda *args: (_ for _ in ()).throw(
            hf.TransportCancelled(request_sent=False)), op_key="before")
        after = self.invoke(lambda *args: (_ for _ in ()).throw(
            hf.TransportCancelled(request_sent=True)), op_key="after")
        self.assertEqual(before["budget"]["state"], "RELEASED")
        self.assertEqual(after["budget"]["state"], "NEEDS_RECONCILIATION")

    def test_replay_malformed_and_unknown_transport_never_dispatch_twice(self):
        pb.reserve_budget(self.store, self.plan, "call-1", 50)
        replay = self.invoke(lambda *args: self.fail("replayed transport called"))
        self.assertEqual(replay["reason"], "RESERVATION_REPLAY_BLOCKED")
        with self.assertRaisesRegex(hf.AdapterBlocked, "JSON_INVALID"):
            self.invoke(lambda *args: (200, {}, b"not-json"), op_key="json")
        with self.assertRaisesRegex(hf.AdapterBlocked, "TRANSPORT_FAILED"):
            self.invoke(lambda *args: (_ for _ in ()).throw(RuntimeError("private")),
                        op_key="transport")
        states = {item["op_key"]: item["state"] for item in
                  pb.budget_status(self.store, "run-hf")["operations"]}
        self.assertEqual(states, {"call-1": "NEEDS_RECONCILIATION",
                                  "json": "NEEDS_RECONCILIATION",
                                  "transport": "NEEDS_RECONCILIATION"})

    def test_wrong_model_and_usage_fail_closed(self):
        wrong = self.response()
        wrong["model"] = "Other/Model"
        with self.assertRaisesRegex(hf.AdapterBlocked, "RESPONSE_SCHEMA"):
            self.invoke(lambda *args: (200, {}, json.dumps(wrong).encode()),
                        op_key="model")
        usage = self.response()
        usage["usage"]["total_tokens"] = 99
        with self.assertRaisesRegex(hf.AdapterBlocked, "USAGE_SCHEMA"):
            self.invoke(lambda *args: (200, {}, json.dumps(usage).encode()),
                        op_key="usage")


if __name__ == "__main__":
    unittest.main()
