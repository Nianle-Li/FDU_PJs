const state = {
  users: [],
  campuses: [],
  activities: [],
  reservations: [],
  currentUserId: 4,
  exploreEntity: "facilities",
};

const exploreColumns = {
  facilities: ["name", "type", "building_name", "open_time"],
  courses: ["course_name", "teachers", "schedules"],
  buildings: ["name", "type", "campus_name"],
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));
const API_BASE = window.location.protocol === "file:" ? "http://127.0.0.1:8000" : "";

async function api(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.error || `请求失败：${response.status}`);
  }
  return payload;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formPayload(form) {
  return Object.fromEntries(new FormData(form).entries());
}

function buildQuery(params) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && String(value).trim() !== "") {
      query.set(key, value);
    }
  });
  const text = query.toString();
  return text ? `?${text}` : "";
}

function showMessage(text, isError = false) {
  const box = $("#message");
  box.textContent = text;
  box.classList.toggle("error", isError);
  box.classList.add("is-visible");
  window.clearTimeout(showMessage.timer);
  showMessage.timer = window.setTimeout(
    () => box.classList.remove("is-visible"),
    2600,
  );
}

function formatTime(value) {
  if (!value) return "待定";
  return String(value).slice(0, 16).replace("T", " ");
}

function currentUser() {
  return state.users.find(
    (user) => Number(user.user_id) === Number(state.currentUserId),
  );
}

function reservationFor(activityId) {
  return state.reservations.find(
    (row) => Number(row.activity_id) === Number(activityId),
  );
}

async function checkHealth() {
  const health = $("#health");
  try {
    const payload = await api("/api/health");
    const db = payload.database;
    health.className = `status ${db.connected ? "ok" : "warn"}`;
    health.textContent = db.connected
      ? `后端正常 · ${db.mode}`
      : "后端正常 · 数据库未连接";
    health.title = db.connected ? "" : db.error || "";
  } catch (error) {
    health.className = "status warn";
    health.textContent = "后端未连接";
    health.title = error.message;
  }
}

async function loadReferenceData() {
  const [users, campuses] = await Promise.all([
    api("/api/users"),
    api("/api/campuses"),
  ]);
  state.users = users.items || [];
  state.campuses = campuses.items || [];
  if (
    !state.users.some(
      (user) => Number(user.user_id) === Number(state.currentUserId),
    ) &&
    state.users.length
  ) {
    state.currentUserId = Number(state.users[0].user_id);
  }
  renderUserSelect();
  renderCampusFilter();
}

function renderUserSelect() {
  const select = $("#userSelect");
  select.innerHTML = state.users
    .map(
      (user) =>
        `<option value="${escapeHtml(user.user_id)}">${escapeHtml(user.name)} · ${escapeHtml(user.role)}</option>`,
    )
    .join("");
  select.value = String(state.currentUserId);
  updateUserProfile();
}

function renderCampusFilter() {
  const select = $("#campusFilter");
  select.innerHTML = [
    `<option value="">全部校区</option>`,
    ...state.campuses.map(
      (campus) =>
        `<option value="${escapeHtml(campus.campus_id)}">${escapeHtml(campus.name)}</option>`,
    ),
  ].join("");
}

function updateUserProfile() {
  const user = currentUser();
  const hidden = $("#nlQueryForm").elements.user_id;
  hidden.value = state.currentUserId;
  $("#userProfile").innerHTML = user
    ? `
      <div><strong>${escapeHtml(user.name)}</strong><span>${escapeHtml(user.role)}</span></div>
      <div>${escapeHtml(user.department)}</div>
    `
    : `<div>请选择用户</div>`;
}

async function loadActivities(event) {
  if (event) event.preventDefault();
  const params = formPayload($("#activityFilterForm"));
  const payload = await api(`/api/activities${buildQuery(params)}`);
  state.activities = payload.items || [];
  renderActivities();
}

async function loadReservations() {
  const payload = await api(`/api/users/${state.currentUserId}/reservations`);
  state.reservations = payload.items || [];
  renderReservations();
  renderActivities();
}

function renderActivities() {
  const target = $("#activityCards");
  if (!state.activities.length) {
    target.innerHTML = `<div class="empty">没有匹配活动</div>`;
    return;
  }
  target.innerHTML = state.activities
    .map((activity) => {
      const reservation = reservationFor(activity.activity_id);
      const reserved = Boolean(reservation);
      return `
        <article class="activity-card ${reserved ? "is-reserved" : ""}">
          <div class="activity-card-head">
            <span class="badge">${escapeHtml(activity.campus_name)}</span>
            <span class="count">${escapeHtml(activity.participant_count)} 人已约</span>
          </div>
          <h3>${escapeHtml(activity.name)}</h3>
          <p>${escapeHtml(activity.description)}</p>
          <dl>
            <div><dt>时间</dt><dd>${escapeHtml(formatTime(activity.start_time))}</dd></div>
            <div><dt>地点</dt><dd>${escapeHtml(activity.building_name)} · ${escapeHtml(activity.facility_name)}</dd></div>
            <div><dt>主办</dt><dd>${escapeHtml(activity.organizer)}</dd></div>
          </dl>
          <div class="card-actions">
            <button type="button" data-reserve="${escapeHtml(activity.activity_id)}" class="${reserved ? "secondary-button" : ""}">
              ${reserved ? "取消预约" : "预约活动"}
            </button>
            ${reserved ? `<span class="reserved-note">${escapeHtml(reservation.status)}</span>` : ""}
          </div>
        </article>
      `;
    })
    .join("");
  $$("[data-reserve]").forEach((button) => {
    button.addEventListener("click", () =>
      toggleReservation(Number(button.dataset.reserve)).catch((error) =>
        showMessage(error.message, true),
      ),
    );
  });
  // 点击卡片展开/收起活动详情；按钮区域不触发
  target.querySelectorAll(".activity-card").forEach((card) => {
    card.addEventListener("click", (event) => {
      if (event.target.closest("[data-reserve], .card-actions")) return;
      card.classList.toggle("is-expanded");
    });
  });
}

function renderReservations() {
  const target = $("#reservationList");
  if (!state.reservations.length) {
    target.innerHTML = `<div class="empty">当前用户还没有预约活动</div>`;
    return;
  }
  target.innerHTML = state.reservations
    .map(
      (item) => `
      <article class="reservation-item">
        <div>
          <strong>${escapeHtml(item.activity_name)}</strong>
          <span>${escapeHtml(formatTime(item.start_time))}</span>
        </div>
        <p>${escapeHtml(item.campus_name)} · ${escapeHtml(item.facility_name)}</p>
        <button type="button" class="secondary-button" data-cancel="${escapeHtml(item.activity_id)}">取消</button>
      </article>
    `,
    )
    .join("");
  $$("[data-cancel]").forEach((button) => {
    button.addEventListener("click", () =>
      cancelReservation(Number(button.dataset.cancel)).catch((error) =>
        showMessage(error.message, true),
      ),
    );
  });
}

async function toggleReservation(activityId) {
  if (reservationFor(activityId)) {
    await cancelReservation(activityId);
    return;
  }
  await api(`/api/activities/${activityId}/reserve`, {
    method: "POST",
    body: JSON.stringify({ user_id: state.currentUserId }),
  });
  showMessage("预约成功");
  await Promise.all([loadActivities(), loadReservations()]);
}

async function cancelReservation(activityId) {
  await api(`/api/activities/${activityId}/reserve/${state.currentUserId}`, {
    method: "DELETE",
  });
  showMessage("预约已取消");
  await Promise.all([loadActivities(), loadReservations()]);
}

async function askNaturalLanguage(event) {
  if (event) event.preventDefault();
  const payload = formPayload($("#nlQueryForm"));
  const result = await api("/api/nl-query", {
    method: "POST",
    body: JSON.stringify({ ...payload, role: "user" }),
  });
  $("#nlAnswer").innerHTML = `
    <div class="answer-summary">
      <div><strong>${escapeHtml(result.title)}</strong><br />${escapeHtml(result.answer)}</div>
      <div><strong>类别</strong><br />${escapeHtml(result.category)}</div>
    </div>
    <div class="sql-result">${renderRows(result.rows || [])}</div>
  `;
  showMessage("查询完成");
}

function renderRows(rows) {
  if (!rows.length) {
    return `<div class="empty">查询无结果</div>`;
  }
  const keys = Object.keys(rows[0]);
  return `
    <table>
      <thead><tr>${keys.map((key) => `<th>${escapeHtml(key)}</th>`).join("")}</tr></thead>
      <tbody>
        ${rows.map((row) => `<tr>${keys.map((key) => `<td>${escapeHtml(row[key])}</td>`).join("")}</tr>`).join("")}
      </tbody>
    </table>
  `;
}

async function loadExplore(event) {
  if (event) event.preventDefault();
  const params = formPayload($("#exploreForm"));
  const payload = await api(`/api/${state.exploreEntity}${buildQuery(params)}`);
  const rows = payload.items || [];
  const keys = exploreColumns[state.exploreEntity];
  $("#exploreContent").innerHTML = rows.length
    ? rows
        .slice(0, 8)
        .map(
          (row) => `
          <article class="compact-item">
            <strong>${escapeHtml(row[keys[0]])}</strong>
            <span>${keys
              .slice(1)
              .map((key) => escapeHtml(row[key]))
              .join(" · ")}</span>
          </article>
        `,
        )
        .join("")
    : `<div class="empty">没有匹配数据</div>`;
}

function bindEvents() {
  $("#userSelect").addEventListener("change", async (event) => {
    state.currentUserId = Number(event.target.value);
    updateUserProfile();
    await loadReservations();
    showMessage("已切换用户");
  });
  $("#activityFilterForm").addEventListener("submit", (event) =>
    loadActivities(event).catch((error) => showMessage(error.message, true)),
  );
  $("#clearActivityFilterBtn").addEventListener("click", () => {
    $("#activityFilterForm").reset();
    loadActivities().catch((error) => showMessage(error.message, true));
  });
  $("#refreshActivitiesBtn").addEventListener("click", () =>
    loadActivities().catch((error) => showMessage(error.message, true)),
  );
  $("#refreshReservationsBtn").addEventListener("click", () =>
    loadReservations().catch((error) => showMessage(error.message, true)),
  );
  $("#nlQueryForm").addEventListener("submit", (event) =>
    askNaturalLanguage(event).catch((error) =>
      showMessage(error.message, true),
    ),
  );
  $$("[data-question]").forEach((button) => {
    button.addEventListener("click", () => {
      $("#nlQuestion").value = button.dataset.question;
      askNaturalLanguage().catch((error) => showMessage(error.message, true));
    });
  });
  $("#exploreEntity").addEventListener("change", (event) => {
    state.exploreEntity = event.target.value;
    loadExplore().catch((error) => showMessage(error.message, true));
  });
  $("#exploreForm").addEventListener("submit", (event) =>
    loadExplore(event).catch((error) => showMessage(error.message, true)),
  );
  $$(".user-section-tabs .tab").forEach((tab) => {
    tab.addEventListener("click", () => switchSection(tab.dataset.section));
  });
}

function switchSection(section) {
  if (!section) return;
  $$(".user-section-tabs .tab").forEach((tab) => {
    const active = tab.dataset.section === section;
    tab.classList.toggle("is-active", active);
    if (active) {
      tab.setAttribute("aria-selected", "true");
    } else {
      tab.removeAttribute("aria-selected");
    }
  });
  $$(".section-pane").forEach((pane) => {
    pane.classList.toggle("hidden", pane.dataset.section !== section);
  });
}

async function init() {
  bindEvents();
  await checkHealth();
  await loadReferenceData();
  await Promise.all([
    loadActivities(),
    loadReservations(),
    askNaturalLanguage(),
    loadExplore(),
  ]);
}

init().catch((error) => showMessage(error.message, true));
