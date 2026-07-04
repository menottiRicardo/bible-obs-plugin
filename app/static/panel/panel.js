const $ = (id) => document.getElementById(id);

let books = [];
let currentState = null;

async function api(path, options) {
  const response = await fetch(path, options);
  return response.json();
}

function postJSON(path, body) {
  return api(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  });
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
  $("preview-ref").textContent = `${msg.book_name} ${msg.chapter}:${msg.verse} (RVR1960)`;
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

function connect() {
  const ws = new WebSocket(`ws://${location.host}/ws?role=panel`);
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

  connect();
}

init();
