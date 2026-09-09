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
  await page.setViewportSize({width:390,height:844});
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  assert.deepEqual(errors,[]);
  console.log('PASS launcher connection, action confirmation, status, update button, mobile layout and no browser errors');
 }finally{if(browser)await browser.close();process.kill();}
})().catch(e=>{console.error(e);process.exit(1)});
