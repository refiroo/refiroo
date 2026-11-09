// Run the existing checker without writing another wave's inventory report.
const fs = require('node:fs');
const path = require('node:path');
const { syncBuiltinESMExports } = require('node:module');
const originalWrite = fs.writeFileSync;
const root = process.cwd();
fs.writeFileSync = function(file, ...args) {
  if (path.resolve(String(file)) !== path.join(root, '_coverage/inventory/uncovered.md')) {
    throw new Error('Unexpected coverage write: ' + String(file));
  }
  return originalWrite.call(this, path.join(root, '_coverage/notes/D-ABOUT/coverage-uncovered.md'), ...args);
};
syncBuiltinESMExports();
