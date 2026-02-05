# -*- coding: utf-8 -*-
"""建筑系统"""

from config import BUILDINGS, DEMOLISH_REFUND_RATE, INTERCEPTOR_COOLDOWN


class Building:
    """建筑基类"""

    def __init__(self, building_type: str, x: int, y: int, owner_id: int, level: int = 1):
        self.building_type = building_type
        self.x = x
        self.y = y
        self.owner_id = owner_id
        self.level = level
        self.config = BUILDINGS[building_type]
        self.built_this_turn = False  # 是否本回合建造

    @property
    def name(self) -> str:
        return f"{self.config['name']}(Lv.{self.level})"

    @property
    def symbol(self) -> str:
        return self.config['symbol']

    def get_level_config(self) -> dict:
        return self.config['levels'][self.level]

    def can_upgrade(self) -> bool:
        return self.level < max(self.config['levels'].keys())

    def get_upgrade_cost(self) -> int:
        if not self.can_upgrade():
            return 0
        return self.config['levels'][self.level + 1]['cost']

    def upgrade(self):
        if self.can_upgrade():
            self.level += 1

    def get_total_invested(self) -> int:
        """获取该建筑总投入的经济（用于计算拆除返还）"""
        total = 0
        for lv in range(1, self.level + 1):
            total += self.config['levels'][lv]['cost']
        return total

    def get_demolish_refund(self) -> int:
        """获取拆除返还的经济"""
        return int(self.get_total_invested() * DEMOLISH_REFUND_RATE)

    def to_dict(self) -> dict:
        return {
            'type': self.building_type,
            'x': self.x,
            'y': self.y,
            'owner_id': self.owner_id,
            'level': self.level,
            'built_this_turn': self.built_this_turn
        }

    @staticmethod
    def from_dict(data: dict) -> 'Building':
        return Building(
            building_type=data['type'],
            x=data['x'],
            y=data['y'],
            owner_id=data['owner_id'],
            level=data['level']
        )


class Factory(Building):
    """工厂 - 提供经济"""

    def __init__(self, x: int, y: int, owner_id: int, level: int = 1):
        super().__init__('factory', x, y, owner_id, level)

    def get_economy_output(self) -> int:
        return self.get_level_config()['economy']


class City(Building):
    """城市 - 提供人口上限和增长率"""

    def __init__(self, x: int, y: int, owner_id: int, level: int = 1):
        super().__init__('city', x, y, owner_id, level)

    def get_pop_cap_bonus(self) -> int:
        return self.get_level_config()['pop_cap']

    def get_growth_bonus(self) -> float:
        return self.get_level_config()['growth_bonus']


class Barracks(Building):
    """兵营 - 生产步兵和摩托化单位"""

    def __init__(self, x: int, y: int, owner_id: int, level: int = 1):
        super().__init__('barracks', x, y, owner_id, level)

    def can_produce(self, unit_type: str) -> bool:
        """检查是否可以生产指定单位"""
        from config import UNITS, get_production_building
        if unit_type not in UNITS:
            return False
        # 检查是否是兵营能生产的单位
        if get_production_building(unit_type) != 'barracks':
            return False
        # 检查等级要求
        required_level = UNITS[unit_type]['required_level']
        return self.level >= required_level


class ArmsFactory(Building):
    """兵工厂 - 生产炮兵和坦克"""

    def __init__(self, x: int, y: int, owner_id: int, level: int = 1):
        super().__init__('arms_factory', x, y, owner_id, level)

    def can_produce(self, unit_type: str) -> bool:
        """检查是否可以生产指定单位"""
        from config import UNITS, get_production_building
        if unit_type not in UNITS:
            return False
        # 检查是否是兵工厂能生产的单位
        if get_production_building(unit_type) != 'arms_factory':
            return False
        # 检查等级要求
        required_level = UNITS[unit_type]['required_level']
        return self.level >= required_level


class Bridge(Building):
    """桥梁 - 建在河流上，消除过河惩罚"""

    def __init__(self, x: int, y: int, owner_id: int, level: int = 1):
        super().__init__('bridge', x, y, owner_id, level)

    def can_upgrade(self) -> bool:
        return False  # 桥梁不能升级


class Fortification(Building):
    """防线 - 为驻守单位提供防御加成"""

    def __init__(self, x: int, y: int, owner_id: int, level: int = 1):
        super().__init__('fortification', x, y, owner_id, level)

    def get_defense_bonus(self) -> float:
        """获取防御加成倍数"""
        return self.get_level_config()['defense_bonus']


class NuclearSilo(Building):
    """核发射井 - 固定核发射平台"""

    def __init__(self, x: int, y: int, owner_id: int, level: int = 1):
        super().__init__('nuclear_silo', x, y, owner_id, level)
        self.fired_this_turn = False  # 本回合是否已发射
        self.built_this_turn = False  # 是否是本回合建造的

    def can_upgrade(self) -> bool:
        return False  # 核发射井不能升级

    def can_fire(self) -> bool:
        """检查是否可以发射"""
        return not self.fired_this_turn

    def fire(self):
        """发射核弹"""
        self.fired_this_turn = True

    def reset_turn(self):
        """重置回合状态"""
        self.fired_this_turn = False
        self.built_this_turn = False

    def to_dict(self) -> dict:
        data = super().to_dict()
        data['fired_this_turn'] = self.fired_this_turn
        data['built_this_turn'] = self.built_this_turn
        return data


class MobileLauncher(Building):
    """移动发射平台 - 可移动的核发射平台"""

    def __init__(self, x: int, y: int, owner_id: int, level: int = 1):
        super().__init__('mobile_launcher', x, y, owner_id, level)
        self.fired_this_turn = False  # 本回合是否已发射
        self.moved_this_turn = False  # 本回合是否已移动
        self.built_this_turn = False  # 是否是本回合建造的
        self.speed = 2  # 移动速度

    def can_upgrade(self) -> bool:
        return False  # 移动发射平台不能升级

    def can_fire(self) -> bool:
        """检查是否可以发射"""
        return not self.fired_this_turn

    def can_move(self) -> bool:
        """检查是否可以移动"""
        return not self.moved_this_turn and not self.fired_this_turn

    def fire(self):
        """发射核弹"""
        self.fired_this_turn = True

    def move_to(self, new_x: int, new_y: int):
        """移动到新位置"""
        self.x = new_x
        self.y = new_y
        self.moved_this_turn = True

    def reset_turn(self):
        """重置回合状态"""
        self.fired_this_turn = False
        self.moved_this_turn = False
        self.built_this_turn = False

    def to_dict(self) -> dict:
        data = super().to_dict()
        data['fired_this_turn'] = self.fired_this_turn
        data['moved_this_turn'] = self.moved_this_turn
        data['built_this_turn'] = self.built_this_turn
        return data


class NuclearInterceptor(Building):
    """核拦截平台 - 拦截范围内的核弹"""

    def __init__(self, x: int, y: int, owner_id: int, level: int = 1):
        super().__init__('nuclear_interceptor', x, y, owner_id, level)
        self.cooldown = 0  # 剩余冷却回合
        self.built_this_turn = False  # 是否是本回合建造的

    def can_upgrade(self) -> bool:
        return False  # 核拦截平台不能升级

    def can_intercept(self) -> bool:
        """检查是否可以拦截"""
        return self.cooldown == 0

    def intercept(self):
        """执行拦截，进入冷却"""
        self.cooldown = INTERCEPTOR_COOLDOWN

    def advance_cooldown(self):
        """推进冷却"""
        if self.cooldown > 0:
            self.cooldown -= 1

    def reset_turn(self):
        """重置回合状态"""
        self.built_this_turn = False

    def to_dict(self) -> dict:
        data = super().to_dict()
        data['cooldown'] = self.cooldown
        data['built_this_turn'] = self.built_this_turn
        return data


class TrainStation(Building):
    """火车站 - 连接铁路网络，发送火车获取经济"""

    def __init__(self, x: int, y: int, owner_id: int, level: int = 1):
        super().__init__('train_station', x, y, owner_id, level)
        self.train_timer = 0  # 距离下次发车的回合数
        self.connected_buildings = []  # 连接的建筑坐标列表 [(x, y), ...]
        self.railways = []  # 铁路路径 [((x1,y1), (x2,y2)), ...]

    def get_connect_radius(self) -> int:
        """获取铁路连接半径"""
        return self.get_level_config()['connect_radius']

    def get_train_interval(self) -> int:
        """获取发车间隔"""
        return self.get_level_config()['train_interval']

    def get_train_income(self) -> int:
        """获取火车经过建筑时产生的经济"""
        return self.get_level_config()['train_income']

    def should_send_train(self) -> bool:
        """检查是否应该发送火车"""
        return self.train_timer <= 0 and len(self.connected_buildings) > 0

    def send_train(self) -> int:
        """发送火车，返回获得的总经济"""
        if not self.should_send_train():
            return 0
        # 重置计时器
        self.train_timer = self.get_train_interval()
        # 计算经济收益（每个连接的建筑都能获得收益）
        income = len(self.connected_buildings) * self.get_train_income()
        return income

    def advance_timer(self):
        """推进发车计时器"""
        if self.train_timer > 0:
            self.train_timer -= 1

    def reset_turn(self):
        """重置回合状态"""
        self.built_this_turn = False

    def to_dict(self) -> dict:
        data = super().to_dict()
        data['train_timer'] = self.train_timer
        data['connected_buildings'] = self.connected_buildings
        data['railways'] = self.railways
        return data


def create_building(building_type: str, x: int, y: int, owner_id: int, level: int = 1, extra_data: dict = None) -> Building:
    """工厂方法创建建筑"""
    building = None
    if building_type == 'factory':
        building = Factory(x, y, owner_id, level)
    elif building_type == 'city':
        building = City(x, y, owner_id, level)
    elif building_type == 'barracks':
        building = Barracks(x, y, owner_id, level)
    elif building_type == 'arms_factory':
        building = ArmsFactory(x, y, owner_id, level)
    elif building_type == 'bridge':
        building = Bridge(x, y, owner_id, level)
    elif building_type == 'fortification':
        building = Fortification(x, y, owner_id, level)
    elif building_type == 'nuclear_silo':
        building = NuclearSilo(x, y, owner_id, level)
        if extra_data:
            building.fired_this_turn = extra_data.get('fired_this_turn', False)
    elif building_type == 'mobile_launcher':
        building = MobileLauncher(x, y, owner_id, level)
        if extra_data:
            building.fired_this_turn = extra_data.get('fired_this_turn', False)
            building.moved_this_turn = extra_data.get('moved_this_turn', False)
    elif building_type == 'nuclear_interceptor':
        building = NuclearInterceptor(x, y, owner_id, level)
        if extra_data:
            building.cooldown = extra_data.get('cooldown', 0)
    elif building_type == 'train_station':
        building = TrainStation(x, y, owner_id, level)
        if extra_data:
            building.train_timer = extra_data.get('train_timer', 0)
            building.connected_buildings = extra_data.get('connected_buildings', [])
            building.railways = extra_data.get('railways', [])
    else:
        building = Building(building_type, x, y, owner_id, level)

    # 恢复所有建筑的built_this_turn状态
    if extra_data:
        building.built_this_turn = extra_data.get('built_this_turn', False)

    return building


def get_build_cost(building_type: str, level: int = 1) -> int:
    """获取建造费用"""
    return BUILDINGS[building_type]['levels'][level]['cost']
