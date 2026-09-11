const {spawn}=require('child_process'),path=require('path'),assert=require('assert');
const {chromium}=require(process.env.PLAYWRIGHT_PATH||'C:/Users/sam/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
(async()=>{
 const proc=spawn('python',['-u','-c',"import launcher;s=launcher.Server(port=0);print(s.origin+'/'+s.token+'/index.html',flush=True);s.serve_forever()"],{cwd:path.resolve(__dirname,'../../MASTER-IT-TOOLKIT')});let browser;
 try{
  const url=await new Promise((resolve,reject)=>{proc.stdout.once('data',d=>resolve(d.toString().trim()));proc.once('error',reject);});
  browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});const page=await browser.newPage({viewport:{width:1280,height:900}});let revision='one';const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/api/setup',r=>r.fulfill({json:{required:false}}));
  await page.route('**/api/catalog*',r=>r.fulfill({json:{revision,tools:{fixture:{status:'ready'}},changes:[{kind:'updated'}]}}));
  await page.route('**/api/workflow-jobs*',r=>r.fulfill({json:{machine:{name:'Fixture PC',matchBasis:'serial'},jobs:[{id:'fixture-job',name:'Migration check',machine:{name:'Fixture PC'},status:'completed',startedAt:1,inputs:{notes:'Sample job notes'},steps:[]}]}}));
  const stale=new URL(url);stale.pathname='/expired-session-fixture-token/index.html';await page.goto(stale.href);assert.equal(page.url(),url);
  const notice=page.locator('#catalog-notice');await notice.waitFor();const toolbar=page.locator('.workspace-toolbar');
  const a=await toolbar.boundingBox(),b=await notice.boundingBox();assert.equal(a.x,b.x);assert(a.height>=50);
  await page.getByRole('button',{name:'Workflow job history',exact:true}).click();const history=page.getByRole('dialog',{name:'Workflow job history',exact:true});await history.getByText('Migration check',{exact:true}).waitFor();
  const box=await history.boundingBox(),close=await history.getByRole('button',{name:'Close',exact:true}).boundingBox();assert(close.x>box.x+box.width-100);
  if(process.env.NOTICE_SCREENSHOT)await page.screenshot({path:process.env.NOTICE_SCREENSHOT});
  await history.getByRole('button',{name:'Close',exact:true}).click();await page.getByRole('button',{name:'Dismiss update notification'}).click();assert(await notice.isHidden());
  await page.reload();await page.getByRole('button',{name:'Workflow job history',exact:true}).waitFor();await page.waitForTimeout(300);assert(await notice.isHidden());
  revision='two';await page.reload();await notice.waitFor();await page.setViewportSize({width:580,height:850});
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await page.getByRole('button',{name:'Mark reviewed',exact:true}).click();assert(await notice.isHidden());assert.deepEqual(errors,[]);
  console.log('PASS stale address recovery, aligned padded controls, history corner close, revision-based dismissal and narrow-screen layout.');
 }finally{if(browser)await browser.close();proc.kill();}
})().catch(e=>{console.error(e);process.exitCode=1;});
