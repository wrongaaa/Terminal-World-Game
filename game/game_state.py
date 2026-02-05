# -*- coding: utf-8 -*-
"""游戏状态管理"""

from typing import Dict, List, Optional, Tuple, Set
from map_generator import GameMap
from buildings import (
    Building, Factory, City, Barracks, ArmsFactory, Bridge, Fortification,
    NuclearSilo, MobileLauncher, NuclearInterceptor, TrainStation,
    create_building, get_build_cost
)
from units import Unit, ProductionQueue, get_production_cost, get_available_units, get_production_time
from combat import resolve_combat, merge_units_at_location
from config import (
    INITIAL_ECONOMY, INITIAL_POPULATION, INITIAL_POP_CAP,
    BASE_POP_GROWTH_RATE, INITIAL_TERRITORY_RADIUS, BUILDINGS, UNITS,
    TERRAIN_RIVER, TERRAIN_BRIDGE, TERRAIN_PLAIN, get_production_building,
    BASE_VISIBILITY_RANGE, UNIT_VISIBILITY_BONUS, SCOUT_VISIBILITY_BONUS,
    NUKE_MISSILE_COST, NUKE_DAMAGE, NUKE_RADIUS, NUKE_BUILDING_DESTROY, NUKE_CAPITAL_DESTROY,
    INTERCEPTOR_RANGE, RAILWAY_CONNECTABLE_BUILDINGS, RAILWAY_SPEED_MULTIPLIER,
    RAILWAY_USABLE_CATEGORIES, TERRITORY_POP_GROWTH_BONUS, TERRITORY_POP_CAP_BONUS,
    TERRITORY_BONUS_THRESHOLD
)
from focus import PlayerFocusTree, get_focus_effect_description


class Player:
    """玩家类"""

    def __init__(self, player_id: int, name: str):
        self.id = player_id
        self.name = name
        self.economy = INITIAL_ECONOMY
        self.population = INITIAL_POPULATION  # k
        self.pop_cap = INITIAL_POP_CAP  # k
        self.capital_x = 0
        self.capital_y = 0
        self.is_alive = True
        self.ready_for_next_turn = False

    def get_growth_rate(self, cities: List[City]) -> float:
        """计算总人口增长率"""
        rate = BASE_POP_GROWTH_RATE
        for city in cities:
            if city.owner_id == self.id:
                rate += city.get_growth_bonus()
        return rate

    def calculate_income(self, factories: List[Factory]) -> int:
        """计算总经济收入"""
        income = 0
        for factory in factories:
            if factory.owner_id == self.id:
                income += factory.get_economy_output()
        return income

    def calculate_pop_cap(self, cities: List[City]) -> int:
        """计算总人口上限"""
        cap = INITIAL_POP_CAP
        for city in cities:
            if city.owner_id == self.id:
                cap += city.get_pop_cap_bonus()
        return cap

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'economy': self.economy,
            'population': self.population,
            'pop_cap': self.pop_cap,
            'capital_x': self.capital_x,
            'capital_y': self.capital_y,
            'is_alive': self.is_alive,
            'ready': self.ready_for_next_turn
        }

    @staticmethod
    def from_dict(data: dict) -> 'Player':
        player = Player(data['id'], data['name'])
        player.economy = data['economy']
        player.population = data['population']
        player.pop_cap = data['pop_cap']
        player.capital_x = data['capital_x']
        player.capital_y = data['capital_y']
        player.is_alive = data['is_alive']
        player.ready_for_next_turn = data['ready']
        return player


class GameState:
    """游戏状态类"""

    def __init__(self):
        self.game_map: Optional[GameMap] = None
        self.players: Dict[int, Player] = {}
        self.buildings: List[Building] = []
        self.units: List[Unit] = []
        self.production_queue: List[ProductionQueue] = []  # 生产队列
        self.pending_territory: Dict[Tuple[int, int], int] = {}  # 待占领领土 {(x,y): player_id}
        self.focus_trees: Dict[int, PlayerFocusTree] = {}  # 玩家国策树
        self.railway_cells: Dict[int, Set[Tuple[int, int]]] = {}  # 玩家铁路格子 {player_id: {(x,y),...}}
        self.active_trains: List[dict] = []  # 活动火车 [{'owner_id','path','pos','timer'}]
        self.current_turn = 1
        self.game_started = False
        self.game_over = False
        self.winner_id = None

    def initialize_game(self, player_names: List[str], map_seed: int = None,
                         map_width: int = None, map_height: int = None):
        """初始化游戏"""
        # 创建地图（使用自定义尺寸或默认值）
        from config import MAP_WIDTH, MAP_HEIGHT, RECOMMENDED_MAP_SIZES
        if map_width is None or map_height is None:
            # 根据玩家数量使用推荐大小
            num_players = len(player_names)
            if num_players in RECOMMENDED_MAP_SIZES:
                map_width, map_height = RECOMMENDED_MAP_SIZES[num_players]
            else:
                map_width = map_width or MAP_WIDTH
                map_height = map_height or MAP_HEIGHT

        self.game_map = GameMap(map_width, map_height)
        # 河流数量根据地图大小动态调整
        river_count = max(2, min(8, (map_width * map_height) // 1000))
        self.game_map.generate(river_count=river_count, seed=map_seed)

        # 获取出生点
        spawn_positions = self.game_map.get_spawn_positions(len(player_names))

        # 创建玩家
        for i, name in enumerate(player_names):
            player = Player(i, name)
            spawn_x, spawn_y = spawn_positions[i]
            player.capital_x = spawn_x
            player.capital_y = spawn_y

            # 设置初始领土
            self.game_map.claim_territory_radius(spawn_x, spawn_y, INITIAL_TERRITORY_RADIUS, i)

            # 创建初始建筑
            self.buildings.append(City(spawn_x, spawn_y, i, level=1))
            self.buildings.append(Barracks(spawn_x + 1, spawn_y, i, level=1))

            # 创建初始军队 - 使用新的单位类型
            self.units.append(Unit('basic_infantry', spawn_x, spawn_y, i, count=5))

            self.players[i] = player

            # 创建国策树
            self.focus_trees[i] = PlayerFocusTree(i)

        self.game_started = True

    def get_player(self, player_id: int) -> Optional[Player]:
        return self.players.get(player_id)

    def get_building_at(self, x: int, y: int) -> Optional[Building]:
        for building in self.buildings:
            if building.x == x and building.y == y:
                return building
        return None

    def get_units_at(self, x: int, y: int) -> List[Unit]:
        return [u for u in self.units if u.x == x and u.y == y and u.is_alive()]

    def get_player_units(self, player_id: int) -> List[Unit]:
        return [u for u in self.units if u.owner_id == player_id and u.is_alive()]

    def get_selected_units(self, player_id: int) -> List[Unit]:
        """获取玩家选中的单位"""
        return [u for u in self.units if u.owner_id == player_id and u.selected and u.is_alive()]

    def get_player_buildings(self, player_id: int) -> List[Building]:
        return [b for b in self.buildings if b.owner_id == player_id]

    def get_player_barracks_level(self, player_id: int) -> int:
        """获取玩家最高兵营等级"""
        max_level = 0
        for b in self.buildings:
            if b.owner_id == player_id and b.building_type == 'barracks':
                max_level = max(max_level, b.level)
        return max_level

    def get_player_arms_factory_level(self, player_id: int) -> int:
        """获取玩家最高兵工厂等级"""
        max_level = 0
        for b in self.buildings:
            if b.owner_id == player_id and b.building_type == 'arms_factory':
                max_level = max(max_level, b.level)
        return max_level

    def get_player_production_queue(self, player_id: int) -> List[ProductionQueue]:
        """获取玩家的生产队列"""
        return [pq for pq in self.production_queue if pq.owner_id == player_id]

    def get_focus_tree(self, player_id: int) -> Optional[PlayerFocusTree]:
        """获取玩家国策树"""
        return self.focus_trees.get(player_id)

    def start_focus(self, player_id: int, focus_id: str) -> Tuple[bool, str]:
        """开始研究国策"""
        player = self.get_player(player_id)
        if not player:
            return False, "玩家不存在"

        tree = self.get_focus_tree(player_id)
        if not tree:
            return False, "国策树不存在"

        can, msg = tree.can_start_focus(focus_id, player.economy)
        if not can:
            return False, msg

        from config import FOCUS_TREE
        cost = FOCUS_TREE[focus_id]['cost']
        player.economy -= cost
        return tree.start_focus(focus_id)

    def get_player_launchers(self, player_id: int) -> List[Building]:
        """获取玩家所有可用的核发射设施"""
        launchers = []
        for b in self.buildings:
            if b.owner_id != player_id:
                continue
            if b.building_type in ('nuclear_silo', 'mobile_launcher'):
                if hasattr(b, 'can_fire') and b.can_fire():
                    launchers.append(b)
        return launchers

    def get_enemy_interceptors(self, player_id: int, target_x: int, target_y: int) -> List[NuclearInterceptor]:
        """获取可以拦截目标位置的敌方拦截器"""
        interceptors = []
        for b in self.buildings:
            if b.owner_id == player_id:
                continue  # 跳过自己的拦截器
            if b.building_type != 'nuclear_interceptor':
                continue
            if not isinstance(b, NuclearInterceptor):
                continue
            if not b.can_intercept():
                continue
            # 检查目标是否在拦截范围内
            dist = max(abs(b.x - target_x), abs(b.y - target_y))
            if dist <= INTERCEPTOR_RANGE:
                interceptors.append(b)
        return interceptors

    def launch_nuke(self, player_id: int, launcher_id: int, target_x: int, target_y: int) -> Tuple[bool, str]:
        """从指定发射器发射核武器"""
        player = self.get_player(player_id)
        if not player:
            return False, "玩家不存在"

        # 查找发射器
        launcher = None
        for b in self.buildings:
            if b.x == launcher_id // 10000 and b.y == launcher_id % 10000 and b.owner_id == player_id:
                if b.building_type in ('nuclear_silo', 'mobile_launcher'):
                    launcher = b
                    break

        if not launcher:
            return False, "发射器不存在"

        if not hasattr(launcher, 'can_fire') or not launcher.can_fire():
            return False, "该发射器本回合已发射"

        # 检查经济（核弹费用）
        if player.economy < NUKE_MISSILE_COST:
            return False, f"经济不足 (需要{NUKE_MISSILE_COST})"

        # 不能核弹自己的领土
        territory_owner = self.game_map.get_territory_owner(target_x, target_y)
        if territory_owner == player_id:
            return False, "不能对自己的领土使用核武器"

        # 扣除经济
        player.economy -= NUKE_MISSILE_COST

        # 标记发射器已使用
        launcher.fire()

        # 检查是否被拦截
        interceptors = self.get_enemy_interceptors(player_id, target_x, target_y)
        if interceptors:
            # 被拦截
            interceptor = interceptors[0]
            interceptor.intercept()
            interceptor_owner = self.players.get(interceptor.owner_id)
            owner_name = interceptor_owner.name if interceptor_owner else "敌方"
            return True, f"核弹被{owner_name}的拦截系统击落！"

        # 执行核爆炸 - 3x3范围
        results = []
        affected_cells = []
        for dy in range(-NUKE_RADIUS, NUKE_RADIUS + 1):
            for dx in range(-NUKE_RADIUS, NUKE_RADIUS + 1):
                affected_cells.append((target_x + dx, target_y + dy))

        total_killed = 0
        buildings_destroyed = []

        for ax, ay in affected_cells:
            # 消灭该格所有单位
            killed_units = [u for u in self.units if u.x == ax and u.y == ay and u.is_alive()]
            for u in killed_units:
                u.take_damage(NUKE_DAMAGE)
            total_killed += len([u for u in killed_units if not u.is_alive()])

            # 摧毁建筑
            if NUKE_BUILDING_DESTROY:
                building = self.get_building_at(ax, ay)
                if building and building.owner_id != player_id:
                    buildings_destroyed.append(building.name)
                    self.buildings = [b for b in self.buildings if not (b.x == ax and b.y == ay)]

            # 检查是否命中首都
            if NUKE_CAPITAL_DESTROY:
                for pid, p in self.players.items():
                    if p.capital_x == ax and p.capital_y == ay and pid != player_id and p.is_alive:
                        self._eliminate_player(pid, player_id)
                        results.append(f"摧毁{p.name}的首都")

            # 占领领土
            current_owner = self.game_map.get_territory_owner(ax, ay)
            if current_owner is not None and current_owner != player_id:
                self.game_map.set_territory(ax, ay, player_id)

        # 清除死亡单位
        self.units = [u for u in self.units if u.is_alive()]

        if total_killed > 0:
            results.append(f"消灭{total_killed}个单位")
        if buildings_destroyed:
            results.append(f"摧毁{len(buildings_destroyed)}座建筑")

        result_text = ', '.join(results) if results else "未造成损害"
        return True, f"核弹命中({target_x},{target_y})! {result_text}"

    def launch_nuke_simple(self, player_id: int, target_x: int, target_y: int) -> Tuple[bool, str]:
        """简化版发射核武器（自动选择可用发射器）"""
        launchers = self.get_player_launchers(player_id)
        if not launchers:
            return False, "没有可用的核发射设施（需要核发射井或移动发射平台）"

        # 使用第一个可用发射器
        launcher = launchers[0]
        launcher_id = launcher.x * 10000 + launcher.y
        return self.launch_nuke(player_id, launcher_id, target_x, target_y)

    def move_mobile_launcher(self, player_id: int, launcher_x: int, launcher_y: int, target_x: int, target_y: int) -> Tuple[bool, str]:
        """移动移动发射平台"""
        # 查找发射器
        launcher = None
        for b in self.buildings:
            if b.x == launcher_x and b.y == launcher_y and b.owner_id == player_id:
                if b.building_type == 'mobile_launcher':
                    launcher = b
                    break

        if not launcher:
            return False, "发射平台不存在"

        if not isinstance(launcher, MobileLauncher):
            return False, "不是移动发射平台"

        if not launcher.can_move():
            return False, "该发射平台本回合无法移动"

        # 检查目标是否在移动范围内
        dist = abs(target_x - launcher_x) + abs(target_y - launcher_y)
        if dist > launcher.speed:
            return False, f"目标太远 (最大移动距离: {launcher.speed})"

        # 检查目标位置
        terrain = self.game_map.get_terrain(target_x, target_y)
        if terrain is None:
            return False, "目标位置超出地图"
        if terrain == TERRAIN_RIVER:
            return False, "不能移动到河流上"
        if self.game_map.get_territory_owner(target_x, target_y) != player_id:
            return False, "只能在自己的领土内移动"
        if self.get_building_at(target_x, target_y):
            return False, "目标位置已有建筑"

        # 移动
        launcher.move_to(target_x, target_y)
        return True, f"移动发射平台到({target_x},{target_y})"

    def has_bridge_at(self, x: int, y: int) -> bool:
        """检查指定位置是否有桥梁"""
        for b in self.buildings:
            if b.x == x and b.y == y and b.building_type == 'bridge':
                return True
        return False

    def get_fortification_at(self, x: int, y: int) -> Optional[Fortification]:
        """获取指定位置的防线"""
        for b in self.buildings:
            if b.x == x and b.y == y and b.building_type == 'fortification':
                return b
        return None

    def get_fortification_defense_bonus(self, x: int, y: int) -> float:
        """获取指定位置的防线防御加成"""
        fort = self.get_fortification_at(x, y)
        if fort:
            return fort.get_defense_bonus()
        return 1.0  # 无加成

    def can_build(self, player_id: int, building_type: str, x: int, y: int) -> Tuple[bool, str]:
        """检查是否可以建造"""
        player = self.get_player(player_id)
        if not player:
            return False, "玩家不存在"

        terrain = self.game_map.get_terrain(x, y)

        # 核设施需要国策解锁
        tree = self.get_focus_tree(player_id)
        if building_type == 'nuclear_silo':
            if not tree or tree.get_effect('can_build_silo', 0) < 1:
                return False, "需要研究国策: 核发射井"
        elif building_type == 'mobile_launcher':
            if not tree or tree.get_effect('can_build_mobile_launcher', 0) < 1:
                return False, "需要研究国策: 移动发射平台"
        elif building_type == 'nuclear_interceptor':
            if not tree or tree.get_effect('can_build_interceptor', 0) < 1:
                return False, "需要研究国策: 核拦截"

        # 桥梁特殊处理：必须建在河流上
        if building_type == 'bridge':
            if terrain != TERRAIN_RIVER:
                return False, "桥梁只能建在河流上"
            if self.get_building_at(x, y):
                return False, "该位置已有建筑"
            # 桥梁不需要在领土内，但需要相邻自己的领土
            adjacent = self.game_map.get_adjacent_cells(x, y)
            has_adjacent_territory = any(
                self.game_map.get_territory_owner(ax, ay) == player_id
                for ax, ay in adjacent
            )
            if not has_adjacent_territory:
                return False, "桥梁必须与你的领土相邻"
        else:
            # 其他建筑检查领土
            if self.game_map.get_territory_owner(x, y) != player_id:
                return False, "不在你的领土内"
            # 不能建在河流上
            if terrain == TERRAIN_RIVER:
                return False, "不能在河流上建造"
            # 检查是否已有建筑
            if self.get_building_at(x, y):
                return False, "该位置已有建筑"

        # 检查费用
        cost = get_build_cost(building_type, 1)
        if player.economy < cost:
            return False, f"经济不足 (需要{cost}，当前{player.economy})"

        return True, "可以建造"

    def build(self, player_id: int, building_type: str, x: int, y: int) -> Tuple[bool, str]:
        """建造建筑"""
        can, msg = self.can_build(player_id, building_type, x, y)
        if not can:
            return False, msg

        player = self.get_player(player_id)
        cost = get_build_cost(building_type, 1)
        player.economy -= cost

        building = create_building(building_type, x, y, player_id, 1)
        # 标记为本回合建造（用于全额返还）
        building.built_this_turn = True
        self.buildings.append(building)

        # 建造火车站或可连接建筑时重建铁路
        if building_type == 'train_station' or building_type in RAILWAY_CONNECTABLE_BUILDINGS:
            self.rebuild_all_railways()

        return True, f"建造了{building.name}"

    def can_upgrade(self, player_id: int, x: int, y: int) -> Tuple[bool, str]:
        """检查是否可以升级建筑"""
        player = self.get_player(player_id)
        building = self.get_building_at(x, y)

        if not building:
            return False, "没有建筑"
        if building.owner_id != player_id:
            return False, "不是你的建筑"
        if not building.can_upgrade():
            return False, "已达最高等级"

        cost = building.get_upgrade_cost()
        if player.economy < cost:
            return False, f"经济不足 (需要{cost})"

        return True, "可以升级"

    def upgrade_building(self, player_id: int, x: int, y: int) -> Tuple[bool, str]:
        """升级建筑"""
        can, msg = self.can_upgrade(player_id, x, y)
        if not can:
            return False, msg

        player = self.get_player(player_id)
        building = self.get_building_at(x, y)
        cost = building.get_upgrade_cost()
        player.economy -= cost
        building.upgrade()

        # 升级火车站时重建铁路（连接半径可能变化）
        if building.building_type == 'train_station':
            self.rebuild_all_railways()

        return True, f"升级到{building.name}"

    def can_demolish(self, player_id: int, x: int, y: int) -> Tuple[bool, str]:
        """检查是否可以拆除建筑"""
        building = self.get_building_at(x, y)

        if not building:
            return False, "没有建筑"
        if building.owner_id != player_id:
            return False, "不是你的建筑"

        # 检查是否是首都所在的城市
        player = self.get_player(player_id)
        if building.building_type == 'city':
            if building.x == player.capital_x and building.y == player.capital_y:
                return False, "不能拆除首都"

        # 本回合建造的建筑全额返还
        if hasattr(building, 'built_this_turn') and building.built_this_turn:
            refund = building.get_total_invested()
            return True, f"可以拆除，全额返还{refund}经济 (本回合建造)"
        else:
            refund = building.get_demolish_refund()
            return True, f"可以拆除，返还{refund}经济"

    def demolish_building(self, player_id: int, x: int, y: int) -> Tuple[bool, str]:
        """拆除建筑"""
        can, msg = self.can_demolish(player_id, x, y)
        if not can:
            return False, msg

        player = self.get_player(player_id)
        building = self.get_building_at(x, y)
        building_name = building.name
        building_type = building.building_type

        # 本回合建造的建筑全额返还
        if hasattr(building, 'built_this_turn') and building.built_this_turn:
            refund = building.get_total_invested()
        else:
            refund = building.get_demolish_refund()

        # 返还经济
        player.economy += refund

        # 移除建筑
        self.buildings = [b for b in self.buildings if not (b.x == x and b.y == y)]

        # 拆除火车站或可连接建筑时重建铁路
        if building_type == 'train_station' or building_type in RAILWAY_CONNECTABLE_BUILDINGS:
            self.rebuild_all_railways()

        return True, f"拆除了{building_name}，返还{refund}经济"

    def can_produce(self, player_id: int, unit_type: str, count: int, x: int, y: int) -> Tuple[bool, str]:
        """检查是否可以生产单位"""
        player = self.get_player(player_id)
        if not player:
            return False, "玩家不存在"

        if unit_type not in UNITS:
            return False, "未知单位类型"

        # 获取生产建筑类型
        production_building = get_production_building(unit_type)
        required_level = UNITS[unit_type]['required_level']

        # 检查是否有对应建筑和等级
        if production_building == 'barracks':
            level = self.get_player_barracks_level(player_id)
            building_name = "兵营"
        else:  # arms_factory
            level = self.get_player_arms_factory_level(player_id)
            building_name = "兵工厂"

        if level < required_level:
            return False, f"需要{required_level}级{building_name}"

        # 检查费用和人口
        cost, pop_cost = get_production_cost(unit_type, count)
        if player.economy < cost:
            return False, f"经济不足 (需要{cost})"
        if player.population < pop_cost:
            return False, f"人口不足 (需要{pop_cost}k)"

        return True, "可以生产"

    def produce_unit(self, player_id: int, unit_type: str, count: int, x: int, y: int) -> Tuple[bool, str]:
        """生产单位"""
        can, msg = self.can_produce(player_id, unit_type, count, x, y)
        if not can:
            return False, msg

        player = self.get_player(player_id)
        cost, pop_cost = get_production_cost(unit_type, count)
        player.economy -= cost
        player.population -= pop_cost

        # 检查是否需要生产时间
        production_time = get_production_time(unit_type)

        if production_time > 0:
            # 加入生产队列
            pq = ProductionQueue(unit_type, count, player_id, x, y)
            self.production_queue.append(pq)
            return True, f"开始生产{UNITS[unit_type]['name']} {count}k (需要{production_time}回合)"
        else:
            # 即时生产
            unit = Unit(unit_type, x, y, player_id, count)
            self.units.append(unit)
            # 合并同位置同类型单位
            self.units = merge_units_at_location(self.units, x, y, player_id)
            return True, f"生产了{UNITS[unit_type]['name']} {count}k"

    def move_unit(self, player_id: int, unit_id: int, target_x: int, target_y: int) -> Tuple[bool, str]:
        """移动单位"""
        unit = None
        for u in self.units:
            if u.id == unit_id and u.owner_id == player_id:
                unit = u
                break

        if not unit:
            return False, "单位不存在"

        terrain = self.game_map.get_terrain(target_x, target_y)
        if terrain is None:
            return False, "目标位置超出地图"

        # 桥梁消除河流移动惩罚
        effective_terrain = terrain
        if terrain == TERRAIN_RIVER and self.has_bridge_at(target_x, target_y):
            effective_terrain = TERRAIN_PLAIN

        # 检查是否可以使用铁路快速移动
        railway_cost = self.get_railway_move_cost(unit, target_x, target_y, effective_terrain)
        if railway_cost is not None:
            # 在铁路上移动，使用铁路移动消耗
            distance = abs(target_x - unit.x) + abs(target_y - unit.y)
            if distance > unit.remaining_moves:
                return False, "移动力不足"
            # 铁路移动消耗固定为1（不受地形影响）
            can_move = True
            move_msg = " [铁路]"
        else:
            # 正常移动
            if not unit.can_move_to(target_x, target_y, effective_terrain):
                return False, "移动力不足"
            can_move = True
            move_msg = ""

        # 检查目标位置是否有敌人
        enemy_units = [u for u in self.get_units_at(target_x, target_y) if u.owner_id != player_id]
        if enemy_units:
            return False, "目标位置有敌军，请使用攻击命令"

        if railway_cost is not None:
            # 铁路移动：每格消耗1移动力
            distance = abs(target_x - unit.x) + abs(target_y - unit.y)
            unit.x = target_x
            unit.y = target_y
            unit.remaining_moves -= distance
        else:
            # 正常移动
            unit.move_to(target_x, target_y, effective_terrain)

        # 领土扩张：无主之地加入待占领列表，下回合生效
        current_owner = self.game_map.get_territory_owner(target_x, target_y)
        if current_owner is None:  # 无主之地
            self.pending_territory[(target_x, target_y)] = player_id

        # 合并单位
        self.units = merge_units_at_location(self.units, target_x, target_y, player_id)

        return True, f"移动到({target_x}, {target_y}){move_msg}"

    def move_selected_units(self, player_id: int, target_x: int, target_y: int) -> Tuple[bool, str]:
        """移动所有选中的单位到目标位置"""
        selected = self.get_selected_units(player_id)
        if not selected:
            return False, "没有选中的单位"

        moved_count = 0
        railway_moves = 0
        for unit in selected:
            terrain = self.game_map.get_terrain(target_x, target_y)
            if terrain is None:
                continue

            effective_terrain = terrain
            if terrain == TERRAIN_RIVER and self.has_bridge_at(target_x, target_y):
                effective_terrain = TERRAIN_PLAIN

            # 检查是否有敌人
            enemy_units = [u for u in self.get_units_at(target_x, target_y) if u.owner_id != player_id]
            if enemy_units:
                continue

            # 检查铁路移动
            railway_cost = self.get_railway_move_cost(unit, target_x, target_y, effective_terrain)
            if railway_cost is not None:
                distance = abs(target_x - unit.x) + abs(target_y - unit.y)
                if distance <= unit.remaining_moves:
                    unit.x = target_x
                    unit.y = target_y
                    unit.remaining_moves -= distance
                    # 领土扩张
                    current_owner = self.game_map.get_territory_owner(target_x, target_y)
                    if current_owner is None:
                        self.pending_territory[(target_x, target_y)] = player_id
                    moved_count += 1
                    railway_moves += 1
            elif unit.can_move_to(target_x, target_y, effective_terrain):
                unit.move_to(target_x, target_y, effective_terrain)
                # 领土扩张
                current_owner = self.game_map.get_territory_owner(target_x, target_y)
                if current_owner is None:
                    self.pending_territory[(target_x, target_y)] = player_id
                moved_count += 1

        # 合并单位
        self.units = merge_units_at_location(self.units, target_x, target_y, player_id)

        if moved_count > 0:
            railway_msg = f" ({railway_moves}个使用铁路)" if railway_moves > 0 else ""
            return True, f"移动了{moved_count}个单位到({target_x}, {target_y}){railway_msg}"
        return False, "没有单位能够移动到目标位置"

    def set_units_target(self, player_id: int, target_x: int, target_y: int) -> Tuple[bool, str]:
        """为选中的单位设置派遣目标"""
        selected = self.get_selected_units(player_id)
        if not selected:
            return False, "没有选中的单位"

        for unit in selected:
            unit.set_target(target_x, target_y)

        return True, f"已设置{len(selected)}个单位的派遣目标为({target_x}, {target_y})"

    def set_units_attack_direction(self, player_id: int, dx: int, dy: int) -> Tuple[bool, str]:
        """为选中的单位设置进攻方向"""
        selected = self.get_selected_units(player_id)
        if not selected:
            return False, "没有选中的单位"

        for unit in selected:
            unit.set_attack_direction(dx, dy)

        direction_name = self._get_direction_name(dx, dy)
        return True, f"已设置{len(selected)}个单位的进攻方向为{direction_name}"

    def set_units_defense_direction(self, player_id: int, dx: int, dy: int) -> Tuple[bool, str]:
        """为选中的单位设置防守方向"""
        selected = self.get_selected_units(player_id)
        if not selected:
            return False, "没有选中的单位"

        for unit in selected:
            unit.set_defense_direction(dx, dy)

        direction_name = self._get_direction_name(dx, dy)
        return True, f"已设置{len(selected)}个单位的防守方向为{direction_name}"

    def split_unit(self, player_id: int, unit_id: int, amount: int) -> Tuple[bool, str]:
        """缩编单位（分割）"""
        unit = None
        for u in self.units:
            if u.id == unit_id and u.owner_id == player_id:
                unit = u
                break

        if not unit:
            return False, "单位不存在"

        new_unit = unit.split(amount)
        if new_unit is None:
            return False, "无法分割（数量无效）"

        self.units.append(new_unit)
        return True, f"分割出{amount}k单位"

    def _get_direction_name(self, dx: int, dy: int) -> str:
        """获取方向名称"""
        if dx == 0 and dy == -1:
            return "北"
        elif dx == 0 and dy == 1:
            return "南"
        elif dx == -1 and dy == 0:
            return "西"
        elif dx == 1 and dy == 0:
            return "东"
        elif dx == 1 and dy == -1:
            return "东北"
        elif dx == 1 and dy == 1:
            return "东南"
        elif dx == -1 and dy == -1:
            return "西北"
        elif dx == -1 and dy == 1:
            return "西南"
        return "无"

    # ==================== 视野系统 ====================

    def get_player_max_detection(self, player_id: int) -> int:
        """获取玩家所有单位中最高的侦察能力"""
        max_detection = 0
        for unit in self.units:
            if unit.owner_id == player_id and unit.is_alive():
                max_detection = max(max_detection, unit.detection)
        return max_detection

    def get_player_visible_cells(self, player_id: int) -> Set[Tuple[int, int]]:
        """获取玩家所有可见格子（不考虑敌方隐蔽性，仅地形视野）"""
        visible = set()

        # 领土内的格子全部可见
        for y in range(self.game_map.height):
            for x in range(self.game_map.width):
                if self.game_map.get_territory_owner(x, y) == player_id:
                    visible.add((x, y))

        # 每个单位提供额外视野（侦察兵有额外视野加成）
        for unit in self.units:
            if unit.owner_id == player_id and unit.is_alive():
                # 侦察类单位有额外视野加成
                if unit.category == 'scout':
                    vis_range = BASE_VISIBILITY_RANGE + SCOUT_VISIBILITY_BONUS
                else:
                    vis_range = BASE_VISIBILITY_RANGE + UNIT_VISIBILITY_BONUS
                for dy in range(-vis_range, vis_range + 1):
                    for dx in range(-vis_range, vis_range + 1):
                        if abs(dx) + abs(dy) <= vis_range:
                            nx, ny = unit.x + dx, unit.y + dy
                            if 0 <= nx < self.game_map.width and 0 <= ny < self.game_map.height:
                                visible.add((nx, ny))

        return visible

    def is_visible_to(self, player_id: int, x: int, y: int) -> bool:
        """检查某个坐标对某玩家是否可见（不考虑单位隐蔽性）"""
        # 领土内可见
        if self.game_map.get_territory_owner(x, y) == player_id:
            return True

        # 检查该玩家的单位视野
        for unit in self.units:
            if unit.owner_id == player_id and unit.is_alive():
                if unit.category == 'scout':
                    vis_range = BASE_VISIBILITY_RANGE + SCOUT_VISIBILITY_BONUS
                else:
                    vis_range = BASE_VISIBILITY_RANGE + UNIT_VISIBILITY_BONUS
                dist = abs(unit.x - x) + abs(unit.y - y)
                if dist <= vis_range:
                    return True
        return False

    def can_see_unit(self, observer_id: int, target_unit: Unit) -> bool:
        """检查一个玩家能否看到某个单位（考虑隐蔽性和侦察能力）"""
        target_x, target_y = target_unit.x, target_unit.y
        target_stealth = target_unit.stealth

        # 领土内始终可见
        if self.game_map.get_territory_owner(target_x, target_y) == observer_id:
            return True

        # 检查观察方的单位视野和侦察能力
        for unit in self.units:
            if unit.owner_id == observer_id and unit.is_alive():
                if unit.category == 'scout':
                    vis_range = BASE_VISIBILITY_RANGE + SCOUT_VISIBILITY_BONUS
                else:
                    vis_range = BASE_VISIBILITY_RANGE + UNIT_VISIBILITY_BONUS

                # 侦察能力抵消隐蔽性
                effective_range = vis_range + unit.detection - target_stealth
                dist = abs(unit.x - target_x) + abs(unit.y - target_y)
                if dist <= effective_range:
                    return True
        return False

    def get_battle_visibility(self, attacker: Unit, defender: Unit) -> str:
        """
        判断战斗视野类型（考虑隐蔽性和侦察能力）:
        - 'normal': 双方互相看见
        - 'ambush_attacker': 攻击方突袭（攻击方看见防守方，防守方看不见攻击方）
        - 'ambush_defender': 防守方看见攻击方但攻击方看不见防守方（不太常见）
        - 'encounter': 遭遇战（双方都没看见对方）
        """
        attacker_sees = self.can_see_unit(attacker.owner_id, defender)
        defender_sees = self.can_see_unit(defender.owner_id, attacker)

        if attacker_sees and defender_sees:
            return 'normal'
        elif attacker_sees and not defender_sees:
            return 'ambush_attacker'
        elif not attacker_sees and defender_sees:
            return 'ambush_defender'
        else:
            return 'encounter'

    def attack(self, player_id: int, unit_id: int, target_x: int, target_y: int) -> Tuple[bool, str]:
        """攻击"""
        attacker = None
        for u in self.units:
            if u.id == unit_id and u.owner_id == player_id:
                attacker = u
                break

        if not attacker:
            return False, "单位不存在"

        # 检查距离（必须相邻）
        distance = abs(target_x - attacker.x) + abs(target_y - attacker.y)
        if distance > 1:
            return False, "目标太远，只能攻击相邻格子"

        # 找到敌方单位
        enemy_units = [u for u in self.get_units_at(target_x, target_y) if u.owner_id != player_id]
        if not enemy_units:
            return False, "目标位置没有敌军"

        # 合并敌方单位进行战斗
        defender = enemy_units[0]
        for other in enemy_units[1:]:
            defender.merge_with(other)

        terrain = self.game_map.get_terrain(target_x, target_y)

        # 判断是否渡河攻击（攻击方所在格或目标格是河流，且没有桥梁）
        attacker_terrain = self.game_map.get_terrain(attacker.x, attacker.y)
        crossing_river = False
        if attacker_terrain == TERRAIN_RIVER and not self.has_bridge_at(attacker.x, attacker.y):
            crossing_river = True
        elif terrain == TERRAIN_RIVER and not self.has_bridge_at(target_x, target_y):
            crossing_river = True

        # 判断战斗视野类型
        battle_type = self.get_battle_visibility(attacker, defender)

        # 获取防线加成
        fortification_bonus = self.get_fortification_defense_bonus(target_x, target_y)

        # 计算同格友军数量（用于协同词条）
        attacker_allies = len([u for u in self.get_units_at(attacker.x, attacker.y)
                               if u.owner_id == player_id and u.id != attacker.id])
        defender_allies = len([u for u in self.get_units_at(target_x, target_y)
                               if u.owner_id == defender.owner_id and u.id != defender.id])

        result = resolve_combat(attacker, defender, terrain, crossing_river, battle_type,
                                fortification_bonus, attacker_allies, defender_allies)

        # 移除死亡单位
        self.units = [u for u in self.units if u.is_alive()]

        # 如果攻击方胜利且存活，移动到目标位置
        if result['attacker_survived'] and not result['defender_survived']:
            attacker.x = target_x
            attacker.y = target_y
            # 占领敌方领土（立即生效）
            self.game_map.set_territory(target_x, target_y, player_id)

            # 检查是否占领首都
            for pid, p in self.players.items():
                if p.capital_x == target_x and p.capital_y == target_y and pid != player_id:
                    self._eliminate_player(pid, player_id)

        cross_msg = " [渡河惩罚]" if crossing_river else ""
        fort_msg = " [防线加成]" if fortification_bonus > 1.0 else ""
        battle_msg = ""
        if battle_type == 'encounter':
            battle_msg = " [遭遇战]"
        elif battle_type == 'ambush_attacker':
            battle_msg = " [突袭成功]"
        elif battle_type == 'ambush_defender':
            battle_msg = " [被伏击]"
        # 词条效果提示
        trait_msg = ""
        if result.get('trait_effects'):
            trait_msg = " [" + ",".join(result['trait_effects']) + "]"
        msg = f"战斗{cross_msg}{fort_msg}{battle_msg}{trait_msg}: 我方损失{result['attacker_losses']}k, 敌方损失{result['defender_losses']}k"
        return True, msg

    def _eliminate_player(self, eliminated_id: int, conqueror_id: int):
        """消灭玩家"""
        eliminated = self.players[eliminated_id]
        eliminated.is_alive = False

        # 转移所有领土
        for y in range(self.game_map.height):
            for x in range(self.game_map.width):
                if self.game_map.territory[y][x] == eliminated_id:
                    self.game_map.territory[y][x] = conqueror_id

        # 转移所有建筑
        for building in self.buildings:
            if building.owner_id == eliminated_id:
                building.owner_id = conqueror_id

        # 检查游戏是否结束
        alive_players = [p for p in self.players.values() if p.is_alive]
        if len(alive_players) == 1:
            self.game_over = True
            self.winner_id = alive_players[0].id

    # ==================== 铁路系统 ====================

    def rebuild_all_railways(self):
        """重建所有玩家的铁路网络"""
        self.railway_cells = {}
        for player_id in self.players:
            self.railway_cells[player_id] = set()
        for b in self.buildings:
            if isinstance(b, TrainStation):
                self._rebuild_station_railways(b)

    def _rebuild_station_railways(self, station: TrainStation):
        """重建单个火车站的铁路连接"""
        station.connected_buildings = []
        station.railways = []
        radius = station.get_connect_radius()

        # 查找范围内可连接的建筑
        for b in self.buildings:
            if b is station:
                continue
            if b.owner_id != station.owner_id:
                continue
            if b.building_type not in RAILWAY_CONNECTABLE_BUILDINGS:
                continue
            dist = abs(b.x - station.x) + abs(b.y - station.y)
            if dist <= radius:
                station.connected_buildings.append([b.x, b.y])
                # 计算铁路路径（直线路径）
                path = self._compute_railway_path(station.x, station.y, b.x, b.y)
                station.railways.append([[station.x, station.y], [b.x, b.y]])
                # 将路径上的格子加入铁路网络
                if station.owner_id not in self.railway_cells:
                    self.railway_cells[station.owner_id] = set()
                for cell in path:
                    self.railway_cells[station.owner_id].add(cell)

    def _compute_railway_path(self, x1: int, y1: int, x2: int, y2: int) -> List[Tuple[int, int]]:
        """计算两点之间的铁路路径（L形路径，先水平后垂直）"""
        path = []
        x, y = x1, y1
        # 先水平移动
        step_x = 1 if x2 > x1 else -1 if x2 < x1 else 0
        while x != x2:
            path.append((x, y))
            x += step_x
        # 再垂直移动
        step_y = 1 if y2 > y1 else -1 if y2 < y1 else 0
        while y != y2:
            path.append((x, y))
            y += step_y
        path.append((x2, y2))
        return path

    def is_on_railway(self, player_id: int, x: int, y: int) -> bool:
        """检查某个格子是否在指定玩家的铁路网络上"""
        if player_id not in self.railway_cells:
            return False
        return (x, y) in self.railway_cells[player_id]

    def can_use_railway(self, unit) -> bool:
        """检查单位是否可以使用铁路快速移动"""
        return unit.category in RAILWAY_USABLE_CATEGORIES

    def get_railway_move_cost(self, unit, target_x: int, target_y: int, terrain: str) -> int:
        """获取铁路上的移动消耗（更低的消耗 = 更快的移动）"""
        # 如果起点和终点都在铁路上，移动消耗降低
        if (self.is_on_railway(unit.owner_id, unit.x, unit.y) and
            self.is_on_railway(unit.owner_id, target_x, target_y) and
            self.can_use_railway(unit)):
            # 铁路移动消耗为1（忽略地形）
            return 1
        return None  # 不在铁路上，使用正常移动消耗

    def _process_train_stations(self):
        """处理火车站：推进计时器、发车、收取经济"""
        for b in self.buildings:
            if not isinstance(b, TrainStation):
                continue
            player = self.get_player(b.owner_id)
            if not player or not player.is_alive:
                continue

            # 推进计时器
            b.advance_timer()

            # 检查是否发车
            if b.should_send_train():
                income = b.send_train()
                if income > 0:
                    player.economy += income
                    # 创建火车动画数据
                    for conn in b.connected_buildings:
                        self.active_trains.append({
                            'owner_id': b.owner_id,
                            'from': [b.x, b.y],
                            'to': conn,
                            'timer': 2  # 火车可见2回合
                        })

    def _process_active_trains(self):
        """处理活动火车（减少可见计时器）"""
        remaining = []
        for train in self.active_trains:
            train['timer'] -= 1
            if train['timer'] > 0:
                remaining.append(train)
        self.active_trains = remaining

    def get_player_train_stations(self, player_id: int) -> List[TrainStation]:
        """获取玩家所有火车站"""
        return [b for b in self.buildings if isinstance(b, TrainStation) and b.owner_id == player_id]

    # ==================== 领土系统 ====================

    def get_player_territory_count(self, player_id: int) -> int:
        """计算玩家的领土格数"""
        count = 0
        for y in range(self.game_map.height):
            for x in range(self.game_map.width):
                if self.game_map.territory[y][x] == player_id:
                    count += 1
        return count

    def get_territory_pop_bonus(self, player_id: int) -> Tuple[float, int]:
        """计算领土带来的人口加成 -> (增长率加成, 人口上限加成)"""
        territory_count = self.get_player_territory_count(player_id)
        effective = max(0, territory_count - TERRITORY_BONUS_THRESHOLD)
        growth_bonus = effective * TERRITORY_POP_GROWTH_BONUS
        cap_bonus = int(effective * TERRITORY_POP_CAP_BONUS)
        return growth_bonus, cap_bonus

    def process_turn(self):
        """处理回合结束"""
        for player in self.players.values():
            if not player.is_alive:
                continue

            # 获取国策效果
            tree = self.get_focus_tree(player.id)
            economy_bonus = tree.get_effect('economy_bonus', 0) if tree else 0
            pop_growth_bonus = tree.get_effect('pop_growth_bonus', 0) if tree else 0
            pop_cap_bonus = tree.get_effect('pop_cap_bonus', 0) if tree else 0

            # 计算收入（含国策加成）
            factories = [b for b in self.buildings if isinstance(b, Factory)]
            income = player.calculate_income(factories)
            income = int(income * (1 + economy_bonus))
            player.economy += income

            # 计算人口增长（含国策加成和领土加成）
            cities = [b for b in self.buildings if isinstance(b, City)]
            territory_growth_bonus, territory_cap_bonus = self.get_territory_pop_bonus(player.id)
            growth_rate = player.get_growth_rate(cities) + pop_growth_bonus + territory_growth_bonus
            player.pop_cap = player.calculate_pop_cap(cities) + int(pop_cap_bonus) + territory_cap_bonus

            growth = int(player.population * growth_rate)
            player.population = min(player.population + growth, player.pop_cap)

            # 重置回合状态
            player.ready_for_next_turn = False

        # 处理国策进度
        self._process_focus_trees()

        # 重建铁路网络
        self.rebuild_all_railways()

        # 处理火车站和火车
        self._process_train_stations()
        self._process_active_trains()

        # 处理生产队列
        self._process_production_queue()

        # 处理待占领领土
        self._process_pending_territory()

        # 重置核设施状态
        self._process_nuclear_facilities()

        # 重置所有建筑的built_this_turn标记
        for b in self.buildings:
            b.built_this_turn = False

        # 重置单位移动力和选中状态
        for unit in self.units:
            unit.reset_moves()
            unit.selected = False

        self.current_turn += 1

    def _process_nuclear_facilities(self):
        """处理核设施回合重置"""
        for b in self.buildings:
            if hasattr(b, 'reset_turn'):
                b.reset_turn()
            # 推进拦截器冷却
            if isinstance(b, NuclearInterceptor):
                b.advance_cooldown()

    def _process_focus_trees(self):
        """处理国策进度"""
        for player_id, tree in self.focus_trees.items():
            player = self.get_player(player_id)
            if not player or not player.is_alive:
                continue
            tree.advance_turn()

    def _process_production_queue(self):
        """处理生产队列"""
        completed = []
        for pq in self.production_queue:
            if pq.advance_turn():
                # 生产完成，创建单位
                unit = Unit(pq.unit_type, pq.x, pq.y, pq.owner_id, pq.count)
                self.units.append(unit)
                # 合并单位
                self.units = merge_units_at_location(self.units, pq.x, pq.y, pq.owner_id)
                completed.append(pq)

        # 移除完成的生产项
        for pq in completed:
            self.production_queue.remove(pq)

    def _process_pending_territory(self):
        """处理待占领领土（下回合生效）"""
        for (x, y), player_id in self.pending_territory.items():
            # 检查该位置是否还有该玩家的单位
            units_at = [u for u in self.get_units_at(x, y) if u.owner_id == player_id]
            if units_at:
                # 确认占领
                current_owner = self.game_map.get_territory_owner(x, y)
                if current_owner is None:  # 仍然是无主之地
                    self.game_map.set_territory(x, y, player_id)

        # 清空待占领列表
        self.pending_territory.clear()

    def select_unit(self, player_id: int, unit_id: int, add_to_selection: bool = False) -> Tuple[bool, str]:
        """选择单位"""
        if not add_to_selection:
            # 清除之前的选择
            for u in self.units:
                if u.owner_id == player_id:
                    u.selected = False

        # 选择新单位
        for u in self.units:
            if u.id == unit_id and u.owner_id == player_id:
                u.selected = True
                return True, f"选中{u.name}"

        return False, "单位不存在"

    def select_units_at(self, player_id: int, x: int, y: int, add_to_selection: bool = False) -> Tuple[bool, str]:
        """选择指定位置的所有单位"""
        if not add_to_selection:
            for u in self.units:
                if u.owner_id == player_id:
                    u.selected = False

        count = 0
        for u in self.units:
            if u.x == x and u.y == y and u.owner_id == player_id and u.is_alive():
                u.selected = True
                count += 1

        if count > 0:
            return True, f"选中了{count}个单位"
        return False, "该位置没有你的单位"

    def deselect_all(self, player_id: int):
        """取消所有选择"""
        for u in self.units:
            if u.owner_id == player_id:
                u.selected = False

    def to_dict(self) -> dict:
        # 将railway_cells转换为可序列化格式
        railway_data = {}
        for pid, cells in self.railway_cells.items():
            railway_data[str(pid)] = [f"{x},{y}" for x, y in cells]

        return {
            'map': self.game_map.to_dict() if self.game_map else None,
            'players': {pid: p.to_dict() for pid, p in self.players.items()},
            'buildings': [b.to_dict() for b in self.buildings],
            'units': [u.to_dict() for u in self.units],
            'production_queue': [pq.to_dict() for pq in self.production_queue],
            'pending_territory': {f"{x},{y}": pid for (x, y), pid in self.pending_territory.items()},
            'focus_trees': {pid: ft.to_dict() for pid, ft in self.focus_trees.items()},
            'railway_cells': railway_data,
            'active_trains': self.active_trains,
            'current_turn': self.current_turn,
            'game_started': self.game_started,
            'game_over': self.game_over,
            'winner_id': self.winner_id
        }

    @staticmethod
    def from_dict(data: dict) -> 'GameState':
        state = GameState()
        state.game_map = GameMap.from_dict(data['map']) if data['map'] else None
        state.players = {int(k): Player.from_dict(v) for k, v in data['players'].items()}
        # 创建建筑，传递额外数据给核设施
        state.buildings = [create_building(b['type'], b['x'], b['y'], b['owner_id'], b['level'], b)
                          for b in data['buildings']]
        state.units = [Unit.from_dict(u) for u in data['units']]
        state.production_queue = [ProductionQueue.from_dict(pq) for pq in data.get('production_queue', [])]
        # 解析 pending_territory
        pending = data.get('pending_territory', {})
        state.pending_territory = {}
        for key, pid in pending.items():
            x, y = map(int, key.split(','))
            state.pending_territory[(x, y)] = pid
        # 解析 focus_trees
        focus_data = data.get('focus_trees', {})
        state.focus_trees = {int(k): PlayerFocusTree.from_dict(v) for k, v in focus_data.items()}
        # 解析 railway_cells
        railway_data = data.get('railway_cells', {})
        state.railway_cells = {}
        for pid_str, cells in railway_data.items():
            pid = int(pid_str)
            state.railway_cells[pid] = set()
            for cell_str in cells:
                x, y = map(int, cell_str.split(','))
                state.railway_cells[pid].add((x, y))
        # 解析 active_trains
        state.active_trains = data.get('active_trains', [])
        state.current_turn = data['current_turn']
        state.game_started = data['game_started']
        state.game_over = data['game_over']
        state.winner_id = data['winner_id']
        return state
