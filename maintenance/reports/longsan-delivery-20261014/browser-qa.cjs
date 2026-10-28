const {chromium}=require('C:/Users/Fifholz/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('fs'),path=require('path');
const url=process.argv[2],report=path.resolve('maintenance/reports/longsan-delivery-20261014');
(async()=>{
const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
const page=await browser.newPage({viewport:{width:1400,height:1000}}),errors=[],tests=[];
page.on('pageerror',e=>errors.push(e.message));
const check=(name,passed,detail)=>{tests.push({name,passed:!!passed,detail});if(!passed)errors.push(name)};
await page.goto(url,{waitUntil:'networkidle',timeout:120000});
await page.waitForFunction(()=>document.querySelector('#map').naturalWidth===3072&&document.querySelector('#status').textContent.includes('3072'),null,{timeout:120000});
check('default day metro clean preview',await page.locator('#map').getAttribute('src')==='day-metro-clean-preview.webp');
for(const theme of ['day','night'])for(const layer of ['base','metro'])for(const labels of ['clean','labels']){
 await page.selectOption('#theme',theme);await page.selectOption('#layer',layer);await page.selectOption('#labels',labels);
 const file=`${theme}-${layer}-${labels}-preview.webp`;
 await page.waitForFunction(file=>document.querySelector('#map').getAttribute('src')===file&&document.querySelector('#status').textContent.includes('3072'),file,{timeout:120000});
 check(file,await page.locator('#map').evaluate(e=>e.complete&&e.naturalWidth===3072&&e.naturalHeight===2304));
}
await page.selectOption('#theme','day');await page.selectOption('#layer','metro');await page.selectOption('#labels','clean');
await page.waitForFunction(()=>document.querySelector('#map').getAttribute('src')==='day-metro-clean-preview.webp');
const before=await page.locator('#map').evaluate(e=>{const b=e.getBoundingClientRect();return [b.x,b.y,b.width,b.height]});
await page.selectOption('#resolution','full');await page.waitForFunction(()=>document.querySelector('#map').naturalWidth===8192&&document.querySelector('#status').textContent.includes('8192'),null,{timeout:120000});
check('8k decoded',await page.locator('#map').evaluate(e=>e.complete&&e.naturalHeight===6144));
const after=await page.locator('#map').evaluate(e=>{const b=e.getBoundingClientRect();return [b.x,b.y,b.width,b.height]});
check('resolution change preserves view',before.every((v,i)=>Math.abs(v-after[i])<.1),{before,after});
await page.click('#in');check('zoom control',await page.locator('#map').evaluate(e=>e.getBoundingClientRect().width)>after[2]);
const panBefore=await page.locator('#map').evaluate(e=>{const r=e.getBoundingClientRect();return [r.x,r.y]});
await page.mouse.move(800,600);await page.mouse.down();await page.mouse.move(900,650);await page.mouse.up();
const panAfter=await page.locator('#map').evaluate(e=>{const r=e.getBoundingClientRect();return [r.x,r.y]});check('pan control',Math.abs(panAfter[0]-panBefore[0]-100)<.1&&Math.abs(panAfter[1]-panBefore[1]-50)<.1,{panBefore,panAfter});
await page.click('#fit');await page.screenshot({path:path.join(report,'server-viewer-desktop.png')});
await page.setViewportSize({width:390,height:844});await page.screenshot({path:path.join(report,'server-viewer-mobile.png')});
check('mobile controls remain reachable',await page.locator('#fit').isVisible()&&await page.locator('#download').isVisible());
check('no load error',await page.locator('#error').textContent()==='');
const record={url,tests,errors,passed:errors.length===0};fs.writeFileSync(path.join(report,'browser-qa.json'),JSON.stringify(record,null,2));
await browser.close();console.log(JSON.stringify({passed:record.passed,tests:tests.length,errors}));if(!record.passed)process.exitCode=1;
})().catch(e=>{console.error(e);process.exit(1)});
