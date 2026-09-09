/* Relative catalog paths stay portable; filesystem paths resolve at runtime. */
(function (root) {
  'use strict';
  function relativeUrl(path) {
    if (typeof path !== 'string' || !path || /^[a-z]+:|^[\/\\]/i.test(path) || path.split(/[\/\\]/).includes('..')) return null;
    return './' + path.replace(/\\/g, '/').split('/').map(encodeURIComponent).join('/');
  }
  function resolve(path, pageUrl) {
    const relative = relativeUrl(path);
    if (!relative) return {url:null, filesystemPath:null, local:false};
    const page = new URL(pageUrl);
    if (page.protocol !== 'file:') return {url:null, filesystemPath:null, local:false};
    const url = new URL(relative, page);
    let native = decodeURIComponent(url.pathname);
    if (url.hostname) native = '\\\\' + url.hostname + native.replace(/\//g, '\\');
    else if (/^\/[A-Za-z]:\//.test(native)) native = native.slice(1).replace(/\//g, '\\');
    return {url:url.href, filesystemPath:native, local:true};
  }
  const api = {relativeUrl, resolve};
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.ToolkitPaths = api;
})(typeof window === 'object' ? window : globalThis);
