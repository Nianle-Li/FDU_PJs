"""
数据模型定义
包含: Room, Monster, Treasure, Player 四个核心类
"""
from dataclasses import dataclass, field
from typing import Optional, List, Set


@dataclass
class Monster:
    """怪物类"""
    name: str
    power: int
    is_boss: bool = False
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "name": self.name,
            "power": self.power,
            "is_boss": self.is_boss
        }


@dataclass
class Treasure:
    """宝箱/道具类"""
    item_type: str  # 头盔/护甲/靴子/兵器/魔法石
    name: str
    value: int  # 宝箱价值 = 武力值增加量
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "item_type": self.item_type,
            "name": self.name,
            "value": self.value
        }


@dataclass
class Room:
    """房间类"""
    id: int
    name: str
    monster: Optional[Monster] = None
    treasure: Optional[Treasure] = None
    neighbors: List[int] = field(default_factory=list)
    is_boss_room: bool = False  # 直接作为字段，可读可写
    defeated_monster_name: Optional[str] = None  # 记录被击败的怪物名称
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "id": self.id,
            "name": self.name,
            "monster": self.monster.to_dict() if self.monster else None,
            "treasure": self.treasure.to_dict() if self.treasure else None,
            "is_boss_room": self.is_boss_room,
            "neighbors": self.neighbors,
            "defeated_monster_name": self.defeated_monster_name
        }


class Player:
    """玩家类"""
    
    def __init__(self):
        self.power: int = 10  # 初始武力值
        self.inventory: List[Treasure] = []
        self.current_room: int = 0
        self.visited_rooms: Set[int] = set()
    
    def add_treasure(self, treasure: Treasure) -> None:
        """添加战利品"""
        self.inventory.append(treasure)
        self.power += treasure.value
    
    def can_fight(self, monster_power: int) -> bool:
        """判断是否可以战斗"""
        return self.power > monster_power
    
    def move_to(self, room_id: int) -> None:
        """移动到新房间"""
        self.current_room = room_id
        self.visited_rooms.add(room_id)
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "power": self.power,
            "current_room": self.current_room,
            "inventory_count": len(self.inventory),
            "visited_count": len(self.visited_rooms),
            "visited_rooms": list(self.visited_rooms),
            "inventory": [t.to_dict() for t in self.inventory]
        }
