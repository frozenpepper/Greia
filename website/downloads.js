// Downloads page behaviour: installer card state, checksum copy, OS tabs
// (pre-selected from the visitor's system) and the boot-key finder.
(() => {
  const card = document.getElementById('latest');

  document.addEventListener('greia:installers', (event) => {
    card.dataset.state = event.detail[card.dataset.target] ? 'ready' : 'error';
  });
  document.addEventListener('greia:installers-error', () => { card.dataset.state = 'error'; });

  document.querySelectorAll('[data-copy-from]').forEach((button) => {
    button.addEventListener('click', async () => {
      const source = button.parentElement.querySelector(`[data-installer="${button.dataset.copyFrom}"]`);
      try {
        await navigator.clipboard.writeText(source.textContent.trim());
        button.textContent = 'Copied';
      } catch {
        getSelection().selectAllChildren(source);
        button.textContent = 'Selected';
      }
      setTimeout(() => { button.textContent = 'Copy'; }, 1800);
    });
  });

  const tabs = [...document.querySelectorAll('.dl-tabs [role=tab]')];
  const selectTab = (tab, focus = false) => {
    tabs.forEach((other) => {
      const selected = other === tab;
      other.setAttribute('aria-selected', String(selected));
      other.tabIndex = selected ? 0 : -1;
      document.getElementById(other.getAttribute('aria-controls')).hidden = !selected;
    });
    if (focus) tab.focus();
  };
  tabs.forEach((tab, i) => {
    tab.addEventListener('click', () => selectTab(tab));
    tab.addEventListener('keydown', (event) => {
      const step = { ArrowRight: 1, ArrowLeft: -1 }[event.key];
      if (step) selectTab(tabs[(i + step + tabs.length) % tabs.length], true);
    });
  });
  const platform = `${navigator.userAgentData?.platform || ''} ${navigator.platform || ''} ${navigator.userAgent}`;
  const detected = /Mac/i.test(platform) && !/iPhone|iPad/i.test(platform) ? 'mac'
    : /Linux|X11|CrOS/i.test(platform) && !/Android/i.test(platform) ? 'linux'
      : /Win/i.test(platform) ? 'windows' : null;
  if (detected) {
    const tab = tabs.find((item) => item.dataset.os === detected);
    selectTab(tab);
    const note = document.getElementById('os-detected');
    note.textContent = `← looks like you're on ${tab.textContent}`;
    note.hidden = false;
  } else {
    selectTab(tabs[0]);
  }

  const key = document.getElementById('boot-key');
  const hint = document.getElementById('boot-hint');
  document.querySelectorAll('.dl-brands button').forEach((button, _, all) => {
    button.addEventListener('click', () => {
      all.forEach((other) => other.setAttribute('aria-pressed', String(other === button)));
      key.textContent = button.dataset.key;
      hint.textContent = button.dataset.hint;
    });
  });
})();
