import { chromium } from '/Users/krisztian/Documents/Projects/rdm-engine/frontend/node_modules/playwright/index.mjs';
import readline from 'node:readline';
import fs from 'node:fs/promises';
const browser = await chromium.connect('ws://127.0.0.1:61382/adf454a106b6f408d64ad8d51e826caf');
const context = await browser.newContext({viewport:{width:1280,height:900}});
const page = await context.newPage();
const noteDir='/Users/krisztian/Documents/Projects/rdm-engine/guide/_coverage/notes/C11-READER2-AI/';
const rl=readline.createInterface({input:process.stdin,output:process.stdout,terminal:false});
console.log('READY');
for await (const line of rl) { try {const result=await eval(`(async()=>{${line}})()`); if(result!==undefined) console.log(typeof result==='string'?result:JSON.stringify(result));} catch(e){console.log('ERROR',e.message);} console.log('DONE'); }
await context.close(); await browser.close();
