import { loadRecipes } from './data.js';
import { read, write, remove } from './storage.js';
import { escapeHtml, formatIngredient, formatAmount, weekStart, weekKey, vibrate } from './utils.js';

const app = document.querySelector('#app');
const modalRoot = document.querySelector('#modal-root');
let db = { categories: {}, recipes: [] };
let plannerOffset = 0;

const $ = (s, root = document) => root.querySelector(s);
const $$ = (s, root = document) => [...root.querySelectorAll(s)];
const recipeById = (id) => db.recipes.find(r => r.id === id);

function navigate(hash) {
  history.pushState({}, '', hash);
  renderRoute();
}

function recipeHref(id) {
  return `#recipe/${encodeURIComponent(id)}`;
}

function renderHome() {
  app.innerHTML = `
    <section class="hero">
      <h1>What are we cooking?</h1>
      <p>Find a recipe by category, name, or ingredient. Save favorites and build your week without leaving the kitchen.</p>
    </section>
    <section class="section">
      <div class="toolbar">
        <div class="grid-2">
          <select id="category" class="control"><option value="">All categories</option></select>
          <select id="subcategory" class="control" disabled><option value="">All sub-categories</option></select>
        </div>
        <div class="grid-2">
          <input id="nameSearch" class="control" type="search" placeholder="Search recipe name…" autocomplete="off">
          <input id="ingredientSearch" class="control" type="search" placeholder="Search ingredients… (comma separated)" autocomplete="off">
        </div>
      </div>
      <div id="results" class="results"></div>
    </section>
    <div class="action-row">
      <button class="btn green" id="plannerBtn">Open Meal Planner</button>
      <button class="btn" id="submitBtn">Submit a Recipe</button>
    </div>`;

  const category = $('#category');
  Object.keys(db.categories).sort((a,b)=>a.localeCompare(b)).forEach(c => category.add(new Option(c,c)));
  const subcategory = $('#subcategory');
  const render = () => {
    const cat = category.value;
    subcategory.innerHTML = '<option value="">All sub-categories</option>';
    subcategory.disabled = !cat;
    if (cat) Object.keys(db.categories[cat]).sort((a,b)=>a.localeCompare(b)).forEach(s => subcategory.add(new Option(s,s)));
    const nameTerm = $('#nameSearch').value.trim().toLowerCase();
    const ingredientTerms = $('#ingredientSearch').value.toLowerCase().split(',').map(s=>s.trim()).filter(Boolean);
    const filtered = db.recipes.filter(r => {
      if (cat && r.category !== cat) return false;
      if (subcategory.value && r.subcategory !== subcategory.value) return false;
      if (nameTerm && !r.displayName.toLowerCase().includes(nameTerm)) return false;
      if (ingredientTerms.length) {
        const ingredients = (r.ingredients ?? []).map(i => `${i.item ?? ''} ${i.note ?? ''}`.toLowerCase());
        if (!ingredientTerms.every(term => ingredients.some(i => i.includes(term)))) return false;
      }
      return true;
    }).sort((a,b)=>(Number(b.favorite)-Number(a.favorite)) || a.displayName.localeCompare(b.displayName));
    $('#results').innerHTML = filtered.length ? filtered.map(r => `
      <article class="card" data-recipe="${escapeHtml(r.id)}">
        <h3>${r.favorite ? '⭐ ' : ''}${escapeHtml(r.displayName)}</h3>
        <div class="meta">${escapeHtml(r.category)} · ${escapeHtml(r.subcategory)}</div>
      </article>`).join('') : '<div class="empty">No recipes matched your search.</div>';
  };
  [category, subcategory, $('#nameSearch'), $('#ingredientSearch')].forEach(el => el.addEventListener('input', render));
  $('#results').addEventListener('click', e => { const card = e.target.closest('[data-recipe]'); if (card) navigate(recipeHref(card.dataset.recipe)); });
  $('#plannerBtn').onclick = () => navigate('#planner');
  $('#submitBtn').onclick = openSubmitModal;
  render();
}

function findImage(recipe) {
  const slug = recipe.id.split('/').pop().replace('.html','');
  return `assets/recipes/${slug}.jpg`;
}

function renderRecipe(id) {
  const r = recipeById(id);
  if (!r) return renderHome();
  const image = findImage(r);
  app.innerHTML = `
    <div class="action-row"><button class="btn" id="back">← Back to Recipes</button></div>
    <section class="section recipe-title">
      <div class="recipe-sub">${escapeHtml(r.category)} · ${escapeHtml(r.subcategory)}</div>
      <h1>${r.favorite ? '⭐ ' : ''}${escapeHtml(r.displayName)}</h1>
      <div class="action-row" style="justify-content:center">
        <button class="btn ${r.favorite ? 'primary' : ''}" id="favorite">${r.favorite ? '★ Favorite' : '☆ Add to Favorites'}</button>
        <button class="btn green" id="print">Print / Save PDF</button>
        <a class="btn" href="${escapeHtml(r.url)}" target="_blank" rel="noopener">Open Original Recipe</a>
      </div>
    </section>
    <section class="recipe-layout" style="margin-top:20px">
      <section class="section">
        <img class="recipe-image" src="${image}" alt="${escapeHtml(r.displayName)}" onerror="this.style.display='none'">
        <div class="switch" style="margin-top:18px"><label><input type="checkbox" id="cookMode"> 🍳 Cook Mode</label></div>
      </section>
      <section class="section">
        <h2>Ingredients</h2>
        <ul class="ingredient-list">${(r.ingredients ?? []).map(i => `<li>${escapeHtml(formatIngredient(i))}</li>`).join('')}</ul>
        <h2 style="margin-top:24px">Directions</h2>
        <div class="empty">Directions remain in the original recipe page. Open the original recipe above to view them.</div>
      </section>
    </section>`;
  $('#back').onclick = () => navigate('#home');
  $('#favorite').onclick = () => {
    const existing = read('favorites', {}); existing[id] = !existing[id]; write('favorites', existing); r.favorite = existing[id]; renderRecipe(id); vibrate(15);
  };
  $('#print').onclick = () => window.print();
  setupCookMode($('#cookMode'));
}

function setupCookMode(toggle) {
  const saved = read('cookMode', false);
  toggle.checked = saved;
  if (saved) requestWakeLock();
  toggle.addEventListener('change', () => { write('cookMode', toggle.checked); if (toggle.checked) requestWakeLock(); else releaseWakeLock(); });
  document.addEventListener('visibilitychange', () => { if (toggle.checked && document.visibilityState === 'visible') requestWakeLock(); }, { once: true });
}
let wakeLock = null;
async function requestWakeLock(){ try { if ('wakeLock' in navigator) wakeLock = await navigator.wakeLock.request('screen'); } catch {} }
async function releaseWakeLock(){ try { await wakeLock?.release(); } catch {} wakeLock = null; }

function getPlan() { return read(`plan:${weekKey(weekStart(new Date(), plannerOffset))}`, Array.from({length:7},()=>[])); }
function savePlan(plan){ write(`plan:${weekKey(weekStart(new Date(), plannerOffset))}`, plan); }

function renderPlanner(){
  const start = weekStart(new Date(), plannerOffset); const plan = getPlan();
  app.innerHTML = `
    <section class="hero"><h1>Weekly Meal Planner</h1><p>Drag recipes onto your week, then generate a consolidated grocery list.</p></section>
    <section class="section">
      <div class="planner-head"><button class="btn" id="prev">← Previous</button><div class="week-label">${start.toLocaleDateString(undefined,{month:'long',day:'numeric',year:'numeric'})}</div><button class="btn" id="next">Next →</button></div>
      <div class="toolbar"><input id="plannerSearch" class="control" type="search" placeholder="Search recipes to add…"></div>
      <div id="pool" class="pool"></div>
      <div id="planner" class="planner"></div>
      <div class="action-row"><button class="btn danger" id="clearWeek">Clear Week</button><button class="btn green" id="grocery">Generate Grocery List</button><button class="btn" id="calendar">Add Week to Calendar</button></div>
      <div id="groceryList" class="grocery"></div>
    </section>`;
  $('#prev').onclick=()=>{plannerOffset--;renderPlanner()}; $('#next').onclick=()=>{plannerOffset++;renderPlanner()}; $('#clearWeek').onclick=()=>{remove(`plan:${weekKey(start)}`);renderPlanner()}; $('#grocery').onclick=renderGrocery; $('#calendar').onclick=exportCalendar;
  const renderPool = () => { const q=$('#plannerSearch').value.toLowerCase().trim(); const list=db.recipes.filter(r=>!q || r.displayName.toLowerCase().includes(q)).slice(0,40); $('#pool').innerHTML=list.map(r=>`<div class="chip" draggable="true" data-add="${escapeHtml(r.id)}"><span>${r.favorite?'⭐ ':''}${escapeHtml(r.displayName)}</span></div>`).join(''); $$('#pool .chip').forEach(el=>el.addEventListener('dragstart',e=>e.dataTransfer.setData('text/plain',el.dataset.add))); };
  const planner=$('#planner');
  for(let i=0;i<7;i++){const dayDate=new Date(start);dayDate.setDate(start.getDate()+i);const day=document.createElement('div');day.className='day'; if(dayDate.toDateString()===new Date().toDateString())day.classList.add('today'); day.innerHTML=`<h3><span class="day-name">${dayDate.toLocaleDateString(undefined,{weekday:'short'})}</span><span class="day-num">${dayDate.getDate()}</span></h3>`; day.addEventListener('dragover',e=>e.preventDefault()); day.addEventListener('drop',e=>{const id=e.dataTransfer.getData('text/plain');if(!id)return;plan[i].push(id);savePlan(plan);renderPlanner();vibrate(20)}); (plan[i]||[]).forEach((id,idx)=>{const r=recipeById(id);if(!r)return;const chip=document.createElement('div');chip.className='chip';chip.innerHTML=`<span title="Open recipe">${r.favorite?'⭐ ':''}${escapeHtml(r.displayName)}</span><button aria-label="Remove">×</button>`; chip.querySelector('span').onclick=()=>navigate(recipeHref(id)); chip.querySelector('button').onclick=()=>{plan[i].splice(idx,1);savePlan(plan);renderPlanner();vibrate(30)}; chip.draggable=true;chip.addEventListener('dragstart',e=>e.dataTransfer.setData('text/plain',id));day.appendChild(chip)}); planner.appendChild(day)}
  $('#plannerSearch').addEventListener('input',renderPool); renderPool();
}

function renderGrocery(){
  const plan=getPlan(); const totals=new Map();
  plan.flat().forEach(id=>{const r=recipeById(id); (r?.ingredients??[]).forEach(i=>{ if(!i.item) return; const key=`${i.item.toLowerCase()}|${i.unit||''}`; const current=totals.get(key); totals.set(key,current?{...current,amount:Number(current.amount||0)+Number(i.amount||0)}:{...i}); });});
  const grouped={}; totals.forEach(i=>{const c=getIngredientCategory(i.item);(grouped[c]??=[]).push(i)});
  $('#groceryList').innerHTML=`<section class="section"><h2>Grocery List</h2>${Object.keys(grouped).sort().map(c=>`<div class="grocery-category"><button type="button" data-collapse>${escapeHtml(c)} <span>▾</span></button><ul class="grocery-items">${grouped[c].sort((a,b)=>(a.item||'').localeCompare(b.item||'')).map(i=>`<li data-check>${escapeHtml(`${formatAmount(i.amount)} ${i.unit||''} ${i.item}${i.note?' — '+i.note:''}`.replace(/\s+/g,' ').trim())}</li>`).join('')}</ul></div>`).join('')}</section>`;
  $$('[data-collapse]').forEach(b=>b.onclick=()=>b.nextElementSibling.classList.toggle('hidden')); $$('[data-check]').forEach(li=>li.onclick=()=>{li.classList.toggle('checked');});
}
function getIngredientCategory(item=''){const n=item.toLowerCase();if(/soup|broth|stock|rotel|beans|canned|jar|package|can /.test(n))return'Canned & Pantry';if(/milk|cheese|cream|butter|yogurt|sour cream/.test(n))return'Dairy';if(/chicken|beef|bacon|pork|ham|steak|turkey|sausage/.test(n))return'Meat';if(/onion|lemon|apple|tomato|cucumber|pepper|cilantro|carrot|lettuce|zucchini|banana/.test(n))return'Produce';if(/flour|sugar|baking|oats|cocoa|powder|chips|rice/.test(n))return'Baking & Dry Goods';return'Other'}
function exportCalendar(){const start=weekStart(new Date(),plannerOffset),plan=getPlan();let ics='BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//Tritle Kitchen//EN\r\n';plan.forEach((day,i)=>{if(!day.length)return;const d=new Date(start);d.setDate(start.getDate()+i);const ds=d.toISOString().slice(0,10).replaceAll('-','');day.forEach(id=>{const r=recipeById(id);if(!r)return;ics+=`BEGIN:VEVENT\r\nUID:${crypto.randomUUID()}\r\nDTSTAMP:${ds}T120000Z\r\nDTSTART;VALUE=DATE:${ds}\r\nSUMMARY:${r.displayName.replaceAll(',','\\,')}\r\nEND:VEVENT\r\n`})});ics+='END:VCALENDAR\r\n';const url=URL.createObjectURL(new Blob([ics],{type:'text/calendar'}));const a=document.createElement('a');a.href=url;a.download=`tritle-kitchen-week-${weekKey(start)}.ics`;a.click();URL.revokeObjectURL(url)}
function openSubmitModal(){modalRoot.innerHTML=`<div class="modal-backdrop" id="submitBackdrop"><div class="modal"><div class="modal-head"><h2>Submit a Recipe</h2><button class="btn" id="close">×</button></div><p class="meta">Prepare your recipe text and attach any photos using your usual submission method.</p><textarea id="recipeText" placeholder="Recipe name\n\nIngredients\n\nDirections"></textarea><div class="action-row"><button class="btn primary" id="copy">Copy Recipe</button><a class="btn" href="mailto:?subject=Tritle%20Kitchen%20Recipe%20Submission" id="email">Email</a></div></div></div>`; $('#close').onclick=()=>modalRoot.innerHTML=''; $('#submitBackdrop').onclick=e=>{if(e.target.id==='submitBackdrop')modalRoot.innerHTML='';}; $('#copy').onclick=async()=>{await navigator.clipboard?.writeText($('#recipeText').value);vibrate(10);}};

function renderRoute(){const raw=decodeURIComponent(location.hash.slice(1)); if(raw.startsWith('recipe/'))renderRecipe(raw.slice(7)); else if(raw==='planner')renderPlanner(); else renderHome(); app.scrollIntoView({behavior:'smooth',block:'start'});}

async function boot(){
  try{
    db=await loadRecipes();
    const favs=read('favorites',{}); db.recipes.forEach(r=>{if(Object.prototype.hasOwnProperty.call(favs,r.id))r.favorite=favs[r.id]});
    addEventListener('hashchange',renderRoute); renderRoute();
    if('serviceWorker' in navigator) navigator.serviceWorker.register('./sw.js').catch(()=>{});
  }catch(error){app.innerHTML=`<section class="section empty"><h2>Kitchen data could not be loaded.</h2><p>${escapeHtml(error.message)}</p></section>`}
}
boot();
