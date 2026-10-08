/**
 * CardModal Component - Full Article Reader Overlay
 */
export function openArticleModal(card = {}, section = {}) {
  const modalOverlay = document.getElementById('article-modal');
  const modalContent = document.getElementById('modal-card-content');
  if (!modalOverlay || !modalContent) return;

  modalContent.innerHTML = `
    <button class="modal-close-btn" id="btn-modal-close" aria-label="Close modal">✕</button>

    <div class="modal-hero-image-wrapper">
    <img
      src="${card.image || 'https://images.unsplash.com/photo-1518770660439-4636190af475'}"
      alt="${card.title}"
      class="modal-hero-image"
    />

    <span
      class="modal-pill"
      style="${section.accent ? `background:${section.accent};` : ''}"
    >
      ${section.eyebrow || 'STORY'}
    </span>
  </div>

  <div class="modal-article-body">
    <div class="modal-meta-row">
      <span class="modal-location-time">
        ${card.place ? `${card.place} · ` : ''}${card.time || card.date || ''}
      </span>
    </div>

  <h1 class="modal-title">${card.title || 'Untitled Story'}</h1>

      <div class="modal-body-text">
        <p>${card.content || ''}</p>
        <br />
        <p style="color: var(--text-secondary); font-style: italic; font-size: 0.95rem;">
          source: ${card.source}
        </p>
      </div>
    </div>
  `;

  modalOverlay.classList.add('active');

  const closeBtn = document.getElementById('btn-modal-close');
  if (closeBtn) {
    closeBtn.addEventListener('click', closeArticleModal);
  }

  modalOverlay.onclick = (e) => {
    if (e.target === modalOverlay) closeArticleModal();
  };
}

export function closeArticleModal() {
  const modalOverlay = document.getElementById('article-modal');
  if (modalOverlay) {
    modalOverlay.classList.remove('active');
  }
}

function publicationBrandName() {
  const brandEl = document.getElementById('brand-name');
  return brandEl ? brandEl.textContent : 'Todards';
}

// Escape key to close modal
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    closeArticleModal();
  }
});
