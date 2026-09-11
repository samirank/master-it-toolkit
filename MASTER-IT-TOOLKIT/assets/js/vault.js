(() => {
 'use strict';
 if(!window.TOOLKIT_LAUNCHER)return;
 const el=(tag,text)=>{const n=document.createElement(tag);if(text)n.textContent=text;return n;};
 async function api(body){const r=await fetch(new URL('api/vault',location.href),body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{cache:'no-store'});const value=await r.json();if(!r.ok)throw Error(value.error||'Vault unavailable');return value;}
 const b=el('button','Private vault');b.id='manage-private-vault';document.querySelector('.header-actions').append(b);
 let dialog;
 b.onclick=async()=>{
  if(dialog?.isConnected){dialog.focus();return;}
  const d=el('dialog');dialog=d;d.className='download-dialog vault-dialog';d.setAttribute('aria-label','Private workspace vault');
  const close=el('button','Close');close.className='dialog-close';close.onclick=()=>d.close();
  d.append(close,el('h2','Private workspace vault'));document.body.append(d);d.onclose=()=>{d.replaceChildren();d.remove();};d.showModal();
  try{
   const state=await api();
   d.append(el('p',state.configured?(state.locked?'Unlock to access your shared notes, favorites, settings and workflow history.':state.master?'This OS account is a master computer. The vault unlocks automatically when you start the toolkit here.':'Unlocked for this session. Other computers need your passphrase or recovery key.'):'Encrypt your workspace database. Exported files, diagnostic reports and browser sessions are separate and are not encrypted by this vault.'));
   d.append(el('p','The vault locks after 15 minutes of inactivity. A master computer can unlock again using its OS credential store. Lock now stays locked until you unlock or restart.'));
   if(!state.configured)d.append(el('p','Use at least 6 characters. A six-digit PIN is accepted; a longer passphrase offers stronger protection.'));
   const secret=el('input');secret.type='password';secret.autocomplete='off';secret.maxLength=1024;secret.setAttribute('aria-label','Vault passphrase or recovery key');const secretField=el('label','Vault passphrase or recovery key');secretField.className='vault-field';secretField.append(secret);d.append(secretField);
   const recovery=el('input');recovery.type='checkbox';const label=el('label','Use recovery key');label.prepend(recovery);if(state.configured)d.append(label);
   const status=el('p');status.className='vault-feedback';status.id='vault-feedback';status.setAttribute('role','status');secret.setAttribute('aria-describedby','vault-feedback');d.append(status);
   secret.oninput=()=>{secret.removeAttribute('aria-invalid');status.textContent='';status.setAttribute('role','status');};
   function requireSecret(message){if(secret.value.trim())return true;status.setAttribute('role','alert');status.textContent=message;secret.setAttribute('aria-invalid','true');secret.focus();return false;}
   const actions=el('div');actions.className='actions';d.append(actions);
   let recoveryPending=false;
   function action(text,fn,parent=actions,validate){
    const button=el('button',text);parent.append(button);
    button.onclick=async()=>{
     if(validate&&!validate())return;
     const controls=[...d.querySelectorAll('button')];controls.forEach(n=>n.disabled=true);d.oncancel=e=>e.preventDefault();status.textContent='Working…';
     try{await fn();}catch(e){status.setAttribute('role','alert');status.textContent=e.message;status.scrollIntoView({block:'nearest'});}
     finally{controls.forEach(n=>n.disabled=false);if(recoveryPending){close.disabled=true;d.oncancel=e=>e.preventDefault();}else d.oncancel=null;}
    };return button;
   }
   if(!state.configured||state.locked){
    action(state.configured?'Unlock':'Encrypt workspace',async()=>{
     const result=await api({operation:state.configured?'unlock':'setup',secret:secret.value,recovery:recovery.checked});secret.value='';
     if(result.recoveryKey){
      for(const key of Object.keys(localStorage))if(/^(master-it\.v1\.|neighbor-circuit\.v1\.|ventoy\.v1\.)/.test(key))localStorage.removeItem(key);
      recoveryPending=true;actions.replaceChildren();
      status.textContent='Save this recovery key somewhere secure, separate from the SSD. It is shown only once. After reloading, open the vault to register master computers.';
      const key=el('textarea');key.readOnly=true;key.value=result.recoveryKey;key.setAttribute('aria-label','New vault recovery key');d.append(key);
      action('I saved the recovery key · Reload',async()=>location.reload());
     }else location.reload();
    });
    if(state.master)action('Unlock on this master computer',async()=>{await api({operation:'master-unlock'});location.reload();});
   }else{
    const session=el('section');session.className='vault-session';session.append(el('h3','Current session'),el('p','Locking hides your private workspace. No passphrase is needed to lock it.'),actions);d.append(session);
    action('Lock now',async()=>{await api({operation:'lock'});location.reload();});
    const section=el('section');section.className='setup-content';d.append(section,el('p','Do not use the toolkit for long-term sensitive storage. Export service records to their permanent home.'));
    section.classList.add('vault-registration');
    section.append(el('h3',state.master?'Manage automatic unlock':'Set up automatic unlock on this computer'),el('p','Enter your vault passphrase again to authorize this change, even though the vault is already unlocked. Use your saved recovery key instead only if you select the option below.'));
    secretField.firstChild.textContent='Confirm vault passphrase or recovery key (required)';secret.setAttribute('aria-label','Confirm vault passphrase or recovery key (required)');secret.autocomplete='current-password';
    const name=el('input');name.placeholder='Example: Home workstation';name.maxLength=80;name.setAttribute('aria-label','Master computer name');const nameField=el('label','Master computer name');nameField.className='vault-field';nameField.append(name);section.append(nameField,secretField,label,status);
    action(state.master?'Update this master computer':'Make this a master computer',async()=>{await api({operation:'trust',secret:secret.value,recovery:recovery.checked,name:name.value});secret.value='';d.close();d.remove();dialog=null;b.click();},section,()=>requireSecret('Enter your vault passphrase or recovery key above to register this computer.'));
    if(state.masters?.length)section.append(el('h3','Registered master computers'));
    for(const master of state.masters||[]){
     const row=el('div');row.className='master-computer-row';row.append(el('span',master.name+' · '+({win32:'Windows',darwin:'macOS',linux:'Linux'}[master.platform]||master.platform)+(master.current?' · This account':'')));
     action('Remove '+master.name,async()=>{await api({operation:'revoke',id:master.id});d.close();d.remove();dialog=null;b.click();},row);section.append(row);
    }
    section.append(el('p','Removing a master revokes automatic unlock for this vault copy. Separate old copies and backups retain their original access settings.'));
   }
  }catch(e){d.append(el('p',e.message));}
 };
 let last=0;for(const event of ['keydown','pointerdown'])document.addEventListener(event,()=>{if(Date.now()-last<60000)return;last=Date.now();api({operation:'touch'}).catch(()=>{});});
 let wasLocked=null;setInterval(async()=>{try{const state=await api();b.textContent=state.configured?(state.locked?'Unlock vault':'Lock / manage vault'):'Set up private vault';if(state.locked&&wasLocked===false)location.reload();wasLocked=state.locked;}catch{}},5000);
 api().then(state=>{if(state.locked)b.click();}).catch(()=>{});
})();
