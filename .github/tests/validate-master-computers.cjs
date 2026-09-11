const {spawn}=require('child_process'),path=require('path'),assert=require('assert');
const {chromium}=require(process.env.PLAYWRIGHT_PATH||'C:/Users/sam/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
(async()=>{
 const code=`import tempfile,shutil,types
from pathlib import Path
import launcher,activity_store,secure_vault as v,trusted_computers as t
tmp=tempfile.TemporaryDirectory(); root=Path(tmp.name)
shutil.copytree('assets',root/'assets'); shutil.copy2('index.html',root/'index.html')
store=activity_store.Store(root,launcher.safe_path); store.workspace('notes',{'issue':'Encrypted shared note'})
v.setup(store.path,'test-only master passphrase'); v.lock(store.path)
keys={}
t.backend=lambda:types.SimpleNamespace(get_password=lambda s,a:keys.get((s,a)),set_password=lambda s,a,k:keys.__setitem__((s,a),k),delete_password=lambda s,a:keys.pop((s,a),None))
server=launcher.Server(root,port=0)
print(server.origin+'/'+server.token+'/index.html',flush=True); server.serve_forever()
`;
 const proc=spawn('python',['-u','-c',code],{cwd:path.resolve(__dirname,'../../MASTER-IT-TOOLKIT')});let browser;
 try{
  const url=await new Promise((resolve,reject)=>{proc.stdout.once('data',d=>resolve(d.toString().trim()));proc.once('error',reject);proc.stderr.on('data',d=>console.error(d.toString()));});
  browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
  const page=await browser.newPage({viewport:{width:1280,height:900}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/api/setup',r=>r.fulfill({json:{required:false}}));await page.goto(url+'#notes');
  const dialog=page.getByRole('dialog',{name:'Private workspace vault',exact:true});await dialog.waitFor();
  await dialog.getByLabel('Vault passphrase or recovery key').fill('test-only master passphrase');await dialog.getByRole('button',{name:'Unlock',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('[data-note="issue"]')?.value==='Encrypted shared note');
  await page.locator('#manage-private-vault').click();
  let trustRequests=0;page.on('request',r=>{if(r.method()==='POST'&&r.url().endsWith('/api/vault')&&r.postDataJSON()?.operation==='trust')trustRequests++;});
  const confirmation=dialog.getByLabel('Confirm vault passphrase or recovery key (required)');
  await dialog.getByRole('button',{name:'Make this a master computer'}).click();
  await dialog.getByRole('alert').getByText('Enter your vault passphrase or recovery key above to register this computer.',{exact:true}).waitFor();
  assert.equal(trustRequests,0,'Empty registration must not call the backend');assert.equal(await confirmation.getAttribute('aria-invalid'),'true');assert(await confirmation.evaluate(e=>e===document.activeElement));
  await page.screenshot({path:path.resolve(__dirname,'../../.development/master-registration-required.png')});
  await confirmation.fill('wrong');await dialog.getByRole('button',{name:'Make this a master computer'}).click();
  await dialog.getByText('Incorrect secret or damaged vault',{exact:true}).waitFor();
  await confirmation.fill('test-only master passphrase');
  await dialog.getByLabel('Master computer name').fill('Home workstation');await dialog.getByRole('button',{name:'Make this a master computer'}).click();
  await dialog.getByRole('button',{name:'Remove Home workstation',exact:true}).waitFor();
  assert.equal(await dialog.getByLabel('Confirm vault passphrase or recovery key (required)').inputValue(),'');
  await page.screenshot({path:path.resolve(__dirname,'../../.development/master-computers.png')});
  await page.setViewportSize({width:390,height:844});
  assert(await dialog.evaluate(d=>d.scrollWidth<=d.clientWidth+1),'Vault must not overflow horizontally on mobile');
  await page.setViewportSize({width:1280,height:900});
  await dialog.getByRole('button',{name:'Lock now',exact:true}).click();
  await dialog.getByRole('button',{name:'Unlock on this master computer',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('[data-note="issue"]')?.value==='Encrypted shared note');
  await page.locator('#manage-private-vault').click();await dialog.getByRole('button',{name:'Remove Home workstation',exact:true}).click();
  await dialog.getByRole('button',{name:'Make this a master computer',exact:true}).waitFor();
  await dialog.getByRole('button',{name:'Lock now',exact:true}).click();await dialog.getByRole('button',{name:'Unlock',exact:true}).waitFor();
  assert.equal(await dialog.getByRole('button',{name:'Unlock on this master computer'}).count(),0);
  assert.deepEqual(errors,[]);console.log('PASS master enrollment requires secret, lists/revokes masters, clears input, unlocks without passphrase, and fits mobile.');
 }finally{if(browser)await browser.close();proc.kill();}
})().catch(e=>{console.error(e);process.exitCode=1;});
