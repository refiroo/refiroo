for (const id of ['4dbadbb9-08ee-4c9d-a1d0-b7b40d8d6d48','6dc50190-2954-4c4e-a137-45b9b759d9c3','bbcd67f9-1af9-46db-af8b-ec945a17c6f1','a3e9769e-988f-4623-bb98-5565d8d5f9bb','fffee11a-95a3-4bcd-a2b2-2aeb3fe73a96','7f000a69-7475-4905-9744-0f7242bdb5bb','d47b220a-c8fd-4209-9ccc-6bcce560f223','280d6684-0d73-470f-9c94-1a483d5977c1']) {
 await page.goto('http://localhost:8480/settings/ai-tasks/'+id);
 await page.getByRole('button',{name:'Back to the workspace',exact:true}).waitFor({timeout:5000}).catch(()=>{});
 const body=await page.locator('main').innerText();
 await fs.writeFile(noteDir+'task-'+id+'.txt',body);
 console.log(id,body.slice(0,220),body.match(/\([^\n]*\d+ s[^\n]*\)/g));
}
