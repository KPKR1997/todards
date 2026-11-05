/* empty css              */(function(){const r=document.createElement("link").relList;if(r&&r.supports&&r.supports("modulepreload"))return;for(const n of document.querySelectorAll('link[rel="modulepreload"]'))s(n);new MutationObserver(n=>{for(const a of n)if(a.type==="childList")for(const c of a.addedNodes)c.tagName==="LINK"&&c.rel==="modulepreload"&&s(c)}).observe(document,{childList:!0,subtree:!0});function t(n){const a={};return n.integrity&&(a.integrity=n.integrity),n.referrerPolicy&&(a.referrerPolicy=n.referrerPolicy),n.crossOrigin==="use-credentials"?a.credentials="include":n.crossOrigin==="anonymous"?a.credentials="omit":a.credentials="same-origin",a}function s(n){if(n.ep)return;n.ep=!0;const a=t(n);fetch(n.href,a)}})();function v(e={}){const r=document.getElementById("meta-issue"),t=document.getElementById("meta-date");if(r){const s=e.issue||e.issueNumber||"ISSUE NO. 248";r.textContent=s.toUpperCase()}if(t){const s=e.publishedAt||e.publishedDate||"21 SEPTEMBER 2026 · 09:00 PM IST";t.textContent=s.toUpperCase()}}function h(e={},r={}){const t=document.getElementById("article-modal"),s=document.getElementById("modal-card-content");if(!t||!s)return;s.innerHTML=`
    <button class="modal-close-btn" id="btn-modal-close" aria-label="Close modal">✕</button>

    <div class="modal-hero-image-wrapper">
    <img
      src="${e.image||"https://images.unsplash.com/photo-1518770660439-4636190af475"}"
      alt="${e.title}"
      class="modal-hero-image"
    />

    <span
      class="modal-pill"
      style="${r.accent?`background:${r.accent};`:""}"
    >
      ${r.eyebrow||"STORY"}
    </span>
  </div>

  <div class="modal-article-body">
    <div class="modal-meta-row">
      <span class="modal-location-time">
        ${e.place?`${e.place} · `:""}${e.time||e.date||""}
      </span>
    </div>

  <h1 class="modal-title">${e.title||"Untitled Story"}</h1>

      <div class="modal-body-text">
        <p>${e.content||""}</p>
        <br />
        <p style="color: var(--text-secondary); font-style: italic; font-size: 0.95rem;">
          source: <a href="${e.url}" target="_blank" rel="noopener noreferrer">${e.source}</a>
        </p>
      </div>
    </div>
  `,t.classList.add("active");const n=document.getElementById("btn-modal-close");n&&n.addEventListener("click",u),t.onclick=a=>{a.target===t&&u()}}function u(){const e=document.getElementById("article-modal");e&&e.classList.remove("active")}document.addEventListener("keydown",e=>{e.key==="Escape"&&u()});function b(e,r){const t=document.createElement("div");t.className="section-stack-container",t.dataset.sectionId=e.id;const s=e.cards||[];let n=0;function a(){t.innerHTML="";const c=document.createElement("div");if(c.className="card-stack-deck",s.length===0){const i=document.createElement("div");i.className="stack-card layer-top",i.style.justifyContent="center",i.style.alignItems="center",i.innerHTML='<p style="color: var(--text-muted);">No cards available in this section.</p>',c.appendChild(i),t.appendChild(c);return}if(s.forEach((i,m)=>{const d=(m-n+s.length)%s.length,o=document.createElement("article");o.className="stack-card",o.style.setProperty("--card-theme",e.theme||"#000000"),o.setAttribute("role","button"),o.setAttribute("tabindex","0"),o.setAttribute("aria-label",i.title),d===0?o.classList.add("layer-top"):d===1?o.classList.add("layer-middle"):d===2?o.classList.add("layer-back"):o.classList.add("layer-hidden"),o.innerHTML=`
        <div class="card-image-wrapper">
          <img src="${i.image||"https://images.unsplash.com/photo-1518770660439-4636190af475"}" 
               alt="${i.title}" 
               class="card-image" 
               loading="lazy" />
          <div class="card-image-overlay">
            <div class="card-overlay-top-bar">
              <span class="category-pill" style="${e.accent?`background:${e.accent};`:""}">${e.eyebrow||"SECTION"}</span>
              <span class="card-date">${i.time||i.date||""}</span>
            </div>
            <h3 class="card-image-title-overlay">${i.title}</h3>
          </div>
        </div>

        <div class="card-content-body">
          <h2 class="card-title">${i.title}</h2>
          <p class="card-snippet">${i.content}</p>
          
          <div class="card-footer-action">
            <span>Read more</span>
            <svg class="arrow-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M14 5l7 7m0 0l-7 7m7-7H3"/>
            </svg>
          </div>
        </div>
      `,o.addEventListener("click",L=>{d===0?h(i,e):(n=m,a())}),c.appendChild(o)}),t.appendChild(c),s.length>1){const i=document.createElement("div");i.className="stack-dots",s.forEach((m,d)=>{const o=document.createElement("button");o.className=`stack-dot ${d===n?"active":""}`,o.setAttribute("aria-label",`Go to card ${d+1}`),o.addEventListener("click",()=>{n=d,a()}),i.appendChild(o)}),t.appendChild(i)}}return a(),t}function y(e=[],r=""){const t=document.getElementById("sections-container");if(!t)return;if(t.innerHTML="",!e||e.length===0){t.innerHTML=`
      <div style="grid-column: 1 / -1; text-align: center; padding: 4rem 1rem; color: var(--text-muted);">
        <p style="font-size: 1.2rem; font-family: var(--font-serif);">No sections available in todards.json</p>
      </div>
    `;return}const s=r.trim().toLowerCase();e.forEach(n=>{let a=n.cards||[];if(s&&(a=a.filter(m=>m.title&&m.title.toLowerCase().includes(s)||m.content&&m.content.toLowerCase().includes(s)||n.eyebrow&&n.eyebrow.toLowerCase().includes(s)||n.title&&n.title.toLowerCase().includes(s)),a.length===0))return;const c={...n,cards:a},i=b(c);t.appendChild(i)}),t.children.length===0&&s&&(t.innerHTML=`
      <div style="grid-column: 1 / -1; text-align: center; padding: 4rem 1rem; color: var(--text-muted);">
        <p style="font-size: 1.2rem; font-family: var(--font-serif);">No stories match "${r}"</p>
      </div>
    `)}function E(e,r){const t=document.getElementById("json-drawer"),s=document.getElementById("btn-toggle-json"),n=document.getElementById("btn-close-drawer"),a=document.getElementById("json-editor-textarea"),c=document.getElementById("btn-drawer-apply"),i=document.getElementById("btn-drawer-reset");if(!t||!s||!a)return;function m(){const o=e();a.value=JSON.stringify(o,null,2),t.classList.add("active")}function d(){t.classList.remove("active")}s.addEventListener("click",m),n.addEventListener("click",d),t.addEventListener("click",o=>{o.target===t&&d()}),i.addEventListener("click",()=>{const o=e();a.value=JSON.stringify(o,null,2)}),c.addEventListener("click",()=>{try{const o=JSON.parse(a.value);r(o),d()}catch(o){alert("Invalid JSON formatting: "+o.message)}})}const l={publication:{},sections:[],searchQuery:"",rawJsonHash:"",isLoaded:!1};function w(e={}){const r=document.getElementById("brand-name"),t=document.getElementById("brand-subtitle"),s=document.getElementById("brand-issue"),n=document.getElementById("footer-left-text"),a=document.getElementById("footer-right-text");r&&e.brand&&(r.textContent=e.brand),t&&e.subtitle&&(t.textContent=e.subtitle),s&&(s.textContent=e.issue||e.issueNumber||"Issue No. 248"),n&&e.footerLeft&&(n.textContent=e.footerLeft),a&&e.footerRight&&(a.textContent=e.footerRight)}function g(){w(l.publication),v(l.publication),y(l.sections,l.searchQuery)}async function f(){const e=document.getElementById("sync-status");try{const r=await fetch(`./data/todards.json?t=${Date.now()}`);if(!r.ok)throw new Error(`HTTP error! status: ${r.status}`);const t=await r.text();if(t!==l.rawJsonHash){const s=JSON.parse(t);l.rawJsonHash=t,l.publication=s.publication||{},l.sections=s.sections||[],l.isLoaded=!0,g(),e&&(e.textContent="Live Sync Active",e.style.color="#15803d")}}catch(r){console.warn("Todards live sync fetch notice:",r.message),e&&!l.isLoaded&&(e.textContent="Offline Mode",e.style.color="#b91c1c")}}function p(){const e=document.getElementById("search-input");e&&e.addEventListener("input",o=>{l.searchQuery=o.target.value,y(l.sections,l.searchQuery)});const r=document.getElementById("btn-nav-about"),t=document.getElementById("brand-name"),s=document.getElementById("cards-view"),n=document.getElementById("about-view"),a=document.getElementById("search-section"),c=document.getElementById("pub-meta-bar");let i="cards";function m(){i="cards",s&&(s.style.display="block"),a&&(a.style.display="flex"),c&&(c.style.display="flex"),n&&(n.style.display="none"),r&&(r.textContent="About Todards"),window.scrollTo({top:0,behavior:"smooth"})}function d(){i="about",s&&(s.style.display="none"),a&&(a.style.display="none"),c&&(c.style.display="none"),n&&(n.style.display="block"),r&&(r.textContent="Back to Cards"),window.scrollTo({top:0,behavior:"smooth"})}r&&r.addEventListener("click",o=>{o.preventDefault(),i==="cards"?d():m()}),t&&t.addEventListener("click",o=>{o.preventDefault(),m()}),E(()=>({publication:l.publication,sections:l.sections}),o=>{l.publication=o.publication||{},l.sections=o.sections||[],l.rawJsonHash=JSON.stringify(o),g()}),f(),setInterval(f,1200)}document.readyState==="loading"?document.addEventListener("DOMContentLoaded",p):p();
