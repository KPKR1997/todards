/**
 * SectionGrid Component - Renders dynamic N section card stacks
 */
import { createCardStack } from './CardStack.js';

export function renderSectionGrid(sections = [], searchQuery = '') {
  const container = document.getElementById('sections-container');
  if (!container) return;

  container.innerHTML = '';

  if (!sections || sections.length === 0) {
    container.innerHTML = `
      <div style="grid-column: 1 / -1; text-align: center; padding: 4rem 1rem; color: var(--text-muted);">
        <p style="font-size: 1.2rem; font-family: var(--font-serif);">No sections available in todards.json</p>
      </div>
    `;
    return;
  }

  const query = searchQuery.trim().toLowerCase();

  sections.forEach((section) => {
    // Filter cards if search query present
    let filteredCards = section.cards || [];
    if (query) {
      filteredCards = filteredCards.filter(card => 
        (card.title && card.title.toLowerCase().includes(query)) ||
        (card.content && card.content.toLowerCase().includes(query)) ||
        (section.eyebrow && section.eyebrow.toLowerCase().includes(query)) ||
        (section.title && section.title.toLowerCase().includes(query))
      );

      // If no cards match search query in this section, skip section
      if (filteredCards.length === 0) return;
    }

    const sectionCopy = {
      ...section,
      cards: filteredCards
    };

    const stackElement = createCardStack(sectionCopy);
    container.appendChild(stackElement);
  });

  if (container.children.length === 0 && query) {
    container.innerHTML = `
      <div style="grid-column: 1 / -1; text-align: center; padding: 4rem 1rem; color: var(--text-muted);">
        <p style="font-size: 1.2rem; font-family: var(--font-serif);">No stories match "${searchQuery}"</p>
      </div>
    `;
  }
}
