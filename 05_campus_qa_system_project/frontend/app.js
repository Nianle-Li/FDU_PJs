const state = {
  meta: { building_types: [], facility_types: [], query_categories: [] },
  campuses: [],
  buildings: [],
  facilities: [],
  activities: [],
  queryMode: "traditional",
  traditionalEntity: "campuses",
  browseTab: "history",
  browseEntity: "campuses",
  currentView: "query",
  browseRows: [],
  popularQueryRows: [],
};

const entityColumns = {
  campuses: [
    ["campus_id", "ID"],
    ["name", "校区"],
    ["address", "地址"],
  ],
  buildings: [
    ["building_id", "ID"],
    ["name", "建筑"],
    ["type", "类型"],
    ["campus_name", "校区"],
  ],
  facilities: [
    ["facility_id", "ID"],
    ["name", "设施"],
    ["type", "类型"],
    ["open_time", "开放时间"],
    ["building_name", "建筑"],
    ["campus_name", "校区"],
  ],
  courses: [
    ["offering_id", "开设ID"],
    ["course_name", "课程"],
    ["course_code", "课程代码"],
    ["teachers", "教师"],
    ["semester", "学期"],
    ["schedules", "排课"],
  ],
  activities: [
    ["activity_id", "ID"],
    ["name", "活动"],
    ["start_time", "开始时间"],
    ["organizer", "主办单位"],
    ["facility_name", "设施"],
    ["campus_name", "校区"],
    ["participant_count", "参与数"],
  ],
  queryLogs: [
    ["log_id", "ID"],
    ["query_time", "时间"],
    ["user_name", "用户"],
    ["query_category", "类别"],
    ["query_content", "内容"],
  ],
  popularQueries: [
    ["query_category", "类别"],
    ["query_count", "次数"],
    ["latest_query", "最近查询"],
    ["latest_query_time", "最近时间"],
  ],
  popularActivities: [
    ["activity_name", "活动"],
    ["participant_count", "参与数"],
    ["start_time", "开始时间"],
    ["organizer", "主办单位"],
    ["facility_name", "设施"],
    ["campus_name", "校区"],
  ],
  activityParticipants: [
    ["user_id", "用户 ID"],
    ["user_name", "用户"],
    ["role", "身份"],
    ["department", "院系"],
    ["status", "参与状态"],
    ["activity_name", "活动"],
  ],
};

const editableEntities = new Set(["buildings", "facilities", "activities"]);

const csvImportDefinitions = {
  buildings: {
    label: "建筑",
    headers: ["name", "type", "campus_id"],
    sample: ["批量导入教学楼", "教学楼", "1"],
    aliases: {
      建筑名称: "name",
      名称: "name",
      建筑类型: "type",
      类型: "type",
      所属校区ID: "campus_id",
      校区ID: "campus_id",
      campus: "campus_id",
    },
  },
  facilities: {
    label: "设施",
    headers: ["name", "type", "open_time", "building_id"],
    sample: ["批量导入自习室", "自习室", "每日 08:00-22:00", "1"],
    aliases: {
      设施名称: "name",
      名称: "name",
      设施类型: "type",
      类型: "type",
      开放时间: "open_time",
      所属建筑ID: "building_id",
      建筑ID: "building_id",
    },
  },
  activities: {
    label: "活动",
    headers: [
      "name",
      "organizer",
      "start_time",
      "end_time",
      "facility_id",
      "description",
    ],
    sample: [
      "批量导入讲座",
      "学生事务中心",
      "2026-06-01T14:00",
      "2026-06-01T16:00",
      "1",
      "CSV 批量导入测试活动",
    ],
    aliases: {
      活动名称: "name",
      名称: "name",
      主办单位: "organizer",
      主办: "organizer",
      开始时间: "start_time",
      结束时间: "end_time",
      举办设施ID: "facility_id",
      设施ID: "facility_id",
      活动简介: "description",
      简介: "description",
    },
  },
  query_logs: {
    label: "查询记录",
    headers: ["user_id", "query_category", "query_content"],
    sample: ["4", "活动", "CSV 导入测试查询"],
    aliases: {
      用户ID: "user_id",
      查询类别: "query_category",
      类别: "query_category",
      查询内容: "query_content",
      内容: "query_content",
    },
  },
};

const traditionalDefinitions = {
  campuses: {
    endpoint: "/api/campuses",
    fields: [
      {
        name: "q",
        label: "关键词",
        type: "search",
        placeholder: "校区名或地址",
      },
    ],
  },
  buildings: {
    endpoint: "/api/buildings",
    fields: [
      {
        name: "q",
        label: "关键词",
        type: "search",
        placeholder: "建筑名、类型或校区",
      },
      {
        name: "campus_id",
        label: "所属校区",
        type: "select",
        source: "campuses",
        placeholder: "全部校区",
      },
      {
        name: "type",
        label: "建筑类型",
        type: "select",
        source: "buildingTypes",
        placeholder: "全部类型",
      },
    ],
  },
  facilities: {
    endpoint: "/api/facilities",
    fields: [
      {
        name: "q",
        label: "关键词",
        type: "search",
        placeholder: "设施名、类型或建筑",
      },
      {
        name: "campus_id",
        label: "所在校区",
        type: "select",
        source: "campuses",
        placeholder: "全部校区",
      },
      {
        name: "building_id",
        label: "所属建筑",
        type: "select",
        source: "buildings",
        placeholder: "全部建筑",
      },
      {
        name: "type",
        label: "设施类型",
        type: "select",
        source: "facilityTypes",
        placeholder: "全部类型",
      },
    ],
  },
  courses: {
    endpoint: "/api/courses",
    fields: [
      {
        name: "q",
        label: "关键词",
        type: "search",
        placeholder: "课程、代码或教师",
      },
      {
        name: "course_name",
        label: "课程名称",
        type: "text",
        placeholder: "例如：数据库系统原理",
      },
      {
        name: "course_code",
        label: "课程代码",
        type: "text",
        placeholder: "例如：COMP130015",
      },
      {
        name: "teacher",
        label: "教师",
        type: "text",
        placeholder: "例如：李芳",
      },
      {
        name: "semester",
        label: "学期",
        type: "text",
        placeholder: "例如：2025-2026 春季学期",
      },
      {
        name: "day_of_week",
        label: "星期",
        type: "select",
        options: ["周一", "周二", "周三", "周四", "周五", "周六", "周日"],
        placeholder: "全部",
      },
    ],
  },
  activities: {
    endpoint: "/api/activities",
    fields: [
      {
        name: "q",
        label: "关键词",
        type: "search",
        placeholder: "活动、简介、主办方或地点",
      },
      {
        name: "organizer",
        label: "主办单位",
        type: "text",
        placeholder: "例如：计算机科学技术学院",
      },
      {
        name: "campus_id",
        label: "所在校区",
        type: "select",
        source: "campuses",
        placeholder: "全部校区",
      },
      {
        name: "facility_id",
        label: "举办设施",
        type: "select",
        source: "facilities",
        placeholder: "全部设施",
      },
      { name: "start_from", label: "开始不早于", type: "datetime-local" },
      { name: "start_to", label: "开始不晚于", type: "datetime-local" },
    ],
  },
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

function showMessage(text, isError = false) {
  const box = $("#message");
  if (!box) {
    if (isError) console.error(text);
    return;
  }
  window.clearTimeout(showMessage.timer);
  box.textContent = text;
  box.classList.toggle("error", isError);
  box.classList.add("is-visible");
  showMessage.timer = window.setTimeout(() => {
    box.classList.remove("is-visible");
  }, isError ? 8000 : 3500);
}

function switchAdminView(view, options = {}) {
  const validViews = new Set(["query", "browse", "maintain"]);
  const nextView = validViews.has(view) ? view : "query";
  state.currentView = nextView;
  $$("[data-admin-section]").forEach((section) => {
    section.classList.toggle(
      "is-hidden",
      section.dataset.adminSection !== nextView,
    );
  });
  $$("[data-admin-view]").forEach((button) => {
    const active = button.dataset.adminView === nextView;
    button.classList.toggle("is-active", active);
    button.setAttribute("aria-pressed", String(active));
  });
  if (options.updateHash !== false && window.location.hash !== `#${nextView}`) {
    window.history.replaceState(null, "", `#${nextView}`);
  }
  if (options.scroll !== false) {
    const section = document.querySelector(
      `[data-admin-section="${nextView}"]`,
    );
    section?.scrollIntoView({ block: "start", behavior: "smooth" });
  }
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

function formPayload(form) {
  const data = new FormData(form);
  return Object.fromEntries(data.entries());
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function selectOptions(source) {
  if (source === "campuses") {
    return state.campuses.map((row) => [row.campus_id, row.name]);
  }
  if (source === "buildings") {
    return state.buildings.map((row) => [row.building_id, row.name]);
  }
  if (source === "facilities") {
    return state.facilities.map((row) => [row.facility_id, row.name]);
  }
  if (source === "activities") {
    return state.activities.map((row) => [
      row.activity_id,
      `${row.name}（ID ${row.activity_id}）`,
    ]);
  }
  if (source === "buildingTypes") {
    return state.meta.building_types.map((value) => [value, value]);
  }
  if (source === "facilityTypes") {
    return state.meta.facility_types.map((value) => [value, value]);
  }
  if (source === "queryCategories") {
    return state.meta.query_categories.map((value) => [value, value]);
  }
  return [];
}

function fillSelect(select, rows, valueKey, labelKey, placeholder) {
  select.innerHTML = "";
  if (placeholder) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = placeholder;
    select.appendChild(option);
  }
  rows.forEach((row) => {
    const option = document.createElement("option");
    option.value = row[valueKey];
    option.textContent = row[labelKey];
    select.appendChild(option);
  });
}

function fillTypeSelect(select, values) {
  select.innerHTML = "";
  values.forEach((value) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value;
    select.appendChild(option);
  });
}

function refreshOptions() {
  $$("[data-options='buildingTypes']").forEach((select) =>
    fillTypeSelect(select, state.meta.building_types),
  );
  $$("[data-options='facilityTypes']").forEach((select) =>
    fillTypeSelect(select, state.meta.facility_types),
  );
  $$("[data-options='queryCategories']").forEach((select) =>
    fillTypeSelect(select, state.meta.query_categories),
  );
  $$("[data-options='campuses']").forEach((select) =>
    fillSelect(select, state.campuses, "campus_id", "name"),
  );
  $$("[data-options='buildings']").forEach((select) =>
    fillSelect(select, state.buildings, "building_id", "name"),
  );
  $$("[data-options='facilities']").forEach((select) =>
    fillSelect(select, state.facilities, "facility_id", "name"),
  );
}

async function loadReferenceData() {
  const [meta, campuses, buildings, facilities, activities] = await Promise.all(
    [
      api("/api/meta"),
      api("/api/campuses"),
      api("/api/buildings"),
      api("/api/facilities"),
      api("/api/activities"),
    ],
  );
  state.meta = meta;
  state.campuses = campuses.items || [];
  state.buildings = buildings.items || [];
  state.facilities = facilities.items || [];
  state.activities = activities.items || [];
  refreshOptions();
  renderAdminMetrics();
}

function formatTime(value) {
  if (!value) return "待定";
  return String(value).slice(0, 16).replace("T", " ");
}

function previewText(value, maxLength = 42) {
  const text = String(value ?? "").trim();
  return text.length > maxLength ? `${text.slice(0, maxLength)}...` : text;
}

function parseCsv(text) {
  const rows = [];
  let row = [];
  let cell = "";
  let inQuotes = false;
  const normalized = text.replace(/^\uFEFF/, "");
  for (let index = 0; index < normalized.length; index += 1) {
    const char = normalized[index];
    const next = normalized[index + 1];
    if (char === '"' && inQuotes && next === '"') {
      cell += '"';
      index += 1;
    } else if (char === '"') {
      inQuotes = !inQuotes;
    } else if (char === "," && !inQuotes) {
      row.push(cell);
      cell = "";
    } else if ((char === "\n" || char === "\r") && !inQuotes) {
      if (char === "\r" && next === "\n") index += 1;
      row.push(cell);
      if (row.some((value) => value.trim() !== "")) rows.push(row);
      row = [];
      cell = "";
    } else {
      cell += char;
    }
  }
  row.push(cell);
  if (row.some((value) => value.trim() !== "")) rows.push(row);
  if (inQuotes) {
    throw new Error("CSV 引号没有正确闭合");
  }
  return rows;
}

function csvEscape(value) {
  const text = String(value ?? "");
  return /[",\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}

function updateCsvImportHint() {
  const hintEl = $("#csvImportHint");
  if (!hintEl) return;
  const entity = $("#csvImportEntity")?.value || "buildings";
  const definition = csvImportDefinitions[entity];
  if (!definition) return;
  hintEl.textContent = `${definition.label} CSV 字段：${definition.headers.join(", ")}`;
}

function normalizeCsvRow(entity, row) {
  const definition = csvImportDefinitions[entity];
  const normalized = {};
  Object.entries(row).forEach(([key, value]) => {
    const trimmedKey = key.trim();
    const targetKey = definition.aliases[trimmedKey] || trimmedKey;
    normalized[targetKey] = String(value ?? "").trim();
  });
  return normalized;
}

async function readCsvFile(file) {
  const text = await file.text();
  const rows = parseCsv(text);
  if (rows.length < 2) {
    throw new Error("CSV 至少需要表头和一行数据");
  }
  const headers = rows[0].map((header) => header.trim());
  return rows
    .slice(1)
    .map((values) =>
      Object.fromEntries(
        headers.map((header, index) => [header, values[index] ?? ""]),
      ),
    );
}

function renderImportResult(result) {
  const errors = result.errors || [];
  $("#csvImportResult").innerHTML = `
    <div class="import-summary ${errors.length ? "has-errors" : ""}">
      <strong>成功 ${escapeHtml(result.created_count)} 行</strong>
      <span>失败 ${escapeHtml(result.failed_count)} 行</span>
    </div>
    ${
      errors.length
        ? `<div class="mini-list">${errors
            .map(
              (error) =>
                `<article><span>第 ${escapeHtml(error.row)} 行</span><p>${escapeHtml(error.error)}</p></article>`,
            )
            .join("")}</div>`
        : ""
    }
  `;
}

async function importCsv(event) {
  event.preventDefault();
  const entity = $("#csvImportEntity").value;
  const file = $("#csvImportFile").files[0];
  if (!file) {
    showMessage("请选择 CSV 文件", true);
    return;
  }
  const rawRows = await readCsvFile(file);
  const rows = rawRows.map((row) => normalizeCsvRow(entity, row));
  const result = await api("/api/import", {
    method: "POST",
    body: JSON.stringify({ entity, rows }),
  });
  renderImportResult(result);
  showMessage(
    `CSV 导入完成：成功 ${result.created_count} 行，失败 ${result.failed_count} 行`,
    Boolean(result.failed_count),
  );
  if (["buildings", "facilities", "activities"].includes(entity)) {
    await reloadAfterWrite(entity);
  } else if (
    state.browseTab === "history" ||
    state.browseTab === "popularQueries"
  ) {
    await loadBrowse();
  }
}

function downloadCsvTemplate() {
  const entity = $("#csvImportEntity").value;
  const definition = csvImportDefinitions[entity];
  const csv = `${definition.headers.join(",")}\r\n${definition.sample.map(csvEscape).join(",")}\r\n`;
  const blob = new Blob([`\uFEFF${csv}`], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${entity}_template.csv`;
  link.click();
  URL.revokeObjectURL(url);
}

function renderAdminMetrics() {
  const metrics = {
    adminCampusCount: state.campuses.length,
    adminBuildingCount: state.buildings.length,
    adminFacilityCount: state.facilities.length,
    adminActivityCount: state.activities.length,
  };
  Object.entries(metrics).forEach(([id, value]) => {
    const node = document.getElementById(id);
    if (node) node.textContent = String(value);
  });
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

function renderInputField(field) {
  const id = `traditional-${field.name}`;
  if (field.type === "select") {
    const options = field.options
      ? field.options.map((value) => [value, value])
      : selectOptions(field.source);
    const optionHtml = [
      field.placeholder
        ? `<option value="">${escapeHtml(field.placeholder)}</option>`
        : "",
      ...options.map(
        ([value, label]) =>
          `<option value="${escapeHtml(value)}">${escapeHtml(label)}</option>`,
      ),
    ].join("");
    return `<label for="${id}">${escapeHtml(field.label)}<select id="${id}" name="${escapeHtml(field.name)}">${optionHtml}</select></label>`;
  }
  return `
    <label for="${id}">
      ${escapeHtml(field.label)}
      <input id="${id}" name="${escapeHtml(field.name)}" type="${escapeHtml(field.type)}" placeholder="${escapeHtml(field.placeholder || "")}" />
    </label>
  `;
}

function renderTraditionalFields() {
  const entity = $("#traditionalEntity").value;
  state.traditionalEntity = entity;
  const definition = traditionalDefinitions[entity];
  $("#traditionalFields").innerHTML = definition.fields
    .map(renderInputField)
    .join("");
}

function setQueryMode(mode) {
  state.queryMode = mode;
  $$(".mode-button").forEach((button) =>
    button.classList.toggle("is-active", button.dataset.queryMode === mode),
  );
  $("#traditionalPane").classList.toggle("hidden", mode !== "traditional");
  $("#naturalPane").classList.toggle("hidden", mode !== "natural");
}

async function runTraditionalQuery(event) {
  if (event) {
    event.preventDefault();
  }
  const form = $("#traditionalQueryForm");
  const payload = formPayload(form);
  const entity = payload.entity;
  delete payload.entity;
  const definition = traditionalDefinitions[entity];
  const result = await api(`${definition.endpoint}${buildQuery(payload)}`);
  renderTable($("#queryResult"), entity, result.items || [], {
    editable: editableEntities.has(entity),
    framed: true,
  });
  showMessage(`传统查询完成，返回 ${(result.items || []).length} 条结果`);
}

async function askNaturalLanguage(event) {
  if (event) {
    event.preventDefault();
  }
  setNaturalQueryLoading(true);
  try {
    const payload = formPayload($("#nlQueryForm"));
    payload.role = "admin";
    const result = await api("/api/nl-query", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    renderNaturalLanguageAnswer(result);
    if (state.browseTab === "history" || state.browseTab === "popularQueries") {
      await loadBrowse();
    }
    showMessage(`自然语言查询完成，返回 ${result.row_count} 条结果`);
  } finally {
    setNaturalQueryLoading(false);
  }
}

function setNaturalQueryLoading(isLoading) {
  const status = $("#nlLoadingStatus");
  const result = $("#queryResult");
  const button = $("#askBtn");
  status?.classList.toggle("is-visible", isLoading);
  status?.setAttribute("aria-hidden", String(!isLoading));
  result?.classList.toggle("is-blurred", isLoading);
  if (button) {
    button.disabled = isLoading;
    button.textContent = isLoading ? "查询中" : "查询";
  }
}

function renderNaturalLanguageAnswer(result) {
  const params =
    result.params && result.params.length
      ? JSON.stringify(result.params, null, 2)
      : "[]";
  $("#queryResult").innerHTML = `
    <div class="answer-box">
      <div class="answer-summary">
        <div><strong>识别意图</strong><br />${escapeHtml(result.title)}</div>
        <div><strong>回答摘要</strong><br />${escapeHtml(result.answer)}</div>
        <div><strong>类别</strong><br />${escapeHtml(result.category)}</div>
        <div><strong>参数</strong><br />${escapeHtml(params)}</div>
      </div>
      <pre>${escapeHtml(result.sql)}</pre>
      <div class="sql-result">${renderRows(result.rows || [])}</div>
    </div>
  `;
}

function renderTable(target, entity, rows, options = {}) {
  if (!rows.length) {
    target.innerHTML = `<div class="empty">没有匹配数据</div>`;
    return;
  }
  const columns = entityColumns[entity];
  const canEdit = options.editable && editableEntities.has(entity);
  const header = columns
    .map(([, label]) => `<th>${escapeHtml(label)}</th>`)
    .join("");
  const editHeader = canEdit ? "<th>操作</th>" : "";
  const body = rows
    .map((row) => {
      const cells = columns
        .map(([key]) => `<td>${escapeHtml(row[key] ?? "")}</td>`)
        .join("");
      const actions = canEdit
        ? `<td><div class="row-actions"><button type="button" data-edit-entity="${entity}" data-edit='${escapeHtml(JSON.stringify(row))}'>编辑</button></div></td>`
        : "";
      return `<tr>${cells}${actions}</tr>`;
    })
    .join("");
  const table = `<table><thead><tr>${header}${editHeader}</tr></thead><tbody>${body}</tbody></table>`;
  target.innerHTML = options.framed
    ? `<div class="table-wrap">${table}</div>`
    : table;
  $$("[data-edit]").forEach((button) => {
    button.addEventListener("click", () =>
      fillEditForm(button.dataset.editEntity, JSON.parse(button.dataset.edit)),
    );
  });
}

function renderRows(rows) {
  if (!rows.length) {
    return `<div class="empty">查询无结果</div>`;
  }
  const keys = Object.keys(rows[0]);
  const header = keys.map((key) => `<th>${escapeHtml(key)}</th>`).join("");
  const body = rows
    .map(
      (row) =>
        `<tr>${keys.map((key) => `<td>${escapeHtml(row[key] ?? "")}</td>`).join("")}</tr>`,
    )
    .join("");
  return `<table><thead><tr>${header}</tr></thead><tbody>${body}</tbody></table>`;
}

function renderDetailRows(items) {
  return `
    <dl class="detail-list">
      ${items
        .map(
          ([label, value]) => `
            <div>
              <dt>${escapeHtml(label)}</dt>
              <dd>${escapeHtml(value ?? "")}</dd>
            </div>
          `,
        )
        .join("")}
    </dl>
  `;
}

function setBrowseSurface(target, mode = "table") {
  target.className = mode === "cards" ? "browse-card-surface" : "table-wrap";
}

function renderQueryLogDetail(row) {
  const target = $("#browseDetail");
  if (!target) return;
  if (!row) {
    target.innerHTML = `<div class="empty">从左侧选择一条查询记录查看完整信息</div>`;
    return;
  }
  target.innerHTML = `
    <div class="detail-heading">
      <span class="badge">${escapeHtml(row.query_category)}</span>
      <strong>查询记录 #${escapeHtml(row.log_id)}</strong>
    </div>
    <p class="detail-main">${escapeHtml(row.query_content)}</p>
    ${renderDetailRows([
      ["查询用户", `${row.user_name}（ID ${row.user_id}）`],
      ["查询时间", formatTime(row.query_time)],
      ["查询类别", row.query_category],
      ["记录编号", row.log_id],
    ])}
  `;
}

function renderQueryLogList(target, rows) {
  setBrowseSurface(target, "cards");
  state.browseRows = rows;
  if (!rows.length) {
    target.innerHTML = `<div class="empty">没有匹配查询记录</div>`;
    return;
  }
  target.innerHTML = `
    <div class="detail-browser">
      <div class="query-card-list" aria-label="查询记录列表">
        ${rows
          .map(
            (row, index) => `
              <button class="query-card ${index === 0 ? "is-active" : ""}" type="button" data-query-detail-index="${index}">
                <span class="badge">${escapeHtml(row.query_category)}</span>
                <span class="query-card-body">
                  <strong>${escapeHtml(previewText(row.query_content, 60))}</strong>
                  <span class="query-card-meta">${escapeHtml(row.user_name)} · ${escapeHtml(formatTime(row.query_time))}</span>
                </span>
              </button>
            `,
          )
          .join("")}
      </div>
      <aside id="browseDetail" class="detail-panel"></aside>
    </div>
  `;
  $$("[data-query-detail-index]").forEach((button) => {
    button.addEventListener("click", () => {
      $$("[data-query-detail-index]").forEach((item) =>
        item.classList.toggle("is-active", item === button),
      );
      renderQueryLogDetail(
        state.browseRows[Number(button.dataset.queryDetailIndex)],
      );
    });
  });
  renderQueryLogDetail(rows[0]);
}

async function renderPopularQueryDetail(row) {
  const target = $("#browseDetail");
  if (!target) return;
  if (!row) {
    target.innerHTML = `<div class="empty">从左侧选择一个热门类别查看详情</div>`;
    return;
  }
  target.innerHTML = `<div class="empty">正在加载 ${escapeHtml(row.query_category)} 的最近查询...</div>`;
  const payload = await api(
    `/api/query-logs${buildQuery({ query_category: row.query_category, limit: 8 })}`,
  );
  const recent = payload.items || [];
  target.innerHTML = `
    <div class="detail-heading">
      <span class="badge">${escapeHtml(row.query_category)}</span>
      <strong>${escapeHtml(row.query_count)} 次查询</strong>
    </div>
    <p class="detail-main">${escapeHtml(row.latest_query || "暂无最近查询")}</p>
    ${renderDetailRows([
      ["最近查询时间", formatTime(row.latest_query_time)],
      ["统计口径", "按 query_log.query_category 聚合"],
      ["查询类别", row.query_category],
    ])}
    <div class="mini-list">
      <strong>最近查询</strong>
      ${
        recent.length
          ? recent
              .map(
                (item) => `
                  <article>
                    <span>${escapeHtml(formatTime(item.query_time))} · ${escapeHtml(item.user_name)}</span>
                    <p>${escapeHtml(item.query_content)}</p>
                  </article>
                `,
              )
              .join("")
          : `<div class="empty">暂无最近查询记录</div>`
      }
    </div>
  `;
}

function renderPopularQueryList(target, rows) {
  setBrowseSurface(target, "cards");
  state.popularQueryRows = rows;
  if (!rows.length) {
    target.innerHTML = `<div class="empty">暂无热门查询统计</div>`;
    return;
  }
  const total = rows.reduce(
    (sum, row) => sum + Number(row.query_count || 0),
    0,
  );
  target.innerHTML = `
    <div class="detail-browser popular-browser">
      <div class="query-card-list" aria-label="热门查询榜单">
        ${rows
          .map((row, index) => {
            const count = Number(row.query_count || 0);
            const percent = total ? Math.round((count / total) * 100) : 0;
            return `
              <button class="query-card rank-card ${index === 0 ? "is-active" : ""}" type="button" data-popular-query-index="${index}">
                <span class="rank-number">#${index + 1}</span>
                <span class="query-card-body">
                  <strong>${escapeHtml(row.query_category)}</strong>
                  <span class="query-card-meta">${escapeHtml(count)} 次 · 最近：${escapeHtml(previewText(row.latest_query, 26))}</span>
                </span>
                <i style="--bar:${percent}%"></i>
              </button>
            `;
          })
          .join("")}
      </div>
      <aside id="browseDetail" class="detail-panel"></aside>
    </div>
  `;
  $$("[data-popular-query-index]").forEach((button) => {
    button.addEventListener("click", () => {
      $$("[data-popular-query-index]").forEach((item) =>
        item.classList.toggle("is-active", item === button),
      );
      renderPopularQueryDetail(
        state.popularQueryRows[Number(button.dataset.popularQueryIndex)],
      ).catch((error) => showMessage(error.message, true));
    });
  });
  renderPopularQueryDetail(rows[0]).catch((error) =>
    showMessage(error.message, true),
  );
}

function browseFilterField(field) {
  if (field.type === "select") {
    const options = selectOptions(field.source);
    return `
      <label>
        ${escapeHtml(field.label)}
        <select name="${escapeHtml(field.name)}">
          <option value="">${escapeHtml(field.placeholder || "全部")}</option>
          ${options.map(([value, label]) => `<option value="${escapeHtml(value)}">${escapeHtml(label)}</option>`).join("")}
        </select>
      </label>
    `;
  }
  return `
    <label>
      ${escapeHtml(field.label)}
      <input name="${escapeHtml(field.name)}" type="${escapeHtml(field.type)}" value="${escapeHtml(field.value || "")}" placeholder="${escapeHtml(field.placeholder || "")}" />
    </label>
  `;
}

function renderBrowseFilters() {
  const form = $("#browseFilterForm");
  if (state.browseTab === "history") {
    form.classList.remove("compact-only");
    form.innerHTML = [
      browseFilterField({
        name: "q",
        label: "关键词",
        type: "search",
        placeholder: "内容、类别或用户",
      }),
      browseFilterField({
        name: "query_category",
        label: "类别",
        type: "select",
        source: "queryCategories",
        placeholder: "全部类别",
      }),
      browseFilterField({ name: "user_id", label: "用户 ID", type: "number" }),
      browseFilterField({
        name: "limit",
        label: "数量",
        type: "number",
        value: "20",
      }),
      `<div class="actions"><button type="submit">浏览</button></div>`,
    ].join("");
    return;
  }
  if (
    state.browseTab === "popularQueries" ||
    state.browseTab === "popularActivities"
  ) {
    form.classList.add("compact-only");
    form.innerHTML = [
      browseFilterField({
        name: "limit",
        label: "数量",
        type: "number",
        value: "10",
      }),
      `<div class="actions"><button type="submit">浏览</button></div>`,
    ].join("");
    return;
  }
  if (state.browseTab === "activityParticipants") {
    form.classList.remove("compact-only");
    form.innerHTML = [
      browseFilterField({
        name: "activity_id",
        label: "活动",
        type: "select",
        source: "activities",
        placeholder: "请选择活动",
      }),
      browseFilterField({
        name: "q",
        label: "用户关键词",
        type: "search",
        placeholder: "姓名或院系",
      }),
      browseFilterField({
        name: "status",
        label: "参与状态",
        type: "search",
        placeholder: "待参加 / 已签到 / 已完成",
      }),
      browseFilterField({
        name: "limit",
        label: "数量",
        type: "number",
        value: "50",
      }),
      `<div class="actions"><button type="submit">查看参与用户</button></div>`,
    ].join("");
    const activitySelect = form.elements.activity_id;
    if (activitySelect && state.activities.length) {
      activitySelect.value = state.activities[0].activity_id;
    }
    return;
  }
  if (state.browseTab === "data") {
    form.classList.remove("compact-only");
    form.innerHTML = `
      <label>
        数据对象
        <select name="entity" id="browseEntity">
          <option value="campuses">校区</option>
          <option value="buildings">建筑</option>
          <option value="facilities">设施</option>
          <option value="courses">课程</option>
          <option value="activities">活动</option>
        </select>
      </label>
      ${browseFilterField({ name: "q", label: "关键词", type: "search" })}
      <div class="actions"><button type="submit">浏览</button></div>
    `;
    $("#browseEntity").value = state.browseEntity;
    return;
  }
  form.classList.add("compact-only");
  form.innerHTML = `<div class="actions"><button type="submit">刷新 SQL 展示</button></div>`;
}

async function loadBrowse(event) {
  if (event) {
    event.preventDefault();
  }
  const form = $("#browseFilterForm");
  const params = formPayload(form);
  const target = $("#browseContent");

  if (state.browseTab === "history") {
    const payload = await api(`/api/query-logs${buildQuery(params)}`);
    renderQueryLogList(target, payload.items || []);
    return;
  }
  if (state.browseTab === "popularQueries") {
    const payload = await api(
      `/api/insights/popular-queries${buildQuery(params)}`,
    );
    renderPopularQueryList(target, payload.items || []);
    return;
  }
  if (state.browseTab === "popularActivities") {
    setBrowseSurface(target, "table");
    const payload = await api(
      `/api/insights/popular-activities${buildQuery(params)}`,
    );
    renderTable(target, "popularActivities", payload.items || []);
    return;
  }
  if (state.browseTab === "activityParticipants") {
    setBrowseSurface(target, "table");
    const activityId = params.activity_id || state.activities[0]?.activity_id;
    if (!activityId) {
      target.innerHTML = `<div class="empty">暂无活动数据</div>`;
      return;
    }
    delete params.activity_id;
    const payload = await api(
      `/api/admin/activities/${activityId}/participants${buildQuery(params)}`,
    );
    renderTable(target, "activityParticipants", payload.items || []);
    return;
  }
  if (state.browseTab === "data") {
    setBrowseSurface(target, "table");
    const entity = params.entity || state.browseEntity;
    state.browseEntity = entity;
    delete params.entity;
    const payload = await api(`/api/${entity}${buildQuery(params)}`);
    renderTable(target, entity, payload.items || [], {
      editable: editableEntities.has(entity),
    });
    return;
  }
  await loadSqlExamples(target);
}

async function loadSqlExamples(target = $("#browseContent")) {
  setBrowseSurface(target, "cards");
  const payload = await api("/api/sql-examples");
  const items = payload.items || [];
  target.innerHTML = `
    <div class="sql-overview">
      <strong>关键 SQL 验收</strong>
      <span>${escapeHtml(items.length)} 条查询 · 实时执行当前数据库数据</span>
    </div>
    ${items
      .map((item, index) => {
        const rows = item.rows || [];
        const tables = Array.isArray(item.tables) ? item.tables : [];
        return `
        <article class="sql-item">
          <div class="sql-heading">
            <div>
              <span class="sql-index">SQL ${index + 1}</span>
              <strong>${escapeHtml(item.title)}</strong>
            </div>
            <span class="badge">${escapeHtml(item.group || "关键查询")}</span>
          </div>
          <div class="sql-summary">
            <p>${escapeHtml(item.purpose || "")}</p>
            <dl>
              <div><dt>业务问题</dt><dd>${escapeHtml(item.business_question || item.title)}</dd></div>
              <div><dt>涉及表</dt><dd>${escapeHtml(tables.join("、") || "-")}</dd></div>
              <div><dt>结果行数</dt><dd>${escapeHtml(rows.length)}</dd></div>
            </dl>
          </div>
          <pre>${escapeHtml(item.sql)}</pre>
          <div class="sql-result">${renderRows(rows)}</div>
        </article>
      `;
      })
      .join("")}
  `;
}

function setBrowseTab(tab) {
  state.browseTab = tab;
  $$(".browse-tabs .tab").forEach((button) =>
    button.classList.toggle("is-active", button.dataset.browse === tab),
  );
  renderBrowseFilters();
}

function showForm(formId) {
  $$(".maintenance-tabs .tab").forEach((tab) =>
    tab.classList.toggle("is-active", tab.dataset.form === formId),
  );
  $$(".crud-form").forEach((form) =>
    form.classList.toggle("hidden", form.id !== formId),
  );
}

function setFormValues(form, values) {
  Object.entries(values).forEach(([key, value]) => {
    const field = form.elements[key];
    if (!field) return;
    if (field.type === "datetime-local" && value) {
      field.value = String(value).slice(0, 16).replace(" ", "T");
    } else {
      field.value = value ?? "";
    }
  });
}

function fillEditForm(entity, row) {
  switchAdminView("maintain");
  if (entity === "buildings") {
    showForm("buildingForm");
    setFormValues($("#buildingForm"), row);
  } else if (entity === "facilities") {
    showForm("facilityForm");
    setFormValues($("#facilityForm"), row);
  } else if (entity === "activities") {
    showForm("activityForm");
    setFormValues($("#activityForm"), row);
  }
  showMessage("已载入记录，可修改后保存");
}

async function saveBuilding(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const payload = formPayload(form);
  const id = payload.building_id;
  delete payload.building_id;
  await api(id ? `/api/buildings/${id}` : "/api/buildings", {
    method: id ? "PUT" : "POST",
    body: JSON.stringify(payload),
  });
  showMessage(id ? "建筑已更新" : "建筑已新增");
  form.reset();
  await reloadAfterWrite("buildings");
}

async function saveFacility(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const payload = formPayload(form);
  const id = payload.facility_id;
  delete payload.facility_id;
  await api(id ? `/api/facilities/${id}` : "/api/facilities", {
    method: id ? "PUT" : "POST",
    body: JSON.stringify(payload),
  });
  showMessage(id ? "设施已更新" : "设施已新增");
  form.reset();
  await reloadAfterWrite("facilities");
}

async function saveActivity(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const payload = formPayload(form);
  const id = payload.activity_id;
  delete payload.activity_id;
  await api(id ? `/api/activities/${id}` : "/api/activities", {
    method: id ? "PUT" : "POST",
    body: JSON.stringify(payload),
  });
  showMessage(id ? "活动已更新" : "活动已新增");
  form.reset();
  await reloadAfterWrite("activities");
}

async function saveQueryLog(event) {
  event.preventDefault();
  const payload = formPayload(event.currentTarget);
  const result = await api("/api/query-log", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  showMessage(`查询记录已写入，log_id=${result.item.log_id}`);
  event.currentTarget.reset();
  if (state.browseTab === "history" || state.browseTab === "popularQueries") {
    await loadBrowse();
  }
}

async function reloadAfterWrite(entity) {
  await loadReferenceData();
  $("#traditionalEntity").value = entity;
  renderTraditionalFields();
  await runTraditionalQuery();
  if (state.browseTab === "data") {
    state.browseEntity = entity;
    renderBrowseFilters();
    await loadBrowse();
  } else if (state.browseTab === "activityParticipants" && entity === "activities") {
    renderBrowseFilters();
    await loadBrowse();
  }
}

async function deleteCurrent(kind) {
  const formMap = {
    building: ["buildingForm", "building_id", "/api/buildings/", "buildings", "建筑"],
    facility: ["facilityForm", "facility_id", "/api/facilities/", "facilities", "设施"],
    activity: ["activityForm", "activity_id", "/api/activities/", "activities", "活动"],
  };
  const [formId, idKey, endpoint, entity, label] = formMap[kind];
  const form = $(`#${formId}`);
  const id = form.elements[idKey].value;
  if (!id) {
    showMessage("请先从表格中选择一条记录", true);
    return;
  }
  showMessage(`正在删除${label}...`);
  await api(`${endpoint}${id}`, { method: "DELETE" });
  showMessage(`${label}已删除`);
  form.reset();
  await reloadAfterWrite(entity);
}

function bindEvents() {
  $$("[data-admin-view]").forEach((button) => {
    button.addEventListener("click", () =>
      switchAdminView(button.dataset.adminView),
    );
  });
  window.addEventListener("hashchange", () =>
    switchAdminView(window.location.hash.slice(1), { updateHash: false }),
  );
  $$(".mode-button").forEach((button) => {
    button.addEventListener("click", () =>
      setQueryMode(button.dataset.queryMode),
    );
  });
  $("#traditionalEntity").addEventListener("change", () => {
    renderTraditionalFields();
    runTraditionalQuery().catch((error) => showMessage(error.message, true));
  });
  $("#traditionalQueryForm").addEventListener("submit", (event) =>
    runTraditionalQuery(event).catch((error) =>
      showMessage(error.message, true),
    ),
  );
  $("#clearTraditionalBtn").addEventListener("click", () => {
    $("#traditionalQueryForm").reset();
    renderTraditionalFields();
    runTraditionalQuery().catch((error) => showMessage(error.message, true));
  });
  $("#nlQueryForm").addEventListener("submit", (event) =>
    askNaturalLanguage(event).catch((error) =>
      showMessage(error.message, true),
    ),
  );
  $$("#nlQueryForm [data-question]").forEach((button) => {
    button.addEventListener("click", () => {
      const textarea = $("#nlQuestion");
      if (textarea) textarea.value = button.dataset.question;
      askNaturalLanguage().catch((error) => showMessage(error.message, true));
    });
  });
  $$(".browse-tabs .tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      setBrowseTab(tab.dataset.browse);
      loadBrowse().catch((error) => showMessage(error.message, true));
    });
  });
  $("#refreshBrowseBtn").addEventListener("click", () =>
    loadBrowse().catch((error) => showMessage(error.message, true)),
  );
  $("#browseFilterForm").addEventListener("submit", (event) =>
    loadBrowse(event).catch((error) => showMessage(error.message, true)),
  );
  $("#browseFilterForm").addEventListener("change", (event) => {
    if (event.target.name === "entity") {
      loadBrowse().catch((error) => showMessage(error.message, true));
    }
  });
  $$(".maintenance-tabs .tab").forEach((tab) =>
    tab.addEventListener("click", () => showForm(tab.dataset.form)),
  );
  $$("[data-reset]").forEach((button) => {
    button.addEventListener("click", () => {
      $(`#${button.dataset.reset}`).reset();
      showMessage("表单已清空");
    });
  });
  $$("[data-delete]").forEach((button) => {
    button.addEventListener("click", () =>
      deleteCurrent(button.dataset.delete).catch((error) =>
        showMessage(error.message, true),
      ),
    );
  });
  $("#buildingForm").addEventListener("submit", (event) =>
    saveBuilding(event).catch((error) => showMessage(error.message, true)),
  );
  $("#facilityForm").addEventListener("submit", (event) =>
    saveFacility(event).catch((error) => showMessage(error.message, true)),
  );
  $("#activityForm").addEventListener("submit", (event) =>
    saveActivity(event).catch((error) => showMessage(error.message, true)),
  );
  $("#queryLogForm").addEventListener("submit", (event) =>
    saveQueryLog(event).catch((error) => showMessage(error.message, true)),
  );
  $("#csvImportForm")?.addEventListener("submit", (event) =>
    importCsv(event).catch((error) => showMessage(error.message, true)),
  );
  $("#csvImportEntity")?.addEventListener("change", updateCsvImportHint);
  $("#downloadCsvTemplateBtn")?.addEventListener("click", downloadCsvTemplate);
}

async function init() {
  bindEvents();
  switchAdminView(window.location.hash.slice(1), {
    updateHash: false,
    scroll: false,
  });
  updateCsvImportHint();
  await checkHealth();
  await loadReferenceData();
  renderTraditionalFields();
  renderBrowseFilters();
  await runTraditionalQuery();
  await loadBrowse();
}

init().catch((error) => showMessage(error.message, true));
