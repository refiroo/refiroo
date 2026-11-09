// Keep the existing checker read-only outside this wave's ownership.
import fs from 'node:fs';
import { syncBuiltinESMExports } from 'node:module';
import { resolve } from 'node:path';
const report = resolve('_coverage/inventory/uncovered.md');
const ownReport = resolve('_coverage/notes/RV-GUIDE/uncovered.md');
const original = fs.writeFileSync;
fs.writeFileSync = function(path, ...args) {
  return original.call(this, resolve(String(path)) === report ? ownReport : path, ...args);
};
syncBuiltinESMExports();
