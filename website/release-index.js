// Reads the public Greia index (updates/greia-updates.json) and fills any
// element marked data-installer="field" with the newest installer image for
// its target (data-target on an ancestor, default legacy-x86-i386).
// tools/build_installer_index.py writes the greia_os.installers list.
(() => {
  const INDEX_URL = 'updates/greia-updates.json';
  const DEFAULT_TARGET = 'legacy-x86-i386';
  const STATUS_LABELS = { 'technical-preview': 'Technical preview', release: 'Release' };
  const BOOT_LABELS = { bios: 'Legacy BIOS', uefi: 'UEFI', 'uefi-experimental': 'UEFI (experimental)' };

  const formatSize = (bytes) => {
    if (!Number.isFinite(bytes)) return '';
    return bytes >= 1e9 ? `${(bytes / 1e9).toFixed(2)} GB` : `${Math.round(bytes / 1e6)} MB`;
  };
  const formatDate = (iso) => {
    const date = new Date(`${iso}T12:00:00Z`);
    return Number.isNaN(date.getTime()) ? iso || '' : date.toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' });
  };
  const httpsUrl = (value) => (typeof value === 'string' && /^https:\/\/\S+$/i.test(value) ? value : null);

  // Newest entry per target; the index lists each target's newest first.
  function latestByTarget(index) {
    const list = index && index.schema === 'greia-updates/1' && index.greia_os && Array.isArray(index.greia_os.installers)
      ? index.greia_os.installers : [];
    const latest = {};
    for (const entry of list) {
      if (!entry || typeof entry.id !== 'string' || latest[entry.id]) continue;
      if (!entry.image || !httpsUrl(entry.image.url)) continue;
      latest[entry.id] = entry;
    }
    return latest;
  }

  function fields(entry) {
    const image = entry.image;
    return {
      title: entry.title || entry.id,
      version: entry.version || '',
      build: entry.build || '',
      status: STATUS_LABELS[entry.status] || entry.status || '',
      date: formatDate(entry.published_at),
      size: formatSize(image.size),
      media: entry.min_media_gb ? `${entry.min_media_gb} GB` : '',
      boot: (entry.boot || []).map((mode) => BOOT_LABELS[mode] || mode).join(' · '),
      reference: (entry.reference_hardware || [])[0] || '',
      file: image.file_name || image.url.split('/').pop(),
      sha256: image.sha256 || '',
      note: (entry.notes && entry.notes.en) || '',
    };
  }

  function fill(entry) {
    const values = fields(entry);
    const scope = (node) => (node.closest('[data-target]') || {}).dataset?.target || DEFAULT_TARGET;
    document.querySelectorAll('[data-installer]').forEach((node) => {
      if (scope(node) !== entry.id) return;
      const value = values[node.dataset.installer];
      if (value) node.textContent = value;
      if (node.dataset.installer === 'status') node.dataset.status = entry.status || '';
    });
    document.querySelectorAll('[data-installer-link]').forEach((link) => {
      if (scope(link) !== entry.id) return;
      link.href = entry.image.url;
      link.setAttribute('download', values.file);
      link.removeAttribute('aria-disabled');
      link.setAttribute('aria-label', `Download Greia ${values.version} for ${values.title}, ${values.size}`);
    });
  }

  const ready = fetch(INDEX_URL, { cache: 'no-cache' })
    .then((response) => { if (!response.ok) throw new Error(`HTTP ${response.status}`); return response.json(); })
    .then((index) => {
      const latest = latestByTarget(index);
      Object.values(latest).forEach(fill);
      document.dispatchEvent(new CustomEvent('greia:installers', { detail: latest }));
      return latest;
    })
    .catch((error) => {
      document.dispatchEvent(new CustomEvent('greia:installers-error', { detail: error }));
      return {};
    });

  window.GreiaReleases = { ready, formatSize };
})();
