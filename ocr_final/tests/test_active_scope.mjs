import test from 'node:test';
import assert from 'node:assert/strict';
import { availableOptions, scopeNotice } from '../frontend/active_scope.mjs';
const options = ['AIT','DSBA','IT','BIT'].map(value => ({value,versions:[{value:'latest'},{value:'old'},{value:'all versions'}]}));
const health = {build_id:'source-bit',queryable_database_count:2,build_contract:{partial:true},databases:[
 {program_id:'BIT-coop',curriculum_version:2565,queryable:true},
 {program_id:'BIT-no-coop',curriculum_version:2565,queryable:true},
 {program_id:'IT-coop',curriculum_version:2560,queryable:false}],
 extraction_provenance:{reviewed_input_scope:'font-encoding-only; no course corrections',profiles:[{method:'pdf-text-tables'}]}};
test('two active BIT plans expose only BIT latest; failed databases cannot enable selections',()=> {
 assert.deepEqual(availableOptions(options,health),[{value:'BIT',versions:[{value:'latest'}]}]);
 assert.deepEqual(availableOptions(options,null),[]);
 assert.deepEqual(availableOptions(options,{databases:[]}),[]);
});
test('scope and native reviewed path cannot be represented as full reconstruction or vision OCR',()=> {
 const text=scopeNotice(health);assert.match(text,/2 profiles/);assert.match(text,/font encoding/);assert.match(text,/ไม่ใช่ vision OCR/);assert.match(text,/ไม่ใช่การสร้างทั้งระบบครบ 14 profiles/);
});
test('old-only active build cannot expose latest or cross-version choice',()=> {
 assert.deepEqual(availableOptions(options,{databases:[{queryable:true,program_id:'DSBA-coop',curriculum_version:2560}]}),[{value:'DSBA',versions:[{value:'old'}]}]);
});

import { readFileSync } from 'node:fs';
import vm from 'node:vm';
function node(tag='div') {
 return {tagName:tag,value:'',textContent:'',disabled:false,children:[],dataset:{},
  classList:{toggle(){},add(){},remove(){}},setAttribute(){},removeAttribute(){},addEventListener(){},querySelectorAll(){return []},
  replaceChildren(){this.children=[];this.value=''},append(...items){this.children.push(...items);if(this.tagName==='select'&&!this.value)this.value=items[0]?.value || ''}};
}
async function initialize(health,fail=false) {
 const nodes=new Map();const document={querySelector(id){if(!nodes.has(id))nodes.set(id,node(id.endsWith('-select')?'select':'div'));return nodes.get(id)},createElement:node};
 const code=readFileSync(new URL('../frontend/app.js',import.meta.url),'utf8').replace(/^import .*;$/gm,'');
 const context={document,window:{location:{pathname:'/frontend/',origin:'http://127.0.0.1:8765'}},availableOptions,scopeNotice,
  fetch:()=>fail?Promise.reject(new Error('offline')):Promise.resolve({ok:true,json:async()=>health})};
 vm.runInNewContext(code,context);for(let i=0;i<5;i++)await new Promise(resolve=>setImmediate(resolve));return nodes;
}
test('application initialization exposes only available controls and blocks failed health',async()=> {
 const nodes=await initialize(health);assert.deepEqual(nodes.get('#curriculum-select').children.map(x=>x.value),['BIT']);
 assert.deepEqual(nodes.get('#version-select').children.map(x=>x.value),['latest']);assert.equal(nodes.get('#ask-button').disabled,false);
 const failed=await initialize(null,true);assert.equal(failed.get('#ask-button').disabled,true);assert.equal(failed.get('#curriculum-select').disabled,true);assert.equal(failed.get('#curriculum-select').children.length,0);
});
