# External R&D synthesis — 2026-10-06

## Hybrid structured perception
Microsoft UFO² frames Windows automation as a Desktop AgentOS using UIA/native application interfaces with visual fallback. Direction for us: semantic structure first; vision fallback/cross-check.

## Exact browser/native surface identity
Cua Driver work demonstrates combining typed CDP browser state/actions with native window/accessibility and background browser control. Direction: bind process/window ↔ browser target/tab/document in one SurfaceGraph.

## WebMCP
Chrome WebMCP lets pages expose typed tools with names/descriptions/JSON schemas. Security guidance treats tool manifests/outputs as untrusted content vulnerable to indirect prompt injection. Direction: discover WebMCP before clicking, but keep authority/effect policy local.

## Demonstrations and trajectories
OpenCUA/AgentNet emphasizes synchronized UI/action trajectories and demonstration data. Direction: Teach mode → immutable trajectory → semantic recipe → replay/canary → skill.

## Typed System-1 rail
Jev ecosystem exposes Choice/Score/Noul. Community browser implementations feed exact allowed actions/DOM state to Jev and let code own the loop. Direction: Laya chooses among deterministic candidate IDs and never invents commands/permissions.

## GUI models
OpenCUA/UI-TARS/OmniParser-like approaches are useful for fallback visual grounding, but structured/browser/native routes should remain preferred for reliability/cost on modest local hardware.

## Repair ownership
Agent failures should be localized to observer/model/rail/provider/executor/memory/environment/verifier edges so the correct component is repaired.

## Earlier topology idea
The exact named “Lepton + Hugging Face Text-to-Topology DOM encoder” project from earlier R&D was not verified. Preserve the underlying topology-aware idea, but ground production implementation in DOM/AX/CDP/UIA/WebMCP; learned graph encoders remain optional experiments.
