// Preserve the shared inventory report while running the unmodified guide checks.
import fs from 'node:fs';
import { syncBuiltinESMExports } from 'node:module';
import { fileURLToPath } from 'node:url';
const shared = fileURLToPath(new URL('../../inventory/uncovered.md', import.meta.url));
const owned = fileURLToPath(new URL('./uncovered.md', import.meta.url));
const write = fs.writeFileSync;
fs.writeFileSync = function (path, ...args) {
  return write.call(this, String(path) === shared ? owned : path, ...args);
};
syncBuiltinESMExports();
