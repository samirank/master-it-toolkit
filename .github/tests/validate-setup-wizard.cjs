const {spawn}=require('child_process'),path=require('path'),assert=require('assert');
const {chromium}=require(process.env.PLAYWRIGHT_PATH||'C:/Users/sam/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
(async()=>{
 const root=path.resolve(__dirname,'../../MASTER-IT-TOOLKIT');
 const code="import tempfile,shutil;from pathlib import Path;import launcher; t=tempfile.TemporaryDirectory();r=Path(t.name);shutil.copytree('assets',r/'assets');shutil.copy2('index.html',r/'index.html');s=launcher.Server(r,port=0);print(s.origin+'/'+s.token+'/index.html',flush=True);s.serve_forever()";
 const proc=spawn('python',['-u','-c',code],{cwd:root});let browser;
 try{
  const url=await new Promise((resolve,reject)=>{proc.stdout.once('data',d=>resolve(d.toString().trim()));proc.on('error',reject);proc.stderr.on('data',d=>console.error(d.toString()));});
  browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));let actions=0;
  page.on('request',r=>{if(r.url().endsWith('/api/action')&&r.method()==='POST')actions++;});
  await page.route('**/api/catalog',r=>r.fulfill({json:{tools:{}}}));await page.goto(url);const wizard=page.getByRole('dialog',{name:'Set up your toolkit',exact:true});
  await wizard.getByRole('heading',{name:'Welcome to Master IT Toolkit'}).waitFor();if(process.env.SETUP_SCREENSHOT)await page.screenshot({path:process.env.SETUP_SCREENSHOT});
  await wizard.getByRole('button',{name:'Continue',exact:true}).click();
  await wizard.getByRole('heading',{name:'Protect your private workspace'}).waitFor();
  assert(await wizard.getByRole('button',{name:'Set up encryption later',exact:true}).isDisabled());
  await wizard.getByRole('button',{name:'Set up later',exact:true}).click();await page.reload();
  await wizard.getByRole('heading',{name:'Protect your private workspace'}).waitFor();
  await wizard.getByRole('checkbox').check();await wizard.getByRole('button',{name:'Set up encryption later',exact:true}).click();
  await wizard.getByLabel('Backup destination',{exact:true}).fill('relative/folder');await wizard.getByRole('button',{name:'Save backup plan',exact:true}).click();
  await wizard.getByText('Use an absolute folder path.',{exact:true}).waitFor();
  await wizard.getByRole('button',{name:'Set up backup later',exact:true}).click();
  await wizard.getByRole('button',{name:'Finish setup',exact:true}).click();await wizard.waitFor({state:'detached'});await page.reload();
  await page.getByRole('button',{name:'Setup wizard',exact:true}).waitFor();await page.waitForTimeout(500);
  assert.equal(await wizard.count(),0,'Completed setup must not reopen after reload');assert.equal(actions,0,'Setup must not automatically run jobs');
  await page.getByRole('button',{name:'Setup wizard',exact:true}).click();await wizard.getByRole('button',{name:'Continue',exact:true}).click();
  await wizard.getByLabel('New vault passphrase',{exact:true}).fill('wizard fixture password');await wizard.getByLabel('Confirm passphrase',{exact:true}).fill('different password');
  await wizard.getByRole('button',{name:'Encrypt workspace',exact:true}).click();await wizard.getByText('Passphrases do not match.',{exact:true}).waitFor();
  await wizard.getByLabel('Confirm passphrase',{exact:true}).fill('wizard fixture password');await wizard.getByRole('button',{name:'Encrypt workspace',exact:true}).click();
  await wizard.getByLabel('New vault recovery key',{exact:true}).waitFor().catch(async e=>{console.error(await wizard.innerText());throw e;});assert((await wizard.getByLabel('New vault recovery key',{exact:true}).inputValue()).length>20);
  assert(await wizard.getByRole('button',{name:'Set up later',exact:true}).isDisabled());
  await wizard.getByRole('button',{name:'I saved the recovery key · Continue',exact:true}).click();await wizard.getByRole('heading',{name:'Choose a backup destination'}).waitFor();assert.equal(await wizard.getByLabel('New vault recovery key',{exact:true}).count(),0);
  await wizard.getByRole('button',{name:'Set up backup later',exact:true}).click();await wizard.getByRole('button',{name:'Finish setup',exact:true}).click();await wizard.waitFor({state:'detached'});
  const result=await page.evaluate(async()=>({setup:await(await fetch(new URL('api/setup',location.href))).json(),vault:await(await fetch(new URL('api/vault',location.href))).json()}));
  assert.equal(result.setup.required,false);assert.equal(result.vault.configured,true);assert.deepEqual(errors,[]);
  console.log('First-run wizard: resume, completion persistence, backup validation, no automatic jobs, encryption and recovery acknowledgement passed.');
 }finally{if(browser)await browser.close();proc.kill();}
})().catch(e=>{console.error(e);process.exitCode=1;});
