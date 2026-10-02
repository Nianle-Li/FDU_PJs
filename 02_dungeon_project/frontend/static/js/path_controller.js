/**
 * 路径控制器 - 处理路径搜索、高亮和展示
 */

import * as apiClient from "./api_client.js";
import {
  highlightPath,
  clearPathHighlight,
  highlightMultiplePaths,
} from "./map_renderer.js";
import * as logger from "./logger.js";

// 模块级别的地图锁定状态（避免闭包问题）
let _savedMapStyles = null;
let _savedParentStyles = null;

/**
 * 锁定地图和父容器的尺寸，防止模态打开时布局偏移
 */
function lockMapAndParentSize() {
  try {
    const mapContainer = document.getElementById("map-container");
    const rightPanel = document.querySelector(".right-panel");
    const mainContainer = document.querySelector(".main-container");

    if (mapContainer) {
      const cs = window.getComputedStyle(mapContainer);
      logger.debug("[lockMapAndParentSize] before lock", {
        innerWidth: window.innerWidth,
        clientWidth: document.documentElement.clientWidth,
        mapRect: `${cs.width} x ${cs.height}`,
      });
      _savedMapStyles = {
        width: mapContainer.style.width,
        height: mapContainer.style.height,
        minWidth: mapContainer.style.minWidth,
        minHeight: mapContainer.style.minHeight,
        maxWidth: mapContainer.style.maxWidth,
        maxHeight: mapContainer.style.maxHeight,
        position: mapContainer.style.position,
        flex: mapContainer.style.flex,
      };
      // 锁定地图容器的像素尺寸
      mapContainer.style.width = cs.width;
      mapContainer.style.height = cs.height;
      mapContainer.style.minWidth = cs.width;
      mapContainer.style.minHeight = cs.height;
      mapContainer.style.maxWidth = cs.width;
      mapContainer.style.maxHeight = cs.height;
      mapContainer.style.position = "relative";
      mapContainer.style.flex = "none";
    }

    // 同时锁定父容器尺寸
    _savedParentStyles = {};
    if (rightPanel) {
      const rcs = window.getComputedStyle(rightPanel);
      _savedParentStyles.rightPanel = {
        width: rightPanel.style.width,
        height: rightPanel.style.height,
        minWidth: rightPanel.style.minWidth,
        minHeight: rightPanel.style.minHeight,
        maxWidth: rightPanel.style.maxWidth,
        maxHeight: rightPanel.style.maxHeight,
        flex: rightPanel.style.flex,
      };
      rightPanel.style.width = rcs.width;
      rightPanel.style.height = rcs.height;
      rightPanel.style.minWidth = rcs.width;
      rightPanel.style.minHeight = rcs.height;
      rightPanel.style.maxWidth = rcs.width;
      rightPanel.style.maxHeight = rcs.height;
      rightPanel.style.flex = "none";
    }
    if (mainContainer) {
      const mcs = window.getComputedStyle(mainContainer);
      _savedParentStyles.mainContainer = {
        width: mainContainer.style.width,
        height: mainContainer.style.height,
        minWidth: mainContainer.style.minWidth,
        minHeight: mainContainer.style.minHeight,
        maxWidth: mainContainer.style.maxWidth,
        maxHeight: mainContainer.style.maxHeight,
      };
      mainContainer.style.width = mcs.width;
      mainContainer.style.height = mcs.height;
      mainContainer.style.minWidth = mcs.width;
      mainContainer.style.minHeight = mcs.height;
      mainContainer.style.maxWidth = mcs.width;
      mainContainer.style.maxHeight = mcs.height;
    }
  } catch (e) {
    logger.warn("Failed to lock map size:", e);
  }
}

/**
 * 恢复地图和父容器的原始样式
 */
function restoreMapAndParentSize() {
  try {
    const mapContainer = document.getElementById("map-container");
    const rightPanel = document.querySelector(".right-panel");
    const mainContainer = document.querySelector(".main-container");

    if (mapContainer && _savedMapStyles) {
      logger.debug("[restoreMapAndParentSize] before restore", {
        innerWidth: window.innerWidth,
        clientWidth: document.documentElement.clientWidth,
        mapSaved: _savedMapStyles,
      });
      mapContainer.style.width = _savedMapStyles.width || "";
      mapContainer.style.height = _savedMapStyles.height || "";
      mapContainer.style.minWidth = _savedMapStyles.minWidth || "";
      mapContainer.style.minHeight = _savedMapStyles.minHeight || "";
      mapContainer.style.maxWidth = _savedMapStyles.maxWidth || "";
      mapContainer.style.maxHeight = _savedMapStyles.maxHeight || "";
      mapContainer.style.position = _savedMapStyles.position || "";
      mapContainer.style.flex = _savedMapStyles.flex || "";
      _savedMapStyles = null;
    }

    if (_savedParentStyles) {
      if (rightPanel && _savedParentStyles.rightPanel) {
        rightPanel.style.width = _savedParentStyles.rightPanel.width || "";
        rightPanel.style.height = _savedParentStyles.rightPanel.height || "";
        rightPanel.style.minWidth =
          _savedParentStyles.rightPanel.minWidth || "";
        rightPanel.style.minHeight =
          _savedParentStyles.rightPanel.minHeight || "";
        rightPanel.style.maxWidth =
          _savedParentStyles.rightPanel.maxWidth || "";
        rightPanel.style.maxHeight =
          _savedParentStyles.rightPanel.maxHeight || "";
        rightPanel.style.flex = _savedParentStyles.rightPanel.flex || "";
      }
      if (mainContainer && _savedParentStyles.mainContainer) {
        mainContainer.style.width =
          _savedParentStyles.mainContainer.width || "";
        mainContainer.style.height =
          _savedParentStyles.mainContainer.height || "";
        mainContainer.style.minWidth =
          _savedParentStyles.mainContainer.minWidth || "";
        mainContainer.style.minHeight =
          _savedParentStyles.mainContainer.minHeight || "";
        mainContainer.style.maxWidth =
          _savedParentStyles.mainContainer.maxWidth || "";
        mainContainer.style.maxHeight =
          _savedParentStyles.mainContainer.maxHeight || "";
      }
      _savedParentStyles = null;
    }
  } catch (e) {
    logger.warn("Failed to restore map size:", e);
  }
}

// 安全的模态显示：优先使用 window.bootstrap.Modal；若不存在，使用简单回退实现
function showModalById(id) {
  const el = document.getElementById(id);
  if (!el) return null;

  if (window.bootstrap && typeof window.bootstrap.Modal === "function") {
    // Use Bootstrap lifecycle events so we lock *after* the modal is fully shown
    const m = new window.bootstrap.Modal(el);

    const onShown = () => {
      try {
        lockMapAndParentSize();
      } catch (e) {
        logger.warn("Failed to lock map size on modal shown:", e);
      }
      el.removeEventListener("shown.bs.modal", onShown);
    };

    const onHidden = () => {
      try {
        if (!_suppressRestoreOnHidden) {
          restoreMapAndParentSize();
        } else {
          logger.log("restore suppressed on modal hidden (highlight flow)");
        }
      } catch (e) {
        logger.warn("Failed to restore map size on modal hidden:", e);
      }
      // ensure shown handler is cleaned up in any case
      el.removeEventListener("shown.bs.modal", onShown);
      el.removeEventListener("hidden.bs.modal", onHidden);
    };

    // 在 modal 开始显示时记录网络视图（以便在尺寸变化后恢复原位）
    let _savedView = null;
    const onShow = () => {
      try {
        const net = window._dungeonNetwork;
        if (net && typeof net.getViewPosition === "function") {
          _savedView = {
            position: net.getViewPosition(),
            scale:
              typeof net.getScale === "function" ? net.getScale() : undefined,
          };
        }
      } catch (e) {
        // ignore
      }
    };

    el.addEventListener("show.bs.modal", onShow);

    el.addEventListener("shown.bs.modal", onShown);
    el.addEventListener("hidden.bs.modal", onHidden);

    m.show();

    // 如果出现偏移，尝试在 modal 完全显示后恢复视图（短延迟以等待布局稳定）
    el.addEventListener("shown.bs.modal", function _restoreViewOnce() {
      try {
        if (
          _savedView &&
          window._dungeonNetwork &&
          typeof window._dungeonNetwork.moveTo === "function"
        ) {
          setTimeout(() => {
            try {
              window._dungeonNetwork.moveTo({
                position: _savedView.position,
                scale: _savedView.scale,
                animation: { duration: 0 },
              });
            } catch (e) {
              // ignore
            }
          }, 10);
        }
      } catch (e) {}
      el.removeEventListener("shown.bs.modal", _restoreViewOnce);
    });

    return m;
  }

  // Fallback: 手动显示模态（简易，支持关闭后移除 backdrop）
  // 在显示回退模态前，记录当前视图并锁定页面滚动以补偿滚动条宽度，避免布局抖动（例如地图偏移）
  let _savedView = null;
  try {
    const net = window._dungeonNetwork;
    if (net && typeof net.getViewPosition === "function") {
      _savedView = {
        position: net.getViewPosition(),
        scale: typeof net.getScale === "function" ? net.getScale() : undefined,
      };
    }
  } catch (e) {
    // ignore
  }

  const prevBodyOverflow = document.body.style.overflow;
  const prevBodyPaddingRight = document.body.style.paddingRight;
  const scrollBarWidth =
    window.innerWidth - document.documentElement.clientWidth;
  if (scrollBarWidth > 0) {
    document.body.style.paddingRight = `${scrollBarWidth}px`;
  }
  document.body.style.overflow = "hidden";
  // 锁定地图尺寸，防止由于滚动/布局变化导致地图重排或偏移
  lockMapAndParentSize();

  el.classList.add("show");
  el.style.display = "block";
  el.setAttribute("aria-modal", "true");
  el.removeAttribute("aria-hidden");

  const backdrop = document.createElement("div");
  backdrop.className = "modal-backdrop fade show";
  backdrop.id = `bs-backdrop-${id}`;
  document.body.appendChild(backdrop);

  // 恢复视图位置，短延迟以等待布局稳定
  if (
    _savedView &&
    window._dungeonNetwork &&
    typeof window._dungeonNetwork.moveTo === "function"
  ) {
    setTimeout(() => {
      try {
        window._dungeonNetwork.moveTo({
          position: _savedView.position,
          scale: _savedView.scale,
          animation: { duration: 0 },
        });
      } catch (e) {
        // ignore
      }
    }, 10);
  }

  // 添加关闭逻辑：绑定 modal 内带有 data-bs-dismiss="modal" 的元素
  const dismissButtons = Array.from(
    el.querySelectorAll('[data-bs-dismiss="modal"]')
  );

  function cleanup() {
    // 移除 backdrop
    const b = document.getElementById(`bs-backdrop-${id}`);
    if (b) b.remove();
    // 移除事件监听
    dismissButtons.forEach((btn) =>
      btn.removeEventListener("click", onDismiss)
    );
    backdrop.removeEventListener("click", onDismiss);
    document.removeEventListener("keydown", onKeyDown);
    // 恢复 body 样式，解除滚动锁定以及滚动条补偿
    try {
      document.body.style.overflow = prevBodyOverflow || "";
      document.body.style.paddingRight = prevBodyPaddingRight || "";
    } catch (e) {
      // ignore
    }
    // 恢复地图样式
    try {
      if (!_suppressRestoreOnHidden) {
        restoreMapAndParentSize();
      } else {
        logger.log(
          "restore suppressed on fallback modal cleanup (highlight flow)"
        );
      }
    } catch (e) {
      // ignore
    }
  }

  function onDismiss(e) {
    // 隐藏 modal
    el.classList.remove("show");
    el.style.display = "none";
    el.setAttribute("aria-hidden", "true");
    cleanup();
  }

  // 绑定事件
  dismissButtons.forEach((btn) => btn.addEventListener("click", onDismiss));
  backdrop.addEventListener("click", onDismiss);
  function onKeyDown(e) {
    if (e.key === "Escape" || e.key === "Esc") onDismiss();
  }
  document.addEventListener("keydown", onKeyDown);

  return {
    _fallback: true,
    hide() {
      onDismiss();
    },
  };
}

// 当前存储的路径数据
let currentPathData = null;
let currentAllPaths = null;
// 当前地图上被高亮的路径（用于实现最多一条高亮）
let currentHighlightedPath = null;
// 当我们从模态内部触发高亮时，隐藏模态会触发 hidden 事件并恢复地图样式，
// 使用此标志可以抑制在 modal hidden 时立即恢复样式（由 safeHighlight 负责恢复）
let _suppressRestoreOnHidden = false;

/**
 * 搜索最短路径并高亮显示
 * @param {number} from - 起始房间
 * @param {number} to - 目标房间
 * @param {number} playerPower - 玩家武力值
 */
export async function searchShortestPath(from, to, playerPower = 10) {
  try {
    logger.log(`🔍 搜索最短路径: ${from} → ${to}`);

    // 调用 API
    const result = await apiClient.getShortestPath({
      from,
      to,
      player_power: playerPower,
      details: true,
    });

    if (!result || !result.path) {
      alert("未找到路径！");
      return null;
    }

    logger.log("✅ 最短路径:", result);

    // 存储当前路径数据
    currentPathData = result;

    // 高亮显示路径（使用安全高亮以避免布局抖动）
    safeHighlight(result.path, "#FFD700", 10);

    // 渲染到左侧面板
    try {
      renderShortestToPanel(result);
    } catch (e) {
      logger.warn(e);
    }

    // 显示路径详情
    showPathDetails(result);

    return result;
  } catch (error) {
    logger.error("❌ 搜索最短路径失败:", error);
    alert(`搜索失败: ${error.message}`);
    return null;
  }
}

/**
 * 搜索所有可行路径并按价值排序
 * @param {number} from - 起始房间
 * @param {number} to - 目标房间
 * @param {number} playerPower - 玩家武力值
 * @param {number} limit - 返回路径数量限制（默认5，显示前5名）
 */
export async function searchAllRankedPaths(
  from,
  to,
  playerPower = 10,
  limit = 5
) {
  try {
    logger.log(`🔍 搜索所有可行路径: ${from} → ${to} (显示前${limit}名)`);

    // 调用 API
    const result = await fetch(
      `/api/path/all?from=${from}&to=${to}&player_power=${playerPower}&limit=${limit}&details=false`
    ).then((r) => r.json());

    if (!result || !result.paths || result.paths.length === 0) {
      alert("未找到可行路径！");
      return null;
    }

    logger.log(
      `✅ 找到 ${result.total_count} 条可行路径，显示战利品价值前 ${result.returned_count} 名`
    );

    // 存储当前路径数据（不自动高亮，用户需手动点击“🔦 高亮此路径”）
    currentAllPaths = result;

    // 渲染到左侧面板
    try {
      renderAllPathsToPanel(result);
    } catch (e) {
      logger.warn(e);
    }

    // 显示所有路径列表（用户点击“🔦 高亮此路径”以在地图上高亮）
    showAllPathsList(result);

    return result;
  } catch (error) {
    logger.error("❌ 搜索所有路径失败:", error);
    alert(`搜索失败: ${error.message}`);
    return null;
  }
}

/**
 * 显示单条路径的详情（在模态框中）
 */
function showPathDetails(pathData) {
  const title = document.getElementById("pathModalTitle");
  const body = document.getElementById("pathModalBody");

  const { path, length, details } = pathData;

  title.textContent = `🎯 最短路径 (${length} 步)`;

  if (!details) {
    body.innerHTML = `
      <div class="alert alert-info">
        <strong>路径:</strong> ${path.join(" → ")}
      </div>
    `;
    return;
  }

  // 构建详细信息 HTML
  let html = `
    <div class="mb-4">
      <h5 style="font-size: 36px">📊 路径概览</h5>
      <div style="background: rgba(0,0,0,0.3); padding: 20px; border-radius: 10px; margin-bottom: 20px">
        <div style="font-size: 32px; line-height: 1.8">
          <strong>路径:</strong> ${path.join(" → ")}<br>
          <strong>探索次数:</strong> ${length}<br>
          <strong>总战利品价值:</strong> ${details.total_treasure_value} 💎<br>
          <strong>总武力提升:</strong> +${details.total_power_boost} ⚔️<br>
          <strong>最终武力:</strong> ${details.final_power} 💪<br>
          <strong>可行性:</strong> ${
            details.feasible
              ? '<span style="color: #00ff00">✅ 可行</span>'
              : '<span style="color: #ff0000">❌ 不可行</span>'
          }
        </div>
      </div>
    </div>

    <div class="mb-4">
      <h5 style="font-size: 36px">🗺️ 逐步详情</h5>
      <div style="max-height: 500px; overflow-y: auto">
  `;

  // 逐步详情
  if (details.rooms_info && details.rooms_info.length > 0) {
    details.rooms_info.forEach((room, index) => {
      const stepNum = index;
      const stepClass = room.combat_result === "defeat" ? "danger" : "dark";

      html += `
        <div class="card mb-3" style="background: rgba(0,0,0,0.3); border: 2px solid #9b7545">
          <div class="card-header" style="background: rgba(${
            room.combat_result === "defeat" ? "255,0,0" : "0,100,0"
          },0.3); font-size: 32px">
            <strong>步骤 ${stepNum}: 房间 ${room.id}</strong>
            <span class="badge bg-${stepClass}" style="float: right; font-size: 28px">
              武力: ${room.power_before} → ${room.power_after}
            </span>
          </div>
          <div class="card-body" style="font-size: 30px; line-height: 1.8">
      `;

      // 怪物信息
      if (room.monster) {
        const resultIcon =
          room.combat_result === "victory"
            ? "✅"
            : room.combat_result === "defeat"
            ? "❌"
            : "";
        html += `
          <div style="margin-bottom: 10px">
            <strong>${resultIcon} 怪物:</strong> ${room.monster.name} 
            (武力 ${room.monster.power}${
          room.monster.is_boss ? " 👑 BOSS" : ""
        })
          </div>
        `;
      }

      // 宝箱信息
      if (room.treasure) {
        html += `
          <div style="color: #FFD700">
            <strong>💎 宝箱:</strong> ${room.treasure.name} 
            (武力 +${room.treasure.value})
          </div>
        `;
      }

      if (!room.monster && !room.treasure) {
        html += `<div style="color: #999">空房间</div>`;
      }

      html += `
          </div>
        </div>
      `;
    });
  }

  html += `
      </div>
    </div>

    <div>
      <h5 style="font-size: 36px">📝 战斗日志</h5>
      <div style="background: rgba(0,0,0,0.5); padding: 20px; border-radius: 10px; max-height: 400px; overflow-y: auto">
        <pre style="color: #ffe8c0; font-size: 26px; margin: 0; white-space: pre-wrap">${details.combat_log.join(
          "\n"
        )}</pre>
      </div>
    </div>
  `;

  body.innerHTML = html;

  // Show modal after content is ready to avoid layout shift
  showModalById("pathModal");
}

/**
 * 显示所有路径列表（在模态框中）
 */
function showAllPathsList(pathsData) {
  const title = document.getElementById("pathModalTitle");
  const body = document.getElementById("pathModalBody");

  const { paths, total_count, returned_count } = pathsData;

  title.textContent = `📊 战利品价值排行榜 (共${total_count}条路径，显示前${returned_count}名)`;

  let html = `
    <div class="alert alert-info" style="font-size: 30px">
      <strong>说明:</strong> 显示战利品总价值<strong>排名前${returned_count}的路线</strong>（按价值从高到低排序）。
      点击每条卡片的 <strong>🔦 高亮此路径</strong> 按钮在地图上高亮对应路线；每次地图上最多高亮一条路径。
    </div>

    <div style="max-height: 600px; overflow-y: auto">
  `;

  paths.forEach((pathInfo, index) => {
    const rank = index + 1;
    const medal =
      rank === 1 ? "🥇" : rank === 2 ? "🥈" : rank === 3 ? "🥉" : `${rank}.`;
    const color =
      rank === 1
        ? "#FFD700"
        : rank === 2
        ? "#FF6B6B"
        : rank === 3
        ? "#4ECDC4"
        : "#999";

    html += `
      <div class="card mb-3" style="background: rgba(0,0,0,0.3); border: 3px solid ${color}">
        <div class="card-header" style="background: rgba(0,0,0,0.5); font-size: 34px">
          <strong style="color: ${color}">${medal} 路径 ${rank}</strong>
          <span class="badge bg-warning text-dark" style="float: right; font-size: 30px">
            💎 价值: ${pathInfo.value}
          </span>
        </div>
        <div class="card-body" style="font-size: 30px">
          <div style="margin-bottom: 10px">
            <strong>路径:</strong> ${pathInfo.path.join(" → ")}
          </div>
          <div style="display: flex; gap: 30px; flex-wrap: wrap">
            <span>📏 长度: ${pathInfo.length} 步</span>
            <span>⚔️ 武力提升: +${pathInfo.power_boost}</span>
            <span>💎 总价值: ${pathInfo.value}</span>
          </div>
          <button 
            class="btn btn-sm btn-outline-light mt-3"
            style="font-size: 28px"
            onclick="window.highlightSinglePathFromModal(${JSON.stringify(
              pathInfo.path
            ).replace(/"/g, "'")}, '${color}')">
            🔦 高亮此路径
          </button>
        </div>
      </div>
    `;
  });

  html += `</div>`;

  body.innerHTML = html;

  // Show modal after content is ready to avoid layout shift
  showModalById("pathModal");
}

/**
 * 清除路径高亮
 */
export function clearPath() {
  clearPathHighlight();
  currentPathData = null;
  currentAllPaths = null;
  currentHighlightedPath = null;

  // 清空面板显示
  const shortestDiv = document.getElementById("lp-shortest");
  const pathsList = document.getElementById("lp-paths-list");
  const detailsBtn = document.getElementById("lp-show-short-details");

  if (shortestDiv) shortestDiv.innerHTML = "Not generated";
  if (pathsList)
    pathsList.innerHTML =
      '<div class="text-muted">No paths yet. Click "Shortest Path" or "Rank Paths".</div>';
  if (detailsBtn) detailsBtn.style.display = "none";

  logger.log("✅ 已清除路径高亮");
}

/**
 * 获取当前路径数据（用于其他模块访问）
 */
export function getCurrentPathData() {
  return currentPathData;
}

export function getCurrentAllPaths() {
  return currentAllPaths;
}

/**
 * 渲染最短路径到左侧面板
 */
export function renderShortestToPanel(pathData) {
  const container = document.getElementById("lp-shortest");
  const detailsBtn = document.getElementById("lp-show-short-details");
  const curRoomBadge = document.getElementById("lp-current-room");
  const curPowerBadge = document.getElementById("lp-player-power");

  if (!container) return;

  if (!pathData || !pathData.path) {
    container.textContent = "No path found";
    if (detailsBtn) detailsBtn.style.display = "none";
    return;
  }

  container.innerHTML = `<strong style="font-size:28px; line-height:1.6">${pathData.path.join(
    " → "
  )}</strong>
    <div style="font-size:24px; margin-top:8px; color:#ddd">Length: ${
      pathData.length
    } steps | Value: ${pathData.details?.total_treasure_value || 0} 💎</div>`;

  // 显示详情按钮并绑定
  if (detailsBtn) {
    detailsBtn.style.display = "inline-block";
    detailsBtn.onclick = () => {
      showPathDetails(pathData);
    };
  }

  // 更新顶部小徽章
  if (pathData.player) {
    if (curRoomBadge) curRoomBadge.textContent = pathData.player.current_room;
    if (curPowerBadge) curPowerBadge.textContent = pathData.player.power;
  }
}

/**
 * 渲染多条路径到左侧面板
 */
export function renderAllPathsToPanel(pathsData) {
  const list = document.getElementById("lp-paths-list");
  if (!list) return;

  if (!pathsData || !pathsData.paths || pathsData.paths.length === 0) {
    list.innerHTML = '<div class="text-muted">No feasible paths</div>';
    return;
  }

  const fragment = document.createDocumentFragment();

  pathsData.paths.forEach((pInfo, idx) => {
    const card = document.createElement("div");
    card.className = "card mb-2";
    card.style =
      "background: rgba(0,0,0,0.25); border: 2px solid #9b7545; padding:12px; font-size:28px; cursor:pointer; transition: all 0.2s;";

    const color =
      idx === 0
        ? "#FFD700"
        : idx === 1
        ? "#FF6B6B"
        : idx === 2
        ? "#4ECDC4"
        : "#999";
    const medal =
      idx === 0 ? "🥇" : idx === 1 ? "🥈" : idx === 2 ? "🥉" : `${idx + 1}.`;

    card.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <div style="flex:1">
          <div><strong style="color:${color}; font-size:32px">${medal}</strong> ${pInfo.path.join(
      " → "
    )}</div>
          <div style="font-size:24px; color:#ddd; margin-top:6px">💎 ${
            pInfo.value
          }  |  ${pInfo.length} steps  |  +${pInfo.power_boost} ⚔️</div>
        </div>
        <div style="margin-left:12px;">
          <button class="btn btn-sm btn-outline-light" data-path-index="${idx}" style="font-size:24px; padding:8px 16px">🔦</button>
        </div>
      </div>
    `;

    // 添加悬停效果
    card.addEventListener("mouseenter", () => {
      card.style.background = "rgba(0,0,0,0.4)";
      card.style.borderColor = color;
    });
    card.addEventListener("mouseleave", () => {
      card.style.background = "rgba(0,0,0,0.25)";
      card.style.borderColor = "#9b7545";
    });

    fragment.appendChild(card);
  });

  list.innerHTML = "";
  list.appendChild(fragment);

  // 绑定点击事件（高亮单条路径）
  list.querySelectorAll("button[data-path-index]").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const i = Number(btn.getAttribute("data-path-index"));
      const path = pathsData.paths[i].path;
      const color =
        i === 0
          ? "#FFD700"
          : i === 1
          ? "#FF6B6B"
          : i === 2
          ? "#4ECDC4"
          : "#999";
      // 使用 safeHighlight 避免布局偏移
      safeHighlight(path, color, 10);
    });
  });
}

// 安全高亮：仅高亮路径，不锁定尺寸（非模态场景）
// 设计思路：
// 1. 左侧栏点击不涉及模态框，无滚动条变化，因此不需要锁定尺寸
// 2. 锁定尺寸本身会触发大量 DOM 重排（修改 width/height/flex 等），反而导致偏移
// 3. vis-network 的 moveTo(duration:0) + highlightPath 已使用即时定位，避免动画导致的布局变化
// 4. 关键：减少不必要的 DOM 操作，让浏览器保持布局稳定
function safeHighlight(path, color, width = 10) {
  try {
    logger.debug("[safeHighlight] start (non-modal, no size lock)", {
      path,
      color,
      width,
    });

    // 直接高亮路径（highlightPath 内部已使用 moveTo duration:0）
    highlightPath(path, color, width);

    logger.debug("[safeHighlight] completed");
  } catch (e) {
    logger.warn("safeHighlight error:", e);
  }
}

// 暴露到全局作用域（用于模态框中的按钮点击）
window.highlightSinglePath = function (path, color) {
  try {
    const pathKey = JSON.stringify(path);
    if (
      currentHighlightedPath &&
      JSON.stringify(currentHighlightedPath) === pathKey
    ) {
      // 点击已高亮的路径则取消高亮（toggle off）
      clearPathHighlight();
      try {
        restoreMapAndParentSize();
      } catch (e) {}
      currentHighlightedPath = null;
      logger.log(`🔁 取消高亮: ${path.join(" → ")}`);
      return;
    }

    // 否则直接高亮新的路径（safeHighlight 内会先 clearPathHighlight()）
    safeHighlight(path, color, 8);
    currentHighlightedPath = path.slice();
    logger.log(`🔦 高亮路径: ${path.join(" → ")}`);
  } catch (e) {
    logger.warn("highlightSinglePath error:", e);
  }
};

// 从模态内部触发的高亮：先隐藏模态（抑制 hidden 时的自动恢复），执行高亮后再重新打开模态
window.highlightSinglePathFromModal = function (path, color) {
  try {
    const el = document.getElementById("pathModal");
    if (!el) {
      // 如果 modal 不存在，退回到普通高亮
      window.highlightSinglePath(path, color);
      return;
    }

    const modalInstance =
      window.bootstrap && typeof window.bootstrap.Modal === "function"
        ? window.bootstrap.Modal.getInstance(el)
        : null;

    _suppressRestoreOnHidden = true;

    const onHiddenOnce = () => {
      try {
        el.removeEventListener("hidden.bs.modal", onHiddenOnce);
      } catch (e) {}

      try {
        safeHighlight(path, color, 8);
        // 记录当前高亮路径，便于后续 toggle 取消
        currentHighlightedPath = path.slice();
      } catch (e) {
        logger.warn("highlightFromModal safeHighlight error:", e);
      }

      // 在高亮启动后短延迟重新打开模态，让 safeHighlight 的锁定机制在模态重新显示时保持有效
      setTimeout(() => {
        try {
          showModalById("pathModal");
        } catch (e) {}
        // 取消抑制，让后续正常隐藏继续恢复（safeHighlight 自己会恢复）
        _suppressRestoreOnHidden = false;
      }, 60);
    };

    if (modalInstance && typeof modalInstance.hide === "function") {
      el.addEventListener("hidden.bs.modal", onHiddenOnce);
      modalInstance.hide();
    } else {
      // fallback hide
      el.classList.remove("show");
      el.style.display = "none";
      el.setAttribute("aria-hidden", "true");
      const b = document.getElementById("bs-backdrop-pathModal");
      if (b) b.remove();
      setTimeout(onHiddenOnce, 60);
    }
  } catch (e) {
    logger.warn("highlightSinglePathFromModal error:", e);
    window.highlightSinglePath(path, color);
  }
};
