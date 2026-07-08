const $ = (id) => document.getElementById(id);

const TOKEN = new URLSearchParams(location.search).get("token");
const WS_PROTO = location.protocol === "https:" ? "wss:" : "ws:";

function withToken(url) {
  if (!TOKEN) return url;
  return url + (url.includes("?") ? "&" : "?") + "token=" + encodeURIComponent(TOKEN);
}

let books = [];
let currentState = null;

async function api(path, options) {
  const response = await fetch(withToken(path), options);
  return response.json();
}

function sendJSON(method, path, body) {
  return api(path, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  });
}

function postJSON(path, body) {
  return sendJSON("POST", path, body);
}

function fillSelect(select, values, labels) {
  select.innerHTML = "";
  values.forEach((value, i) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = labels ? labels[i] : value;
    select.appendChild(option);
  });
}

function selectedBook() {
  return books.find((b) => b.id === Number($("book-select").value));
}

function populateBooks() {
  fillSelect($("book-select"), books.map((b) => b.id), books.map((b) => b.name));
  populateChapters();
}

function populateChapters() {
  const book = selectedBook();
  fillSelect($("chapter-select"), book.chapters.map((_, i) => i + 1));
  populateVerses();
}

function populateVerses() {
  const book = selectedBook();
  const chapter = Number($("chapter-select").value);
  const count = book.chapters[chapter - 1];
  fillSelect($("verse-select"), Array.from({ length: count }, (_, i) => i + 1));
}

function renderState(msg) {
  if (msg.type !== "state") return;
  currentState = msg;
  $("preview-text").textContent = msg.text;
  $("preview-ref").textContent =
    msg.mode === "slide"
      ? msg.caption || "Mensaje"
      : `${msg.book_name} ${msg.chapter}:${msg.verse} (RVR1960)`;
  $("preview-status").textContent = msg.visible ? "EN PANTALLA" : "Oculto";
  $("preview").classList.toggle("live", msg.visible);
  const toggle = $("toggle-btn");
  toggle.textContent = msg.visible ? "Ocultar" : "Mostrar";
  toggle.classList.toggle("showing", msg.visible);
  const dot = $("conn-dot");
  const connected = msg.overlays > 0;
  dot.classList.toggle("on", connected);
  dot.classList.toggle("off", !connected);
  dot.title = connected ? "Overlay conectado" : "Overlay desconectado";
}

let slides = [];
let editingId = null;

function slideForm() {
  return {
    text: $("slide-text").value.trim(),
    caption: $("slide-caption").value.trim(),
  };
}

function stopEditing() {
  editingId = null;
  $("slide-text").value = "";
  $("slide-caption").value = "";
  $("slide-save-btn").textContent = "Guardar";
  $("slide-cancel-btn").classList.add("hidden");
}

function startEditing(slide) {
  editingId = slide.id;
  $("slide-text").value = slide.text;
  $("slide-caption").value = slide.caption;
  $("slide-save-btn").textContent = "Actualizar";
  $("slide-cancel-btn").classList.remove("hidden");
}

async function deleteSlide(id) {
  if (!confirm("¿Borrar este mensaje?")) return;
  await api(`/api/slides/${id}`, { method: "DELETE" });
  if (editingId === id) stopEditing();
  await loadSlides();
}

function renderSlideList() {
  const list = $("slide-list");
  list.innerHTML = "";
  slides.forEach((slide) => {
    const li = document.createElement("li");
    const label = document.createElement("span");
    label.textContent = slide.caption ? `${slide.text} — ${slide.caption}` : slide.text;
    li.appendChild(label);
    const actions = document.createElement("div");
    const buttons = [
      ["Mostrar", () => postJSON("/api/slide", { text: slide.text, caption: slide.caption })],
      ["Editar", () => startEditing(slide)],
      ["Borrar", () => deleteSlide(slide.id)],
    ];
    buttons.forEach(([name, handler]) => {
      const btn = document.createElement("button");
      btn.textContent = name;
      if (name === "Borrar") btn.classList.add("danger");
      btn.onclick = handler;
      actions.appendChild(btn);
    });
    li.appendChild(actions);
    list.appendChild(li);
  });
}

async function loadSlides() {
  slides = await api("/api/slides");
  renderSlideList();
}

function connect() {
  const ws = new WebSocket(withToken(`${WS_PROTO}//${location.host}/ws?role=panel`));
  ws.onmessage = (ev) => renderState(JSON.parse(ev.data));
  ws.onclose = () => setTimeout(connect, 1500);
}

async function init() {
  books = await api("/api/books");
  populateBooks();

  $("book-select").onchange = populateChapters;
  $("chapter-select").onchange = populateVerses;

  $("set-btn").onclick = () =>
    postJSON("/api/verse", {
      book_id: Number($("book-select").value),
      chapter: Number($("chapter-select").value),
      verse: Number($("verse-select").value),
    });

  $("next-btn").onclick = () => postJSON("/api/next");
  $("prev-btn").onclick = () => postJSON("/api/prev");
  $("toggle-btn").onclick = () =>
    postJSON("/api/visibility", { visible: !(currentState && currentState.visible) });

  $("search-form").onsubmit = async (event) => {
    event.preventDefault();
    const q = $("search-input").value.trim();
    if (!q) return;
    const result = await api(`/api/search?q=${encodeURIComponent(q)}`);
    if (!result.found) {
      $("search-error").classList.remove("hidden");
      return;
    }
    $("search-error").classList.add("hidden");
    await postJSON("/api/verse", {
      book_id: result.book_id,
      chapter: result.chapter,
      verse: result.verse,
    });
    $("search-input").select();
  };

  $("slide-show-btn").onclick = () => {
    const payload = slideForm();
    if (!payload.text) return;
    postJSON("/api/slide", payload);
  };

  $("slide-save-btn").onclick = async () => {
    const payload = slideForm();
    if (!payload.text) return;
    if (editingId === null) {
      await postJSON("/api/slides", payload);
    } else {
      await sendJSON("PUT", `/api/slides/${editingId}`, payload);
    }
    stopEditing();
    await loadSlides();
  };

  $("slide-cancel-btn").onclick = stopEditing;

  await loadSlides();

  connect();
}

init();
