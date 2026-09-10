/* Injected only by the optional local launcher; never loaded by the hosted demo. */
(() => {
  'use strict';
  const endpoint = new URL('api/', location.href);
  const panel = document.getElementById('launcher-panel');
  panel.closest('details').open = false;
  const summary=message=>String(message||'Ready.').split(/\r?\n/)[0].slice(0,180);
  let busy = false;
  let initialized = false;
  let lastMessage = '';
  let refreshing=false, startedAt=0, pending=false;
  function confirmAction(item,message){
    return new Promise(resolve=>{
      const dialog=document.createElement('dialog');dialog.className='download-dialog';dialog.setAttribute('aria-label',item.name);
      const title=document.createElement('h2');title.textContent=item.name;
      const description=document.createElement('p');description.textContent=message;description.style.whiteSpace='pre-line';
      const controls=document.createElement('div');controls.className='actions';
      const cancel=document.createElement('button');cancel.textContent='Cancel';cancel.onclick=()=>dialog.close('cancel');
      const run=document.createElement('button');run.textContent='Run now';run.className='primary';run.onclick=()=>dialog.close('run');
      controls.append(cancel,run);dialog.append(title,description,controls);document.body.append(dialog);
      dialog.addEventListener('close',()=>{const accepted=dialog.returnValue==='run';dialog.remove();resolve(accepted);},{once:true});
      dialog.showModal();cancel.focus();
    });
  }
  const activity=document.createElement('aside');activity.id='toolkit-activity';activity.hidden=true;activity.setAttribute('aria-label','Background activity');
  activity.innerHTML='<span class="activity-spinner" aria-hidden="true"></span><div class="activity-copy"><strong id="activity-title"></strong><p id="activity-message" role="status"></p><small id="activity-elapsed" aria-hidden="true"></small></div><button aria-label="Dismiss activity notification" hidden>×</button>';
  document.body.append(activity);
  activity.querySelector('button').onclick=()=>activity.hidden=true;
  function showActivity(state){
    activity.hidden=false;activity.classList.toggle('is-working',!!state.busy);activity.classList.toggle('is-error',state.stage==='error');activity.setAttribute('aria-busy',String(!!state.busy));
    activity.querySelector('button').hidden=!!state.busy;
    document.getElementById('activity-title').textContent=state.busy?'Working…':state.stage==='error'?'Action stopped':'Finished';
    const milestones=String(state.message||'').split(/\r?\n/).filter(line=>line.startsWith('✓')).slice(0,3);
    document.getElementById('activity-message').textContent=state.stage==='complete'&&milestones.length?milestones.join('\n'):summary(state.message);
    if(state.busy){if(state.startedAt)startedAt=state.startedAt*1000;else if(!startedAt)startedAt=Date.now();}
    else{startedAt=0;document.getElementById('activity-elapsed').textContent='';}
  }
  setInterval(()=>{if(startedAt){const seconds=Math.floor((Date.now()-startedAt)/1000);document.getElementById('activity-elapsed').textContent='Running · '+Math.floor(seconds/60)+'m '+seconds%60+'s';}},1000);
  window.addEventListener('toolkit-activity',event=>{showActivity({busy:true,...event.detail});});
  panel.innerHTML = '<h2>Local launcher connected</h2><p>Run a bundled script in its own terminal, or update the toolkit from GitHub. Windows scripts require Windows; repair may require an administrator launcher.</p><div id="launcher-actions" class="actions"></div><progress id="launcher-progress" aria-label="Current transfer progress" max="100" hidden></progress><p id="launcher-status" role="status">Connecting…</p><details class="job-log"><summary>Full report</summary><pre id="launcher-log"></pre></details><button id="activity-history">Job history</button>';
  document.querySelector('.local-label').textContent = 'LAUNCHER MODE';
  async function refresh() {
    if(refreshing||pending)return;refreshing=true;
    try {
      const response = await fetch(new URL('status', endpoint));
      if (!response.ok) throw new Error('Session unavailable');
      const state = await response.json(); const completed = busy && !state.busy; busy = state.busy;
      if((!busy && (completed || state.message !== lastMessage)) || !initialized){
        const snapshot=await fetch(new URL('inventory',endpoint));
        if(snapshot.ok)window.dispatchEvent(new CustomEvent('toolkit-inventory',{detail:await snapshot.json()}));
        initialized=true;
      }
      if(state.busy||completed||state.message!==lastMessage&&initialized&&state.stage)showActivity(state);
      lastMessage=state.message;
      panel.setAttribute('aria-busy',String(busy));
      document.getElementById('launcher-log').textContent=state.message;
      document.getElementById('launcher-status').textContent = summary(state.message)+(state.received!==undefined?' · '+(state.received/1048576).toFixed(1)+' MB'+(state.total?' / '+(state.total/1048576).toFixed(1)+' MB':''):'');
      const meter=document.getElementById('launcher-progress');meter.hidden=!state.busy;if(state.total)meter.value=state.received/state.total*100;else meter.removeAttribute('value');
      const actions = document.getElementById('launcher-actions'); actions.replaceChildren();
      for (const item of [...state.scripts, {id:'update', name:'Update toolkit from GitHub', enabled:true}]) {
        const button = document.createElement('button'); button.textContent = item.name;
        button.disabled = busy || !item.enabled;
        button.title = item.path || 'Update application, scripts and documentation; preserve downloaded tools and local data.';
        button.onclick = async () => {
          if(pending)return;
          pending=true;
          const message = item.id === 'update' ? 'Download and apply the latest toolkit from samirank/master-it-toolkit? Existing files are backed up; locally modified managed files stop the update. Restart the launcher afterward.' : 'Run ' + item.name + '?\n' + item.path + '\nReview the script terminal for prompts and results. PowerShell uses a process-only execution policy; organization policy still applies.';
          if (!['inventory','check-updates','metadata','manifest'].includes(item.id) && !await confirmAction(item,message)) {pending=false;document.getElementById('launcher-status').textContent=item.name+' cancelled.';return;}
          button.disabled = true;showActivity({busy:true,message:'Starting '+item.name+'…'});
          document.getElementById('launcher-status').textContent='Starting '+item.name+'…';
          try {
            const result = await fetch(new URL('action', endpoint), {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({action:item.id, confirmed:true})});
            const data = await result.json();
            if (!result.ok) throw new Error(data.error);
            pending=false;showActivity(data);await refresh();
          } catch (error) {document.getElementById('launcher-status').textContent = error.message;showActivity({busy:false,stage:'error',message:error.message});}
          finally{pending=false;button.disabled=false;}
        };
        actions.append(button);
      }
    } catch (error) {document.getElementById('launcher-status').textContent = 'Launcher disconnected. Restart it to continue.';document.getElementById('launcher-progress').hidden=true;panel.setAttribute('aria-busy','false');showActivity({busy:false,stage:'error',message:'Launcher disconnected. Reconnect to check the task status.'});} finally {refreshing=false;}
  }
  async function history(){
    const d=document.createElement('dialog');d.className='download-dialog';d.setAttribute('aria-label','Job history');
    const close=document.createElement('button');close.textContent='Close';close.onclick=()=>d.close();d.append(close);document.body.append(d);d.onclose=()=>d.remove();d.showModal();
    const h=document.createElement('h2');h.textContent='Job history';d.append(h);
    try{const response=await fetch(new URL('history',endpoint));const data=await response.json();if(data.error)throw Error(data.error);
     if(!data.jobs.length){const p=document.createElement('p');p.textContent='No completed jobs recorded yet.';d.append(p);}
     for(const job of data.jobs){const entry=document.createElement('details'),title=document.createElement('summary'),log=document.createElement('pre');title.textContent=new Date(job.finished*1000).toLocaleString()+' · '+job.action+' · '+job.stage;log.textContent=job.message;entry.className='job-log';entry.append(title,log);d.append(entry);}
    }catch(error){const p=document.createElement('p');p.textContent=error.message;d.append(p);}
  }
  document.getElementById('activity-history').onclick=history;
  const reportButton=document.createElement('button');reportButton.textContent='Logs';reportButton.onclick=history;activity.append(reportButton);
  let eventRevision=-1;
  const events=new EventSource(new URL('events',endpoint));
  events.onmessage=async event=>{
    const revision=JSON.parse(event.data).revision;if(revision===eventRevision)return;eventRevision=revision;
    try{const response=await fetch(new URL('inventory',endpoint));if(response.ok){const inventory=await response.json();if(revision===eventRevision)window.dispatchEvent(new CustomEvent('toolkit-inventory',{detail:inventory}));}}catch{}
    window.dispatchEvent(new Event('toolkit-completed'));refresh();
  };
  window.addEventListener('pagehide',()=>events.close(),{once:true});
  refresh(); setInterval(refresh, 2500);
})();
