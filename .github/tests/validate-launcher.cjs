const {spawn}=require('child_process'),path=require('path'),assert=require('assert');
const {chromium}=require(process.env.PLAYWRIGHT_PATH||'C:/Users/sam/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
(async()=>{
 const process=spawn('python',['-u','-c',"import launcher; launcher.run_script=lambda key:'Test action completed'; s=launcher.Server(port=0); print(s.origin+'/'+s.token+'/index.html',flush=True); s.serve_forever()"],{cwd:path.resolve(__dirname,'../../MASTER-IT-TOOLKIT')});
 let browser;
 try {
  const url=await new Promise((resolve,reject)=>{process.stdout.once('data',d=>resolve(d.toString().trim()));process.once('error',reject);process.stderr.on('data',d=>console.error(d.toString()));});
  browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
  const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(url);await page.getByRole('button',{name:'Scan local inventory',exact:true}).waitFor();
  assert.equal(await page.locator('.local-label').innerText(),'LAUNCHER MODE');
  assert(!(await page.locator('main').innerText()).includes('HOSTED DEMO'));
  page.once('dialog',d=>d.accept());await page.getByRole('button',{name:'Scan local inventory',exact:true}).click();
  await page.getByText('Test action completed',{exact:true}).waitFor();
  assert(await page.getByRole('button',{name:'Update toolkit from GitHub',exact:true}).isEnabled());
  assert(!(await page.locator('.page-heading').innerText()).includes('Hosted demo'));
  await page.route('**/api/download-options?tool=7zip',route=>route.fulfill({json:{assets:[{id:'win',name:'test-x64.exe',platform:'Windows'},{id:'linux',name:'test-linux.tar.xz',platform:'Linux'}]}}));
  let selected;
  await page.route('**/api/action',route=>{const body=route.request().postDataJSON();if(body.action==='download'){selected=body;return route.fulfill({status:202,json:{message:'started'}});}return route.continue();});
  await page.locator('[data-nav="downloads"]').first().click();
  await page.locator('[data-download="7zip"]').click();
  await page.getByRole('button',{name:'All platforms',exact:true}).click();
  assert.equal(await page.locator('.download-options input:checked').count(),2);
  await page.getByRole('button',{name:'Windows',exact:true}).click();
  assert.equal(await page.locator('.download-options input:checked').count(),1);
  await page.getByRole('button',{name:'Download selected to SSD',exact:true}).click();
  await page.getByText('Download started.',{exact:false}).waitFor();
  assert.deepEqual(selected.assets,['win']);assert.equal(selected.tool,'7zip');
  await page.locator('.download-dialog').getByRole('button',{name:'Close',exact:true}).click();
  await page.setViewportSize({width:390,height:844});
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  assert.deepEqual(errors,[]);
  console.log('PASS launcher connection, action confirmation, status, update button, mobile layout and no browser errors');
 }finally{if(browser)await browser.close();process.kill();}
})().catch(e=>{console.error(e);process.exit(1)});
