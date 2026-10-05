/**
 * Hero Component - Renders editorial headlines dynamically from publication metadata
 */
export function renderHero(publication = {}) {
  const issueEl = document.getElementById('meta-issue');
  const dateEl = document.getElementById('meta-date');

  if (issueEl) {
    const rawIssue = publication.issue || publication.issueNumber || 'ISSUE NO. 248';
    issueEl.textContent = rawIssue.toUpperCase();
  }

  if (dateEl) {
    const rawDate = publication.publishedAt || publication.publishedDate || '21 SEPTEMBER 2026 · 09:00 PM IST';
    dateEl.textContent = rawDate.toUpperCase();
  }
}
