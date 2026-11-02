(()=>{
const style=document.getElementById('tc-page-style');
const hosts=[...document.querySelectorAll('.tc-content-host')];
for(const host of hosts){
 const root=host.attachShadow({mode:'open'});
 root.append(style.content.cloneNode(true),host.querySelector('template').content.cloneNode(true));
 root.querySelectorAll('[contenteditable]').forEach(e=>e.removeAttribute('contenteditable'));
 const pageIndex=[...document.querySelectorAll('.brief-section')].indexOf(host.closest('.brief-section'));
 let pageNumber=root.querySelector('.tc-page-number');
 if(!pageNumber){pageNumber=document.createElement('div');pageNumber.className='tc-page-number';root.querySelector('.slide').append(pageNumber);}
 pageNumber.textContent=(pageIndex+1)+' / '+document.querySelectorAll('.brief-section').length;

 root.addEventListener('click',e=>{
  const link=e.target.closest('a[href^="#"]');
  if(link){e.preventDefault();document.querySelector('aside nav a[href="'+link.getAttribute('href')+'"]')?.click();}
  const tab=e.target.closest('[data-demo]');if(tab){const parent=tab.closest('.mock');parent.querySelectorAll('[data-demo]').forEach(x=>x.classList.toggle('active',x===tab));parent.querySelectorAll('[data-panel]').forEach(x=>x.hidden=x.dataset.panel!==tab.dataset.demo);}
  const unlock=e.target.closest('[data-preview-unlock]');if(unlock)unlock.textContent=unlock.textContent==='已解锁（演示）'?'预览解锁':'已解锁（演示）';
 });
}
function fit(){for(const host of hosts){if(!host.clientWidth)continue;const root=host.shadowRoot,canvas=root.getElementById('canvas'),claim=root.querySelector('.claim'),body=root.querySelector('.body');canvas.style.transform='scale('+host.clientWidth/1280+')';if(claim&&body){const bottom=111+claim.offsetHeight;const top=bottom+Math.max(0,210-bottom)/2;body.style.top=top+'px';body.style.height=(720-top-24)+'px';}}}
new ResizeObserver(fit).observe(document.querySelector('main'));
window.addEventListener('resize',fit);window.addEventListener('tc-fit',fit);document.fonts.ready.then(fit);
new MutationObserver(fit).observe(document.documentElement,{attributes:true,attributeFilter:['data-language']});
new MutationObserver(fit).observe(document.querySelector('main'),{subtree:true,attributes:true,attributeFilter:['hidden']});
let timer;window.addEventListener('pointermove',()=>{document.body.classList.add('controls-visible');clearTimeout(timer);timer=setTimeout(()=>document.body.classList.remove('controls-visible'),1800);});fit();
})();
