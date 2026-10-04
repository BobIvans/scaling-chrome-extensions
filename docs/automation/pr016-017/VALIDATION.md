# Validation of the combined baseline

Local Linux, Python 3.12.14, Node 24.19.0:

| Command | Result | Scope |
|---|---|---|
| `python -m unittest discover -s content-lab -p 'test_*.py' -q` | 304 PASS | Real Git/SQLite, synthetic corpus; 125000-file inventory fixture |
| `python -m unittest discover -s desktop/tests -p 'test_*.py' -q` | 30 tests, PASS, 2 skipped | Real Native IPC, synthetic PCM; Tk display unavailable locally |
| `node --test agent-bridge/*.test.mjs` | 47 PASS | Native bridge regression |
| `node --test one-click-context/tests/*.test.*` | 116 PASS | Existing browser extension regression |
| `python -m unittest discover -s agent-bridge -p test_qualification_adapter.py -q` | 8 PASS | Existing qualification adapter contracts |

New action tests cover revision/policy/STOP fences, immutable 257-part ledger,
21-part delivery, loss of acknowledgement and restart without a duplicate send,
unknown-effect cancellation, wrong target/focus, frozen goal prompt, coverage
version checks, independent skill candidate/receipt/stale states, eligible source
namespace and optimizer keeping the new version unqualified. Browser transport
doubles test admission and quoting, not real DOM event semantics or actual UI.

The existing deterministic-core CI runs full Python/Node suites on Ubuntu and
Windows, with Xvfb for Linux Tk. CI success does not qualify a real microphone,
provider account, vendor integration, Windows installed packaging or live Grok UI.

All 220 original criterion rows remain OPEN. Function BASELINE/PARTIAL statuses
describe code presence, not whole-criterion acceptance. No automatic model result
or operator receipt self-promotes the entire strategy to DONE.
