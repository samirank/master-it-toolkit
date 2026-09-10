const {spawn}=require('child_process'),path=require('path'),assert=require('assert');
const {chromium}=require(process.env.PLAYWRIGHT_PATH||'C:/Users/sam/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
(async()=>{
 const proc=spawn('python',['-u','-c',"import launcher; s=launcher.Server(port=0); print(s.origin+'/'+s.token+'/index.html',flush=True);s.serve_forever()"],{cwd:path.resolve(__dirname,'../../MASTER-IT-TOOLKIT')});let browser;
 try{
  const url=await new Promise((resolve,reject)=>{proc.stdout.once('data',d=>resolve(d.toString().trim()));proc.once('error',reject);});
  browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});const page=await browser.newPage();let calls=[],fail=false;
  await page.route('**/api/catalog*',r=>r.fulfill({json:{schema:1,tools:{}}}));
  // No native-dialog listener: reproduce the embedded browser's automatic dismissal.
  await page.route('**/api/action',async r=>{calls.push(r.request().postDataJSON());await new Promise(resolve=>setTimeout(resolve,150));return r.fulfill({status:fail?409:202,json:fail?{error:'Fixture: another action is running'}:{busy:true,message:'Fixture action accepted'}});});
  await page.goto(url);await page.locator('.launcher-panel > summary').click();
  await page.getByRole('button',{name:'Scan local inventory',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('#activity-message').textContent.includes('Fixture action accepted'));
  assert.equal(calls[0].action,'inventory');
  await page.getByRole('button',{name:'Repair Windows system files',exact:true}).click();
  const dialog=page.getByRole('dialog',{name:'Repair Windows system files'});await dialog.waitFor();
  await dialog.getByRole('button',{name:'Cancel',exact:true}).click();assert.equal(calls.length,1);
  await page.getByRole('button',{name:'Repair Windows system files',exact:true}).click();
  await dialog.getByRole('button',{name:'Run now',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('#activity-message').textContent.includes('Fixture action accepted'));
  assert.equal(calls[1].action,'repair');assert.equal(calls[1].confirmed,true);
  fail=true;await page.getByRole('button',{name:'Scan local inventory',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('#activity-message').textContent.includes('Fixture: another action'));
  assert(await page.locator('#toolkit-activity').isVisible());
  console.log('PASS scan feedback, visible repair confirmation, cancellation, accepted action and visible server errors without native dialogs. No scripts executed.');
 }finally{if(browser)await browser.close();proc.kill();}
})().catch(e=>{console.error(e);process.exitCode=1});
