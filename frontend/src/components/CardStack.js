/**
 * CardStack Component - Interactive 3D Stack Deck for a Section
 */
import { openArticleModal } from './CardModal.js';

export function createCardStack(section, onCardSelect) {
  const container = document.createElement('div');
  container.className = 'section-stack-container';
  container.dataset.sectionId = section.id;

  const cards = section.cards || [];
  let activeIndex = 0;

  function renderDeck() {
    container.innerHTML = '';

    const deck = document.createElement('div');
    deck.className = 'card-stack-deck';

    if (cards.length === 0) {
      const emptyMsg = document.createElement('div');
      emptyMsg.className = 'stack-card layer-top';
      emptyMsg.style.justifyContent = 'center';
      emptyMsg.style.alignItems = 'center';
      emptyMsg.innerHTML = '<p style="color: var(--text-muted);">No cards available in this section.</p>';
      deck.appendChild(emptyMsg);
      container.appendChild(deck);
      return;
    }

    // Reorder cards relative to activeIndex so activeIndex card is layer-top
    cards.forEach((card, idx) => {
      const relativePos = (idx - activeIndex + cards.length) % cards.length;
      const cardEl = document.createElement('article');
      cardEl.className = 'stack-card';
      // Section theme color used by the card border/shadow
      cardEl.style.setProperty(
        '--card-theme',
        section.theme || '#000000'
      );
      cardEl.setAttribute('role', 'button');
      cardEl.setAttribute('tabindex', '0');
      cardEl.setAttribute('aria-label', card.title);

      // Assign layer positioning class
      if (relativePos === 0) {
        cardEl.classList.add('layer-top');
      } else if (relativePos === 1) {
        cardEl.classList.add('layer-middle');
      } else if (relativePos === 2) {
        cardEl.classList.add('layer-back');
      } else {
        cardEl.classList.add('layer-hidden');
      }

      // Card Content Markup
      cardEl.innerHTML = `
        <div class="card-image-wrapper">
          <img src="${card.image || 'https://images.unsplash.com/photo-1518770660439-4636190af475'}" 
               alt="${card.title}" 
               class="card-image" 
               loading="lazy" />
          <div class="card-image-overlay">
            <div class="card-overlay-top-bar">
              <span class="category-pill" style="${section.accent ? `background:${section.accent};` : ''}">${section.eyebrow || 'SECTION'}</span>
              <span class="card-date">${card.time || card.date || ''}</span>
            </div>
            <h3 class="card-image-title-overlay">${card.title}</h3>
          </div>
        </div>

        <div class="card-content-body">
          <h2 class="card-title">${card.title}</h2>
          <p class="card-snippet">${card.content}</p>
          
          <div class="card-footer-action">
            <span>Read more</span>
            <svg class="arrow-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M14 5l7 7m0 0l-7 7m7-7H3"/>
            </svg>
          </div>
        </div>
      `;

      // Card Click Handler
      cardEl.addEventListener('click', (e) => {
        if (relativePos === 0) {
          // Top card clicked -> Open full Article Reader Modal
          openArticleModal(card, section);
          if (onCardSelect) onCardSelect(card);
        } else {
          // Stacked card behind clicked -> Bring it to front!
          activeIndex = idx;
          renderDeck();
        }
      });

      deck.appendChild(cardEl);
    });

    container.appendChild(deck);

    // Render Pagination Dots below Deck
    if (cards.length > 1) {
      const dotsContainer = document.createElement('div');
      dotsContainer.className = 'stack-dots';

      cards.forEach((_, idx) => {
        const dot = document.createElement('button');
        dot.className = `stack-dot ${idx === activeIndex ? 'active' : ''}`;
        dot.setAttribute('aria-label', `Go to card ${idx + 1}`);
        dot.addEventListener('click', () => {
          activeIndex = idx;
          renderDeck();
        });
        dotsContainer.appendChild(dot);
      });

      container.appendChild(dotsContainer);
    }
  }

  renderDeck();
  return container;
}
