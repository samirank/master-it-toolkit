const {spawn}=require('child_process'),path=require('path'),assert=require('assert');
const {chromium}=require(process.env.PLAYWRIGHT_PATH||'C:/Users/sam/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
(async()=>{
 const proc=spawn('python',['-u','-c',"import launcher;s=launcher.Server(port=0);print(s.origin+'/'+s.token+'/index.html',flush=True);s.serve_forever()"],{cwd:path.resolve(__dirname,'../../MASTER-IT-TOOLKIT')});let browser;
 try{
  const url=await new Promise((resolve,reject)=>{proc.stdout.once('data',d=>resolve(d.toString().trim()));proc.once('error',reject);});
  browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});const page=await browser.newPage();let storage={},action;const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/api/catalog*',r=>r.fulfill({json:{tools:{}}}));
  await page.route('**/api/workspace',r=>{if(r.request().method()==='POST'){const b=r.request().postDataJSON();storage[b.key]=b.value;return r.fulfill({json:{saved:true}});}return r.fulfill({json:storage});});
  await page.route('**/api/action',r=>{action=r.request().postDataJSON();return r.fulfill({status:202,json:{busy:true,message:'Fixture accepted'}});});
  await page.route('**/api/setup',r=>r.fulfill({json:{required:false}}));await page.goto(url+'#builds');await page.getByRole('heading',{name:'Gaming PC',exact:true}).waitFor();
  assert.equal(await page.locator('#build-library .tool-card').count(),18);
  const gaming=page.locator('#build-library .tool-card').filter({has:page.getByRole('heading',{name:'Gaming PC',exact:true})});
  await gaming.getByRole('button',{name:'Review build',exact:true}).click();await page.getByRole('button',{name:'Download build packages',exact:true}).click();
  assert.equal(action.action,'bulk-download');assert(action.tools.includes('steam'));assert(!action.tools.includes('kdenlive'));
  await page.getByRole('button',{name:'Customize build',exact:true}).click();
  const edit=page.getByRole('dialog',{name:'Create custom build',exact:true});await edit.getByLabel('Build name',{exact:true}).fill('My gaming workstation');
  await edit.getByRole('button',{name:'Save custom build',exact:true}).click();await edit.waitFor({state:'detached'});
  assert.equal(Object.values(storage.customWorkflows)[0].name,'My gaming workstation');
  await page.reload();await page.getByRole('heading',{name:'My gaming workstation',exact:true}).waitFor();
  const card=page.locator('#build-library .tool-card').filter({has:page.getByRole('heading',{name:'My gaming workstation',exact:true})});await card.getByRole('button',{name:'Review build',exact:true}).click();await page.getByRole('button',{name:'Start guided build',exact:true}).click();
  await page.getByRole('button',{name:'Start · Manual launches',exact:true}).click();assert(action.workflow.startsWith('custom-'));assert.equal(action.mode,'manual');
  assert.deepEqual(errors,[]);console.log('PASS profile library, scoped downloads, clone/save/reload and custom workflow start. No apps installed.');
 }finally{if(browser)await browser.close();proc.kill();}
})().catch(e=>{console.error(e);process.exitCode=1});
