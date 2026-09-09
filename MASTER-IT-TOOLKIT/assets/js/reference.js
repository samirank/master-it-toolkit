'use strict';
try { document.documentElement.dataset.theme=JSON.parse((localStorage.getItem('master-it.v1.preferences')||localStorage.getItem('ventoy.v1.preferences'))||'{}').theme||'dark'; } catch {}
document.querySelector('#print-reference')?.addEventListener('click',()=>window.print());
document.querySelector('#boot-search')?.addEventListener('input',e=>{for(const row of document.querySelectorAll('#boot-table tbody tr'))row.hidden=!row.textContent.toLowerCase().includes(e.target.value.toLowerCase());});
