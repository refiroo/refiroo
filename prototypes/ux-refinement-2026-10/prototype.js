/* Isolated design prototype. No API calls, authentication, persistence or production imports. */
"use strict";

const paths = {
  grid: '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
  layers: '<path d="m12 3 9 5-9 5-9-5 9-5Zm-9 9 9 5 9-5M3 16l9 5 9-5"/>',
  server:
    '<rect x="3" y="3" width="18" height="7" rx="2"/><rect x="3" y="14" width="18" height="7" rx="2"/><path d="M7 6.5h.01M7 17.5h.01M16 6.5h2M16 17.5h2"/>',
  search: '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
  arrow: '<path d="m9 5 7 7-7 7"/>',
  back: '<path d="m14 5-7 7 7 7M7 12h14"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  close: '<path d="m6 6 12 12M6 18 18 6"/>',
  edit: '<path d="m15 4 5 5M4 20l5-1L20 8a3.5 3.5 0 0 0-5-5L4 14v6Z"/>',
  filter: '<path d="M4 7h16M7 12h10M10 17h4"/>',
  moon: '<path d="M20.5 13A9 9 0 0 1 11 3.5 9 9 0 1 0 20.5 13Z"/>',
  menu: '<path d="M4 6h16M4 12h16M4 18h16"/>',
  branch: '<path d="M5 4v16M5 7h8M5 17h8M13 4h7v6h-7zM13 14h7v6h-7z"/>',
  expand: '<path d="M14 3h7v7M21 3l-8 8M10 21H3v-7M3 21l8-8"/>',
  check: '<path d="m5 12 4 4L19 6"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7h.01"/>',
  download: '<path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5"/>',
};
const icon = (name) =>
  `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true">${paths[name] || paths.grid}</svg>`;
const esc = (value) =>
  String(value).replace(
    /[&<>"']/g,
    (character) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        character
      ],
  );
const brand = () =>
  '<img src="assets/refiroo-mascot.png" alt=""/><img class="wordmark" src="assets/refiroo-wordmark.png" alt="refiroo"/>';
const definitions = {
  delivery: {
    name: "Delivery method",
    plural: "Delivery methods",
    description:
      "The shared meaning behind every way an order reaches a customer.",
    icon: "layers",
    ownerLabel: "Data owner",
    relationLabel: "Used by",
    group: "Customer experience",
    rows: [
      [
        "home",
        "Home delivery",
        "HOME",
        "Customer experience",
        "Deliver an order directly to the customer's address.",
        true,
        "commerce",
      ],
      [
        "collection",
        "Click & collect",
        "COLLECT",
        "Retail operations",
        "Collect an online order at a selected store.",
        true,
        "stores",
      ],
      [
        "locker",
        "Parcel locker",
        "LOCKER",
        "Customer experience",
        "Collect a parcel from a secure self-service locker.",
        true,
        "commerce",
      ],
      [
        "express",
        "Express delivery",
        "EXPRESS",
        "Logistics",
        "Priority delivery on the next working day.",
        true,
        "warehouse",
      ],
      [
        "scheduled",
        "Scheduled delivery",
        "SCHEDULED",
        "Logistics",
        "Delivery during a time window chosen by the customer.",
        true,
        "warehouse",
      ],
      [
        "international",
        "International delivery",
        "INTL",
        "Logistics",
        "Delivery to supported destinations outside the home market.",
        true,
        "warehouse",
      ],
      [
        "legacy",
        "Postal collection",
        "POSTAL",
        "Retail operations",
        "A retired collection service retained for historical records.",
        false,
        "stores",
      ],
    ],
  },
  systems: {
    name: "Business system",
    plural: "Business systems",
    description:
      "The systems that use and exchange your shared reference data.",
    icon: "server",
    ownerLabel: "System owner",
    relationLabel: "Uses",
    group: "Connected platforms",
    rows: [
      [
        "commerce",
        "Commerce platform",
        "COMMERCE",
        "Digital products",
        "The online storefront and order experience.",
        true,
        "home",
      ],
      [
        "stores",
        "Store operations",
        "STORES",
        "Retail operations",
        "Store tooling for collection and customer service.",
        true,
        "collection",
      ],
      [
        "warehouse",
        "Warehouse platform",
        "WAREHOUSE",
        "Logistics",
        "Fulfilment, dispatch and delivery coordination.",
        true,
        "express",
      ],
    ],
  },
};
const seed = Object.fromEntries(
  Object.entries(definitions).map(([key, type]) => [
    key,
    type.rows.map(([id, name, code, owner, description, active, related]) => ({
      id: `demo-${key}-${id}`,
      name,
      code,
      owner,
      description,
      active,
      related,
      version: 1,
    })),
  ]),
);
const datasets = Object.fromEntries(
  ["live", "draft", "publication"].map((key) => [key, structuredClone(seed)]),
);
const state = {
  page: "collection",
  type: "delivery",
  lens: "table",
  context: "live",
  query: "",
  activeOnly: false,
  ascending: true,
  selected: null,
  expanded: false,
  edits: [],
  lastRecord: "demo-delivery-home",
  lastType: "delivery",
};
const app = document.getElementById("app");
const dialog = document.getElementById("dialog");
let returnFocus = null;
let toastTimer;
const type = () => definitions[state.type];
const rows = () => datasets[state.context][state.type];
const record = () => rows().find((row) => row.id === state.selected);
const readonly = () => state.context === "publication";
const status = (row) =>
  `<span class="status${row.active ? "" : " inactive"}">${row.active ? "Active" : "Inactive"}</span>`;

function notify(message) {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.classList.add("visible");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove("visible"), 3500);
}

function sidebar() {
  return `<aside class="sidebar" aria-label="Workspace navigation">
    <div class="workspace-label"><span class="eyebrow">Workspace</span><strong>Everyday essentials</strong><p class="small muted">Shared reference data</p></div>
    <nav aria-label="Collections"><p class="eyebrow nav-title">Collections</p>${Object.entries(
      definitions,
    )
      .map(
        ([key, definition]) =>
          `<button class="nav-item" data-action="collection" data-type="${key}" data-kind="${key}" ${state.type === key && state.page === "collection" ? 'aria-current="page"' : ""}><span class="tile">${icon(definition.icon)}</span>${definition.plural}<span class="count">${datasets[state.context][key].length}</span></button>`,
      )
      .join("")}</nav>
    ${
      state.lens !== "hierarchy"
        ? `<details class="browse"><summary>Browse individual records</summary>${rows()
            .slice(0, 4)
            .map(
              (row) =>
                `<button class="ghost" data-action="open" data-id="${row.id}">${icon(type().icon)} ${esc(row.name)}</button>`,
            )
            .join("")}</details>`
        : ""
    }
    <div class="sidebar-foot"><strong>A little structure. A lot of clarity.</strong>One shared language for your data.</div>
  </aside>`;
}

function topbar() {
  return `<header class="topbar"><button class="icon-button ghost mobile-nav" data-action="navigation" aria-label="Open navigation">${icon("menu")}</button><button class="brand" data-action="home" aria-label="refiroo home">${brand()}</button>
    <nav class="topnav" aria-label="Main navigation"><button data-action="home" ${state.page === "home" ? 'aria-current="page"' : ""}>Home</button><button data-action="workspace" ${state.page === "collection" ? 'aria-current="page"' : ""}>${icon("layers")} Reference data</button></nav>
    <div class="top-actions"><button class="icon-button ghost" data-action="theme" aria-label="Switch colour theme" title="Switch colour theme">${icon("moon")}</button><button class="avatar" data-action="account" aria-label="Alex Morgan account">AM</button></div></header>`;
}

function contextBand() {
  const explanation = {
    live: "Saved changes are live immediately.",
    draft: "Your edits stay here until published.",
    publication: "Read-only snapshot · 24 Oct 2026",
  }[state.context];
  return `<div class="context-band" data-context="${state.context}">${icon(state.context === "publication" ? "layers" : "check")}<label class="sr-only" for="context">Data context</label><select id="context">${[
    ["live", "Live data"],
    ["draft", "Change set · Autumn tidy-up"],
    ["publication", "Publication #12"],
  ]
    .map(
      ([value, label]) =>
        `<option value="${value}" ${value === state.context ? "selected" : ""}>${label}</option>`,
    )
    .join(
      "",
    )}</select><span class="context-explanation">${explanation}</span><button class="context-action" data-action="${state.context === "draft" ? "review" : "context-help"}">${state.context === "draft" ? `Review changes (${state.edits.filter((edit) => edit.context === "draft").length})` : "About this context"}</button></div>`;
}

function render() {
  if (state.page === "signin") {
    app.innerHTML = signIn();
    return;
  }
  app.innerHTML = `${topbar()}${state.page === "home" ? `<main class="content" id="main" tabindex="-1" style="max-width:1080px">${home()}</main>` : `<div class="shell">${sidebar()}<main class="main" id="main" tabindex="-1">${contextBand()}<div class="content">${collection()}</div></main></div>`}`;
  if (state.page === "collection" && !state.expanded) updateResults();
}

function home() {
  const previous = datasets.live[state.lastType].find(
    (row) => row.id === state.lastRecord,
  );
  return `<div class="home-intro"><img src="assets/refiroo-mascot.png" alt=""/><div><span class="eyebrow">Your workspace, ready when you are</span><h1>Welcome back, Alex.</h1><p>A few good connections keep everything in step.</p></div></div>
    <button class="continue-card" data-action="continue"><span class="tile">${icon("back")}</span><span><span class="eyebrow">Continue where you left off</span><strong>${esc(previous?.name || "Delivery methods")}</strong><span class="small muted">Everyday essentials / ${definitions[state.lastType].plural}</span></span>${icon("arrow")}</button>
    <h2>Your workspace</h2><p class="muted small" style="margin-top:5px">One place for the definitions your teams share.</p><div class="workspace-cards">${Object.entries(
      definitions,
    )
      .map(
        ([key, definition]) =>
          `<section class="surface workspace-card" data-kind="${key}"><span class="tile">${icon(definition.icon)}</span><h2>${definition.plural}</h2><p>${definition.description}</p><button data-action="collection" data-type="${key}">Browse ${definition.plural.toLowerCase()} ${icon("arrow")}</button></section>`,
      )
      .join("")}</div>`;
}

function collection() {
  const row = record();
  if (row && state.expanded)
    return `<div class="record-page"><button class="ghost back" data-action="collapse">${icon("back")} Back to ${type().plural.toLowerCase()}</button>${inspector(row)}</div>`;
  return `<div class="page-heading"><div><p class="eyebrow">Everyday essentials / Reference data</p><h1>${type().plural}</h1><p>${type().description}</p></div><div class="heading-actions">${!readonly() ? `<button class="primary" data-action="new" aria-label="Add ${type().name.toLowerCase()}">${icon("plus")}<span class="add-label"> Add ${type().name.toLowerCase()}</span><span class="mobile-add-label" aria-hidden="true">Add</span></button>` : ""}</div></div>
    <div class="collection-layout${row ? " has-inspector" : ""}"><section class="collection-primary" aria-label="${type().plural}"><div class="view-tabs" role="tablist" aria-label="Collection view"><button id="table-tab" role="tab" aria-controls="view-panel" aria-selected="${state.lens === "table"}" data-action="lens" data-lens="table">${icon("grid")} Table</button><button id="hierarchy-tab" role="tab" aria-controls="view-panel" aria-selected="${state.lens === "hierarchy"}" data-action="lens" data-lens="hierarchy">${icon("branch")} Hierarchy</button></div>
    <div class="surface" id="view-panel" role="tabpanel" aria-labelledby="${state.lens}-tab"><div class="toolbar"><label class="search">${icon("search")}<span class="sr-only">Search ${type().plural.toLowerCase()}</span><input id="search" type="search" placeholder="Search ${type().plural.toLowerCase()}…" value="${esc(state.query)}"/></label><button class="filter${state.activeOnly ? " active" : ""}" data-action="filter" aria-pressed="${state.activeOnly}">${icon("filter")} ${state.activeOnly ? "Active only" : "Status"}</button><button class="icon-button ghost" data-action="export" aria-label="Export sample CSV" title="Export sample CSV">${icon("download")}</button></div><div id="results"></div></div><p class="hint">${icon("info")} Open a record to see its details${readonly() ? ". This snapshot is read-only." : " and edit a field in place."}</p></section>${row ? inspector(row) : ""}</div>`;
}

function matchingRows() {
  return rows()
    .filter(
      (row) =>
        (!state.activeOnly || row.active) &&
        `${row.name} ${row.code} ${row.owner}`
          .toLowerCase()
          .includes(state.query.toLowerCase()),
    )
    .sort((a, b) => a.name.localeCompare(b.name) * (state.ascending ? 1 : -1));
}

function updateResults() {
  const results = document.getElementById("results");
  if (!results) return;
  const found = matchingRows();
  if (!found.length) {
    results.innerHTML = `<div class="empty"><h3>No matching records</h3><p class="muted small">Try a different name or code, or clear your filters.</p><button data-action="clear">Clear search and filters</button></div>`;
    return;
  }
  const contents =
    state.lens === "hierarchy"
      ? `<p class="tree-heading">${icon("branch")} ${type().group}</p>${found.map((row) => `<div class="tree-row child">${icon(type().icon)}<button class="button-link" data-action="open" data-id="${row.id}">${esc(row.name)}</button>${status(row)}</div>`).join("")}`
      : `<div class="table-scroll"><table aria-label="${type().plural}"><thead><tr><th scope="col" aria-sort="${state.ascending ? "ascending" : "descending"}"><button data-action="sort">Name <span aria-hidden="true">${state.ascending ? "↑" : "↓"}</span></button></th><th scope="col">Code</th><th scope="col" class="owner-column">${type().ownerLabel}</th><th scope="col">Status</th></tr></thead><tbody>${found.map((row) => `<tr${state.selected === row.id ? ' class="selected"' : ""}><td><button class="button-link record-name" data-action="open" data-id="${row.id}" ${state.selected === row.id ? 'aria-current="true"' : ""}>${esc(row.name)}${icon("arrow")}</button></td><td class="code">${esc(row.code)}</td><td class="muted owner-column">${esc(row.owner)}</td><td>${status(row)}</td></tr>`).join("")}</tbody></table></div><div class="mobile-list">${found.map((row) => `<button class="mobile-record" data-action="open" data-id="${row.id}"><span><span class="record-name">${esc(row.name)}</span><span class="mobile-record-meta"><span class="code">${esc(row.code)}</span>${status(row)}</span></span>${icon("arrow")}</button>`).join("")}</div>`;
  results.innerHTML = `${contents}<div class="table-foot"><span>${found.length} of ${rows().length} records</span><span class="footer-hint">${icon("check")} ${readonly() ? "Snapshot" : "All changes saved"}</span></div>`;
}

function inspector(row) {
  const otherType = Object.keys(definitions).find((key) => key !== state.type);
  const related = datasets[state.context][otherType].find(
    (item) => item.id === `demo-${otherType}-${row.related}`,
  );
  const fields = [
    ["code", "Code"],
    ["owner", type().ownerLabel],
    ["description", "Description"],
    ["active", "Status"],
  ];
  const latest = state.edits
    .filter((edit) => edit.id === row.id && edit.context === state.context)
    .at(-1);
  return `<aside class="inspector" aria-label="Record details" data-kind="${state.type}"><div class="inspector-tools"><span>Record details</span><div><button class="icon-button ghost" data-action="expand" aria-label="Expand to full page" title="Expand to full page">${icon("expand")}</button><button class="icon-button ghost" data-action="close-record" aria-label="Close record details">${icon("close")}</button></div></div>
    <div class="record-intro"><span class="tile">${icon(type().icon)}</span><h2>${esc(row.name)}</h2><p>${type().name} · Everyday essentials</p>${status(row)}</div>
    <section class="record-section"><h3 class="eyebrow">Details</h3>${fields.map(([key, label]) => `<div class="field"><span>${label}</span>${readonly() ? `<span class="readonly-value">${esc(key === "active" ? (row.active ? "Active" : "Inactive") : row[key])}</span>` : `<button data-action="edit" data-field="${key}" aria-label="Edit ${label.toLowerCase()}"><span>${esc(key === "active" ? (row.active ? "Active" : "Inactive") : row[key])}</span>${icon("edit")}</button>`}</div>`).join("")}${!readonly() ? '<button class="button-link small" style="margin-top:12px" data-action="edit" data-field="name">Rename record</button>' : ""}</section>
    ${related ? `<section class="record-section"><h3 class="eyebrow">${type().relationLabel}</h3><button class="relation-link" data-action="related" data-type="${otherType}" data-id="${related.id}">${esc(related.name)}${icon("arrow")}</button><p class="relation-label">${definitions[otherType].name}</p></section>` : ""}
    <section class="record-section"><h3 class="eyebrow">Recent activity</h3><div class="history-entry"><strong>${latest ? esc(latest.label) : "Record reviewed"}</strong><p>${latest ? "Alex Morgan · Just now · Sample activity" : "Alex Morgan · 24 Oct 2026 · Sample activity"}</p></div></section>
    <details class="technical"><summary>Technical details</summary><dl><dt>ID</dt><dd class="code">${row.id}</dd><dt>Version</dt><dd>${row.version}</dd></dl><button class="button-link small" style="margin-top:12px" data-action="copy-id">Copy record ID</button></details></aside>`;
}

function showDialog(content, drawer = false) {
  returnFocus = document.activeElement;
  dialog.className = drawer ? "drawer" : "";
  dialog.innerHTML = content;
  dialog.showModal();
}
function closeDialog(selector) {
  dialog.close();
  if (selector) document.querySelector(selector)?.focus();
  else if (returnFocus?.isConnected) returnFocus.focus();
}
const dialogHead = (title, eyebrow = "") =>
  `<div class="dialog-head"><div>${eyebrow ? `<p class="eyebrow">${eyebrow}</p>` : ""}<h2 id="dialog-title">${title}</h2></div><button class="icon-button ghost" data-action="dismiss" aria-label="Close dialog">${icon("close")}</button></div>`;

function editField(field) {
  const row = record();
  if (!row || readonly()) return;
  const labels = {
    code: "Code",
    owner: type().ownerLabel,
    description: "Description",
    active: "Status",
    name: "Name",
  };
  const control =
    field === "active"
      ? `<select name="value" id="edit-value"><option value="true"${row.active ? " selected" : ""}>Active</option><option value="false"${!row.active ? " selected" : ""}>Inactive</option></select>`
      : field === "description"
        ? `<textarea name="value" id="edit-value">${esc(row[field])}</textarea>`
        : `<input name="value" id="edit-value" value="${esc(row[field])}" required maxlength="120"/>`;
  showDialog(
    `${dialogHead(`Edit ${labels[field].toLowerCase()}`, row.name)}<form data-form="edit" data-field="${field}"><div class="form-field"><label for="edit-value">${labels[field]}</label>${control}</div><p class="small muted">${state.context === "draft" ? "Saved in Autumn tidy-up. Live data stays unchanged." : "Saved to the sample live data in this tab."}</p><p class="dialog-error" role="alert" id="form-error"></p><div class="dialog-actions"><button type="button" data-action="dismiss">Cancel</button><button class="primary" type="submit">Save change</button></div></form>`,
  );
  document.getElementById("edit-value").focus();
}

function signIn() {
  return `<main id="main" class="signin"><div class="signin-wrap"><button class="brand" data-action="home" aria-label="Back to prototype home">${brand()}</button><section class="surface signin-card"><h1>Good to see you.</h1><p>Sign in to your refiroo workspace.</p><form data-form="signin"><label class="form-field">Username<input name="username" autocomplete="off" placeholder="alex.morgan" required/></label><label class="form-field" for="password">Password</label><div class="password-wrap"><input id="password" name="password" type="password" autocomplete="off" placeholder="Use any sample password" required/><button type="button" data-action="password" aria-controls="password" aria-pressed="false">Show</button></div><p class="small muted" style="margin-top:12px">Use made-up details. This preview does not authenticate.</p><button class="primary" type="submit">Open sample workspace ${icon("arrow")}</button></form><button class="button-link small" data-action="reset-password">Forgot your password?</button></section><p class="signin-note">A little structure. A lot of clarity.</p></div></main>`;
}

function changeCollection(key) {
  Object.assign(state, {
    type: key,
    page: "collection",
    query: "",
    selected: null,
    expanded: false,
    activeOnly: false,
  });
  if (dialog.open) closeDialog();
  render();
}

document.addEventListener("input", (event) => {
  if (event.target.id === "search") {
    state.query = event.target.value;
    updateResults();
  }
});
document.addEventListener("change", (event) => {
  if (event.target.id === "context") {
    state.context = event.target.value;
    render();
    document.getElementById("context").focus();
    notify(
      {
        live: "Viewing sample live data",
        draft: "Autumn tidy-up · edits stay in this change set",
        publication: "Publication #12 · read-only sample snapshot",
      }[state.context],
    );
  }
});

document.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-action]");
  if (!button) return;
  const action = button.dataset.action;
  if (action === "dismiss") return closeDialog();
  if (action === "home") {
    state.page = "home";
    render();
  }
  if (action === "workspace") {
    state.page = "collection";
    state.expanded = false;
    render();
  }
  if (action === "collection") changeCollection(button.dataset.type);
  if (action === "open") {
    if (dialog.open) closeDialog();
    state.page = "collection";
    state.selected = button.dataset.id;
    state.lastRecord = state.selected;
    state.lastType = state.type;
    render();
    const heading = document.querySelector(".record-intro h2");
    heading?.setAttribute("tabindex", "-1");
    heading?.focus();
  }
  if (action === "related") {
    changeCollection(button.dataset.type);
    state.selected = button.dataset.id;
    state.lastRecord = state.selected;
    state.lastType = state.type;
    render();
    document.querySelector(".record-intro h2")?.setAttribute("tabindex", "-1");
    document.querySelector(".record-intro h2")?.focus();
  }
  if (action === "continue") {
    changeCollection(state.lastType);
    state.selected = state.lastRecord;
    render();
  }
  if (action === "close-record" || action === "collapse") {
    const previous = state.selected;
    state.selected = null;
    state.expanded = false;
    render();
    Array.from(document.querySelectorAll('[data-action="open"]'))
      .find(
        (item) => item.dataset.id === previous && item.getClientRects().length,
      )
      ?.focus();
  }
  if (action === "expand") {
    state.expanded = true;
    render();
  }
  if (action === "theme") {
    document.documentElement.dataset.theme =
      document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    notify(
      `${document.documentElement.dataset.theme === "dark" ? "Dark" : "Light"} appearance`,
    );
  }
  if (action === "filter") {
    state.activeOnly = !state.activeOnly;
    render();
    document.querySelector('[data-action="filter"]').focus();
  }
  if (action === "clear") {
    state.query = "";
    state.activeOnly = false;
    render();
    document.getElementById("search").focus();
  }
  if (action === "sort") {
    state.ascending = !state.ascending;
    updateResults();
    document.querySelector('[data-action="sort"]').focus();
  }
  if (action === "lens") {
    state.lens = button.dataset.lens;
    render();
    document.querySelector(`[data-lens="${state.lens}"]`).focus();
  }
  if (action === "navigation")
    showDialog(`${dialogHead("Browse workspace")}${sidebar()}`, true);
  if (action === "edit") editField(button.dataset.field);
  if (action === "new" && !readonly()) {
    showDialog(
      `${dialogHead(`Add ${type().name.toLowerCase()}`, "A new shared definition")}<form data-form="new"><label class="form-field">Name<input name="name" required maxlength="120" autofocus/></label><label class="form-field">Code<input name="code" required maxlength="40"/></label><label class="form-field">${type().ownerLabel}<input name="owner" required maxlength="120"/></label><p class="small muted">Added to ${state.context === "draft" ? "your sample change set" : "the sample live data"}. It resets when you reload.</p><p class="dialog-error" role="alert" id="form-error"></p><div class="dialog-actions"><button type="button" data-action="dismiss">Cancel</button><button class="primary" type="submit">Add record</button></div></form>`,
    );
  }
  if (action === "context-help") {
    showDialog(
      `${dialogHead("Know where your changes go", "Data context")}<p class="dialog-description"><strong>Live data</strong> is your everyday working data. Saved edits apply immediately.</p><p class="dialog-description"><strong>A change set</strong> keeps coordinated edits separate until they are reviewed and published.</p><p class="dialog-description"><strong>A publication</strong> is a fixed, read-only snapshot.</p><p class="small muted">This prototype keeps three separate sample datasets in memory. Publishing is outside this preview.</p><div class="dialog-actions"><button class="primary" data-action="dismiss">Got it</button></div>`,
    );
  }
  if (action === "review") {
    const edits = state.edits.filter((edit) => edit.context === "draft");
    showDialog(
      `${dialogHead("Autumn tidy-up", "Change-set review")}<p class="dialog-description">${edits.length ? `${edits.length} sample edit${edits.length === 1 ? "" : "s"}. Live data is unchanged.` : "No changes yet. Open a record and edit a field to try it."}</p>${edits.map((edit) => `<p class="small" style="padding:8px 0;border-bottom:1px solid var(--border)">${esc(edit.record)} · ${esc(edit.label)}</p>`).join("")}<div class="dialog-actions"><button class="primary" data-action="dismiss">Continue editing</button></div>`,
    );
  }
  if (action === "account")
    showDialog(
      `${dialogHead("Alex Morgan", "Sample account")}<p class="dialog-description">Data steward · Everyday essentials</p><button data-action="signin">Preview sign-in ${icon("arrow")}</button><div class="dialog-actions"><button data-action="dismiss">Close</button></div>`,
    );
  if (action === "signin") {
    closeDialog();
    state.page = "signin";
    render();
  }
  if (action === "password") {
    const password = document.getElementById("password");
    password.type = password.type === "password" ? "text" : "password";
    button.textContent = password.type === "password" ? "Show" : "Hide";
    button.setAttribute("aria-pressed", String(password.type === "text"));
  }
  if (action === "reset-password")
    showDialog(
      `${dialogHead("Get back to your workspace")}<p class="dialog-description">Enter your username or email address. If an account matches, we'll send a reset link.</p><form data-form="reset"><label class="form-field">Username or email<input name="identity" required/></label><p class="small muted">Preview only. No message will be sent.</p><div class="dialog-actions"><button type="button" data-action="dismiss">Cancel</button><button class="primary">Preview request</button></div></form>`,
    );
  if (action === "copy-id") {
    try {
      await navigator.clipboard.writeText(record().id);
      notify("Sample record ID copied");
    } catch {
      notify("Copy the ID from the technical details above.");
    }
  }
  if (action === "export") {
    const csvCell = (value) => `"${String(value).replace(/"/g, '""')}"`;
    const csv = [
      ["Name", "Code", "Owner", "Active"],
      ...matchingRows().map((row) => [
        row.name,
        row.code,
        row.owner,
        row.active,
      ]),
    ]
      .map((line) => line.map(csvCell).join(","))
      .join("\r\n");
    const url = URL.createObjectURL(
      new Blob([csv], { type: "text/csv;charset=utf-8" }),
    );
    const link = document.createElement("a");
    link.href = url;
    link.download = `refiroo-sample-${state.type}.csv`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    notify("Sample CSV exported with the current search and filter");
  }
});

document.addEventListener("submit", (event) => {
  const form = event.target;
  if (!form.dataset.form) return;
  event.preventDefault();
  const data = new FormData(form);
  if (form.dataset.form === "signin") {
    form.reset();
    state.page = "home";
    render();
    notify("Welcome to your sample workspace");
    return;
  }
  if (form.dataset.form === "reset") {
    closeDialog();
    notify(
      "Preview complete. If an account matched, a reset link would be sent.",
    );
    return;
  }
  if (readonly()) return;
  if (form.dataset.form === "edit") {
    const row = record();
    const field = form.dataset.field;
    const value =
      field === "active"
        ? data.get("value") === "true"
        : String(data.get("value")).trim();
    if (field !== "description" && value === "") {
      document.getElementById("form-error").textContent =
        "Enter a value before saving.";
      return;
    }
    if (
      field === "code" &&
      rows().some(
        (other) =>
          other.id !== row.id &&
          other.code.toLowerCase() === value.toLowerCase(),
      )
    ) {
      document.getElementById("form-error").textContent =
        "This code is already used. Choose a different code.";
      return;
    }
    row[field] = value;
    row.version += 1;
    state.edits.push({
      context: state.context,
      id: row.id,
      record: row.name,
      label: `${field === "active" ? "Status" : field.charAt(0).toUpperCase() + field.slice(1)} updated`,
    });
    render();
    closeDialog(`[data-action="edit"][data-field="${field}"]`);
    notify(
      state.context === "draft"
        ? "Saved in Autumn tidy-up · live data unchanged"
        : "Change saved to sample live data",
    );
  }
  if (form.dataset.form === "new") {
    const name = String(data.get("name")).trim();
    const code = String(data.get("code")).trim();
    const owner = String(data.get("owner")).trim();
    if (!name || !code || !owner) {
      document.getElementById("form-error").textContent =
        "Complete all three fields before adding the record.";
      return;
    }
    if (rows().some((row) => row.code.toLowerCase() === code.toLowerCase())) {
      document.getElementById("form-error").textContent =
        "This code is already used. Choose a different code.";
      return;
    }
    const row = {
      id: `demo-${state.type}-${Date.now()}`,
      name,
      code,
      owner,
      description: "",
      active: true,
      version: 1,
      related: null,
    };
    rows().push(row);
    state.edits.push({
      context: state.context,
      id: row.id,
      record: name,
      label: "Record added",
    });
    state.selected = row.id;
    state.query = "";
    render();
    closeDialog('[data-action="close-record"]');
    notify(`${type().name} added to the sample data`);
  }
});

// Native dialog supplies focus containment and Escape; it restores focus for an unmodified opener.
dialog.addEventListener("close", () => {
  if (returnFocus?.isConnected) returnFocus.focus();
});
document.addEventListener("keydown", (event) => {
  if (
    event.target.matches('[role="tab"]') &&
    ["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)
  ) {
    event.preventDefault();
    state.lens =
      event.key === "Home"
        ? "table"
        : event.key === "End"
          ? "hierarchy"
          : state.lens === "table"
            ? "hierarchy"
            : "table";
    render();
    document.querySelector(`[data-lens="${state.lens}"]`).focus();
  }
  if (
    event.key === "Escape" &&
    !dialog.open &&
    state.selected &&
    !event.target.matches("input,textarea,select")
  )
    document
      .querySelector('[data-action="close-record"], [data-action="collapse"]')
      ?.click();
});
render();
