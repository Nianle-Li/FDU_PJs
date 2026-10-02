"""
图结构实现 + 路径搜索算法
"""
from collections import deque
from typing import Dict, List, Set, Optional, Tuple

from models import Room


class DungeonGraph:  # ✅ 确保类名是 DungeonGraph
    """
    地下城地图图结构（邻接表实现）+ 路径搜索算法
    """
    
    def __init__(self):
        """初始化空图"""
        self.rooms: Dict[int, Room] = {}
        self.adjacency_list: Dict[int, List[int]] = {}
    
    def add_room(self, room: Room) -> None:
        """添加房间到图中"""
        self.rooms[room.id] = room
        if room.id not in self.adjacency_list:
            self.adjacency_list[room.id] = []
    
    def add_edge(self, room1_id: int, room2_id: int) -> None:
        """添加双向边（同时更新 adjacency_list 和 Room.neighbors）"""
        if room1_id not in self.adjacency_list:
            self.adjacency_list[room1_id] = []
        if room2_id not in self.adjacency_list:
            self.adjacency_list[room2_id] = []
        
        # 避免重复边
        if room2_id not in self.adjacency_list[room1_id]:
            self.adjacency_list[room1_id].append(room2_id)
        if room1_id not in self.adjacency_list[room2_id]:
            self.adjacency_list[room2_id].append(room1_id)
        
        # 同步更新 Room 对象的 neighbors 字段
        if room1_id in self.rooms and room2_id not in self.rooms[room1_id].neighbors:
            self.rooms[room1_id].neighbors.append(room2_id)
        if room2_id in self.rooms and room1_id not in self.rooms[room2_id].neighbors:
            self.rooms[room2_id].neighbors.append(room1_id)
    
    def get_room(self, room_id: int) -> Optional[Room]:
        """获取房间对象"""
        return self.rooms.get(room_id)
    
    def get_neighbors(self, room_id: int) -> List[int]:
        """获取相邻房间ID列表"""
        return self.adjacency_list.get(room_id, [])
    
    def is_connected(self, room1_id: int, room2_id: int) -> bool:
        """判断两个房间是否连通（使用BFS）"""
        if room1_id not in self.rooms or room2_id not in self.rooms:
            return False
        
        visited = {room1_id}
        queue = deque([room1_id])
        
        while queue:
            current = queue.popleft()
            if current == room2_id:
                return True
            
            for neighbor in self.get_neighbors(current):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        
        return False
    
    def get_all_room_ids(self) -> List[int]:
        """获取所有房间ID"""
        return list(self.rooms.keys())
    
    def get_boss_room_id(self) -> Optional[int]:
        """获取Boss房间ID"""
        for room_id, room in self.rooms.items():
            if room.is_boss_room:
                return room_id
        return None
    
    # ===== 路径搜索算法 =====
    
    def bfs_shortest_path(self, start: int, end: int, 
                           initial_power: int = 10) -> Optional[List[int]]:
        """
        【优化版】最短可行路径：直接从 dfs_all_feasible_paths 的结果中获取
        
        核心思路：
        - dfs_all_feasible_paths 使用状态空间BFS，已经枚举了所有宝箱组合
        - 每个组合对应的路径是BFS找到的最短路径
        - 不收集任何宝箱的路径（mask=0）就是物理最短可行路径
        - 如果没有mask=0的路径，说明必须收集宝箱才能通过
        
        优势：
        - 避免重复计算：利用已有的完整枚举结果
        - 算法统一：与价值排名使用相同的搜索机制
        - 保证正确：BFS确保是最短路径
        
        Args:
            start: 起始房间ID
            end: 目标房间ID
            initial_power: 初始战力值（默认10）
        
        Returns:
            最短可行路径 [start, ..., end]，如果不存在返回 None
        """
        # 复用完整枚举算法
        all_paths = self.dfs_all_feasible_paths(start, end, initial_power)
        
        if not all_paths:
            return None
        
        # 返回最短的路径（所有路径都是各自宝箱组合的最短路径）
        # 按路径长度排序，长度相同时价值高的优先
        return min(all_paths, key=lambda p: (len(p), -self.calculate_path_value(p)))
    
    def dfs_all_feasible_paths(self, start: int, end: int, 
                                player_power: int) -> List[List[int]]:
        """
        【完全重构版】状态空间 BFS：枚举所有可达的宝箱组合及其最短路径
        
        核心算法（基于状态图的完全搜索）：
        1. 状态表示：(room_id, treasure_mask) - 房间位置 + 已收集宝箱的位掩码
        2. BFS 穷举：从起点开始，遍历所有可达状态，保证不遗漏任何宝箱组合
        3. 最短路径：每个状态第一次被 BFS 发现时即为该状态的最短路径
        4. 战力计算：根据位掩码动态计算当前战力，判断能否进入下一房间
        5. 路径记录：使用 parent 字典回溯完整路径
        
        理论保证：
        - 完全性：所有能收集的宝箱组合都会被枚举到
        - 最优性：每个宝箱组合对应的路径是最短的
        - 正确性：排序按总战利品价值，确保价值最高的排第一
        
        时间复杂度：O(V * 2^C)，V=房间数，C=宝箱数（通常 C << V）
        
        Args:
            start: 起始房间ID
            end: 目标房间ID（Boss房间）
            player_power: 玩家初始武力值
        
        Returns:
            所有可行路径的列表（每条路径是房间ID列表）
        """
        if start not in self.rooms or end not in self.rooms:
            return []
        
        # ===== 第1步：预处理 - 识别所有有宝箱的房间 =====
        treasure_rooms = []  # 有宝箱的房间ID列表
        treasure_idx = {}    # room_id -> 位掩码索引
        treasure_info = {}   # 位索引 -> (room_id, boost, value)
        
        for room_id, room in self.rooms.items():
            if room.treasure:
                idx = len(treasure_rooms)
                treasure_rooms.append(room_id)
                treasure_idx[room_id] = idx
                treasure_info[idx] = (
                    room_id, 
                    room.treasure.value, 
                    room.treasure.value
                )
        
        num_treasures = len(treasure_rooms)
        
        # 如果没有宝箱，退化为简单最短路径（纯BFS）
        if num_treasures == 0:
            # 不使用已删除的函数，直接在这里实现简单BFS
            if start == end:
                return [[start]]
            
            queue_simple = deque([(start, [start])])
            visited_simple = {start}
            
            while queue_simple:
                curr, path = queue_simple.popleft()
                
                for neighbor in self.get_neighbors(curr):
                    if neighbor in visited_simple:
                        continue
                    
                    neighbor_room = self.rooms[neighbor]
                    monster_power = neighbor_room.monster.power if neighbor_room.monster else 0
                    if player_power <= monster_power:
                        continue  # 战力不足
                    
                    new_path = path + [neighbor]
                    if neighbor == end:
                        return [new_path]  # 找到即返回
                    
                    visited_simple.add(neighbor)
                    queue_simple.append((neighbor, new_path))
            
            return []  # 无可行路径
        
        # ===== 第2步：初始化 BFS =====
        # 状态：(room_id, mask)
        # visited[room_id][mask] = True 表示该状态已访问
        visited = {}
        for room_id in self.rooms.keys():
            visited[room_id] = {}
        
        # parent[(room, mask)] = (prev_room, prev_mask) 用于回溯路径
        parent = {}
        
        # 计算起点的初始掩码（如果起点有宝箱且能收集）
        start_mask = 0
        start_power = player_power
        start_room = self.rooms[start]
        
        if start_room.treasure and start in treasure_idx:
            # 起点宝箱直接收集（无怪物阻挡）
            start_mask = 1 << treasure_idx[start]
            start_power += start_room.treasure.value
        
        # BFS 队列：(room_id, mask, power, path)
        queue = deque([(start, start_mask, start_power, [start])])
        visited[start][start_mask] = True
        parent[(start, start_mask)] = None
        
        # 记录所有到达目标的状态：mask -> (path, total_value)
        end_states = {}
        
        # ===== 第3步：BFS 主循环 - 穷举所有状态 =====
        while queue:
            curr_room, curr_mask, curr_power, curr_path = queue.popleft()
            
            # 如果到达目标，记录这个宝箱组合
            if curr_room == end:
                # 计算这个 mask 的总价值
                total_value = sum(
                    treasure_info[i][2]  # value
                    for i in range(num_treasures)
                    if (curr_mask >> i) & 1
                )
                
                # 只保留第一次到达该 mask 的路径（即最短路径）
                if curr_mask not in end_states:
                    end_states[curr_mask] = (curr_path, total_value)
                continue
            
            # 尝试扩展到所有邻居
            for neighbor in self.get_neighbors(curr_room):
                neighbor_room = self.rooms[neighbor]
                
                # 检查是否能进入（战力 > 怪物战力）
                monster_power = neighbor_room.monster.power if neighbor_room.monster else 0
                if curr_power <= monster_power:
                    continue  # 战力不足，跳过
                
                # 计算新的掩码（如果邻居有宝箱则收集）
                new_mask = curr_mask
                new_power = curr_power
                
                if neighbor in treasure_idx:
                    bit = treasure_idx[neighbor]
                    # 只有未收集过才更新掩码和战力
                    if not ((curr_mask >> bit) & 1):
                        new_mask = curr_mask | (1 << bit)
                        # 类型检查：确保 treasure 不为 None
                        if neighbor_room.treasure:
                            new_power = curr_power + neighbor_room.treasure.value
                
                # 检查是否已访问过这个状态
                if new_mask not in visited[neighbor]:
                    visited[neighbor][new_mask] = True
                    parent[(neighbor, new_mask)] = (curr_room, curr_mask)
                    
                    # 入队
                    new_path = curr_path + [neighbor]
                    queue.append((neighbor, new_mask, new_power, new_path))
        
        # ===== 第4步：提取所有可行路径 =====
        if not end_states:
            return []  # 没有任何可行路径
        
        # 转换为路径列表（已经是最短路径）
        all_paths = [path for path, _ in end_states.values()]
        
        return all_paths
    
    def rank_by_treasure_value(self, paths: List[List[int]]) -> List[Tuple[List[int], int]]:
        """按战利品总价值对路径排序"""
        path_values = [(path, self.calculate_path_value(path)) for path in paths]
        return sorted(path_values, key=lambda x: x[1], reverse=True)
    
    def calculate_path_value(self, path: List[int]) -> int:
        """
        【重构版】精确计算路径的战利品总价值
        
        策略：严格模拟玩家沿路径行走，只收集路径上直接经过的房间的宝箱
        不再使用"贪心绕道"策略，因为 dfs_all_feasible_paths 已经通过
        状态空间搜索穷举了所有可能的宝箱组合。
        
        注意：此函数用于对已枚举的路径进行价值计算和排序
        """
        if not path:
            return 0
        
        total_value = 0
        power = 10  # 初始战力
        
        for room_id in path:
            room = self.get_room(room_id)
            if not room:
                continue
            
            # 检查是否能战胜怪物
            if room.monster:
                if power <= room.monster.power:
                    # 路径不可行，返回0价值
                    return 0
            
            # 收集宝箱
            if room.treasure:
                total_value += room.treasure.value
                power += room.treasure.value
        
        return total_value
    
    def get_path_details(self, path: List[int], initial_power: int = 10) -> dict:
        """
        获取路径的详细信息（用于前端展示）
        
        Returns:
            {
                'path': List[int],               # 路径房间ID列表
                'length': int,                   # 路径长度（探索次数）
                'total_treasure_value': int,     # 总战利品价值
                'total_power_boost': int,        # 总武力值提升
                'final_power': int,              # 最终武力值
                'feasible': bool,                # 路径是否可行
                'rooms_info': List[dict],        # 每个房间的详细信息
                'combat_log': List[str]          # 战斗日志
            }
        """
        if not path:
            return {
                'path': [],
                'length': 0,
                'total_treasure_value': 0,
                'total_power_boost': 0,
                'final_power': initial_power,
                'feasible': False,
                'rooms_info': [],
                'combat_log': ['路径为空']
            }
        
        rooms_info = []
        combat_log = []
        current_power = initial_power
        total_value = 0
        total_boost = 0
        feasible = True
        
        for i, room_id in enumerate(path):
            room = self.get_room(room_id)
            if not room:
                combat_log.append(f"❌ 房间 {room_id} 不存在")
                feasible = False
                break
            
            room_info = {
                'id': room_id,
                'name': room.name,
                'step': i,
                'power_before': current_power
            }
            
            # 检查怪物战斗
            if room.monster:
                monster_power = room.monster.power
                room_info['monster'] = {
                    'name': room.monster.name,
                    'power': monster_power,
                    'is_boss': room.monster.is_boss
                }
                
                if current_power > monster_power:
                    combat_log.append(
                        f"✅ 步骤 {i}: 房间 {room_id} - 战胜 {room.monster.name} "
                        f"(怪物武力 {monster_power} < 玩家武力 {current_power})"
                    )
                    room_info['combat_result'] = 'victory'
                else:
                    combat_log.append(
                        f"❌ 步骤 {i}: 房间 {room_id} - 无法战胜 {room.monster.name} "
                        f"(怪物武力 {monster_power} >= 玩家武力 {current_power})"
                    )
                    room_info['combat_result'] = 'defeat'
                    feasible = False
            else:
                room_info['monster'] = None
                room_info['combat_result'] = 'no_combat'
            
            # 收集宝箱
            if room.treasure:
                treasure_value = room.treasure.value
                room_info['treasure'] = {
                    'name': room.treasure.name,
                    'type': room.treasure.item_type,
                    'value': treasure_value
                }
                
                current_power += treasure_value
                total_value += treasure_value
                total_boost += treasure_value
                
                combat_log.append(
                    f"💎 步骤 {i}: 房间 {room_id} - 获得宝箱 {room.treasure.name} "
                    f"(武力 +{treasure_value} → {current_power})"
                )
            else:
                room_info['treasure'] = None
            
            room_info['power_after'] = current_power
            rooms_info.append(room_info)
            
            # 如果路径不可行，停止模拟
            if not feasible:
                break
        
        return {
            'path': path,
            'length': len(path) - 1,  # 探索次数 = 房间数 - 1
            'total_treasure_value': total_value,
            'total_power_boost': total_boost,
            'final_power': current_power,
            'feasible': feasible,
            'rooms_info': rooms_info,
            'combat_log': combat_log
        }
    
    def to_dict(self) -> dict:
        """转换为JSON格式"""
        return {
            "rooms": [room.to_dict() for room in self.rooms.values()],
            "boss_room_id": self.get_boss_room_id()
        }
    
    def __len__(self) -> int:
        """返回房间数量"""
        return len(self.rooms)

    def clear(self) -> None:
        """清空图的边信息（保留 rooms 字典），用于重建邻接关系"""
        self.adjacency_list = {}
        # 同时清空所有 Room 的 neighbors
        for room in self.rooms.values():
            room.neighbors = []
