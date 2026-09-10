(() => {
 'use strict';let settings=null;
 const el=(tag,text)=>{const n=document.createElement(tag);if(text)n.textContent=text;return n;};
 const field=(label,input)=>{const l=el('label',label);l.className='note-field';input.setAttribute('aria-label',label);l.append(input);return l;};
 async function api(path,body){const r=await fetch(new URL('api/'+path,location.href),body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{});const data=await r.json();if(!r.ok)throw Error(data.error||'Launcher unavailable');return data;}
 async function render(root){root.replaceChildren(el('p','Loading backup settings…'));let error='';if(!settings){settings={destination:'',scope:'workspace'};if(window.TOOLKIT_LAUNCHER){try{settings={...settings,...(await api('workspace')).backupSettings};}catch(e){error=e.message;}}}if(!root.isConnected)return;root.replaceChildren();
  const panel=el('section');panel.className='panel';root.append(panel);panel.append(el('h2','Back up this toolkit'),el('p','Save a dated, checksum-verified ZIP to a NAS share, mounted drive or a folder managed by your cloud sync client. Each backup is a new file; existing backups are retained.'));
  const dest=el('input');dest.value=settings.destination;dest.placeholder='Z:\\ToolkitBackups, \\\\NAS\\Backups, or /mnt/nas/toolkit';dest.oninput=()=>settings.destination=dest.value;
  const scope=el('select');for(const [value,text] of [['workspace','Workspace: dashboard, settings, SQLite, notes and workflows'],['full','Full toolkit: workspace + downloaded tools and bundled runtime']]){const o=el('option',text);o.value=value;scope.append(o);}scope.value=settings.scope;scope.onchange=()=>settings.scope=scope.value;
  panel.append(field('Existing destination folder (absolute path)',dest),field('Backup scope',scope));
  const automatic=el('input');automatic.type='checkbox';automatic.checked=!!settings.automatic;automatic.onchange=()=>{settings.automatic=automatic.checked;if(automatic.checked){settings.scope='full';scope.value='full';}};
  const interval=el('select');for(const hours of [1,6,12,24,48,168]){const option=el('option',hours+' hours');option.value=hours;interval.append(option);}interval.value=settings.intervalHours||24;interval.onchange=()=>settings.intervalHours=Number(interval.value);
  panel.append(field('Automatically back up when destination is available',automatic),field('Minimum time between automatic backups',interval),el('p','Runs while the launcher is open. Checks destination availability every minute and retries deferred or failed attempts after five minutes. Enabling selects full backup (tools plus local data); you can change scope. Save destination to activate. Cloud folders still depend on their sync client to upload.'));

  panel.append(el('p','Includes service notes and saved workflow data. ZIPs are not encrypted: use a private destination or an encrypted backup app below. Browser sessions, temporary files and old update rollback folders are excluded. A cloud-synced folder confirms a local backup only—check upload completion in your cloud client.'));
  const status=el('p',error||'Ready. No backup has been started.');status.setAttribute('role','status');const actions=el('div');actions.className='actions';panel.append(actions,status);
  const act=(label,fn)=>{const b=el('button',label);b.disabled=!window.TOOLKIT_LAUNCHER;b.onclick=async()=>{b.disabled=true;try{await fn();}catch(e){status.textContent=e.message;window.dispatchEvent(new CustomEvent('toolkit-activity',{detail:{busy:false,stage:'error',message:e.message}}));}finally{b.disabled=false;}};actions.append(b);return b;};
  act('Save destination',async()=>{await api('workspace',{key:'backupSettings',value:settings});status.textContent='Backup preferences saved to SQLite.';});
  async function start(body){status.textContent='Starting…';const result=await api('action',{...body,confirmed:true});status.textContent=result.message;window.dispatchEvent(new CustomEvent('toolkit-activity',{detail:{busy:true,message:result.message}}));}
  act('Create backup now',()=>start({action:'backup-toolkit',...settings}));
  act('Cancel backup',async()=>{const result=await api('action',{action:'cancel-backup',confirmed:true});status.textContent=result.message;});
  const verify=el('input');verify.placeholder='Full path to a saved master-it-…zip';panel.append(field('Existing backup ZIP to verify',verify));act('Verify backup ZIP',()=>start({action:'verify-backup',archive:verify.value}));
  panel.append(el('h3','Restore procedure'),el('p','Verify the ZIP first. Close the toolkit, then extract a full backup into a new empty folder and open its launcher. For a workspace backup, extract it over a fresh toolkit package with the launcher closed. Keep the original SSD untouched until the restored notes, custom builds and tools are checked.'));
  if(!window.TOOLKIT_LAUNCHER)panel.append(el('p','Open the desktop launcher to create or verify backups.'));
  const apps=el('section');apps.className='panel';apps.append(el('h2','Backup applications'));
  for(const id of ['veeam','restic','kopia','duplicati','rclone','rescuezilla','freefilesync']){const t=(window.TOOLKIT_DATA||[]).find(t=>t.id===id);if(!t)continue;const row=el('div');row.className='actions';row.append(el('strong',t.name));const b=el('button','View setup / download');b.dataset.detail=id;row.append(b);apps.append(row);}root.append(apps);
 }
 window.ToolkitBackups={render};
})();
