# -*- coding: utf-8 -*-
"""国策系统"""

from typing import Dict, List, Optional, Tuple
from config import FOCUS_TREE, FOCUS_CATEGORIES


class FocusProgress:
    """国策进度"""

    def __init__(self, focus_id: str, owner_id: int):
        self.focus_id = focus_id
        self.owner_id = owner_id
        self.config = FOCUS_TREE[focus_id]
        self.remaining_turns = self.config['time']
        self.completed = False

    @property
    def name(self) -> str:
        return self.config['name']

    @property
    def is_complete(self) -> bool:
        return self.remaining_turns <= 0

    def advance_turn(self) -> bool:
        """推进一回合，返回是否完成"""
        if self.remaining_turns > 0:
            self.remaining_turns -= 1
        if self.remaining_turns <= 0:
            self.completed = True
        return self.completed

    def to_dict(self) -> dict:
        return {
            'focus_id': self.focus_id,
            'owner_id': self.owner_id,
            'remaining_turns': self.remaining_turns,
            'completed': self.completed
        }

    @staticmethod
    def from_dict(data: dict) -> 'FocusProgress':
        fp = FocusProgress(data['focus_id'], data['owner_id'])
        fp.remaining_turns = data['remaining_turns']
        fp.completed = data['completed']
        return fp


class PlayerFocusTree:
    """玩家国策树"""

    def __init__(self, player_id: int):
        self.player_id = player_id
        self.completed_focuses: List[str] = []  # 已完成的国策ID列表
        self.current_focus: Optional[FocusProgress] = None  # 当前正在研究的国策
        self.effects: Dict[str, float] = {}  # 当前生效的效果

    def can_start_focus(self, focus_id: str, player_economy: int) -> Tuple[bool, str]:
        """检查是否可以开始研究某个国策"""
        if focus_id not in FOCUS_TREE:
            return False, "国策不存在"

        if focus_id in self.completed_focuses:
            return False, "该国策已完成"

        if self.current_focus is not None:
            return False, f"正在研究: {self.current_focus.name}"

        config = FOCUS_TREE[focus_id]

        # 检查前置条件
        for prereq in config.get('prerequisites', []):
            if prereq not in self.completed_focuses:
                prereq_name = FOCUS_TREE[prereq]['name']
                return False, f"需要先完成: {prereq_name}"

        # 检查经济
        if player_economy < config['cost']:
            return False, f"经济不足 (需要{config['cost']})"

        return True, "可以研究"

    def start_focus(self, focus_id: str) -> Tuple[bool, str]:
        """开始研究国策（不扣除经济，由外部处理）"""
        self.current_focus = FocusProgress(focus_id, self.player_id)
        return True, f"开始研究: {self.current_focus.name}"

    def advance_turn(self) -> Optional[str]:
        """推进回合，返回完成的国策ID（如果有）"""
        if self.current_focus is None:
            return None

        if self.current_focus.advance_turn():
            completed_id = self.current_focus.focus_id
            self.completed_focuses.append(completed_id)

            # 应用效果
            effects = FOCUS_TREE[completed_id].get('effects', {})
            for effect_key, effect_value in effects.items():
                if effect_key in self.effects:
                    self.effects[effect_key] += effect_value
                else:
                    self.effects[effect_key] = effect_value

            self.current_focus = None
            return completed_id

        return None

    def get_effect(self, effect_key: str, default: float = 0) -> float:
        """获取某个效果的累计值"""
        return self.effects.get(effect_key, default)

    def has_completed(self, focus_id: str) -> bool:
        """检查是否已完成某个国策"""
        return focus_id in self.completed_focuses

    def has_nuclear_capability(self) -> bool:
        """检查是否拥有核武器能力"""
        return 'nuclear_weapons' in self.completed_focuses

    def get_available_focuses(self) -> List[str]:
        """获取当前可研究的国策列表"""
        available = []
        for focus_id, config in FOCUS_TREE.items():
            if focus_id in self.completed_focuses:
                continue
            # 检查前置条件
            prereqs = config.get('prerequisites', [])
            if all(p in self.completed_focuses for p in prereqs):
                available.append(focus_id)
        return available

    def get_focuses_by_category(self, category: str) -> List[Tuple[str, dict, str]]:
        """获取某分类的所有国策及其状态
        返回: [(focus_id, config, status)]
        status: 'completed' | 'in_progress' | 'available' | 'locked'
        """
        result = []
        for focus_id, config in FOCUS_TREE.items():
            if config['category'] != category:
                continue

            if focus_id in self.completed_focuses:
                status = 'completed'
            elif self.current_focus and self.current_focus.focus_id == focus_id:
                status = 'in_progress'
            else:
                prereqs = config.get('prerequisites', [])
                if all(p in self.completed_focuses for p in prereqs):
                    status = 'available'
                else:
                    status = 'locked'

            result.append((focus_id, config, status))

        return result

    def to_dict(self) -> dict:
        return {
            'player_id': self.player_id,
            'completed_focuses': self.completed_focuses,
            'current_focus': self.current_focus.to_dict() if self.current_focus else None,
            'effects': self.effects
        }

    @staticmethod
    def from_dict(data: dict) -> 'PlayerFocusTree':
        tree = PlayerFocusTree(data['player_id'])
        tree.completed_focuses = data['completed_focuses']
        tree.current_focus = FocusProgress.from_dict(data['current_focus']) if data['current_focus'] else None
        tree.effects = data.get('effects', {})
        return tree


def get_focus_effect_description(effects: dict) -> str:
    """获取效果描述文本"""
    descriptions = []
    effect_names = {
        'economy_bonus': '经济收入',
        'pop_growth_bonus': '人口增长',
        'pop_cap_bonus': '人口上限',
        'attack_bonus': '攻击力',
        'defense_bonus': '防御力',
        'production_speed': '生产速度',
        'building_cost_reduction': '建筑费用',
        'unit_cost_reduction': '单位费用',
        'nuclear_capability': '核武器',
        'nuke_damage': '核弹伤害'
    }

    for key, value in effects.items():
        name = effect_names.get(key, key)
        if key == 'nuclear_capability':
            descriptions.append('解锁核武器')
        elif key == 'nuke_damage':
            descriptions.append(f'核弹伤害+{int(value)}')
        elif value > 0:
            if 'bonus' in key or 'reduction' in key:
                descriptions.append(f'{name}+{int(value * 100)}%')
            else:
                descriptions.append(f'{name}+{int(value)}')
        else:
            if 'bonus' in key or 'reduction' in key:
                descriptions.append(f'{name}{int(value * 100)}%')
            else:
                descriptions.append(f'{name}{int(value)}')

    return ', '.join(descriptions) if descriptions else '无'
