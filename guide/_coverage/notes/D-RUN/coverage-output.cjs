const fs = require("node:fs");
const path = require("node:path");
const original = fs.writeFileSync;
const shared = path.resolve("_coverage/inventory/uncovered.md");
fs.writeFileSync = function(file, ...args) {
  const target = path.resolve(String(file)) === shared ? path.resolve("_coverage/notes/D-RUN/uncovered.md") : file;
  return original.call(this, target, ...args);
};
require("node:module").syncBuiltinESMExports();
