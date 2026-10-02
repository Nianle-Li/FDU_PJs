"""
战利品树结构 - 用于分类管理道具
使用多叉树实现
"""
from typing import Optional, List, Dict, Set
from models import Treasure


class TreasureTreeNode:
    """战利品树节点"""
    
    def __init__(self, name: str, treasure: Optional[Treasure] = None):
        self.name = name
        self.treasure = treasure
        self.children: List[TreasureTreeNode] = []
    
    def add_child(self, child: 'TreasureTreeNode') -> None:
        """添加子节点"""
        self.children.append(child)
    
    def to_dict(self) -> dict:
        """递归转换为字典格式"""
        result = {
            "name": self.name,
            "treasure": self.treasure.to_dict() if self.treasure else None,
            "children": [child.to_dict() for child in self.children]
        }
        return result


class TreasureTree:
    """战利品树 - 分类管理系统"""
    
    # Item type constants
    ITEM_TYPES = ["Helmet", "Armor", "Boots", "Weapon", "Stone"]
    
    def __init__(self):
        self.root = TreasureTreeNode("All Treasures")
        self._init_categories()
        self.favorites: Set[str] = set()  # 收藏的战利品名称集合
    
    def _init_categories(self) -> None:
        """初始化5个道具类型节点"""
        for item_type in self.ITEM_TYPES:
            category_node = TreasureTreeNode(item_type)
            self.root.add_child(category_node)
    
    def add_treasure(self, treasure: Treasure) -> None:
        """
        添加战利品到树中
        自动归类到对应类型节点下
        """
        # 找到对应类型的节点
        for category_node in self.root.children:
            if category_node.name == treasure.item_type:
                # 创建具体道具节点
                item_node = TreasureTreeNode(treasure.name, treasure)
                category_node.add_child(item_node)
                break
    
    def get_by_category(self, category: str) -> List[Treasure]:
        """按类别获取战利品"""
        treasures = []
        for category_node in self.root.children:
            if category_node.name == category:
                for item_node in category_node.children:
                    if item_node.treasure:
                        treasures.append(item_node.treasure)
        return treasures
    
    def get_all_treasures(self) -> List[Treasure]:
        """获取所有战利品"""
        treasures = []
        for category_node in self.root.children:
            for item_node in category_node.children:
                if item_node.treasure:
                    treasures.append(item_node.treasure)
        return treasures
    
    def display_tree(self, node: Optional[TreasureTreeNode] = None, level: int = 0) -> str:
        """
        以树形结构展示（命令行版本）
        """
        if node is None:
            node = self.root
        
        result = "  " * level + f"├─ {node.name}"
        if node.treasure:
            result += f" (价值(武力): {node.treasure.value})"
        result += "\n"
        
        for child in node.children:
            result += self.display_tree(child, level + 1)
        
        return result
    
    def to_dict(self) -> dict:
        """转换为JSON格式（用于前端）"""
        return self.root.to_dict()
    
    def get_total_value(self) -> int:
        """计算所有战利品的总价值"""
        total = 0
        for treasure in self.get_all_treasures():
            total += treasure.value
        return total
    
    def get_statistics(self) -> Dict[str, int]:
        """获取各类别道具数量统计"""
        stats = {item_type: 0 for item_type in self.ITEM_TYPES}
        for treasure in self.get_all_treasures():
            stats[treasure.item_type] += 1
        return stats
    
    def add_favorite(self, treasure_name: str) -> bool:
        """
        添加战利品到收藏
        
        Args:
            treasure_name: 战利品名称
            
        Returns:
            是否添加成功
        """
        # 验证该战利品是否存在
        all_treasures = self.get_all_treasures()
        if any(t.name == treasure_name for t in all_treasures):
            self.favorites.add(treasure_name)
            return True
        return False
    
    def remove_favorite(self, treasure_name: str) -> bool:
        """
        从收藏中移除战利品
        
        Args:
            treasure_name: 战利品名称
            
        Returns:
            是否移除成功
        """
        if treasure_name in self.favorites:
            self.favorites.remove(treasure_name)
            return True
        return False
    
    def is_favorite(self, treasure_name: str) -> bool:
        """检查战利品是否被收藏"""
        return treasure_name in self.favorites
    
    def get_favorites(self) -> List[Treasure]:
        """获取所有收藏的战利品"""
        all_treasures = self.get_all_treasures()
        return [t for t in all_treasures if t.name in self.favorites]
    
    def get_favorites_count(self) -> int:
        """获取收藏数量"""
        return len(self.favorites)
