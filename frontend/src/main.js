/**
 * Todards Main Controller & Live File Synchronization Engine
 */
import { renderHero } from './components/Hero.js';
import { renderSectionGrid } from './components/SectionGrid.js';
import { initJsonDrawer } from './components/JsonDrawer.js';

// Global Application State
const appState = {
  publication: {},
  sections: [],
  searchQuery: '',
  rawJsonHash: '',
  isLoaded: false
};

/**
 * Update Header and Footer Brand Metadata
 */
function updatePublicationBranding(publication = {}) {
  const brandName = document.getElementById('brand-name');
  const brandSubtitle = document.getElementById('brand-subtitle');
  const brandIssue = document.getElementById('brand-issue');
  const footerLeft = document.getElementById('footer-left-text');
  const footerRight = document.getElementById('footer-right-text');

  if (brandName && publication.brand) brandName.textContent = publication.brand;
  if (brandSubtitle && publication.subtitle) brandSubtitle.textContent = publication.subtitle;
  if (brandIssue) brandIssue.textContent = publication.issue || publication.issueNumber || 'Issue No. 248';
  if (footerLeft && publication.footerLeft) footerLeft.textContent = publication.footerLeft;
  if (footerRight && publication.footerRight) footerRight.textContent = publication.footerRight;
}

/**
 * Full UI Render Cycle
 */
function renderApp() {
  updatePublicationBranding(appState.publication);
  renderHero(appState.publication);
  renderSectionGrid(appState.sections, appState.searchQuery);
}

/**
 * Live File Synchronization Engine
 * Polls data/todards.json with a timestamp to bust browser cache
 */
async function syncDataWithFile() {
  const syncStatusEl = document.getElementById('sync-status');

  try {
    // Add cache busting timestamp
    const response = await fetch(`./data/todards.json?t=${Date.now()}`);
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

    const text = await response.text();
    
    // Check if file content changed
    if (text !== appState.rawJsonHash) {
      const data = JSON.parse(text);
      appState.rawJsonHash = text;
      appState.publication = data.publication || {};
      appState.sections = data.sections || [];
      appState.isLoaded = true;
      
      renderApp();

      if (syncStatusEl) {
        syncStatusEl.textContent = 'Live Sync Active';
        syncStatusEl.style.color = '#15803d';
      }
    }
  } catch (err) {
    console.warn('Todards live sync fetch notice:', err.message);
    if (syncStatusEl && !appState.isLoaded) {
      syncStatusEl.textContent = 'Offline Mode';
      syncStatusEl.style.color = '#b91c1c';
    }
  }
}

/**
 * Initialize Application Event Listeners & Search
 */
function initApp() {
  // Search Input Event Listener
  const searchInput = document.getElementById('search-input');
  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      appState.searchQuery = e.target.value;
      renderSectionGrid(appState.sections, appState.searchQuery);
    });
  }

  // Navigation View Router (Cards View vs About Todards Page)
  const btnAbout = document.getElementById('btn-nav-about');
  const brandName = document.getElementById('brand-name');
  const cardsView = document.getElementById('cards-view');
  const aboutView = document.getElementById('about-view');
  const searchSection = document.getElementById('search-section');
  const pubMetaBar = document.getElementById('pub-meta-bar');

  let currentView = 'cards';

  function showCardsView() {
    currentView = 'cards';
    if (cardsView) cardsView.style.display = 'block';
    if (searchSection) searchSection.style.display = 'flex';
    if (pubMetaBar) pubMetaBar.style.display = 'flex';
    if (aboutView) aboutView.style.display = 'none';
    if (btnAbout) btnAbout.textContent = 'About Todards';
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function showAboutView() {
    currentView = 'about';
    if (cardsView) cardsView.style.display = 'none';
    if (searchSection) searchSection.style.display = 'none';
    if (pubMetaBar) pubMetaBar.style.display = 'none';
    if (aboutView) aboutView.style.display = 'block';
    if (btnAbout) btnAbout.textContent = 'Back to Cards';
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  if (btnAbout) {
    btnAbout.addEventListener('click', (e) => {
      e.preventDefault();
      if (currentView === 'cards') {
        showAboutView();
      } else {
        showCardsView();
      }
    });
  }

  if (brandName) {
    brandName.addEventListener('click', (e) => {
      e.preventDefault();
      showCardsView();
    });
  }

  // Initialize In-Browser Live JSON Drawer
  initJsonDrawer(
    () => ({
      publication: appState.publication,
      sections: appState.sections
    }),
    (newParsedData) => {
      appState.publication = newParsedData.publication || {};
      appState.sections = newParsedData.sections || [];
      appState.rawJsonHash = JSON.stringify(newParsedData);
      renderApp();
    }
  );

  // Initial Fetch & Start Continuous Live File Polling (every 1.2s)
  syncDataWithFile();
  setInterval(syncDataWithFile, 1200);
}

// Start application when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initApp);
} else {
  initApp();
}
