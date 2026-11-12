// Keep verify's generated coverage report inside this wave's permitted notes directory.
import fs from 'node:fs';
import { syncBuiltinESMExports } from 'node:module';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
const directory = fileURLToPath(new URL('.', import.meta.url));
const destination = resolve(directory, 'uncovered.md');
const source = resolve(directory, '../../inventory/uncovered.md');
const original = fs.writeFileSync;
fs.writeFileSync = function (path, ...args) {
  const candidate = path instanceof URL ? fileURLToPath(path) : typeof path === 'string' ? resolve(path) : null;
  return original.call(this, candidate === source ? destination : path, ...args);
};
syncBuiltinESMExports();
