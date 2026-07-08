(function () {
  const box = document.getElementById("lower-third");
  const textEl = document.getElementById("verse-text");
  const refEl = document.getElementById("verse-ref");
  let currentKey = null;
  let pending = null;
  let retryMs = 1000;

  const TOKEN = new URLSearchParams(location.search).get("token");
  const WS_PROTO = location.protocol === "https:" ? "wss:" : "ws:";

  function apply(msg) {
    textEl.textContent = msg.text;
    if (msg.mode === "slide") {
      refEl.textContent = msg.caption;
      refEl.style.display = msg.caption ? "" : "none";
    } else {
      refEl.textContent = `${msg.book_name} ${msg.chapter}:${msg.verse} (RVR1960)`;
      refEl.style.display = "";
    }
    box.classList.remove("len-lg", "len-xl");
    if (msg.text.length > 320) box.classList.add("len-xl");
    else if (msg.text.length > 200) box.classList.add("len-lg");
  }

  function render(msg) {
    if (msg.type !== "state") return;
    const key =
      msg.mode === "slide"
        ? `s:${msg.text}|${msg.caption}`
        : `v:${msg.book_id}:${msg.chapter}:${msg.verse}`;
    if (pending) { clearTimeout(pending); pending = null; }

    if (!msg.visible) {
      box.classList.add("hidden");
      currentKey = key;
      pending = setTimeout(() => apply(msg), 300);
      return;
    }
    if (box.classList.contains("hidden")) {
      apply(msg);
      box.classList.remove("hidden");
      currentKey = key;
      return;
    }
    if (key === currentKey) {
      apply(msg);
      return;
    }
    // Cambio de versículo con el overlay visible: fundido salida → entrada.
    box.classList.add("hidden");
    pending = setTimeout(() => {
      apply(msg);
      box.classList.remove("hidden");
    }, 300);
    currentKey = key;
  }

  function connect() {
    let url = `${WS_PROTO}//${location.host}/ws?role=overlay`;
    if (TOKEN) url += `&token=${encodeURIComponent(TOKEN)}`;
    const ws = new WebSocket(url);
    ws.onopen = () => { retryMs = 1000; };
    ws.onmessage = (ev) => render(JSON.parse(ev.data));
    ws.onclose = () => {
      box.classList.add("hidden");
      setTimeout(connect, retryMs);
      retryMs = Math.min(retryMs * 2, 5000);
    };
  }

  connect();
})();
