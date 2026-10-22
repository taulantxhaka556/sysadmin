// Run with: node tests/test_beginner_ui.cjs. No browser or network required.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const timers=new Map(),events={};let sequence=0;
const media={matches:false,addEventListener(_,fn){this.changed=fn;}};
const document={hidden:false,activeElement:null,addEventListener(name,fn){events[name]=fn;}};
const context={document,matchMedia:()=>media,
  setInterval:fn=>{timers.set(++sequence,fn);return sequence;},clearInterval:id=>timers.delete(id),
  esc:value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))};
vm.createContext(context);
vm.runInContext(fs.readFileSync(path.join(__dirname,'../static/beginner.js'),'utf8'),context);
const foundations=vm.runInContext('foundations',context),modules=vm.runInContext('moduleScenes',context);
assert.equal(foundations.length,5);assert.equal(Object.keys(modules).length,14);
const kinds=new Set();
for(const scene of [...foundations,...Object.values(modules)]){
  kinds.add(scene.kind);
  for(let step=0;step<scene.steps.length;step++){
    const svg=context.sceneSVG(scene.kind,step);
    assert(svg.includes('role="img"'));assert(svg.includes('<text'));assert(!svg.includes('undefined'));
    assert(scene.steps[step][1].length>20);
  }
}
assert(kinds.size>=10);
assert(!context.glossaryHTML([{term:'<script>',definition:'<img src=x>',example:'"&'}]).includes('<script>'));
const materials=JSON.parse(fs.readFileSync(path.join(__dirname,'../beginner_content.json'),'utf8'));
for(const material of Object.values(materials)){
  const html=context.beginnerLessonHTML({beginner:material});
  assert(html.includes('Новые слова'));assert(html.includes('id="lesson-scene"'));
}
function makeRoot(){
  let html='',buttons={};
  return {isConnected:true,dataset:{},contains:()=>false,
    set innerHTML(value){html=value;buttons={};},get innerHTML(){return html;},
    querySelector(selector){return buttons[selector]??=( {setAttribute(){},focus(){}} );}};
}
const root=makeRoot();context.mountScene(root,foundations[0]);
assert.equal(timers.size,0);assert(root.innerHTML.includes('Шаг 1 из 3'));
root.querySelector('[data-scene-play]').onclick();assert.equal(timers.size,1);
[...timers.values()][0]();assert(root.innerHTML.includes('Шаг 2 из 3'));
root.querySelector('[data-scene-play]').onclick();assert.equal(timers.size,0);
root.querySelector('[data-scene-next]').onclick();assert(root.innerHTML.includes('Шаг 3 из 3'));
root.querySelector('[data-scene-play]').onclick();assert(root.innerHTML.includes('Шаг 1 из 3'));
[...timers.values()][0]();[...timers.values()][0]();assert.equal(timers.size,0);
root.querySelector('[data-scene-play]').onclick();document.hidden=true;events.visibilitychange();assert.equal(timers.size,0);
document.hidden=false;media.matches=true;media.changed();
root.querySelector('[data-scene-play]').onclick();assert.equal(timers.size,0);
assert(root.innerHTML.includes('Анимация отключена'));
media.matches=false;media.changed();root.querySelector('[data-scene-play]').onclick();context.stopBeginner();assert.equal(timers.size,0);
const removed=makeRoot();context.mountScene(removed,foundations[0]);removed.querySelector('[data-scene-play]').onclick();removed.isConnected=false;[...timers.values()][0]();assert.equal(timers.size,0);
// Exercise the actual lesson template, including nested disclosure boundaries.
const learn=fs.readFileSync(path.join(__dirname,'../static/learn.js'),'utf8');
const ui=fs.readFileSync(path.join(__dirname,'../static/course-ui.js'),'utf8');
const nodes={};context.$=selector=>nodes[selector]??=({innerHTML:'',textContent:'',addEventListener(){}});
context.moduleId=1;context.state={completed:[]};context.bindOrders=()=>{};context.mountScene=()=>{};
context.navigate=()=>{};context.renderVisual=()=>{};
const details=JSON.parse(fs.readFileSync(path.join(__dirname,'../detailed_materials.json'),'utf8'));
context.lessons=[{id:'client',title:'Клиент и сервер',visual:'exchange',source:5,minutes:10,lead:'Technical lead',beginner:materials['5'],blocks:[['Разбор','Technical reading']],detail:details['theory:5'],summary:'Exam summary',pitfall:'Pitfall',questions:[]}];
vm.runInContext(ui.slice(ui.indexOf('function detailedReading(')),context);
vm.runInContext(learn.slice(learn.indexOf('function renderLesson('),learn.indexOf('function renderVisual(')),context);
vm.runInContext('renderLesson(lessons[0])',context);
const html=nodes['#content'].innerHTML;
assert(html.includes(materials['5'].intro));assert(!html.includes('Technical lead'));
let depth=0;
for(const match of html.matchAll(/<\/?details\b[^>]*>/g)){
  if(match[0].startsWith('</')){depth--;assert(depth>=0);}
  else{
    if(match[0].includes('id="technical-reading"')||match[0].includes('id="lesson-checks"')){assert.equal(depth,0);assert(!match[0].includes(' open'));}
    depth++;
  }
}
assert.equal(depth,0);
console.log('19 scenes, 60 primers, escaping, playback lifecycle, reduced motion and real lesson disclosure layout verified');
