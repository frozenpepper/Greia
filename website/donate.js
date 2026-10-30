// PayPal donation button. The site otherwise loads no third-party script
// (see PRIVACY.md), so PayPal's SDK is fetched only after a visitor clicks
// "Donate with PayPal"; the hosted button then renders in that page's slot.
(() => {
  const SDK_URL = 'https://www.paypal.com/sdk/js?client-id=BAADJAjP3IrRBEOl-R5xcs7kFhCowp3s7BhfAuvmTyTz9-SgAMOEsRWK8pirHETQkig3WrNwS3N8MO95qk&components=hosted-buttons&disable-funding=venmo&currency=EUR';
  const HOSTED_BUTTON_ID = 'QU8KAK4X5S7VJ';
  let sdk = null;

  const loadSdk = () => sdk || (sdk = new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = SDK_URL;
    script.onload = () => (window.paypal ? resolve(window.paypal) : reject(new Error('PayPal SDK missing')));
    script.onerror = () => { sdk = null; reject(new Error('PayPal SDK failed to load')); };
    document.head.append(script);
  }));

  document.querySelectorAll('.donate').forEach((box) => {
    const start = box.querySelector('[data-paypal-start]');
    const slot = box.querySelector('.donate-slot');
    start.addEventListener('click', async () => {
      box.dataset.paypal = 'loading';
      try {
        const paypal = await loadSdk();
        await paypal.HostedButtons({ hostedButtonId: HOSTED_BUTTON_ID }).render(`#${slot.id}`);
        box.dataset.paypal = 'ready';
      } catch {
        box.dataset.paypal = 'failed';
      }
    });
  });
})();
