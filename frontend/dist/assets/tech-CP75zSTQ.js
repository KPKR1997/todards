import"./modulepreload-polyfill-B5Qt9EMX.js";const i={products:[],searchQuery:"",isLoaded:!1};function s(t){return typeof t!="string"?"":t.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#039;")}function h(t="Resource"){return`
    <div class="tt-card-thumb-fallback" aria-hidden="true">
      <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
        <polyline points="14 2 14 8 20 8"></polyline>
        <line x1="16" y1="13" x2="8" y2="13"></line>
        <line x1="16" y1="17" x2="8" y2="17"></line>
        <polyline points="10 9 9 9 8 9"></polyline>
      </svg>
      <span>${s(t)} Guide</span>
    </div>
  `}function $(t){const n=s(t.title||"Untitled Resource"),o=s(t.description||""),e=s(t.category||"Engineering"),r=t.downloadUrl?s(t.downloadUrl):"#",a=t.thumbnail?s(t.thumbnail):"",l=(t.type||"").trim().toLowerCase(),c=l==="download"||!l&&/\.(docx|pdf|zip|tar|gz|epub|pptx|xlsx)$/i.test(r),y=s(t.buttonText||(c?"Download":"Open Link")),p=r.split("/"),m=p[p.length-1].split("?")[0]||"download",v=c?`download="${m}" target="_blank" rel="noopener noreferrer"`:'target="_blank" rel="noopener noreferrer"',w=c?`<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
        <polyline points="7 10 12 15 17 10"></polyline>
        <line x1="12" y1="15" x2="12" y2="3"></line>
       </svg>`:`<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
        <polyline points="15 3 21 3 21 9"></polyline>
        <line x1="10" y1="14" x2="21" y2="3"></line>
       </svg>`,b=c?"Direct Download":"External Link",d=document.createElement("article");d.className="tt-card",d.id=`product-${s(t.id||Math.random().toString(36).substr(2,9))}`;let u="";return a?u=`
      <div class="tt-card-thumb-wrap">
        <span class="tt-badge-category">${e}</span>
        <img 
          src="${a}" 
          alt="${n}" 
          class="tt-card-thumb" 
          loading="lazy"
          onerror="this.parentElement.innerHTML = \`<span class='tt-badge-category'>${e}</span>${h(e).replace(/"/g,"&quot;")}\`"
        />
      </div>
    `:u=`
      <div class="tt-card-thumb-wrap">
        <span class="tt-badge-category">${e}</span>
        ${h(e)}
      </div>
    `,d.innerHTML=`
    ${u}
    <div class="tt-card-body">
      <h3 class="tt-card-title">${n}</h3>
      <p class="tt-card-desc">${o}</p>
      <div class="tt-card-footer">
        <span class="tt-card-type-tag">${b}</span>
        <a 
          href="${r}" 
          class="tt-btn-download" 
          ${v}
          aria-label="${c?"Download":"Open"} ${n}"
        >
          ${w}
          <span>${y}</span>
        </a>
      </div>
    </div>
  `,d}function x(t){if(!t||typeof t!="object")throw new Error("Invalid JSON payload: expected a root JSON object.");if(!Array.isArray(t.products))throw new Error('Invalid JSON structure: missing or non-array "products" field.');return t.products}async function E(){const t=[`/tech/products.json?t=${Date.now()}`,`./tech/products.json?t=${Date.now()}`,`./products.json?t=${Date.now()}`];let n=null;for(const o of t)try{const e=await fetch(o);if(e.ok){const r=await e.text(),a=JSON.parse(r);return x(a)}}catch(e){n=e}throw n||new Error("Failed to load products.json from configured endpoints.")}function g(){const t=document.getElementById("products-grid"),n=document.getElementById("products-count");if(!t)return;const o=i.searchQuery.trim().toLowerCase();let e=i.products.filter(r=>r&&r.enabled!==!1);if(o&&(e=e.filter(r=>{const a=(r.title||"").toLowerCase(),l=(r.description||"").toLowerCase(),c=(r.category||"").toLowerCase();return a.includes(o)||l.includes(o)||c.includes(o)})),n){const r=i.products.filter(a=>a.enabled!==!1).length;o?n.textContent=`${e.length} of ${r} Resources`:n.textContent=`${e.length} ${e.length===1?"Resource":"Resources"}`}if(t.innerHTML="",e.length===0){o?t.innerHTML=`
        <div class="tt-state-box">
          <h3>No matching resources</h3>
          <p>No guides match "${s(i.searchQuery)}". Try searching for "Python", "Data Science", or "SQL".</p>
        </div>
      `:t.innerHTML=`
        <div class="tt-state-box">
          <h3>No resources published</h3>
          <p>Configure products in <code>products.json</code> to display them here.</p>
        </div>
      `;return}e.forEach(r=>{const a=$(r);t.appendChild(a)})}function k(){const t=document.getElementById("search-input");t&&document.addEventListener("keydown",n=>{n.key==="/"&&document.activeElement!==t&&(n.preventDefault(),t.focus(),t.select()),n.key==="Escape"&&document.activeElement===t&&t.blur()})}async function f(){const t=document.getElementById("products-grid"),n=document.getElementById("search-input");n&&n.addEventListener("input",o=>{i.searchQuery=o.target.value,g()}),k(),t&&(t.innerHTML=`
      <div class="tt-state-box">
        <h3>Loading resources...</h3>
        <p>Connecting to catalog database.</p>
      </div>
    `);try{const o=await E();i.products=o,i.isLoaded=!0,g()}catch(o){console.error("TechTodards catalog error:",o);const e=document.getElementById("products-count");e&&(e.textContent="0 Resources"),t&&(t.innerHTML=`
        <div class="tt-state-box error">
          <h3>Unable to load catalog</h3>
          <p>Please ensure <code>products.json</code> is accessible and valid JSON.</p>
        </div>
      `)}}document.readyState==="loading"?document.addEventListener("DOMContentLoaded",f):f();
