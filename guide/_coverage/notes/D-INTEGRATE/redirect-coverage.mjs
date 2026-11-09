// Redirect only the coverage report; shared inventory and the checker remain unchanged.
import fs from 'node:fs';
import { syncBuiltinESMExports } from 'node:module';
import { fileURLToPath } from 'node:url';
const report = fileURLToPath(new URL('./uncovered.md', import.meta.url));
const write = fs.writeFileSync;
fs.writeFileSync = function (file, ...args) {
  const target = String(file).endsWith('/_coverage/inventory/uncovered.md') ? report : file;
  return write.call(this, target, ...args);
};
syncBuiltinESMExports();
