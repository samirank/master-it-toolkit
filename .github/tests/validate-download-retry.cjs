const {spawn}=require('child_process'),path=require('path'),assert=require('assert');
const {chromium}=require(process.env.PLAYWRIGHT_PATH||'C:/Users/sam/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
(async()=>{
 const proc=spawn('python',['-u','-c',"import launcher;s=launcher.Server(port=0);print(s.origin+'/'+s.token+'/index.html',flush=True);s.serve_forever()"],{cwd:path.resolve(__dirname,'../../MASTER-IT-TOOLKIT')});let browser;
 try{
  const url=await new Promise((resolve,reject)=>{proc.stdout.once('data',d=>resolve(d.toString().trim()));proc.once('error',reject);});
  browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});const page=await browser.newPage();let state={busy:false},requests=0;
  await page.route('**/api/setup',r=>r.fulfill({json:{required:false}}));
  await page.route('**/api/status',r=>r.fulfill({json:state}));
  await page.route('**/api/tool-files?tool=cdi',r=>r.fulfill({json:{folder:'D:/fixture/CrystalDiskInfo',files:[]}}));
  await page.route('**/api/download-options?tool=cdi',r=>r.fulfill({json:{assets:[{id:'portable',name:'CrystalDiskInfo9_9_2.zip',platform:'Windows'}],recommended:{'Windows/x64':['portable']}}}));
  await page.route('**/api/action',r=>{requests++;state={tool:'cdi',busy:true,startedAt:requests,stage:'download',message:'Downloading fixture'};return r.fulfill({status:202,json:{message:'Started'}});});
  await page.goto(url);await page.evaluate(()=>{const b=document.createElement('button');b.dataset.manageDownload='cdi';document.body.append(b);b.click();b.remove();});
  const dialog=page.locator('dialog.download-dialog');await dialog.getByRole('button',{name:'Download selected to SSD',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('[data-download-submit]')?.disabled);
  state={...state,busy:false,stage:'error',message:'Stopped: fixture redirect failure'};
  const retry=dialog.getByRole('button',{name:'Retry selected download',exact:true});await retry.waitFor();assert(await retry.isEnabled());
  assert((await dialog.innerText()).includes('Download did not finish'));await retry.click();
  await page.waitForFunction(()=>document.querySelector('[data-download-submit]')?.disabled);assert.equal(requests,2);
  state={...state,busy:false,stage:'complete',message:'Fixture package saved'};
  await dialog.getByText('Download finished. Files and scan results appear below.',{exact:true}).waitFor();
  assert(await dialog.getByRole('button',{name:'Download selected to SSD',exact:true}).isEnabled());
  console.log('PASS failed download offers an enabled retry; successful retry clears stale failure/start messaging. No package executed.');
 }finally{if(browser)await browser.close();proc.kill();}
})().catch(e=>{console.error(e);process.exitCode=1;});
