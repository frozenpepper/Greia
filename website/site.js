document.documentElement.classList.add('has-js');
const $ = selector => document.querySelector(selector);
const $$ = selector => [...document.querySelectorAll(selector)];
const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;

// The original 52 PNGs remain the animation authority; the wide SVG only extends their landscape.
const frames = Array.from({length: 52}, (_, index) => {
  const image = new Image();
  image.src = `assets/boot/frame_${String(index).padStart(4, '0')}.png`;
  return image;
});
let openingRun = 0;
let openingFrame = 0;
function finishOpening(run) {
  if (run !== openingRun) return;
  cancelAnimationFrame(openingFrame);
  $('#boot-frame').src = frames[51].src;
  $('#intro-counter').textContent = '52 / 52';
  document.body.classList.remove('is-opening');
  document.body.classList.add('is-ready');
}
async function playOpening() {
  const run = ++openingRun;
  cancelAnimationFrame(openingFrame);
  document.body.classList.add('is-opening');
  document.body.classList.remove('is-ready');
  $('#boot-frame').src = frames[0].src;
  $('#intro-counter').textContent = '01 / 52';
  if (reducedMotion || (location.hash && location.hash !== '#top')) { finishOpening(run); return; }
  await Promise.all(frames.map(image => image.decode().catch(() => {})));
  if (run !== openingRun) return;
  let start;
  let previous = -1;
  function tick(time) {
    if (run !== openingRun) return;
    start ??= time;
    const elapsed = Math.min(1, (time - start) / 4700);
    const index = Math.min(51, Math.floor(elapsed * 52));
    if (index !== previous) {
      $('#boot-frame').src = frames[index].src;
      $('#intro-counter').textContent = `${String(index + 1).padStart(2, '0')} / 52`;
      previous = index;
    }
    if (elapsed < 1) openingFrame = requestAnimationFrame(tick);
    else setTimeout(() => finishOpening(run), 350);
  }
  openingFrame = requestAnimationFrame(tick);
}
$('#skip-intro').addEventListener('click', () => finishOpening(++openingRun));
$('#replay-intro').addEventListener('click', () => {
  window.scrollTo({top: 0, behavior: reducedMotion ? 'instant' : 'smooth'});
  playOpening();
});
playOpening();

// A small, bounded swarm moves while the opening is visible. Pointer motion
// gently pulls nearby lights; the lights continue wandering when it stops.
const fireflyField = $('#fireflies');
const fireflyStage = $('#top');
const fireflyMotion = !reducedMotion;
const fireflyPointer = {x:0, y:0, active:false};
let fireflyWidth = fireflyStage.clientWidth;
let fireflyHeight = fireflyStage.clientHeight;
let fireflyVisible = true;
let fireflyFrame = 0;
let fireflyLastTime = 0;
let randomSeed = 9217;
function fireflyRandom() {
  randomSeed = (randomSeed * 1664525 + 1013904223) >>> 0;
  return randomSeed / 4294967296;
}
const fireflies = Array.from({length: innerWidth < 620 ? 13 : 19}, (_, index) => {
  const node = document.createElement('i');
  const size = 3 + fireflyRandom() * 4;
  node.style.cssText = `left:0;top:0;width:${size}px;height:${size}px;animation:none;opacity:${.45+fireflyRandom()*.45}`;
  fireflyField.append(node);
  const light = {
    node,
    x:fireflyRandom()*fireflyWidth,
    y:fireflyHeight*(.2+fireflyRandom()*.72),
    vx:(fireflyRandom()-.5)*26,
    vy:(fireflyRandom()-.5)*20,
    phase:index*.77
  };
  node.style.transform = `translate3d(${light.x}px,${light.y}px,0)`;
  return light;
});
function animateFireflies(time) {
  if (!fireflyVisible || document.hidden) {fireflyFrame=0;return;}
  const dt=Math.min(.04,(time-(fireflyLastTime||time))/1000);
  fireflyLastTime=time;
  for (const light of fireflies) {
    const driftX=Math.sin(time*.00042+light.phase)*9;
    const driftY=Math.cos(time*.00056+light.phase)*12;
    let pullX=0,pullY=0;
    if (fireflyPointer.active) {
      const dx=fireflyPointer.x-light.x,dy=fireflyPointer.y-light.y;
      const distance=Math.hypot(dx,dy);
      if (distance>1 && distance<300) {
        const pull=115*(1-distance/300);
        pullX=dx/distance*pull;
        pullY=dy/distance*pull;
      }
    }
    light.vx=(light.vx+(driftX+pullX)*dt)*Math.pow(.993,dt*60);
    light.vy=(light.vy+(driftY+pullY)*dt)*Math.pow(.993,dt*60);
    light.x+=light.vx*dt;
    light.y+=light.vy*dt;
    if(light.x<-20)light.x=fireflyWidth+20;
    if(light.x>fireflyWidth+20)light.x=-20;
    if(light.y<fireflyHeight*.12)light.y=fireflyHeight*.9;
    if(light.y>fireflyHeight*.95)light.y=fireflyHeight*.12;
    light.node.style.transform=`translate3d(${light.x.toFixed(1)}px,${light.y.toFixed(1)}px,0)`;
  }
  fireflyFrame=requestAnimationFrame(animateFireflies);
}
function startFireflies() {
  if (!fireflyMotion || !fireflyVisible || document.hidden || fireflyFrame) return;
  fireflyLastTime=0;
  fireflyFrame=requestAnimationFrame(animateFireflies);
}
fireflyStage.addEventListener('pointermove',event=>{
  const bounds=fireflyStage.getBoundingClientRect();
  fireflyPointer.x=event.clientX-bounds.left;
  fireflyPointer.y=event.clientY-bounds.top;
  fireflyPointer.active=true;
},{passive:true});
fireflyStage.addEventListener('pointerleave',()=>{fireflyPointer.active=false;});
addEventListener('resize',()=>{
  fireflyWidth=fireflyStage.clientWidth;
  fireflyHeight=fireflyStage.clientHeight;
},{passive:true});
document.addEventListener('visibilitychange',()=>{
  if(document.hidden){cancelAnimationFrame(fireflyFrame);fireflyFrame=0;}
  else startFireflies();
});
new IntersectionObserver(([entry])=>{
  fireflyVisible=entry.isIntersecting;
  if(fireflyVisible)startFireflies();
  else{cancelAnimationFrame(fireflyFrame);fireflyFrame=0;}
},{threshold:0}).observe(fireflyStage);
startFireflies();

const nav = $('#site-nav');
const menuToggle = $('#menu-toggle');
menuToggle.addEventListener('click', () => {
  const opened = nav.classList.toggle('is-open');
  menuToggle.setAttribute('aria-expanded', String(opened));
});
nav.querySelectorAll('a').forEach(link => link.addEventListener('click', () => {
  nav.classList.remove('is-open');
  menuToggle.setAttribute('aria-expanded', 'false');
}));
document.addEventListener('keydown', event => {
  if (event.key !== 'Escape') return;
  nav.classList.remove('is-open');
  menuToggle.setAttribute('aria-expanded', 'false');
  if ($('#shot-dialog').open) $('#shot-dialog').close();
  if (document.body.classList.contains('is-opening')) finishOpening(++openingRun);
});
function onScroll() {
  const maximum = document.documentElement.scrollHeight - innerHeight;
  $('#reading-progress').style.width = `${maximum > 0 ? Math.min(100, scrollY / maximum * 100) : 0}%`;
  $('#site-header').classList.toggle('is-scrolled', scrollY > 80);
}
addEventListener('scroll', onScroll, {passive:true});
onScroll();
const revealObserver = new IntersectionObserver(entries => entries.forEach(entry => {
  if (entry.isIntersecting) { entry.target.classList.add('is-visible'); revealObserver.unobserve(entry.target); }
}), {threshold:.08});
$$('.section-heading,.mission-head,.explorer,.hardware-layout,.architecture-interactive,.parent-grid,.creation-lab,.voice-layout,.mission-points,.architecture-more,.parent-feature-row,.faq-grid,.os-flow,.impact-grid,.language-pair').forEach(node => revealObserver.observe(node));

const gallery = [
  {category:'shell',label:'GREIA SHELL',title:'A starting place of their own.',description:'After selecting a child profile, Greia opens into large Collections and Activity cards. These are places to create, play, learn and explore, with no ordinary desktop or browser to navigate.',facts:['ENGLISH UI','CHILD PROFILE','NO DESKTOP'],source:'English real-service Simulator · 23 September 2026',src:'assets/screens/shell-en.png',alt:'English Greia Shell showing the Create collection and Activity cards'},
  {category:'shell',label:'PROFILE PICKER',title:'Whose computer is it today?',description:'Greia asks who is here at each start. A child enters their own profile, with their creations, Activity saves and progress kept separately.',facts:['CHOOSE A PROFILE','PERSONAL WORK','SHARED MACHINE'],source:'English real-service Simulator · 23 September 2026',src:'assets/screens/profile-en.png',alt:'English Greia profile picker with Explorer profile'},
  {category:'play',label:'MAGIC AQUARIUM',title:'Life beneath the surface.',description:'Fish, food, bubbles and daylight make a lively place to explore. The scene remains inside Greia, with the protected Home control always available.',facts:['POINTER PLAY','LIVING SCENE','GREIA HOME'],source:'English real-service Simulator · 23 September 2026',src:'assets/screens/aquarium-en.png',alt:'English Magic Aquarium Activity with fish and play controls'},
  {category:'play',label:'MAGICAL BAKERY',title:'A recipe for playful thinking.',description:'A child fills a sweet order with visible ingredients, then can try patterns or free play. The challenge is carried by action and pictures, not a worksheet.',facts:['COUNTING','PATTERNS','FREE PLAY'],source:'English real-service Simulator · 23 September 2026',src:'assets/screens/bakery-en.png',alt:'English Magical Bakery Activity with a strawberry and blueberry order'},
  {category:'explore',label:'ENCYCLOPEDIA',title:'Follow a question anywhere.',description:'Animals, space, Earth, the body, machines and history become visual places to enter. This is the evolving development Encyclopedia, not final release-content acceptance.',facts:['SIX TOPIC FAMILIES','VISUAL DISCOVERY','ENGLISH UI'],source:'English real-service Simulator · 23 September 2026',src:'assets/screens/encyclopedia-en.png',alt:'English Greia Encyclopedia home with illustrated topic cards'},
  {category:'explore',label:'NUMBER TRAIN',title:'Numbers can move.',description:'A train turns simple addition into visible objects and a journey. Common Greia input and protected Home keep the interaction familiar.',facts:['EARLY MATHS','LEARN BY DOING','DIRECTIONAL INPUT'],source:'English real-service Simulator · 23 September 2026',src:'assets/screens/train-en.png',alt:'Number Train Activity with apples, tracks and number choices'},
  {category:'play',label:'MY CUTE PET',title:'Care is a kind of play.',description:'A pet invites children to feed, bathe, play, rest and decorate. Activities can support care and routines as well as scores and puzzles.',facts:['CARE ROUTINE','CHILD CHOICE','RETURN LATER'],source:'English real-service Simulator · 23 September 2026',src:'assets/screens/pet-en.png',alt:'English My Cute Pet Activity with a cat and care controls'},
  {category:'play',label:'MAGIC ORCHESTRA',title:'Try a sound. Make a pattern.',description:'Instruments and large colourful notes make room for experimentation. Sound is part of the action, not just background decoration.',facts:['MUSIC','PATTERNS','SOUND'],source:'English real-service Simulator · 23 September 2026',src:'assets/screens/orchestra-en.png',alt:'English Magic Orchestra Activity with instruments and musical notes'},
  {category:'explore',label:'WORD FOREST',title:'A letter can become a discovery.',description:'A spoken and pictured word anchors an early reading choice. Greia can make learning audible and visual for children who are still becoming readers.',facts:['EARLY LITERACY','AUDIO CUE','PICTURE FIRST'],source:'English real-service Simulator · 23 September 2026',src:'assets/screens/word-forest-en.png',alt:'English Word Forest Activity showing Apple and large letter choices'},
  {category:'create',label:'WRITING',title:'An empty page is an invitation.',description:'Greia includes a first-party Writing Activity with large child-sized space, profile-scoped saving and no Linux file manager in the way.',facts:['CREATE','LARGE PAGE','PROFILE SAVE'],source:'English real-service Simulator · 23 September 2026',src:'assets/screens/writing-en.png',alt:'Greia Writing Activity with a large blank page and child-sized controls'}
];
let filtered = gallery.map((_,index) => index);
let selected = 0;
const rail = $('#thumb-rail');
gallery.forEach((item, index) => {
  const button = document.createElement('button');
  button.type = 'button';
  button.dataset.index = String(index);
  button.setAttribute('aria-label', `Show ${item.label.toLowerCase()} screenshot`);
  const image = document.createElement('img'); image.src = item.src; image.alt = ''; image.loading = 'lazy';
  const caption = document.createElement('span'); caption.textContent = `${String(index+1).padStart(2,'0')} / ${item.label}`;
  button.append(image,caption);
  button.addEventListener('click', () => showGallery(index));
  rail.append(button);
});
function showGallery(index, scrollRail = true) {
  selected = index;
  const item = gallery[index];
  $('#gallery-image').src = item.src;
  $('#gallery-image').alt = item.alt;
  $('#gallery-category').textContent = item.label;
  $('#gallery-title').textContent = item.title;
  $('#gallery-description').textContent = item.description;
  $('#gallery-facts').replaceChildren(...item.facts.map(fact => {const span=document.createElement('span');span.textContent=fact;return span;}));
  $('#gallery-source').textContent = item.source;
  $('#gallery-count').textContent = `${String(filtered.indexOf(index)+1).padStart(2,'0')} / ${String(filtered.length).padStart(2,'0')}`;
  $$('#thumb-rail button').forEach(button => {button.classList.toggle('is-active',Number(button.dataset.index)===index);button.hidden=!filtered.includes(Number(button.dataset.index));});
  if (scrollRail) {
    const thumb = rail.querySelector(`[data-index="${index}"]`);
    if (thumb) rail.scrollTo({left:thumb.offsetLeft - rail.offsetLeft - (rail.clientWidth - thumb.clientWidth)/2,behavior:reducedMotion?'instant':'smooth'});
  }
}
function moveGallery(delta) {showGallery(filtered[(filtered.indexOf(selected)+delta+filtered.length)%filtered.length]);}
$('#gallery-prev').addEventListener('click', () => moveGallery(-1));
$('#gallery-next').addEventListener('click', () => moveGallery(1));
$$('[data-filter]').forEach(button => button.addEventListener('click', () => {
  filtered = gallery.map((item,index)=>item.category===button.dataset.filter||button.dataset.filter==='all'?index:-1).filter(index=>index>=0);
  $$('[data-filter]').forEach(other => other.setAttribute('aria-pressed',String(other===button)));
  showGallery(filtered[0]);
}));
showGallery(0, false);
const dialog = $('#shot-dialog');
$('#gallery-zoom').addEventListener('click', () => {
  $('#dialog-image').src = gallery[selected].src;
  $('#dialog-image').alt = gallery[selected].alt;
  $('#dialog-caption').textContent = `${gallery[selected].label} · ${gallery[selected].source}`;
  dialog.showModal();
});
$('#parent-zoom').addEventListener('click', () => {
  $('#dialog-image').src = 'assets/parent/this-greia-1024x600.png';
  $('#dialog-image').alt = 'Readable single-screen Greia Parents development capture showing This Greia device status';
  $('#dialog-caption').textContent = 'GREIA PARENTS · This Greia single viewport · 2 September 2026';
  dialog.showModal();
});
$('#close-shot').addEventListener('click', () => dialog.close());
dialog.addEventListener('click', event => {if (event.target===dialog) dialog.close();});

const hardware = {
  old:{label:'MAKE GOOD HARDWARE USEFUL AGAIN',title:'From netbooks onward.',description:'Greia aims to make older laptops and small PCs useful, legible and pleasant for children. The first-generation Acer Aspire One is our toughest low-resource reference, not the only computer we care about.',specs:[['Old → new','one child experience'],['Low resource','part of the design'],['Device by device','compatibility verified']],note:'Hardware support is checked per device and image. This is not a promise that every PC has passed release acceptance.'},
  pi400:{label:'A COMPUTER INSIDE THE KEYBOARD',title:'The Pi 400 is wonderfully practical.',description:'Connect a Raspberry Pi 400 to a screen, supply power, and give the child the keyboard itself. Greia is designed to make that small, self-contained setup feel like a complete child computer.',specs:[['Keyboard PC','simple to hand over'],['ARM','first-class target'],['Same Greia','same child rules']],note:'The Pi 400 is an explicit reference target. Its release image and graphics/input evidence still need device-specific verification.'},
  pi500:{label:'A COMPUTER INSIDE THE KEYBOARD',title:'The Pi 500 carries the same idea further.',description:'The Pi 500 combines a keyboard and computer in one compact device. Greia aims to bring the same child Shell, Activities and Parent control there without inventing a separate ARM-only experience.',specs:[['Keyboard PC','small footprint'],['ARM','first-class target'],['Portable','child data']],note:'The Pi 500 is an explicit target; its ordinary-family release support is not yet certified.'},
  other:{label:'ONE PLATFORM, MANY DEVICE CLASSES',title:'A broad hardware ambition.',description:'The long-term goal includes older and newer x86 computers, ARM boards and other appropriate devices. Greia keeps the child-facing contract steady while hardware adapters and image support vary underneath.',specs:[['x86 + ARM','co-equal direction'],['One Shell','shared experience'],['Tested scope','named per release']],note:'A future download must name exactly which models, input and graphics paths it has actually passed.'}
};
$$('[data-hardware]').forEach(button => button.addEventListener('click', () => {
  const data=hardware[button.dataset.hardware];
  $('#hardware-label').textContent=data.label;$('#hardware-title').textContent=data.title;$('#hardware-description').textContent=data.description;$('#hardware-note').textContent=data.note;
  $('#hardware-specs').replaceChildren(...data.specs.map(([value,label])=>{const div=document.createElement('div');const strong=document.createElement('strong');strong.textContent=value;const span=document.createElement('span');span.textContent=label;div.append(strong,span);return div;}));
  $$('[data-hardware]').forEach(other=>other.setAttribute('aria-pressed',String(other===button)));
}));
const layers = {
  child:{kicker:'01 / THE CHILD’S WORLD',title:'A place they can learn by using.',description:'Each child explicitly chooses a Greia profile. The Shell presents Activities in understandable Collections, and Greia keeps a real Home control available above an Activity so a child always has a way back.',points:['No login prompt, desktop, file manager or browser chrome during normal child use.','A profile owns the child’s saves, creations, progress and language state.','Home belongs to Greia, never to the Activity rendering underneath it.']},
  activity:{kicker:'02 / ACTIVITIES',title:'Different ideas. One dependable contract.',description:'Writing, Painting, a story, a game or a science toy are all Activities. Python, Web and future runtimes are adapters beneath shared lifecycle, storage, package and input rules.',points:['Built-in Activities follow the same lifecycle and profile boundaries as independent ones.','Each Activity declares its interaction profile and required capabilities.','An Activity reports facts; Greia owns global progression and awards.']},
  platform:{kicker:'03 / GREIA’S SHARED CORE',title:'The quiet machinery parents can trust.',description:'Profiles, saves, permissions, progression, package trust, parent policy, Home/Back and input normalization have one platform owner. Activity authors can focus on what a child does inside their experience.',points:['Parent visibility is applied before child discovery.','Packages are checked before installation; removable media never autoruns code.','The platform keeps resource use bounded for the low-memory reference.']},
  hardware:{kicker:'04 / THE COMPUTER BELOW',title:'Old x86 and new ARM under the same roof.',description:'Linux and Greia-owned hardware adapters manage devices, graphics, sound and physical input. The target is a minimal appliance session, not a general desktop environment.',points:['The Acer Aspire One and Raspberry Pi 400/500 are explicit reference classes.','Portable child data should move across architecture families.','Production graphics/session selection and device acceptance are still active work.']}
};
$$('[data-architecture]').forEach(button=>button.addEventListener('click',()=>{
  const data=layers[button.dataset.architecture];
  $('#architecture-kicker').textContent=data.kicker;$('#architecture-title').textContent=data.title;$('#architecture-description').textContent=data.description;
  $('#architecture-list').replaceChildren(...data.points.map(point=>{const li=document.createElement('li');li.textContent=point;return li;}));
  $$('[data-architecture]').forEach(other=>other.setAttribute('aria-pressed',String(other===button)));
}));
const parentTopics = {
  profiles:{kicker:'ONE CHILD AT A TIME',title:'A real place for each child.',description:'A child picks their profile at boot. Writing, drawings, Activity saves, progress and language preferences belong to that profile.',points:['Separate creations and Activity data.','Age suitability and challenge are different choices.','Parents choose which Activities this child sees.'],note:'The screenshot at left is the real “This Greia” development-client viewport. These buttons explain other Parent capabilities without changing that image.'},
  discovery:{kicker:'VISIBLE TO THIS CHILD',title:'Choose what appears.',description:'Greia Parents can set age and challenge intent, then always show or always hide an individual Activity for a child. Greia applies that choice before showing the catalogue.',points:['Explicit Parent choices override automatic recommendations.','An Activity can be installed without being shown to everyone.','Hiding does not delete a child’s saved work.'],note:'Parent policy is implemented in current source/API/client; family usability and release acceptance are separate.'},
  device:{kicker:'THE COMPUTER, WITHOUT LINUX ADMIN',title:'A useful device dashboard.',description:'The screenshot at left is the real development “This Greia” page. It brings system health, network and language, supported input, audio, security and connected Parent devices into one place.',points:['Settings are typed and bounded by Greia.','Controls appear only when device capabilities are reported.','A local network lets the parent manage the device from another screen.'],note:'This is one readable 1024×600 viewport capture. It does not prove every setting works on every physical model.'},
  install:{kicker:'PARENT-AUTHORIZED ACTIVITY INSTALL',title:'New worlds are a grown-up choice.',description:'The intended individual package is a .greiaactivity file. Greia checks archive shape, rules, compatibility and source/trust information before Parent approval and installation.',points:['A file extension alone never proves trust.','Package installation and child visibility are separate choices.','The public catalogue and complete release update lifecycle are still being built.'],note:'A bounded new-install service exists in development. Public downloadable packages are not yet published on this site.'}
};
$$('[data-parent]').forEach(button=>button.addEventListener('click',()=>{
  const data=parentTopics[button.dataset.parent];
  $('#parent-kicker').textContent=data.kicker;$('#parent-title').textContent=data.title;$('#parent-description').textContent=data.description;$('#parent-note').textContent=data.note;
  $('#parent-points').replaceChildren(...data.points.map(point=>{const li=document.createElement('li');li.textContent=point;return li;}));
  $$('[data-parent]').forEach(other=>other.setAttribute('aria-pressed',String(other===button)));
}));
const ideas={
  garden:{title:'Our little garden',character:'tito',make:'Plant a seed, draw what grows and come back to notice the change. A child can make this place feel like theirs.',explore:'Wander through a garden with a familiar plant, follow a tiny visitor and notice what changes each day.',learn:'Compare seeds, water and sunlight through playful choices around a garden they recognise.'},
  trains:{title:'The big train day',character:'flash',make:'Design carriages, choose colours and build a route to somewhere they know.',explore:'Follow a railway through places from their own stories, choosing the next stop together.',learn:'Count carriages, spot patterns and move people and things through a journey with meaning.'},
  space:{title:'The night sky club',character:'leo',make:'Draw a constellation and give it a name that belongs to their family.',explore:'Look closely at stars and planets, then follow one new question into another.',learn:'Sort bright and dim stars, trace shapes and discover what the night sky can tell us.'}
};
let chosenIdea='garden',chosenMode='make';
function updateIdea(){const data=ideas[chosenIdea];$('#idea-title').textContent=data.title;$('#idea-description').textContent=data[chosenMode];$('#idea-character').src=`assets/characters/${data.character}_happy.png`;$('#idea-character').alt=`${data.character[0].toUpperCase()+data.character.slice(1)}, a Greia character`;$('.idea-result').dataset.idea=chosenIdea;}
$$('[data-idea]').forEach(button=>button.addEventListener('click',()=>{chosenIdea=button.dataset.idea;$$('[data-idea]').forEach(other=>other.setAttribute('aria-pressed',String(other===button)));updateIdea();}));
$$('[data-mode]').forEach(button=>button.addEventListener('click',()=>{chosenMode=button.dataset.mode;$$('[data-mode]').forEach(other=>other.setAttribute('aria-pressed',String(other===button)));updateIdea();}));
const voices={
  lilli:"Hi! I'm Lilli! I love making up stories, drawing colorful things, and finding a little magic everywhere. Got a silly idea? Come with me!",
  flash:"Hey! I'm Flash! I love running, playing, and trying super-fast challenges. If you hear someone shout go, I've probably already started!",
  momo:"Booo! Just kidding! I'm Momo! I love music, silly noises, strange experiments, and surprise parties. If something goes boing, I want to try it!",
  tito:"Hello, explorer! I'm Tito! I love poking around forests, seas, trails, and little mysteries. Let's see what's around the corner!",
  leo:"Oh, hello! I'm Leo. I like stories, words, and all those questions that start with why. If there's something to discover, I'm ready!",
  dani:"Beep-bop! I'm Dani! I like numbers, patterns, puzzles, and things that click into exactly the right place. Friendship mode: activated!"
};
const audio=$('#voice-audio');
for(let i=0;i<39;i++){const bar=document.createElement('i');bar.style.setProperty('--bar-height',`${20+(i*37%80)}%`);bar.style.setProperty('--bar-delay',`${(i%7)*-.12}s`);$('#voice-bars').append(bar);}
function voiceStopped(){ $('.voice-main').classList.remove('is-playing');$('#voice-now').textContent='SELECT A CHARACTER TO HEAR A REAL INTRODUCTION'; }
audio.addEventListener('ended',voiceStopped);audio.addEventListener('pause',voiceStopped);
$$('[data-voice]').forEach(button=>button.addEventListener('click',async()=>{
  const name=button.dataset.voice;
  audio.pause();audio.src=`assets/voices/${name}.ogg`;
  $('#voice-character').src=`assets/characters/${name}_happy.png`;
  $('#voice-character').alt=name[0].toUpperCase()+name.slice(1);
  $('#voice-transcript').textContent=`“${voices[name]}”`;
  $$('[data-voice]').forEach(other=>other.setAttribute('aria-pressed',String(other===button)));
  try{await audio.play();$('.voice-main').classList.add('is-playing');$('#voice-now').textContent=`PLAYING ${name.toUpperCase()} · OWNER-ACCEPTED ENGLISH INTRODUCTION`;}catch{$('#voice-now').textContent='AUDIO COULD NOT PLAY IN THIS BROWSER';}
}));
new IntersectionObserver(([entry])=>{if(!entry.isIntersecting&&!audio.paused)audio.pause();},{threshold:.04}).observe($('#voices'));
