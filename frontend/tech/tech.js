/**
 * TechTodards - Client-Side Controller
 * Modern Technology Platform Interface
 * Dynamically loads and renders product cards from products.json
 * Features instant search filtering, keyboard shortcut (/), SVG fallbacks, and schema validation.
 */

const techState = {
  products: [],
  searchQuery: '',
  isLoaded: false
};

/**
 * Basic HTML sanitizer to prevent XSS from JSON strings
 */
function escapeHtml(str) {
  if (typeof str !== 'string') return '';
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

/**
 * Creates SVG fallback element when thumbnail is missing or fails to load
 */
function createFallbackThumb(category = 'Resource') {
  return `
    <div class="tt-card-thumb-fallback" aria-hidden="true">
      <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
        <polyline points="14 2 14 8 20 8"></polyline>
        <line x1="16" y1="13" x2="8" y2="13"></line>
        <line x1="16" y1="17" x2="8" y2="17"></line>
        <polyline points="10 9 9 9 8 9"></polyline>
      </svg>
      <span>${escapeHtml(category)} Guide</span>
    </div>
  `;
}

/**
 * Builds HTML for a single product card (Modern Tech Aesthetic)
 */
function createProductCard(product) {
  const title = escapeHtml(product.title || 'Untitled Resource');
  const desc = escapeHtml(product.description || '');
  const category = escapeHtml(product.category || 'Engineering');
  const downloadUrl = product.downloadUrl ? escapeHtml(product.downloadUrl) : '#';
  const thumbnail = product.thumbnail ? escapeHtml(product.thumbnail) : '';

  // Handle "type" parameter: "download" vs "link"
  const rawType = (product.type || '').trim().toLowerCase();
  const isDownload = rawType === 'download' || (!rawType && /\.(docx|pdf|zip|tar|gz|epub|pptx|xlsx)$/i.test(downloadUrl));
  const buttonText = escapeHtml(product.buttonText || (isDownload ? 'Download' : 'Open Link'));

  // Extract clean filename for download attribute if type="download"
  const urlParts = downloadUrl.split('/');
  const defaultFileName = urlParts[urlParts.length - 1].split('?')[0] || 'download';

  // Anchor attributes: "download" triggers file download; "link" redirects/navigates to URL
  const actionAttrs = isDownload 
    ? `download="${defaultFileName}" target="_blank" rel="noopener noreferrer"` 
    : `target="_blank" rel="noopener noreferrer"`;

  const actionIcon = isDownload
    ? `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
        <polyline points="7 10 12 15 17 10"></polyline>
        <line x1="12" y1="15" x2="12" y2="3"></line>
       </svg>`
    : `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
        <polyline points="15 3 21 3 21 9"></polyline>
        <line x1="10" y1="14" x2="21" y2="3"></line>
       </svg>`;

  const typeTag = isDownload ? 'Direct Download' : 'External Link';

  const card = document.createElement('article');
  card.className = 'tt-card';
  card.id = `product-${escapeHtml(product.id || Math.random().toString(36).substr(2, 9))}`;

  // Image section with category badge and error handling
  let thumbHtml = '';
  if (thumbnail) {
    thumbHtml = `
      <div class="tt-card-thumb-wrap">
        <span class="tt-badge-category">${category}</span>
        <img 
          src="${thumbnail}" 
          alt="${title}" 
          class="tt-card-thumb" 
          loading="lazy"
          onerror="this.parentElement.innerHTML = \`<span class='tt-badge-category'>${category}</span>${createFallbackThumb(category).replace(/"/g, '&quot;')}\`"
        />
      </div>
    `;
  } else {
    thumbHtml = `
      <div class="tt-card-thumb-wrap">
        <span class="tt-badge-category">${category}</span>
        ${createFallbackThumb(category)}
      </div>
    `;
  }

  card.innerHTML = `
    ${thumbHtml}
    <div class="tt-card-body">
      <h3 class="tt-card-title">${title}</h3>
      <p class="tt-card-desc">${desc}</p>
      <div class="tt-card-footer">
        <span class="tt-card-type-tag">${typeTag}</span>
        <a 
          href="${downloadUrl}" 
          class="tt-btn-download" 
          ${actionAttrs}
          aria-label="${isDownload ? 'Download' : 'Open'} ${title}"
        >
          ${actionIcon}
          <span>${buttonText}</span>
        </a>
      </div>
    </div>
  `;

  return card;
}

/**
 * Validates JSON structure
 */
function validateProductsPayload(data) {
  if (!data || typeof data !== 'object') {
    throw new Error('Invalid JSON payload: expected a root JSON object.');
  }
  if (!Array.isArray(data.products)) {
    throw new Error('Invalid JSON structure: missing or non-array "products" field.');
  }
  return data.products;
}

/**
 * Fetches products.json with multiple candidate endpoints
 */
async function fetchProductsData() {
  const candidateUrls = [
    `/tech/products.json?t=${Date.now()}`,
    `./tech/products.json?t=${Date.now()}`,
    `./products.json?t=${Date.now()}`
  ];

  let lastError = null;

  for (const url of candidateUrls) {
    try {
      const res = await fetch(url);
      if (res.ok) {
        const text = await res.text();
        const json = JSON.parse(text);
        return validateProductsPayload(json);
      }
    } catch (err) {
      lastError = err;
    }
  }

  throw lastError || new Error('Failed to load products.json from configured endpoints.');
}

/**
 * Renders the products grid based on current search query
 */
function renderGrid() {
  const gridContainer = document.getElementById('products-grid');
  const countEl = document.getElementById('products-count');

  if (!gridContainer) return;

  const query = techState.searchQuery.trim().toLowerCase();

  // Filter enabled products only
  let filtered = techState.products.filter(item => item && item.enabled !== false);

  if (query) {
    filtered = filtered.filter(item => {
      const title = (item.title || '').toLowerCase();
      const desc = (item.description || '').toLowerCase();
      const cat = (item.category || '').toLowerCase();
      return title.includes(query) || desc.includes(query) || cat.includes(query);
    });
  }

  if (countEl) {
    const totalEnabled = techState.products.filter(p => p.enabled !== false).length;
    if (query) {
      countEl.textContent = `${filtered.length} of ${totalEnabled} Resources`;
    } else {
      countEl.textContent = `${filtered.length} ${filtered.length === 1 ? 'Resource' : 'Resources'}`;
    }
  }

  gridContainer.innerHTML = '';

  if (filtered.length === 0) {
    if (query) {
      gridContainer.innerHTML = `
        <div class="tt-state-box">
          <h3>No matching resources</h3>
          <p>No guides match "${escapeHtml(techState.searchQuery)}". Try searching for "Python", "Data Science", or "SQL".</p>
        </div>
      `;
    } else {
      gridContainer.innerHTML = `
        <div class="tt-state-box">
          <h3>No resources published</h3>
          <p>Configure products in <code>products.json</code> to display them here.</p>
        </div>
      `;
    }
    return;
  }

  filtered.forEach(product => {
    const cardEl = createProductCard(product);
    gridContainer.appendChild(cardEl);
  });
}

/**
 * Keyboard shortcuts (/ to search)
 */
function setupKeyboardShortcuts() {
  const searchInput = document.getElementById('search-input');
  if (!searchInput) return;

  document.addEventListener('keydown', (e) => {
    // If user presses '/' when not currently in an input
    if (e.key === '/' && document.activeElement !== searchInput) {
      e.preventDefault();
      searchInput.focus();
      searchInput.select();
    }
    // Escape to blur search
    if (e.key === 'Escape' && document.activeElement === searchInput) {
      searchInput.blur();
    }
  });
}

/**
 * Main initialization routine
 */
async function initTechPage() {
  const gridContainer = document.getElementById('products-grid');
  const searchInput = document.getElementById('search-input');

  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      techState.searchQuery = e.target.value;
      renderGrid();
    });
  }

  setupKeyboardShortcuts();

  if (gridContainer) {
    gridContainer.innerHTML = `
      <div class="tt-state-box">
        <h3>Loading resources...</h3>
        <p>Connecting to catalog database.</p>
      </div>
    `;
  }

  try {
    const rawProducts = await fetchProductsData();
    techState.products = rawProducts;
    techState.isLoaded = true;
    renderGrid();
  } catch (err) {
    console.error('TechTodards catalog error:', err);
    const countEl = document.getElementById('products-count');
    if (countEl) countEl.textContent = '0 Resources';

    if (gridContainer) {
      gridContainer.innerHTML = `
        <div class="tt-state-box error">
          <h3>Unable to load catalog</h3>
          <p>Please ensure <code>products.json</code> is accessible and valid JSON.</p>
        </div>
      `;
    }
  }
}

// Initialise when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initTechPage);
} else {
  initTechPage();
}
