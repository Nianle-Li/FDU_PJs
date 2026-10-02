"""
地下城服务 - 地图生成、战斗系统、Boss移动
"""
import random
from typing import Dict, List, Optional
from datetime import datetime
from models import Room, Monster, Treasure, Player
from graph import DungeonGraph  # ✅ 确保导入 DungeonGraph
from tree import TreasureTree
from config import DEBUG


class DungeonService:
    """地下城核心业务逻辑"""
    
    # 怪物名称库（英文）
    MONSTER_NAMES = [
        "Goblin", "Skull", "Shade", "Fire", "Ice",
        "Viper", "Wolf", "Ogre", "Ghost", "Gargoyle",
        "Knight", "Mage", "Demon", "Drake", "Vampire",
        "Slime", "Orc", "Bat", "Golem", "Plant",
        "Worm", "Troll", "Bolt"
    ]
    
    # Boss名称（英文）
    BOSS_NAME = "Boss"
    
    # 道具名称库（英文）
    TREASURE_NAMES = {
        "Helmet": ["IronHelmet", "KnightHelmet", "DragonHelmet", "ShadowHood", "Crown"],
        "Armor": ["LeatherArmor", "ChainMail", "PlateMail", "DragonArmor", "HolyArmor"],
        "Boots": ["ClothShoes", "LeatherBoots", "IronBoots", "WindBoots", "FlyingBoots"],
        "Weapon": ["Dagger", "Sword", "Axe", "MagicStaff", "HolySword"],
        "Stone": ["FireStone", "IceStone", "ThunderStone", "ShadowStone", "LightStone"]
    }
    
    def __init__(self):
        self.graph = DungeonGraph()
        self.player = Player()
        self.boss_room_id: Optional[int] = None
        self.displaced_monster: Optional[Monster] = None  # 保存被Boss替代的怪兽
        self.boss_movement_paused = False  # ✅ 新增：Boss移动暂停标志
        self.game_status = "idle"  # 游戏状态: idle, playing, victory, defeat
        self.game_start_time = None
        self.game_end_time = None
    
    def create_empty_dungeon(self, num_rooms: int = 20) -> dict:
        """
        创建空房间框架（不分配怪物、道具、邻居关系）
        前端将生成布局后调用commit_layout完成地图
        
        Returns:
            包含空房间列表的字典
        """
        # 设置游戏状态
        self.game_status = "playing"
        self.game_start_time = datetime.now()
        self.game_end_time = None
        
        # 清空现有数据
        self.graph = DungeonGraph()
        self.player = Player()
        self.boss_room_id = None
        
        # 创建空房间
        rooms = []
        for i in range(num_rooms):
            is_boss = (i == num_rooms - 1)  # 最后一个房间是Boss房间
            room = Room(id=i, name=f"Room{i}", is_boss_room=is_boss)
            rooms.append(room)
            self.graph.add_room(room)
        
        return {
            "rooms": [room.to_dict() for room in rooms],
            "boss_room_id": num_rooms - 1,
            "player": {"current_room": 0, "power": 10, "inventory_count": 0, "visited_count": 1},
            "visited_rooms": [0]
        }
    
    def generate_dungeon(self, num_rooms: int = 20) -> dict:
        """
        生成随机地下城
        
        Args:
            num_rooms: 房间数量（默认20）
        
        Returns:
            地图数据字典
        """
        # 1. 创建房间
        rooms = self._create_rooms(num_rooms)
        
        # 2. 先分配宝箱（路径上随机放置）
        self._assign_treasures(rooms)
        
        # 3. 再分配怪物（根据玩家武力值严格计算）
        self._assign_monsters(rooms)
        
        # 4. 验证路径可行性（仅打印，不调整）
        self._ensure_solvability(rooms)
        
        # 5. 添加房间到图
        for room in rooms:
            self.graph.add_room(room)
        
        # 6. 添加边
        for room in rooms:
            for neighbor_id in room.neighbors:
                self.graph.add_edge(room.id, neighbor_id)
        
        # 7. 记录Boss房间
        self.boss_room_id = self.graph.get_boss_room_id()
        
        # 8. 初始化玩家
        self.player = Player()
        self.player.move_to(0)  # 从房间0开始
        
        return {
            "rooms": [room.to_dict() for room in rooms],
            "boss_room_id": self.boss_room_id,
            "player": self.player.to_dict(),
            "visited_rooms": list(self.player.visited_rooms)
        }
    
    def _create_rooms(self, num_rooms: int) -> List[Room]:
        """创建指定数量的房间"""
        rooms = []
        for i in range(num_rooms):
            is_boss = (i == num_rooms - 1)  # 最后一个房间是Boss房间
            room = Room(id=i, name=f"房间 {i}", is_boss_room=is_boss)
            rooms.append(room)
        return rooms
    
    def _find_solution_path(self, rooms: List[Room]) -> List[int]:
        """
        找到从Room 0到Boss房间的一条较长路径（使用BFS，优先选择度数小的邻居）
        
        Returns:
            路径房间ID列表 [0, ..., boss_room_id]
        """
        from collections import deque
        
        boss_id = len(rooms) - 1
        
        # BFS搜索，但优先选择度数较小的邻居（更可能产生较长路径）
        queue = deque([(0, [0])])
        visited = {0}
        longest_path = [0, boss_id]  # 默认最短路径
        
        while queue:
            current, path = queue.popleft()
            
            if current == boss_id:
                # 找到一条路径，如果比当前最长路径长则更新
                if len(path) > len(longest_path):
                    longest_path = path
                continue
            
            # 获取邻居并按度数排序（度数小的优先，倾向于走更长的路）
            neighbors = rooms[current].neighbors[:]
            neighbors.sort(key=lambda n: len(rooms[n].neighbors))
            
            for neighbor in neighbors:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        
        # 确保路径至少有3个房间（起点、至少一个中间点、终点）
        if len(longest_path) < 5 and len(rooms) >= 5:
            # 如果路径太短，尝试找一条通过中间房间的路径
            for mid in range(1, len(rooms) - 1):
                if mid in rooms[0].neighbors:
                    if boss_id in rooms[mid].neighbors or any(boss_id in rooms[n].neighbors for n in rooms[mid].neighbors):
                        longest_path = [0, mid, boss_id]
                        break
        
        return longest_path
    
    def _assign_monsters(self, rooms: List[Room]) -> None:
        """
        新算法第二步：在分配宝箱后，遍历路径并根据玩家当前武力值放置怪物
        1. Boss固定power=50
        2. 遍历路径，跟踪玩家武力值变化（收集宝箱）
        3. 在路径上的部分房间放置怪物，确保怪物power严格 < 玩家当前power
        4. 在路径外随机分配剩余怪物以达到40%总比例
        """
        boss_id = len(rooms) - 1
        solution_path = self._find_solution_path(rooms)
        solution_set = set(solution_path)
        
        # 0. 首先确保所有房间的is_boss_room标志都是False
        for room in rooms:
            room.is_boss_room = False
        
        # 1. Boss固定power=50，并设置is_boss_room标志
        boss_room = rooms[boss_id]
        boss_room.monster = Monster(
            name=self.BOSS_NAME,
            power=50,
            is_boss=True
        )
        boss_room.is_boss_room = True  # ✅ 关键：设置Boss房间标志
        
        # 2. 遍历路径，计算进入每个房间前的玩家武力值
        # 注意：玩家只有在打败房间内的怪物后才能获得该房间的宝箱，
        # 所以在为房间分配怪物时必须使用进入该房间之前的武力值（前一个房间的状态）
        initial_power = 10  # 初始武力值
        power_before_room: Dict[int, int] = {0: initial_power}
        curr_power = initial_power

        # 逐步计算：记录到达每个房间之前的武力值，然后如果该房间有宝箱，累加
        for room_id in solution_path[1:]:  # 跳过起点
            power_before_room[room_id] = curr_power
            room = rooms[room_id]
            # 玩家在当前房间获得宝箱的加成是在战斗之后，因此这里累加用于后续房间
            if room.treasure:
                curr_power += room.treasure.value
        
        # 3. 在路径上按顺序放置怪物（除了起点和Boss房间）
        # 计算总怪物数量（40%，包括Boss）
        total_monster_count = int(len(rooms) * 0.4)
        
        # 路径上可以放置怪物的房间（排除起点和Boss房间）
        path_rooms = [rid for rid in solution_path if rid != 0 and rid != boss_id]
        
        # 在路径上放置部分怪物（约40%的总怪物数，不包括Boss）
        target_monsters_on_path = min(len(path_rooms), max(1, int((total_monster_count - 1) * 0.4)))
        
        # 按路径顺序遍历，只在武力值足够的地方放置怪物
        placed_on_path = 0
        monster_interval = max(1, len(path_rooms) // target_monsters_on_path) if target_monsters_on_path > 0 else 1
        
        for i, room_id in enumerate(path_rooms):
            # 跳过部分房间以达到目标数量（均匀分布）
            if i % monster_interval != 0 or placed_on_path >= target_monsters_on_path:
                continue
            
            # 获取玩家进入该房间之前的武力值（这是用于判定能否放怪物的正确值）
            current_power_before = power_before_room.get(room_id, 10)
            
            # 怪物武力值必须严格 < 玩家进入该房间前的武力值，留出安全余量
            max_monster_power = min(boss_room.monster.power - 5, current_power_before - 3)
            
            # 如果进入前的武力值太低（<=11），跳过这个房间，不放置怪物
            if max_monster_power < 8:
                if DEBUG:
                    print(f"  [怪物分配] Room {room_id} 跳过（进入前玩家武力值 {current_power_before} 太低）")
                continue
            
            # 随机设置怪物武力值（范围：5 到 max_monster_power），并保证上限合理
            monster_power = random.randint(5, max(5, max_monster_power))
            
            name = random.choice(self.MONSTER_NAMES)
            rooms[room_id].monster = Monster(name=name, power=monster_power, is_boss=False)
            placed_on_path += 1
            if DEBUG:
                print(f"  [怪物分配] Room {room_id} 怪物power={monster_power} (进入前玩家power={current_power_before})")
        
        # 4. 在路径外随机分配剩余怪物
        remaining_monsters = total_monster_count - 1 - placed_on_path  # 减去Boss和路径上的怪物
        off_path_rooms = [i for i in range(1, len(rooms) - 1) if i not in solution_set]
        
        if remaining_monsters > 0 and len(off_path_rooms) > 0:
            random.shuffle(off_path_rooms)
            for i in range(min(remaining_monsters, len(off_path_rooms))):
                room_id = off_path_rooms[i]
                # 路径外怪物武力值随机（15-45）
                power = random.randint(15, 45)
                name = random.choice(self.MONSTER_NAMES)
                rooms[room_id].monster = Monster(name=name, power=power, is_boss=False)
        

    
    def _assign_treasures(self, rooms: List[Room]) -> None:
        """
        新算法第一步：先在解决路径上按顺序均匀分配宝箱
        1. 在路径上（除了起点和终点）按顺序均匀分布宝箱，确保路径前期有宝箱
        2. 随机设置宝箱的武力值加成（8-15）
        3. 然后在路径外随机分配剩余宝箱以达到30%总比例
        """
        boss_id = len(rooms) - 1
        solution_path = self._find_solution_path(rooms)
        solution_set = set(solution_path)
        
        # 路径上可以放置宝箱的房间（排除起点和Boss房间）
        path_rooms = [rid for rid in solution_path if rid != 0 and rid != boss_id]
        
        # 计算总宝箱数量（30%）
        total_treasure_count = int(len(rooms) * 0.3)
        
        # 在路径上放置足够的宝箱（至少60%的总宝箱数，确保玩家能积累武力值）
        num_treasures_on_path = min(len(path_rooms), max(4, int(total_treasure_count * 0.7)))

        # 按路径顺序均匀分布宝箱（不打乱），确保路径前期就有宝箱
        if len(path_rooms) > 0:
            step = max(1, len(path_rooms) / num_treasures_on_path)
            for i in range(num_treasures_on_path):
                idx = int(i * step)
                if idx < len(path_rooms):
                    room_id = path_rooms[idx]
                    item_type = random.choice(list(self.TREASURE_NAMES.keys()))
                    name = random.choice(self.TREASURE_NAMES[item_type])
                    # 宝箱价值 = 武力值加成：8-27
                    value = random.randint(8, 27)

                    rooms[room_id].treasure = Treasure(
                        item_type=item_type,
                        name=name,
                        value=value
                    )
                    if DEBUG:
                        if DEBUG:
                            print(f"  [宝箱分配] Room {room_id} +{value} power (路径位置 {i+1}/{num_treasures_on_path})")

        # 确保：玩家从初始武力10出发，收集完路径上所有宝箱后武力值必须 > Boss(50)
        # 计算路径上宝箱总加成，如果不足则优先在路径上未放宝箱的房间添加宝箱，
        # 或增强已有宝箱，直到满足条件。
        required_final_power = 52  # 必须严格大于50
        initial_power = 10
        current_total_boost = 0
        for rid in path_rooms:
            t = rooms[rid].treasure
            if t:
                current_total_boost += t.value

        needed_boost = max(0, required_final_power - (initial_power + current_total_boost))
        if needed_boost > 0:
            if DEBUG:
                if DEBUG:
                    print(f"  [宝箱调整] 路径宝箱总加成不足，需要补充 {needed_boost} 武力")

            # 1) 优先在路径上还没有宝箱的房间添加宝箱（每个新宝箱最多15）
            for rid in path_rooms:
                if needed_boost <= 0:
                    break
                if rooms[rid].treasure is None:
                    add = min(15, needed_boost)
                    rooms[rid].treasure = Treasure(
                        item_type="Stone",
                        name="PathBoost",
                        value=add
                    )
                    needed_boost -= add
                    if DEBUG:
                        print(f"   ✅ 在路径房间 {rid} 新增宝箱 +{add} 武力，剩余需补 {needed_boost}")

            # 2) 如果仍不足，增强已有宝箱（单个最多提升到38）
            if needed_boost > 0:
                for rid in path_rooms:
                    if needed_boost <= 0:
                        break
                    t = rooms[rid].treasure
                    if t:
                        cap = 38
                        can_add = cap - t.value
                        if can_add <= 0:
                            continue
                        add = min(can_add, needed_boost)
                        t.value += add
                        needed_boost -= add
                        if DEBUG:
                            print(f"   ✅ 增强房间 {rid} 的宝箱 +{add} 武力，剩余需补 {needed_boost}")
            # 最后防护：如果仍然没满足（极少发生），把剩余加到第一个路径房间的宝箱
            if needed_boost > 0 and len(path_rooms) > 0:
                rid = path_rooms[0]
                t = rooms[rid].treasure
                if t is None:
                    rooms[rid].treasure = Treasure(item_type="Stone", name="PathBoost", value=needed_boost)
                else:
                    t.value += needed_boost
                if DEBUG:
                    if DEBUG:
                        if DEBUG:
                            print(f"   ⚠️ 最后手段：在房间 {rid} 增加剩余 {needed_boost} 武力以保证可解")
        
        # 在路径外随机分配剩余宝箱
        remaining_treasures = total_treasure_count - num_treasures_on_path
        off_path_rooms = [i for i in range(1, len(rooms)) if i not in solution_set and rooms[i].treasure is None]
        
        if remaining_treasures > 0 and len(off_path_rooms) > 0:
            random.shuffle(off_path_rooms)
            for i in range(min(remaining_treasures, len(off_path_rooms))):
                room_id = off_path_rooms[i]
                item_type = random.choice(list(self.TREASURE_NAMES.keys()))
                name = random.choice(self.TREASURE_NAMES[item_type])
                # 宝箱价值 = 武力值加成：5-15
                value = random.randint(5, 15)
                
                rooms[room_id].treasure = Treasure(
                    item_type=item_type,
                    name=name,
                    value=value
                )
    
    def _ensure_solvability(self, rooms: List[Room]) -> None:
        """
        仅验证路径可行性（不做任何调整）
        新算法通过严格计算已经保证路径一定可行
        """
        boss_id = len(rooms) - 1
        solution_path = self._find_solution_path(rooms)
        
        # 模拟玩家沿着解决路径前进，验证可行性
        power = 10  # 初始武力值
        path_details = [f"Room 0 (初始武力值: {power})"]
        
        for room_id in solution_path[1:]:
            room = rooms[room_id]
            
            # 先战斗（如果有怪物）
            if room.monster:
                if power <= room.monster.power:
                    if DEBUG:
                        if DEBUG:
                            print(f"❌ 路径验证失败：Room {room_id} 怪物武力值 {room.monster.power} >= 玩家武力值 {power}")
                        if DEBUG:
                            print(f"   路径详情: {' -> '.join(path_details)}")
                    return
                path_details.append(f"Room {room_id} [战斗: 怪物power={room.monster.power}, 玩家power={power}]")
            
            # 再收集宝箱（如果有）
            if room.treasure:
                power += room.treasure.value
                path_details.append(f"Room {room_id} [宝箱: +{room.treasure.value}, 当前power={power}]")
        
        # 验证最终能否战胜Boss
        boss_room = rooms[boss_id]
        boss_power = boss_room.monster.power if boss_room.monster else 0
        
        if power <= boss_power:
            if DEBUG:
                if DEBUG:
                    print(f"❌ 路径验证失败：玩家最终武力值 {power} <= Boss武力值 {boss_power}")
        else:
            if DEBUG:
                print(f"✅ 路径验证通过：玩家最终武力值 {power} > Boss武力值 {boss_power}")
                print(f"   解决路径: {' -> '.join(map(str, solution_path))}")
                print(f"   路径长度: {len(solution_path)} 个房间")
    
    def _simulate_exploration(self, rooms: List[Room], start: int, boss_id: int, initial_power: int) -> dict:
        """
        模拟玩家从起点开始的BFS探索，真实反映游戏过程
        
        返回:
        {
            'reachable': set,  # 可达的房间ID集合
            'max_power': int,  # 能达到的最大武力值
            'can_beat_boss': bool,  # 是否能战胜boss
            'stuck_rooms': list,  # 被困的房间（所有邻居都进不去）
            'power_at_room': dict  # 到达每个房间时的武力值
        }
        """
        from collections import deque
        
        # BFS状态: (room_id, current_power, collected_treasures_set)
        queue = deque([(start, initial_power, frozenset())])
        
        # 记录每个房间能达到的最大武力值
        max_power_at_room: Dict[int, int] = {start: initial_power}
        reachable: set[int] = {start}
        stuck_rooms: List[int] = []
        
        while queue:
            current_id, power, collected = queue.popleft()
            
            # ✅ 确保current_id有效
            if current_id is None or current_id >= len(rooms) or current_id < 0:
                continue
                
            current_room = rooms[current_id]
            
            # 收集当前房间的宝箱（如果还没收集过）
            current_treasure = current_room.treasure
            if current_treasure is not None and current_id not in collected:
                power += current_treasure.value
                collected = collected | {current_id}
                # 更新该房间的最大武力值 - ✅ 确保current_id不为None
                existing_power = max_power_at_room.get(current_id, 0)
                if power > existing_power:
                    max_power_at_room[current_id] = power
            
            # 检查是否有可进入的邻居
            has_accessible_neighbor = False
            
            # 尝试探索所有邻居
            for neighbor_id in current_room.neighbors:
                # ✅ 验证neighbor_id有效性
                if neighbor_id is None or neighbor_id >= len(rooms) or neighbor_id < 0:
                    continue
                    
                neighbor_room = rooms[neighbor_id]
                neighbor_monster = neighbor_room.monster
                neighbor_monster_power = neighbor_monster.power if neighbor_monster is not None else 0
                
                # 检查武力值是否足够
                if power > neighbor_monster_power:
                    has_accessible_neighbor = True
                    
                    # 如果这是到达该邻居的更好方式，加入队列
                    existing_neighbor_power = max_power_at_room.get(neighbor_id, 0)
                    if neighbor_id not in max_power_at_room or power > existing_neighbor_power:
                        max_power_at_room[neighbor_id] = power
                        reachable.add(neighbor_id)
                        queue.append((neighbor_id, power, collected))
            
            # 如果当前房间所有邻居都进不去，且不是起点，标记为被困
            if not has_accessible_neighbor:
                if current_id not in stuck_rooms:
                    stuck_rooms.append(current_id)
        
        # 检查是否能战胜boss
        boss_room = rooms[boss_id]
        boss_monster = boss_room.monster
        boss_power = boss_monster.power if boss_monster is not None else 0
        max_power = max(max_power_at_room.values()) if max_power_at_room else initial_power
        boss_power_at_arrival = max_power_at_room.get(boss_id, 0)
        can_beat_boss = (boss_id in reachable) and (boss_power_at_arrival > boss_power)
        
        return {
            'reachable': reachable,
            'max_power': max_power,
            'can_beat_boss': can_beat_boss,
            'stuck_rooms': stuck_rooms,
            'power_at_room': max_power_at_room
        }
    
    def _fix_stuck_room(self, rooms: List[Room], stuck_room_id: int, current_power: int) -> None:
        """
        修复被困房间：在其可进入的邻居中削弱怪物或在被困房间添加宝箱
        """
        # ✅ 验证stuck_room_id有效性
        if stuck_room_id is None or stuck_room_id >= len(rooms) or stuck_room_id < 0:
            return
            
        stuck_room = rooms[stuck_room_id]
        
        # 找到所有阻塞的邻居（怪物太强）
        blocking_neighbors: List[tuple[int, int]] = []
        for neighbor_id in stuck_room.neighbors:
            # ✅ 验证neighbor_id有效性
            if neighbor_id is None or neighbor_id >= len(rooms) or neighbor_id < 0:
                continue
                
            neighbor = rooms[neighbor_id]
            neighbor_monster = neighbor.monster
            if neighbor_monster is not None and current_power <= neighbor_monster.power:
                blocking_neighbors.append((neighbor_id, neighbor_monster.power))
        
        if not blocking_neighbors:
            return
        
        # 策略：削弱最弱的阻塞怪物或添加宝箱
        blocking_neighbors.sort(key=lambda x: x[1])  # 按武力值排序
        weakest_blocker_id, weakest_power = blocking_neighbors[0]
        
        # ✅ 再次验证weakest_blocker_id
        if weakest_blocker_id is None or weakest_blocker_id >= len(rooms) or weakest_blocker_id < 0:
            return
        
        # 需要的武力值提升
        needed_boost = weakest_power - current_power + 5
        
        # 优先在被困房间添加宝箱
        if stuck_room.treasure is None and stuck_room_id != 0:
            stuck_room.treasure = Treasure(
                item_type="Stone",
                name="EscapeStone",
                value=needed_boost
            )
            if DEBUG:
                print(f"   ✅ 在被困房间 {stuck_room_id} 添加宝箱 (+{needed_boost} 武力)")
        else:
            # 削弱阻塞怪物
            blocker_room = rooms[weakest_blocker_id]
            blocker_monster = blocker_room.monster
            if blocker_monster is not None:
                old_power = blocker_monster.power
                blocker_monster.power = current_power - 2
                if DEBUG:
                    print(f"   ✅ 削弱房间 {weakest_blocker_id} 的怪物 {old_power} -> {blocker_monster.power}")
        
        # 如果被困房间是room 0，必须削弱阻塞怪物
        if stuck_room_id == 0:
            blocker_room = rooms[weakest_blocker_id]
            blocker_monster = blocker_room.monster
            if blocker_monster is not None:
                old_power = blocker_monster.power
                blocker_monster.power = 5
                if DEBUG:
                    print(f"   ✅ 削弱房间 {weakest_blocker_id} 的怪物 {old_power} -> {blocker_monster.power}")

    def _boost_reachable_treasures(self, rooms: List[Room], reachable: set, needed_power: int, boss_id: int) -> None:
        """
        在可达房间中添加/增强宝箱
        """
        # 优先选择没有宝箱的可达房间（排除room 0和boss房间）
        # ✅ 确保过滤掉None值
        candidates: List[int] = []
        for rid in reachable:
            if rid is not None and rid != 0 and rid != boss_id and 0 <= rid < len(rooms):
                candidates.append(rid)
        
        for room_id in candidates:
            if needed_power <= 0:
                break
            
            # ✅ 再次验证room_id
            if room_id is None or room_id >= len(rooms) or room_id < 0:
                continue
                
            room = rooms[room_id]
            if room.treasure is None:
                boost = min(needed_power, 15)
                room.treasure = Treasure(
                    item_type="Stone",
                    name="PowerStone",
                    value=boost
                )
                needed_power -= boost
                if DEBUG:
                    print(f"   ✅ 在房间 {room_id} 添加宝箱 (+{boost} 武力)")
        
        # 如果还不够，增强现有宝箱
        if needed_power > 0:
            for room_id in candidates:
                if needed_power <= 0:
                    break
                
                # ✅ 再次验证room_id
                if room_id is None or room_id >= len(rooms) or room_id < 0:
                    continue
                    
                room = rooms[room_id]
                if room.treasure:
                    boost = min(needed_power, 10)
                    room.treasure.value += boost
                    needed_power -= boost
                    if DEBUG:
                        print(f"   ✅ 增强房间 {room_id} 的宝箱 (+{boost} 武力)")
    
    def _clear_path_to_boss(self, rooms: List[Room], reachable: set, boss_id: int) -> None:
        """
        清理从可达区域到boss的路径
        """
        from collections import deque
        
        # ✅ 验证boss_id有效性
        if boss_id is None or boss_id >= len(rooms) or boss_id < 0:
            return
        
        # 从boss反向BFS找到最近的可达房间
        boss_room = rooms[boss_id]
        queue: deque[int] = deque([boss_id])
        visited: set[int] = {boss_id}
        parent: Dict[int, Optional[int]] = {boss_id: None}
        
        bridge_room: Optional[int] = None
        while queue:
            current = queue.popleft()
            
            # ✅ 验证current有效性
            if current is None or current >= len(rooms) or current < 0:
                continue
            
            if current in reachable:
                bridge_room = current
                break
                
            for neighbor_id in rooms[current].neighbors:
                # ✅ 验证neighbor_id有效性
                if neighbor_id is None or neighbor_id >= len(rooms) or neighbor_id < 0:
                    continue
                    
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    parent[neighbor_id] = current
                    queue.append(neighbor_id)
        
        # 沿着路径削弱怪物
        if bridge_room is not None:
            path: List[int] = []
            current: Optional[int] = boss_id
            while current is not None and current != bridge_room:
                path.append(current)
                current = parent.get(current)
            
            if DEBUG:
                print(f"   清理路径: {bridge_room} -> {' -> '.join(map(str, reversed(path)))}")
            for room_id in path:
                if room_id is None or room_id >= len(rooms) or room_id < 0:
                    continue
                    
                room = rooms[room_id]
                room_monster = room.monster
                if room_monster is not None and room_id != boss_id:
                    old_power = room_monster.power
                    room_monster.power = max(8, old_power // 2)
                    if DEBUG:
                        print(f"   ✅ 削弱房间 {room_id} 的怪物 {old_power} -> {room_monster.power}")
    
    def _find_reachable_rooms(self, rooms: List[Room], start: int, initial_power: int) -> list:
        """
        找到从起点可达的所有房间（武力值足够通过路上的怪物）
        """
        from collections import deque
        
        reachable: List[int] = []
        queue: deque[tuple[int, int]] = deque([(start, initial_power)])
        visited: set[int] = {start}
        
        while queue:
            current, power = queue.popleft()
            
            # ✅ 验证current有效性
            if current is None or current >= len(rooms) or current < 0:
                continue
                
            reachable.append(current)
            
            room = rooms[current]
            for neighbor_id in room.neighbors:
                # ✅ 验证neighbor_id有效性
                if neighbor_id is None or neighbor_id >= len(rooms) or neighbor_id < 0:
                    continue
                    
                if neighbor_id in visited:
                    continue
                
                neighbor = rooms[neighbor_id]
                neighbor_monster = neighbor.monster
                
                # 检查是否能通过
                if neighbor_monster is not None and power <= neighbor_monster.power:
                    continue
                
                new_power = power
                neighbor_treasure = neighbor.treasure
                if neighbor_treasure is not None:
                    new_power += neighbor_treasure.value
                
                visited.add(neighbor_id)
                queue.append((neighbor_id, new_power))
        
        return reachable
    
    def move_to_room(self, room_id: int, combat_mode: str = "dice") -> dict:
        """
        玩家移动到房间并战斗（骰子对决系统）
        
        战斗机制：
        1. 双方各投一个D20骰子
        2. 总战力 = 基础战力 + 骰子点数
        3. 暴击（20）：总战力翻倍
        4. 大失败（1）：总战力减半
        5. Boss有二次投掷机会（取高值）
        
        Returns:
            {
                "success": bool,
                "power": int,
                "new_treasure": Treasure | None,
                "message": str,
                "combat": dict | None  # 战斗详情
            }
        """
        room = self.graph.get_room(room_id)
        
        if not room:
            return {
                "success": False,
                "power": self.player.power,
                "new_treasure": None,
                "message": "房间不存在",
                "combat": None
            }
        
        # 检查目标房间是否与当前房间相邻
        current_room = self.graph.get_room(self.player.current_room)
        if current_room and room_id not in current_room.neighbors:
            return {
                "success": False,
                "power": self.player.power,
                "new_treasure": None,
                "message": f"房间 {room_id} 与当前房间不相邻，无法移动",
                "combat": None
            }
        
        # 检查目标房间的怪物（如果有）
        room_monster = room.monster
        combat_result = None
        if room_monster is not None:
            monster_type = "Boss" if room_monster.is_boss else "Monster"
            if combat_mode == "power_only":
                # 只比较基础武力值
                if self.player.power > room_monster.power:
                    # 玩家胜利，击败怪物
                    combat_result = {
                        "player_wins": True,
                        "player_base": self.player.power,
                        "monster_base": room_monster.power,
                        "mode": "power_only",
                        "message": f"You defeated the {monster_type} by power! ({self.player.power} > {room_monster.power})",
                        "power_gain": 2,
                        "combat_log": [f"玩家武力值 {self.player.power} > 怪物武力值 {room_monster.power}，直接胜利"]
                    }
                    self.player.power += 2
                    room.defeated_monster_name = room_monster.name
                    room.monster = None
                else:
                    # 玩家失败
                    self.player.power = max(0, self.player.power - 2)
                    game_status_check = self.check_game_status()
                    return {
                        "success": False,
                        "power": self.player.power,
                        "new_treasure": None,
                        "message": f"Your power ({self.player.power}) is not greater than the {monster_type}'s power ({room_monster.power}). Cannot enter room {room_id}.",
                        "combat": {
                            "player_wins": False,
                            "player_base": self.player.power,
                            "monster_base": room_monster.power,
                            "mode": "power_only",
                            "message": f"{monster_type} is too strong! ({self.player.power} <= {room_monster.power})",
                            "power_gain": 0,
                            "combat_log": [f"玩家武力值 {self.player.power} <= 怪物武力值 {room_monster.power}，挑战失败"]
                        },
                        "game_over": game_status_check["game_over"],
                        "game_status": game_status_check["status"],
                        "game_message": game_status_check["message"]
                    }
            else:
                # 默认骰子对决
                combat_result = self._simulate_dice_combat(
                    self.player.power, 
                    room_monster.power,
                    room_monster.is_boss
                )
                if not combat_result["player_wins"]:
                    self.player.power = max(0, self.player.power - 2)
                    game_status_check = self.check_game_status()
                    return {
                        "success": False,
                        "power": self.player.power,
                        "new_treasure": None,
                        "message": combat_result["message"],
                        "combat": combat_result,
                        "game_over": game_status_check["game_over"],
                        "game_status": game_status_check["status"],
                        "game_message": game_status_check["message"]
                    }
                power_gain = combat_result["power_gain"]
                self.player.power += power_gain
                room.defeated_monster_name = room_monster.name
                room.monster = None
        
        # 移动成功
        self.player.move_to(room_id)
        
        # 获得宝箱
        new_treasure = None
        room_treasure = room.treasure
        if room_treasure is not None:
            self.player.add_treasure(room_treasure)
            new_treasure = room_treasure
            room.treasure = None  # 宝箱已拾取
        
        # ✅ 如果击败的是Boss，检查游戏状态
        if room_monster and room_monster.is_boss:
            game_status_check = self.check_game_status()
            if game_status_check["game_over"]:
                return {
                    "success": True,
                    "power": self.player.power,
                    "new_treasure": new_treasure.to_dict() if new_treasure else None,
                    "message": combat_result["message"] if combat_result else "Move successful",
                    "visited_rooms": list(self.player.visited_rooms),
                    "updated_room": room.to_dict(),
                    "combat": combat_result,
                    "game_over": True,
                    "game_status": game_status_check["status"],
                    "game_message": game_status_check["message"]
                }
        
        return {
            "success": True,
            "power": self.player.power,
            "new_treasure": new_treasure.to_dict() if new_treasure else None,
            "message": "移动成功" if not combat_result else combat_result["message"],
            "visited_rooms": list(self.player.visited_rooms),
            "updated_room": room.to_dict(),
            "combat": combat_result
        }
    
    def _simulate_dice_combat(self, player_power: int, monster_power: int, is_boss: bool = False) -> dict:
        """
        骰子对决战斗模拟
        
        Args:
            player_power: 玩家基础战力
            monster_power: 怪物基础战力
            is_boss: 是否为Boss战斗
        
        Returns:
            {
                "player_wins": bool,
                "player_base": int,
                "player_dice": int,
                "player_total": int,
                "monster_base": int,
                "monster_dice": int,
                "monster_total": int,
                "is_critical": bool,
                "is_fumble": bool,
                "power_gain": int,
                "message": str,
                "combat_log": List[str]
            }
        """
        import random
        
        combat_log = []
        
        # 玩家投骰
        player_dice = random.randint(1, 20)
        player_base = player_power
        is_critical = False
        is_fumble = False
        
        # 检查暴击和大失败
        if player_dice == 20:
            is_critical = True
            player_total = player_base * 2 + player_dice
            combat_log.append(f"🎯 玩家暴击！投出 20 点，战力翻倍！")
        elif player_dice == 1:
            is_fumble = True
            player_total = player_base // 2 + player_dice
            combat_log.append(f"💀 玩家大失败！投出 1 点，战力减半！")
        else:
            player_total = player_base + player_dice
            combat_log.append(f"⚔️ 玩家投掷 D20：{player_dice} 点")
        
        # 怪物投骰（Boss有二次机会）
        monster_dice = random.randint(1, 20)
        if is_boss:
            monster_dice2 = random.randint(1, 20)
            monster_dice = max(monster_dice, monster_dice2)
            combat_log.append(f"👑 Boss 特权：投掷两次（{monster_dice2}, {monster_dice}），取高值 {monster_dice}")
        else:
            combat_log.append(f"🛡️ 怪物投掷 D20：{monster_dice} 点")
        
        monster_base = monster_power
        
        # 怪物暴击和大失败
        if monster_dice == 20:
            monster_total = monster_base * 2 + monster_dice
            combat_log.append(f"⚠️ 怪物暴击！战力翻倍！")
        elif monster_dice == 1:
            monster_total = monster_base // 2 + monster_dice
            combat_log.append(f"✨ 怪物大失败！战力减半！")
        else:
            monster_total = monster_base + monster_dice
        
        # 判断胜负
        player_wins = player_total > monster_total
        
        # 计算奖励
        power_gain = 0
        if player_wins:
            power_gain = 3 if is_critical else 2
            combat_log.append(f"")
            combat_log.append(f"🎉 胜利！玩家 {player_total} vs 怪物 {monster_total}")
            combat_log.append(f"💪 获得经验值 +{power_gain}")
        else:
            combat_log.append(f"")
            combat_log.append(f"💔 失败！玩家 {player_total} vs 怪物 {monster_total}")
        
        message = "战斗胜利！" if player_wins else "战斗失败！"
        
        return {
            "player_wins": player_wins,
            "player_base": player_base,
            "player_dice": player_dice,
            "player_total": player_total,
            "monster_base": monster_base,
            "monster_dice": monster_dice,
            "monster_total": monster_total,
            "is_critical": is_critical,
            "is_fumble": is_fumble,
            "power_gain": power_gain,
            "message": message,
            "combat_log": combat_log
        }
    
    def move_boss_randomly(self) -> dict:
        """
        Boss随机移动到相邻房间（增强版 - 允许攻击玩家）
        
        新特性：
        1. Boss只能移动到相邻房间（图连通性）
        2. 可以移动到玩家当前所在的房间（触发战斗）
        3. 如果目标房间有怪兽，Boss替代该怪兽并保存原怪兽信息
        4. Boss离开时，恢复原房间的怪兽（如果有）
        5. 如果移动到玩家房间，返回特殊标记用于触发战斗
        
        Returns:
            dict: {
                'new_room_id': int,  # 新的Boss房间ID
                'is_attacking_player': bool,  # 是否攻击玩家
                'old_room_id': int  # 旧的Boss房间ID
            }
        """
        # ✅ 检查Boss移动是否被暂停
        if self.boss_movement_paused:
            return {
                'new_room_id': self.boss_room_id,
                'is_attacking_player': False,
                'old_room_id': self.boss_room_id
            }
        
        if not self.boss_room_id:
            return {'new_room_id': -1, 'is_attacking_player': False, 'old_room_id': -1}
        
        # 获取Boss当前房间
        current_boss_room = self.graph.get_room(self.boss_room_id)
        if not current_boss_room:
            return {'new_room_id': -1, 'is_attacking_player': False, 'old_room_id': -1}
        
        # 获取相邻房间
        neighbors = self.graph.get_neighbors(self.boss_room_id)
        if not neighbors:
            return {'new_room_id': self.boss_room_id, 'is_attacking_player': False, 'old_room_id': self.boss_room_id}
        
        # 随机选择一个相邻房间（包括玩家房间）
        new_boss_room_id = random.choice(neighbors)
        is_attacking_player = (new_boss_room_id == self.player.current_room)
        new_boss_room = self.graph.get_room(new_boss_room_id)
        
        if not new_boss_room:
            return {
                'new_room_id': self.boss_room_id,
                'is_attacking_player': False,
                'old_room_id': self.boss_room_id
            }
        
        # 获取Boss怪物对象
        boss_monster = current_boss_room.monster
        
        # 恢复旧Boss房间的原怪兽（如果有保存的）
        # ✅ 关键：必须先清除is_boss_room标志，防止显示多个Boss
        current_boss_room.is_boss_room = False
        if self.displaced_monster:
            current_boss_room.monster = self.displaced_monster
            self.displaced_monster = None
        else:
            # 如果没有保存的怪兽，则清空
            current_boss_room.monster = None
        
        # 保存新房间的原怪兽（如果有）
        if new_boss_room.monster:
            self.displaced_monster = new_boss_room.monster
        else:
            self.displaced_monster = None
        
        # Boss移动到新房间
        new_boss_room.monster = boss_monster
        new_boss_room.is_boss_room = True
        
        # 更新Boss房间ID
        old_boss_room_id = self.boss_room_id
        self.boss_room_id = new_boss_room_id
        
        if DEBUG:
            print(f"[Boss移动] 从房间 {old_boss_room_id} → 房间 {new_boss_room_id}")
        if is_attacking_player:
            if DEBUG:
                print(f"  ⚠️  Boss正在接近玩家！")
        if self.displaced_monster:
            if DEBUG:
                print(f"  ├─ 替代了怪兽: {self.displaced_monster.name} (武力: {self.displaced_monster.power})")
        
        return {
            'new_room_id': self.boss_room_id,
            'is_attacking_player': is_attacking_player,
            'old_room_id': old_boss_room_id
        }
    
    # ✅ 新增：Boss移动控制方法
    def pause_boss_movement(self) -> None:
        """暂停Boss移动"""
        self.boss_movement_paused = True
        if DEBUG:
            print("🔒 Boss移动已暂停")
    
    def resume_boss_movement(self) -> None:
        """恢复Boss移动"""
        self.boss_movement_paused = False
        if DEBUG:
            print("🔓 Boss移动已恢复")
    
    def boss_attack_player(self) -> dict:
        """
        Boss攻击玩家（Boss移动到玩家房间后触发）
        
        Returns:
            dict: {
                'success': bool,  # 玩家是否存活
                'combat': dict,  # 战斗详情
                'game_over': bool,  # 游戏是否结束
                'message': str
            }
        """
        # 确认Boss和玩家在同一房间
        if self.boss_room_id != self.player.current_room:
            return {
                'success': True,
                'combat': None,
                'game_over': False,
                'message': 'Boss未在玩家房间'
            }
        
        # 获取Boss房间
        if not self.boss_room_id:
            return {
                'success': True,
                'combat': None,
                'game_over': False,
                'message': 'Boss房间ID无效'
            }
        
        boss_room = self.graph.get_room(self.boss_room_id)
        if not boss_room or not boss_room.monster:
            return {
                'success': True,
                'combat': None,
                'game_over': False,
                'message': 'Boss房间无效'
            }
        
        # 模拟Boss战斗
        combat_result = self._simulate_dice_combat(
            self.player.power,
            boss_room.monster.power,
            is_boss=True
        )
        
        if combat_result["player_wins"]:
            # 玩家获胜 - 游戏胜利！
            power_gain = combat_result["power_gain"]
            self.player.power += power_gain
            boss_room.monster = None
            boss_room.is_boss_room = False
            self.boss_room_id = None
            
            return {
                'success': True,
                'combat': combat_result,
                'game_over': True,
                'game_won': True,
                'message': f'恭喜！您击败了Boss并赢得了游戏！',
                'final_power': self.player.power
            }
        else:
            # 玩家失败 - 游戏结束
            return {
                'success': False,
                'combat': combat_result,
                'game_over': True,
                'game_won': False,
                'message': 'Boss击败了你，游戏结束！',
                'final_power': self.player.power
            }
    
    def _calculate_max_possible_power(self) -> int:
        """计算通过收集所有宝箱可能达到的最大武力值"""
        total_treasure_boost = 0
        for room in self.graph.rooms.values():
            room_treasure = room.treasure
            if room_treasure is not None:
                total_treasure_boost += room_treasure.value
        
        return self.player.power + total_treasure_boost

    def update_layout(self, positions: List[Dict], edges: List[Dict]) -> None:
        """
        更新后端存储的布局（节点位置与边），并同步房间邻居信息到graph。

        positions: list of {id: int, x: float, y: float}
        edges: list of {from: int, to: int}
        """
        # 存储位置到每个Room（如果已存在房间）
        for pos in positions:
            rid = pos.get('id')
            if rid is None:
                continue
            try:
                rid = int(rid)
            except Exception:
                continue
            room = self.graph.get_room(rid)
            if room:
                # 将视觉坐标放在room上，前端可能会需要
                try:
                    setattr(room, 'x', float(pos.get('x', getattr(room, 'x', 0))))
                    setattr(room, 'y', float(pos.get('y', getattr(room, 'y', 0))))
                except Exception:
                    # 忽略解析错误
                    pass

        # 清空并重建邻接关系
        # 首先清除所有现有邻居
        for r in list(self.graph.rooms.values()):
            r.neighbors = []

        # 添加边（无向）- 先去重
        edge_set = set()
        unique_edges = []
        for e in edges:
            fa = e.get('from')
            fb = e.get('to')
            if fa is None or fb is None:
                continue
            try:
                a = int(fa)
                b = int(fb)
            except Exception:
                continue
            
            # 创建标准化的边key（小id-大id）
            edge_key = (min(a, b), max(a, b))
            if edge_key not in edge_set:
                edge_set.add(edge_key)
                unique_edges.append((a, b))
        
        # 使用去重后的边列表
        for a, b in unique_edges:
            ra = self.graph.get_room(a)
            rb = self.graph.get_room(b)
            if ra and rb:
                if b not in ra.neighbors:
                    ra.neighbors.append(b)
                if a not in rb.neighbors:
                    rb.neighbors.append(a)

        # 重新构建 graph adjacency_list for quick lookup
        # 只清除 adjacency_list，保留 room.neighbors
        self.graph.adjacency_list = {}
        for room in list(self.graph.rooms.values()):
            if room.id not in self.graph.adjacency_list:
                self.graph.adjacency_list[room.id] = []
            for nb in room.neighbors:
                if nb not in self.graph.adjacency_list[room.id]:
                    self.graph.adjacency_list[room.id].append(nb)
        
        # 基于前端提交的最终图结构，在后端分配怪物与宝箱并确保可解性
        rooms_list = list(self.graph.rooms.values())
        if len(rooms_list) > 0:
            # 先分配宝箱（路径上随机放置）
            self._assign_treasures(rooms_list)
            # 再根据玩家武力值严格计算并分配怪物
            self._assign_monsters(rooms_list)
            # 最后仅验证路径可行性（不做调整）
            self._ensure_solvability(rooms_list)

            # 更新Boss房间ID并确保玩家在房间0
            self.boss_room_id = self.graph.get_boss_room_id()
            if not self.player:
                self.player = Player()
            self.player.move_to(0)
            
            # ✅ 验证：确保只有一个房间的 is_boss_room 为 True
            boss_rooms = [r for r in rooms_list if r.is_boss_room]
            if len(boss_rooms) != 1:
                if DEBUG:
                    print(f"⚠️  警告：检测到 {len(boss_rooms)} 个Boss房间，正在修复...")
                # 清除所有Boss标志
                for r in rooms_list:
                    r.is_boss_room = False
                # 只在实际Boss房间设置标志
                if self.boss_room_id is not None and self.boss_room_id < len(rooms_list):
                    rooms_list[self.boss_room_id].is_boss_room = True
                    if DEBUG:
                        print(f"✅ 已修正：只有房间 {self.boss_room_id} 是Boss房间")
    
    def simulate_battle(self, player_power: int, monster_power: int) -> bool:
        """
        战斗模拟（可选扩展功能）
        使用随机数比大小
        
        Returns:
            True: 玩家胜利, False: 玩家失败
        """
        player_roll = random.randint(1, 20) + player_power
        monster_roll = random.randint(1, 20) + monster_power
        
        return player_roll > monster_roll
    
    def _is_physically_connected(self, rooms: List[Room], start: int, end: int) -> bool:
        """
        检查两个房间是否物理连通（不考虑怪物阻挡）
        """
        from collections import deque
        
        visited = {start}
        queue = deque([start])
        
        while queue:
            current = queue.popleft()
            if current == end:
                return True
            
            room = rooms[current]
            for neighbor_id in room.neighbors:
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    queue.append(neighbor_id)
        
        return False
    
    # ==================== 游戏状态管理 ====================
    
    def check_game_status(self) -> dict:
        """
        检查游戏状态（是否胜利或失败）
        
        Returns:
            {
                "game_over": bool,
                "status": str,  # playing, victory, defeat
                "message": str
            }
        """
        # 检查是否击败Boss
        if self.boss_room_id is not None:
            boss_room = self.graph.get_room(self.boss_room_id)
            if boss_room and boss_room.monster is None and boss_room.defeated_monster_name:
                self.game_status = "victory"
                self.game_end_time = datetime.now()
                return {
                    "game_over": True,
                    "status": "victory",
                    "message": "Congratulations! You defeated the Boss!"
                }
        
        # 检查玩家是否死亡（武力值降到0或负数）
        if self.player.power <= 0:
            self.game_status = "defeat"
            self.game_end_time = datetime.now()
            return {
                "game_over": True,
                "status": "defeat",
                "message": "Game Over! Your power reached 0."
            }
        
        return {
            "game_over": False,
            "status": "playing",
            "message": "Game in progress"
        }
    
    def get_game_state(self) -> dict:
        """
        获取完整游戏状态（用于保存）
        
        Returns:
            包含所有游戏数据的字典
        """
        return {
            "game_status": self.game_status,
            "game_start_time": self.game_start_time.isoformat() if self.game_start_time else None,
            "game_end_time": self.game_end_time.isoformat() if self.game_end_time else None,
            "player": self.player.to_dict(),
            "boss_room_id": self.boss_room_id,
            "rooms": [room.to_dict() for room in self.graph.rooms.values()],
            "boss_movement_paused": self.boss_movement_paused
        }
    
    def reset_game(self) -> dict:
        """
        重置游戏状态
        
        Returns:
            重置结果
        """
        self.graph = DungeonGraph()
        self.player = Player()
        self.boss_room_id = None
        self.displaced_monster = None
        self.boss_movement_paused = False
        self.game_status = "idle"
        self.game_start_time = None
        self.game_end_time = None
        
        return {
            "success": True,
            "message": "Game reset successfully"
        }
