/* End-to-end smoke check for the actual public demo. Requires development Playwright. */
const fs=require('fs'),path=require('path'),assert=require('assert');
const {chromium}=require(process.env.PLAYWRIGHT_PATH||'C:/Users/sam/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const root=path.resolve(__dirname,'../..'),out=path.join(root,'.development/published-validation');fs.mkdirSync(out,{recursive:true});
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.BROWSER_EXECUTABLE||'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
 const context=await browser.newContext({viewport:{width:1440,height:1000},acceptDownloads:true});
 const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(process.env.DEMO_URL||'https://samirank.github.io/master-it-toolkit/',{waitUntil:'networkidle'});
 assert.equal(await page.title(),'Master IT Toolkit');assert((await page.locator('main').innerText()).includes('HOSTED DEMO'));
 assert.equal(await page.locator('.brand img, link[rel="icon"]').count(),0);
 assert.equal(await page.getByRole('link',{name:'GitHub repository'}).getAttribute('href'),'https://github.com/samirank/master-it-toolkit');
 const license=await context.request.get(new URL('LICENSE.txt',page.url()).href);assert(license.ok());assert((await license.text()).includes('Source-Available License 1.0'));
 const [archive]=await Promise.all([page.waitForEvent('download'),page.getByRole('link',{name:'Download offline ZIP'}).click()]);
 await archive.saveAs(path.join(out,'MASTER-IT-TOOLKIT.zip'));
 assert(fs.statSync(path.join(out,'MASTER-IT-TOOLKIT.zip')).size>100000);
 await page.locator('#search').fill('GPU crash');assert(await page.locator('[data-tool-id="ddu"]').count());
 await page.locator('[data-detail="ddu"]').first().click();assert((await page.locator('#detail-body').innerText()).includes('Destination within downloaded toolkit'));
 assert.equal(await page.locator('#detail-body a[href^="file:"]').count(),0);assert(await page.getByRole('button',{name:'OPEN FOLDER · local use only'}).isDisabled());await page.keyboard.press('Escape');
 await page.locator('[data-nav="downloads"]').first().click();assert(await page.locator('[data-path]').first().isDisabled());
 await page.locator('[data-nav="home"]').first().click();await page.screenshot({path:path.join(out,'demo.png'),fullPage:true});
 assert.deepEqual(errors,[]);await browser.close();
 console.log('PASS public Pages redirect, brand, demo notice, ZIP download, search, disabled local access and zero JavaScript errors');
})().catch(e=>{console.error(e);process.exit(1)});
