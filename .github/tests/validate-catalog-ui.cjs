const {spawn}=require('child_process'),path=require('path'),assert=require('assert'),fs=require('fs');
const {chromium}=require(process.env.PLAYWRIGHT_PATH||'C:/Users/sam/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
(async()=>{
 const proc=spawn('python',['-u','-c',"import launcher; s=launcher.Server(port=0); print(s.origin+'/'+s.token+'/index.html',flush=True);s.serve_forever()"],{cwd:path.resolve(__dirname,'../../MASTER-IT-TOOLKIT')});let browser;
 try{
  const url=await new Promise((resolve,reject)=>{proc.stdout.once('data',d=>resolve(d.toString().trim()));proc.once('error',reject);});
  browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
  const catalog=JSON.parse(fs.readFileSync(path.resolve(__dirname,'../../MASTER-IT-TOOLKIT/assets/download-catalog.json'),'utf8'));let action;
  await page.route('**/api/catalog*',r=>r.fulfill({json:catalog}));
  await page.route('**/api/action',r=>{action=r.request().postDataJSON();return r.fulfill({status:202,json:{busy:true,message:'Fixture queue started'}})});
  await page.goto(url+'#downloads');await page.locator('#catalog-notice').waitFor();
  await page.locator('#bulk-platform').selectOption('Linux');await page.locator('#bulk-architecture').selectOption('arm64');
  await page.locator('[data-bulk-download="missing"]').click();
  await page.waitForFunction(()=>document.querySelector('#activity-message').textContent.includes('Starting download queue'));
  assert.deepEqual(action,{action:'bulk-download',confirmed:true,platform:'Linux',architecture:'arm64',mode:'missing'});
  await page.locator('[data-cancel-downloads]').click();assert.equal(action.action,'cancel-downloads');
  await page.locator('#search').fill('Clonezilla');await page.locator('[data-download="clonezilla"]').click();
  await page.locator('.download-option').first().waitFor();assert(await page.locator('.download-option input:checked').count()>0);
  assert.equal(errors.length,0,errors.join('\n'));console.log('PASS repository catalog, bulk platform selection, cancellation, and recommended Clonezilla ISO. No package downloaded.');
 }finally{if(browser)await browser.close();proc.kill();}
})().catch(e=>{console.error(e);process.exitCode=1});
