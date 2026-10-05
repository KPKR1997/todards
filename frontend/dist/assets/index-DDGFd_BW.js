(function(){let e=document.createElement(`link`).relList;if(e&&e.supports&&e.supports(`modulepreload`))return;for(let e of document.querySelectorAll(`link[rel="modulepreload"]`))n(e);new MutationObserver(e=>{for(let t of e)if(t.type===`childList`)for(let e of t.addedNodes)e.tagName===`LINK`&&e.rel===`modulepreload`&&n(e)}).observe(document,{childList:!0,subtree:!0});function t(e){let t={};return e.integrity&&(t.integrity=e.integrity),e.referrerPolicy&&(t.referrerPolicy=e.referrerPolicy),t.credentials=e.crossOrigin===`use-credentials`?`include`:e.crossOrigin===`anonymous`?`omit`:`same-origin`,t}function n(e){if(e.ep)return;e.ep=!0;let n=t(e);fetch(e.href,n)}})();function e(e={}){let t=document.getElementById(`meta-issue`),n=document.getElementById(`meta-date`);t&&(t.textContent=(e.issue||e.issueNumber||`ISSUE NO. 248`).toUpperCase()),n&&(n.textContent=(e.publishedAt||e.publishedDate||`21 SEPTEMBER 2026 · 09:00 PM IST`).toUpperCase())}function t(e={},t={}){let i=document.getElementById(`article-modal`),a=document.getElementById(`modal-card-content`);if(!i||!a)return;a.innerHTML=`
    <button class="modal-close-btn" id="btn-modal-close" aria-label="Close modal">✕</button>

    <div class="modal-hero-image-wrapper">
      <img src="${e.image||`https://images.unsplash.com/photo-1518770660439-4636190af475`}" 
           alt="${e.title}" 
           class="modal-hero-image" />
    </div>

    <div class="modal-article-body">
      <div class="modal-meta-row">
        <span class="modal-pill" style="${t.accent?`background:${t.accent};`:``}">
          ${t.eyebrow||`STORY`}
        </span>
        <span class="modal-location-time">
          ${e.place?`${e.place} · `:``}${e.time||e.date||``}
        </span>
      </div>

      <h1 class="modal-title">${e.title||`Untitled Story`}</h1>

      <div class="modal-body-text">
        <p>${e.content||``}</p>
        <br />
        <p style="color: var(--text-secondary); font-style: italic; font-size: 0.95rem;">
          Published as part of the ${r()} daily editorial cards.
        </p>
      </div>
    </div>
  `,i.classList.add(`active`);let o=document.getElementById(`btn-modal-close`);o&&o.addEventListener(`click`,n),i.onclick=e=>{e.target===i&&n()}}function n(){let e=document.getElementById(`article-modal`);e&&e.classList.remove(`active`)}function r(){let e=document.getElementById(`brand-name`);return e?e.textContent:`Todards`}document.addEventListener(`keydown`,e=>{e.key===`Escape`&&n()});function i(e,n){let r=document.createElement(`div`);r.className=`section-stack-container`,r.dataset.sectionId=e.id;let i=e.cards||[],a=0;function o(){r.innerHTML=``;let s=document.createElement(`div`);if(s.className=`card-stack-deck`,i.length===0){let e=document.createElement(`div`);e.className=`stack-card layer-top`,e.style.justifyContent=`center`,e.style.alignItems=`center`,e.innerHTML=`<p style="color: var(--text-muted);">No cards available in this section.</p>`,s.appendChild(e),r.appendChild(s);return}if(i.forEach((r,c)=>{let l=(c-a+i.length)%i.length,u=document.createElement(`article`);u.className=`stack-card`,u.setAttribute(`role`,`button`),u.setAttribute(`tabindex`,`0`),u.setAttribute(`aria-label`,r.title),l===0?u.classList.add(`layer-top`):l===1?u.classList.add(`layer-middle`):l===2?u.classList.add(`layer-back`):u.classList.add(`layer-hidden`),u.innerHTML=`
        <div class="card-image-wrapper">
          <img src="${r.image||`https://images.unsplash.com/photo-1518770660439-4636190af475`}" 
               alt="${r.title}" 
               class="card-image" 
               loading="lazy" />
          <div class="card-image-overlay">
            <div class="card-overlay-top-bar">
              <span class="category-pill" style="${e.accent?`background:${e.accent};`:``}">${e.eyebrow||`SECTION`}</span>
              <span class="card-date">${r.time||r.date||``}</span>
            </div>
            <h3 class="card-image-title-overlay">${r.title}</h3>
          </div>
        </div>

        <div class="card-content-body">
          <h2 class="card-title">${r.title}</h2>
          <p class="card-snippet">${r.content}</p>
          
          <div class="card-footer-action">
            <span>Read more</span>
            <svg class="arrow-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M14 5l7 7m0 0l-7 7m7-7H3"/>
            </svg>
          </div>
        </div>
      `,u.addEventListener(`click`,i=>{l===0?(t(r,e),n&&n(r)):(a=c,o())}),s.appendChild(u)}),r.appendChild(s),i.length>1){let e=document.createElement(`div`);e.className=`stack-dots`,i.forEach((t,n)=>{let r=document.createElement(`button`);r.className=`stack-dot ${n===a?`active`:``}`,r.setAttribute(`aria-label`,`Go to card ${n+1}`),r.addEventListener(`click`,()=>{a=n,o()}),e.appendChild(r)}),r.appendChild(e)}}return o(),r}function a(e=[],t=``){let n=document.getElementById(`sections-container`);if(!n)return;if(n.innerHTML=``,!e||e.length===0){n.innerHTML=`
      <div style="grid-column: 1 / -1; text-align: center; padding: 4rem 1rem; color: var(--text-muted);">
        <p style="font-size: 1.2rem; font-family: var(--font-serif);">No sections available in todards.json</p>
      </div>
    `;return}let r=t.trim().toLowerCase();e.forEach(e=>{let t=e.cards||[];if(r&&(t=t.filter(t=>t.title&&t.title.toLowerCase().includes(r)||t.content&&t.content.toLowerCase().includes(r)||e.eyebrow&&e.eyebrow.toLowerCase().includes(r)||e.title&&e.title.toLowerCase().includes(r)),t.length===0))return;let a=i({...e,cards:t});n.appendChild(a)}),n.children.length===0&&r&&(n.innerHTML=`
      <div style="grid-column: 1 / -1; text-align: center; padding: 4rem 1rem; color: var(--text-muted);">
        <p style="font-size: 1.2rem; font-family: var(--font-serif);">No stories match "${t}"</p>
      </div>
    `)}function o(e,t){let n=document.getElementById(`json-drawer`),r=document.getElementById(`btn-toggle-json`),i=document.getElementById(`btn-close-drawer`),a=document.getElementById(`json-editor-textarea`),o=document.getElementById(`btn-drawer-apply`),s=document.getElementById(`btn-drawer-reset`);if(!n||!r||!a)return;function c(){let t=e();a.value=JSON.stringify(t,null,2),n.classList.add(`active`)}function l(){n.classList.remove(`active`)}r.addEventListener(`click`,c),i.addEventListener(`click`,l),n.addEventListener(`click`,e=>{e.target===n&&l()}),s.addEventListener(`click`,()=>{let t=e();a.value=JSON.stringify(t,null,2)}),o.addEventListener(`click`,()=>{try{t(JSON.parse(a.value)),l()}catch(e){alert(`Invalid JSON formatting: `+e.message)}})}var s={publication:{},sections:[],searchQuery:``,rawJsonHash:``,isLoaded:!1};function c(e={}){let t=document.getElementById(`brand-name`),n=document.getElementById(`brand-subtitle`),r=document.getElementById(`brand-issue`),i=document.getElementById(`footer-left-text`),a=document.getElementById(`footer-right-text`);t&&e.brand&&(t.textContent=e.brand),n&&e.subtitle&&(n.textContent=e.subtitle),r&&(r.textContent=e.issue||e.issueNumber||`Issue No. 248`),i&&e.footerLeft&&(i.textContent=e.footerLeft),a&&e.footerRight&&(a.textContent=e.footerRight)}function l(){c(s.publication),e(s.publication),a(s.sections,s.searchQuery)}async function u(){let e=document.getElementById(`sync-status`);try{let t=await fetch(`./data/todards.json?t=${Date.now()}`);if(!t.ok)throw Error(`HTTP error! status: ${t.status}`);let n=await t.text();if(n!==s.rawJsonHash){let t=JSON.parse(n);s.rawJsonHash=n,s.publication=t.publication||{},s.sections=t.sections||[],s.isLoaded=!0,l(),e&&(e.textContent=`Live Sync Active`,e.style.color=`#15803d`)}}catch(t){console.warn(`Todards live sync fetch notice:`,t.message),e&&!s.isLoaded&&(e.textContent=`Offline Mode`,e.style.color=`#b91c1c`)}}function d(){let e=document.getElementById(`search-input`);e&&e.addEventListener(`input`,e=>{s.searchQuery=e.target.value,a(s.sections,s.searchQuery)});let t=document.getElementById(`btn-nav-about`),n=document.getElementById(`brand-name`),r=document.getElementById(`cards-view`),i=document.getElementById(`about-view`),c=document.getElementById(`search-section`),d=document.getElementById(`pub-meta-bar`),f=`cards`;function p(){f=`cards`,r&&(r.style.display=`block`),c&&(c.style.display=`flex`),d&&(d.style.display=`flex`),i&&(i.style.display=`none`),t&&(t.textContent=`About Todards`),window.scrollTo({top:0,behavior:`smooth`})}function m(){f=`about`,r&&(r.style.display=`none`),c&&(c.style.display=`none`),d&&(d.style.display=`none`),i&&(i.style.display=`block`),t&&(t.textContent=`Back to Cards`),window.scrollTo({top:0,behavior:`smooth`})}t&&t.addEventListener(`click`,e=>{e.preventDefault(),f===`cards`?m():p()}),n&&n.addEventListener(`click`,e=>{e.preventDefault(),p()}),o(()=>({publication:s.publication,sections:s.sections}),e=>{s.publication=e.publication||{},s.sections=e.sections||[],s.rawJsonHash=JSON.stringify(e),l()}),u(),setInterval(u,1200)}document.readyState===`loading`?document.addEventListener(`DOMContentLoaded`,d):d();