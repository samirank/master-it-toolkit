const {spawn}=require('child_process'),path=require('path'),assert=require('assert');
const {chromium}=require(process.env.PLAYWRIGHT_PATH||'C:/Users/sam/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
(async()=>{
 const proc=spawn('python',['-u','-c',"import launcher; s=launcher.Server(port=0); print(s.origin+'/'+s.token+'/index.html',flush=True);s.serve_forever()"],{cwd:path.resolve(__dirname,'../../MASTER-IT-TOOLKIT')});let browser;
 try{
  const url=await new Promise((resolve,reject)=>{proc.stdout.once('data',d=>resolve(d.toString().trim()));proc.once('error',reject);});
  browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
  let stored={},fail=false;
  const page=await browser.newPage();
  await page.route('**/api/catalog*',r=>r.fulfill({json:{tools:{}}}));
  await page.route('**/api/workspace',r=>{if(r.request().method()==='POST'){if(fail)return r.fulfill({status:503,json:{error:'locked'}});const {key,value}=r.request().postDataJSON();stored[key]=value;return r.fulfill({json:{saved:true}});}return r.fulfill({json:stored});});
  await page.addInitScript(()=>localStorage.setItem('master-it.v1.notes',JSON.stringify({issue:'Legacy note'})));
  await page.route('**/api/setup',r=>r.fulfill({json:{required:false}}));await page.goto(url+'#notes');await page.locator('[data-note="issue"]').waitFor();
  assert.equal(await page.locator('[data-note="issue"]').inputValue(),'');
  assert.equal(stored.notes,undefined); // Stale browser copies must never unlock/repopulate a private workspace.
  await page.locator('[data-note="issue"]').fill('New SSD note');
  await page.waitForFunction(()=>document.querySelector('#notes-state').textContent.includes('Saved to SSD'));
  assert.equal(stored.notes.issue,'New SSD note');
  await page.reload();await page.locator('[data-note="issue"]').waitFor();assert.equal(await page.locator('[data-note="issue"]').inputValue(),'New SSD note');
  fail=true;await page.locator('[data-note="issue"]').fill('Unsaved');await page.waitForFunction(()=>document.querySelector('#notes-state').textContent.includes('Save failed'));
  assert.equal(stored.notes.issue,'New SSD note');
  assert.equal(await page.evaluate(()=>JSON.parse(localStorage.getItem('master-it.v1.notes')).issue),'Legacy note');
  console.log('PASS no stale browser fallback, SQLite precedence, save feedback and no plaintext fallback on failure.');
 }finally{if(browser)await browser.close();proc.kill();}
})().catch(e=>{console.error(e);process.exitCode=1});
