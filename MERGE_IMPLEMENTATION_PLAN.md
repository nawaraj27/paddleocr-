# Mero Dokan — Storefront + Gemini Workspace Merge: Implementation Plan

> **Scope of this document:** architecture & step-by-step plan only — no production
> code yet. It builds on the *existing* Django project (`apps/core, users, uploads,
> processing, analytics`) and the already-built DataFast landing page.
>
> **Correction honored:** the project does **not** use PaddleOCR. All intelligence
> comes from the **Gemini API** (`apps/processing/gemini.py`, `schema.py`, parsing
> prompts, analytics). Nothing in that path is removed or weakened — it is *extended*.

---

## 0. Guiding principles (enterprise practices applied throughout)

1. **Reuse before rebuild.** The landing page, auth/RBAC, upload pipeline, Gemini
   service and analytics already exist. We add four new apps and *wire into* the
   existing extraction flow rather than duplicating it.
2. **Single source of truth / zero redundancy.** Each fact lives in exactly one
   table. Raw OCR output is an immutable audit snapshot; operational records
   (stock, sales, purchases) are derived from it through an explicit, reviewed
   mapping — never copied blindly.
3. **Multi-tenant by default.** Every operational row is scoped to a `Store`
   (Dokan). Cross-tenant access is impossible by construction (querysets always
   filter on the active store).
4. **Append-only audit for anything that moves money or stock.** Stock balances
   are a *cached projection* of an immutable `StockMovement` ledger, so every
   change is traceable to a transaction and a document.
5. **Human-in-the-loop for destructive writes.** Gemini suggestions never
   auto-mutate inventory silently; a user confirms the mapping. This is both an
   accuracy and a liability safeguard.
6. **Idempotency & atomicity.** Posting a scanned document to the ledger is wrapped
   in a DB transaction and guarded by the source document id, so a double-click or
   retry can never double-post stock.

---

## 1. Combined relational data model (normalized)

New Django apps: **`stores`**, **`cms`**, **`inventory`**, **`ledger`**.
Existing apps keep their models; `processing.ExtractedDocument` becomes the OCR
audit anchor.

### 1.1 Tenancy & identity (extends existing `users`)

- **`User`** *(exists)* — keep custom user, roles (admin/manager/analyst/viewer),
  approval gate. No change to fields.
- **`stores.Store` (Dokan)** — `owner = FK(User)`, `name`, `slug`, `currency`,
  `address`, `phone`, `logo`, `is_active`, timestamps.
  - **Cardinality decision:** **User 1 : M Store** (`owner` FK), *not* 1:1. A user
    can run more than one dokan, and this superset trivially supports the 1:1 case.
- **`stores.StoreMembership`** — `store FK`, `user FK`, `role` (owner/manager/staff/
  viewer), `is_active`, `unique_together(store, user)`. Enables multiple staff per
  dokan with per-store RBAC (the existing global `User.role` governs platform-level
  admin; `StoreMembership.role` governs in-store permissions).

### 1.2 Dynamic landing content — `cms` (admin-driven, public read)

All landing variables move out of templates into the DB, editable from Django admin:

- **`cms.SiteSettings`** *(singleton)* — `brand_name`, `logo`, `hero_headline`,
  `hero_highlight`, `hero_subheadline`, `social_proof_count`, `primary_cta_label`,
  `primary_cta_href`, default theme.
- **`cms.FeatureBlock`** — `title`, `body`, `image`, `order`, `layout`
  (LEFT/RIGHT → powers the **alternating split grid**), `is_published`.
- **`cms.Screenshot`** — `image`, `caption`, `chrome` (BROWSER/PHONE/WINDOWS →
  device-chrome wrapper), `order`, `is_published`.
- **`cms.PlatformDownload`** — `platform` (iOS/Android/Web/Windows), `label`,
  `url`, `icon`, `is_active` → dynamic download buttons.
- **`cms.NavLink`** / **`cms.FooterLink`** — `label`, `href`, `group`, `order`.

> These are global marketing content (one public site), so they are **not**
> store-scoped.

### 1.3 Inventory & stock — `inventory`

- **`inventory.ProductCategory`** — `store FK`, `name`, `unique_together(store,
  name)`. (Store-scoped to keep tenants isolated; the existing global
  `core.Category` stays only for document tagging and is *not* reused here, to
  avoid cross-tenant name collisions.)
- **`inventory.Product`** — `store FK`, `sku`, `name`, `category FK`, `unit`
  (pcs/kg/…), `cost_price`, `sale_price`, `reorder_level`, `quantity_on_hand`
  *(cached projection)*, `is_active`. `unique_together(store, sku)`.
- **`inventory.StockMovement`** *(append-only, source of truth for stock)* —
  `store FK`, `product FK`, `delta` (signed), `reason` (PURCHASE/SALE/ADJUSTMENT/
  RETURN), `transaction_line FK (null)`, `created_by`, `created_at`.
  - `Product.quantity_on_hand` is recomputed (`F()` increment) inside the same
    atomic block that writes the movement → balance and ledger never diverge.

### 1.4 Sales & purchases — `ledger`

A **single unified transaction model** (DRY) instead of separate Sale/Purchase
tables:

- **`ledger.Party`** — `store FK`, `name`, `kind` (CUSTOMER/VENDOR), `phone`,
  `notes`. Optional but normalizes repeat customers/vendors.
- **`ledger.Transaction`** — `store FK`, `kind` (SALE/PURCHASE/ESTIMATE),
  `number`, `party FK (null)`, `date`, `subtotal`, `tax`, `total`, `status`
  (DRAFT/CONFIRMED/VOID), `created_by`, `source_document = FK(processing.
  ExtractedDocument, null)`, timestamps. `unique_together(store, kind, number)`.
- **`ledger.TransactionLine`** — `transaction FK`, `product FK (null until
  mapped)`, `description`, `quantity`, `unit_price`, `amount`. **This is the
  canonical structured line.** On confirm, each line emits one `StockMovement`
  (+ for PURCHASE, − for SALE; ESTIMATE emits none until converted).

### 1.5 OCR scan audit & log (binds Gemini output to a transactional row)

- **`processing.ExtractedDocument`** *(exists)* — remains the immutable OCR record:
  `raw_json`, `confidence`, `model_version`, denormalized header fields. **No data
  loss.**
- **`ledger.DocumentMapping`** *(new audit table)* — `document = OneToOne(Extracted
  Document)`, `store FK`, `transaction FK (null)`, `detected_kind`, `status`
  (PENDING/MAPPED/REJECTED), `mapped_by`, `mapped_at`, `field_map JSON`,
  `notes`. This is the explicit, queryable link demanded in the brief: *Gemini
  text output → the specific Sale/Purchase/Inventory rows it produced.*

### 1.6 Redundancy resolution (the "zero redundancy" decisions)

| Concern | Existing | Decision |
|---|---|---|
| Raw OCR line items | `processing.InvoiceItem` | Repurpose as a **read-only staging buffer** populated from `raw_json`; the **canonical** operational line is `ledger.TransactionLine`. Analytics repoints to `TransactionLine`/`StockMovement`. No duplicated business truth. |
| Stock balance | — | Never stored as an independent editable number. `quantity_on_hand` is a cached sum of `StockMovement`; the movement ledger is authoritative. |
| Categories | `core.Category` (global) | Keep for *document tagging only*. Inventory uses store-scoped `inventory.ProductCategory`. |
| Document ↔ transaction link | — | Exactly one `DocumentMapping` row per document; `Transaction.source_document` is the inverse pointer. |

### 1.7 ER summary (text)

```
User 1─M Store 1─M StoreMembership M─1 User
Store 1─M ProductCategory 1─M Product 1─M StockMovement
Store 1─M Party
Store 1─M Transaction 1─M TransactionLine 1─0..1 StockMovement
ExtractedDocument 1─1 DocumentMapping 0..1─1 Transaction
(CMS tables are global, public-read)
```

### 1.8 Indexes & constraints

- Tenant filters: index `(store, ...)` on every operational query path
  (`Product(store, sku)`, `Transaction(store, kind, date)`, `StockMovement(store,
  product, created_at)`).
- Uniqueness: `(store, sku)`, `(store, kind, number)`, `(store, name)` for
  categories/parties.
- Money fields: `DecimalField(max_digits=14, decimal_places=2)` everywhere (no
  floats), matching existing `ExtractedDocument`.

---

## 2. Middleware & authentication logic (protecting the workspace)

### 2.1 Route zones

| Zone | Paths | Access |
|---|---|---|
| **Public** | `/` (landing), `/auth/login`, `/auth/register`, static, public CMS API | anyone |
| **Auth** | login/register/JWT issue | anonymous only |
| **Protected workspace** | `/app/*`, `/uploads/*`, `/processing/*`, `/analytics/*`, all `/api/*` except public content | authenticated **+ approved + store member** |

### 2.2 Layered enforcement (defence in depth — reuse + extend existing pieces)

1. **`LoginRequiredMiddleware`** — redirects anonymous users hitting any non-public
   prefix to `/auth/login`. (Existing views already use `LoginRequiredMixin`; the
   middleware makes the guarantee global so no new view can leak.)
2. **`ApprovalRequiredMiddleware`** — blocks authenticated-but-unapproved users
   (`User.is_approved == False`) from the workspace, sending them to a "pending
   approval" page. Reuses the existing approval gate.
3. **`StoreContextMiddleware`** — resolves the **active store** (from session
   selection / URL slug) and verifies an active `StoreMembership`. Attaches
   `request.store`. Any workspace queryset filters on `request.store`, so a user
   can never read another tenant's data even by ID tampering.
4. **DRF permission classes** — extend the current `IsApproved`, `CanUpload`:
   add **`IsStoreMember`** and **`HasStoreRole(...)`**. Every API viewset gets
   `permission_classes = [IsAuthenticated, IsApproved, IsStoreMember]`.

### 2.3 Existing security kept

CSRF, secure session cookies, JWT (SimpleJWT) for API, upload rate-limiting, file
magic-byte validation, prompt-injection-resistant Gemini input, and `AuditLog`
remain in force. New admin/mapping actions also write `AuditLog` entries.

### 2.4 Pseudocode (StoreContextMiddleware)

```
def __call__(self, request):
    if is_public(request.path):
        return self.get_response(request)
    if not request.user.is_authenticated:
        return redirect("users:login")
    if not request.user.is_approved:
        return redirect("users:pending")
    store = resolve_store(request)          # session id or /app/<slug>/
    if store is None or not StoreMembership.objects.filter(
            store=store, user=request.user, is_active=True).exists():
        return HttpResponseForbidden()
    request.store = store
    return self.get_response(request)
```

---

## 3. Gemini → Sales / Purchase / Inventory mapping (technical spec)

### 3.1 Extend the extraction schema (keep current Gemini setup)

Augment `apps/processing/schema.py` so the *same* Gemini call also returns a
classification — no extra tokens beyond a few output fields, prompt stays compact:

```jsonc
{
  "doc_type": "SALE | PURCHASE | ESTIMATE",   // new classifier
  "party_name": "string",
  "date": "YYYY-MM-DD",
  "currency": "string",
  "lines": [{ "name": "...", "quantity": 0, "unit_price": 0, "amount": 0 }],
  "subtotal": 0, "tax": 0, "total": 0,
  "confidence": 0.0
}
```

Strict-JSON enforcement, `response_mime_type=application/json`, defensive parsing
and validation already exist and are retained.

### 3.2 Pipeline (extends the current upload→extract flow)

```
Upload (existing) ─► Gemini extract (existing) ─► ExtractedDocument.raw_json
   ─► classify doc_type ─► create DocumentMapping(status=PENDING)
   ─► "Review & Map" screen  ◄── human-in-the-loop
   ─► on Confirm: atomic post to ledger + inventory ─► DocumentMapping(MAPPED)
```

### 3.3 Product resolution (avoid duplicate SKUs)

For each extracted line, within `request.store`:
1. Exact SKU/name match → propose existing `Product`.
2. Fuzzy name match (trigram/`icontains`) above threshold → propose with a
   "confirm match?" prompt.
3. No match → propose **create new Product** (user sets SKU, category, prices).
The user confirms each mapping before anything is written.

### 3.4 Posting rules (atomic, idempotent)

On **Confirm** (single DB transaction):
- Create `Transaction(kind = doc_type, source_document = document, status =
  CONFIRMED)` and its `TransactionLine`s (linked to resolved Products).
- For each line emit a `StockMovement`:
  - **PURCHASE / ESTIMATE→converted:** `delta = +quantity` (stock up; cost price
    optionally updated).
  - **SALE:** `delta = −quantity` (stock down). If it would drive stock negative,
    block or warn per a store setting (`allow_negative_stock`).
  - **ESTIMATE:** recorded as DRAFT, **no** stock movement until converted to a
    real purchase/sale.
- Update `Product.quantity_on_hand` via `F()` in the same block.
- Set `DocumentMapping.status = MAPPED`, write `AuditLog`.
- **Idempotency:** `DocumentMapping.document` is OneToOne and checked first — a
  retry/double-submit finds it already MAPPED and is a no-op.

### 3.5 Confidence & review gates

- `confidence < threshold` or missing required fields → mapping stays PENDING and
  is flagged for manual completion (never auto-posted).
- Low-confidence numeric fields highlighted in the review UI for correction before
  posting.

### 3.6 Failure handling

Any exception rolls back the whole atomic block; `DocumentMapping` stays PENDING
with an error note; `ProcessingLog`/`AuditLog` capture the failure. No partial
stock writes are possible.

---

## 4. Public → authenticated integration blueprint

### 4.1 Public landing (data-driven from `cms`)

Rebuild the existing landing sections to read from the DB:
Navbar (`NavLink` + `SiteSettings`), Hero (`SiteSettings`), Features
(`FeatureBlock` alternating split grid), App Screenshots (`Screenshot` in
browser/phone chrome), Download buttons (`PlatformDownload`), Footer
(`FooterLink`). A public, cached, read-only `/api/content/` endpoint (or direct
context) serves them. Editing happens entirely in Django admin.

### 4.2 Authenticated workspace

After login → approved → store selected, land on `/app/` (consolidated workspace).
Sidebar: **Overview, Scan & Upload, Review/Map queue, Inventory, Sales, Purchases,
Parties, Analytics, Store settings, Users (admin)**. All views store-scoped via
`request.store`.

### 4.3 The Gemini loop in the UI

"Scan & Upload" reuses the existing drag-drop uploader → extraction → a **Review &
Map** card showing the detected `doc_type`, parsed lines, product-match
suggestions, and **Confirm** (post to ledger/inventory) **or** Download JSON/Save
as draft — matching the save-vs-download behavior already added to the data viewer.

---

## 5. Theming (Tailwind, Light/Dark via CSS variables)

- Define the supplied palettes as CSS variables on `:root` (light) and `.dark`
  (dark); configure `tailwind.config` `theme.extend.colors` to reference
  `rgb(var(--…))` tokens so utilities like `bg-card-lime`, `text-muted`,
  `border-input-border` map to the brand.
- `darkMode: 'class'`; a toggle flips `.dark` on `<html>` and persists the choice.
- The current `datafast.css` already encodes these exact variables — we either
  (a) keep the CSS-variable system and add Tailwind on top, or (b) migrate the
  classes to Tailwind utilities. **Recommendation:** keep the variables as the
  single color source of truth and let Tailwind consume them, so light/dark stays
  one definition.

| Token | Light | Dark |
|---|---|---|
| bg | #FFFFFF | #14171a |
| text | #1A1A1A | #ECEFE9 |
| text2 | #4A4A4A | #B6BDB0 |
| muted | #6B6B6B | #8C948A |
| nav | #2D2D2D | #D7DCD2 |
| input-bg | #F7F5F2 | #1d2128 |
| input-border | #E8E5E0 | #2a2f37 |
| chrome | #F5F3EF | #1a1e24 |
| card-lime | #E8EAB4 | #2b3320 |
| card-green | #D4E4B4 | #27331f |
| btn | #3D4A3A | (shared) |
| chart-light/med/line | #C8D9A8 / #A8C898 / #2D4A2D | (shared) |
| logo / hl / demo | #E07830 / #D4E4B4 / #5A6A4A | (shared) |

---

## 6. Phased delivery roadmap

- **Phase 1 — CMS + dynamic landing.** `cms` app, admin, seed data, repoint landing
  templates. (Public, low risk, immediately visible.)
- **Phase 2 — Tenancy.** `stores` app, `StoreMembership`, the three middlewares,
  `IsStoreMember` permission, store-selector UI. Backfill: create one Store per
  existing user and migrate their documents to it.
- **Phase 3 — Inventory.** `Product`, `ProductCategory`, `StockMovement`, balance
  projection, CRUD screens.
- **Phase 4 — Ledger.** `Party`, `Transaction`, `TransactionLine`, confirm→movement
  posting, sales/purchase screens; repoint analytics to the new tables.
- **Phase 5 — Gemini mapping loop.** Schema `doc_type`, `DocumentMapping`, Review &
  Map UI, atomic idempotent posting, product matching.
- **Phase 6 — Hardening.** Migrations committed, tests, exports, performance
  (indexes, cached analytics), docs.

Each phase ends with `makemigrations`/`migrate`, tests, and a working app.

---

## 7. Testing & rollout

- **Unit:** stock-projection math, posting rules (sale decrements, purchase
  increments, negative-stock guard), idempotency, tenant isolation.
- **API:** workspace endpoints reject anonymous / unapproved / non-member (403s).
- **Integration:** upload → extract (mock Gemini) → classify → confirm → ledger +
  stock updated → `DocumentMapping=MAPPED`; retry is a no-op.
- **Security:** cross-tenant ID access blocked; CSRF/JWT; prompt-injection input
  unchanged.
- Keep the offline **mock Gemini** so the whole loop runs with no API key in CI.

---

## 8. Open decisions (recommended defaults, change if you prefer)

1. **Store↔User:** 1:M with optional staff memberships — *recommended* (supports
   1:1 too).
2. **Auto-post vs review:** human-confirmed mapping — *recommended* for accuracy &
   audit (auto-post available later as an opt-in per store for high-confidence
   scans).
3. **`InvoiceItem`:** demote to raw staging, make `TransactionLine` canonical —
   *recommended* to kill redundancy. (Alternative: keep both; rejected as
   duplicative.)
4. **Tailwind adoption:** keep CSS variables as the color source, layer Tailwind —
   *recommended* over a full rewrite of `datafast.css`.
