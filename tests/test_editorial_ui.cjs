// Presentation regression checks. Run: node tests/test_editorial_ui.cjs
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const root=path.join(__dirname,'../static');
const ctx={document:{addEventListener(){}},moduleId:1,demo:false,
  esc:s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])),
  course:{title:'Основы',goal:'Базовый курс'},
  state:{completed:[],solved:{},unlocked:['client'],best:null,passed:false},
  lessons:[{id:'client',title:'Кто просит, а кто отвечает?',minutes:10,questions:[]},{id:'devices',title:'Устройства',minutes:10,questions:[]}],
  catalog:[{id:1,title:'Как устроена сеть',goal:'Простой обмен данными',available:true,passed:false},{id:2,title:'Канальный уровень',goal:'Ethernet',available:false,passed:false},{id:3,title:'Адресация',goal:'IP',available:false,passed:false},{id:4,title:'VLAN',goal:'Сегменты',available:false,passed:false}]};
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(path.join(root,'editorial.js'),'utf8'),ctx);
const ui=fs.readFileSync(path.join(root,'course-ui.js'),'utf8');
vm.runInContext(ui.slice(ui.indexOf('function moduleUrl('),ui.indexOf('function setupCourse(')),ctx);
vm.runInContext(ui.slice(ui.indexOf('function courseMap('),ui.indexOf('function practiceCards(')),ctx);
let html=ctx.editorialHomeHTML();
assert(html.includes('id="continue"'));assert(html.includes('id="open-basics"'));
assert.equal((html.match(/class="editorial-module"/g)||[]).length,4);
assert(!html.includes('href="/learn/2"'));assert(html.includes('aria-disabled="true"'));
assert(html.includes('data-lesson="devices" disabled'));
assert(html.includes('<strong>—</strong>'));assert(html.includes('0 / 2'));
assert(html.includes('viewBox="0 0 640 240"'));assert(!html.includes('Александр'));
ctx.state.best=0;html=ctx.editorialHomeHTML();assert(html.includes('0/100'));
ctx.state.passed=true;html=ctx.editorialHomeHTML();assert(html.includes('href="/learn/2"'));
assert(!html.includes('href="/learn/3"'));
ctx.state.passed=false;
ctx.catalog.forEach(m=>{m.available=true;});
html=ctx.editorialHomeHTML();
for(const id of [1,2,3,4])assert(html.includes(`href="/learn/${id}"`));
assert(!html.includes('aria-disabled="true"'));
const controls=new Map();let selectedModule;
ctx.$=selector=>{if(!controls.has(selector))controls.set(selector,{});return controls.get(selector);};
ctx.$('#basics-nav');
ctx.location={assign:url=>{selectedModule=url;}};
vm.runInContext(ui.slice(ui.indexOf('function setupCourse('),ui.indexOf('function courseMap(')),ctx);
ctx.setupCourse();
assert(!ctx.$('#module-picker').innerHTML.includes('disabled'));
ctx.$('#module-picker').onchange({target:{value:'4'}});
assert.equal(selectedModule,'/learn/4');
ctx.catalog[0].title='<script>alert(1)</script>';html=ctx.editorialHomeHTML();assert(!html.includes('<script>'));assert(html.includes('&lt;script&gt;'));
ctx.moduleId=2;ctx.course={title:'Адреса и <сети>',goal:'Разбор'};html=ctx.editorialHomeHTML();
assert(!html.includes('id="open-basics"'));assert(html.includes('Адреса и &lt;сети&gt;'));
const template=fs.readFileSync(path.join(root,'learn.html'),'utf8');
for(const id of ['content','lesson-nav','lab-status','exam-status','sidebar-progress','module-picker','mode-banner','theme','toast'])assert(template.includes(`id="${id}"`),id);
for(const marker of ['{{DEMO}}','{{MODULE}}','{{ACCOUNT}}'])assert.equal(template.split(marker).length-1,1,marker);
assert(template.includes('data-course-home'));assert(template.includes('class="course-outline"'));
for(const href of ['/assignments','/journal','/trainer','/exam'])assert(template.includes(`href="${href}"`));
for(const name of ['editorial.js','editorial.css','editorial-font.css'])assert(fs.statSync(path.join(root,name)).size>0);
const css=fs.readFileSync(path.join(root,'editorial.css'),'utf8');
assert(css.includes('repeat(4,minmax(0,1fr))'));assert(css.includes('@media(max-width:900px)'));assert(css.includes('@media(max-width:600px)'));assert(css.includes('prefers-reduced-motion'));
console.log('Editorial rendering, module links and picker, progress, escaping and responsive rules verified');
