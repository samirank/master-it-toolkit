/* Per-tool publisher choices. Direct SSD writes require the local launcher. */
(() => {
 'use strict';
 const element=(tag,text)=>{const e=document.createElement(tag);if(text)e.textContent=text;return e;};
 document.addEventListener('click',async event=>{
  const trigger=event.target.closest('[data-download],[data-manage-download]');if(!trigger)return;
  const tool=window.TOOLKIT_DATA.find(t=>t.id===(trigger.dataset.download||trigger.dataset.manageDownload));if(!tool)return;
  const dialog=element('dialog');dialog.className='download-dialog';
  const close=element('button','Close');close.className='dialog-close';close.onclick=()=>dialog.close();dialog.append(close);
  dialog.append(element('h2','Downloads · '+tool.name));
  const status=element('p','Loading publisher choices…');status.setAttribute('role','status');status.classList.add('is-loading');dialog.append(status);
  document.body.append(dialog);dialog.addEventListener('close',()=>dialog.remove());dialog.showModal();
  const pathLabel=element('label','Save in this toolkit folder');pathLabel.className='note-field';
  const pathField=element('input');pathField.readOnly=true;pathField.setAttribute('aria-label','Download destination');
  pathField.value=window.ToolkitPaths.resolve(tool.localFolder,window.TOOLKIT_LOCAL_BASE||location.href).filesystemPath||tool.localFolder;
  pathLabel.append(pathField);dialog.append(pathLabel);
  const copyPath=element('button','Copy destination path');copyPath.onclick=async()=>{try{await navigator.clipboard.writeText(pathField.value);copyPath.textContent='Path copied';}catch{pathField.focus();pathField.select();copyPath.textContent=document.execCommand('copy')?'Path copied':'Select the path and copy manually';}};dialog.append(copyPath);
  let watching=false, tracking=false, baseline=null, stable=null, repeats=0, polling=false;
  const meter=element('progress');meter.max=100;meter.hidden=true;meter.setAttribute('aria-label','Download progress');dialog.append(meter);
  const transfer=element('p');transfer.setAttribute('role','status');dialog.append(transfer);
  const fileList=element('div');fileList.className='download-files';dialog.append(fileList);
  const api=(name)=>new URL('api/'+name,location.href);
  const refreshInventory=async()=>{const r=await fetch(api('inventory'));if(r.ok)window.dispatchEvent(new CustomEvent('toolkit-inventory',{detail:await r.json()}));};
  const activity=(message,busy=true)=>window.dispatchEvent(new CustomEvent('toolkit-activity',{detail:{message,busy,stage:busy?'working':'error'}}));
  const rescan=async()=>{
   transfer.classList.add('is-loading');activity('Scanning and organizing files…');
   try{const r=await fetch(api('action'),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'inventory',tool:tool.id,confirmed:true})});
   const b=await r.json();if(!r.ok)throw Error(b.error);tracking=true;transfer.textContent='Scanning and organizing files…';
   }catch(error){transfer.classList.remove('is-loading');activity(error.message,false);throw error;}
  };
  async function poll(){
   if(polling||!dialog.isConnected)return;polling=true;
   try{
    const [sr,fr]=await Promise.all([fetch(api('status')),fetch(api('tool-files?tool='+encodeURIComponent(tool.id)))]);
    if(!sr.ok||!fr.ok)throw Error('Launcher connection unavailable');
    const state=await sr.json(),folder=await fr.json();pathField.value=folder.folder;
    fileList.replaceChildren(element('h3','Files in destination'));
    if(!folder.files.length)fileList.append(element('p','No downloaded files in this folder yet.'));
    for(const f of folder.files){const row=element('div');row.className='download-file';row.append(element('strong',f.name+(f.partial?' · In progress':'')),element('small',f.kind==='folder'?'Folder':(f.size/1048576).toFixed(2)+' MB'),element('code',f.path));fileList.append(row);}
    if(state.tool===tool.id){
     if(state.busy){transfer.classList.add('is-loading');tracking=true;transfer.textContent=state.message+(state.received!==undefined?' · '+(state.received/1048576).toFixed(1)+' MB'+(state.total?' / '+(state.total/1048576).toFixed(1)+' MB':''):'')+(state.count?' · File '+state.index+' of '+state.count:'');meter.hidden=false;if(state.total)meter.value=state.received/state.total*100;else meter.removeAttribute('value');}
     else if(tracking){transfer.classList.remove('is-loading');tracking=false;meter.hidden=true;transfer.textContent=state.message;await refreshInventory();}
    }
    const signature=JSON.stringify(folder.files.filter(f=>!f.partial&&f.kind!=='folder').map(f=>[f.name,f.size,f.modified]));
    if(baseline===null)baseline=signature;
    if(signature===stable)repeats++;else{stable=signature;repeats=0;}
    if(watching&&signature!==baseline&&repeats>=2&&!folder.files.some(f=>f.partial)&&!state.busy){await rescan();baseline=signature;}
   }catch(error){transfer.classList.remove('is-loading');transfer.textContent=error.message;}finally{polling=false;}
  }
  if(window.TOOLKIT_LAUNCHER){
   const controls=element('div');controls.className='actions';
   const scan=element('button','Refresh files & scan');scan.onclick=()=>rescan().catch(e=>transfer.textContent=e.message);
   const picker=element('input');picker.type='file';picker.hidden=true;picker.accept='.exe,.msi,.msix,.zip,.7z,.gz,.xz,.bz2,.dmg,.pkg,.deb,.rpm,.AppImage,.iso';
   const upload=element('button','Import downloaded file…');upload.onclick=()=>picker.click();
   picker.onchange=()=>{const file=picker.files[0];if(!file)return;upload.disabled=true;transfer.classList.add('is-loading');activity('Importing '+file.name+'…');
    const request=new XMLHttpRequest();request.open('PUT',api('import?tool='+encodeURIComponent(tool.id)+'&name='+encodeURIComponent(file.name)));
    request.upload.onprogress=e=>{meter.hidden=false;if(e.lengthComputable){meter.value=e.loaded/e.total*100;transfer.textContent='Importing '+file.name+' · '+Math.round(meter.value)+'%';}};
    request.onload=()=>{upload.disabled=false;picker.value='';let body;try{body=JSON.parse(request.responseText);}catch{body={error:'Import failed'};}if(request.status!==202){transfer.textContent=body.error;meter.hidden=true;transfer.classList.remove('is-loading');activity(body.error,false);}else{tracking=true;transfer.textContent='Imported. Scanning and organizing…';poll();}};
    request.onerror=()=>{upload.disabled=false;transfer.classList.remove('is-loading');activity('Import interrupted. Reconnect and try again.',false);meter.hidden=true;transfer.textContent='Import interrupted. Reconnect the launcher and try again.';};request.send(file);
   };
   controls.append(scan,upload,picker);dialog.append(controls);poll();const timer=setInterval(poll,1500);dialog.addEventListener('close',()=>clearInterval(timer));
  }
  const official=()=>{const a=element('a','Open publisher downloads ↗');a.href=tool.officialDownload;a.target='_blank';a.rel='noopener noreferrer';
   a.onclick=event=>{event.preventDefault();watching=true;window.open(tool.officialDownload,'_blank','popup,width=1100,height=800,noopener,noreferrer');transfer.textContent=window.TOOLKIT_LAUNCHER?'Publisher window opened. Save to the destination above, or import the file here. Completed files trigger a local scan; publisher transfer progress remains in its browser download panel.':'Publisher window opened. Local file management requires the launcher.';};dialog.append(a);};
  let info;
  try{
   if(window.TOOLKIT_LAUNCHER){
    const response=await fetch(new URL('api/download-options?tool='+encodeURIComponent(tool.id),location.href));
    info=await response.json();if(!response.ok)throw Error(info.error||'Publisher lookup failed');
   }else{
    info={assets:[]};
    if(tool.id==='7zip')info.assets=[['Windows','7z2603-x64.exe'],['Windows','7z2603.exe'],['Windows','7z2603-arm64.exe'],['Linux','7z2603-linux-x64.tar.xz'],['Linux','7z2603-linux-x86.tar.xz'],['Linux','7z2603-linux-arm64.tar.xz'],['Linux','7z2603-linux-arm.tar.xz'],['macOS','7z2603-mac.tar.xz']].map(([platform,name])=>({platform,name,url:'https://github.com/ip7z/7zip/releases/download/26.03/'+name}));
   }
   status.classList.remove('is-loading');
   if(!dialog.isConnected)return;
   if(!info.assets.length){status.textContent='This publisher uses its own download or license flow. Choose the platform on the official page, then save the file to '+tool.localFolder+'.';official();return;}
   status.textContent=window.TOOLKIT_LAUNCHER?'Select the packages to save on your SSD. The scan organizes ZIP downloads into Ready folders. Installers are not run.':'Open a package link to download through your browser. Start the local launcher for multi-select downloads straight to your SSD.';
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
     submit.disabled=true;transfer.classList.add('is-loading');activity('Starting selected downloads…');
     try{
      const response=await fetch(new URL('api/action',location.href),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'download',tool:tool.id,assets,confirmed:true})});
      const body=await response.json();if(!response.ok)throw Error(body.error);
      tracking=true;status.textContent='Download started. Progress and saved files appear below.';poll();
      document.querySelector('.launcher-panel').open=true;
     }catch(error){transfer.classList.remove('is-loading');activity(error.message,false);status.textContent=error.message;submit.disabled=false;}
    };dialog.append(submit);
   }
   official();
  }catch(error){status.classList.remove('is-loading');status.textContent='Could not load release choices: '+error.message+'. You can still use the publisher page.';official();}
 });
})();
