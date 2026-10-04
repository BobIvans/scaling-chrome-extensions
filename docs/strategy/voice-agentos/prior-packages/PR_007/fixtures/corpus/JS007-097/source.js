	// fake: import x from "./wrong.js"
const pending = import("./util.js");
export function caller() { return 1; }
