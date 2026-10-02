// ==================== 战利品收藏展示模块 ====================
// 负责渲染战利品树结构、统计信息和收藏管理

import { getTreasureTree, toggleFavorite } from "./api_client.js";
import * as logger from "./logger.js";

// 全局状态
let currentFilter = "all"; // 'all' 或 'favorites'
let favoritesSet = new Set(); // 收藏的战利品名称集合

/**
 * 更新战利品收藏展示
 * 从后端获取战利品树数据并渲染
 */
export async function updateTreasureDisplay(data = null) {
  try {
    const payload = data || (await getTreasureTree());

    // 更新收藏集合
    if (payload.favorites) {
      favoritesSet = new Set(payload.favorites);
    }

    // 更新统计信息
    updateStatistics(
      payload.statistics || {
        total_count: 0,
        total_value: 0,
        favorites_count: 0,
      }
    );

    // 渲染树结构
    renderTreasureTree(payload.tree || { children: [] });
  } catch (error) {
    logger.error("Failed to update treasure display:", error);
  }
}

/**
 * 更新统计信息
 */
function updateStatistics(statistics) {
  const totalCountEl = document.getElementById("treasure-total-count");
  const totalValueEl = document.getElementById("treasure-total-value");

  if (totalCountEl) {
    totalCountEl.textContent = statistics.total_count || 0;
  }
  if (totalValueEl) {
    totalValueEl.textContent = statistics.total_value || 0;
  }

  // 更新收藏统计（如果有显示元素）
  const favoritesCountEl = document.getElementById("treasure-favorites-count");
  if (favoritesCountEl) {
    favoritesCountEl.textContent = statistics.favorites_count || 0;
  }
}

/**
 * 渲染战利品树结构
 * @param {Object} treeData - 树的根节点数据
 */
function renderTreasureTree(treeData) {
  const container = document.getElementById("treasure-tree-container");
  if (!container) return;

  // 如果没有战利品，显示提示
  const hasItems =
    treeData.children &&
    treeData.children.some((cat) => cat.children && cat.children.length > 0);

  if (!hasItems) {
    container.innerHTML = `
      <div class="text-muted" style="font-size: 30px; text-align: center; padding: 20px;">
        尚未收集任何战利品<br>探索地牢获取宝箱！
      </div>
    `;
    return;
  }

  // 渲染过滤按钮
  let html = `
    <div class="filter-buttons" style="margin-bottom: 16px; display: flex; gap: 8px;">
      <button 
        id="filter-all" 
        class="btn ${
          currentFilter === "all" ? "btn-warning" : "btn-outline-light"
        }" 
        style="flex: 1; font-size: 28px; padding: 8px 16px;"
        onclick="window.treasureFilterAll()">
        📦 全部 (${countAllTreasures(treeData)})
      </button>
      <button 
        id="filter-favorites" 
        class="btn ${
          currentFilter === "favorites" ? "btn-warning" : "btn-outline-light"
        }" 
        style="flex: 1; font-size: 28px; padding: 8px 16px;"
        onclick="window.treasureFilterFavorites()">
        ⭐ 收藏 (${favoritesSet.size})
      </button>
    </div>
  `;

  html += '<div class="treasure-tree">';

  // 遍历类别节点（Helmet, Armor, Boots, Weapon, Stone）
  for (const category of treeData.children) {
    if (!category.children || category.children.length === 0) {
      continue; // 跳过空类别
    }

    // 根据过滤条件筛选道具
    const filteredItems = filterItems(category.children);
    if (filteredItems.length === 0) {
      continue; // 如果过滤后没有道具，跳过该类别
    }

    html += renderCategoryNode(category, filteredItems);
  }

  html += "</div>";
  container.innerHTML = html;
}

/**
 * 根据当前过滤条件筛选道具
 */
function filterItems(items) {
  if (currentFilter === "favorites") {
    return items.filter(
      (item) => item.treasure && favoritesSet.has(item.treasure.name)
    );
  }
  return items; // 'all' - 返回所有道具
}

/**
 * 统计所有战利品数量
 */
function countAllTreasures(treeData) {
  let count = 0;
  for (const category of treeData.children) {
    if (category.children) {
      count += category.children.length;
    }
  }
  return count;
}

/**
 * 渲染单个类别节点
 */
function renderCategoryNode(categoryNode, filteredItems) {
  const categoryIcons = {
    Helmet: "⛑️",
    Armor: "🛡️",
    Boots: "👢",
    Weapon: "⚔️",
    Stone: "💎",
  };

  const categoryColors = {
    Helmet: "#8b6d3f",
    Armor: "#6b8e23",
    Boots: "#cd853f",
    Weapon: "#b22222",
    Stone: "#9370db",
  };

  const icon = categoryIcons[categoryNode.name] || "📦";
  const color = categoryColors[categoryNode.name] || "#8b7355";

  let html = `
        <div class="category-node" style="margin-bottom: 20px;">
            <div class="category-header" style="
                font-size: 34px;
                font-weight: bold;
                color: #f4d58d;
                margin-bottom: 12px;
                padding: 12px;
                background: linear-gradient(135deg, ${color}aa 0%, ${color}66 100%);
                border-radius: 8px;
                border: 2px solid ${color};
                display: flex;
                align-items: center;
                box-shadow: 0 2px 8px rgba(0,0,0,0.3);
            ">
                <span style="margin-right: 12px; font-size: 38px;">${icon}</span>
                <span>${categoryNode.name}</span>
                <span style="margin-left: auto; font-size: 28px; color: #ffe8c0;">×${filteredItems.length}</span>
            </div>
            <div class="category-items" style="padding-left: 20px;">
    `;

  // 渲染该类别下的所有道具
  for (const item of filteredItems) {
    html += renderItemNode(item);
  }

  html += `
            </div>
        </div>
    `;

  return html;
}

/**
 * 渲染单个道具节点
 */
function renderItemNode(itemNode) {
  if (!itemNode.treasure) return "";

  const treasure = itemNode.treasure;
  const isFavorite = favoritesSet.has(treasure.name);

  return `
        <div class="treasure-item" style="
            font-size: 30px;
            padding: 10px 16px;
            margin-bottom: 8px;
            background: rgba(139, 109, 63, 0.25);
            border-left: 4px solid #d4a960;
            border-radius: 6px;
            color: #ffe8c0;
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: all 0.2s;
        "
        onmouseover="this.style.background='rgba(212, 169, 96, 0.35)'; this.style.transform='translateX(5px)';"
        onmouseout="this.style.background='rgba(139, 109, 63, 0.25)'; this.style.transform='translateX(0)';"
        >
            <div style="display: flex; align-items: center; gap: 12px;">
                <button 
                    onclick="window.toggleTreasureFavorite('${treasure.name}')"
                    style="
                        background: ${
                          isFavorite
                            ? "linear-gradient(135deg, #ffd700 0%, #ffed4e 100%)"
                            : "rgba(255, 255, 255, 0.1)"
                        };
                        border: 2px solid ${
                          isFavorite ? "#ffd700" : "rgba(255, 255, 255, 0.3)"
                        };
                        color: ${isFavorite ? "#3a2a1a" : "#ffe8c0"};
                        padding: 4px 10px;
                        border-radius: 50%;
                        font-size: 24px;
                        cursor: pointer;
                        transition: all 0.2s;
                        box-shadow: ${
                          isFavorite
                            ? "0 2px 8px rgba(255, 215, 0, 0.4)"
                            : "none"
                        };
                    "
                    onmouseover="this.style.transform='scale(1.15)';"
                    onmouseout="this.style.transform='scale(1)';"
                    title="${isFavorite ? "取消收藏" : "添加到收藏"}"
                >
                    ${isFavorite ? "⭐" : "☆"}
                </button>
                <span style="font-weight: 500;">📦 ${treasure.name}</span>
            </div>
            <span style="
                background: linear-gradient(135deg, #d4a960 0%, #f4d58d 100%);
                padding: 6px 16px;
                border-radius: 20px;
                font-weight: bold;
                font-size: 26px;
                color: #3a2a1a;
                box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            ">
                +${treasure.value} ⚔️
            </span>
        </div>
    `;
}

/**
 * 切换战利品收藏状态
 */
async function handleToggleFavorite(treasureName) {
  try {
    const result = await toggleFavorite(treasureName);

    if (result.success) {
      // 更新本地收藏集合
      if (result.is_favorite) {
        favoritesSet.add(treasureName);
      } else {
        favoritesSet.delete(treasureName);
      }

      // 重新渲染展示
      await updateTreasureDisplay();
    }
  } catch (error) {
    logger.error("Failed to toggle favorite:", error);
    alert("操作失败，请重试");
  }
}

/**
 * 设置过滤器为"全部"
 */
function setFilterAll() {
  currentFilter = "all";
  updateTreasureDisplay();
}

/**
 * 设置过滤器为"收藏"
 */
function setFilterFavorites() {
  currentFilter = "favorites";
  updateTreasureDisplay();
}

/**
 * 初始化战利品展示（页面加载时调用）
 */
export function initTreasureDisplay() {
  // 将函数暴露到全局作用域，供HTML内联事件调用
  window.toggleTreasureFavorite = handleToggleFavorite;
  window.treasureFilterAll = setFilterAll;
  window.treasureFilterFavorites = setFilterFavorites;

  // 加载初始数据
  updateTreasureDisplay();
}
