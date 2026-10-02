// ==================== 地图渲染器模块 ====================
// 负责所有地图可视化与布局算法
// 前端负责生成图结构（MST + 随机边），后端只提供房间基础数据
import * as logger from "./logger.js";

// ==================== 内部状态管理 ====================
let network = null;
let iconCache = {};
let visitedRooms = new Set();
let previousPlayerRoom = null;

// ==================== 导出状态访问器 ====================
export function getNetwork() {
  return network;
}
export function setVisitedRooms(rooms) {
  visitedRooms = new Set(rooms);
}
export function getVisitedRooms() {
  return visitedRooms;
}
export function setPreviousPlayerRoom(roomId) {
  previousPlayerRoom = roomId;
}

// ==================== 工具函数 ====================

/**
 * 颜色变亮工具
 */
export function lightenColor(hex) {
  const rgb = parseInt(hex.substring(1), 16);
  const r = Math.min(255, ((rgb >> 16) & 0xff) + 40);
  const g = Math.min(255, ((rgb >> 8) & 0xff) + 40);
  const b = Math.min(255, (rgb & 0xff) + 40);
  return `rgb(${r},${g},${b})`;
}

/**
 * 线段相交检测
 */
export function segIntersects(a, b, c, d) {
  function orient(p, q, r) {
    return (q.x - p.x) * (r.y - p.y) - (q.y - p.y) * (r.x - p.x);
  }
  function onSeg(p, q, r) {
    return (
      Math.min(p.x, q.x) <= r.x &&
      r.x <= Math.max(p.x, q.x) &&
      Math.min(p.y, q.y) <= r.y &&
      r.y <= Math.max(p.y, q.y)
    );
  }
  const o1 = orient(a, b, c),
    o2 = orient(a, b, d),
    o3 = orient(c, d, a),
    o4 = orient(c, d, b);
  if (o1 === 0 && onSeg(a, b, c)) return true;
  if (o2 === 0 && onSeg(a, b, d)) return true;
  if (o3 === 0 && onSeg(c, d, a)) return true;
  if (o4 === 0 && onSeg(c, d, b)) return true;
  return o1 > 0 !== o2 > 0 && o3 > 0 !== o4 > 0;
}

// ==================== 布局算法 ====================

/**
 * 泊松盘采样 - 生成均匀分散的初始位置
 * 设计思路：
 * 1. 使用改进的 Bridson 算法，保证点之间最小距离
 * 2. 通过 spacingFactor 增大实际间距，提升视觉均匀度
 * 3. 使用网格索引加速邻域查询，时间复杂度 O(n)
 * 4. 首点偏向中心区域，避免边界聚集
 */
function poissonDiskSampling(numPoints, canvasWidth, canvasHeight, minDist) {
  // 间距放大因子：使房间更加分散，减少视觉拥挤（增大以增加间距）
  const spacingFactor = 1.65;
  const effectiveMinDist = minDist * spacingFactor;

  const points = [];
  const cellSize = effectiveMinDist / Math.sqrt(2);
  const gridWidth = Math.max(3, Math.ceil(canvasWidth / cellSize));
  const gridHeight = Math.max(3, Math.ceil(canvasHeight / cellSize));
  const grid = Array.from({ length: gridHeight }, () =>
    Array(gridWidth).fill(null)
  );
  const active = [];

  // 工具函数：坐标转网格索引（以画布中心为原点）
  function toGrid(p) {
    const gx = Math.floor((p.x + canvasWidth / 2) / cellSize);
    const gy = Math.floor((p.y + canvasHeight / 2) / cellSize);
    return { gx, gy };
  }

  // 工具函数：检查是否在画布内
  function inBounds(p) {
    return (
      Math.abs(p.x) <= canvasWidth / 2 && Math.abs(p.y) <= canvasHeight / 2
    );
  }

  // 初始化：首点放置在中心附近（减少边界效应）
  const firstPoint = {
    x: (Math.random() - 0.5) * canvasWidth * 0.6,
    y: (Math.random() - 0.5) * canvasHeight * 0.6,
  };
  points.push(firstPoint);
  active.push(firstPoint);

  const g0 = toGrid(firstPoint);
  if (g0.gx >= 0 && g0.gx < gridWidth && g0.gy >= 0 && g0.gy < gridHeight) {
    grid[g0.gy][g0.gx] = firstPoint;
  }

  const k = 30; // 每个活性点的尝试次数

  // 主循环：从活性列表中生成新点
  while (active.length > 0 && points.length < numPoints) {
    const idx = Math.floor(Math.random() * active.length);
    const base = active[idx];
    let found = false;

    for (let t = 0; t < k; t++) {
      const angle = Math.random() * Math.PI * 2;
      const radius = effectiveMinDist * (1 + Math.random());
      const np = {
        x: base.x + Math.cos(angle) * radius,
        y: base.y + Math.sin(angle) * radius,
      };

      if (!inBounds(np)) continue;

      const { gx, gy } = toGrid(np);
      if (gx < 0 || gy < 0 || gx >= gridWidth || gy >= gridHeight) continue;

      // 检查周围 5×5 网格区域内的点
      let ok = true;
      for (let oy = -2; oy <= 2 && ok; oy++) {
        for (let ox = -2; ox <= 2; ox++) {
          const nx = gx + ox;
          const ny = gy + oy;
          if (nx < 0 || ny < 0 || nx >= gridWidth || ny >= gridHeight) continue;
          const neighbor = grid[ny][nx];
          if (!neighbor) continue;
          const d = Math.hypot(np.x - neighbor.x, np.y - neighbor.y);
          if (d < effectiveMinDist) {
            ok = false;
            break;
          }
        }
      }

      if (!ok) continue;

      // 通过检查，添加新点
      points.push(np);
      active.push(np);
      grid[gy][gx] = np;
      found = true;
      break;
    }

    if (!found) {
      active.splice(idx, 1);
    }
  }

  // 若点数不足，采用分散补充策略（尽量保持间距）
  if (points.length < numPoints) {
    const deficit = numPoints - points.length;
    for (let i = 0; i < deficit; i++) {
      let p,
        tries = 0;
      do {
        p = {
          x: (Math.random() - 0.5) * canvasWidth,
          y: (Math.random() - 0.5) * canvasHeight,
        };
        tries++;
        if (tries > 50) break; // 防止无限循环

        // 简单检查：是否与已有点过近
        const { gx, gy } = toGrid(p);
        let ok = true;
        if (gx >= 0 && gy >= 0 && gx < gridWidth && gy < gridHeight) {
          for (let oy = -1; oy <= 1 && ok; oy++) {
            for (let ox = -1; ox <= 1; ox++) {
              const nx = gx + ox,
                ny = gy + oy;
              if (nx < 0 || ny < 0 || nx >= gridWidth || ny >= gridHeight)
                continue;
              const neighbor = grid[ny][nx];
              if (!neighbor) continue;
              if (
                Math.hypot(p.x - neighbor.x, p.y - neighbor.y) <
                effectiveMinDist * 0.7
              ) {
                ok = false;
                break;
              }
            }
          }
        }
        if (ok) break;
      } while (true);
      points.push(p);
    }
  }

  return points.slice(0, numPoints);
}

/**
 * 构建最小生成树（Prim算法）
 */
function buildMST(positions) {
  const n = positions.length;
  const visited = new Array(n).fill(false);
  const edges = [];

  visited[0] = true;

  for (let count = 0; count < n - 1; count++) {
    let minDist = Infinity;
    let minEdge = null;

    for (let i = 0; i < n; i++) {
      if (!visited[i]) continue;
      for (let j = 0; j < n; j++) {
        if (visited[j]) continue;
        const dist = Math.sqrt(
          Math.pow(positions[i].x - positions[j].x, 2) +
            Math.pow(positions[i].y - positions[j].y, 2)
        );
        if (dist < minDist) {
          minDist = dist;
          minEdge = { from: i, to: j, dist: dist };
        }
      }
    }

    if (minEdge) {
      edges.push(minEdge);
      visited[minEdge.to] = true;
    }
  }

  return edges;
}

/**
 * 添加额外连接边（贪婪局部算法）
 * 设计思路：
 * 1. 只从每个节点的 K 近邻中选择候选边（避免横穿地图的长边）
 * 2. 候选边按距离升序排序（优先添加短边）
 * 3. 限制每个节点的最大度数（控制视觉复杂度）
 * 4. 限制长边数量（减少横穿地图的连接）
 * 5. 拒绝高度并行重叠的边（通过中点距离和角度过滤）
 * 6. 允许少量交叉（增加连通性和多样性）
 */
export function addRandomLongEdges(positions, existingEdges, rooms) {
  const n = positions.length;
  const edgeSet = new Set(
    existingEdges.map(
      (e) => `${Math.min(e.from, e.to)}-${Math.max(e.from, e.to)}`
    )
  );
  const newEdges = [];

  const numExtra = Math.max(1, Math.floor(n * 0.06)); // 额外边数量约为节点数的 6%

  // 估算地图尺度
  let minX = Infinity,
    minY = Infinity,
    maxX = -Infinity,
    maxY = -Infinity;
  for (const p of positions) {
    if (!p) continue;
    minX = Math.min(minX, p.x);
    minY = Math.min(minY, p.y);
    maxX = Math.max(maxX, p.x);
    maxY = Math.max(maxY, p.y);
  }
  const span = Math.max(1, Math.max(maxX - minX, maxY - minY));

  // 边长阈值（避免过短或过长的边）
  const minLen = Math.max(60, span * 0.06);
  const maxLen = Math.max(120, span * 0.35);
  const longThreshold = span * 0.2; // 超过此长度视为"长边"
  const maxLongEdges = Math.max(1, Math.ceil(numExtra * 0.35)); // 长边数量上限

  // 为每个节点收集 K 最近邻作为候选（局部连接策略）
  const kNearest = Math.min(12, Math.max(6, Math.floor(Math.sqrt(n) * 2)));
  const candidates = [];

  for (let i = 0; i < n; i++) {
    const pi = positions[i];
    if (!pi) continue;

    const dists = [];
    for (let j = 0; j < n; j++) {
      if (i === j) continue;
      const pj = positions[j];
      if (!pj) continue;
      const d = Math.hypot(pi.x - pj.x, pi.y - pj.y);
      dists.push({ from: i, to: j, dist: d });
    }

    // 按距离排序，只取前 K 个
    dists.sort((a, b) => a.dist - b.dist);
    for (let t = 0; t < Math.min(kNearest, dists.length); t++) {
      const c = dists[t];
      if (c.dist < minLen || c.dist > maxLen) continue;
      const key = `${Math.min(c.from, c.to)}-${Math.max(c.from, c.to)}`;
      if (!edgeSet.has(key)) {
        candidates.push(c);
      }
    }
  }

  // 候选边按距离升序排序（优先添加较短边）
  candidates.sort((a, b) => a.dist - b.dist);

  // 记录节点度数
  const degrees = new Array(n).fill(0);
  const baseDegrees = new Map();
  for (const e of existingEdges) {
    baseDegrees.set(e.from, (baseDegrees.get(e.from) || 0) + 1);
    baseDegrees.set(e.to, (baseDegrees.get(e.to) || 0) + 1);
  }
  for (let i = 0; i < n; i++) {
    degrees[i] = baseDegrees.get(i) || 0;
  }

  let longCount = 0;
  const maxDegree = 3; // 每个节点最多连接 3 条额外边

  // 贪婪选择边
  for (const c of candidates) {
    if (newEdges.length >= numExtra) break;

    const key = `${Math.min(c.from, c.to)}-${Math.max(c.from, c.to)}`;
    if (edgeSet.has(key)) continue;

    // 检查度数限制
    if (degrees[c.from] >= maxDegree || degrees[c.to] >= maxDegree) continue;

    // 检查长边数量限制
    if (c.dist > longThreshold && longCount >= maxLongEdges) continue;

    // 评估与现有边的并行重叠度
    let intersections = 0;
    let parallelNearby = 0;
    const mid = {
      x: (positions[c.from].x + positions[c.to].x) / 2,
      y: (positions[c.from].y + positions[c.to].y) / 2,
    };
    const angle = Math.atan2(
      positions[c.to].y - positions[c.from].y,
      positions[c.to].x - positions[c.from].x
    );

    for (const e of [...existingEdges, ...newEdges]) {
      // 跳过共享端点的边
      if (
        e.from === c.from ||
        e.from === c.to ||
        e.to === c.from ||
        e.to === c.to
      )
        continue;

      const pa = positions[e.from];
      const pb = positions[e.to];
      if (!pa || !pb) continue;

      // 检查相交
      if (segIntersects(positions[c.from], positions[c.to], pa, pb)) {
        intersections++;
      }

      // 检查并行重叠（中点接近且角度相似）
      const mid2 = { x: (pa.x + pb.x) / 2, y: (pa.y + pb.y) / 2 };
      const mdist = Math.hypot(mid.x - mid2.x, mid.y - mid2.y);
      const angle2 = Math.atan2(pb.y - pa.y, pb.x - pa.x);
      const angDiff = Math.abs(
        ((angle - angle2 + Math.PI) % (2 * Math.PI)) - Math.PI
      );

      // 如果中点距离很近且角度相似，视为并行重叠
      if (mdist < Math.max(30, span * 0.035) && angDiff < 0.35) {
        parallelNearby++;
      }
    }

    // 拒绝条件：不允许并行重叠，允许少量交叉
    if (parallelNearby > 0) continue;
    if (intersections > 1) continue; // 最多允许与 1 条边相交

    // 通过检查，添加边
    newEdges.push({ from: c.from, to: c.to, dist: c.dist });
    edgeSet.add(key);
    degrees[c.from]++;
    degrees[c.to]++;
    if (c.dist > longThreshold) longCount++;
  }

  // 若不足，放宽条件补充（降级策略）
  if (newEdges.length < numExtra) {
    for (const c of candidates) {
      if (newEdges.length >= numExtra) break;
      const key = `${Math.min(c.from, c.to)}-${Math.max(c.from, c.to)}`;
      if (edgeSet.has(key)) continue;
      if (degrees[c.from] >= maxDegree || degrees[c.to] >= maxDegree) continue;

      newEdges.push({ from: c.from, to: c.to, dist: c.dist });
      edgeSet.add(key);
      degrees[c.from]++;
      degrees[c.to]++;
    }
  }

  return newEdges;
}

/**
 * 力导向布局优化
 */
export function forceDirectedLayout(positions, edges, iterations) {
  const n = positions.length;
  const pos = positions.map((p) => ({ x: p.x, y: p.y }));
  const velocities = Array(n)
    .fill(null)
    .map(() => ({ x: 0, y: 0 }));

  const repulsionStrength = 8000; // 强化斥力，避免粘连
  const springStrength = 0.008;
  const damping = 0.85;

  for (let iter = 0; iter < iterations; iter++) {
    // 斥力
    for (let i = 0; i < n; i++) {
      for (let j = i + 1; j < n; j++) {
        const dx = pos[j].x - pos[i].x;
        const dy = pos[j].y - pos[i].y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const force = repulsionStrength / (dist * dist);

        velocities[i].x -= (force * dx) / dist;
        velocities[i].y -= (force * dy) / dist;
        velocities[j].x += (force * dx) / dist;
        velocities[j].y += (force * dy) / dist;
      }
    }

    // 弹簧力
    for (const edge of edges) {
      const dx = pos[edge.to].x - pos[edge.from].x;
      const dy = pos[edge.to].y - pos[edge.from].y;
      const dist = Math.sqrt(dx * dx + dy * dy) || 1;
      const force = springStrength * dist;

      velocities[edge.from].x += (force * dx) / dist;
      velocities[edge.from].y += (force * dy) / dist;
      velocities[edge.to].x -= (force * dx) / dist;
      velocities[edge.to].y -= (force * dy) / dist;
    }

    // 更新位置
    for (let i = 0; i < n; i++) {
      velocities[i].x *= damping;
      velocities[i].y *= damping;
      pos[i].x += velocities[i].x;
      pos[i].y += velocities[i].y;
    }
  }

  return pos;
}

/**
 * 基于房间尺寸进行碰撞消解
 */
export function enforceSeparation(
  positions,
  minClear,
  canvasWidth,
  canvasHeight,
  iterations = 60,
  edges = []
) {
  const n = positions.length;
  const pos = positions.map((p) => ({ x: p.x, y: p.y }));
  // ✅ 增大边界缓冲到100px，给边缘房间更多空间
  const halfX = canvasWidth / 2 - 100;
  const halfY = canvasHeight / 2 - 100;
  // ✅ 定义边界危险区（距离边界150px内）
  const dangerZoneX = halfX - 150;
  const dangerZoneY = halfY - 150;

  for (let it = 0; it < iterations; it++) {
    // 每次迭代逐渐降低推力系数（模拟退火）
    const cooldown = 1.0 - (it / iterations) * 0.3;

    for (let i = 0; i < n; i++) {
      for (let j = i + 1; j < n; j++) {
        const dx = pos[j].x - pos[i].x;
        const dy = pos[j].y - pos[i].y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;

        if (dist < minClear) {
          const overlap = minClear - dist;

          // ✅ 边界增强：如果两个房间都在边界附近，增强分离力
          let boostFactor = 1.2;
          const iNearBorder =
            Math.abs(pos[i].x) > dangerZoneX ||
            Math.abs(pos[i].y) > dangerZoneY;
          const jNearBorder =
            Math.abs(pos[j].x) > dangerZoneX ||
            Math.abs(pos[j].y) > dangerZoneY;
          if (iNearBorder && jNearBorder) {
            boostFactor = 1.8; // 边界区域房间使用更强的分离力
          }

          const moveX = (((dx / dist) * overlap) / 2) * cooldown * boostFactor;
          const moveY = (((dy / dist) * overlap) / 2) * cooldown * boostFactor;

          pos[i].x -= moveX;
          pos[i].y -= moveY;
          pos[j].x += moveX;
          pos[j].y += moveY;
        }
      }

      // 对节点与边的重叠做排斥，减少边穿过房间
      if (edges && edges.length > 0) {
        const p = pos[i];
        for (const e of edges) {
          if (e.from === i || e.to === i) continue; // 跳过与当前节点相连的边
          const a = pos[e.from];
          const b = pos[e.to];
          if (!a || !b) continue;

          // 计算点到线段的投影与距离
          const vx = b.x - a.x;
          const vy = b.y - a.y;
          const len2 = vx * vx + vy * vy || 1;
          const t = Math.max(
            0,
            Math.min(1, ((p.x - a.x) * vx + (p.y - a.y) * vy) / len2)
          );
          const cx = a.x + t * vx;
          const cy = a.y + t * vy;
          const dxp = p.x - cx;
          const dyp = p.y - cy;
          const distToEdge = Math.hypot(dxp, dyp) || 1;

          // 期望的点-边最小间距（基于房间尺寸）
          const desiredClear = Math.max(minClear * 0.5, 120);
          if (distToEdge < desiredClear) {
            const push = (desiredClear - distToEdge) * 0.7 * cooldown;
            p.x += (dxp / distToEdge) * push;
            p.y += (dyp / distToEdge) * push;
          }
        }
      }
    }

    // ✅ 软性边界推力：在硬约束前，对接近边界的房间施加向中心的推力
    for (let i = 0; i < n; i++) {
      const distToEdgeX = halfX - Math.abs(pos[i].x);
      const distToEdgeY = halfY - Math.abs(pos[i].y);

      // 如果距离边界小于200px，施加向中心的推力
      if (distToEdgeX < 200) {
        const pushForce = (200 - distToEdgeX) * 0.3 * cooldown;
        pos[i].x -= Math.sign(pos[i].x) * pushForce;
      }
      if (distToEdgeY < 200) {
        const pushForce = (200 - distToEdgeY) * 0.3 * cooldown;
        pos[i].y -= Math.sign(pos[i].y) * pushForce;
      }
    }

    // 边界硬约束（分别对 X/Y 限制）
    for (let i = 0; i < n; i++) {
      pos[i].x = Math.max(-halfX, Math.min(halfX, pos[i].x));
      pos[i].y = Math.max(-halfY, Math.min(halfY, pos[i].y));
    }
  }

  return pos;
}

/**
 * 生成带文本的房间SVG并返回 data URL
 */
export function createRoomSVGEmbedded(
  lines,
  size = 300,
  fontScale = 1.0,
  type = {
    isBoss: false,
    hasMonster: false,
    hasTreasure: false,
    isPlayerRoom: false,
  }
) {
  const svgNS = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(svgNS, "svg");
  svg.setAttribute("xmlns", svgNS);
  svg.setAttribute("width", size);
  svg.setAttribute("height", size);
  svg.setAttribute("viewBox", `0 0 ${size} ${size}`);

  // defs: gradient + drop shadow
  const defs = document.createElementNS(svgNS, "defs");

  // background gradient
  const grad = document.createElementNS(svgNS, "linearGradient");
  grad.setAttribute("id", "bgGrad");
  grad.setAttribute("x1", "0%");
  grad.setAttribute("y1", "0%");
  grad.setAttribute("x2", "100%");
  grad.setAttribute("y2", "100%");
  const stopA = document.createElementNS(svgNS, "stop");
  stopA.setAttribute("offset", "0%");
  stopA.setAttribute("stop-color", "#ffffff");
  stopA.setAttribute("stop-opacity", "0.04");
  const stopB = document.createElementNS(svgNS, "stop");
  stopB.setAttribute("offset", "100%");
  stopB.setAttribute("stop-color", "#000000");
  stopB.setAttribute("stop-opacity", "0.02");
  grad.appendChild(stopA);
  grad.appendChild(stopB);
  defs.appendChild(grad);

  // subtle drop shadow for content
  const filter = document.createElementNS(svgNS, "filter");
  filter.setAttribute("id", "ds");
  filter.setAttribute("x", "-20%");
  filter.setAttribute("y", "-20%");
  filter.setAttribute("width", "140%");
  filter.setAttribute("height", "140%");
  const feDrop = document.createElementNS(svgNS, "feDropShadow");
  feDrop.setAttribute("dx", "0");
  feDrop.setAttribute("dy", "3");
  feDrop.setAttribute("stdDeviation", "6");
  feDrop.setAttribute("flood-color", "#000000");
  feDrop.setAttribute("flood-opacity", "0.18");
  filter.appendChild(feDrop);
  defs.appendChild(filter);

  svg.appendChild(defs);

  const radius = Math.floor(size * 0.12);
  // 🎨 使用深色、有质感的游戏风格配色
  const bg = document.createElementNS(svgNS, "rect");
  const baseColor = type.isBoss
    ? "#cc6666" // 暗红色（Boss）
    : type.hasMonster
    ? "#d4a574" // 深沙黄色（怪物）
    : type.hasTreasure
    ? "#7fb069" // 深绿色（宝箱）
    : "#8b8b8b"; // 深灰色（普通）
  const strokeColor = type.isBoss
    ? "#661111"
    : type.hasMonster
    ? "#8b5a00"
    : type.hasTreasure
    ? "#2d5016"
    : "#4a4a4a";

  bg.setAttribute("x", 0);
  bg.setAttribute("y", 0);
  bg.setAttribute("width", size);
  bg.setAttribute("height", size);
  bg.setAttribute("rx", radius);
  bg.setAttribute("ry", radius);
  bg.setAttribute("fill", baseColor);
  bg.setAttribute("stroke", strokeColor);
  bg.setAttribute("stroke-width", Math.max(4, Math.floor(size * 0.022)));
  bg.setAttribute("filter", "url(#ds)");
  svg.appendChild(bg);

  // 🌟 玩家所在房间：发光外边框标记
  if (type.isPlayerRoom) {
    // 第一层：青色发光外框（模拟外发光效果）
    const playerGlow1 = document.createElementNS(svgNS, "rect");
    playerGlow1.setAttribute("x", -Math.floor(size * 0.04));
    playerGlow1.setAttribute("y", -Math.floor(size * 0.04));
    playerGlow1.setAttribute("width", Math.floor(size * 1.08));
    playerGlow1.setAttribute("height", Math.floor(size * 1.08));
    playerGlow1.setAttribute("rx", radius * 1.2);
    playerGlow1.setAttribute("ry", radius * 1.2);
    playerGlow1.setAttribute("fill", "none");
    playerGlow1.setAttribute("stroke", "#2dd4bf"); // 青色
    playerGlow1.setAttribute(
      "stroke-width",
      Math.max(6, Math.floor(size * 0.03))
    );
    playerGlow1.setAttribute("stroke-opacity", "0.6");
    svg.appendChild(playerGlow1);

    // 第二层：更亮的内发光
    const playerGlow2 = document.createElementNS(svgNS, "rect");
    playerGlow2.setAttribute("x", -Math.floor(size * 0.02));
    playerGlow2.setAttribute("y", -Math.floor(size * 0.02));
    playerGlow2.setAttribute("width", Math.floor(size * 1.04));
    playerGlow2.setAttribute("height", Math.floor(size * 1.04));
    playerGlow2.setAttribute("rx", radius * 1.1);
    playerGlow2.setAttribute("ry", radius * 1.1);
    playerGlow2.setAttribute("fill", "none");
    playerGlow2.setAttribute("stroke", "#5eead4"); // 更亮的青色
    playerGlow2.setAttribute(
      "stroke-width",
      Math.max(4, Math.floor(size * 0.02))
    );
    playerGlow2.setAttribute("stroke-opacity", "0.8");
    svg.appendChild(playerGlow2);

    // 顶部标记：向下箭头指示器
    const scale = size / 96;
    const arrowGroup = document.createElementNS(svgNS, "g");
    arrowGroup.setAttribute("opacity", "0.9");

    // 箭头外框（背景）
    const arrowBg = document.createElementNS(svgNS, "path");
    arrowBg.setAttribute(
      "d",
      `M${48 * scale} ${-12 * scale} L${56 * scale} ${-4 * scale} L${
        52 * scale
      } ${-4 * scale} L${52 * scale} ${4 * scale} L${44 * scale} ${
        4 * scale
      } L${44 * scale} ${-4 * scale} L${40 * scale} ${-4 * scale} Z`
    );
    arrowBg.setAttribute("fill", "#0f766e");
    arrowBg.setAttribute("stroke", "#134e4a");
    arrowBg.setAttribute("stroke-width", 1.5 * scale);
    arrowGroup.appendChild(arrowBg);

    // 箭头高光
    const arrowHighlight = document.createElementNS(svgNS, "path");
    arrowHighlight.setAttribute(
      "d",
      `M${48 * scale} ${-10 * scale} L${54 * scale} ${-4 * scale} L${
        51 * scale
      } ${-4 * scale} L${51 * scale} ${2 * scale} L${45 * scale} ${
        2 * scale
      } L${45 * scale} ${-4 * scale} L${42 * scale} ${-4 * scale} Z`
    );
    arrowHighlight.setAttribute("fill", "#2dd4bf");
    arrowHighlight.setAttribute("stroke", "none");
    arrowGroup.appendChild(arrowHighlight);

    svg.appendChild(arrowGroup);
  }

  // 内部装饰框
  const innerFrame = document.createElementNS(svgNS, "rect");
  innerFrame.setAttribute("x", Math.floor(size * 0.08));
  innerFrame.setAttribute("y", Math.floor(size * 0.08));
  innerFrame.setAttribute("width", Math.floor(size * 0.84));
  innerFrame.setAttribute("height", Math.floor(size * 0.84));
  innerFrame.setAttribute("rx", Math.floor(radius * 0.7));
  innerFrame.setAttribute("ry", Math.floor(radius * 0.7));
  innerFrame.setAttribute("fill", "none");
  innerFrame.setAttribute("stroke", type.isPlayerRoom ? "#2dd4bf" : "#ffffff"); // 玩家房间用青色
  innerFrame.setAttribute(
    "stroke-width",
    Math.max(2, Math.floor(size * 0.012))
  );
  innerFrame.setAttribute("stroke-opacity", type.isPlayerRoom ? "0.5" : "0.25");
  svg.appendChild(innerFrame);

  // subtle glass overlay using gradient
  const overlay = document.createElementNS(svgNS, "rect");
  overlay.setAttribute("x", Math.floor(size * 0.06));
  overlay.setAttribute("y", Math.floor(size * 0.06));
  overlay.setAttribute("width", Math.floor(size * 0.88));
  overlay.setAttribute("height", Math.floor(size * 0.88));
  overlay.setAttribute("rx", Math.floor(radius * 0.6));
  overlay.setAttribute("ry", Math.floor(radius * 0.6));
  overlay.setAttribute("fill", "url(#bgGrad)");
  overlay.setAttribute("opacity", "0.2");
  svg.appendChild(overlay);

  // ✨ 添加大型装饰元素（根据房间类型）
  const decorGroup = document.createElementNS(svgNS, "g");
  const scale = size / 96; // 统一缩放比例

  if (type.isBoss) {
    // 👑 Boss房间：大型王冠 + 威严眼睛 + 装饰符文
    decorGroup.setAttribute("opacity", "0.35");

    // 王冠（放大1.5倍）
    const crown = document.createElementNS(svgNS, "path");
    crown.setAttribute(
      "d",
      `M${16 * scale} ${30 * scale} L${26 * scale} ${22 * scale} L${
        38 * scale
      } ${40 * scale} L${48 * scale} ${22 * scale} L${58 * scale} ${
        40 * scale
      } L${68 * scale} ${22 * scale} L${80 * scale} ${30 * scale} L${
        80 * scale
      } ${42 * scale} L${16 * scale} ${42 * scale} Z`
    );
    crown.setAttribute("fill", "#ffd700");
    crown.setAttribute("stroke", "#b8860b");
    crown.setAttribute("stroke-width", 2 * scale);
    decorGroup.appendChild(crown);

    // 王冠珠宝
    for (let i = 0; i < 5; i++) {
      const jewel = document.createElementNS(svgNS, "circle");
      jewel.setAttribute("cx", (20 + i * 15) * scale);
      jewel.setAttribute("cy", 36 * scale);
      jewel.setAttribute("r", 2.5 * scale);
      jewel.setAttribute("fill", i % 2 === 0 ? "#ff4444" : "#4444ff");
      decorGroup.appendChild(jewel);
    }

    // 大眼睛
    const eye1Outer = document.createElementNS(svgNS, "circle");
    eye1Outer.setAttribute("cx", 34 * scale);
    eye1Outer.setAttribute("cy", 58 * scale);
    eye1Outer.setAttribute("r", 7 * scale);
    eye1Outer.setAttribute("fill", "#fff");
    decorGroup.appendChild(eye1Outer);

    const eye1Inner = document.createElementNS(svgNS, "circle");
    eye1Inner.setAttribute("cx", 34 * scale);
    eye1Inner.setAttribute("cy", 58 * scale);
    eye1Inner.setAttribute("r", 4.5 * scale);
    eye1Inner.setAttribute("fill", "#8b0000");
    decorGroup.appendChild(eye1Inner);

    const eye2Outer = document.createElementNS(svgNS, "circle");
    eye2Outer.setAttribute("cx", 62 * scale);
    eye2Outer.setAttribute("cy", 58 * scale);
    eye2Outer.setAttribute("r", 7 * scale);
    eye2Outer.setAttribute("fill", "#fff");
    decorGroup.appendChild(eye2Outer);

    const eye2Inner = document.createElementNS(svgNS, "circle");
    eye2Inner.setAttribute("cx", 62 * scale);
    eye2Inner.setAttribute("cy", 58 * scale);
    eye2Inner.setAttribute("r", 4.5 * scale);
    eye2Inner.setAttribute("fill", "#8b0000");
    decorGroup.appendChild(eye2Inner);

    // 装饰符文（四角）
    for (let corner of [
      [15, 15],
      [81, 15],
      [15, 81],
      [81, 81],
    ]) {
      const rune = document.createElementNS(svgNS, "rect");
      rune.setAttribute("x", corner[0] * scale - 3);
      rune.setAttribute("y", corner[1] * scale - 3);
      rune.setAttribute("width", 6 * scale);
      rune.setAttribute("height", 6 * scale);
      rune.setAttribute("rx", 1 * scale);
      rune.setAttribute("fill", "#ff0000");
      rune.setAttribute("opacity", "0.5");
      decorGroup.appendChild(rune);
    }
  } else if (type.hasMonster) {
    // 👹 怪物房间：大型怪物脸 + 爪痕装饰
    decorGroup.setAttribute("opacity", "0.38");

    // 大眼睛（放大）
    const leftEyeOuter = document.createElementNS(svgNS, "circle");
    leftEyeOuter.setAttribute("cx", 32 * scale);
    leftEyeOuter.setAttribute("cy", 40 * scale);
    leftEyeOuter.setAttribute("r", 9 * scale);
    leftEyeOuter.setAttribute("fill", "#fff");
    decorGroup.appendChild(leftEyeOuter);

    const leftEyeInner = document.createElementNS(svgNS, "circle");
    leftEyeInner.setAttribute("cx", 32 * scale);
    leftEyeInner.setAttribute("cy", 40 * scale);
    leftEyeInner.setAttribute("r", 6 * scale);
    leftEyeInner.setAttribute("fill", "#111");
    decorGroup.appendChild(leftEyeInner);

    const leftPupil = document.createElementNS(svgNS, "circle");
    leftPupil.setAttribute("cx", 33 * scale);
    leftPupil.setAttribute("cy", 39 * scale);
    leftPupil.setAttribute("r", 2.5 * scale);
    leftPupil.setAttribute("fill", "#ff0000");
    decorGroup.appendChild(leftPupil);

    const rightEyeOuter = document.createElementNS(svgNS, "circle");
    rightEyeOuter.setAttribute("cx", 64 * scale);
    rightEyeOuter.setAttribute("cy", 40 * scale);
    rightEyeOuter.setAttribute("r", 9 * scale);
    rightEyeOuter.setAttribute("fill", "#fff");
    decorGroup.appendChild(rightEyeOuter);

    const rightEyeInner = document.createElementNS(svgNS, "circle");
    rightEyeInner.setAttribute("cx", 64 * scale);
    rightEyeInner.setAttribute("cy", 40 * scale);
    rightEyeInner.setAttribute("r", 6 * scale);
    rightEyeInner.setAttribute("fill", "#111");
    decorGroup.appendChild(rightEyeInner);

    const rightPupil = document.createElementNS(svgNS, "circle");
    rightPupil.setAttribute("cx", 65 * scale);
    rightPupil.setAttribute("cy", 39 * scale);
    rightPupil.setAttribute("r", 2.5 * scale);
    rightPupil.setAttribute("fill", "#ff0000");
    decorGroup.appendChild(rightPupil);

    // 大嘴巴
    const mouth = document.createElementNS(svgNS, "path");
    mouth.setAttribute(
      "d",
      `M${24 * scale} ${62 * scale} C${36 * scale} ${76 * scale}, ${
        60 * scale
      } ${76 * scale}, ${72 * scale} ${62 * scale}`
    );
    mouth.setAttribute("fill", "#8b0000");
    mouth.setAttribute("stroke", "#4a0000");
    mouth.setAttribute("stroke-width", 2 * scale);
    decorGroup.appendChild(mouth);

    // 大牙齿
    for (let i = 0; i < 5; i++) {
      const tooth = document.createElementNS(svgNS, "path");
      const x = 30 + i * 9;
      tooth.setAttribute(
        "d",
        `M${x * scale} ${64 * scale} L${(x + 3) * scale} ${72 * scale} L${
          (x + 6) * scale
        } ${64 * scale} Z`
      );
      tooth.setAttribute("fill", "#fff");
      decorGroup.appendChild(tooth);
    }

    // 爪痕装饰（左上角）
    for (let i = 0; i < 3; i++) {
      const scratch = document.createElementNS(svgNS, "line");
      scratch.setAttribute("x1", (12 + i * 6) * scale);
      scratch.setAttribute("y1", 18 * scale);
      scratch.setAttribute("x2", (18 + i * 6) * scale);
      scratch.setAttribute("y2", 28 * scale);
      scratch.setAttribute("stroke", "#4a0000");
      scratch.setAttribute("stroke-width", 2 * scale);
      scratch.setAttribute("stroke-linecap", "round");
      decorGroup.appendChild(scratch);
    }
  } else if (type.hasTreasure) {
    // 💎 宝箱房间：大宝箱 + 金币堆 + 闪光效果
    decorGroup.setAttribute("opacity", "0.4");

    // 宝箱主体（放大）
    const chestBody = document.createElementNS(svgNS, "rect");
    chestBody.setAttribute("x", 28 * scale);
    chestBody.setAttribute("y", 50 * scale);
    chestBody.setAttribute("width", 40 * scale);
    chestBody.setAttribute("height", 26 * scale);
    chestBody.setAttribute("rx", 3 * scale);
    chestBody.setAttribute("fill", "#8b6914");
    chestBody.setAttribute("stroke", "#4a3808");
    chestBody.setAttribute("stroke-width", 2 * scale);
    decorGroup.appendChild(chestBody);

    // 宝箱装饰条纹
    for (let i = 0; i < 3; i++) {
      const stripe = document.createElementNS(svgNS, "rect");
      stripe.setAttribute("x", 28 * scale);
      stripe.setAttribute("y", (54 + i * 7) * scale);
      stripe.setAttribute("width", 40 * scale);
      stripe.setAttribute("height", 2 * scale);
      stripe.setAttribute("fill", "#5a4208");
      decorGroup.appendChild(stripe);
    }

    // 宝箱盖子
    const lid = document.createElementNS(svgNS, "rect");
    lid.setAttribute("x", 28 * scale);
    lid.setAttribute("y", 42 * scale);
    lid.setAttribute("width", 40 * scale);
    lid.setAttribute("height", 10 * scale);
    lid.setAttribute("rx", 3 * scale);
    lid.setAttribute("fill", "#a0771a");
    lid.setAttribute("stroke", "#4a3808");
    lid.setAttribute("stroke-width", 2 * scale);
    decorGroup.appendChild(lid);

    // 大锁扣
    const lockOuter = document.createElementNS(svgNS, "rect");
    lockOuter.setAttribute("x", 44 * scale);
    lockOuter.setAttribute("y", 46 * scale);
    lockOuter.setAttribute("width", 8 * scale);
    lockOuter.setAttribute("height", 10 * scale);
    lockOuter.setAttribute("rx", 2 * scale);
    lockOuter.setAttribute("fill", "#ffd700");
    lockOuter.setAttribute("stroke", "#b8860b");
    lockOuter.setAttribute("stroke-width", 1.5 * scale);
    decorGroup.appendChild(lockOuter);

    const keyhole = document.createElementNS(svgNS, "circle");
    keyhole.setAttribute("cx", 48 * scale);
    keyhole.setAttribute("cy", 51 * scale);
    keyhole.setAttribute("r", 2 * scale);
    keyhole.setAttribute("fill", "#4a3808");
    decorGroup.appendChild(keyhole);

    // 大宝石装饰（顶部多个）
    const gems = [
      { cx: 32, cy: 32, r: 4, fill: "#4dabf7" },
      { cx: 42, cy: 28, r: 5, fill: "#ffd43b" },
      { cx: 48, cy: 26, r: 6, fill: "#ff6b6b" },
      { cx: 54, cy: 28, r: 5, fill: "#51cf66" },
      { cx: 64, cy: 32, r: 4, fill: "#a78bfa" },
    ];

    gems.forEach((gem) => {
      const gemElem = document.createElementNS(svgNS, "circle");
      gemElem.setAttribute("cx", gem.cx * scale);
      gemElem.setAttribute("cy", gem.cy * scale);
      gemElem.setAttribute("r", gem.r * scale);
      gemElem.setAttribute("fill", gem.fill);
      gemElem.setAttribute("stroke", "#fff");
      gemElem.setAttribute("stroke-width", 0.5 * scale);
      decorGroup.appendChild(gemElem);
    });

    // 金币堆（底部）
    for (let i = 0; i < 4; i++) {
      const coin = document.createElementNS(svgNS, "ellipse");
      coin.setAttribute("cx", (34 + i * 8) * scale);
      coin.setAttribute("cy", 78 * scale);
      coin.setAttribute("rx", 4 * scale);
      coin.setAttribute("ry", 3 * scale);
      coin.setAttribute("fill", "#ffd700");
      coin.setAttribute("stroke", "#b8860b");
      coin.setAttribute("stroke-width", 0.8 * scale);
      decorGroup.appendChild(coin);
    }
  } else {
    // 🚪 普通房间：大门 + 石砖纹理
    decorGroup.setAttribute("opacity", "0.4");

    // 石砖纹理（四个角）
    for (let pos of [
      [12, 12],
      [72, 12],
      [12, 72],
      [72, 72],
    ]) {
      const brick = document.createElementNS(svgNS, "rect");
      brick.setAttribute("x", pos[0] * scale);
      brick.setAttribute("y", pos[1] * scale);
      brick.setAttribute("width", 12 * scale);
      brick.setAttribute("height", 8 * scale);
      brick.setAttribute("fill", "#5a5a5a");
      brick.setAttribute("stroke", "#3a3a3a");
      brick.setAttribute("stroke-width", 1 * scale);
      decorGroup.appendChild(brick);
    }

    // 大门
    const door = document.createElementNS(svgNS, "rect");
    door.setAttribute("x", 38 * scale);
    door.setAttribute("y", 54 * scale);
    door.setAttribute("width", 20 * scale);
    door.setAttribute("height", 30 * scale);
    door.setAttribute("rx", 3 * scale);
    door.setAttribute("fill", "#3b3b3b");
    door.setAttribute("stroke", "#1a1a1a");
    door.setAttribute("stroke-width", 2 * scale);
    decorGroup.appendChild(door);

    // 门板条纹
    for (let i = 0; i < 3; i++) {
      const plank = document.createElementNS(svgNS, "line");
      plank.setAttribute("x1", 40 * scale);
      plank.setAttribute("y1", (60 + i * 8) * scale);
      plank.setAttribute("x2", 56 * scale);
      plank.setAttribute("y2", (60 + i * 8) * scale);
      plank.setAttribute("stroke", "#2a2a2a");
      plank.setAttribute("stroke-width", 1.5 * scale);
      decorGroup.appendChild(plank);
    }

    // 大门把手
    const doorKnob = document.createElementNS(svgNS, "circle");
    doorKnob.setAttribute("cx", 52 * scale);
    doorKnob.setAttribute("cy", 69 * scale);
    doorKnob.setAttribute("r", 3 * scale);
    doorKnob.setAttribute("fill", "#ffd700");
    doorKnob.setAttribute("stroke", "#b8860b");
    doorKnob.setAttribute("stroke-width", 1 * scale);
    decorGroup.appendChild(doorKnob);
  }

  svg.appendChild(decorGroup);

  // 字体稍微缩小以便在房间内更从容地显示，同时保留 MV Boli 字体
  const baseSize = Math.floor(size * 0.09 * fontScale);
  const lineHeight = Math.floor(baseSize * 1.25);
  const totalHeight = lineHeight * lines.length;
  const startY = Math.floor((size - totalHeight) / 2) + lineHeight;

  lines.forEach((text, idx) => {
    // ✨ 检查是否有删除线标记 ~~text~~
    const hasStrikethrough = text.includes("~~");
    let displayText = text;

    if (hasStrikethrough) {
      // 移除 ~~ 标记
      displayText = text.replace(/~~/g, "");
    }

    const textEl = document.createElementNS(svgNS, "text");
    textEl.setAttribute("x", size / 2);
    textEl.setAttribute("y", startY + idx * lineHeight);
    textEl.setAttribute("text-anchor", "middle");
    textEl.setAttribute("dominant-baseline", "middle");
    textEl.setAttribute("font-family", '"MV Boli", "Arial", sans-serif');
    textEl.setAttribute("font-size", `${baseSize}px`);
    textEl.setAttribute("fill", hasStrikethrough ? "#999999" : "#ffffff"); // 被击败的怪物用灰色
    textEl.setAttribute("stroke", "#000000");
    textEl.setAttribute(
      "stroke-width",
      Math.max(1, Math.floor(baseSize * 0.22))
    );
    textEl.setAttribute("paint-order", "stroke");

    // ✨ 添加删除线装饰
    if (hasStrikethrough) {
      textEl.setAttribute("text-decoration", "line-through");
      textEl.setAttribute("opacity", "0.7"); // 半透明效果
    }

    textEl.textContent = displayText;
    svg.appendChild(textEl);
  });

  const serializer = new XMLSerializer();
  const svgString = serializer.serializeToString(svg);
  const encoded = encodeURIComponent(svgString)
    .replace(/'/g, "%27")
    .replace(/"/g, "%22");
  return `data:image/svg+xml;charset=UTF-8,${encoded}`;
}

/**
 * 构建高质感隧道（带并行边偏移与曲线）
 * 设计思路：
 * 1. 检测并行/邻近的边（中点接近且角度相似）
 * 2. 为同组的并行边分配法向偏移索引（中心对齐分布）
 * 3. 根据偏移量启用曲线渲染（smooth），视觉上分散重叠
 * 4. 保留两层绘制（暗底 + 高光）维持隧道质感
 */
export function buildBeautifulEdges(edges, positions) {
  const visEdges = [];
  const edgeMap = new Map();

  edges.forEach((edge) => {
    const key = `${Math.min(edge.from, edge.to)}-${Math.max(
      edge.from,
      edge.to
    )}`;
    edgeMap.set(key, (edgeMap.get(key) || 0) + 1);
  });

  const tunnelColorPalettes = [
    {
      dark: "#3b2a20",
      rim: "#c98f4a",
      glow: "#f0d7b0",
      shadow: "rgba(30,18,8,0.55)",
    },
    {
      dark: "#432f23",
      rim: "#b06a36",
      glow: "#e6c39a",
      shadow: "rgba(34,20,10,0.52)",
    },
    {
      dark: "#3a2b25",
      rim: "#9f6a3a",
      glow: "#d9b78f",
      shadow: "rgba(36,20,8,0.50)",
    },
    {
      dark: "#2f251f",
      rim: "#8f5a2f",
      glow: "#cfa77f",
      shadow: "rgba(28,16,6,0.50)",
    },
  ];

  // 预计算每条边的元数据（中点、法向量、角度等）
  const meta = edges.map((edge) => {
    const a = positions[edge.from];
    const b = positions[edge.to];
    const dx = b.x - a.x;
    const dy = b.y - a.y;
    const len = Math.max(1, Math.hypot(dx, dy));
    return {
      dx,
      dy,
      len,
      mid: { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 },
      normal: { x: -dy / len, y: dx / len },
      angle: Math.atan2(dy, dx),
    };
  });

  // 估算地图尺度
  const spanEstimate = (() => {
    let minX = Infinity,
      minY = Infinity,
      maxX = -Infinity,
      maxY = -Infinity;
    for (const p of positions) {
      if (!p) continue;
      minX = Math.min(minX, p.x);
      minY = Math.min(minY, p.y);
      maxX = Math.max(maxX, p.x);
      maxY = Math.max(maxY, p.y);
    }
    return Math.max(1, Math.max(maxX - minX, maxY - minY));
  })();

  // 构建并行边分组（使用邻接表）
  const groups = new Array(edges.length).fill(null).map(() => []);
  for (let i = 0; i < edges.length; i++) {
    for (let j = i + 1; j < edges.length; j++) {
      const md = Math.hypot(
        meta[i].mid.x - meta[j].mid.x,
        meta[i].mid.y - meta[j].mid.y
      );
      const angDiff = Math.abs(
        ((meta[i].angle - meta[j].angle + Math.PI) % (2 * Math.PI)) - Math.PI
      );

      // 判断为并行/邻近：中点距离近且角度相似
      if (md < Math.max(28, spanEstimate * 0.03) && angDiff < 0.35) {
        groups[i].push(j);
        groups[j].push(i);
      }
    }
  }

  // 为每条边分配偏移索引（DFS 找连通分量，组内均匀分配偏移）
  const assignedOffset = new Array(edges.length).fill(0);
  const visited = new Array(edges.length).fill(false);

  for (let i = 0; i < edges.length; i++) {
    if (visited[i]) continue;

    // DFS 找出一个连通分量
    const stack = [i];
    const comp = [];
    visited[i] = true;
    while (stack.length) {
      const u = stack.pop();
      comp.push(u);
      for (const v of groups[u]) {
        if (!visited[v]) {
          visited[v] = true;
          stack.push(v);
        }
      }
    }

    // 对组内边分配偏移（中心对齐）
    comp.sort((a, b) => a - b);
    const spacingBase = Math.min(
      18,
      Math.max(6, Math.floor(spanEstimate * 0.01))
    );
    for (let k = 0; k < comp.length; k++) {
      assignedOffset[comp[k]] = (k - (comp.length - 1) / 2) * spacingBase;
    }
  }

  // 构建 vis-network 边对象
  edges.forEach((edge, idx) => {
    const a = positions[edge.from];
    const b = positions[edge.to];
    if (!a || !b) return;

    const m = meta[idx];
    const palette = tunnelColorPalettes[idx % tunnelColorPalettes.length];
    const dist = edge.dist || m.len;

    // 根据长度调整宽度
    let baseWidth = 18;
    if (dist > 350) baseWidth = 32;
    else if (dist > 220) baseWidth = 26;
    const rimWidth = Math.max(3, Math.floor(baseWidth * 0.28));

    // 计算偏移和曲率
    const offset = assignedOffset[idx] || 0;
    const roundness = Math.min(
      0.5,
      (Math.abs(offset) / Math.max(60, m.len)) * 1.8
    );

    // 曲线配置
    const smoothSpec = {
      enabled: roundness > 0.001,
      type: offset >= 0 ? "curvedCW" : "curvedCCW",
      roundness: roundness,
    };

    // 第一层：暗色粗底
    visEdges.push({
      from: edge.from,
      to: edge.to,
      width: baseWidth,
      color: {
        color: palette.dark,
        highlight: palette.dark,
        hover: palette.dark,
        opacity: 0.98,
      },
      smooth: smoothSpec,
      shadow: {
        enabled: true,
        color: palette.shadow,
        size: Math.min(28, Math.floor(baseWidth * 0.9)),
        x: 6,
        y: 6,
      },
      selectable: false,
    });

    // 第二层：窄高光
    visEdges.push({
      from: edge.from,
      to: edge.to,
      width: Math.max(3, Math.floor(rimWidth)),
      color: {
        color: palette.rim,
        highlight: palette.glow,
        hover: palette.glow,
        opacity: 1.0,
      },
      smooth: smoothSpec,
      shadow: { enabled: false },
      dashes: false,
      selectable: false,
    });
  });

  return visEdges;
}

// ==================== 主渲染函数 ====================

/**
 * 渲染地图主函数
 * 前端负责生成图结构（MST + 随机边），然后提交给后端保存
 * @param {Object} dungeonData - 地牢数据 {rooms, boss_room_id, player}
 * @param {Object} opts - 选项 {onNodeClick, onRenderComplete}
 */
export async function renderMap(dungeonData, opts = {}) {
  logger.log("🎨 Start rendering map (frontend generates graph)");

  // ✅ 清空图标缓存，确保使用最新数据生成图标（特别是后端调整宝箱/怪物后）
  iconCache = {};

  const container = document.getElementById("map-container");
  if (!container) {
    logger.error("❌ map-container not found");
    return null;
  }

  const numRooms = dungeonData.rooms.length;
  const rect = container.getBoundingClientRect();
  logger.log(
    `📐 Container dimensions: ${rect.width.toFixed(
      1
    )}px × ${rect.height.toFixed(1)}px`
  );
  // 使用宽高独立的画布尺寸（长方形支持），充分利用宽屏同时保持纵向空间
  const canvasWidth = Math.floor(rect.width * 0.95);
  const canvasHeight = Math.floor(rect.height * 0.95);
  logger.log(`📏 Canvas: ${canvasWidth}px × ${canvasHeight}px (W×H)`);

  // 分离视觉尺寸与物理尺寸：NODE_SIZE用于渲染，PHYSICAL_SIZE用于算法
  const NODE_SIZE = 175; // 视觉尺寸（更小的房间图标）
  const PHYSICAL_SIZE = 250; // 物理碰撞尺寸（保持算法间距）

  // 使用 PHYSICAL_SIZE 计算间距，避免视觉缩小影响布局算法
  const minDist = Math.max(
    PHYSICAL_SIZE + 520,
    Math.floor(
      (Math.min(canvasWidth, canvasHeight) / Math.sqrt(numRooms)) * 1.25
    )
  );

  // ✅ 步骤1：使用泊松盘采样初始化节点位置
  const positions = poissonDiskSampling(
    numRooms,
    canvasWidth,
    canvasHeight,
    minDist
  );
  logger.log(
    "✅ Poisson-disk sampling completed, generated",
    positions.length,
    "positions"
  );

  // ✅ 步骤2：使用力导向布局优化节点分布（无边约束，纯斥力）
  const optimizedPositions = forceDirectedLayout(positions, [], 180);
  logger.log("✅ Force-directed layout (repulsion-only) completed");

  // ✅ 步骤3：基于房间尺寸进行碰撞消解（使用物理尺寸而非视觉尺寸）
  const minClear = Math.floor(PHYSICAL_SIZE * 2.3); // 约 575px 最小间距，确保边可见且不重叠
  const separatedPositions = enforceSeparation(
    optimizedPositions,
    minClear,
    canvasWidth,
    canvasHeight,
    220, // 更多迭代确保充分分离
    [] // 此时还没有边
  );
  logger.log("✅ Collision resolution completed");

  // ✅ 验证位置分布与画布尺寸
  const boundX = canvasWidth / 2 - 100;
  const boundY = canvasHeight / 2 - 100;
  let minDistance = Infinity;
  let outOfBounds = 0;
  for (let i = 0; i < separatedPositions.length; i++) {
    // 检查是否超出边界
    if (
      Math.abs(separatedPositions[i].x) > boundX ||
      Math.abs(separatedPositions[i].y) > boundY
    ) {
      outOfBounds++;
    }
    // 检查最小房间间距
    for (let j = i + 1; j < separatedPositions.length; j++) {
      const dx = separatedPositions[j].x - separatedPositions[i].x;
      const dy = separatedPositions[j].y - separatedPositions[i].y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      minDistance = Math.min(minDistance, dist);
    }
  }
  logger.log(`📊 Position validation:`);
  logger.log(
    `   Canvas bounds: ±${boundX.toFixed(0)}px × ±${boundY.toFixed(0)}px`
  );
  logger.log(
    `   Out of bounds: ${outOfBounds}/${separatedPositions.length} rooms`
  );
  logger.log(
    `   Min room distance: ${minDistance.toFixed(1)}px (target: ${minClear}px)`
  );
  if (minDistance < minClear * 0.8) {
    logger.warn(
      `⚠️ Some rooms may be too close (${minDistance.toFixed(1)}px < ${(
        minClear * 0.8
      ).toFixed(1)}px)`
    );
  }

  // ✅ 步骤4：基于最终位置构建MST（确保连接真正相邻的房间）
  const mstEdges = buildMST(separatedPositions);
  logger.log("✅ MST built on final positions,", mstEdges.length, "edges");

  // ✅ 步骤5：在最终位置基础上添加额外连接边
  const additionalEdges = addRandomLongEdges(
    separatedPositions,
    mstEdges,
    dungeonData.rooms
  );
  logger.log(
    "✅ Added",
    additionalEdges.length,
    "additional edges (greedy local strategy)"
  );

  // ✅ 步骤6：去重边（关键修复：包含 additionalEdges！）
  const allEdgesRaw = [...mstEdges, ...additionalEdges];
  const uniqueEdgesMap = new Map();
  allEdgesRaw.forEach((edge) => {
    const key = `${Math.min(edge.from, edge.to)}-${Math.max(
      edge.from,
      edge.to
    )}`;
    if (!uniqueEdgesMap.has(key)) {
      uniqueEdgesMap.set(key, edge);
    }
  });
  const uniqueEdges = Array.from(uniqueEdgesMap.values());
  logger.log(
    `✅ Deduplicated edges: ${allEdgesRaw.length} -> ${uniqueEdges.length}`
  );

  // ✅ 步骤7：构建初始节点（使用空数据或部分数据）
  const initialNodes = dungeonData.rooms.map((room, index) => {
    const pos = separatedPositions[index];
    const isStartRoom = room.id === 0;
    const isBoss = room.is_boss_room;
    const hasMonster = room.monster !== null && room.monster !== undefined;
    const hasTreasure = room.treasure !== null && room.treasure !== undefined;

    const lines = [`#${room.id}`];

    // ✨ 处理被击败的怪物（显示删除线）
    if (room.defeated_monster_name) {
      if (isBoss) {
        lines.push(`👑~~${room.defeated_monster_name}~~`);
      } else {
        lines.push(`👾~~${room.defeated_monster_name}~~`);
      }
    } else if (isBoss && hasMonster) {
      lines.push(`👑${room.monster.name} ${room.monster.power}`);
    } else if (hasMonster) {
      lines.push(`👾${room.monster.name} ${room.monster.power}`);
    }

    if (hasTreasure) {
      const t = room.treasure;
      const itemIconMap = {
        Gold: "💰",
        Dagger: "🗡️",
        Sword: "⚔️",
        Amulet: "🔮",
        Potion: "🧪",
        Helmet: "🪖",
        Armor: "🛡️",
        Boots: "🥾",
        Weapon: "🗡️",
        Stone: "🔷",
      };
      const icon = itemIconMap[t.item_type] || "🎁";
      lines.push(`${icon}${t.item_type} +${t.power_boost}`);
    }

    const cacheKey = `${room.id}_${isStartRoom}_${isBoss}_${hasMonster}_${hasTreasure}`;
    if (!iconCache[cacheKey]) {
      iconCache[cacheKey] = createRoomSVGEmbedded(lines, NODE_SIZE, 1.5, {
        isBoss,
        hasMonster,
        hasTreasure,
      });
    }

    return {
      id: room.id,
      label: "",
      title: `Room ${room.id}${
        hasMonster
          ? `\nMonster: ${room.monster.name} (${room.monster.power})`
          : ""
      }${hasTreasure ? `\nTreasure: ${room.treasure.name}` : ""}`,
      x: pos.x,
      y: pos.y,
      fixed: { x: true, y: true },
      shape: "image",
      image: iconCache[cacheKey],
      brokenImage: "/frontend/static/img/room.svg",
      shapeProperties: {
        useImageSize: false,
        useBorderWithImage: true,
      },
      size: 155,
      widthConstraint: { minimum: NODE_SIZE, maximum: NODE_SIZE },
      heightConstraint: { minimum: NODE_SIZE, maximum: NODE_SIZE },
      borderWidth: 4,
      borderWidthSelected: 6,
      color: { border: "#6b4d30" },
      shadow: {
        enabled: true,
        color: "rgba(0,0,0,0.3)",
        size: 8,
        x: 2,
        y: 2,
      },
    };
  });
  logger.log(`✅ Created ${initialNodes.length} initial nodes`);

  // ✅ 步骤8：构建高质感隧道
  const edges = buildBeautifulEdges(uniqueEdges, separatedPositions);
  logger.log("✅ Built", edges.length, "beautiful edges (2 layers per edge)");

  // ✅ 步骤9：将布局提交到后端，后端将分配怪物道具并返回完整数据
  const positionsPayload = initialNodes.map((n) => ({
    id: n.id,
    x: n.x,
    y: n.y,
  }));
  const edgesPayload = uniqueEdges.map((e) => ({ from: e.from, to: e.to }));

  let finalDungeonData = dungeonData; // 默认使用传入的数据

  try {
    const resp = await fetch("/api/dungeon/commit_layout", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        positions: positionsPayload,
        edges: edgesPayload,
      }),
    });
    const j = await resp.json();
    if (j.success && j.rooms) {
      // 后端返回了完整数据（包含怪物道具）
      finalDungeonData = {
        rooms: j.rooms,
        boss_room_id: j.boss_room_id,
        player: j.player,
        visited_rooms: j.visited_rooms,
      };
      dungeonData.rooms = j.rooms;
      dungeonData.boss_room_id = j.boss_room_id;
      dungeonData.player = j.player;
      logger.log(
        "✅ Layout committed, received complete dungeon data from backend"
      );
      logger.log("   Monsters:", j.rooms.filter((r) => r.monster).length);
      logger.log("   Treasures:", j.rooms.filter((r) => r.treasure).length);
      logger.log("   Boss room:", j.boss_room_id);
    } else {
      logger.error("❌ commit_layout failed:", j);
    }
  } catch (err) {
    logger.error("❌ commit_layout error", err);
  }

  // ✅ 步骤10：用完整数据重建节点（包含怪物道具）
  const nodes = finalDungeonData.rooms.map((room, index) => {
    const pos = separatedPositions[index];
    const isStartRoom = room.id === 0;
    const isBoss = room.is_boss_room;
    const hasMonster = room.monster !== null && room.monster !== undefined;
    const hasTreasure = room.treasure !== null && room.treasure !== undefined;
    // ✅ 判断是否为玩家当前位置（初始为Room 0）
    const isPlayerRoom =
      finalDungeonData.player &&
      room.id === finalDungeonData.player.current_room;

    // 🎯 统一房间编号显示，不使用emoji区分玩家位置
    const lines = [`#${room.id}`];
    const monsterPower = hasMonster ? room.monster.power : 0;
    const treasureBoost = hasTreasure ? room.treasure.value : 0;

    if (isBoss && hasMonster) {
      lines.push(`👑${room.monster.name} ${room.monster.power}`);
    } else if (hasMonster) {
      lines.push(`👾${room.monster.name} ${room.monster.power}`);
    }
    if (hasTreasure) {
      const t = room.treasure;
      const itemIconMap = {
        Gold: "💰",
        Dagger: "🗡️",
        Sword: "⚔️",
        Amulet: "🔮",
        Potion: "🧪",
        Helmet: "🪖",
        Armor: "🛡️",
        Boots: "🥾",
        Weapon: "🗡️",
        Stone: "🔷",
      };
      const icon = itemIconMap[t.item_type] || "🎁";
      lines.push(`${icon}${t.item_type} +${t.value}`);
    }

    // ✅ 修复：缓存键必须包含怪物、宝箱数值以及玩家位置，确保正确缓存
    const cacheKey = `${room.id}_${isStartRoom}_${isBoss}_${hasMonster}_${hasTreasure}_M${monsterPower}_T${treasureBoost}_P${isPlayerRoom}`;
    if (!iconCache[cacheKey]) {
      iconCache[cacheKey] = createRoomSVGEmbedded(lines, NODE_SIZE, 1.5, {
        isBoss,
        hasMonster,
        hasTreasure,
        isPlayerRoom,
      });
    }

    return {
      id: room.id,
      label: "",
      title: `Room ${room.id}${
        hasMonster
          ? `\nMonster: ${room.monster.name} (${room.monster.power})`
          : ""
      }${hasTreasure ? `\nTreasure: ${room.treasure.name}` : ""}`,
      x: pos.x,
      y: pos.y,
      fixed: { x: true, y: true },
      shape: "image",
      image: iconCache[cacheKey],
      brokenImage: "/frontend/static/img/room.svg",
      shapeProperties: {
        useImageSize: false,
        useBorderWithImage: true,
      },
      size: isPlayerRoom ? 160 : 155,
      widthConstraint: { minimum: NODE_SIZE, maximum: NODE_SIZE },
      heightConstraint: { minimum: NODE_SIZE, maximum: NODE_SIZE },
      // ✅ 根据是否为玩家房间设置不同样式
      borderWidth: isPlayerRoom ? 7 : 4,
      borderWidthSelected: isPlayerRoom ? 8 : 6,
      color: isPlayerRoom
        ? {
            border: "#2A9D8F", // 典雅清新（青绿色）
            background: "rgba(42,157,143,0.12)",
            highlight: {
              border: "#4FB3A6", // 清新高亮
              background: "rgba(79,179,166,0.20)",
            },
          }
        : { border: "#6b4d30" },
      shadow: isPlayerRoom
        ? {
            enabled: true,
            color: "rgba(75,0,130,0.6)", // 靛蓝光晕
            size: 20,
            x: 0,
            y: 0,
          }
        : {
            enabled: true,
            color: "rgba(0,0,0,0.3)",
            size: 8,
            x: 2,
            y: 2,
          },
    };
  });
  logger.log(
    `✅ Rebuilt ${nodes.length} nodes with complete data (monsters & treasures)`
  );

  // 初始化玩家位置跟踪
  previousPlayerRoom = 0;

  // 销毁旧网络
  if (network) {
    network.destroy();
    network = null;
  }

  // 创建vis-network
  const data = { nodes, edges };
  const options = {
    autoResize: false, // ✅ 禁用自动调整大小，防止模态打开时地图重排
    layout: {
      randomSeed: undefined,
      improvedLayout: false,
    },
    physics: { enabled: false },
    interaction: {
      hover: true,
      tooltipDelay: 100,
      zoomView: false, // 禁用缩放，与 original_index.html 一致
      // 禁用视图拖拽，防止用户移动整个地图
      dragView: false,
      // 禁止拖拽节点，确保房间位置固定
      dragNodes: false,
      // 降低交互复杂性，防止意外选择或多选导致布局变化
      multiselect: false,
      selectConnectedEdges: false,
    },
    nodes: {
      shapeProperties: { useImageSize: false },
      size: NODE_SIZE / 2,
      chosen: false,
    },
    edges: {
      // 不设置全局 smooth: false，让每条边可以独立控制曲线
      chosen: false,
      width: 2,
    },
  };

  try {
    network = new vis.Network(container, data, options);
    window._dungeonNetwork = network;
    logger.log("✅ vis-network created");

    // 设置 canvas 背景透明
    const canvas = container.querySelector("canvas");
    if (canvas) {
      canvas.style.backgroundColor = "transparent";
      logger.log("✅ Canvas background set to transparent");
    }

    // Note: autoResize is disabled via options; do NOT override
    // `network.activator.dom.rootWindow` — doing so can break event
    // propagation in some vis-network builds. Keep default behavior.

    network.on("click", (params) => {
      if (params.nodes.length > 0) {
        const roomId = params.nodes[0];
        logger.log("[DEBUG] map_renderer click -> roomId:", roomId);
        if (opts.onNodeClick) {
          try {
            opts.onNodeClick(roomId);
          } catch (err) {
            logger.error("opts.onNodeClick error:", err);
          }
        }
      }
    });

    // Fallback: attach container click handler to detect clicks that
    // don't reach vis-network (some environments may swallow vis events).
    try {
      container.addEventListener("click", (ev) => {
        try {
          // Quick log for diagnostics
          logger.log("[DEBUG] map_container click at:", ev.clientX, ev.clientY);

          // If vis click already handled, params.nodes would have fired above.
          // Use network.DOMtoCanvas to map client coords to canvas coords,
          // then find nearest node by positions.
          if (!network || !opts.onNodeClick) return;

          const canvasPos = network.DOMtoCanvas({
            x: ev.clientX,
            y: ev.clientY,
          });
          const positions = network.getPositions();
          let nearestId = null;
          let nearestDist = Infinity;
          const threshold = 120; // px in canvas coordinates

          for (const [id, pos] of Object.entries(positions)) {
            const dx = pos.x - canvasPos.x;
            const dy = pos.y - canvasPos.y;
            const d = Math.hypot(dx, dy);
            if (d < nearestDist) {
              nearestDist = d;
              nearestId = id;
            }
          }

          if (nearestId !== null && nearestDist <= threshold) {
            logger.log(
              "[DEBUG] fallback detected nearest node:",
              nearestId,
              "dist:",
              nearestDist
            );
            try {
              opts.onNodeClick(Number(nearestId));
            } catch (err) {
              logger.error("fallback onNodeClick error:", err);
            }
          }
        } catch (e) {
          logger.warn("fallback container click handler error:", e);
        }
      });
    } catch (e) {
      logger.warn("Failed to attach fallback container click handler:", e);
    }

    // 自动适应视图
    setTimeout(() => {
      network.fit({ animation: { duration: 300 }, padding: 80 });
      logger.log("✅ View fitted");
    }, 100);

    logger.log("✅ Map render complete");

    if (opts.onRenderComplete) {
      opts.onRenderComplete(finalDungeonData);
    }

    return network;
  } catch (error) {
    logger.error("❌ vis-network creation failed:", error);
    throw error;
  }
}

/**
 * 更新地图上的玩家位置标记
 */
export function updatePlayerMarkerOnMap(newRoomId, dungeonData) {
  if (!network || !dungeonData) return;

  const nodes = dungeonData.rooms.map((room) => {
    const isBoss = room.is_boss_room;
    const hasMonster = room.monster !== null && room.monster !== undefined;
    const hasTreasure = room.treasure !== null && room.treasure !== undefined;
    const hasPlayer = room.id === newRoomId;
    const isVisited = visitedRooms.has(room.id) && room.id !== newRoomId;

    // 已访问房间隐藏内容
    const displayRoom = isVisited
      ? { ...room, monster: null, treasure: null }
      : room;

    // 🎯 统一房间编号显示，不使用emoji
    const lines = [`#${room.id}`];
    if (!isVisited) {
      // ✨ 处理被击败的怪物（显示删除线）
      if (displayRoom.defeated_monster_name) {
        if (displayRoom.is_boss_room) {
          lines.push(`👑~~${displayRoom.defeated_monster_name}~~`);
        } else {
          lines.push(`👾~~${displayRoom.defeated_monster_name}~~`);
        }
      } else if (displayRoom.is_boss_room && displayRoom.monster) {
        lines.push(
          `👑${displayRoom.monster.name} ${displayRoom.monster.power}`
        );
      } else if (displayRoom.monster) {
        lines.push(
          `👾${displayRoom.monster.name} ${displayRoom.monster.power}`
        );
      }

      if (displayRoom.treasure) {
        const t = displayRoom.treasure;
        const itemIconMap = {
          Gold: "💰",
          Dagger: "🗡️",
          Sword: "⚔️",
          Amulet: "🔮",
          Potion: "🧪",
          Helmet: "🪖",
          Armor: "🛡️",
          Boots: "🥾",
          Weapon: "🗡️",
          Stone: "🔷",
        };
        const icon = itemIconMap[t.item_type] || "🎁";
        lines.push(`${icon}${t.item_type} +${t.value}`);
      }
    }

    const cacheKey = `${room.id}_${hasPlayer}_${isVisited}`;
    if (!iconCache[cacheKey]) {
      // 已访问/玩家状态图标使用与 NODE_SIZE 相对的更小尺寸
      iconCache[cacheKey] = createRoomSVGEmbedded(lines, 270, 1.5, {
        isBoss: isVisited ? false : isBoss,
        hasMonster: isVisited ? false : hasMonster,
        hasTreasure: isVisited ? false : hasTreasure,
        isPlayerRoom: hasPlayer,
      });
    }

    // 玩家所在房间有特殊靛蓝色边框
    const nodeUpdate = {
      id: room.id,
      image: iconCache[cacheKey],
    };

    if (hasPlayer) {
      // 玩家当前所在房间 - 优雅的靛蓝色边框
      nodeUpdate.borderWidth = 7;
      nodeUpdate.borderWidthSelected = 8;
      nodeUpdate.size = 160;
      nodeUpdate.color = {
        border: "#2A9D8F", // 典雅清新（青绿色）
        background: "rgba(42,157,143,0.12)",
        highlight: {
          border: "#4FB3A6", // 清新高亮
          background: "rgba(79,179,166,0.20)",
        },
      };
      nodeUpdate.shadow = {
        enabled: true,
        color: "rgba(42,157,143,0.45)", // 清新光晕
        size: 20,
        x: 0,
        y: 0,
      };
    } else {
      // 非玩家房间 - 普通边框
      nodeUpdate.borderWidth = 4;
      nodeUpdate.borderWidthSelected = 6;
      nodeUpdate.size = 155;
      nodeUpdate.color = { border: "#6b4d30" };
      nodeUpdate.shadow = {
        enabled: true,
        color: "rgba(0,0,0,0.3)",
        size: 8,
        x: 2,
        y: 2,
      };
    }

    return nodeUpdate;
  });

  network.body.data.nodes.update(nodes);
  previousPlayerRoom = newRoomId;
  visitedRooms.add(newRoomId);
}

// ==================== 路径高亮功能 ====================

// 全局保存的原始样式（用于完整恢复）
let savedOriginalStyles = null;

/**
 * 高亮显示路径（简化版：直接高亮，支持双向箭头）
 * 核心特性：
 * 1. 节点显示完整访问序列（多次到访显示所有步序）
 * 2. 不使用曲线，直接正常高亮边
 * 3. 如果边已被高亮，在原有基础上增加另一个方向的箭头（双向箭头）
 * 4. 边标签显示所有经过的步序
 *
 * @param {Array<number>} path - 房间ID数组（可以包含重复节点）
 * @param {string} color - 高亮颜色 (默认: #FFD700 金色)
 * @param {number} width - 边的宽度 (默认: 8)
 */
export function highlightPath(path, color = "#FFD700", width = 8) {
  if (!network || !path || path.length < 2) {
    logger.warn("无法高亮路径：network未初始化或路径无效");
    return;
  }

  // 先清除之前的高亮（如果存在）
  clearPathHighlight();

  // 保存原始样式
  const edges = network.body.data.edges.get();
  const nodes = network.body.data.nodes.get();
  savedOriginalStyles = {
    edges: new Map(),
    nodes: new Map(),
  };

  edges.forEach((e) => {
    savedOriginalStyles.edges.set(e.id, JSON.parse(JSON.stringify(e)));
  });
  nodes.forEach((n) => {
    savedOriginalStyles.nodes.set(n.id, JSON.parse(JSON.stringify(n)));
  });

  // ===== 第1步：分析路径，收集节点访问信息和边的使用信息 =====
  const nodeVisits = new Map(); // roomId -> [步序数组]
  const edgeUsage = new Map(); // "edgeId" -> [{step, from, to}]

  path.forEach((roomId, idx) => {
    if (!nodeVisits.has(roomId)) {
      nodeVisits.set(roomId, []);
    }
    nodeVisits.get(roomId).push(idx);
  });

  // 找到边并记录使用情况
  for (let i = 0; i < path.length - 1; i++) {
    const from = path[i];
    const to = path[i + 1];

    // 找到对应的边
    const edge = edges.find(
      (e) =>
        (e.from === from && e.to === to) || (e.from === to && e.to === from)
    );

    if (!edge) continue;

    if (!edgeUsage.has(edge.id)) {
      edgeUsage.set(edge.id, []);
    }

    edgeUsage.get(edge.id).push({
      step: i + 1,
      from: from,
      to: to,
    });
  }

  // ===== 第2步：处理边的高亮（不使用曲线，支持双向箭头） =====
  const edgesToUpdate = [];

  edgeUsage.forEach((usages, edgeId) => {
    const currentEdge = edges.find((e) => e.id === edgeId);
    if (!currentEdge) return;

    const update = JSON.parse(JSON.stringify(currentEdge));

    // 不使用曲线
    update.smooth = { enabled: false };

    // 高亮样式
    update.color = { color: color, highlight: color, opacity: 1.0 };
    update.width = width + 2;
    update.shadow = {
      enabled: true,
      color: color,
      size: 14,
      x: 0,
      y: 0,
    };
    update.dashes = false;

    // 判断箭头方向：检查是否有正向和反向的使用
    const hasForward = usages.some(
      (u) => u.from === currentEdge.from && u.to === currentEdge.to
    );
    const hasBackward = usages.some(
      (u) => u.from === currentEdge.to && u.to === currentEdge.from
    );

    // 根据使用情况设置箭头（如果同时有正向和反向，则显示双向箭头）
    update.arrows = {
      to: {
        enabled: hasForward,
        scaleFactor: 1.2,
        type: "arrow",
      },
      from: {
        enabled: hasBackward,
        scaleFactor: 1.2,
        type: "arrow",
      },
    };

    // 边标签：显示所有步序
    const steps = usages.map((u) => u.step).sort((a, b) => a - b);
    update.label =
      steps.length === 1 ? `步${steps[0]}` : `步${steps.join(",")}`;
    update.font = {
      color: "#ffffff",
      size: 24,
      background: color,
      strokeWidth: 0,
      bold: true,
      align: "middle",
    };

    update._highlighted = true;
    update._steps = steps;

    edgesToUpdate.push(update);
  });

  // ===== 第3步：处理节点的高亮（显示完整访问序列） =====
  const nodesToUpdate = [];

  nodeVisits.forEach((visits, roomId) => {
    const nodeData = nodes.find((n) => n.id === roomId);
    if (!nodeData) return;

    const update = JSON.parse(JSON.stringify(nodeData));

    const isStart = visits.includes(0);
    const isEnd = visits.includes(path.length - 1);
    const visitCount = visits.length;

    // 多次访问显示访问序列
    let visitLabel = "";
    if (visitCount === 1) {
      const stepNum = visits[0];
      if (isStart) {
        visitLabel = "🏁起点";
      } else if (isEnd) {
        visitLabel = "🎯终点";
      } else {
        visitLabel = `步${stepNum}`;
      }
    } else {
      // 多次访问：显示所有步序
      visitLabel = `步${visits.join(",")}`;
    }

    // 节点样式增强
    update.borderWidth = isStart || isEnd ? 16 : visitCount > 1 ? 14 : 12;
    update.borderWidthSelected = update.borderWidth + 3;

    update.color = {
      border: color,
      background: nodeData.color && nodeData.color.background,
      highlight: {
        border: color,
        background: nodeData.color && nodeData.color.background,
      },
    };

    update.shadow = {
      enabled: true,
      color: color,
      size: isStart || isEnd ? 45 : visitCount > 1 ? 35 : 30,
      x: 0,
      y: 0,
    };

    update.font = {
      color: "#ffffff",
      size: visitCount > 1 ? 28 : 32,
      strokeWidth: 6,
      strokeColor: color,
      bold: true,
    };

    // 多次访问用双虚线边框标识
    update.shapeProperties = {
      borderDashes:
        visitCount > 1 ? [8, 4, 2, 4] : isStart || isEnd ? [10, 5] : false,
      borderRadius: 50,
    };

    // 标签：保留原始节点标签（移除步序标注）
    update.label = nodeData.label || "";

    // 悬浮提示：详细访问信息（通过title属性）
    const visitDetails = visits.map((v) => `步${v}`).join(", ");
    update.title = `访问序列: ${visitDetails}\n访问次数: ${visitCount}次`;

    update._highlighted = true;
    update._visitCount = visitCount;
    update._pathColor = color;

    nodesToUpdate.push(update);
  });

  // ===== 第4步：应用所有更新 =====
  try {
    network.body.data.edges.update(edgesToUpdate);
    network.body.data.nodes.update(nodesToUpdate);
    logger.log(
      `✅ 已高亮路径: ${path.length}步, ${nodeVisits.size}个节点, ${edgeUsage.size}条边`
    );
  } catch (e) {
    logger.warn("[highlightPath] update failed:", e);
  }
}

/**
 * 清除路径高亮（完全恢复原始样式）
 */
export function clearPathHighlight() {
  if (!network || !savedOriginalStyles) return;

  const edgeRestores = [];
  const nodeRestores = [];

  savedOriginalStyles.edges.forEach((orig) => {
    const restore = JSON.parse(JSON.stringify(orig));
    // 清除自定义属性
    delete restore._highlighted;
    delete restore._pathIndex;
    delete restore._pathColor;
    delete restore._steps;

    // 恢复箭头设置
    if (orig.arrows) {
      restore.arrows = JSON.parse(JSON.stringify(orig.arrows));
    } else {
      // 如果原始没有箭头，显式关闭
      restore.arrows = { to: { enabled: false }, from: { enabled: false } };
    }

    // 恢复其他可能被修改的属性
    if (orig.smooth !== undefined) {
      restore.smooth = JSON.parse(JSON.stringify(orig.smooth));
    }
    if (orig.shadow !== undefined) {
      restore.shadow = JSON.parse(JSON.stringify(orig.shadow));
    }

    edgeRestores.push(restore);
  });

  savedOriginalStyles.nodes.forEach((orig) => {
    const restore = JSON.parse(JSON.stringify(orig));
    // 清除自定义属性
    delete restore._highlighted;
    delete restore._pathIndex;
    delete restore._pathColor;
    nodeRestores.push(restore);
  });

  if (edgeRestores.length > 0) {
    network.body.data.edges.update(edgeRestores);
  }
  if (nodeRestores.length > 0) {
    network.body.data.nodes.update(nodeRestores);
  }

  savedOriginalStyles = null;
  logger.log("✅ 路径高亮已清除");
}

/**
 * 在地图上显示多条路径（用不同颜色，优化视觉层次）
 * @param {Array<Array<number>>} paths - 路径数组
 * @param {Array<string>} colors - 颜色数组（可选）
 */
export function highlightMultiplePaths(paths, colors = null) {
  if (!network || !paths || paths.length === 0) return;
  const defaultColors = [
    "#FFD700",
    "#FF6B6B",
    "#4ECDC4",
    "#95E1D3",
    "#F38181",
    "#AA96DA",
    "#FCBAD3",
    "#A8D8EA",
  ];
  const useColors = colors || defaultColors;
  clearPathHighlight();
  const edges = network.body.data.edges.get();
  const nodes = network.body.data.nodes.get();
  savedOriginalStyles = {
    edges: new Map(),
    nodes: new Map(),
  };
  // 全量保存所有原始属性
  edges.forEach((e) => {
    savedOriginalStyles.edges.set(e.id, JSON.parse(JSON.stringify(e)));
  });
  nodes.forEach((n) => {
    savedOriginalStyles.nodes.set(n.id, JSON.parse(JSON.stringify(n)));
  });
  const allEdgesToUpdate = [];
  const nodeMap = new Map();
  paths.forEach((path, pathIndex) => {
    const color = useColors[pathIndex % useColors.length];
    const width = Math.max(6, 10 - pathIndex * 0.8);
    for (let i = 0; i < path.length - 1; i++) {
      const from = path[i];
      const to = path[i + 1];
      const edge = edges.find(
        (e) =>
          (e.from === from && e.to === to) || (e.from === to && e.to === from)
      );
      if (edge) {
        const update = JSON.parse(JSON.stringify(edge));
        update.color = {
          color: color,
          highlight: color,
          opacity: pathIndex === 0 ? 1.0 : 0.8,
        };
        update.width = width;
        update.chosen = false;
        update.smooth = { enabled: true, type: "continuous" };
        update.label = `路径${pathIndex + 1}`;
        update.font = {
          color: "#ffffff",
          size: 24,
          background: color,
          strokeWidth: 0,
        };
        update._highlighted = true;
        update._pathIndex = pathIndex;
        allEdgesToUpdate.push(update);
      }
    }
    path.forEach((roomId, index) => {
      if (!nodeMap.has(roomId) || nodeMap.get(roomId).pathIndex > pathIndex) {
        const nodeData = nodes.find((n) => n.id === roomId);
        if (!nodeData) return;
        const update = JSON.parse(JSON.stringify(nodeData));
        update.borderWidth = pathIndex === 0 ? 12 : 10;
        update.color = {
          border: color,
          background: nodeData.color && nodeData.color.background,
        };
        update.shadow = {
          enabled: true,
          color: color,
          size: pathIndex === 0 ? 30 : 20,
          x: 0,
          y: 0,
        };
        update.font = {
          color: "#ffffff",
          size: 32,
          strokeWidth: 6,
          strokeColor: color,
          bold: pathIndex < 3,
        };
        update._highlighted = true;
        update._pathIndex = pathIndex;
        update._pathColor = color;
        nodeMap.set(roomId, { pathIndex, update });
      }
    });
  });
  network.body.data.edges.update(allEdgesToUpdate);
  network.body.data.nodes.update(
    Array.from(nodeMap.values()).map((item) => item.update)
  );
  logger.log(`✅ 已高亮 ${paths.length} 条路径`);
}

/**
 * 清空地图
 */
export function clearMap() {
  if (network) {
    network.destroy();
    network = null;
  }

  const container = document.getElementById("map-container");
  if (container) {
    container.innerHTML = "";
  }

  visitedRooms = [];
  previousPlayerRoom = null;

  logger.log("🗑️ Map cleared");
}
