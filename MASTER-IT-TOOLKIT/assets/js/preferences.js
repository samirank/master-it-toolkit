/* Recommendation policy; does not change execution rights or consent. */
window.TOOLKIT_PREFERENCES = {
 tier(tool) {
  if(tool.license==='Open source')return 0;
  if(['Free','Included with OS','Included'].includes(tool.license))return 1;
  if(tool.license==='Paid')return 3;
  return 2; // Personal-only, freemium, trial or edition-dependent licensing.
 },
 compare(a,b,mode='recommended') {
  const priority=()=>a.priority.localeCompare(b.priority);
  const automation=()=>Number(b.automationSupport?.level==='documented')-Number(a.automationSupport?.level==='documented');
  if(mode==='priority')return priority()||a.name.localeCompare(b.name);
  return this.tier(a)-this.tier(b)||(mode==='automation'?automation()||priority():priority()||automation())||a.name.localeCompare(b.name);
 }
};
