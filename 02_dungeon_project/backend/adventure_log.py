"""
探险日志实现 - 会话式记录
每个会话记录包含完整的探索路径和每步详情
"""
from collections import deque
from typing import List, Dict, Optional
from datetime import datetime


class AdventureLog:
    """探险日志管理类 - 会话式记录"""
    
    def __init__(self, max_size: int = 100):
        self.sessions: deque = deque(maxlen=max_size)  # 会话列表
        self.session_counter: int = 0
        self.current_session: Optional[Dict] = None  # 当前活动会话
    
    def start_session(self, start_room: int, initial_power: int) -> None:
        """开始新的探索会话"""
        self.current_session = {
            'id': self.session_counter,
            'start_room': start_room,
            'current_room': start_room,
            'initial_power': initial_power,
            'current_power': initial_power,
            'path': [start_room],  # 完整路径
            'steps': [],  # 详细步骤列表
            'total_treasure_value': 0,
            'total_power_boost': 0,
            'treasures_collected': [],  # 收集的宝箱列表
            'monsters_defeated': [],  # 击败的怪物列表
            'start_time': datetime.now().isoformat(),
            'end_time': None,
            'active': True
        }
        self.session_counter += 1
    
    def add_step(self, step_data: Dict) -> None:
        """
        添加探索步骤
        step_data = {
            'from_room': int,
            'to_room': int,
            'power_before': int,
            'power_after': int,
            'monster': dict or None,
            'treasure': dict or None,
            'combat_result': dict or None
        }
        """
        if not self.current_session or not self.current_session['active']:
            return
        
        # 添加步骤到列表
        step = {
            'step_number': len(self.current_session['steps']) + 1,
            'from_room': step_data.get('from_room'),
            'to_room': step_data.get('to_room'),
            'power_before': step_data.get('power_before'),
            'power_after': step_data.get('power_after'),
            'timestamp': datetime.now().isoformat()
        }
        
        # 怪物信息
        if step_data.get('monster'):
            step['monster'] = step_data['monster']
            self.current_session['monsters_defeated'].append({
                'room': step_data['to_room'],
                'monster': step_data['monster']
            })
        
        # 宝箱信息
        if step_data.get('treasure'):
            step['treasure'] = step_data['treasure']
            treasure_value = step_data['treasure'].get('value', 0)
            self.current_session['total_treasure_value'] += treasure_value
            self.current_session['total_power_boost'] += treasure_value
            self.current_session['treasures_collected'].append({
                'room': step_data['to_room'],
                'treasure': step_data['treasure']
            })
        
        # 战斗详情
        if step_data.get('combat_result'):
            step['combat_result'] = step_data['combat_result']
        
        self.current_session['steps'].append(step)
        
        # 更新路径和当前位置
        if step_data['to_room'] not in self.current_session['path'] or \
           self.current_session['path'][-1] != step_data['to_room']:
            self.current_session['path'].append(step_data['to_room'])
        
        self.current_session['current_room'] = step_data['to_room']
        self.current_session['current_power'] = step_data['power_after']
    
    def end_session(self) -> None:
        """结束当前会话并保存"""
        if self.current_session and self.current_session['active']:
            self.current_session['end_time'] = datetime.now().isoformat()
            self.current_session['active'] = False
            
            # 计算会话统计
            self.current_session['total_steps'] = len(self.current_session['steps'])
            self.current_session['path_length'] = len(self.current_session['path']) - 1
            
            # 保存到历史记录
            self.sessions.append(self.current_session)
            self.current_session = None
    
    def get_current_session(self) -> Optional[Dict]:
        """获取当前活动会话"""
        return self.current_session
    
    def get_recent(self, n: int) -> List[Dict]:
        """获取最近n条会话记录"""
        return list(self.sessions)[-n:]
    
    def get_all(self) -> List[Dict]:
        """获取所有会话记录"""
        return list(self.sessions)
    
    def clear(self) -> None:
        """清空所有记录"""
        self.sessions.clear()
        self.session_counter = 0
        self.current_session = None
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "total_sessions": len(self.sessions),
            "current_session": self.current_session,
            "sessions": list(self.sessions)
        }
