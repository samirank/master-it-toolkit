const {spawn}=require('child_process'),path=require('path'),assert=require('assert'),fs=require('fs'),vm=require('vm');
const {chromium}=require(process.env.PLAYWRIGHT_PATH||'C:/Users/sam/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
(async()=>{
 const root=path.resolve(__dirname,'../../MASTER-IT-TOOLKIT'),scope={window:{}};
 for(const f of ['guides-data.js','workflows-data.js'])vm.runInNewContext(fs.readFileSync(path.join(root,'assets/js',f),'utf8'),scope);
 assert.equal(JSON.stringify(scope.window.TOOLKIT_WORKFLOWS),JSON.stringify(JSON.parse(fs.readFileSync(path.join(root,'assets/workflows.json'),'utf8'))));
 const catalog=JSON.parse(fs.readFileSync(path.join(root,'assets/toolkit-manifest.json'),'utf8'));
 for(const [id,w] of Object.entries(scope.window.TOOLKIT_WORKFLOWS)){
  assert.deepEqual(w.steps.map(s=>s.text),scope.window.TOOLKIT_CHECKLISTS[id].items);
  for(const step of w.steps)if(step.tool)assert(catalog.some(t=>t.id===step.tool&&t.kind==='Portable'));
 }
 const proc=spawn('python',['-u','-c',"import launcher; s=launcher.Server(port=0); print(s.origin+'/'+s.token+'/index.html',flush=True); s.serve_forever()"],{cwd:root});let browser;
 try{
  const url=await new Promise((resolve,reject)=>{proc.stdout.once('data',d=>resolve(d.toString().trim()));proc.once('error',reject);proc.stderr.on('data',d=>console.error(d.toString()));});
  browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
  let run;
  await page.route('**/api/run-options?tool=bcu',r=>r.fulfill({json:{files:[{name:'BCUninstaller.exe',path:'fixture/BCUninstaller.exe',fullPath:'D:\\fixture\\BCUninstaller.exe'}]}}));
  await page.route('**/api/action',r=>{const b=r.request().postDataJSON();if(b.action==='run-portable'){run=b;return r.fulfill({status:202,json:{message:'Fixture launch'}});}return r.continue();});
  await page.goto(url+'#tools');await page.locator('#search').fill('Bulk Crap Uninstaller');await page.locator('[data-run-tool="bcu"]').first().click();
  await page.waitForFunction(()=>!document.querySelector('dialog.download-dialog'));assert.equal(run.tool,'bcu');assert.equal(run.executable,'fixture/BCUninstaller.exe');
  await page.locator('[data-nav="checklists"]').first().click();await page.locator('[data-checklist="migration"]').click();await page.locator('[data-workflow="migration"]').click();
  await page.getByRole('button',{name:'Start · Manual launches',exact:true}).click();
  await page.getByRole('button',{name:'I verified this step · Continue',exact:true}).waitFor();
  assert((await page.locator('.workflow-body').innerText()).includes('owner-approved'));
  await page.getByRole('button',{name:'I verified this step · Continue',exact:true}).click();
  await page.getByRole('button',{name:'Launch step tool',exact:true}).waitFor();
  await page.getByRole('button',{name:'Stop workflow',exact:true}).click();
  await page.getByRole('button',{name:'Export workflow record',exact:true}).waitFor();
  assert((await page.locator('.workflow-body').innerText()).includes('stopped'));
  assert.equal(await page.locator('[data-check="0"]').isChecked(),false,'Runner must not silently mark saved manual checklists');
  assert.deepEqual(errors,[]);console.log('Workflow definitions, one-click portable request, real manual checkpoint controls, stop and export UI passed. No executable ran.');
 }finally{if(browser)await browser.close();proc.kill();}
})().catch(e=>{console.error(e);process.exitCode=1;});
