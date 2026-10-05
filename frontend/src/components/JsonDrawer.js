/**
 * JsonDrawer Component - Interactive In-Browser Live JSON Editor
 */
export function initJsonDrawer(getCurrentData, onApplyEdits) {
  const drawerOverlay = document.getElementById('json-drawer');
  const toggleBtn = document.getElementById('btn-toggle-json');
  const closeBtn = document.getElementById('btn-close-drawer');
  const textarea = document.getElementById('json-editor-textarea');
  const applyBtn = document.getElementById('btn-drawer-apply');
  const resetBtn = document.getElementById('btn-drawer-reset');

  if (!drawerOverlay || !toggleBtn || !textarea) return;

  function openDrawer() {
    const data = getCurrentData();
    textarea.value = JSON.stringify(data, null, 2);
    drawerOverlay.classList.add('active');
  }

  function closeDrawer() {
    drawerOverlay.classList.remove('active');
  }

  toggleBtn.addEventListener('click', openDrawer);
  closeBtn.addEventListener('click', closeDrawer);

  drawerOverlay.addEventListener('click', (e) => {
    if (e.target === drawerOverlay) closeDrawer();
  });

  resetBtn.addEventListener('click', () => {
    const data = getCurrentData();
    textarea.value = JSON.stringify(data, null, 2);
  });

  applyBtn.addEventListener('click', () => {
    try {
      const parsed = JSON.parse(textarea.value);
      onApplyEdits(parsed);
      closeDrawer();
    } catch (err) {
      alert('Invalid JSON formatting: ' + err.message);
    }
  });
}
