(() => {
 'use strict';
 const message=document.getElementById('download-message'),links=document.getElementById('download-links');
 const query=new URLSearchParams(location.search),id=query.get('tool'),platform=query.get('platform')||'Windows',arch=query.get('architecture')||'x64';
 const https=url=>{const parsed=new URL(url);if(parsed.protocol!=='https:'||parsed.username||parsed.password)throw Error('Invalid publisher link');return parsed.href;};
 fetch('https://raw.githubusercontent.com/samirank/master-it-toolkit/download-catalog/catalog.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('Catalog unavailable');return r.json();}).then(catalog=>{
  const tool=catalog.tools[id];if(!tool)throw Error('Unknown tool. Choose a tool in the dashboard.');
  const choices=tool.assets||[];
  const target=(tool.recommended?.[platform+'/'+arch]||[])[0];
  message.textContent=tool.name+' · '+(tool.version||'Publisher download');
  if(tool.status!=='ready'||!target){
   message.textContent+=' — '+(tool.reason||'Select a platform/package below.');
   for(const asset of choices){const a=document.createElement('a');a.textContent=asset.name;a.href=https(asset.url);links.append(a);}
   if(!choices.length&&tool.source){const a=document.createElement('a');a.textContent='Open publisher website';a.href=https(tool.source);links.append(a);}
   return;
  }
  const asset=choices.find(a=>a.id===target);if(!asset)throw Error('Package changed. Return to the toolkit and refresh.');
  const a=document.createElement('a');a.textContent='Download '+asset.name;a.href=https(asset.url);links.append(a);
  message.textContent+=' — redirecting to the publisher…';location.replace(a.href);
 }).catch(error=>message.textContent=error.message+' Retry when online.');
})();
