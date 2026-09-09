/* Per-tool publisher choices. Direct SSD writes require the local launcher. */
(() => {
 'use strict';
 const element=(tag,text)=>{const e=document.createElement(tag);if(text)e.textContent=text;return e;};
 document.addEventListener('click',async event=>{
  const trigger=event.target.closest('[data-download]');if(!trigger)return;
  const tool=window.TOOLKIT_DATA.find(t=>t.id===trigger.dataset.download);if(!tool)return;
  const dialog=element('dialog');dialog.className='download-dialog';
  const close=element('button','Close');close.className='dialog-close';close.onclick=()=>dialog.close();dialog.append(close);
  dialog.append(element('h2','Download '+tool.name));
  const status=element('p','Loading publisher choices…');status.setAttribute('role','status');dialog.append(status);
  document.body.append(dialog);dialog.addEventListener('close',()=>dialog.remove());dialog.showModal();
  const official=()=>{const a=element('a','Open publisher downloads ↗');a.href=tool.officialDownload;a.target='_blank';a.rel='noopener noreferrer';dialog.append(a);};
  let info;
  try{
   if(window.TOOLKIT_LAUNCHER){
    const response=await fetch(new URL('api/download-options?tool='+encodeURIComponent(tool.id),location.href));
    info=await response.json();if(!response.ok)throw Error(info.error||'Publisher lookup failed');
   }else{
    info={assets:[]};
    if(tool.id==='7zip')info.assets=[['Windows','7z2603-x64.exe'],['Windows','7z2603.exe'],['Windows','7z2603-arm64.exe'],['Linux','7z2603-linux-x64.tar.xz'],['Linux','7z2603-linux-x86.tar.xz'],['Linux','7z2603-linux-arm64.tar.xz'],['Linux','7z2603-linux-arm.tar.xz'],['macOS','7z2603-mac.tar.xz']].map(([platform,name])=>({platform,name,url:'https://github.com/ip7z/7zip/releases/download/26.03/'+name}));
   }
   if(!dialog.isConnected)return;
   if(!info.assets.length){status.textContent='This publisher uses its own download or license flow. Choose the platform on the official page, then save the file to '+tool.localFolder+'.';official();return;}
   status.textContent=window.TOOLKIT_LAUNCHER?'Select the packages to save on your SSD. Downloads are not installed or extracted.':'Open a package link to download through your browser. Start the local launcher for multi-select downloads straight to your SSD.';
   const inputs=[];
   if(window.TOOLKIT_LAUNCHER){
    const controls=element('div');controls.className='actions';
    for(const platform of ['All platforms',...new Set(info.assets.map(a=>a.platform)),'Clear']){
     const button=element('button',platform);button.onclick=()=>inputs.forEach(({input,asset})=>input.checked=platform==='All platforms'||asset.platform===platform);controls.append(button);
    }
    dialog.append(controls);
   }
   const list=element('div');list.className='download-options';
   for(const asset of info.assets){
    const row=element('label');row.className='download-option';
    if(window.TOOLKIT_LAUNCHER){const input=element('input');input.type='checkbox';inputs.push({input,asset});row.append(input);}
    const detail=element('span');detail.append(element('strong',asset.platform));detail.append(element('small',asset.name+(asset.size?' · '+(asset.size/1048576).toFixed(1)+' MB':'')));row.append(detail);
    if(!window.TOOLKIT_LAUNCHER){const a=element('a','Download ↗');a.href=asset.url;a.target='_blank';a.rel='noopener noreferrer';row.append(a);}
    list.append(row);
   }
   dialog.append(list);
   if(window.TOOLKIT_LAUNCHER){
    const submit=element('button','Download selected to SSD');submit.className='primary';
    submit.onclick=async()=>{
     const assets=inputs.filter(i=>i.input.checked).map(i=>i.asset.id);
     if(!assets.length){status.textContent='Select at least one package.';return;}
     submit.disabled=true;
     try{
      const response=await fetch(new URL('api/action',location.href),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'download',tool:tool.id,assets,confirmed:true})});
      const body=await response.json();if(!response.ok)throw Error(body.error);
      status.textContent='Download started. Progress and full saved paths appear in the launcher panel.';
      document.querySelector('.launcher-panel').open=true;
     }catch(error){status.textContent=error.message;submit.disabled=false;}
    };dialog.append(submit);
   }
   official();
  }catch(error){status.textContent='Could not load release choices: '+error.message+'. You can still use the publisher page.';official();}
 });
})();
