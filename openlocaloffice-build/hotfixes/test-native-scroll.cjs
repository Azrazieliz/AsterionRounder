/* Prevent scroll regressions: Android must handle one-finger touch/fling.
   Gesture handlers only intercept two-finger pinch; no pointer capture. */
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const code=fs.readFileSync('app/src/main/assets/fg-early-page.js','utf8');
const unified=fs.readFileSync('app/src/main/assets/unified-viewer-controls.js','utf8');
const css=fs.readFileSync('app/src/main/assets/style.css','utf8');
assert(!code.includes('setPointerCapture('),'Progressive reader must not capture swipes');
assert(!code.includes('scroll.scrollTop+=before.y-e.clientY'),
  'Progressive reader must not emulate a native fling as 3mm delta moves');
assert(code.includes('touch-action:pan-x pan-y'),
  'Progressive content must allow native horizontal/vertical scroll');
assert(!unified.includes('oneFinger.x-t.clientX'),
  'Regular comic reader must not override native one-finger movement');
assert(css.includes('touch-action:pan-x pan-y!important'),
  'Normal comic/image reader must allow Android swipe and momentum');
class Element{
 constructor(tag){this.tag=tag;this.children=[];this.listeners={};
   this.style={};this.dataset={};this.hidden=false;this.scrollTop=0;this.scrollLeft=0;
   this.clientHeight=850;this.clientWidth=450;}
 append(...kids){this.children.push(...kids);for(const k of kids)k.parent=this;}
 appendChild(k){this.append(k);}
 remove(){if(this.parent)this.parent.children=this.parent.children.filter(x=>x!==this);}
 setAttribute(){}
 addEventListener(name,handler){(this.listeners[name]??=[]).push(handler);}
 dispatch(name,event){for(const handler of this.listeners[name]||[])handler(event);}
 getBoundingClientRect(){return {top:0,bottom:900,left:0,right:450};}
}
const body=new Element('body'),head=new Element('head');
const document={body,head,createElement:tag=>new Element(tag),
  querySelector:()=>null};
const win={addEventListener(){},loadDocument(){},
  AndroidBridge:{setReadingImmersive(){}}};
vm.runInNewContext(code,{document,window:win,console,Date,Math,
 requestAnimationFrame:fn=>fn()},{filename:'fg-early-page.js'});
const reader=win.FileGestionerEarly;
assert(reader,'Streaming reader missing');
for(let i=0;i<28;i++)
 reader.append('https://fg-assets.invalid/early/test/'+i,'p'+i+'.jpg',i);
const surface=body.children.find(x=>x.className==='fg-progressive-comic');
assert(surface,'Native scroll surface absent');
const scroll=surface.children.find(x=>x.className==='fg-progressive-scroll');
const stack=scroll.children[0];
assert.strictEqual(stack.children.length,28,'Pages 1..28 must be immediately readable');
assert(scroll.listeners.touchstart?.length,'Touch start listener missing');
assert(!scroll.listeners.pointermove?.length,'Pointer movement must not capture scrolling');
const finger=(x,y)=>({clientX:x,clientY:y});
let prevented=0;
scroll.dispatch('touchstart',{touches:[finger(240,440)]});
scroll.dispatch('touchmove',{touches:[finger(240,120)],cancelable:true,
 preventDefault(){prevented++;}});
assert.strictEqual(prevented,0,'One-finger swipe must not prevent native scrolling');
assert.strictEqual(scroll.scrollTop,0,'JavaScript must leave native scroll position alone');
scroll.dispatch('touchcancel',{});
scroll.dispatch('touchstart',{touches:[finger(130,300),finger(260,300)]});
scroll.dispatch('touchmove',{touches:[finger(60,300),finger(330,300)],
 cancelable:true,preventDefault(){prevented++;}});
assert.strictEqual(prevented,1,'Two-finger pinch must remain active');
assert(Number.parseInt(stack.style.width)>100,'Pinch must enlarge content');
scroll.dispatch('touchend',{touches:[],changedTouches:[finger(300,300)]});
const tap=()=>{scroll.dispatch('touchstart',{touches:[finger(180,300)]});
  scroll.dispatch('touchend',{touches:[],changedTouches:[finger(180,300)]});};
tap();tap();
assert.strictEqual(stack.style.width,'100%','Double tap must reset to fit');
console.log('PASS: native momentum scroll is not stolen; 28 streaming pages, pinch and double tap fit.');
