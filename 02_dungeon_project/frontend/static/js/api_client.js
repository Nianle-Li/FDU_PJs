/**
 * API客户端 - 负责与后端通信
 */

/**
 * 生成新地牢
 */
export async function generateDungeon() {
  const response = await fetch("/api/dungeon/new");
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${await response.text()}`);
  }
  return await response.json();
}

/**
 * 获取当前地图
 */
export async function getGraph() {
  const response = await fetch("/api/dungeon/graph");
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return await response.json();
}

/**
 * 获取房间详情
 */
export async function getRoom(roomId) {
  const response = await fetch(`/api/rooms/${roomId}`);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return await response.json();
}

/**
 * 查找最短路径
 */
export async function getShortestPath(params) {
  const { from, to, player_power = 10, details = true } = params;
  const response = await fetch(
    `/api/path/shortest?from=${from}&to=${to}&player_power=${player_power}&details=${details}`
  );
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return await response.json();
}

/**
 * 获取所有路径
 */
export async function getAllPaths(params) {
  const { from, to, playerPower } = params;
  const response = await fetch(
    `/api/path/all?from=${from}&to=${to}&player_power=${playerPower}`
  );
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return await response.json();
}

/**
 * 移动玩家
 */
export async function movePlayer(roomId, combatMode = "dice") {
  const response = await fetch("/api/player/move", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ room_id: roomId, combat_mode: combatMode }),
  });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return await response.json();
}

/**
 * 获取战利品树
 */
export async function getTreasureTree() {
  const response = await fetch("/api/treasure/tree");
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return await response.json();
}

/** * 切换战利品收藏状态
 */
export async function toggleFavorite(treasureName) {
  const response = await fetch("/api/treasure/favorite", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ treasure_name: treasureName }),
  });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return await response.json();
}

/**
 * 获取所有收藏的战利品
 */
export async function getFavorites() {
  const response = await fetch("/api/treasure/favorites");
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return await response.json();
}

/**
 * 获取探险日志
 */
export async function getAdventureLog() {
  const response = await fetch("/api/log/history");
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return await response.json();
}

/**
 * 获取 Boss 当前位置
 */
export async function getBossStatus() {
  const response = await fetch("/api/boss/status");
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return await response.json();
}

/**
 * 触发 Boss 移动（测试用）
 */
export async function moveBoss() {
  const response = await fetch("/api/boss/move", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return await response.json();
}

/**
 * 暂停Boss移动
 */
export async function pauseBossMovement() {
  const response = await fetch("/api/boss/pause", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return await response.json();
}

/**
 * 恢复Boss移动
 */
export async function resumeBossMovement() {
  const response = await fetch("/api/boss/resume", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return await response.json();
}

/** * 提交布局（前端生成布局后调用此接口完成地图生成）
 */
export async function commitLayout(positions, edges) {
  const response = await fetch("/api/dungeon/commit_layout", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ positions, edges }),
  });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${await response.text()}`);
  }
  return await response.json();
}

/**
 * 获取游戏状态
 */
export async function getGameStatus() {
  const response = await fetch("/api/game/status");
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return await response.json();
}

// Save game endpoint removed from client: getGameState() has been deleted because save functionality is no longer supported.
/**
 * 重置游戏
 */
export async function resetGame() {
  const response = await fetch("/api/game/reset", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return await response.json();
}
