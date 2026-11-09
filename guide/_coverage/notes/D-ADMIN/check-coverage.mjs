// Run the repository checker unchanged, redirecting its shared generated report into
// this wave's allowed notes directory. Other waves own inventory/uncovered.md too.
import fs from 'node:fs';
import { syncBuiltinESMExports } from 'node:module';
import { fileURLToPath } from 'node:url';
const sharedReport = fileURLToPath(new URL('../../inventory/uncovered.md', import.meta.url));
const privateReport = fileURLToPath(new URL('./uncovered.md', import.meta.url));
const write = fs.writeFileSync;
fs.writeFileSync = function (path, ...args) {
  if (String(path) !== sharedReport) throw new Error(`Unexpected checker write: ${path}`);
  return write.call(fs, privateReport, ...args);
};
syncBuiltinESMExports();
process.argv[2] = 'coverage';
await import('../../../tools/check.mjs');
