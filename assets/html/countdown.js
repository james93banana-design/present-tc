(()=>{
'use strict';
const input=document.getElementById('presentation-minutes');
const clock=document.getElementById('presentation-countdown');
const sections=[...document.querySelectorAll('.brief-section')];
const storageKey='present-tc-presentation-clock-v1:'+(document.documentElement.dataset.layoutRevision||location.pathname);
let state={minutes:Number(input.value)||60,deadline:null};
try{const saved=JSON.parse(sessionStorage.getItem(storageKey));if(saved&&saved.minutes>0&&Number.isFinite(saved.minutes)&&(saved.deadline===null||Number.isFinite(saved.deadline)))state=saved;}catch(e){}
input.value=String(state.minutes);
input.setAttribute('value',String(state.minutes));
function persist(){try{sessionStorage.setItem(storageKey,JSON.stringify(state));}catch(e){}}
function render(){
 const presenting=document.body.classList.contains('presentation');
 clock.hidden=!presenting||sections.some(section=>section.id==='cover'&&!section.hidden);
 const remaining=state.deadline===null?state.minutes*60000:Math.max(0,state.deadline-Date.now());
 const seconds=Math.ceil(remaining/1000);
 clock.textContent=Math.floor(seconds/60)+':'+String(seconds%60).padStart(2,'0');
 const index=sections.findIndex(section=>!section.hidden);
 clock.dataset.background=sections[index]?.dataset.timerBackground==='white'?'white':'transparent';
 const remainingPages=sections.length-Math.max(0,index+1);
 const remainingPageShare=remainingPages/sections.length;
 const remainingTimeShare=remaining/(state.minutes*60000);
 const warning=state.deadline!==null&&(remaining===0||remainingPageShare-remainingTimeShare>0.15+1e-9);
 clock.classList.toggle('behind-schedule',warning);
 clock.setAttribute('aria-label','剩余时间 '+Math.floor(seconds/60)+' 分 '+seconds%60+' 秒'+(warning?'，请加快进度':''));
 clock.title=warning?'剩余时间占比比剩余页数占比低超过 15 个百分点':'退出和重新进入 PRESENT 不会重置；修改分钟数可重新计时';
}
function onPresentation(){
 if(document.body.classList.contains('presentation')&&state.deadline===null){state.deadline=Date.now()+state.minutes*60000;persist();}
 render();
}
function resetFromInput(){
 const minutes=Number(input.value);
 if(!input.value||!Number.isFinite(minutes)||minutes<=0){input.setCustomValidity('请输入大于 0 的有效分钟数');return;}
 input.setCustomValidity('');state={minutes,deadline:null};input.setAttribute('value',String(minutes));persist();render();
}
input.addEventListener('input',resetFromInput);
input.addEventListener('change',resetFromInput);
input.addEventListener('blur',()=>{if(!input.checkValidity()){input.value=String(state.minutes);input.setCustomValidity('');}});
new MutationObserver(onPresentation).observe(document.body,{attributes:true,attributeFilter:['class']});
new MutationObserver(render).observe(document.querySelector('main'),{subtree:true,attributes:true,attributeFilter:['hidden']});
document.addEventListener('visibilitychange',render);
window.addEventListener('pageshow',render);
setInterval(render,250);onPresentation();
})();
