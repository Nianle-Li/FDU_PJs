/**
 * log_viewer.js - 探险日志查看器（会话式）
 * 负责渲染和展示玩家的探险历史记录
 */

import { getAdventureLog } from "./api_client.js";
import * as logger from "./logger.js";

/**
 * 渲染单条会话记录
 * @param {Object} session - 会话记录对象
 * @param {number} index - 记录索引
 * @returns {HTMLElement} - 渲染好的会话记录元素
 */
function renderSessionRecord(session, index) {
  const recordDiv = document.createElement("div");
  recordDiv.className = "log-record";
  recordDiv.style.cssText = `
    margin-bottom: 16px;
    padding: 16px;
    background: rgba(212, 169, 96, 0.08);
    border-radius: 8px;
    border-left: 4px solid ${session.active ? "#00ff00" : "#d4a960"};
    transition: all 0.3s ease;
    cursor: pointer;
  `;

  // Timestamp formatting
  const startTime = session.start_time
    ? new Date(session.start_time).toLocaleString("zh-CN")
    : "未知时间";

  // Session status badge
  const statusBadge = session.active
    ? '<span style="background: #00ff00; color: #000; padding: 2px 8px; border-radius: 4px; font-size: 20px; margin-left: 10px;">进行中</span>'
    : "";

  // 路径信息
  const path = session.path || [session.start_room];
  const startRoom = session.start_room || 0;
  const endRoom = session.current_room || startRoom;
  const pathLength = session.path_length || path.length - 1;

  // 构建HTML内容
  recordDiv.innerHTML = `
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
      <div style="font-size: 30px; font-weight: bold; color: #f4d58d;">
        会话 #${session.id !== undefined ? session.id : index + 1}${statusBadge}
      </div>
      <div style="font-size: 24px; color: #a8a8a8;">
        ${startTime}
      </div>
    </div>
    
    <div style="font-size: 28px; color: #ffe8c0; margin-bottom: 6px;">
      <span style="color: #ffa500;">📍 起点:</span> 房间 ${startRoom}
      <span style="margin: 0 12px; color: #888;">→</span>
      <span style="color: #00ff00;">🎯 当前:</span> 房间 ${endRoom}
    </div>
    
    <div style="font-size: 26px; color: #d0d0d0; margin-bottom: 6px;">
      <span style="color: #87ceeb;">🗺️ 路径长度:</span> ${pathLength} 步 (${
    path.length
  } 房间)
    </div>
    
    <div style="font-size: 26px; color: #d0d0d0; margin-bottom: 6px;">
      <span style="color: #ff6b6b;">⚔️ 当前武力:</span> ${
        session.current_power || session.initial_power || 0
      }
      ${
        session.total_power_boost > 0
          ? `<span style="color: #00ff00;">(+${session.total_power_boost})</span>`
          : ""
      }
    </div>
    
    <div style="font-size: 26px; color: #d0d0d0; margin-bottom: 6px;">
      <span style="color: #ffd700;">💰 总收益:</span> ${
        session.total_treasure_value || 0
      }
    </div>
    
    <div style="font-size: 26px; color: #d0d0d0;">
      <span style="color: #ff6b6b;">⚔️ 击败怪物:</span> ${
        (session.monsters_defeated || []).length
      } 只
    </div>
    
    <div class="session-details" style="display: none; margin-top: 12px; padding: 12px; background: rgba(0, 0, 0, 0.2); border-radius: 6px;">
      <div style="font-size: 24px; color: #87ceeb; margin-bottom: 8px; font-weight: bold;">
        📜 完整路径:
      </div>
      <div style="font-size: 24px; color: #c0c0c0; word-wrap: break-word; margin-bottom: 12px;">
        ${path.join(" → ")}
      </div>
      
      ${
        session.steps && session.steps.length > 0
          ? `
        <div style="font-size: 24px; color: #87ceeb; margin-bottom: 8px; margin-top: 12px; font-weight: bold;">
          📋 详细步骤 (${session.steps.length} 步):
        </div>
        <div style="max-height: 300px; overflow-y: auto;">
          ${session.steps
            .map(
              (step) => `
            <div style="
              padding: 8px;
              margin-bottom: 6px;
              background: rgba(255, 255, 255, 0.05);
              border-radius: 4px;
              font-size: 22px;
              color: #d0d0d0;
            ">
              <div style="color: #f4d58d; font-weight: bold;">第 ${
                step.step_number
              } 步:</div>
              <div>房间 ${step.from_room} → 房间 ${step.to_room}</div>
              <div style="color: #ff6b6b;">武力: ${step.power_before} → ${
                step.power_after
              }</div>
              ${
                step.monster
                  ? `<div style="color: #ff4444;">⚔️ 击败: ${step.monster.name} (武力 ${step.monster.power})</div>`
                  : ""
              }
              ${
                step.treasure
                  ? `<div style="color: #ffd700;">💎 获得: ${step.treasure.name} (+${step.treasure.value})</div>`
                  : ""
              }
            </div>
          `
            )
            .join("")}
        </div>
      `
          : ""
      }
    </div>
  `;

  // 添加点击展开/折叠功能
  recordDiv.addEventListener("click", () => {
    const detailDiv = recordDiv.querySelector(".session-details");
    if (detailDiv) {
      const isVisible = detailDiv.style.display !== "none";
      detailDiv.style.display = isVisible ? "none" : "block";
    }
  });

  // 悬停效果
  recordDiv.addEventListener("mouseenter", () => {
    recordDiv.style.background = "rgba(212, 169, 96, 0.15)";
    recordDiv.style.borderLeftColor = session.active ? "#00ff00" : "#ffd700";
  });

  recordDiv.addEventListener("mouseleave", () => {
    recordDiv.style.background = "rgba(212, 169, 96, 0.08)";
    recordDiv.style.borderLeftColor = session.active ? "#00ff00" : "#d4a960";
  });

  return recordDiv;
}

/**
 * 计算会话统计信息
 * @param {Array} sessions - 会话记录数组
 * @returns {Object} - 统计数据
 */
function calculateLogStats(sessions) {
  if (!sessions || sessions.length === 0) {
    return {
      totalCount: 0,
      totalMoves: 0,
      totalValue: 0,
    };
  }

  const totalCount = sessions.length;
  const totalMoves = sessions.reduce((sum, session) => {
    return sum + (session.total_steps || session.path_length || 0);
  }, 0);
  const totalValue = sessions.reduce(
    (sum, session) => sum + (session.total_treasure_value || 0),
    0
  );

  return {
    totalCount,
    totalMoves,
    totalValue,
  };
}

/**
 * 更新统计信息显示
 * @param {Object} stats - 统计数据
 */
function updateLogStats(stats) {
  document.getElementById("log-total-count").textContent = stats.totalCount;
  document.getElementById("log-total-moves").textContent = stats.totalMoves;
  document.getElementById("log-total-value").textContent = stats.totalValue;
}

/**
 * 渲染会话列表
 * @param {Array} sessions - 会话记录数组
 */
function renderLogList(sessions) {
  const container = document.getElementById("log-container");

  if (!sessions || sessions.length === 0) {
    container.innerHTML = `
      <div class="text-muted" style="font-size: 30px; text-align: center; padding: 20px;">
        尚无探险记录<br/>开始探索吧！
      </div>
    `;
    return;
  }

  // 清空容器
  container.innerHTML = "";

  // 反向排序（最新的在前），但保持当前活动会话在最前面
  const activeSessions = sessions.filter((s) => s.active);
  const completedSessions = sessions.filter((s) => !s.active).reverse();
  const sortedSessions = [...activeSessions, ...completedSessions];

  // 渲染每条记录
  sortedSessions.forEach((session, index) => {
    const recordElement = renderSessionRecord(session, index);
    container.appendChild(recordElement);
  });
}

/**
 * 更新日志显示（主入口函数）
 */
export async function updateLogDisplay(data = null) {
  try {
    const apiData = data || (await getAdventureLog());

    // 提取会话列表（可能在 data.sessions 或直接是数组）
    const sessions = Array.isArray(apiData) ? apiData : apiData.sessions || [];

    // 如果有当前活动会话，也加入列表
    if (apiData.current_session && !Array.isArray(apiData)) {
      sessions.push(apiData.current_session);
    }

    // 计算统计信息
    const stats = calculateLogStats(sessions);
    updateLogStats(stats);

    // 渲染日志列表
    renderLogList(sessions);
  } catch (error) {
    logger.error("更新日志显示失败:", error);

    // 显示错误信息
    const container = document.getElementById("log-container");
    container.innerHTML = `
      <div class="text-danger" style="font-size: 28px; text-align: center; padding: 20px;">
        ⚠️ 加载日志失败<br/>
        <small style="font-size: 22px;">${error.message}</small>
      </div>
    `;
  }
}

/**
 * 初始化日志查看器
 */
export function initLogViewer() {
  // 页面加载时显示空状态
  updateLogStats({ totalCount: 0, totalMoves: 0, totalValue: 0 });

  logger.log("日志查看器已初始化");
}
