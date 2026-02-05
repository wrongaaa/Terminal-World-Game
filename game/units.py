# -*- coding: utf-8 -*-
"""兵种系统"""

from typing import Tuple, List, Optional
from config import UNITS, TERRAIN_RIVER, RIVER_MOVE_COST, UNIT_PRODUCTION_SOURCE, get_production_building


class Unit:
    """军队单位类"""

    _next_id = 1

    def __init__(self, unit_type: str, x: int, y: int, owner_id: int, count: int = 1):
        self.id = Unit._next_id
        Unit._next_id += 1

        self.unit_type = unit_type
        self.x = x
        self.y = y
        self.owner_id = owner_id
        self.count = count  # 以k为单位
        self.remaining_moves = 0  # 本回合剩余移动力
        self.config = UNITS[unit_type]

        # 微操控制状态
        self.selected = False  # 是否被选中
        self.attack_direction: Optional[Tuple[int, int]] = None  # 进攻方向 (dx, dy)
        self.defense_direction: Optional[Tuple[int, int]] = None  # 防守方向 (dx, dy)
        self.target_position: Optional[Tuple[int, int]] = None  # 派遣目标位置

    @property
    def name(self) -> str:
        return f"{self.config['name']} ({self.count}k)"

    @property
    def symbol(self) -> str:
        return self.config['symbol']

    @property
    def category(self) -> str:
        return self.config['category']

    @property
    def attack(self) -> int:
        return self.config['attack'] * self.count

    @property
    def defense(self) -> int:
        return self.config['defense'] * self.count

    @property
    def speed(self) -> int:
        return self.config['speed']

    @property
    def stealth(self) -> int:
        """隐蔽性：越高越难被发现"""
        base = self.config.get('stealth', 0)
        # 潜行词条：隐蔽+1
        if self.trait == 'stealth':
            base += 1
        return base

    @property
    def detection(self) -> int:
        """侦察能力：越高越容易发现隐蔽单位"""
        base = self.config.get('detection', 0)
        # 侦察支援词条：侦察+2
        if self.trait == 'recon_support':
            base += 2
        return base

    @property
    def trait(self) -> str:
        """获取单位词条"""
        return self.config.get('trait', '')

    @property
    def trait_name(self) -> str:
        """获取词条名称"""
        return self.config.get('trait_name', '')

    @property
    def trait_desc(self) -> str:
        """获取词条描述"""
        return self.config.get('trait_desc', '')

    def has_moved_this_turn(self) -> bool:
        """检查本回合是否移动过"""
        return self.remaining_moves < self.speed

    def reset_moves(self):
        """重置移动力（每回合开始时调用）"""
        self.remaining_moves = self.speed

    def can_move_to(self, target_x: int, target_y: int, terrain: str) -> bool:
        """检查是否可以移动到目标位置"""
        distance = abs(target_x - self.x) + abs(target_y - self.y)
        move_cost = distance
        if terrain == TERRAIN_RIVER:
            move_cost *= RIVER_MOVE_COST
        return move_cost <= self.remaining_moves

    def move_to(self, target_x: int, target_y: int, terrain: str) -> bool:
        """移动到目标位置"""
        distance = abs(target_x - self.x) + abs(target_y - self.y)
        move_cost = distance
        if terrain == TERRAIN_RIVER:
            move_cost *= RIVER_MOVE_COST

        if move_cost <= self.remaining_moves:
            self.x = target_x
            self.y = target_y
            self.remaining_moves -= move_cost
            return True
        return False

    def take_damage(self, damage: int):
        """受到伤害，减少单位数量"""
        # 每10点伤害减少1k单位
        units_lost = damage // 10
        self.count = max(0, self.count - units_lost)

    def is_alive(self) -> bool:
        return self.count > 0

    def merge_with(self, other: 'Unit'):
        """合并同类型单位"""
        if self.unit_type == other.unit_type and self.owner_id == other.owner_id:
            self.count += other.count
            other.count = 0

    def split(self, amount: int) -> Optional['Unit']:
        """分割单位（缩编）"""
        if amount >= self.count or amount <= 0:
            return None
        self.count -= amount
        new_unit = Unit(self.unit_type, self.x, self.y, self.owner_id, amount)
        new_unit.remaining_moves = self.remaining_moves
        return new_unit

    def set_attack_direction(self, dx: int, dy: int):
        """设置进攻方向"""
        if dx == 0 and dy == 0:
            self.attack_direction = None
        else:
            # 归一化方向
            length = max(abs(dx), abs(dy))
            self.attack_direction = (dx // length if length > 0 else 0,
                                      dy // length if length > 0 else 0)

    def set_defense_direction(self, dx: int, dy: int):
        """设置防守方向"""
        if dx == 0 and dy == 0:
            self.defense_direction = None
        else:
            # 归一化方向
            length = max(abs(dx), abs(dy))
            self.defense_direction = (dx // length if length > 0 else 0,
                                       dy // length if length > 0 else 0)

    def clear_defense_direction(self):
        """清除防守方向"""
        self.defense_direction = None

    def set_target(self, x: int, y: int):
        """设置派遣目标"""
        self.target_position = (x, y)

    def clear_target(self):
        """清除派遣目标"""
        self.target_position = None

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'type': self.unit_type,
            'x': self.x,
            'y': self.y,
            'owner_id': self.owner_id,
            'count': self.count,
            'remaining_moves': self.remaining_moves,
            'selected': self.selected,
            'attack_direction': self.attack_direction,
            'defense_direction': self.defense_direction,
            'target_position': self.target_position
        }

    @staticmethod
    def from_dict(data: dict) -> 'Unit':
        unit = Unit(
            unit_type=data['type'],
            x=data['x'],
            y=data['y'],
            owner_id=data['owner_id'],
            count=data['count']
        )
        unit.id = data['id']
        unit.remaining_moves = data['remaining_moves']
        unit.selected = data.get('selected', False)
        unit.attack_direction = data.get('attack_direction')
        unit.defense_direction = data.get('defense_direction')
        unit.target_position = data.get('target_position')
        if data['id'] >= Unit._next_id:
            Unit._next_id = data['id'] + 1
        return unit


class ProductionQueue:
    """生产队列项"""

    _next_id = 1

    def __init__(self, unit_type: str, count: int, owner_id: int, x: int, y: int):
        self.id = ProductionQueue._next_id
        ProductionQueue._next_id += 1

        self.unit_type = unit_type
        self.count = count
        self.owner_id = owner_id
        self.x = x  # 生产完成后出现的位置
        self.y = y
        self.config = UNITS[unit_type]
        self.remaining_turns = self.config['production_time']  # 剩余回合数
        self.total_turns = self.config['production_time']

    @property
    def name(self) -> str:
        return f"{self.config['name']} ({self.count}k)"

    @property
    def is_complete(self) -> bool:
        return self.remaining_turns <= 0

    def advance_turn(self) -> bool:
        """推进一回合，返回是否完成"""
        self.remaining_turns -= 1
        return self.is_complete

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'unit_type': self.unit_type,
            'count': self.count,
            'owner_id': self.owner_id,
            'x': self.x,
            'y': self.y,
            'remaining_turns': self.remaining_turns,
            'total_turns': self.total_turns
        }

    @staticmethod
    def from_dict(data: dict) -> 'ProductionQueue':
        pq = ProductionQueue(
            unit_type=data['unit_type'],
            count=data['count'],
            owner_id=data['owner_id'],
            x=data['x'],
            y=data['y']
        )
        pq.id = data['id']
        pq.remaining_turns = data['remaining_turns']
        pq.total_turns = data['total_turns']
        if data['id'] >= ProductionQueue._next_id:
            ProductionQueue._next_id = data['id'] + 1
        return pq


def get_production_cost(unit_type: str, count: int = 1) -> Tuple[int, int]:
    """获取生产费用和人口消耗"""
    config = UNITS[unit_type]
    return config['cost'] * count, config['pop_cost'] * count


def get_production_time(unit_type: str) -> int:
    """获取生产时间（回合数）"""
    return UNITS[unit_type]['production_time']


def get_available_units_for_building(building_type: str, building_level: int) -> List[str]:
    """根据建筑类型和等级获取可生产的兵种"""
    available = []
    for unit_type, config in UNITS.items():
        # 检查生产建筑是否匹配
        source = get_production_building(unit_type)
        if source != building_type:
            continue
        # 检查等级要求
        if config['required_level'] <= building_level:
            available.append(unit_type)
    return available


def get_available_units(barracks_level: int = 0, arms_factory_level: int = 0) -> dict:
    """获取所有可生产的兵种（按类别分组）"""
    available = {
        'barracks': [],      # 兵营可生产
        'arms_factory': []   # 兵工厂可生产
    }

    for unit_type, config in UNITS.items():
        source = get_production_building(unit_type)
        required_level = config['required_level']

        if source == 'barracks' and barracks_level >= required_level:
            available['barracks'].append(unit_type)
        elif source == 'arms_factory' and arms_factory_level >= required_level:
            available['arms_factory'].append(unit_type)

    return available
