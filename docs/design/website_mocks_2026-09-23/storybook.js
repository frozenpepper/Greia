document.documentElement.classList.add('has-js');
const $ = selector => document.querySelector(selector);
const $$ = selector => [...document.querySelectorAll(selector)];
const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;

// The original 52 PNGs remain the animation authority; the wide SVG only extends their landscape.
const frames = Array.from({length: 52}, (_, index) => {
  const image = new Image();
  image.src = `../../../assets/boot/frames/frame_${String(index).padStart(4, '0')}.png`;
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
$$('.section-heading,.mission-head,.explorer,.hardware-layout,.architecture-interactive,.parent-grid,.creation-lab,.voice-layout,.mission-points,.architecture-more,.parent-feature-row,.faq-grid').forEach(node => revealObserver.observe(node));

const gallery = [
  {category:'shell', label:'THE CHILD SHELL', title:'Their own starting place.', description:'After choosing a profile, a child sees Greia’s Collections, large Activity cards and a clear route into making, playing, learning or exploring. The desktop stays out of sight.', facts:['PROFILE FIRST','COLLECTIONS, NOT FOLDERS','NO LINUX DESKTOP'], source:'Development Simulator capture · 22 August 2026', src:'../../../docs/reviews/visual/2026-08-22_launcher-shell-productization/02-after-main-shell-1024x600.png', alt:'Greia Shell showing the Create collection'},
  {category:'shell', label:'PROFILES', title:'A computer shared, a world of their own.', description:'The boot path explicitly asks which child is here. Greia keeps that child’s creations, progress, language and Activity saves under their profile rather than silently resuming someone else.', facts:['EXPLICIT PROFILE PICKER','PERSONAL SAVES','PORTABLE STATE'], source:'Development Simulator capture · 30 August 2026', src:'../../../docs/reviews/visual/2026-08-30_ENCYCLOPEDIA_TRAVERSAL/screenshots/00-shell-profile-picker.png', alt:'Greia child profile selection screen'},
  {category:'create', label:'PAINTING', title:'A canvas big enough for an idea.', description:'Painting is a required first-party Activity. The child gets a large responsive canvas, a small tool set, bounded undo and profile-scoped autosave without a file dialog.', facts:['LARGE CANVAS','AUTOSAVE','PROFILE OWNED'], source:'Development Simulator capture · 22 August 2026', src:'../../../docs/reviews/visual/2026-08-22_painting-visual-productization/06-best-product-proof.png', alt:'Greia Painting with a childlike garden drawing'},
  {category:'create', label:'WRITING', title:'A little page with room for anything.', description:'Writing is the other required creative starting point: large readable text, ordinary Unicode and emoji, an approachable document gallery and automatic saving. The captured state here shows a new empty page.', facts:['LARGE TYPE','EMOJI SUPPORT','NO FILE MANAGER'], source:'Development Activity capture · 22 August 2026', src:'../../../docs/reviews/visual/2026-08-22_first-party-activity-visual-audit/captures/org.greia.writing.png', alt:'Greia Writing showing a blank child-friendly document'},
  {category:'play', label:'TRAIN OF NUMBERS', title:'Learning carried by play.', description:'The number train uses familiar objects and a visually legible scene rather than a worksheet on a desktop. It is one example of an Activity living inside the same Greia Home and profile system.', facts:['NUMBERS','ARROWS + SPACE','GREIA HOME'], source:'Development Simulator capture · 22 August 2026', src:'../../../docs/reviews/visual/2026-08-22_first-party-batch-1/treno_numeri/04-best-product-proof.png', alt:'Greia number train Activity'},
  {category:'play', label:'MAGIC MAZE', title:'A small adventure with learned controls.', description:'A maze can use the same directional input a child learns elsewhere. The Activity brings the challenge and art; Greia keeps the protected route Home.', facts:['DIRECTIONAL INPUT','ACTIVITY LIFECYCLE','SHARED HOME'], source:'Development Simulator capture · 22 August 2026', src:'../../../docs/reviews/visual/2026-08-22_first-party-batch-1/labirinto_magico/04-best-product-proof.png', alt:'Greia Magic Maze Activity'},
  {category:'play', label:'MAGIC AQUARIUM', title:'Curiosity can start with a fish.', description:'In Magic Aquarium, the child interacts with fish, food, bubbles and light. Different Activities can feel distinct while preserving a consistent way into and out of them.', facts:['TOUCH + POINTER','DISTINCT WORLDS','COMMON PLATFORM'], source:'Development Simulator capture · 22 August 2026', src:'../../../docs/reviews/visual/2026-08-22_first-party-batch-1/acquario_magico/04-best-product-proof.png', alt:'Greia Magic Aquarium Activity'},
  {category:'play', label:'MAGICAL BAKERY', title:'Not every challenge looks like a quiz.', description:'The bakery combines playful orders, patterns and free creation. Greia’s Activity model has room for different rhythms of learning and making.', facts:['ORDERS','PATTERNS','FREE PLAY'], source:'Development Activity capture · 22 August 2026', src:'../../../docs/reviews/visual/2026-08-22_first-party-activity-visual-audit/captures/org.greia.pasticceria-magica.png', alt:'Greia Magical Bakery Activity'},
  {category:'explore', label:'ENCYCLOPEDIA', title:'An invitation to keep asking why.', description:'The Encyclopedia is an evolving first-party exploration world. Its sections include animals, space, Earth, the body, machines and history; the development captures are not final content acceptance.', facts:['SIX TOPIC FAMILIES','VISUAL EXPLORATION','PRE-PUBLIC'], source:'Development Simulator traversal · 30 August 2026', src:'../../../docs/reviews/visual/2026-08-30_ENCYCLOPEDIA_TRAVERSAL/screenshots/00-encyclopedia-home.png', alt:'Greia Encyclopedia home'},
  {category:'explore', label:'SPACE', title:'The whole solar system can fit in a question.', description:'The Space section uses a navigable visual scene instead of a wall of text. Its screenshot also shows Greia’s protected Home control in the Activity corner.', facts:['SPACE','DISCOVERY','PROTECTED HOME'], source:'Development Simulator traversal · 30 August 2026', src:'../../../docs/reviews/visual/2026-08-30_ENCYCLOPEDIA_TRAVERSAL/screenshots/sections/02-space.png', alt:'Greia Encyclopedia Space section'},
  {category:'explore', label:'EARTH', title:'Learning can be something you touch.', description:'A rainbow entry presents a visual model children can explore. The broader Encyclopedia art and runtime still have their own review and acceptance gates.', facts:['EARTH','INTERACTIVE ENTRY','WORK IN PROGRESS'], source:'Development Simulator traversal · 30 August 2026', src:'../../../docs/reviews/visual/2026-08-30_ENCYCLOPEDIA_TRAVERSAL/screenshots/entries/earth.rainbow-after.png', alt:'Greia Encyclopedia interactive rainbow entry'},
  {category:'play', label:'LITTLE GREENHOUSE', title:'Return to see what changed.', description:'A garden Activity makes space for small routines and care: plant, water, wait and notice. It suggests how a child’s own interests can shape an experience.', facts:['SEEDS','CARE','REVISIT'], source:'Development Activity capture · 22 August 2026', src:'../../../docs/reviews/visual/2026-08-22_first-party-activity-visual-audit/captures/org.greia.piccola-serra.png', alt:'Greia Little Greenhouse Activity'}
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
  $('#dialog-image').src = 'assets/parent-app-full-2026-09-02.png';
  $('#dialog-image').alt = 'Full Greia Parents development capture showing device status and settings';
  $('#dialog-caption').textContent = 'GREIA PARENTS · This Greia development capture · 2 September 2026';
  dialog.showModal();
});
$('#close-shot').addEventListener('click', () => dialog.close());
dialog.addEventListener('click', event => {if (event.target===dialog) dialog.close();});

const hardware = {
  acer:{label:'THE EXTREME REFERENCE',title:'Small, old, still useful.',description:'Greia keeps the earliest Aspire One in view when making decisions about memory, storage, responsiveness and legibility. If a feature only works on a fast development laptop, it is not enough.',specs:[['~768 MiB','estimated RAM reference'],['~7 GB','estimated storage reference'],['1024×600','target screen class']],note:'These Acer numbers are planning estimates pending inventory and physical acceptance, not a compatibility guarantee.'},
  pi400:{label:'A FIRST-CLASS ARM TARGET',title:'A keyboard that is also a computer.',description:'Raspberry Pi 400 is explicitly part of Greia’s reference family. The Activity and profile contracts should travel across hardware architectures without making a second, lesser Greia for ARM.',specs:[['ARM','co-equal architecture'],['Same','Activity contract'],['Portable','child profile data']],note:'Final image, graphics/session and input evidence for Pi 400 still belongs to the release acceptance programme.'},
  pi500:{label:'A FIRST-CLASS ARM TARGET',title:'More room, the same promises.',description:'Raspberry Pi 500 is another named target. More capable hardware can feel smoother and richer, while Greia’s essential child navigation, parent authority and offline behavior stay the same.',specs:[['ARM','co-equal architecture'],['Same','Greia Shell'],['Same','parent controls']],note:'This is a target commitment. Device-specific release readiness must be verified, not inferred from the mock.'}
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
  profiles:{kicker:'ONE CHILD AT A TIME',title:'A real place for each child.',description:'A child picks their own profile at boot. Their writing, drawings, Activity data, progress and language preferences belong to that profile, rather than spilling into a sibling’s world.',points:['Profile-scoped creations and Activity saves.','Age and challenge intent stay distinct.','Parents decide which Activities this child sees.'],note:'The displayed Parent screenshot is from a development acceptance run. Its controls are capability-gated and release pairing/transport work remains open.'},
  discovery:{kicker:'VISIBLE TO THIS CHILD',title:'Installation is only one decision.',description:'Greia Parents can set age and difficulty intent and make an explicit always-show or always-hide choice for an Activity. Greia applies that projection before it builds the child’s catalogue.',points:['An explicit parent choice wins over automatic recommendations.','Difficulty does not substitute for age suitability.','Hiding an Activity does not delete its package or the child’s saved work.'],note:'This is current source/API/client direction; final release and family usability acceptance are still separate.'},
  device:{kicker:'THE DEVICE, WITHOUT LINUX ADMIN',title:'Useful settings in one grown-up place.',description:'The real screenshot at left shows Greia Parents “This Greia”: status, network, language, bounded input/display/audio controls, parent devices and access. Unsupported controls stay out of view.',points:['Hardware settings are typed and bounded, not arbitrary shell commands.','Microphone and speaker controls appear when supported.','Local management is designed without a cloud account.'],note:'The screenshot is a development run, not proof of every control on every device.'},
  install:{kicker:'PARENT-AUTHORIZED ACTIVITY INSTALL',title:'Know what is going onto their computer.',description:'A compatible independent Activity can be packaged as a .greiaactivity file. Greia validates the archive, package rules, compatibility and trust information before a parent approves a bounded installation.',points:['The file extension is a routing hint, not a trust proof.','Installation does not silently grant visibility to every child.','The broader release update/rollback/provenance lifecycle remains open.'],note:'The bounded new-install service and Parent upload seam exist; this is not a claim of complete ordinary-family release readiness.'}
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
function updateIdea(){const data=ideas[chosenIdea];$('#idea-title').textContent=data.title;$('#idea-description').textContent=data[chosenMode];$('#idea-character').src=`../../../assets/visual/runtime/v1/characters/${data.character}_happy.png`;$('#idea-character').alt=`${data.character[0].toUpperCase()+data.character.slice(1)}, a Greia character`;$('.idea-result').dataset.idea=chosenIdea;}
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
  audio.pause();audio.src=`../../../assets/audio/characters/shared/v0.2/_intros/en/${name}.ogg`;
  $('#voice-character').src=`../../../assets/visual/runtime/v1/characters/${name}_happy.png`;
  $('#voice-character').alt=name[0].toUpperCase()+name.slice(1);
  $('#voice-transcript').textContent=`“${voices[name]}”`;
  $$('[data-voice]').forEach(other=>other.setAttribute('aria-pressed',String(other===button)));
  try{await audio.play();$('.voice-main').classList.add('is-playing');$('#voice-now').textContent=`PLAYING ${name.toUpperCase()} · OWNER-ACCEPTED ENGLISH INTRODUCTION`;}catch{$('#voice-now').textContent='AUDIO COULD NOT PLAY IN THIS BROWSER';}
}));
new IntersectionObserver(([entry])=>{if(!entry.isIntersecting&&!audio.paused)audio.pause();},{threshold:.04}).observe($('#voices'));
