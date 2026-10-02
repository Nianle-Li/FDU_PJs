// snapshot.js - lightweight snapshot feature (IndexedDB storage)
// Dependencies: html2canvas (global)
import * as logger from "./logger.js";

// Minimal IndexedDB helper
function openDB() {
  return new Promise((resolve, reject) => {
    const rq = indexedDB.open("dungeon_snapshots", 1);
    rq.onupgradeneeded = (e) => {
      const db = e.target.result;
      if (!db.objectStoreNames.contains("snapshots")) {
        db.createObjectStore("snapshots", { keyPath: "id" });
      }
    };
    rq.onsuccess = (e) => resolve(e.target.result);
    rq.onerror = (e) => reject(e.target.error);
  });
}

async function saveSnapshotToDB(item) {
  const db = await openDB();
  return new Promise((res, rej) => {
    const tx = db.transaction("snapshots", "readwrite");
    const store = tx.objectStore("snapshots");
    const rq = store.put(item);
    rq.onsuccess = () => res(item);
    rq.onerror = (e) => rej(e.target.error);
  });
}

async function getAllSnapshotsFromDB() {
  const db = await openDB();
  return new Promise((res, rej) => {
    const tx = db.transaction("snapshots", "readonly");
    const store = tx.objectStore("snapshots");
    const rq = store.getAll();
    rq.onsuccess = () => res(rq.result || []);
    rq.onerror = (e) => rej(e.target.error);
  });
}

async function deleteSnapshotFromDB(id) {
  const db = await openDB();
  return new Promise((res, rej) => {
    const tx = db.transaction("snapshots", "readwrite");
    const store = tx.objectStore("snapshots");
    const rq = store.delete(id);
    rq.onsuccess = () => res();
    rq.onerror = (e) => rej(e.target.error);
  });
}

// Utility: convert canvas to Blob Promise
function canvasToBlob(canvas, type = "image/jpeg", quality = 0.85) {
  return new Promise((res) => canvas.toBlob(res, type, quality));
}

async function makeThumbnailFromCanvas(canvas, width = 400) {
  const ratio = width / canvas.width;
  const h = Math.round(canvas.height * ratio);
  const thumb = document.createElement("canvas");
  thumb.width = width;
  thumb.height = h;
  const ctx = thumb.getContext("2d");
  ctx.drawImage(canvas, 0, 0, width, h);
  const blob = await canvasToBlob(thumb, "image/png", 0.7);
  return blob;
}

const HTML2CANVAS_CDN =
  "https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/dist/html2canvas.min.js";

async function ensureHtml2Canvas() {
  if (window.html2canvas) return;

  const tried = [];
  // Build a list of candidate URLs to try (CDN https, CDN http if page is http, local relative paths)
  const candidates = [HTML2CANVAS_CDN];
  if (location.protocol === "http:") {
    candidates.push(HTML2CANVAS_CDN.replace(/^https:/, "http:"));
  }
  // Local fallbacks (relative to the served index page) — append cache-bust to force re-fetch when we just updated the file
  const cacheBust = "?v=" + Date.now();
  candidates.push("static/js/vendor/html2canvas.min.js" + cacheBust);
  candidates.push("/frontend/static/js/vendor/html2canvas.min.js" + cacheBust);

  let lastErr = null;
  for (const url of candidates) {
    try {
      await new Promise((resolve, reject) => {
        const s = document.createElement("script");
        s.src = url;
        s.crossOrigin = "anonymous";
        s.onload = () => resolve();
        s.onerror = (e) => reject(new Error("Failed to load script: " + url));
        document.head.appendChild(s);
        // If network errors result in stalled loads, add a timeout
        setTimeout(
          () => reject(new Error("Timeout loading script: " + url)),
          7000
        );
      });
      // Ensure the library attached a global
      if (window.html2canvas) return;
      lastErr = new Error(
        "Script loaded but html2canvas global not found: " + url
      );
    } catch (err) {
      logger.warn("html2canvas load attempt failed:", url, err);
      tried.push({ url, err: err.message });
      lastErr = err;
      // try next candidate
    }
  }

  // If we reach here, all attempts failed
  const hint =
    `Failed to load html2canvas. Attempts: ${JSON.stringify(tried)}.\n` +
    "Possible workarounds: 1) Download html2canvas (v1.4.1) and place it at 'frontend/static/js/vendor/html2canvas.min.js'. 2) Ensure your environment allows HTTPS requests to CDN (check proxy/TLS interception).";
  const e = new Error(hint + " Last error: " + (lastErr && lastErr.message));
  throw e;
}

async function takeSnapshot() {
  const btn = document.getElementById("btn-snapshot");
  try {
    if (btn) {
      btn.disabled = true;
      btn.textContent = "📸 Capturing...";
    }

    await ensureHtml2Canvas();

    const target = document.querySelector("#map-container") || document.body;
    const dpr = window.devicePixelRatio || 1;
    // Try to preserve element background and avoid black fill from JPEG when parts are transparent
    const bg = window.getComputedStyle(target).backgroundColor || null;
    const canvas = await html2canvas(target, {
      scale: Math.min(dpr, 2),
      useCORS: true,
      backgroundColor: bg,
    });

    // Use PNG for full snapshot to preserve transparency / avoid black fill when some layers can't be captured
    const fullBlob = await canvasToBlob(canvas, "image/png", 0.9);
    const thumbBlob = await makeThumbnailFromCanvas(canvas, 400);

    const id = "snap_" + Date.now();
    const meta = {
      id,
      ts: new Date().toISOString(),
      room: document.getElementById("player-room-navbar")?.textContent || null,
      power:
        document.getElementById("player-power-navbar")?.textContent || null,
    };

    const item = { id, meta, fullBlob, thumbBlob };

    await saveSnapshotToDB(item);
    alert("Snapshot saved");
    renderSnapshotLibrary();
  } catch (err) {
    logger.error("Snapshot error", err);
    const msg = `Snapshot failed: ${
      err.message || err
    }.\n\nPossible fixes:\n - Download html2canvas v1.4.1 and save it to 'frontend/static/js/vendor/html2canvas.min.js'\n - Ensure your network/proxy allows HTTPS access to the CDN (https://cdn.jsdelivr.net).`;
    alert(msg);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = "📸 Snapshot";
    }
  }
}

// Render library modal grid
async function renderSnapshotLibrary() {
  const list = document.getElementById("snapshot-list");
  if (!list) return;
  list.innerHTML = '<div class="text-muted">Loading...</div>';
  try {
    const items = await getAllSnapshotsFromDB();
    if (!items.length) {
      list.innerHTML = '<div class="text-muted">No snapshots yet</div>';
      return;
    }
    list.innerHTML = "";
    for (const item of items.sort((a, b) => (a.meta.ts < b.meta.ts ? 1 : -1))) {
      const url = URL.createObjectURL(item.thumbBlob);
      const card = document.createElement("div");
      card.className = "snapshot-card";
      card.style.cssText =
        "display:inline-block; margin:8px; width:220px; vertical-align:top;";
      card.innerHTML = `
        <div style="border:1px solid #444; border-radius:6px; overflow:hidden; background:#2b241c; color:#ffe8c0;">
          <img src="${url}" style="width:100%; display:block;" />
          <div style="padding:8px; font-size:14px;">
            <div><strong>${new Date(
              item.meta.ts
            ).toLocaleString()}</strong></div>
            <div>Room: ${item.meta.room || "-"}</div>
            <div>Power: ${item.meta.power || "-"}</div>
            <div style="margin-top:6px; display:flex; gap:6px;">
              <button class="btn btn-sm btn-light" data-action="view" data-id="${
                item.id
              }">View</button>
              <button class="btn btn-sm btn-outline-light" data-action="download" data-id="${
                item.id
              }">Download</button>
              <button class="btn btn-sm btn-danger" data-action="delete" data-id="${
                item.id
              }">Delete</button>
            </div>
          </div>
        </div>
      `;
      list.appendChild(card);
      // attach handlers
      card.addEventListener("click", (e) => {
        const btn = e.target.closest("button");
        if (!btn) return;
        const action = btn.getAttribute("data-action");
        const id = btn.getAttribute("data-id");
        if (action === "view") viewSnapshot(id);
        if (action === "download") downloadSnapshot(id);
        if (action === "delete") confirmDeleteSnapshot(id);
      });
    }
  } catch (err) {
    list.innerHTML = '<div class="text-danger">Failed to load snapshots</div>';
    logger.error(err);
  }
}

async function getSnapshotById(id) {
  const all = await getAllSnapshotsFromDB();
  return all.find((x) => x.id === id);
}

async function viewSnapshot(id) {
  const item = await getSnapshotById(id);
  if (!item) return alert("Snapshot not found");
  const url = URL.createObjectURL(item.fullBlob);
  const img = document.getElementById("snapshot-view-img");
  img.src = url;
  document.getElementById("snapshot-view-meta").textContent = `${new Date(
    item.meta.ts
  ).toLocaleString()}  Room: ${item.meta.room || "-"}  Power: ${
    item.meta.power || "-"
  }`;
  const modal = new bootstrap.Modal(
    document.getElementById("snapshotViewerModal")
  );
  modal.show();
}

async function downloadSnapshot(id) {
  const item = await getSnapshotById(id);
  if (!item) return alert("Snapshot not found");
  const url = URL.createObjectURL(item.fullBlob);
  const a = document.createElement("a");
  a.href = url;
  // infer extension from blob mime type (fallback to png)
  const ext =
    (item.fullBlob && item.fullBlob.type && item.fullBlob.type.split("/")[1]) ||
    "png";
  a.download = `${item.id}.${ext}`;
  document.body.appendChild(a);
  a.click();
  a.remove();
}

async function confirmDeleteSnapshot(id) {
  if (!confirm("Delete this snapshot?")) return;
  await deleteSnapshotFromDB(id);
  renderSnapshotLibrary();
}

// init
document.addEventListener("DOMContentLoaded", () => {
  const btn = document.getElementById("btn-snapshot");
  if (btn) btn.addEventListener("click", takeSnapshot);
  const openBtn = document.getElementById("btn-open-snapshots");
  if (openBtn)
    openBtn.addEventListener("click", () => {
      const modal = new bootstrap.Modal(
        document.getElementById("snapshotModal")
      );
      renderSnapshotLibrary();
      modal.show();
    });
});

export {};
