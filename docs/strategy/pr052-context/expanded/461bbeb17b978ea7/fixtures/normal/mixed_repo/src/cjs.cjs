const actual = require("./value.ts");
function shadow(require) { return require("not-a-module"); }
require(process.env.MOD);
