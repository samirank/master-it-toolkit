const {spawn}=require('child_process'),path=require('path'),assert=require('assert');
const {chromium}=require(process.env.PLAYWRIGHT_PATH||'C:/Users/sam/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
(async()=>{
 const script="import launcher,tempfile,shutil;from pathlib import Path;t=tempfile.TemporaryDirectory();r=Path(t.name);shutil.copytree('assets',r/'assets');shutil.copy('index.html',r/'index.html');s=launcher.Server(r,port=0);print(s.origin+'/'+s.token+'/index.html',flush=True);s.serve_forever()";
 const proc=spawn('python',['-u','-c',script],{cwd:path.resolve(__dirname,'../../MASTER-IT-TOOLKIT')});let browser;
 try{
  const url=await new Promise((resolve,reject)=>{proc.stdout.once('data',d=>resolve(d.toString().trim()));proc.once('error',reject);});
  browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});const page=await browser.newPage();
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/api/setup',r=>r.fulfill({json:{required:false}}));await page.goto(url+'#notes');await page.locator('[data-note="issue"]').fill('Private test issue');
  await page.waitForFunction(()=>document.querySelector('#notes-state').textContent.includes('Saved to SSD'));
  await page.getByRole('button',{name:/Private vault|Set up private vault/}).click();
  await page.getByLabel('Vault passphrase or recovery key').fill('test-only long vault passphrase');
  await page.getByRole('button',{name:'Encrypt workspace',exact:true}).click();
  const recovery=await page.getByLabel('New vault recovery key').inputValue();assert(recovery.length>30);
  await page.getByRole('button',{name:'I saved the recovery key · Reload'}).click();
  await page.getByRole('button',{name:/Private vault|Lock \/ manage vault/}).click();
  await page.getByRole('button',{name:'Lock now',exact:true}).click();
  await page.locator('[data-note="issue"]').waitFor();
  await page.waitForFunction(()=>document.querySelector('[data-note="issue"]')?.value==='');
  const status=await page.evaluate(async()=>{const r=await fetch(new URL('api/history',location.href));return r.status;});assert.equal(status,423);
  await page.getByRole('dialog',{name:'Private workspace vault',exact:true}).waitFor();
  await page.getByLabel('Vault passphrase or recovery key').fill(recovery);await page.getByLabel('Use recovery key').check();
  await page.getByRole('button',{name:'Unlock',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('[data-note="issue"]')?.value==='Private test issue');
  assert.deepEqual(errors,[]);console.log('PASS vault setup, lock clears private UI, history access denied, recovery unlock restores notes.');
 }finally{if(browser)await browser.close();proc.kill();}
})().catch(e=>{console.error(e);process.exitCode=1});
