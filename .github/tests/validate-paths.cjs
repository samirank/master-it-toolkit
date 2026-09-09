const assert=require('assert'),path=require('path');
const {resolve,relativeUrl}=require('../../MASTER-IT-TOOLKIT/assets/js/paths.js');
const cases=[
 ['Windows SSD','file:///E:/MASTER-IT-TOOLKIT/index.html','20_PORTABLE_APPS/App/tool.exe','E:\\MASTER-IT-TOOLKIT\\20_PORTABLE_APPS\\App\\tool.exe'],
 ['Windows nested folder','file:///D:/My%20Tools/MASTER-IT-TOOLKIT/index.html','Apps/My App/tool.exe','D:\\My Tools\\MASTER-IT-TOOLKIT\\Apps\\My App\\tool.exe'],
 ['Linux mount','file:///media/sam/SSD/MASTER-IT-TOOLKIT/index.html','Apps/tool','/media/sam/SSD/MASTER-IT-TOOLKIT/Apps/tool'],
 ['Linux spaces','file:///run/media/sam/My%20SSD/index.html','Apps/Test #1/tool','/run/media/sam/My SSD/Apps/Test #1/tool'],
 ['macOS volume','file:///Volumes/Tech%20SSD/MASTER-IT-TOOLKIT/index.html','Apps/tool','/Volumes/Tech SSD/MASTER-IT-TOOLKIT/Apps/tool'],
 ['UNC share','file://server/share/Toolkit/index.html','Apps/tool.exe','\\\\server\\share\\Toolkit\\Apps\\tool.exe'],
 ['Changed drive letter','file:///Z:/Toolkit/index.html','Apps/tool.exe','Z:\\Toolkit\\Apps\\tool.exe'],
 ['Unicode','file:///media/user/%E5%B7%A5%E5%85%B7/index.html','Apps/Résumé.txt','/media/user/工具/Apps/Résumé.txt']
];
for(const [name,base,file,expected]of cases){const r=resolve(file,base);assert.equal(r.filesystemPath,expected);assert(r.url.startsWith('file:'));console.log('PASS '+name)}
for(const bad of ['../outside','/etc/passwd','C:\\Windows','https://example.com','a/../b','a\\..\\b'])assert.equal(relativeUrl(bad),null);
console.log('PASS unsafe catalog paths rejected');
const remote=resolve('Apps/tool.exe','https://samirank.github.io/master-it-toolkit/MASTER-IT-TOOLKIT/index.html');
assert.equal(remote.filesystemPath,null);assert.equal(remote.url,null);assert.equal(remote.local,false);
console.log('PASS hosted demo never invents local filesystem paths');
