# TechTodards Documentation & Operations Guide

## 1. Overview & Purpose
**TechTodards** is a dedicated, standalone technology resource platform within the Todards website ecosystem. It delivers engineering guides, interview cheatsheets, and architectural resources for software developers, data scientists, and technology learners.

### Visual Aesthetic & Logo-Derived Color Palette
The page features a modern technology platform aesthetic inspired by the official TechTodards logo:
- **Primary Brand Colors**:
  - **Electric Blue (`#0052ff`)**: Directly matching the blue dot and "Tech" branding from the official logo. Used for interactive CTAs, hero accents, active states, and focus rings.
  - **Stark Tech Black (`#09090b`)**: Bold, high-contrast headings, logo mark, and card typography.
  - **Clean White (`#ffffff`) & Slate Backgrounds (`#f8fafc`)**: Crisp backdrop with a subtle modern developer grid pattern (`40px x 40px`).
  - **Slate Greys (`#64748b` / `#e2e8f0`)**: Subtle micro-borders, metadata badges, and clean secondary typography.
- **Typography**: Crisp modern sans-serif (`Inter`) paired with monospace accents (`JetBrains Mono`) for categories and metadata.
- **Header**: Minimalist navigation bar with logo and live hub indicator (no page navigation links).
- **Interactive Search**: Real-time filtering with `/` keyboard shortcut support.

---

## 2. Page Route & Access
- **Route**: `/tech` (served via `tech/index.html`)
- **Development Server Access**: When running Vite (`npm run dev`), the page is accessible at:
  `http://localhost:5173/tech` or `http://localhost:5173/tech/`

---

## 3. Architecture & File Structure
All new code and visual assets remain strictly isolated within dedicated directories to protect the production Todards news application:

```text
frontend/
│
├── tech/
│   ├── index.html       # Standalone HTML entry point for the /tech route
│   ├── tech.js          # Client-side dynamic loader, live search, validator & renderer
│   ├── tech.css         # Page-scoped CSS styles under .tech-page (Tech theme)
│   └── products.json    # Single source of truth for all product cards
│
├── assets/
│   └── tech/
│       ├── logo.jpg                  # Official TechTodards brand logo
│       └── product-thumbnails/       # Source SVG/PNG product thumbnails
│           ├── data-science-interview.svg
│           ├── python-guide.svg
│           ├── system-design.svg
│           └── ml-guide.svg
│
├── public/
│   ├── assets/
│   │   └── tech/        # Publicly served assets (logo, thumbnails)
│   └── tech/
│       └── products.json # Static runtime endpoint fallback
│
└── README_TECH.md       # Operational documentation & change ledger
```

---

## 4. Technologies & Components Used
- **Vanilla JavaScript (ES Modules)**: Lightweight, 0 external npm runtime dependencies.
- **Page-Scoped CSS**: All styles are strictly scoped under `.tech-page` to completely eliminate CSS leakage into existing pages.
- **Dynamic Search & Filtering**: Client-side query matching against `title`, `description`, and `category` with `/` shortcut.
- **JSON Data Architecture**: Dynamic DOM rendering with runtime validation, XSS sanitization (`escapeHtml`), and automatic fallback placeholders for missing or failing images.

---

## 5. Product Management Guide (`products.json`)

The file `tech/products.json` is the **single source of truth** for all product cards displayed on the page.

### Schema
```json
{
  "products": [
    {
      "id": "unique-product-slug",
      "title": "Title of Guide or Handbook",
      "description": "Short summary explaining the value of the resource.",
      "category": "Data Science | Python | Architecture | etc.",
      "thumbnail": "/assets/tech/your-image.svg",
      "downloadUrl": "https://example.com/download-link",
      "buttonText": "Download",
      "type": "download | link",
      "enabled": true
    }
  ]
}
```

### Action Types: `download` vs `link`
- **`type: "download"`**:
  - Automatically triggers a direct browser file download for the file location specified in `downloadUrl`.
  - Attaches the HTML `download` attribute and displays a direct download icon.
- **`type: "link"`**:
  - Redirects / navigates to the external destination URL in a new tab (`target="_blank" rel="noopener noreferrer"`).
  - Displays an external link arrow icon.
- **Default / Fallback**: If `type` is omitted, `tech.js` automatically infers `download` for file assets (`.docx`, `.pdf`, `.zip`, etc.) and `link` for web URLs.

### How to Add a New Product
1. Open `tech/products.json`.
2. Add a new object inside the `"products"` array:
   ```json
   {
     "id": "docker-kubernetes-cheatsheet",
     "title": "Docker & Kubernetes Cheatsheet",
     "description": "Production container commands, orchestration patterns, and debugging tips.",
     "category": "DevOps",
     "thumbnail": "/assets/tech/docker-cheatsheet.svg",
     "downloadUrl": "https://example.com/docker-guide",
     "buttonText": "Download",
     "enabled": true
   }
   ```
3. Save the file. When refreshed, the page will automatically create and display the new card without requiring any code changes.

### How to Edit Product Details
- Modify the title, description, or category string directly in `tech/products.json`.
- Changes take effect immediately upon page reload.

### How to Replace a Thumbnail
1. Place the new image/SVG file into `public/assets/tech/` (e.g. `public/assets/tech/my-thumbnail.png`).
2. Update the `"thumbnail"` field in `tech/products.json`:
   ```json
   "thumbnail": "/assets/tech/my-thumbnail.png"
   ```
3. If a thumbnail file is missing or fails to load, `tech.js` automatically renders a graceful fallback placeholder with the category title.

### How to Configure a Download URL
- Set `"downloadUrl"` to the target external or hosted resource URL.
- Use `"buttonText"` to customize the button label. Defaults to `"Download"` if omitted.

### How to Disable or Remove a Product
- **Temporary hide**: Set `"enabled": false`. The item will remain in the JSON but will not be rendered on the website.
- **Permanent removal**: Delete the product object from the `"products"` array.

---

## 6. Limitations & Outstanding Items
1. **Production Build (`vite build`) Configuration**:
   - In development mode (`npm run dev`), the `/tech` route is served automatically by Vite.
   - For production distribution builds (`npm run build`), Vite builds entry points defined in `rollupOptions.input` in `vite.config.js`. Adding `tech: resolve(__dirname, "tech/index.html")` will output `dist/tech/index.html`.
   - In strict compliance with instructions, `vite.config.js` has **not** been modified without prior user authorization.
2. **Placeholder URLs**: All URLs currently configured in `products.json` point to `https://example.com/*` placeholders for demonstration. Replace them with actual product URLs when live resources become available.

---

## 7. Change Log

| Date | File | Change | Reason |
|---|---|---|---|
| 2026-11-05 | `tech/products.json` | Created initial products catalog schema and sample entries | Single source of truth for JSON-driven product cards |
| 2026-11-05 | `tech/tech.css` | Created page-scoped stylesheet under `.tech-page` | Scoped visual styling |
| 2026-11-05 | `tech/tech.js` | Created JSON loader, data validator, fallback logic, live search, and card renderer | Dynamic rendering of cards from `products.json` |
| 2026-11-05 | `tech/index.html` | Created standalone entry point for `/tech` route | Serves the TechTodards page |
| 2026-11-05 | `public/assets/tech/logo.jpg` | Added official TechTodards brand logo | Header brand presentation |
| 2026-11-05 | `public/assets/tech/*.svg` | Created vector thumbnails for sample cards | High quality card visuals |
| 2026-11-05 | `assets/tech/*` | Mirrored logo and thumbnails | Fulfill project structure requirements |
| 2026-11-05 | `public/tech/products.json` | Mirrored catalog file | Runtime fetch endpoint fallback |
| 2026-11-05 | `tech/index.html` | Redesigned with modern technology site aesthetic; removed page nav links | User request to use theme in logo color palette and remove nav links |
| 2026-11-05 | `tech/tech.css` | Rebuilt theme around electric blue (`#0052ff`), dark black (`#09090b`), slate borders, and subtle tech grid | Align styling with official logo color palette |
| 2026-11-05 | `tech/tech.js` | Updated card rendering to modern tech card design; added keyboard shortcut (`/`) | Modern tech platform experience |
| 2026-11-06 | `tech/products.json` & `tech/tech.js` | Added `"type": "download" \| "link"` parameter support | Download triggers file download; link redirects to target URL |
| 2026-11-05 | `README_TECH.md` | Created comprehensive operations manual & change log | Documentation & maintenance instructions |
