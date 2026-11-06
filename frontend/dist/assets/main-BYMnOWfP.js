import"./modulepreload-polyfill-B5Qt9EMX.js";/* empty css              */function g(e={}){const a=document.getElementById("meta-issue"),t=document.getElementById("meta-date");if(a){const s=e.issue||e.issueNumber||"ISSUE NO. 248";a.textContent=s.toUpperCase()}if(t){const s=e.publishedAt||e.publishedDate||"21 SEPTEMBER 2026 · 09:00 PM IST";t.textContent=s.toUpperCase()}}function h(e={},a={}){const t=document.getElementById("article-modal"),s=document.getElementById("modal-card-content");if(!t||!s)return;s.innerHTML=`
    <button class="modal-close-btn" id="btn-modal-close" aria-label="Close modal">✕</button>

    <div class="modal-hero-image-wrapper">
    <img
      src="${e.image||"https://images.unsplash.com/photo-1518770660439-4636190af475"}"
      alt="${e.title}"
      class="modal-hero-image"
    />

    <span
      class="modal-pill"
      style="${a.accent?`background:${a.accent};`:""}"
    >
      ${a.eyebrow||"STORY"}
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
  `,t.classList.add("active");const i=document.getElementById("btn-modal-close");i&&i.addEventListener("click",u),t.onclick=l=>{l.target===t&&u()}}function u(){const e=document.getElementById("article-modal");e&&e.classList.remove("active")}document.addEventListener("keydown",e=>{e.key==="Escape"&&u()});function b(e,a){const t=document.createElement("div");t.className="section-stack-container",t.dataset.sectionId=e.id;const s=e.cards||[];let i=0;function l(){t.innerHTML="";const r=document.createElement("div");if(r.className="card-stack-deck",s.length===0){const o=document.createElement("div");o.className="stack-card layer-top",o.style.justifyContent="center",o.style.alignItems="center",o.innerHTML='<p style="color: var(--text-muted);">No cards available in this section.</p>',r.appendChild(o),t.appendChild(r);return}if(s.forEach((o,m)=>{const d=(m-i+s.length)%s.length,n=document.createElement("article");n.className="stack-card",n.style.setProperty("--card-theme",e.theme||"#000000"),n.setAttribute("role","button"),n.setAttribute("tabindex","0"),n.setAttribute("aria-label",o.title),d===0?n.classList.add("layer-top"):d===1?n.classList.add("layer-middle"):d===2?n.classList.add("layer-back"):n.classList.add("layer-hidden"),n.innerHTML=`
        <div class="card-image-wrapper">
          <img src="${o.image||"https://images.unsplash.com/photo-1518770660439-4636190af475"}" 
               alt="${o.title}" 
               class="card-image" 
               loading="lazy" />
          <div class="card-image-overlay">
            <div class="card-overlay-top-bar">
              <span class="category-pill" style="${e.accent?`background:${e.accent};`:""}">${e.eyebrow||"SECTION"}</span>
              <span class="card-date">${o.time||o.date||""}</span>
            </div>
            <h3 class="card-image-title-overlay">${o.title}</h3>
          </div>
        </div>

        <div class="card-content-body">
          <h2 class="card-title">${o.title}</h2>
          <p class="card-snippet">${o.content}</p>
          
          <div class="card-footer-action">
            <span>Read more</span>
            <svg class="arrow-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M14 5l7 7m0 0l-7 7m7-7H3"/>
            </svg>
          </div>
        </div>
      `,n.addEventListener("click",L=>{d===0?h(o,e):(i=m,l())}),r.appendChild(n)}),t.appendChild(r),s.length>1){const o=document.createElement("div");o.className="stack-dots",s.forEach((m,d)=>{const n=document.createElement("button");n.className=`stack-dot ${d===i?"active":""}`,n.setAttribute("aria-label",`Go to card ${d+1}`),n.addEventListener("click",()=>{i=d,l()}),o.appendChild(n)}),t.appendChild(o)}}return l(),t}function p(e=[],a=""){const t=document.getElementById("sections-container");if(!t)return;if(t.innerHTML="",!e||e.length===0){t.innerHTML=`
      <div style="grid-column: 1 / -1; text-align: center; padding: 4rem 1rem; color: var(--text-muted);">
        <p style="font-size: 1.2rem; font-family: var(--font-serif);">No sections available in todards.json</p>
      </div>
    `;return}const s=a.trim().toLowerCase();e.forEach(i=>{let l=i.cards||[];if(s&&(l=l.filter(m=>m.title&&m.title.toLowerCase().includes(s)||m.content&&m.content.toLowerCase().includes(s)||i.eyebrow&&i.eyebrow.toLowerCase().includes(s)||i.title&&i.title.toLowerCase().includes(s)),l.length===0))return;const r={...i,cards:l},o=b(r);t.appendChild(o)}),t.children.length===0&&s&&(t.innerHTML=`
      <div style="grid-column: 1 / -1; text-align: center; padding: 4rem 1rem; color: var(--text-muted);">
        <p style="font-size: 1.2rem; font-family: var(--font-serif);">No stories match "${a}"</p>
      </div>
    `)}function E(e,a){const t=document.getElementById("json-drawer"),s=document.getElementById("btn-toggle-json"),i=document.getElementById("btn-close-drawer"),l=document.getElementById("json-editor-textarea"),r=document.getElementById("btn-drawer-apply"),o=document.getElementById("btn-drawer-reset");if(!t||!s||!l)return;function m(){const n=e();l.value=JSON.stringify(n,null,2),t.classList.add("active")}function d(){t.classList.remove("active")}s.addEventListener("click",m),i.addEventListener("click",d),t.addEventListener("click",n=>{n.target===t&&d()}),o.addEventListener("click",()=>{const n=e();l.value=JSON.stringify(n,null,2)}),r.addEventListener("click",()=>{try{const n=JSON.parse(l.value);a(n),d()}catch(n){alert("Invalid JSON formatting: "+n.message)}})}const c={publication:{},sections:[],searchQuery:"",rawJsonHash:"",isLoaded:!1};function w(e={}){const a=document.getElementById("brand-name"),t=document.getElementById("brand-subtitle"),s=document.getElementById("brand-issue"),i=document.getElementById("footer-left-text"),l=document.getElementById("footer-right-text");a&&e.brand&&(a.textContent=e.brand),t&&e.subtitle&&(t.textContent=e.subtitle),s&&(s.textContent=e.issue||e.issueNumber||"Issue No. 248"),i&&e.footerLeft&&(i.textContent=e.footerLeft),l&&e.footerRight&&(l.textContent=e.footerRight)}function v(){w(c.publication),g(c.publication),p(c.sections,c.searchQuery)}async function f(){const e=document.getElementById("sync-status");try{const a=await fetch(`./data/todards.json?t=${Date.now()}`);if(!a.ok)throw new Error(`HTTP error! status: ${a.status}`);const t=await a.text();if(t!==c.rawJsonHash){const s=JSON.parse(t);c.rawJsonHash=t,c.publication=s.publication||{},c.sections=s.sections||[],c.isLoaded=!0,v(),e&&(e.textContent="Live Sync Active",e.style.color="#15803d")}}catch(a){console.warn("Todards live sync fetch notice:",a.message),e&&!c.isLoaded&&(e.textContent="Offline Mode",e.style.color="#b91c1c")}}function y(){const e=document.getElementById("search-input");e&&e.addEventListener("input",n=>{c.searchQuery=n.target.value,p(c.sections,c.searchQuery)});const a=document.getElementById("btn-nav-about"),t=document.getElementById("brand-name"),s=document.getElementById("cards-view"),i=document.getElementById("about-view"),l=document.getElementById("search-section"),r=document.getElementById("pub-meta-bar");let o="cards";function m(){o="cards",s&&(s.style.display="block"),l&&(l.style.display="flex"),r&&(r.style.display="flex"),i&&(i.style.display="none"),a&&(a.textContent="About Todards"),window.scrollTo({top:0,behavior:"smooth"})}function d(){o="about",s&&(s.style.display="none"),l&&(l.style.display="none"),r&&(r.style.display="none"),i&&(i.style.display="block"),a&&(a.textContent="Back to Cards"),window.scrollTo({top:0,behavior:"smooth"})}a&&a.addEventListener("click",n=>{n.preventDefault(),o==="cards"?d():m()}),t&&t.addEventListener("click",n=>{n.preventDefault(),m()}),E(()=>({publication:c.publication,sections:c.sections}),n=>{c.publication=n.publication||{},c.sections=n.sections||[],c.rawJsonHash=JSON.stringify(n),v()}),f(),setInterval(f,1200)}document.readyState==="loading"?document.addEventListener("DOMContentLoaded",y):y();
