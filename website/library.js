const activities = window.GREIA_LIBRARY || [];
const grid = document.querySelector('#activity-grid');
const filters = [...document.querySelectorAll('[data-category]')];
const search = document.querySelector('#activity-search');
const detail = document.querySelector('#activity-dialog');
let category = 'all';
const categoryNames = {create:'MAKE',play:'PLAY',learn:'LEARN',explore:'EXPLORE'};

function packageControl(activity, className) {
  if (activity.packageUrl && activity.packageUrl.endsWith('.greiaactivity')) {
    const link = document.createElement('a');
    link.href = activity.packageUrl;
    link.className = className + ' package-link';
    link.textContent = 'Download .greiaactivity ↗';
    link.setAttribute('download', `${activity.id}.greiaactivity`);
    return link;
  }
  const button = document.createElement('button');
  button.type = 'button';
  button.disabled = true;
  button.className = className;
  button.textContent = 'Package coming';
  button.setAttribute('aria-label', `${activity.title} package is not published yet`);
  return button;
}
function openActivity(activity) {
  const image = document.querySelector('#detail-image');
  image.src = activity.image;
  image.alt = `${activity.title} English development screenshot`;
  document.querySelector('#detail-category').textContent = `${categoryNames[activity.category]} / DEVELOPMENT PREVIEW`;
  document.querySelector('#detail-title').textContent = activity.title;
  document.querySelector('#detail-description').textContent = activity.description;
  const featureList = document.querySelector('#detail-features');
  featureList.replaceChildren(...activity.features.map(feature => {const li=document.createElement('li');li.textContent=feature;return li;}));
  const sourceLink = document.createElement('a');
  sourceLink.href = `https://github.com/frozenpepper/Greia/tree/main/${activity.sourcePath}`;
  sourceLink.target = '_blank';
  sourceLink.rel = 'noopener';
  sourceLink.textContent = 'View Activity source ↗';
  document.querySelector('#detail-actions').replaceChildren(packageControl(activity,'download-button'),sourceLink);
  detail.showModal();
}
function activityCard(activity) {
  const article = document.createElement('article'); article.className='activity-card';
  const image = document.createElement('img'); image.src=activity.image; image.alt=`${activity.title} English development screenshot`; image.loading='lazy';
  const body = document.createElement('div'); body.className='activity-card-body';
  const kind = document.createElement('span'); kind.className='card-category'; kind.textContent=`${categoryNames[activity.category]} / DEVELOPMENT PREVIEW`;
  const title = document.createElement('h3'); title.textContent=activity.title;
  const description = document.createElement('p'); description.textContent=activity.description;
  const actions = document.createElement('div'); actions.className='card-actions';
  const preview = document.createElement('button'); preview.className='preview-button'; preview.type='button'; preview.textContent='Explore details ↗'; preview.addEventListener('click',()=>openActivity(activity));
  actions.append(preview,packageControl(activity,'download-button'));
  body.append(kind,title,description,actions); article.append(image,body);
  return article;
}
function render() {
  const query = search.value.trim().toLocaleLowerCase();
  const selected = activities.filter(item => (category==='all'||item.category===category) && (`${item.title} ${item.description} ${item.features.join(' ')}`).toLocaleLowerCase().includes(query));
  if (selected.length) grid.replaceChildren(...selected.map(activityCard));
  else {const message=document.createElement('p');message.className='empty-library';message.textContent='No Activities match yet. Try another word or category.';grid.replaceChildren(message);}
  document.querySelector('#result-count').textContent=`${selected.length} ${selected.length===1?'ACTIVITY':'ACTIVITIES'} SHOWN`;
}
filters.forEach(button=>button.addEventListener('click',()=>{
  category=button.dataset.category;
  filters.forEach(other=>other.setAttribute('aria-pressed',String(other===button)));
  render();
}));
search.addEventListener('input',render);
document.querySelector('#close-activity').addEventListener('click',()=>detail.close());
detail.addEventListener('click',event=>{if(event.target===detail)detail.close();});
render();
