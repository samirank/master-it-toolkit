/* Injected only by the optional local launcher; never loaded by the hosted demo. */
(() => {
  'use strict';
  const endpoint = new URL('api/', location.href);
  const panel = document.getElementById('launcher-panel');
  panel.closest('details').open = true;
  let busy = false;
  let initialized = false;
  let lastMessage = '';
  panel.innerHTML = '<h2>Local launcher connected</h2><p>Run a bundled script in its own terminal, or update the toolkit from GitHub. Windows scripts require Windows; repair may require an administrator launcher.</p><div id="launcher-actions" class="actions"></div><p id="launcher-status" role="status">Connecting…</p>';
  document.querySelector('.local-label').textContent = 'LAUNCHER MODE';
  async function refresh() {
    try {
      const response = await fetch(new URL('status', endpoint));
      if (!response.ok) throw new Error('Session unavailable');
      const state = await response.json(); const completed = busy && !state.busy; busy = state.busy;
      if((!busy && (completed || state.message !== lastMessage)) || !initialized){
        const snapshot=await fetch(new URL('inventory',endpoint));
        if(snapshot.ok)window.dispatchEvent(new CustomEvent('toolkit-inventory',{detail:await snapshot.json()}));
        initialized=true;
      }
      lastMessage=state.message;
      document.getElementById('launcher-status').textContent = state.message;
      const actions = document.getElementById('launcher-actions'); actions.replaceChildren();
      for (const item of [...state.scripts, {id:'update', name:'Update toolkit from GitHub', enabled:true}]) {
        const button = document.createElement('button'); button.textContent = item.name;
        button.disabled = busy || !item.enabled;
        button.title = item.path || 'Update application, scripts and documentation; preserve downloaded tools and local data.';
        button.onclick = async () => {
          const message = item.id === 'update' ? 'Download and apply the latest toolkit from samirank/master-it-toolkit? Existing files are backed up; locally modified managed files stop the update. Restart the launcher afterward.' : 'Run ' + item.name + '?\n' + item.path + '\nReview the script terminal for prompts and results. PowerShell uses a process-only execution policy; organization policy still applies.';
          if (!confirm(message)) return;
          button.disabled = true;
          try {
            const result = await fetch(new URL('action', endpoint), {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({action:item.id, confirmed:true})});
            const data = await result.json();
            if (!result.ok) throw new Error(data.error);
            await refresh();
          } catch (error) {document.getElementById('launcher-status').textContent = error.message;}
        };
        actions.append(button);
      }
    } catch (error) {document.getElementById('launcher-status').textContent = 'Launcher disconnected. Restart it to continue.';}
  }
  refresh(); setInterval(refresh, 2500);
})();
