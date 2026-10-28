// Run real boot navigation with an in-memory API response.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(require('node:path').join(__dirname,'../static/learn.js'),'utf8');
async function initialView(demo,activeExam=null){
  const elements=new Map();let destination;
  const ctx={moduleId:1,demo,state:{draft:null,active_exam:activeExam,completed:[],solved:{},attempts:{}},
    $:selector=>{if(!elements.has(selector))elements.set(selector,{});return elements.get(selector);},
    api:async()=>({lessons:[],module:{},catalog:[],practice:[],lab:null,exam_count:3}),
    setupCourse(){},navigate(view){destination=view;},esc:String};
  vm.createContext(ctx);
  vm.runInContext(source.slice(source.indexOf('async function boot(){'),source.lastIndexOf('boot();')),ctx);
  await ctx.boot();return destination;
}
(async()=>{
  assert.equal(await initialView(false),'home','New students must see the module choices');
  assert.equal(await initialView(true),'basics','Demo keeps the introductory tour');
  assert.equal(await initialView(false,{id:'active'}),'exam','An active test must resume');
  console.log('Course entry, demo introduction and active test navigation verified');
})().catch(error=>{console.error(error);process.exitCode=1;});
