// Compare coverage against this wave's starting text without rewriting any page.
import fs from 'node:fs';
import { syncBuiltinESMExports } from 'node:module';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
const directory = fileURLToPath(new URL('.', import.meta.url));
const root = resolve(directory, '../../../..');
const originalRead = fs.readFileSync;
const originalWrite = fs.writeFileSync;
const before = JSON.parse(originalRead(resolve(directory, 'before.json'), 'utf8'));
fs.readFileSync = function(path, ...args) {
  const candidate = typeof path === 'string' ? resolve(path) : null;
  const relative = candidate?.startsWith(root + '/') ? candidate.slice(root.length + 1) : null;
  if (relative && Object.hasOwn(before, relative)) return args[0] ? before[relative] : Buffer.from(before[relative]);
  return originalRead.call(this, path, ...args);
};
fs.writeFileSync = function(path, ...args) {
  const candidate = typeof path === 'string' ? resolve(path) : null;
  const destination = resolve(directory, '../../inventory/uncovered.md');
  return originalWrite.call(this, candidate === destination ? resolve(directory, 'before-uncovered.md') : path, ...args);
};
syncBuiltinESMExports();
