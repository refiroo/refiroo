import { chromium } from '/Users/krisztian/Documents/Projects/rdm-engine/frontend/node_modules/playwright/index.mjs';
import fs from 'node:fs';
import readline from 'node:readline';
const browser = await chromium.connect('ws://127.0.0.1:51548/eafaad2d1dbe56f94a543ee4d3347c04');
const page = await (await browser.newContext({viewport:{width:1280,height:900}})).newPage();
const context = page.context();
page.setDefaultTimeout(2500);
const env = names => Object.fromEntries(fs.readFileSync('guide/reference/.env','utf8').split('\n').filter(l=>names.some(n=>l.startsWith(n+'='))).map(l=>{const p=l.indexOf('=');return [l.slice(0,p),l.slice(p+1).replace(/^['"]|['"]$/g,'')]}));
const snap = async name => {await page.screenshot({path:'guide/_coverage/notes/C11-READER2/'+name+'.png',fullPage:true}); console.log(await page.locator('body').innerText());};
console.log('READY');
for await (const line of readline.createInterface({input:process.stdin})) {try { const r=await eval('(async()=>{'+line+'})()');if(r!==undefined)console.log(r);}catch(e){console.log(e.message);}console.log('DONE');}
await browser.close();
