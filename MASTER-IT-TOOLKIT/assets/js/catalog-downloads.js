/* Repository-managed package catalog. Downloads are performed only by explicit user action. */
(() => {
 'use strict';
 const feed='https://raw.githubusercontent.com/samirank/master-it-toolkit/download-catalog/catalog.json';
 const api=name=>new URL('api/'+name,location.href);
 let catalog=null;
 async function load(refresh=false){
  const url=window.TOOLKIT_LAUNCHER?api('catalog'+(refresh?'?refresh=1':'')):feed;
  try{const response=await fetch(url,{cache:'no-store'});if(!response.ok)throw Error('Catalog unavailable');catalog=await response.json();}
  catch{if(!catalog){const response=await fetch('assets/download-catalog.json');catalog=await response.json();}}
  window.TOOLKIT_DOWNLOAD_CATALOG=catalog;
  window.dispatchEvent(new CustomEvent('toolkit-catalog',{detail:catalog}));
  const errors=Object.values(catalog.tools||{}).filter(t=>t.status==='error').length;
  const ready=Object.values(catalog.tools||{}).filter(t=>t.status==='ready').length;
  let banner=document.getElementById('catalog-notice');
  if(!banner){banner=document.createElement('aside');banner.id='catalog-notice';banner.className='catalog-notice';document.querySelector('main')?.before(banner);}
  banner.replaceChildren();
  const text=document.createElement('span');text.textContent=ready+' tools support automatic downloads'+(errors?' · '+errors+' sources need attention':'')+(catalog.warning?' · Offline/saved catalog':'')+'.';banner.append(text);
  const link=document.createElement('a');link.href='https://github.com/samirank/master-it-toolkit/issues?q=is%3Aissue+%22Download+catalog%22';link.target='_blank';link.rel='noopener noreferrer';link.textContent='Update notifications ↗';banner.append(link);
  let seen='';try{seen=localStorage.getItem('master-it.catalog-seen')||'';}catch{}
  if(catalog.revision&&catalog.revision!==seen){
   const updates=(catalog.changes||[]).filter(c=>c.kind==='updated');
   if(updates.length){const message=document.createElement('strong');message.textContent=updates.length+' catalog updates since the last catalog change';banner.prepend(message);}
   const dismiss=document.createElement('button');dismiss.textContent='Mark reviewed';dismiss.onclick=()=>{try{localStorage.setItem('master-it.catalog-seen',catalog.revision);}catch{}dismiss.remove();};banner.append(dismiss);
  }
  return catalog;
 }
 window.ToolkitDownloadCatalog={load};
 document.addEventListener('click',async event=>{
  const button=event.target.closest('[data-bulk-download],[data-catalog-refresh],[data-cancel-downloads]');if(!button)return;
  button.disabled=true;
  try{
   if(button.hasAttribute('data-catalog-refresh')){await load(true);return;}
   if(!window.TOOLKIT_LAUNCHER)throw Error('Open the desktop launcher to download packages into your toolkit.');
   const body=button.hasAttribute('data-cancel-downloads')?{action:'cancel-downloads',confirmed:true}:{action:'bulk-download',confirmed:true,
     platform:document.getElementById('bulk-platform')?.value||'Windows',architecture:document.getElementById('bulk-architecture')?.value||'x64',mode:button.dataset.bulkDownload||'missing'};
   if(button.hasAttribute('data-selected-download')){
    body.tools=window.ToolkitSelection?.ids()||[];
    if(!body.tools.length)throw Error('Select at least one tool.');
    body.platform=document.getElementById('selection-platform').value;
    body.architecture=document.getElementById('selection-architecture').value;
   }
   window.dispatchEvent(new CustomEvent('toolkit-activity',{detail:{busy:true,message:body.action==='bulk-download'?'Starting download queue…':'Stopping after the current transfer…'}}));
   const response=await fetch(api('action'),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
   const result=await response.json();if(!response.ok)throw Error(result.error);
  }catch(error){window.dispatchEvent(new CustomEvent('toolkit-activity',{detail:{busy:false,stage:'error',message:error.message}}));}
  finally{button.disabled=false;}
 });
 // Catalog checks fetch small metadata only. They never start a package download.
 if(location.protocol!=='file:')load(true).catch(()=>{});
 window.addEventListener('toolkit-completed',()=>load(false).catch(()=>{}));
})();
