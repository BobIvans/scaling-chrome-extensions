# Counterfactual Action Preview
V1 deterministic: for every consequential candidate observe current DOM/AX/UIA/tool state, estimate structural delta from capability contract, validate target/resources, compare expected postcondition, reject candidates that cannot help.
V2 optional learned predictor: state abstraction + semantic action → next-state abstraction. It ranks only; never grants authority.

Before MESSAGE_SEND/GITHUB_WRITE/INSTALL_UPDATE/delete/financial-like effect: exact identity → fresh re-observation → draft/readback if relevant → preview → deterministic gate → dispatch once → reconcile. Prediction/observation mismatch creates FailureEdge and lowers reliability.
