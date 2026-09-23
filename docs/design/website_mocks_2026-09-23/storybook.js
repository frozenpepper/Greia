const chapters = [...document.querySelectorAll('.chapter')];
const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
const intro = document.getElementById('intro');
const introFrame = document.getElementById('intro-frame');
const introProgress = document.getElementById('intro-progress');
const introCount = document.getElementById('intro-count');
let introRun = 0;
let introRaf = 0;

function endIntro(run) {
  if (run !== introRun) return;
  cancelAnimationFrame(introRaf);
  intro.classList.add('is-leaving');
  document.body.classList.remove('intro-open');
  window.setTimeout(() => {
    if (run === introRun) intro.hidden = true;
  }, 710);
}

async function playIntro() {
  const run = ++introRun;
  cancelAnimationFrame(introRaf);
  intro.hidden = false;
  intro.classList.remove('is-leaving');
  document.body.classList.add('intro-open');
  introProgress.style.width = '0%';
  introCount.textContent = '00 / 52';
  introFrame.src = '../../../assets/boot/frames/frame_0000.png';
  if (reducedMotion) {
    introFrame.src = '../../../assets/boot/frames/frame_0051.png';
    endIntro(run);
    return;
  }
  // Decode the real boot frames once so the opening can run without network stutters.
  const frames = Array.from({length: 52}, (_, index) => {
    const image = new Image();
    image.src = `../../../assets/boot/frames/frame_${String(index).padStart(4, '0')}.png`;
    return image;
  });
  await Promise.all(frames.map(image => image.decode().catch(() => {})));
  if (run !== introRun) return;
  const duration = 4800;
  let start;
  let previous = -1;
  function tick(time) {
    if (run !== introRun) return;
    start ??= time;
    const progress = Math.min(1, (time - start) / duration);
    const index = Math.min(51, Math.floor(progress * 52));
    if (index !== previous) {
      introFrame.src = frames[index].src;
      introCount.textContent = `${String(index + 1).padStart(2, '0')} / 52`;
      previous = index;
    }
    introProgress.style.width = `${Math.round(progress * 100)}%`;
    if (progress < 1) introRaf = requestAnimationFrame(tick);
    else window.setTimeout(() => endIntro(run), 460);
  }
  introRaf = requestAnimationFrame(tick);
}

document.getElementById('skip-intro').addEventListener('click', () => endIntro(++introRun));
document.getElementById('replay-intro').addEventListener('click', playIntro);
playIntro();

function go(index) {
  chapters[index]?.scrollIntoView({behavior: reducedMotion ? 'instant' : 'smooth'});
}
document.querySelectorAll('[data-go]').forEach(button => button.addEventListener('click', () => go(Number(button.dataset.go))));
const chapterObserver = new IntersectionObserver(entries => {
  entries.forEach(entry => {
    if (!entry.isIntersecting) return;
    entry.target.classList.add('is-visible');
    const index = chapters.indexOf(entry.target);
    document.querySelectorAll('.chapter-nav button').forEach((button, buttonIndex) => button.setAttribute('aria-current', String(index === buttonIndex)));
  });
}, {threshold: .48});
chapters.forEach(chapter => chapterObserver.observe(chapter));

document.addEventListener('keydown', event => {
  if (event.key === 'Escape') {
    document.getElementById('top-nav').classList.remove('is-open');
    document.getElementById('menu-toggle').setAttribute('aria-expanded', 'false');
    if (!intro.hidden) endIntro(++introRun);
    return;
  }
  if (!intro.hidden || !['ArrowDown', 'ArrowUp'].includes(event.key)) return;
  if (['BUTTON', 'A', 'INPUT'].includes(document.activeElement?.tagName)) return;
  event.preventDefault();
  const current = Number(document.querySelector('.chapter-nav [aria-current="true"]')?.dataset.go ?? 0);
  go(Math.max(0, Math.min(chapters.length - 1, current + (event.key === 'ArrowDown' ? 1 : -1))));
});
const menu = document.getElementById('top-nav');
const menuToggle = document.getElementById('menu-toggle');
menuToggle.addEventListener('click', () => {
  const isOpen = menu.classList.toggle('is-open');
  menuToggle.setAttribute('aria-expanded', String(isOpen));
});
menu.querySelectorAll('a').forEach(link => link.addEventListener('click', () => {
  menu.classList.remove('is-open');
  menuToggle.setAttribute('aria-expanded', 'false');
}));

const devices = {
  acer: ['The extreme reference floor', 'The original little Acer keeps Greia honest about memory, storage and screen space.'],
  pi400: ['ARM belongs from the start', 'Raspberry Pi 400 is a first-class design target for the same child and parent experience.'],
  pi500: ['Room to grow, same promises', 'Raspberry Pi 500 is another first-class target, without splitting Greia into a different product.']
};
document.querySelectorAll('[data-device]').forEach(button => button.addEventListener('click', () => {
  const key = button.dataset.device;
  document.getElementById('device').dataset.mode = key;
  document.getElementById('device-title').textContent = devices[key][0];
  document.getElementById('device-description').textContent = devices[key][1];
  document.querySelectorAll('[data-device]').forEach(item => item.setAttribute('aria-pressed', String(item === button)));
}));

const layers = {
  activity: ['THE CHILD SEES', 'A world of Activities.', 'One familiar way to choose, play, create and go Home. Greia’s own navigation stays available above every Activity.'],
  core: ['THE PLATFORM OWNS', 'The parts that must be dependable.', 'Greia keeps profiles, saves, permissions, input and progression consistent. Activities concentrate on their own experience.'],
  hardware: ['UNDER IT ALL', 'One design, different computers.', 'Runtime and device adapters bridge old x86 and ARM without asking families to learn separate versions of Greia.']
};
document.querySelectorAll('[data-layer]').forEach(button => button.addEventListener('click', () => {
  const [kicker, title, description] = layers[button.dataset.layer];
  document.getElementById('architecture-kicker').textContent = kicker;
  document.getElementById('architecture-title').textContent = title;
  document.getElementById('architecture-description').textContent = description;
  document.querySelectorAll('[data-layer]').forEach(item => {
    item.classList.toggle('is-active', item === button);
    item.setAttribute('aria-pressed', String(item === button));
  });
}));

const parentTopics = {
  children: ['One space for each child', 'Profiles keep creations and progress personal. Parents can tune discovery and visibility for each child.'],
  activities: ['You choose what appears', 'Inspect Activities, adjust who sees them and, where the device permits, install an approved package.'],
  device: ['A clear view of this Greia', 'The Parent app brings device status, language and bounded settings into one grown-up place.']
};
document.querySelectorAll('[data-parent]').forEach(button => button.addEventListener('click', () => {
  const [title, description] = parentTopics[button.dataset.parent];
  document.getElementById('parent-title').textContent = title;
  document.getElementById('parent-description').textContent = description;
  document.querySelectorAll('[data-parent]').forEach(item => item.setAttribute('aria-pressed', String(item === button)));
}));

const interests = {
  garden: ['Our little garden', 'Plant, notice, return tomorrow. A familiar place becomes a curious little world.', 'tito_happy.png'],
  trains: ['The big train day', 'Count carriages, choose a route and make a journey feel like their own.', 'flash_happy.png'],
  stars: ['The night sky club', 'Find shapes in the dark and ask what might be shining back.', 'leo_happy.png']
};
document.querySelectorAll('[data-interest]').forEach(button => button.addEventListener('click', () => {
  const key = button.dataset.interest;
  const [title, description, image] = interests[key];
  document.getElementById('idea-title').textContent = title;
  document.getElementById('idea-description').textContent = description;
  document.getElementById('idea-image').src = `../../../assets/visual/runtime/v1/characters/${image}`;
  document.getElementById('idea-card').dataset.interest = key;
  document.querySelectorAll('[data-interest]').forEach(item => item.setAttribute('aria-pressed', String(item === button)));
}));

const introductions = {
  lilli: "Hi! I'm Lilli! I love making up stories, drawing colorful things, and finding a little magic everywhere. Got a silly idea? Come with me!",
  flash: "Hey! I'm Flash! I love running, playing, and trying super-fast challenges. If you hear someone shout go, I've probably already started!",
  momo: "Booo! Just kidding! I'm Momo! I love music, silly noises, strange experiments, and surprise parties. If something goes boing, I want to try it!"
};
const audio = document.getElementById('character-audio');
const waves = document.getElementById('voice-waves');
for (let index = 0; index < 31; index++) {
  const bar = document.createElement('i');
  bar.style.setProperty('--h', `${18 + (index * 37 % 110)}px`);
  bar.style.setProperty('--d', `${(index % 7) * -.11}s`);
  waves.append(bar);
}
function stopVoice() {
  waves.classList.remove('is-playing');
  document.getElementById('voice-help').textContent = 'Select a character to hear the accepted English voice sample.';
}
audio.addEventListener('ended', stopVoice);
audio.addEventListener('pause', stopVoice);
new IntersectionObserver(([entry]) => {
  if (!entry.isIntersecting && !audio.paused) audio.pause();
}, {threshold: .12}).observe(document.getElementById('voices'));
document.querySelectorAll('[data-voice]').forEach(button => button.addEventListener('click', async () => {
  const name = button.dataset.voice;
  audio.pause();
  audio.src = `../../../assets/audio/characters/shared/v0.2/_intros/en/${name}.ogg`;
  document.getElementById('voice-quote').textContent = `“${introductions[name]}”`;
  document.querySelectorAll('[data-voice]').forEach(item => item.setAttribute('aria-pressed', String(item === button)));
  try {
    await audio.play();
    waves.classList.add('is-playing');
    document.getElementById('voice-help').textContent = `Playing ${name[0].toUpperCase() + name.slice(1)}'s real introduction · select another to switch`;
  } catch {
    document.getElementById('voice-help').textContent = 'Audio could not play in this browser.';
  }
}));
