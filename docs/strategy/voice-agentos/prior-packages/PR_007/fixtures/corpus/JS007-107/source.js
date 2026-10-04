	// fake: import x from "./wrong.js"
const pending = import(choice);
export function caller() { return 1; }
