// ==================== 主入口模块 ====================
// 负责初始化、事件绑定和应用流程协调

import * as api from "./api_client.js";
import * as mapRenderer from "./map_renderer.js";
import * as pathController from "./path_controller.js";
import {
  initTreasureDisplay,
  updateTreasureDisplay,
} from "./treasure_viewer.js";
import { initLogViewer, updateLogDisplay } from "./log_viewer.js";
import * as logger from "./logger.js";

// ==================== 全局应用状态 ====================
let currentDungeonData = null;
let bossTrackingInterval = null; // Boss 位置追踪定时器
let lastKnownBossRoom = null; // 上次已知的 Boss 房间
let bossAutoMoveTimeout = null; // Boss 自动移动定时器
let bossIsMoving = false; // 当 Boss 正在移动并触发渲染时置为 true，阻止玩家操作
const BOSS_AUTO_MOVE_MIN_MS = 20000; // 20 秒
const BOSS_AUTO_MOVE_MAX_MS = 75000; // 75 秒

// ==================== 页面初始化 ====================
document.addEventListener("DOMContentLoaded", () => {
  logger.log("🎮 Page loaded");

  // 检查vis库是否加载
  if (typeof vis === "undefined") {
    logger.error("❌ vis-network failed to load!");
    alert("Map library failed to load, please refresh and try again");
    return;
  }
  logger.log("✅ vis-network loaded");

  // 检查容器是否存在
  const container = document.getElementById("map-container");
  if (!container) {
    logger.error("❌ map container not found");
    return;
  }
  logger.log("✅ map container found:", container);

  // 绑定按钮事件
  document
    .getElementById("btn-new-map")
    .addEventListener("click", generateNewMap);
  document
    .getElementById("btn-shortest")
    .addEventListener("click", showShortestPath);
  document
    .getElementById("btn-all-paths")
    .addEventListener("click", showAllPaths);
  document.getElementById("lp-clear-paths").addEventListener("click", () => {
    pathController.clearPath();
  });

  // 绑定目标房间设置按钮
  document.getElementById("btn-set-boss").addEventListener("click", () => {
    if (currentDungeonData && currentDungeonData.boss_room_id != null) {
      document.getElementById("target-room-input").value =
        currentDungeonData.boss_room_id;
      updateTargetRoomStatus();
    } else {
      alert("⚠️ Please generate a map first!");
    }
  });

  // 监听目标房间输入变化
  document
    .getElementById("target-room-input")
    .addEventListener("input", updateTargetRoomStatus);

  // 绑定游戏控制按钮
  document
    .getElementById("btn-reset-game")
    .addEventListener("click", confirmResetGame);

  // 绑定游戏结束模态框按钮
  document
    .getElementById("btn-new-game")
    .addEventListener("click", startNewGame);
  document
    .getElementById("btn-reset-only")
    .addEventListener("click", resetGameOnly);

  logger.log("✅ event handlers bound");

  // 初始化战利品展示
  initTreasureDisplay();

  // 初始化日志查看器
  initLogViewer();

  // Boss 将在游戏中自动随机移动（由前端按随机间隔触发移动请求）
});

// ==================== 简单交互锁（阻止玩家在Boss移动时操作） ====================
function disablePlayerActions() {
  try {
    const container = document.getElementById("map-container");
    if (!container) return;
    // 添加覆盖层阻止交互
    let overlay = document.getElementById("boss-lock-overlay");
    if (!overlay) {
      overlay = document.createElement("div");
      overlay.id = "boss-lock-overlay";
      overlay.style.cssText = `position:absolute;left:0;top:0;right:0;bottom:0;z-index:9998;background:rgba(0,0,0,0);cursor:wait;`;
      container.style.position = container.style.position || "relative";
      container.appendChild(overlay);
    }
  } catch (e) {
    // 忽略覆盖失败
  }
}

function enablePlayerActions() {
  try {
    const overlay = document.getElementById("boss-lock-overlay");
    if (overlay && overlay.parentNode) overlay.parentNode.removeChild(overlay);
  } catch (e) {
    // 忽略
  }
}

// ==================== 更新目标房间状态显示 ====================
function updateTargetRoomStatus() {
  const input = document.getElementById("target-room-input");
  const statusDiv = document.getElementById("target-room-status");

  if (!input || !statusDiv) return;

  const targetRoom = parseInt(input.value);

  if (isNaN(targetRoom) || input.value === "") {
    statusDiv.textContent = "No target set";
    statusDiv.style.color = "#ffe8c0";
    return;
  }

  if (currentDungeonData) {
    const room = currentDungeonData.rooms.find((r) => r.id === targetRoom);
    if (room) {
      const isBoss = room.is_boss_room ? " 👑" : "";
      statusDiv.textContent = `Target: Room ${targetRoom}${isBoss}`;
      statusDiv.style.color = "#ffd700";
    } else {
      statusDiv.textContent = `⚠️ Room ${targetRoom} not found`;
      statusDiv.style.color = "#ff6b6b";
    }
  } else {
    statusDiv.textContent = `Target: Room ${targetRoom} (Generate map first)`;
    statusDiv.style.color = "#ffe8c0";
  }
}

// ==================== 生成新地图 ====================
async function generateNewMap() {
  logger.log("📡 Generating new dungeon...");

  // ✅ 暂停Boss移动，防止在地图生成过程中发生故障
  pauseBossMovement();

  // 清空缓存
  mapRenderer.setPreviousPlayerRoom(null);
  mapRenderer.setVisitedRooms([]);

  try {
    logger.log("Step 1: Request empty dungeon framework from backend");
    const emptyData = await api.generateDungeon();

    logger.log("✅ Empty dungeon framework received");
    logger.log("Rooms:", emptyData.rooms.length);

    if (!emptyData.rooms || emptyData.rooms.length === 0) {
      throw new Error("Dungeon data is empty");
    }

    // 暂存空框架数据
    currentDungeonData = emptyData;

    // 渲染地图（会生成布局并调用commit_layout获取完整数据）
    logger.log(
      "Step 2: Rendering map (will generate layout and commit to backend)..."
    );
    await mapRenderer.renderMap(emptyData, {
      onNodeClick: showRoomDetails,
      onRenderComplete: (finalData) => {
        // commit_layout返回的完整数据
        if (finalData) {
          currentDungeonData = finalData;
          logger.log("Step 3: Complete dungeon data received from backend");
          logger.log("Boss room:", finalData.boss_room_id);

          // 初始化访问记录
          if (finalData.visited_rooms) {
            mapRenderer.setVisitedRooms(finalData.visited_rooms);
          }

          updateMapStats(finalData);
          if (finalData.player) {
            updatePlayerUI(finalData.player);
          }

          // 重置战利品展示（新地图时战利品树为空）
          updateTreasureDisplay();

          // 重置日志展示（新地图时日志为空）
          updateLogDisplay();

          // 初始化目标房间为Boss房间
          const targetInput = document.getElementById("target-room-input");
          if (targetInput) {
            targetInput.value = finalData.boss_room_id;
            updateTargetRoomStatus();
          }

          // 启动 Boss 位置追踪 & 自动移动
          startBossTracking();
          startBossAutoMove();

          // ✅ 地图生成完成后恢复Boss移动
          resumeBossMovement();

          alert(
            `✅ Dungeon generated successfully!\n\nRooms: ${finalData.rooms.length}\nBoss: Room ${finalData.boss_room_id}\nStart at: Room 0`
          );
        }
      },
    });

    logger.log("✅ Map generation pipeline completed");
  } catch (error) {
    logger.error("❌ Generation failed:", error);

    // ✅ 出错时也要恢复Boss移动
    resumeBossMovement();

    alert(`❌ Failed to generate dungeon: ${error.message}`);
  }
}

// ==================== 显示房间详情 & 处理房间移动 ====================
async function showRoomDetails(roomId) {
  logger.log("[DEBUG] showRoomDetails called for roomId:", roomId);
  if (bossIsMoving) {
    alert("⚠️ Boss 正在移动，请等待移动与渲染完成后再操作。");
    return;
  }
  if (!currentDungeonData || !Array.isArray(currentDungeonData.rooms)) {
    alert("Dungeon data not loaded!");
    return;
  }
  const room = currentDungeonData.rooms.find((r) => r.id === roomId);
  if (!room) {
    alert("Room not found!");
    return;
  }

  // 检查是否为同一个房间
  if (
    currentDungeonData.player &&
    currentDungeonData.player.current_room === roomId
  ) {
    alert(`You are already in Room ${roomId}`);
    return;
  }

  // 如果房间有怪物，弹窗选择战斗方式
  let combatMode = "dice";
  // 回退选择器（confirm）和可选的自定义modal选择器
  function chooseCombatModeConfirm() {
    return new Promise((resolve) => {
      const msg =
        "You encountered a monster!\n\nChoose battle mode:\n\nOK = Dice Duel (Random)\nCancel = Power Only (No Dice)";
      const useDice = window.confirm(msg);
      resolve(useDice ? "dice" : "power_only");
    });
  }

  function chooseCombatModeModal(room) {
    return new Promise((resolve, reject) => {
      const modalEl = document.getElementById("combatChoiceModal");
      if (!modalEl) return reject(new Error("no modal"));

      try {
        modalEl.querySelector(
          ".modal-title"
        ).textContent = `Encounter: ${room.monster.name}`;
        modalEl.querySelector("#combat-choice-monster-power").textContent =
          room.monster.power;

        const modal = new bootstrap.Modal(modalEl);

        const btnDice = modalEl.querySelector("#combat-choice-dice");
        const btnPower = modalEl.querySelector("#combat-choice-power");
        const btnCancel = modalEl.querySelector("#combat-choice-cancel");

        function cleanup() {
          btnDice.removeEventListener("click", onDice);
          btnPower.removeEventListener("click", onPower);
          btnCancel.removeEventListener("click", onCancel);
        }

        function onDice() {
          cleanup();
          modal.hide();
          resolve("dice");
        }
        function onPower() {
          cleanup();
          modal.hide();
          resolve("power_only");
        }
        function onCancel() {
          cleanup();
          modal.hide();
          resolve(null);
        }

        btnDice.addEventListener("click", onDice);
        btnPower.addEventListener("click", onPower);
        btnCancel.addEventListener("click", onCancel);

        modal.show();
      } catch (err) {
        reject(err);
      }
    });
  }
  if (room.monster) {
    logger.log("[DEBUG] room has monster:", room.monster);
    // 先尝试使用自定义modal（如果存在），否则回退到confirm
    try {
      combatMode = await chooseCombatModeModal(room);
    } catch (err) {
      logger.warn("chooseCombatModeModal failed, falling back to confirm", err);
      combatMode = await chooseCombatModeConfirm();
    }
    if (!combatMode) return; // 用户取消
  }

  // 调用后端API移动玩家到该房间
  try {
    const result = await api.movePlayer(roomId, combatMode);

    if (result.success) {
      // 如果有战斗，根据玩家选择的战斗模式决定是否显示动画
      if (result.combat) {
        if (combatMode === "power_only") {
          // power_only 模式下直接比较武力值，不显示骰子模态或动画
          logger.log(
            "⚔️ Combat resolved in power-only mode; skipping dice animation"
          );
        } else {
          await showCombatAnimation(result.combat, room);
        }
      }

      currentDungeonData.player.current_room = roomId;
      currentDungeonData.player.power = result.power;

      // 更新访问记录
      if (result.visited_rooms) {
        mapRenderer.setVisitedRooms(result.visited_rooms);
      }

      // 更新房间状态
      if (result.updated_room) {
        const roomIndex = currentDungeonData.rooms.findIndex(
          (r) => r.id === roomId
        );
        if (roomIndex !== -1) {
          currentDungeonData.rooms[roomIndex] = result.updated_room;
        }
      }

      updatePlayerUI(currentDungeonData.player);

      // 更新地图上的玩家位置标记
      mapRenderer.updatePlayerMarkerOnMap(roomId, currentDungeonData);

      // 更新目标房间状态（因为玩家位置变了）
      updateTargetRoomStatus();

      // 如果获得了战利品，更新战利品展示
      if (result.new_treasure) {
        updateTreasureDisplay();
      }

      // 更新探险日志
      updateLogDisplay();

      // 检查游戏是否结束
      if (result.game_over) {
        await handleGameOver(result.game_status, result.game_message);
      } else if (room.is_boss_room && room.monster) {
        // 只在Boss战斗时显示结果（如果游戏未结束，说明战斗胜利但Boss还在）
        if (result.combat && result.combat.player_wins) {
          alert(
            `🏆 You defeated the Boss!\n\nYour power: ${currentDungeonData.player.power}\n\nGAME WON! 🎊`
          );
        }
      }
    } else {
      // 移动失败
      if (result.combat) {
        // 战斗失败 - 玩家留在原房间
        if (combatMode === "power_only") {
          // power_only 模式：不显示骰子动画，直接处理战斗结果
          logger.log(
            "⚔️ Combat failed in power-only mode; skipping dice animation"
          );
        } else {
          await showCombatAnimation(result.combat, room);
        }

        // 更新玩家power（已被扣除2点）
        if (currentDungeonData && currentDungeonData.player) {
          currentDungeonData.player.power = result.power;
          updatePlayerUI(currentDungeonData.player);
        }

        // 检查游戏是否结束（玩家死亡）
        if (result.game_over) {
          await handleGameOver(result.game_status, result.game_message);
        } else {
          // 显示明确的失败提示
          alert(
            `❌ Combat Failed!\n\nYour power -2\nCurrent power: ${result.power}\n\nYou remain in Room ${currentDungeonData.player.current_room}`
          );
        }
      } else {
        // 其他失败原因（例如武力值不足无法进入）
        alert(`⚠️ Cannot Move:\n\n${result.message}`);
      }
    }
  } catch (error) {
    logger.error("❌ Move error:", error);
    alert(`❌ Error: ${error.message}`);
  }
}

// ==================== 更新玩家UI ====================
function updatePlayerUI(player) {
  if (!player) return;

  // 更新导航栏的实时显示
  const powerNavbar = document.getElementById("player-power-navbar");
  const roomNavbar = document.getElementById("player-room-navbar");
  if (powerNavbar) powerNavbar.textContent = player.power;
  if (roomNavbar) roomNavbar.textContent = player.current_room;

  // 更新玩家信息显示
  const statsDiv = document.getElementById("map-stats");
  if (statsDiv) {
    statsDiv.innerHTML = `
            <p><strong>🎮 Player Status</strong></p>
            <p>Current Room: <span style="color: #00ff00; font-weight: bold;">#${player.current_room}</span></p>
            <p>Power: ${player.power}</p>
            <p>Treasures: ${player.inventory_count}</p>
            <p>Visited: ${player.visited_count} rooms</p>
        `;
  }
}

// ====================  Update Map Stats ====================
function updateMapStats(data) {
  logger.log("Updating statistics");
  const container = document.getElementById("map-stats");
  if (!container) {
    logger.error("❌ 统计容器不存在");
    return;
  }

  const totalRooms = data.rooms.length;
  const monstersCount = data.rooms.filter((r) => r.monster).length;
  const treasuresCount = data.rooms.filter((r) => r.treasure).length;
  const bossRoom = data.rooms.find((r) => r.is_boss_room);
  const totalEdges =
    data.rooms.reduce((sum, r) => sum + r.neighbors.length, 0) / 2;

  let html =
    '<div style="display: flex; justify-content: space-around; align-items: center; font-size: 52px;">';
  html += `<span><strong>Rooms:</strong> ${totalRooms}</span>`;
  html += `<span><strong>Monsters:</strong> ${monstersCount}</span>`;
  html += `<span><strong>Treasures:</strong> ${treasuresCount}</span>`;
  html += `<span><strong>Connections:</strong> ${totalEdges}</span>`;
  if (bossRoom) {
    html += `<span style="color: #dc3545;"><strong>👹 Boss:</strong> Room ${bossRoom.id} (Power ${bossRoom.monster.power})</span>`;
  }
  html += "</div>";

  container.innerHTML = html;
  logger.log("✅ Statistics updated");
}

// ==================== 显示最短路径 ====================
async function showShortestPath() {
  if (!currentDungeonData) {
    alert("⚠️ Please generate a map first!");
    return;
  }

  if (bossIsMoving) {
    alert("⚠️ Boss 正在移动，请稍后再搜索路径。");
    return;
  }

  // ✅ 暂停Boss移动，防止路径搜索过程中Boss移动导致故障
  pauseBossMovement();

  try {
    // 获取用户设置的目标房间
    const targetInput = document.getElementById("target-room-input");
    let targetRoom =
      targetInput && targetInput.value ? parseInt(targetInput.value) : null;

    // 如果没有设置目标，默认使用Boss房间
    if (targetRoom == null || isNaN(targetRoom)) {
      targetRoom = currentDungeonData.boss_room_id;
      if (targetInput) {
        targetInput.value = targetRoom;
        updateTargetRoomStatus();
      }
    }

    // 验证目标房间是否存在
    const targetRoomData = currentDungeonData.rooms.find(
      (r) => r.id === targetRoom
    );
    if (!targetRoomData) {
      alert(`⚠️ 房间 ${targetRoom} 不存在！请重新设置目标。`);
      return;
    }

    const startRoom = currentDungeonData.player.current_room;
    const playerPower = currentDungeonData.player.power;

    logger.log(
      `🔍 搜索最短路径: 起点=${startRoom}, 终点=${targetRoom}, 武力=${playerPower}`
    );

    await pathController.searchShortestPath(startRoom, targetRoom, playerPower);
  } finally {
    // ✅ 路径搜索完成后恢复Boss移动
    resumeBossMovement();
  }
}

// ==================== 显示所有路径 ====================
async function showAllPaths() {
  if (!currentDungeonData) {
    alert("⚠️ Please generate a map first!");
    return;
  }

  if (bossIsMoving) {
    alert("⚠️ Boss 正在移动，请稍后再搜索路径。");
    return;
  }

  // ✅ 暂停Boss移动，防止路径搜索过程中Boss移动导致故障
  pauseBossMovement();

  try {
    // 获取用户设置的目标房间
    const targetInput = document.getElementById("target-room-input");
    let targetRoom =
      targetInput && targetInput.value ? parseInt(targetInput.value) : null;

    // 如果没有设置目标，默认使用Boss房间
    if (targetRoom == null || isNaN(targetRoom)) {
      targetRoom = currentDungeonData.boss_room_id;
      if (targetInput) {
        targetInput.value = targetRoom;
        updateTargetRoomStatus();
      }
    }

    // 验证目标房间是否存在
    const targetRoomData = currentDungeonData.rooms.find(
      (r) => r.id === targetRoom
    );
    if (!targetRoomData) {
      alert(`⚠️ 房间 ${targetRoom} 不存在！请重新设置目标。`);
      return;
    }

    const startRoom = currentDungeonData.player.current_room;
    const playerPower = currentDungeonData.player.power;

    logger.log(
      `🔍 搜索所有可行路径: 起点=${startRoom}, 终点=${targetRoom}, 武力=${playerPower}`
    );

    // 限制返回前10条路径
    await pathController.searchAllRankedPaths(
      startRoom,
      targetRoom,
      playerPower,
      10
    );
  } finally {
    // ✅ 路径搜索完成后恢复Boss移动
    resumeBossMovement();
  }
}

// ==================== Boss 位置追踪 ====================

/**
 * 启动 Boss 位置追踪
 * 设计：每 3 秒轮询一次 Boss 位置，检测移动并更新 UI
 */
function startBossTracking() {
  // 停止之前的追踪
  stopBossTracking();

  if (!currentDungeonData) return;

  // 初始化 Boss 位置
  lastKnownBossRoom = currentDungeonData.boss_room_id;
  logger.log(
    `🎯 Boss tracking started, current position: Room ${lastKnownBossRoom}`
  );

  // 每 3 秒检查一次
  bossTrackingInterval = setInterval(async () => {
    try {
      const status = await api.getBossStatus();
      const newBossRoom = status.boss_room_id;

      // 检测 Boss 是否移动
      if (newBossRoom !== lastKnownBossRoom) {
        logger.log(`👹 Boss moved: ${lastKnownBossRoom} → ${newBossRoom}`);
        handleBossMovement(lastKnownBossRoom, newBossRoom);
        lastKnownBossRoom = newBossRoom;
      }
    } catch (error) {
      logger.error("Boss 位置查询失败:", error);
    }
  }, 3000); // 3 秒轮询一次
}

/**
 * 停止 Boss 追踪
 */
function stopBossTracking() {
  if (bossTrackingInterval) {
    clearInterval(bossTrackingInterval);
    bossTrackingInterval = null;
    logger.log("🛑 Boss tracking stopped");
  }
  // 同时停止自动移动
  stopBossAutoMove();
}

/**
 * 启动 Boss 自动移动（前端触发后端移动接口），间隔为 BOSS_AUTO_MOVE_MIN_MS..BOSS_AUTO_MOVE_MAX_MS
 */
function startBossAutoMove() {
  // 停止之前的自动移动
  stopBossAutoMove();

  const scheduleNext = () => {
    const delay = Math.floor(
      Math.random() * (BOSS_AUTO_MOVE_MAX_MS - BOSS_AUTO_MOVE_MIN_MS) +
        BOSS_AUTO_MOVE_MIN_MS
    );
    bossAutoMoveTimeout = setTimeout(async () => {
      try {
        // 请求后端移动 Boss
        const res = await api.moveBoss();
        if (res && res.new_room_id != null && res.new_room_id >= 0) {
          const newRoom = res.new_room_id;
          const oldRoom =
            res.old_room_id != null && res.old_room_id >= 0
              ? res.old_room_id
              : lastKnownBossRoom != null
              ? lastKnownBossRoom
              : currentDungeonData.boss_room_id;
          logger.log(
            `🚶‍♂️ Frontend triggered Boss movement: ${oldRoom} → ${newRoom}`
          );
          // 处理移动（后端已更新位置，但仍调用本地处理以保持一致性）
          await handleBossMovement(oldRoom, newRoom);
          lastKnownBossRoom = newRoom;
        } else {
          logger.warn("Boss移动失败或返回无效数据:", res);
        }
      } catch (err) {
        logger.error("自动触发 Boss 移动失败:", err);
      } finally {
        // 无论成功与否都安排下一次移动
        scheduleNext();
      }
    }, delay);
  };

  scheduleNext();
  logger.log("🌀 Boss auto-movement started (interval 20-60s)");
}

function stopBossAutoMove() {
  if (bossAutoMoveTimeout) {
    clearTimeout(bossAutoMoveTimeout);
    bossAutoMoveTimeout = null;
    logger.log("🛑 Boss auto-movement stopped");
  }
}

/**
 * 处理 Boss 移动事件
 * @param {number} oldRoom - 旧房间 ID
 * @param {number} newRoom - 新房间 ID
 */
async function handleBossMovement(oldRoom, newRoom) {
  // 更新本地数据
  // 加锁，阻止玩家在 Boss 移动与渲染过程中进行操作
  bossIsMoving = true;
  disablePlayerActions();

  // 更新本地数据
  currentDungeonData.boss_room_id = newRoom;
  // 将全部更新/渲染流程放入 try/catch/finally，确保最终解锁
  try {
    // 从后端重新获取房间数据以同步怪兽信息
    const oldRoomResponse = await api.getRoom(oldRoom);
    const newRoomResponse = await api.getRoom(newRoom);

    // 更新旧房间数据并清除Boss标记
    const oldRoomIndex = currentDungeonData.rooms.findIndex(
      (r) => r.id === oldRoom
    );
    if (oldRoomIndex !== -1) {
      currentDungeonData.rooms[oldRoomIndex] = oldRoomResponse;
      currentDungeonData.rooms[oldRoomIndex].is_boss_room = false;
    }

    // 更新新房间数据并设置Boss标记
    const newRoomIndex = currentDungeonData.rooms.findIndex(
      (r) => r.id === newRoom
    );
    if (newRoomIndex !== -1) {
      currentDungeonData.rooms[newRoomIndex] = newRoomResponse;
      currentDungeonData.rooms[newRoomIndex].is_boss_room = true;
    }

    logger.log(
      `✅ Room data synchronized: Old room=${oldRoom}, New room=${newRoom}`
    );

    // 检查Boss是否移动到玩家房间
    if (newRoom === currentDungeonData.player.current_room) {
      logger.warn("⚠️ Boss正在接近玩家房间！");
      // 显示警告通知
      showBossWarning();

      // 延迟1-2秒后触发战斗
      const delay = 1000 + Math.random() * 1000; // 1-2秒随机延迟
      setTimeout(async () => {
        // 重新获取最新数据，检查玩家是否已经逃离
        const currentData = await api.getGraph();
        if (currentData && currentData.player.current_room === newRoom) {
          // 玩家仍在原地，触发Boss战斗
          await handleBossAttack();
        } else {
          logger.log("✅ 玩家已逃离，Boss攻击失效");
          showNotification("💨 您及时逃离了Boss的攻击！", "success");
        }
      }, delay);
    }

    // 视觉反馈：闪烁提示
    showBossMovementNotification(oldRoom, newRoom);

    // 更新地图上的 Boss 标记
    updateBossMarkerOnMap(oldRoom, newRoom);

    // 如果当前目标是旧 Boss 房间，自动更新为新房间
    const targetInput = document.getElementById("target-room-input");
    if (targetInput && parseInt(targetInput.value) === oldRoom) {
      targetInput.value = newRoom;
      updateTargetRoomStatus();
      logger.log(`🎯 Target room auto-updated: ${oldRoom} → ${newRoom}`);
    }
  } catch (error) {
    logger.error("同步房间数据失败:", error);
  } finally {
    // 解锁，允许玩家操作
    bossIsMoving = false;
    enablePlayerActions();
  }
}

/**
 * 显示Boss警告
 */
function showBossWarning() {
  const container = document.getElementById("map-container");
  if (!container) return;

  const warning = document.createElement("div");
  warning.style.cssText = `
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    background: linear-gradient(135deg, #ff0000 0%, #8b0000 100%);
    color: white;
    padding: 30px 50px;
    border-radius: 15px;
    font-size: 24px;
    font-weight: bold;
    box-shadow: 0 10px 40px rgba(255, 0, 0, 0.5);
    z-index: 9999;
    text-align: center;
    border: 3px solid #fff;
    animation: pulse 0.5s ease-in-out infinite alternate;
  `;
  warning.innerHTML = `
    <div style="font-size: 48px; margin-bottom: 10px;">⚠️</div>
    <div>Boss正在接近！</div>
    <div style="font-size: 16px; margin-top: 10px; opacity: 0.9;">快速逃离或准备战斗...</div>
  `;

  container.appendChild(warning);

  // 添加脉冲动画
  const style = document.createElement("style");
  style.textContent = `
    @keyframes pulse {
      from { transform: translate(-50%, -50%) scale(1); }
      to { transform: translate(-50%, -50%) scale(1.05); }
    }
  `;
  document.head.appendChild(style);

  // 2秒后移除
  setTimeout(() => {
    warning.remove();
    style.remove();
  }, 2000);
}

/**
 * 处理Boss攻击玩家
 */
async function handleBossAttack() {
  try {
    logger.log("⚔️ Boss attacks player!");

    // 调用后端Boss攻击接口
    const result = await fetch("/api/boss/attack", { method: "POST" });
    const data = await result.json();

    logger.log("Boss combat result:", data);

    if (data.combat) {
      // 显示战斗动画
      const bossRoom = currentDungeonData.rooms.find(
        (r) => r.id === currentDungeonData.boss_room_id
      );
      await showCombatAnimation(data.combat, bossRoom);
    }

    if (data.game_over) {
      if (data.game_won) {
        // 玩家击败Boss - 游戏胜利！
        alert(
          `🏆 恭喜！您击败了Boss！\n\n最终武力值: ${data.final_power}\n\n游戏胜利！🎊`
        );
      } else {
        // 玩家被Boss击败 - 游戏失败
        alert(
          `💀 ${data.message}\n\n最终武力值: ${data.final_power}\n\n游戏结束！`
        );
      }

      // 停止Boss自动移动
      stopBossAutoMove();

      // 可选：禁用进一步操作或重新生成地图
      const regenerate = confirm("是否重新生成地图？");
      if (regenerate) {
        await generateNewMap();
      }
    } else if (!data.success) {
      // 战斗失败但游戏未结束（理论上不应该发生在Boss战中）
      alert(`⚔️ Combat failed!\n\n${data.message}`);
    }

    // 刷新地图数据
    const updatedData = await api.getGraph();
    if (updatedData) {
      currentDungeonData = updatedData;
      updatePlayerUI(currentDungeonData.player);
    }
  } catch (error) {
    logger.error("❌ Boss attack handling failed:", error);
    alert(`Boss attack error: ${error.message}`);
  }
}

/**
 * 显示 Boss 移动通知（闪烁动画）
 */
function showBossMovementNotification(oldRoom, newRoom) {
  const notification = document.createElement("div");
  notification.style.cssText = `
    position: fixed;
    top: 120px;
    left: 50%;
    transform: translateX(-50%);
    background: linear-gradient(135deg, #ff6b6b 0%, #cc0000 100%);
    color: white;
    padding: 20px 40px;
    border-radius: 12px;
    font-size: 32px;
    font-weight: bold;
    box-shadow: 0 8px 24px rgba(255, 0, 0, 0.4);
    z-index: 9999;
    animation: bossAlert 0.5s ease-in-out;
    border: 3px solid #ffd700;
  `;
  notification.innerHTML = `
    👹 <span style="color: #ffd700;">Boss Moved!</span><br>
    <span style="font-size: 26px;">Room ${oldRoom} → Room ${newRoom}</span>
  `;

  // 添加动画样式
  const style = document.createElement("style");
  style.textContent = `
    @keyframes bossAlert {
      0%, 100% { transform: translateX(-50%) scale(1); }
      50% { transform: translateX(-50%) scale(1.05); }
    }
  `;
  document.head.appendChild(style);

  document.body.appendChild(notification);

  // 3 秒后移除
  setTimeout(() => {
    notification.style.transition = "opacity 0.5s";
    notification.style.opacity = "0";
    setTimeout(() => notification.remove(), 500);
  }, 3000);
}

/**
 * 更新地图上的 Boss 标记
 */
function updateBossMarkerOnMap(oldRoom, newRoom) {
  const network = mapRenderer.getNetwork();
  if (!network) return;
  if (oldRoom == null || newRoom == null || oldRoom < 0 || newRoom < 0) {
    logger.warn("无效的房间ID:", { oldRoom, newRoom });
    return;
  }

  try {
    const nodes = network.body.data.nodes;

    // 恢复旧房间节点样式（移除 Boss 标记，可能恢复原怪兽）
    const oldNode = nodes.get(oldRoom);
    if (oldNode) {
      const oldRoomData = currentDungeonData.rooms.find(
        (r) => r.id === oldRoom
      );
      if (oldRoomData) {
        // 构建标签行（统一格式）
        const lines = [`Room ${oldRoom}`];

        // 怪兽信息（可能是恢复的原怪兽）
        if (oldRoomData.monster) {
          lines.push(`👹 ${oldRoomData.monster.name}`);
          lines.push(`⚔️ ${oldRoomData.monster.power}`);
        }

        // 宝箱信息
        if (oldRoomData.treasure) {
          const itemIconMap = {
            Helmet: "🪖",
            Armor: "🛡️",
            Boots: "🥾",
            Weapon: "🗡️",
            Stone: "🔷",
          };
          const icon = itemIconMap[oldRoomData.treasure.item_type] || "🎁";
          lines.push(
            `${icon}${oldRoomData.treasure.item_type} +${oldRoomData.treasure.value}`
          );
        }

        const newImage = mapRenderer.createRoomSVGEmbedded(lines, 300, 1.5, {
          isBoss: false,
          hasMonster: oldRoomData.monster != null,
          hasTreasure: oldRoomData.treasure != null,
          isPlayerRoom: oldRoom === currentDungeonData.player.current_room,
        });

        // 完全恢复旧房间为正常样式，清除所有Boss特效
        nodes.update({
          id: oldRoom,
          image: newImage,
          borderWidth: 4,
          color: {
            border: "#6b4d30",
            background: "transparent",
            hover: {
              border: "#ff7e5f",
              background: "transparent",
            },
            highlight: {
              border: "#ff7e5f",
              background: "transparent",
            },
          },
          shadow: {
            enabled: true,
            color: "rgba(0, 0, 0, 0.3)",
            size: 8,
            x: 2,
            y: 2,
          },
        });
      }
    }

    // 更新新房间节点样式（添加 Boss 标记）
    const newNode = nodes.get(newRoom);
    if (newNode) {
      const newRoomData = currentDungeonData.rooms.find(
        (r) => r.id === newRoom
      );
      if (newRoomData) {
        // 构建标签行（统一格式）
        const lines = [`Room ${newRoom}`];

        // Boss 信息（统一格式）
        if (newRoomData.monster && newRoomData.monster.is_boss) {
          lines.push(`👹 ${newRoomData.monster.name}`);
          lines.push(`⚔️ ${newRoomData.monster.power}`);
        }

        // 宝箱信息
        if (newRoomData.treasure) {
          const itemIconMap = {
            Helmet: "🪖",
            Armor: "🛡️",
            Boots: "🥾",
            Weapon: "🗡️",
            Stone: "🔷",
          };
          const icon = itemIconMap[newRoomData.treasure.item_type] || "🎁";
          lines.push(
            `${icon}${newRoomData.treasure.item_type} +${newRoomData.treasure.value}`
          );
        }

        const newImage = mapRenderer.createRoomSVGEmbedded(lines, 300, 1.5, {
          isBoss: true,
          hasMonster: true,
          hasTreasure: newRoomData.treasure != null,
          isPlayerRoom: newRoom === currentDungeonData.player.current_room,
        });

        nodes.update({ id: newRoom, image: newImage });
      }
    }

    // 闪烁效果：新 Boss 房间
    flashNode(newRoom, 3);

    logger.log(`✅ Map updated: Boss from Room ${oldRoom} → ${newRoom}`);
  } catch (error) {
    logger.error("更新 Boss 标记失败:", error);
  }
}

/**
 * 节点闪烁效果
 */
function flashNode(nodeId, times) {
  const network = mapRenderer.getNetwork();
  if (!network) return;

  let count = 0;
  const flashInterval = setInterval(() => {
    const nodes = network.body.data.nodes;
    const node = nodes.get(nodeId);

    if (node) {
      // 切换边框颜色
      const currentBorderWidth = node.borderWidth || 6;
      nodes.update({
        id: nodeId,
        borderWidth: currentBorderWidth === 6 ? 12 : 6,
        color: {
          border:
            currentBorderWidth === 6
              ? "#ffd700"
              : node.color?.border || "#cc0000",
        },
      });
    }

    count++;
    if (count >= times * 2) {
      clearInterval(flashInterval);
    }
  }, 300);
}

// ==================== 战斗动画系统 ====================

/**
 * 显示战斗动画和结果
 * @param {Object} combat - 战斗数据
 * @param {Object} room - 房间信息
 */
async function showCombatAnimation(combat, room) {
  return new Promise((resolve) => {
    // 获取模态框元素
    const modal = new bootstrap.Modal(document.getElementById("combatModal"));

    // 填充基础信息
    document.getElementById("combat-player-base").textContent =
      combat.player_base;
    document.getElementById("combat-monster-base").textContent =
      combat.monster_base;
    document.getElementById("combat-monster-name").textContent =
      room.monster?.name || "怪物";

    // 初始化骰子为 ?
    document.getElementById("combat-player-dice").textContent = "?";
    document.getElementById("combat-monster-dice").textContent = "?";
    document.getElementById("combat-player-total").textContent = "0";
    document.getElementById("combat-monster-total").textContent = "0";

    // 清空日志
    const logDiv = document.getElementById("combat-log");
    logDiv.innerHTML = '<div style="color: #87ceeb;">🎲 投掷骰子中...</div>';

    // 隐藏继续按钮
    document.getElementById("combat-continue-btn").style.display = "none";

    // 显示模态框
    modal.show();

    // 动画序列
    setTimeout(() => {
      // 第1步：玩家投掷骰子（模拟滚动动画）
      animateDiceRoll("combat-player-dice", combat.player_dice, () => {
        // 第2步：显示玩家总战力
        document.getElementById("combat-player-total").textContent =
          combat.player_total;

        // 第3步：怪物投掷骰子
        setTimeout(() => {
          animateDiceRoll("combat-monster-dice", combat.monster_dice, () => {
            // 第4步：显示怪物总战力
            document.getElementById("combat-monster-total").textContent =
              combat.monster_total;

            // 第5步：显示战斗日志
            setTimeout(() => {
              displayCombatLog(combat);

              // 显示继续按钮
              document.getElementById("combat-continue-btn").style.display =
                "block";

              // 点击继续按钮后关闭并解析 Promise
              document.getElementById("combat-continue-btn").onclick = () => {
                modal.hide();
                resolve();
              };
            }, 500);
          });
        }, 1000);
      });
    }, 800);
  });
}

/**
 * 骰子滚动动画
 * @param {string} elementId - 元素ID
 * @param {number} finalValue - 最终点数
 * @param {Function} callback - 完成回调
 */
function animateDiceRoll(elementId, finalValue, callback) {
  const element = document.getElementById(elementId);
  let count = 0;
  const rollDuration = 1500; // 滚动1.5秒
  const rollInterval = 100; // 每100ms更新一次
  const maxRolls = rollDuration / rollInterval;

  const interval = setInterval(() => {
    if (count < maxRolls) {
      // 显示随机数字
      element.textContent = Math.floor(Math.random() * 20) + 1;
      count++;
    } else {
      // 显示最终结果
      clearInterval(interval);
      element.textContent = finalValue;

      // 暴击或大失败特效
      if (finalValue === 20) {
        element.style.color = "#ffd700";
        element.style.textShadow = "0 0 20px #ffd700";
        element.style.transform = "scale(1.3)";
        setTimeout(() => {
          element.style.transform = "scale(1)";
        }, 300);
      } else if (finalValue === 1) {
        element.style.color = "#ff4444";
        element.style.textShadow = "0 0 20px #ff4444";
      }

      if (callback) callback();
    }
  }, rollInterval);
}

/**
 * 显示战斗日志
 * @param {Object} combat - 战斗数据
 */
function displayCombatLog(combat) {
  const logDiv = document.getElementById("combat-log");
  const logs = combat.combat_log || [];

  let html = "";
  logs.forEach((log) => {
    html += `<div style="margin-bottom: 8px;">${log}</div>`;
  });

  // 添加结果样式
  if (combat.player_wins) {
    logDiv.style.borderColor = "#00ff00";
    logDiv.style.background = "rgba(0, 255, 0, 0.1)";
  } else {
    logDiv.style.borderColor = "#ff4444";
    logDiv.style.background = "rgba(255, 68, 68, 0.1)";
  }

  logDiv.innerHTML = html;
}

// ==================== Boss移动控制函数 ====================

/**
 * 暂停Boss移动
 */
async function pauseBossMovement() {
  try {
    await api.pauseBossMovement();
    logger.log("🔒 Boss移动已暂停");
  } catch (error) {
    logger.error("暂停Boss移动失败:", error);
  }
}

/**
 * 恢复Boss移动
 */
async function resumeBossMovement() {
  try {
    await api.resumeBossMovement();
    logger.log("🔓 Boss移动已恢复");
  } catch (error) {
    logger.error("恢复Boss移动失败:", error);
  }
}

// ==================== 游戏状态管理函数 ====================

/**
 * 处理游戏结束
 */
async function handleGameOver(status, message) {
  logger.log(`🎮 Game Over: ${status} - ${message}`);

  // 停止Boss自动移动
  stopBossAutoMove();
  stopBossTracking();

  // 显示游戏结束模态框
  const modal = new bootstrap.Modal(document.getElementById("gameOverModal"));
  const titleEl = document.getElementById("gameOverTitle");
  const messageEl = document.getElementById("gameOverMessage");
  const statsEl = document.getElementById("gameOverStats");

  // 设置标题和消息
  if (status === "victory") {
    titleEl.innerHTML = "🏆 VICTORY! 🏆";
    titleEl.style.color = "#ffd700";
    messageEl.innerHTML = message || "Congratulations! You defeated the Boss!";
  } else if (status === "defeat") {
    titleEl.innerHTML = "💀 GAME OVER 💀";
    titleEl.style.color = "#ff6b6b";
    messageEl.innerHTML = message || "You were defeated...";
  }

  // 显示游戏统计
  if (currentDungeonData && currentDungeonData.player) {
    const player = currentDungeonData.player;
    statsEl.innerHTML = `
      <div style="text-align: left; display: inline-block;">
        <div>⚔️ Final Power: <strong>${player.power}</strong></div>
        <div>🏺 Treasures Collected: <strong>${
          player.inventory_count || 0
        }</strong></div>
        <div>🗺️ Rooms Visited: <strong>${
          player.visited_count || 0
        }</strong></div>
      </div>
    `;
  }

  modal.show();
}

// Save game feature removed: UI buttons and functions have been deleted to stop further development on save functionality.
/**
 * 开始新游戏
 */
async function startNewGame() {
  // 关闭模态框
  const modal = bootstrap.Modal.getInstance(
    document.getElementById("gameOverModal")
  );
  modal.hide();

  // 生成新地图
  await generateNewMap();
}

/**
 * 仅重置游戏
 */
async function resetGameOnly() {
  // 关闭模态框
  const modal = bootstrap.Modal.getInstance(
    document.getElementById("gameOverModal")
  );
  modal.hide();

  // 重置游戏
  await resetGameInternal();
}

/**
 * 确认重置游戏
 */
async function confirmResetGame() {
  const confirmed = confirm(
    "⚠️ Are you sure you want to reset the game?\n\nThis will:\n- Clear the current map\n- Reset player stats\n- Clear all logs and treasures\n\nThis action cannot be undone!"
  );

  if (confirmed) {
    await resetGameInternal();
  }
}

/**
 * 内部重置游戏函数
 */
async function resetGameInternal() {
  try {
    logger.log("🔄 Resetting game...");

    // 停止Boss自动移动
    stopBossAutoMove();
    stopBossTracking();

    // 调用后端重置API
    const result = await api.resetGame();

    // 清空前端状态
    currentDungeonData = null;
    lastKnownBossRoom = null;

    // 清空地图
    mapRenderer.clearMap();

    // 清空战利品和日志展示
    updateTreasureDisplay();
    updateLogDisplay();

    // 清空路径高亮
    pathController.clearPath();

    // 重置UI
    const statsDiv = document.getElementById("map-stats");
    if (statsDiv) {
      statsDiv.innerHTML =
        '<p class="text-muted text-center mb-0">Click "Generate Map" to start exploring</p>';
    }

    alert("✅ Game reset! Ready to start a new adventure.");
  } catch (error) {
    logger.error("❌ Reset game failed:", error);
    alert(`❌ Failed to reset game: ${error.message}`);
  }
}
