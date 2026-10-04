# Benchmarks

Track per command:
- command_id
- transcript
- intent accuracy
- context precision/recall
- executor chosen
- executor fallback count
- success/failure
- verified postcondition
- latency: speech_end_to_start_ms
- latency: total_ms
- model tokens
- API cost
- local CPU/RAM
- retries
- rollback used
- human intervention
- provenance completeness

Core benchmark groups:
1. 50 known deterministic voice commands
2. 20 unknown tasks requiring skill birth
3. 20 browser workflows
4. 20 Windows multi-app workflows
5. 20 Studious-Pancake repo/qualification workflows
6. 10 crash/restart durability workflows
7. 10 intentionally broken primary-executor cases

Primary metric:
verified_success_rate = verified_successes / attempted_commands

Secondary:
cost_per_verified_success
p50/p95 latency
fallback recovery rate
context provenance coverage
regression retention rate
