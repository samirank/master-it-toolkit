/* Offline assistant; generated text never becomes HTML or executable actions. */
(() => {
 'use strict';
 let busy=false,messages=[],matches=[],warning='',root=null;
 const el=(tag,text)=>{const n=document.createElement(tag);if(text)n.textContent=text;return n;};
 const button=(text,fn)=>{const n=el('button',text);n.type='button';if(fn)n.onclick=fn;return n;};
 async function api(body){const r=await fetch(new URL('api/assistant',location.href),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const d=await r.json();if(!r.ok)throw Error(d.error||'Assistant unavailable');return d;}
 function showReview(action,label){
  const d=el('dialog');d.className='download-dialog';d.append(el('h2',label),el('p','Run this bundled toolkit command on this computer? Its progress and result will appear in toolkit activity.'));
  d.append(button('Cancel',()=>d.close()),button('Run '+label,async()=>{try{const r=await fetch(new URL('api/action',location.href),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action,confirmed:true})});const result=await r.json();if(!r.ok)throw Error(result.error||'Command failed');window.dispatchEvent(new CustomEvent('toolkit-activity',{detail:{busy:true,message:label+' started…'}}));d.close();}catch(e){d.append(el('p',e.message));}}));
  d.onclose=()=>d.remove();document.body.append(d);d.showModal();
 }
 function paint(){
  if(!root?.isConnected)return;
  const log=root.querySelector('.assistant-log');log.replaceChildren();
  for(const message of messages){const row=el('article');row.className='panel';row.append(el('strong',message.role==='user'?'You':'Toolkit assistant'),el('p',message.content));log.append(row);}
  const results=root.querySelector('.assistant-results');results.replaceChildren();
  for(const m of matches){const row=el('section');row.className='panel';row.append(el('h3',m.name));
   const actions=el('div');actions.className='actions';
   if(m.type==='tool'){
    const b=button('Open tool & how-to');b.dataset.detail=m.id;actions.append(b);
    const download=button('Download / manage');download.dataset.manageDownload=m.id;actions.append(download);
    if(m.kind==='Portable'){const run=button('Run portable tool');run.dataset.runTool=m.id;actions.append(run);}
    if(m.kind==='Installer'){const install=button('Review installation');install.dataset.install=m.id;actions.append(install);}
    for(const step of m.steps||[])row.append(el('p',step));
   }else{const b=button('Review workflow');b.dataset.workflow=m.id;actions.append(b);}
   row.append(actions);results.append(row);
  }
  root.querySelector('.assistant-state').setAttribute('aria-busy',String(busy));
  root.querySelector('.assistant-state').textContent=busy?'Working locally… The first model response can take longer.':warning||'Ready · chat history stays in SQLite on this toolkit.';
  root.querySelector('form button').disabled=busy;
 }
 async function render(target){
  root=target;target.replaceChildren();
  const panel=el('section');panel.className='panel';panel.append(el('h2','Offline toolkit assistant'),el('p','Find tools, troubleshoot issues and review actions. Catalog mode works immediately; AI chat uses a model running on this computer.'));
  if(!window.TOOLKIT_LAUNCHER){panel.append(el('p','Open the desktop launcher to use the assistant. The hosted demo cannot access a local AI or run commands.'));target.append(panel);return;}
  const portable=el('details');portable.open=true;portable.append(el('summary','Portable AI on this SSD'));
  portable.append(el('p','Download about 650 MB once. The model and selected runtimes travel with the SSD and are included in full backups. No Ollama installation is required. Allow about 2 GB free RAM for chat; older CPUs may be unsupported.'));
  const platforms=el('select');platforms.setAttribute('aria-label','Portable AI platform');portable.append(platforms);
  const transfer=el('progress');transfer.max=100;transfer.hidden=true;portable.append(transfer);
  const preparation=el('p');preparation.setAttribute('role','status');portable.append(preparation);
  const prepare=button('Prepare portable AI on SSD',async()=>{try{prepare.disabled=true;await api({operation:'portable-prepare',platform:platforms.value});await poll();}catch(e){preparation.textContent=e.message;prepare.disabled=false;}});
  portable.append(prepare,button('Cancel AI download',async()=>{try{const r=await api({operation:'portable-cancel'});preparation.textContent=r.message;}catch(e){preparation.textContent=e.message;}}));
  let timer;
  async function poll(){clearTimeout(timer);if(!portable.isConnected)return;try{const data=await api({operation:'portable-status'});if(!platforms.options.length){for(const p of [...data.platforms,'All']){const o=el('option',p==='All'?'All supported platforms':p);o.value=p;platforms.append(o);}platforms.value=data.platforms.includes(data.platform)?data.platform:'All';}prepare.disabled=!!data.busy;transfer.hidden=!data.busy;if(data.total)transfer.value=data.received/data.total*100;else transfer.removeAttribute('value');preparation.textContent=(data.message||(data.ready?'Portable AI ready. Select Portable AI chat below.':'Not prepared for this computer.'))+(data.total?' � '+Math.round(data.received/1048576)+' / '+Math.round(data.total/1048576)+' MB':'')+'\nSaved in: '+data.path;}catch(e){preparation.textContent=e.message;}if(portable.isConnected)timer=setTimeout(poll,1500);}
  panel.append(portable);setTimeout(poll,0);
  const setup=el('details');setup.append(el('summary','Optional: use Ollama installed on this computer'));
  const link=el('a','Install Ollama from the official website');link.href='https://ollama.com/download';link.target='_blank';link.rel='noopener noreferrer';setup.append(link,el('p','Start Ollama with cloud features disabled (OLLAMA_NO_CLOUD=1). Then download qwen3:0.6b below while online. Afterwards chat works offline. The model lives in Ollama’s model folder on this computer; it is not bundled in the toolkit ZIP.'));
  setup.append(button('Download local model (internet required)',async()=>{if(busy)return;busy=true;warning='';paint();try{await api({operation:'prepare'});warning='Local model ready. Select Local AI chat.';}catch(e){warning=e.message;}finally{busy=false;paint();}}));
  panel.append(setup,el('p','Temporary assistance only. Do not enter passwords, recovery codes or sensitive customer data. Copy any guidance or records you need to approved permanent storage; do not rely on chat as a long-term record.'));
  const actions=el('div');actions.className='actions';for(const [action,label] of [['inventory','Scan inventory'],['pc','PC diagnostics'],['network','Network diagnostics']])actions.append(button(label,()=>showReview(action,label)));
  actions.append(button('PC builds',()=>location.hash='builds'),button('Toolkit backup',()=>location.hash='backups'));panel.append(actions);
  const mode=el('select');mode.setAttribute('aria-label','Assistant mode');for(const [value,label] of [['catalog','Offline catalog guide'],['portable','Portable AI chat (SSD)'],['ai','Host Ollama chat']]){const o=el('option',label);o.value=value;mode.append(o);}panel.append(mode);
  panel.append(button('Clear saved chat',async()=>{if(busy)return;try{await api({operation:'clear'});messages=[];matches=[];warning='Chat cleared.';paint();}catch(e){warning=e.message;paint();}}));
  const status=el('p');status.className='assistant-state';status.setAttribute('role','status');panel.append(status);target.append(panel);
  const log=el('div');log.className='assistant-log';target.append(log);
  const results=el('div');results.className='assistant-results';target.append(results);
  const form=el('form');form.className='panel';const input=el('textarea');input.maxLength=4000;input.required=true;input.setAttribute('aria-label','Message the toolkit assistant');input.placeholder='For example: My Windows PC cannot connect to Wi-Fi. Where should I start?';const send=button('Send');send.type='submit';form.append(input,send);target.append(form);
  form.onsubmit=async e=>{e.preventDefault();if(busy||!input.value.trim())return;const message=input.value.trim();input.value='';messages.push({role:'user',content:message});busy=true;warning='';paint();try{const data=await api({message,mode:mode.value});messages.push({role:'assistant',content:data.answer});matches=data.matches;warning=data.warning||(data.mode==='ai'?'Answered by local Qwen3 · review suggestions before acting.':'Offline catalog results · no AI model used.');}catch(error){warning=error.message;}finally{busy=false;paint();}};
  paint();if(!busy)try{const data=await api({operation:'status'});if(busy)return;messages=data.messages;warning=data.ready?'Local AI model ready. Choose Local AI chat to use it.':data.message||'Catalog guide ready. Download the model to enable AI chat.';paint();}catch(e){warning=e.message;paint();}
 }
 window.ToolkitAssistant={render};
})();
