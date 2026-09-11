const {spawn}=require('child_process'),path=require('path'),assert=require('assert');
const {chromium}=require(process.env.PLAYWRIGHT_PATH||'C:/Users/sam/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
(async()=>{
 const proc=spawn('python',['-u','-c',"import launcher; launcher.run_script=lambda key:'Fixture scan completed'; s=launcher.Server(port=0); print(s.origin+'/'+s.token+'/index.html',flush=True);s.serve_forever()"],{cwd:path.resolve(__dirname,'../../MASTER-IT-TOOLKIT')});let browser;
 try{
  const url=await new Promise((resolve,reject)=>{proc.stdout.once('data',d=>resolve(d.toString().trim()));proc.once('error',reject);});
  browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});const page=await browser.newPage();let downloaded=false;
  await page.route('**/api/inventory',r=>r.fulfill({json:{tools:{winutil:{downloaded,ready:downloaded}}}}));
  await page.route('**/api/setup',r=>r.fulfill({json:{required:false}}));await page.goto(url+'#downloads');await page.locator('#search').fill('WinUtil');await page.locator('[data-download="winutil"]').waitFor();
  downloaded=true;const started=Date.now();
  await page.evaluate(async()=>{const r=await fetch(new URL('api/action',location.href),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'inventory',confirmed:true})});if(!r.ok)throw Error('Fixture action failed');});
  await page.locator('[data-download="winutil"]').waitFor({state:'detached',timeout:1000});
  assert(Date.now()-started<1000);console.log('PASS completion push removes WinUtil from Missing downloads in under one second. No script or package executed.');
 }finally{if(browser)await browser.close();proc.kill();}
})().catch(e=>{console.error(e);process.exitCode=1;});
