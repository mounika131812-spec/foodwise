/**
 * Smart Food Waste Management Platform - Frontend Application
 * Pure vanilla JS - No frameworks
 * Design system v2: glassmorphism, smooth animations, interactive UI
 */

// ===== API Helper =====
const API_BASE = '/api';

async function apiFetch(endpoint, options = {}) {
  const token = localStorage.getItem('token');
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    ...options.headers,
  };

  const res = await fetch(`${API_BASE}${endpoint}`, { ...options, headers });
  const data = await res.json().catch(() => ({}));

  if (!res.ok) {
    if (res.status === 401) {
      logout();
      throw new Error(data.error || 'Session expired');
    }
    throw new Error(data.error || 'Request failed');
  }
  return data;
}

// ===== Toast Notification =====
const TOAST_ICO = { success: '✅', error: '⚠️', info: 'ℹ️' };
function showToast(message, type = 'success') {
  const toast = document.getElementById('toast');
  toast.querySelector('.toast-ico').textContent = TOAST_ICO[type] || '✅';
  toast.querySelector('.toast-msg').textContent = message;
  toast.classList.remove('hiding');
  toast.className = `toast ${type}`;
  toast._timer = setTimeout(() => {
    toast.classList.add('hiding');
    toast._timer = null;
  }, 3000);
  toast.addEventListener('animationend', () => {
    if (toast.classList.contains('hiding') && !toast._timer) toast.className = 'toast hidden';
  }, { once: true });
}

// ===== Auth System =====
function login(user) {
  localStorage.setItem('token', user.token);
  localStorage.setItem('user', JSON.stringify(user.user));
  showApp();
}

function logout() {
  localStorage.removeItem('token');
  localStorage.removeItem('user');
  showAuth();
}

async function checkAuth() {
  const token = localStorage.getItem('token');
  if (!token) {
    showAuth();
    return;
  }
  try {
    const user = await apiFetch('/auth/me');
    if (user) {
      login({ token, user });
    } else {
      showAuth();
    }
  } catch (err) {
    showAuth();
  }
}

function getUser() {
  return JSON.parse(localStorage.getItem('user') || 'null');
}

function showAuth() {
  document.getElementById('auth-view').classList.remove('hidden');
  document.getElementById('app-view').classList.add('hidden');
  spawnParticles();
}

function showApp() {
  const user = getUser();
  document.getElementById('auth-view').classList.add('hidden');
  document.getElementById('app-view').classList.remove('hidden');
  if (user) {
    document.getElementById('user-name').textContent = user.name;
    setAvatar(user.name);
  }
  navigateTo('dashboard');
  loadDashboard();
}

function setAvatar(name) {
  const el = document.getElementById('avatar-initials');
  if (!name) { el.textContent = '👤'; return; }
  const parts = name.trim().split(/\s+/);
  el.textContent = parts.length === 1
    ? parts[0].slice(0, 2).toUpperCase()
    : parts[0][0].toUpperCase() + parts[parts.length - 1][0].toUpperCase();
}

// ===== Floating Food Particles (Auth view background) =====
function spawnParticles() {
  const container = document.getElementById('particles');
  if (!container || container.children.length > 0) return;
  const emojis = ['🥑', '🍎', '🥦', '🥕', '🍞', '🧀', '🍓', '🍋', '🍇', '🌽'];
  for (let i = 0; i < 18; i++) {
    const p = document.createElement('span');
    p.className = 'particle';
    p.textContent = emojis[i % emojis.length];
    p.style.left = `${Math.random() * 92 + 2}%`;
    p.style.animationDuration = `${8 + Math.random() * 12}s`;
    p.style.animationDelay = `${Math.random() * 8}s`;
    container.appendChild(p);
  }
}

// ===== Navigation =====
function navigateTo(view) {
  document.querySelectorAll('.view').forEach(v => v.classList.add('hidden'));
  document.querySelectorAll('.nav-links a').forEach(a => a.classList.remove('active'));

  const target = document.getElementById(`${view}-view`);
  if (target) {
    target.classList.remove('hidden');
    document.querySelector(`[data-view="${view}"]`)?.classList.add('active');
  }

  // Load view data
  if (view === 'dashboard') loadDashboard();
  if (view === 'pantry') loadFood();
  if (view === 'waste') loadWaste();
  if (view === 'recipes') loadRecipes();
  if (view === 'analytics') loadAnalytics();
}

// ===== Dashboard =====
async function loadDashboard() {
  try {
    const stats = await apiFetch('/analytics');
    animateStat('stat-total', stats.overview.totalItems);
    animateStat('stat-fresh', stats.overview.freshItems);
    animateStat('stat-expiring', stats.overview.expiringSoon);
    animateStat('stat-wasted', stats.overview.wastedItems);

    const expiring = stats.overview.expiringSoon;
    const expiringCard = document.getElementById('stat-expiring').closest('.stat-card');
    expiringCard.classList.toggle('is-pulsing', expiring > 0);

    const alertBanner = document.getElementById('expiry-alert');
    if (expiring > 0) {
      document.getElementById('expiry-alert-text').textContent =
        `You have ${expiring} item${expiring > 1 ? 's' : ''} expiring in the next 3 days!`;
      alertBanner.classList.remove('hidden');
    } else {
      alertBanner.classList.add('hidden');
    }

    const recentList = document.getElementById('recent-waste-list');
    if (stats.recentWaste.length === 0) {
      recentList.innerHTML = '<p class="empty-state">No waste logged yet.</p>';
    } else {
      recentList.innerHTML = stats.recentWaste.map((w, i) => `
        <div class="waste-item reveal" style="animation-delay:${i * 0.06}s">
          <div>
            <strong>${escapeHtml(w.name)}</strong> - ${w.quantity} ${w.unit}
            <span class="badge badge-expired">${escapeHtml(w.reason)}</span>
          </div>
          <span style="color: var(--text-muted); font-size: 0.85rem;">${formatDate(w.waste_date)}</span>
        </div>
      `).join('');
      revealIn();
    }
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// ===== Animated Stat Counters =====
function animateStat(id, target) {
  const el = document.getElementById(id);
  if (!el) return;
  const prev = parseInt(el.dataset.count || '0', 10);
  el.dataset.count = String(target);
  const duration = 900;
  const start = performance.now();
  const ease = (t) => 1 - Math.pow(1 - t, 3);
  function tick(now) {
    const p = Math.min((now - start) / duration, 1);
    el.textContent = Math.round(prev + (target - prev) * ease(p));
    if (p < 1) requestAnimationFrame(tick);
    else el.textContent = String(target);
  }
  requestAnimationFrame(tick);
  if (target !== prev) {
    el.classList.remove('bump');
    void el.offsetWidth;
    el.classList.add('bump');
  }
}

// ===== Pantry / Food Items =====
async function loadFood() {
  const filterCategory = document.getElementById('filter-category').value;
  const filterStatus = document.getElementById('filter-status').value;

  try {
    let endpoint = '/food';
    const params = [];
    if (filterCategory) params.push(`category=${filterCategory}`);
    if (filterStatus) params.push(`status=${filterStatus}`);
    if (params.length) endpoint += '?' + params.join('&');

    const items = await apiFetch(endpoint);
    renderFoodList(items);
  } catch (err) {
    showToast(err.message, 'error');
  }
}

function renderFoodList(items) {
  const container = document.getElementById('food-list');
  if (items.length === 0) {
    container.innerHTML = '<p class="empty-state">No food items in your pantry. Add some!</p>';
    return;
  }

  container.innerHTML = items.map((item, i) => {
    const status = getStatus(item);
    const statusClass = `badge-${status.class}`;
    return `
      <div class="food-item reveal" style="animation-delay:${Math.min(i, 8) * 0.05}s">
        <div class="food-info">
          <h4>${escapeHtml(item.name)}</h4>
          <div class="food-meta">
            <span>🏷️ ${escapeHtml(item.category)}</span>
            <span>📦 ${item.quantity} ${item.unit}</span>
            <span>📅 Expires: ${formatDate(item.expiry_date)}</span>
            <span>📍 ${escapeHtml(item.location)}</span>
          </div>
        </div>
        <div class="food-actions">
          <span class="badge ${statusClass}">${status.label}</span>
          <button class="btn btn-small btn-danger" onclick="deleteFood(${item.id}, this)">Delete</button>
        </div>
      </div>
    `;
  }).join('');
  revealIn();
}

function getStatus(item) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const expiry = new Date(item.expiry_date);
  expiry.setHours(0, 0, 0, 0);
  const diff = (expiry - today) / (1000 * 60 * 60 * 24);

  if (item.status === 'wasted') return { label: 'Wasted', class: 'wasted' };
  if (diff < 0) return { label: 'Expired', class: 'expired' };
  if (diff <= 3) return { label: 'Expiring Soon', class: 'expiring' };
  return { label: 'Fresh', class: 'fresh' };
}

async function deleteFood(id, btn) {
  if (!confirm('Delete this food item?')) return;
  const card = btn?.closest('.food-item');
  if (card) card.classList.add('removing');
  setTimeout(async () => {
    try {
      await apiFetch(`/food/${id}`, { method: 'DELETE' });
      showToast('Food item deleted');
      loadFood();
    } catch (err) {
      showToast(err.message, 'error');
      if (card) card.classList.remove('removing');
    }
  }, 250);
}

// Filter handlers
document.getElementById('filter-category')?.addEventListener('change', loadFood);
document.getElementById('filter-status')?.addEventListener('change', loadFood);

// ===== Location Picker Segmented Control =====
document.querySelectorAll('.seg-btn').forEach(btn => {
  btn.addEventListener('click', (e) => {
    const parent = e.target.closest('.form-group');
    parent.querySelectorAll('.seg-btn').forEach(b => b.classList.remove('active'));
    e.target.classList.add('active');
    const input = parent.querySelector('input[name="location"]');
    if (input) input.value = e.target.dataset.location;
  });
});

// ===== Add Food Modal =====
document.getElementById('add-food-btn')?.addEventListener('click', () => {
  document.getElementById('food-form').reset();
  document.querySelector('#food-form input[name="id"]').value = '';
  document.getElementById('food-modal-title').textContent = 'Add Food Item';
  document.getElementById('food-form').dataset.editId = '';
  openModal('food-modal');
});

document.getElementById('food-form')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const form = e.target;
  const id = form.dataset.editId;
  const data = {
    name: form.name.value,
    category: form.category.value,
    quantity: parseFloat(form.quantity.value),
    unit: form.unit.value,
    purchase_date: form.purchase_date.value,
    expiry_date: form.expiry_date.value,
    location: form.location.value || 'fridge',
    notes: form.notes.value,
  };

  try {
    if (id) {
      await apiFetch(`/food/${id}`, { method: 'PUT', body: JSON.stringify(data) });
      showToast('Food item updated');
    } else {
      await apiFetch('/food', { method: 'POST', body: JSON.stringify(data) });
      showToast('Food item added');
    }
    closeModal('food-modal');
    loadFood();
  } catch (err) {
    showToast(err.message, 'error');
  }
});

// ===== Waste Log =====
async function loadWaste() {
  try {
    const items = await apiFetch('/waste');
    renderWasteList(items);
  } catch (err) {
    showToast(err.message, 'error');
  }
}

function renderWasteList(items) {
  const container = document.getElementById('waste-list');
  if (items.length === 0) {
    container.innerHTML = '<p class="empty-state">No waste logged yet.</p>';
    return;
  }

  container.innerHTML = items.map((w, i) => `
    <div class="waste-item reveal" style="animation-delay:${Math.min(i, 8) * 0.05}s">
      <div>
        <strong>${escapeHtml(w.name)}</strong> - ${w.quantity} ${w.unit}
        <span class="badge badge-expired">${escapeHtml(w.reason)}</span>
      </div>
      <div style="display: flex; gap: 10px; align-items: center;">
        <span style="color: var(--text-muted); font-size: 0.85rem;">${formatDate(w.waste_date)}</span>
        <button class="btn btn-small btn-danger" onclick="deleteWaste(${w.id}, this)">Delete</button>
      </div>
    </div>
  `).join('');
  revealIn();
}

async function deleteWaste(id, btn) {
  if (!confirm('Delete this waste entry?')) return;
  const row = btn?.closest('.waste-item');
  if (row) row.classList.add('removing');
  setTimeout(async () => {
    try {
      await apiFetch(`/waste/${id}`, { method: 'DELETE' });
      showToast('Waste entry deleted');
      loadWaste();
    } catch (err) {
      showToast(err.message, 'error');
      if (row) row.classList.remove('removing');
    }
  }, 250);
}

// Log Waste Modal
let wasteItemChoices = [];

// Choosing a pantry item fills the fields below it, so the required Name isn't
// left blank after you've already said what went to waste.
function applyWasteItem() {
  const form = document.getElementById('waste-form');
  const item = wasteItemChoices.find(i => String(i.id) === form.food_item_id.value);
  if (!item) return;
  form.name.value = item.name;
  form.category.value = item.category;
  form.quantity.value = item.quantity;
  form.unit.value = item.unit;
}

document.getElementById('log-waste-btn')?.addEventListener('click', async () => {
  const form = document.getElementById('waste-form');
  form.reset();
  try {
    const items = await apiFetch('/food');
    wasteItemChoices = items.filter(i => i.status !== 'wasted');
    form.food_item_id.innerHTML = '<option value="">-- Enter Manually --</option>' +
      wasteItemChoices.map(i =>
        `<option value="${i.id}">${escapeHtml(i.name)} (${i.quantity} ${i.unit})</option>`
      ).join('');
  } catch (err) {
    wasteItemChoices = [];
    form.food_item_id.innerHTML = '<option value="">-- Enter Manually --</option>';
    showToast(err.message, 'error');
  }
  openModal('waste-modal');
});

document.querySelector('#waste-form select[name="food_item_id"]')
  ?.addEventListener('change', applyWasteItem);

document.getElementById('waste-form')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const form = e.target;
  const data = {
    food_item_id: form.food_item_id.value ? parseInt(form.food_item_id.value) : null,
    name: form.name.value,
    category: form.category.value,
    quantity: parseFloat(form.quantity.value),
    unit: form.unit.value,
    reason: form.reason.value,
  };

  try {
    await apiFetch('/waste', { method: 'POST', body: JSON.stringify(data) });
    showToast('Waste logged successfully');
    closeModal('waste-modal');
    loadWaste();
  } catch (err) {
    showToast(err.message, 'error');
  }
});

// ===== Recipes =====
async function loadRecipes() {
  showRecipeSkeleton();

  try {
    const recipes = await apiFetch('/recipes');
    renderRecipeList(recipes);
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function generateAiRecipes() {
  showRecipeSkeleton();

  const btn = document.getElementById('ai-generate-btn');
  const originalText = btn.innerHTML;
  btn.innerHTML = '<span class="spinner" style="margin-right:8px"></span> Generating...';
  btn.disabled = true;

  try {
    const data = await apiFetch('/recipes/ai-generate-save', { method: 'POST' });
    const saved = data.count ?? (data.recipes || []).length;
    await loadRecipes();
    if (saved > 0) {
      const dupes = data.skipped_duplicates
        ? ` · ${data.skipped_duplicates} duplicate${data.skipped_duplicates === 1 ? '' : 's'} skipped`
        : '';
      showToast(`Saved ${saved} new recipe${saved === 1 ? '' : 's'}${dupes}`, 'success');
    } else {
      showToast(data.message || 'No new recipes generated', 'error');
    }
  } catch (err) {
    showToast(err.message, 'error');
    loadRecipes();
  } finally {
    btn.innerHTML = originalText;
    btn.disabled = false;
  }
}

function renderRecipeList(recipes) {
  const container = document.getElementById('recipe-list');
  if (recipes.length === 0) {
    container.innerHTML = '<p class="empty-state">No recipes generated yet. Click "AI Generate" to create recipes from your expiring ingredients!</p>';
    return;
  }

  container.innerHTML = recipes.map((r, i) => `
    <div class="recipe-card reveal" style="animation-delay:${Math.min(i, 8) * 0.06}s">
      <h3>${escapeHtml(r.title)}</h3>
      ${r.prep_time ? `<div class="recipe-meta">⏱️ ${r.prep_time} minutes</div>` : ''}
      <div class="recipe-ingredients">
        <strong>Ingredients:</strong><br>
        ${escapeHtml(Array.isArray(r.ingredients) ? r.ingredients.join(', ') : r.ingredients)}
      </div>
      <div class="recipe-instructions">${escapeHtml(r.instructions)}</div>
      <button class="btn btn-small btn-danger" onclick="deleteRecipe(${r.id}, this)">Delete</button>
    </div>
  `).join('');
  revealIn();
}

function showRecipeSkeleton() {
  const container = document.getElementById('recipe-list');
  container.innerHTML = `
    <div class="skeleton-card loading" style="animation-delay:0s"></div>
    <div class="skeleton-card loading" style="animation-delay:0.06s"></div>
    <div class="skeleton-card loading" style="animation-delay:0.12s"></div>
  `;
}

async function deleteRecipe(id, btn) {
  if (!confirm('Delete this recipe?')) return;
  const card = btn?.closest('.recipe-card');
  if (card) card.classList.add('removing');
  setTimeout(async () => {
    try {
      await apiFetch(`/recipes/${id}`, { method: 'DELETE' });
      showToast('Recipe deleted');
      loadRecipes();
    } catch (err) {
      showToast(err.message, 'error');
      if (card) card.classList.remove('removing');
    }
  }, 250);
}

document.getElementById('add-recipe-btn')?.addEventListener('click', () => {
  document.getElementById('recipe-form').reset();
  openModal('recipe-modal');
});

document.getElementById('ai-generate-btn')?.addEventListener('click', generateAiRecipes);

document.getElementById('recipe-form')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const form = e.target;
  const data = {
    title: form.title.value,
    ingredients: form.ingredients.value.split(',').map(s => s.trim()).filter(Boolean),
    instructions: form.instructions.value,
    prep_time: form.prep_time.value ? parseInt(form.prep_time.value) : null,
  };

  try {
    await apiFetch('/recipes', { method: 'POST', body: JSON.stringify(data) });
    showToast('Recipe saved');
    closeModal('recipe-modal');
    loadRecipes();
  } catch (err) {
    showToast(err.message, 'error');
  }
});

// ===== Analytics =====
async function loadAnalytics() {
  const root = document.getElementById('analytics-bento');
  if (!root) return;
  try {
    const stats = await apiFetch('/analytics');
    ABENTO.render(root, stats.bento);
  } catch (err) {
    root.removeAttribute('aria-busy');
    root.innerHTML = '<div class="ab-empty">Could not load analytics — '
      + escapeHtml(err.message) + '</div>';
    showToast(err.message, 'error');
  }
}

// ===== Stagger Reveal Helper =====
function revealIn() {
  requestAnimationFrame(() => {
    document.querySelectorAll('.reveal:not(.in-view)').forEach(el => {
      el.classList.add('in-view');
    });
  });
}

// ===== Modal Helpers =====
function openModal(id) {
  const modal = document.getElementById(id);
  if (!modal) return;
  modal.classList.remove('hidden', 'closing');
  document.body.style.overflow = 'hidden';
}

function closeModal(id) {
  const modal = document.getElementById(id);
  if (!modal || modal.classList.contains('hidden')) return;
  modal.classList.add('closing');
  setTimeout(() => {
    modal.classList.add('hidden');
    modal.classList.remove('closing');
    document.body.style.overflow = '';
  }, 220);
}

// Button ripple effect
document.addEventListener('click', (e) => {
  const btn = e.target.closest('.btn');
  if (!btn) return;
  const rect = btn.getBoundingClientRect();
  const circle = document.createElement('span');
  const diameter = Math.max(rect.width, rect.height);
  circle.style.width = circle.style.height = `${diameter}px`;
  circle.style.left = `${e.clientX - rect.left - diameter / 2}px`;
  circle.style.top = `${e.clientY - rect.top - diameter / 2}px`;
  circle.className = 'ripple';
  btn.appendChild(circle);
  setTimeout(() => circle.remove(), 600);
});

// Close modal on overlay click
document.querySelectorAll('.modal').forEach(modal => {
  modal.addEventListener('click', (e) => {
    if (e.target === modal) closeModal(modal.id);
  });
});

// Close modal on Escape key
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    document.querySelectorAll('.modal:not(.hidden)').forEach(m => closeModal(m.id));
  }
});

// Close modal on .modal-close click
document.addEventListener('click', (e) => {
  const closeBtn = e.target.closest('.modal-close');
  if (closeBtn) {
    const modal = closeBtn.closest('.modal');
    if (modal) closeModal(modal.id);
    e.preventDefault();
  }
});

// ===== Auth Form Handlers =====
const AUTH_COPY = {
  login:    { title: 'Welcome back',    sub: 'Sign in to keep wasting less' },
  register: { title: 'Create account',  sub: 'Two minutes now, less waste forever' },
};

function setAuthTab(tab) {
  const toggle = document.querySelector('.auth-toggle');
  if (!toggle) return;
  toggle.classList.toggle('register-mode', tab === 'register');
  toggle.querySelectorAll('.toggle-btn').forEach(b =>
    b.classList.toggle('active', b.dataset.tab === tab));
  document.getElementById('login-form')?.classList.toggle('hidden', tab !== 'login');
  document.getElementById('register-form')?.classList.toggle('hidden', tab !== 'register');
  const copy = AUTH_COPY[tab] || AUTH_COPY.login;
  const titleEl = document.getElementById('auth-title');
  const subEl = document.getElementById('auth-sub');
  if (titleEl) titleEl.textContent = copy.title;
  if (subEl) subEl.textContent = copy.sub;
}

document.querySelectorAll('.auth-toggle .toggle-btn').forEach(btn => {
  btn.addEventListener('click', () => setAuthTab(btn.dataset.tab));
});

document.querySelectorAll('[data-tab-link]').forEach(link => {
  link.addEventListener('click', (e) => {
    e.preventDefault();
    setAuthTab(link.dataset.tabLink);
  });
});

// Password show/hide
document.querySelectorAll('.pw-toggle').forEach(btn => {
  btn.addEventListener('click', () => {
    const input = btn.closest('.input-wrap')?.querySelector('input');
    if (!input) return;
    const show = input.type === 'password';
    input.type = show ? 'text' : 'password';
    btn.textContent = show ? '🙈' : '👁️';
    btn.setAttribute('aria-label', show ? 'Hide password' : 'Show password');
    input.focus();
  });
});

document.getElementById('login-form')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const form = e.target;
  const errorEl = document.getElementById('login-error');
  errorEl.textContent = '';
  try {
    const data = await apiFetch('/auth/login', {
      method: 'POST',
      body: JSON.stringify({
        email: form.email.value,
        password: form.password.value,
      })
    });
    login(data);
  } catch (err) {
    errorEl.textContent = err.message;
  }
});

document.getElementById('register-form')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const form = e.target;
  const errorEl = document.getElementById('register-error');
  errorEl.textContent = '';
  try {
    const data = await apiFetch('/auth/register', {
      method: 'POST',
      body: JSON.stringify({
        name: form.name.value,
        email: form.email.value,
        password: form.password.value,
        role: form.role.value,
      })
    });
    login(data);
  } catch (err) {
    errorEl.textContent = err.message;
  }
});

// ===== Nav Handlers =====
document.querySelectorAll('.nav-links a').forEach(link => {
  link.addEventListener('click', (e) => {
    if (!link.dataset.view) return; // let external links (e.g. /conveyor) navigate normally
    e.preventDefault();
    document.getElementById('nav-links').classList.remove('open');
    navigateTo(link.dataset.view);
  });
});

document.getElementById('logout-btn')?.addEventListener('click', logout);

document.getElementById('nav-toggle')?.addEventListener('click', () => {
  document.getElementById('nav-links').classList.toggle('open');
});

// ===== Utility Functions =====
function formatDate(dateStr) {
  if (!dateStr) return 'N/A';
  return new Date(dateStr).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
}

function escapeHtml(str) {
  if (!str) return '';
  const div = document.createElement('div');
  div.textContent = String(str);
  return div.innerHTML;
}

// ===== Initialize =====
document.addEventListener('DOMContentLoaded', checkAuth);
