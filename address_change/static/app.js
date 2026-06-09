/* Address Change Manager — frontend logic. Talks to the JSON API in app.py. */

let state = null;

const $ = (sel) => document.querySelector(sel);

const STATUS_LABELS = {
  todo: "To do",
  in_progress: "In progress",
  done: "Done ✓",
  na: "N/A",
};

// ---------------------------------------------------------------- api helpers
// In the standalone build (build.py inlines everything into standalone.html),
// window.MASTER_DATA is defined and state persists to localStorage instead of
// the server. Both modes share all the code below this section.
const LOCAL_KEY = "address-change-manager-v1";

function saveLocal() {
  localStorage.setItem(LOCAL_KEY, JSON.stringify(state));
}

function loadLocal() {
  const master = JSON.parse(JSON.stringify(window.MASTER_DATA));
  const raw = localStorage.getItem(LOCAL_KEY);
  if (!raw) return master;
  let saved;
  try { saved = JSON.parse(raw); } catch { return master; }
  // Merge in master items added since this browser's copy was saved.
  const known = new Set(saved.items.map((i) => i.id));
  for (const item of master.items) if (!known.has(item.id)) saved.items.push(item);
  saved.categories = master.categories;
  return saved;
}

function localApi(path, method, body) {
  // Persist on the next tick, after the caller has applied the returned
  // value to `state` (callers update state synchronously after awaiting).
  setTimeout(saveLocal, 0);

  if (path === "/api/state" && method === "GET") return loadLocal();

  if (path === "/api/move" && method === "PUT") {
    for (const key of Object.keys(state.move)) {
      if (key in body) state.move[key] = String(body[key]);
    }
    return { ...state.move };
  }

  if (path === "/api/reset" && method === "POST") {
    localStorage.removeItem(LOCAL_KEY);
    return JSON.parse(JSON.stringify(window.MASTER_DATA));
  }

  if (path === "/api/items" && method === "POST") {
    return {
      id: "custom-" + Math.random().toString(16).slice(2, 10),
      name: String(body.name || "").trim(),
      category: state.categories.includes(body.category) ? body.category : "People & other",
      when: "As soon as date is known",
      hint: String(body.hint || "").trim(),
      link: String(body.link || "").trim() || null,
      status: "todo",
      notes: "",
      custom: true,
    };
  }

  const m = path.match(/^\/api\/items\/([\w-]+)$/);
  if (m) {
    const item = state.items.find((i) => i.id === m[1]);
    if (!item) throw new Error("unknown item");
    if (method === "PATCH") {
      if ("status" in body) item.status = body.status;
      if ("notes" in body) item.notes = String(body.notes);
      return { ...item };
    }
    if (method === "DELETE") return { deleted: item.id };
  }
  throw new Error(`unsupported: ${method} ${path}`);
}

async function api(path, method = "GET", body = null) {
  if (window.MASTER_DATA) return localApi(path, method, body);
  const opts = { method, headers: {} };
  if (body !== null) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(path, opts);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || `${method} ${path} failed (${res.status})`);
  }
  return res.json();
}

function toast(msg) {
  const el = $("#toast");
  el.textContent = msg;
  el.hidden = false;
  clearTimeout(el._t);
  el._t = setTimeout(() => { el.hidden = true; }, 2500);
}

function debounce(fn, ms) {
  let t;
  return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
}

// ---------------------------------------------------------------- rendering
function visibleItems() {
  const q = $("#search").value.trim().toLowerCase();
  const filter = $("#status-filter").value;
  return state.items.filter((item) => {
    if (filter === "open" && (item.status === "done" || item.status === "na")) return false;
    if (filter !== "all" && filter !== "open" && item.status !== filter) return false;
    if (q && !(item.name + " " + (item.hint || "")).toLowerCase().includes(q)) return false;
    return true;
  });
}

function renderProgress() {
  const relevant = state.items.filter((i) => i.status !== "na");
  const done = relevant.filter((i) => i.status === "done").length;
  const pct = relevant.length ? Math.round((done / relevant.length) * 100) : 0;
  $("#progress-bar").style.width = pct + "%";
  $("#progress-label").textContent = `${done} of ${relevant.length} done (${pct}%)`;

  const cd = $("#countdown");
  if (state.move.move_date) {
    const days = Math.ceil((new Date(state.move.move_date) - new Date()) / 86400000);
    cd.hidden = false;
    if (days > 1) cd.textContent = `🗓️ ${days} days until moving day`;
    else if (days === 1) cd.textContent = "🗓️ Moving day is tomorrow!";
    else if (days === 0) cd.textContent = "🚚 Moving day is today!";
    else cd.textContent = `✅ Moved ${-days} day${days === -1 ? "" : "s"} ago`;
  } else {
    cd.hidden = true;
  }
}

function itemCard(item) {
  const div = document.createElement("div");
  div.className = `item ${item.status}`;
  div.dataset.id = item.id;

  const main = document.createElement("div");
  main.className = "item-main";

  const title = document.createElement("div");
  title.className = "item-title";
  title.textContent = item.name;
  if (item.link) {
    const a = document.createElement("a");
    a.href = item.link;
    a.target = "_blank";
    a.rel = "noopener";
    a.textContent = "Open site ↗";
    title.appendChild(a);
  }
  const when = document.createElement("span");
  when.className = "badge";
  when.textContent = item.when;
  title.appendChild(when);
  if (item.custom) {
    const c = document.createElement("span");
    c.className = "badge custom";
    c.textContent = "custom";
    title.appendChild(c);
  }
  main.appendChild(title);

  if (item.hint) {
    const hint = document.createElement("p");
    hint.className = "item-hint";
    hint.textContent = item.hint;
    main.appendChild(hint);
  }
  div.appendChild(main);

  const side = document.createElement("div");
  side.className = "item-side";

  const sel = document.createElement("select");
  sel.className = `status-select ${item.status}`;
  for (const [value, label] of Object.entries(STATUS_LABELS)) {
    const opt = document.createElement("option");
    opt.value = value;
    opt.textContent = label;
    opt.selected = value === item.status;
    sel.appendChild(opt);
  }
  sel.addEventListener("change", async () => {
    const updated = await api(`/api/items/${item.id}`, "PATCH", { status: sel.value });
    Object.assign(item, updated);
    render();
  });
  side.appendChild(sel);

  const actions = document.createElement("div");
  actions.className = "item-actions";

  const notesBtn = document.createElement("button");
  notesBtn.className = "mini-btn";
  notesBtn.textContent = item.notes ? "Notes •" : "Notes";
  notesBtn.addEventListener("click", () => {
    const wrap = div.querySelector(".item-notes");
    wrap.hidden = !wrap.hidden;
    if (!wrap.hidden) wrap.querySelector("textarea").focus();
  });
  actions.appendChild(notesBtn);

  if (item.custom) {
    const del = document.createElement("button");
    del.className = "mini-btn";
    del.textContent = "Delete";
    del.addEventListener("click", async () => {
      if (!confirm(`Delete "${item.name}"?`)) return;
      await api(`/api/items/${item.id}`, "DELETE");
      state.items = state.items.filter((i) => i.id !== item.id);
      render();
    });
    actions.appendChild(del);
  }
  side.appendChild(actions);
  div.appendChild(side);

  const notesWrap = document.createElement("div");
  notesWrap.className = "item-notes";
  notesWrap.hidden = !item.notes;
  const ta = document.createElement("textarea");
  ta.rows = 2;
  ta.placeholder = "Account numbers, who you spoke to, reference numbers…";
  ta.value = item.notes || "";
  ta.addEventListener("input", debounce(async () => {
    item.notes = ta.value;
    await api(`/api/items/${item.id}`, "PATCH", { notes: ta.value });
    notesBtn.textContent = ta.value ? "Notes •" : "Notes";
  }, 500));
  notesWrap.appendChild(ta);
  div.appendChild(notesWrap);

  return div;
}

function render() {
  const root = $("#checklist");
  root.innerHTML = "";
  const items = visibleItems();

  for (const category of state.categories) {
    const inCat = items.filter((i) => i.category === category);
    if (!inCat.length) continue;

    const all = state.items.filter((i) => i.category === category && i.status !== "na");
    const done = all.filter((i) => i.status === "done").length;

    const section = document.createElement("div");
    section.className = "category";
    const header = document.createElement("div");
    header.className = "category-header";
    header.innerHTML = `<h2>${category}</h2><span class="category-count">${done}/${all.length} done</span>`;
    section.appendChild(header);
    for (const item of inCat) section.appendChild(itemCard(item));
    root.appendChild(section);
  }

  if (!items.length) {
    root.innerHTML = '<p class="empty">Nothing matches — adjust the search or filter.</p>';
  }
  renderProgress();
}

// ---------------------------------------------------------------- move form
function fillMoveForm() {
  const form = $("#move-form");
  for (const [key, value] of Object.entries(state.move)) {
    if (form.elements[key]) form.elements[key].value = value;
  }
}

$("#move-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.target;
  const move = {};
  for (const key of Object.keys(state.move)) move[key] = form.elements[key].value;
  state.move = await api("/api/move", "PUT", move);
  const flash = $("#move-saved");
  flash.hidden = false;
  setTimeout(() => { flash.hidden = true; }, 2000);
  renderProgress();
});

// ---------------------------------------------------------------- tools
function buildLetter() {
  const m = state.move;
  const date = m.move_date
    ? new Date(m.move_date).toLocaleDateString(undefined, { day: "numeric", month: "long", year: "numeric" })
    : "[moving date]";
  return `Dear Sir or Madam,

Re: Change of address — ${m.name || "[your name]"}

I am writing to notify you that I am moving home and would like the address you hold on file for me updated.

Current address on file:
${m.old_address || "[old address]"}

New address (effective ${date}):
${m.new_address || "[new address]"}

Please update your records and send all future correspondence to the new address. Should you need to contact me, I can be reached${m.phone ? ` on ${m.phone}` : ""}${m.phone && m.email ? " or" : ""}${m.email ? ` at ${m.email}` : ""}.

Thank you for your assistance.

Yours faithfully,
${m.name || "[your name]"}`;
}

$("#copy-letter").addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(buildLetter());
    toast("Notification letter copied to clipboard");
  } catch {
    // Clipboard API can be unavailable over plain http — fall back to a prompt.
    window.prompt("Copy the letter below:", buildLetter());
  }
});

$("#export-csv").addEventListener("click", () => {
  const esc = (s) => `"${String(s || "").replace(/"/g, '""')}"`;
  const rows = [["Category", "Item", "When", "Status", "Notes", "Link"]];
  for (const item of state.items) {
    rows.push([item.category, item.name, item.when, STATUS_LABELS[item.status], item.notes, item.link || ""]);
  }
  const csv = rows.map((r) => r.map(esc).join(",")).join("\n");
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
  a.download = "address-change-progress.csv";
  a.click();
  URL.revokeObjectURL(a.href);
});

$("#reset").addEventListener("click", async () => {
  if (!confirm("Reset everything? All statuses, notes and custom items will be cleared.")) return;
  state = await api("/api/reset", "POST");
  fillMoveForm();
  render();
  toast("Checklist reset");
});

// ---------------------------------------------------------------- add item
$("#show-add").addEventListener("click", () => {
  $("#add-form").hidden = false;
  $("#add-form").elements.name.focus();
});
$("#cancel-add").addEventListener("click", () => { $("#add-form").hidden = true; });

$("#add-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.target;
  const item = await api("/api/items", "POST", {
    name: form.elements.name.value,
    category: form.elements.category.value,
    link: form.elements.link.value,
    hint: form.elements.hint.value,
  });
  state.items.push(item);
  form.reset();
  form.hidden = true;
  render();
  toast(`Added "${item.name}"`);
});

// ---------------------------------------------------------------- boot
$("#search").addEventListener("input", debounce(render, 150));
$("#status-filter").addEventListener("change", render);

(async function boot() {
  state = await api("/api/state");
  const catSel = $("#add-category");
  for (const c of state.categories) {
    const opt = document.createElement("option");
    opt.value = c;
    opt.textContent = c;
    catSel.appendChild(opt);
  }
  fillMoveForm();
  render();
})();
