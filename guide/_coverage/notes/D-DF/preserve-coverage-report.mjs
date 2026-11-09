// Keep verify's generated coverage report inside the wave's authorised working notes.
import fs from 'node:fs';
import { syncBuiltinESMExports } from 'node:module';
import { fileURLToPath } from 'node:url';
const report = fileURLToPath(new URL('./uncovered.md', import.meta.url));
const write = fs.writeFileSync;
fs.writeFileSync = function (path, ...args) {
  const target = String(path).endsWith('/guide/_coverage/inventory/uncovered.md') ? report : path;
  return write.call(this, target, ...args);
};
syncBuiltinESMExports();
