# -*- coding: utf-8 -*-
"""CMD渲染器"""

import os
from typing import Optional, List
from game_state import GameState, Player
from config import (
    TERRAIN_PLAIN, TERRAIN_RIVER, TERRAIN_BRIDGE, PLAYER_SYMBOLS, PLAYER_COLORS, COLOR_RESET,
    SYMBOL_CAPITAL, SYMBOL_ARMY, SYMBOL_SELECTED, BUILDINGS, UNITS, DEMOLISH_REFUND_RATE,
    UNIT_CATEGORIES, get_production_building, GAME_NAME, FOCUS_CATEGORIES, FOCUS_TREE,
    NUKE_MISSILE_COST, NUKE_RADIUS, INTERCEPTOR_RANGE, INTERCEPTOR_COOLDOWN,
    RAILWAY_SYMBOL_H, RAILWAY_SYMBOL_V, RAILWAY_SYMBOL_CROSS, TRAIN_SYMBOL,
    TERRITORY_POP_GROWTH_BONUS, TERRITORY_POP_CAP_BONUS, TERRITORY_BONUS_THRESHOLD
)


class Renderer:
    """CMD渲染器"""

    def __init__(self, view_width: int = 60, view_height: int = 20):
        self.view_width = view_width
        self.view_height = view_height
        self.camera_x = 0
        self.camera_y = 0
        self.selected_x = 0
        self.selected_y = 0

    def clear_screen(self):
        """清屏"""
        os.system('cls' if os.name == 'nt' else 'clear')

    def move_camera(self, dx: int, dy: int, game_state: GameState):
        """移动摄像机"""
        self.camera_x = max(0, min(self.camera_x + dx,
                                   game_state.game_map.width - self.view_width))
        self.camera_y = max(0, min(self.camera_y + dy,
                                   game_state.game_map.height - self.view_height))

    def center_camera_on(self, x: int, y: int, game_state: GameState):
        """将摄像机中心对准指定位置"""
        self.camera_x = max(0, min(x - self.view_width // 2,
                                   game_state.game_map.width - self.view_width))
        self.camera_y = max(0, min(y - self.view_height // 2,
                                   game_state.game_map.height - self.view_height))

    def move_selection(self, dx: int, dy: int, game_state: GameState):
        """移动选择光标"""
        new_x = max(0, min(self.selected_x + dx, game_state.game_map.width - 1))
        new_y = max(0, min(self.selected_y + dy, game_state.game_map.height - 1))
        self.selected_x = new_x
        self.selected_y = new_y

        # 自动滚动地图以保持光标可见
        if self.selected_x < self.camera_x + 2:
            self.camera_x = max(0, self.selected_x - 2)
        elif self.selected_x >= self.camera_x + self.view_width - 2:
            self.camera_x = min(game_state.game_map.width - self.view_width,
                               self.selected_x - self.view_width + 3)

        if self.selected_y < self.camera_y + 2:
            self.camera_y = max(0, self.selected_y - 2)
        elif self.selected_y >= self.camera_y + self.view_height - 2:
            self.camera_y = min(game_state.game_map.height - self.view_height,
                               self.selected_y - self.view_height + 3)

    def render_game(self, game_state: GameState, current_player_id: int, message: str = ""):
        """渲染游戏画面"""
        self.clear_screen()

        player = game_state.get_player(current_player_id)

        # 计算收入
        from buildings import Factory
        factories = [b for b in game_state.buildings if isinstance(b, Factory)]
        income = player.calculate_income(factories)

        # 顶部状态栏
        print("=" * 80)
        print(f"  回合: {game_state.current_turn}  |  玩家: {player.name} [{PLAYER_SYMBOLS[current_player_id]}]  "
              f"|  人口: {player.population}k/{player.pop_cap}k  |  经济: {player.economy} (+{income}/回合)")

        # 显示选中单位数量
        selected_units = game_state.get_selected_units(current_player_id)
        if selected_units:
            print(f"  [已选中 {len(selected_units)} 个单位]", end="")

        # 显示生产队列
        production_queue = game_state.get_player_production_queue(current_player_id)
        if production_queue:
            queue_info = ", ".join([f"{pq.name}({pq.remaining_turns}回合)" for pq in production_queue[:3]])
            if len(production_queue) > 3:
                queue_info += f" +{len(production_queue)-3}..."
            print(f"  [生产中: {queue_info}]", end="")

        print()
        print("=" * 80)

        # 渲染地图
        self._render_map(game_state, current_player_id)

        print("=" * 80)

        # 显示选中位置信息
        self._render_selection_info(game_state, current_player_id)

        # 操作提示
        print("-" * 80)
        print("  WASD: 移动  L: 选择单位  CTRL+L: 多选  G: 派遣  F: 进攻方向  R: 防守中心")
        print("  B: 建造  U: 升级  X: 拆除  P: 生产  M: 移动  T: 攻击  N: 缩编  ESC: 取消选择")
        print("  J: 国策  K: 核武器  C: 居中首都  E: 结束回合  H: 帮助  Q: 退出")
        print("-" * 80)

        # 显示消息
        if message:
            print(f"  >>> {message}")

    def _render_map(self, game_state: GameState, current_player_id: int):
        """渲染地图区域"""
        game_map = game_state.game_map

        # 构建建筑位置映射
        building_map = {}
        for b in game_state.buildings:
            building_map[(b.x, b.y)] = b

        # 构建单位位置映射
        unit_map = {}
        for u in game_state.units:
            if u.is_alive():
                key = (u.x, u.y)
                if key not in unit_map:
                    unit_map[key] = []
                unit_map[key].append(u)

        # 构建铁路位置映射（当前玩家的铁路）
        railway_cells = game_state.railway_cells.get(current_player_id, set())

        # 构建火车位置映射
        train_map = {}
        for train in game_state.active_trains:
            if train['owner_id'] == current_player_id:
                # 将火车显示在起点和终点之间
                train_map[(train['from'][0], train['from'][1])] = train
                train_map[(train['to'][0], train['to'][1])] = train

        # 逐行渲染
        for vy in range(self.view_height):
            map_y = self.camera_y + vy
            line = "  "

            for vx in range(self.view_width):
                map_x = self.camera_x + vx

                if map_x >= game_map.width or map_y >= game_map.height:
                    line += " "
                    continue

                # 检查是否是选中位置
                is_selected = (map_x == self.selected_x and map_y == self.selected_y)

                # 获取该位置的内容
                char = self._get_cell_display(game_state, map_x, map_y,
                                             building_map, unit_map, current_player_id,
                                             railway_cells, train_map)

                # 选中高亮
                if is_selected:
                    line += f"\033[7m{char}\033[0m"  # 反色显示
                else:
                    line += char

            print(line)

    def _get_cell_display(self, game_state: GameState, x: int, y: int,
                          building_map: dict, unit_map: dict, current_player_id: int,
                          railway_cells: set = None, train_map: dict = None) -> str:
        """获取单元格显示字符"""
        game_map = game_state.game_map
        terrain = game_map.get_terrain(x, y)
        owner = game_map.get_territory_owner(x, y)

        if railway_cells is None:
            railway_cells = set()
        if train_map is None:
            train_map = {}

        # 检查是否是首都
        for player in game_state.players.values():
            if player.capital_x == x and player.capital_y == y:
                color = PLAYER_COLORS[player.id] if owner is not None else ""
                return f"{color}{SYMBOL_CAPITAL}{COLOR_RESET}"

        # 检查单位
        if (x, y) in unit_map:
            units = unit_map[(x, y)]
            unit = units[0]
            color = PLAYER_COLORS[unit.owner_id]
            # 检查是否有选中的单位
            has_selected = any(u.selected for u in units)
            if has_selected:
                # 选中的单位用特殊符号显示
                return f"{color}\033[1m{SYMBOL_SELECTED}{COLOR_RESET}"  # 粗体+特殊符号
            return f"{color}{SYMBOL_ARMY}{COLOR_RESET}"

        # 检查建筑
        if (x, y) in building_map:
            building = building_map[(x, y)]
            color = PLAYER_COLORS[building.owner_id]
            return f"{color}{building.symbol}{COLOR_RESET}"

        # 检查火车
        if (x, y) in train_map:
            color = PLAYER_COLORS[current_player_id]
            return f"{color}{TRAIN_SYMBOL}{COLOR_RESET}"

        # 检查铁路（仅在自己的领土内显示）
        if (x, y) in railway_cells and owner == current_player_id:
            color = PLAYER_COLORS[current_player_id]
            # 判断铁路方向
            has_h = ((x-1, y) in railway_cells or (x+1, y) in railway_cells)
            has_v = ((x, y-1) in railway_cells or (x, y+1) in railway_cells)
            if has_h and has_v:
                return f"{color}{RAILWAY_SYMBOL_CROSS}{COLOR_RESET}"
            elif has_v:
                return f"{color}{RAILWAY_SYMBOL_V}{COLOR_RESET}"
            else:
                return f"{color}{RAILWAY_SYMBOL_H}{COLOR_RESET}"

        # 显示领土或地形
        if owner is not None:
            color = PLAYER_COLORS[owner]
            # 领土内显示玩家符号（小写）
            symbol = PLAYER_SYMBOLS[owner].lower()
            return f"{color}{symbol}{COLOR_RESET}"
        else:
            # 无主之地显示地形
            if terrain == TERRAIN_RIVER:
                return '\033[96m~\033[0m'  # 青色河流
            return terrain

    def _direction_to_name(self, direction: tuple) -> str:
        """将方向元组转换为名称"""
        if direction is None:
            return "无"
        dx, dy = direction
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

    def _render_selection_info(self, game_state: GameState, current_player_id: int):
        """渲染选中位置信息"""
        x, y = self.selected_x, self.selected_y
        terrain = game_state.game_map.get_terrain(x, y)
        owner = game_state.game_map.get_territory_owner(x, y)

        terrain_names = {TERRAIN_PLAIN: "平地", TERRAIN_RIVER: "河流", TERRAIN_BRIDGE: "桥梁"}
        terrain_name = terrain_names.get(terrain, terrain)

        # 如果有桥梁建筑，也显示为桥梁
        if game_state.has_bridge_at(x, y):
            terrain_name = "桥梁"

        # 检查是否是待占领状态
        pending_mark = ""
        if (x, y) in game_state.pending_territory:
            pending_mark = " [下回合占领]"

        owner_name = game_state.players[owner].name if owner is not None else "无主之地"

        info = f"  ({x},{y}) {terrain_name} | {owner_name}{pending_mark}"

        # 显示建筑信息
        building = game_state.get_building_at(x, y)
        if building:
            info += f" | {building.name}"
            if building.owner_id == current_player_id:
                refund = building.get_demolish_refund()
                info += f" [拆除返还{refund}]"
            # 防线显示防御加成
            if building.building_type == 'fortification':
                bonus = int((building.get_level_config()['defense_bonus'] - 1) * 100)
                info += f" [防御+{bonus}%]"
            # 核发射井/移动发射平台显示状态
            if building.building_type in ('nuclear_silo', 'mobile_launcher'):
                if hasattr(building, 'can_fire'):
                    if building.can_fire():
                        info += " [可发射]"
                    else:
                        info += " [已发射]"
                if hasattr(building, 'built_this_turn') and building.built_this_turn:
                    info += " [本回合建造]"
            # 核拦截平台显示冷却
            if building.building_type == 'nuclear_interceptor':
                if hasattr(building, 'cooldown'):
                    if building.cooldown > 0:
                        info += f" [冷却:{building.cooldown}回合]"
                    else:
                        info += " [就绪]"
                if hasattr(building, 'built_this_turn') and building.built_this_turn:
                    info += " [本回合建造]"
            # 火车站显示连接数和发车倒计时
            if building.building_type == 'train_station':
                conn_count = len(building.connected_buildings) if hasattr(building, 'connected_buildings') else 0
                info += f" [连接:{conn_count}建筑]"
                if hasattr(building, 'train_timer'):
                    if building.train_timer > 0:
                        info += f" [发车:{building.train_timer}回合]"
                    else:
                        info += " [即将发车]"
                if hasattr(building, 'built_this_turn') and building.built_this_turn:
                    info += " [本回合建造]"

        print(info)

        # 显示单位信息
        units = game_state.get_units_at(x, y)
        if units:
            for unit in units:
                owner_name = game_state.players[unit.owner_id].name
                selected_mark = "[选中]" if unit.selected else ""

                # 基础信息行
                trait_mark = f"[{unit.trait_name}]" if unit.trait_name else ""
                print(f"  {unit.name} {unit.count}k | {owner_name} | 攻:{unit.attack} 防:{unit.defense} "
                      f"移动:{unit.remaining_moves}/{unit.speed} {trait_mark} {selected_mark}")

                # 额外信息行（如果有的话）
                extra_info = []
                if unit.stealth > 0:
                    extra_info.append(f"隐蔽:{unit.stealth}")
                if unit.detection > 0:
                    extra_info.append(f"侦察:{unit.detection}")
                if unit.target_position:
                    extra_info.append(f"目标:{unit.target_position}")
                if unit.defense_direction:
                    dir_name = self._direction_to_name(unit.defense_direction)
                    extra_info.append(f"防守:{dir_name}")
                if unit.attack_direction:
                    dir_name = self._direction_to_name(unit.attack_direction)
                    extra_info.append(f"进攻:{dir_name}")

                if extra_info:
                    print(f"    {' | '.join(extra_info)}")

    def render_main_menu(self):
        """渲染主菜单"""
        self.clear_screen()
        print("=" * 70)
        print(f"              {GAME_NAME}")
        print("=" * 70)
        print()
        print("  1. 创建房间")
        print("  2. 加入房间")
        print("  3. 单机测试")
        print("  4. 游戏说明")
        print("  5. 退出")
        print()
        print("-" * 70)
        print("  游戏简介:")
        print("  - 回合制策略游戏，建造建筑、发展经济、训练军队、占领领土")
        print("  - 建造桥梁跨越河流，避免渡河攻击惩罚")
        print("  - 占领敌方首都(*)即可消灭敌人，消灭所有敌人获胜")
        print("=" * 70)

    def render_lobby(self, players: list, is_host: bool, room_ip: str = "", map_size_text: str = "",
                      internet_mode: bool = False, internet_ip: str = None):
        """渲染等待房间"""
        self.clear_screen()
        print("=" * 60)
        print("                    等待房间")
        print("=" * 60)
        if room_ip:
            print(f"  局域网IP: {room_ip}")
        if internet_mode and internet_ip:
            print(f"  公网IP:   {internet_ip}  [互联网模式已开启]")
        elif is_host:
            print(f"  互联网:   未开启 (按 I 开启)")
        if map_size_text:
            print(f"  地图大小: {map_size_text}")
        print()
        print("  当前玩家:")
        for i, name in enumerate(players):
            host_mark = " (房主)" if i == 0 else ""
            print(f"    {i + 1}. {name}{host_mark}")
        print()
        if is_host:
            print("  S: 开始游戏  |  Z: 地图设置  |  I: 互联网连接  |  Q: 关闭房间")
        else:
            print("  等待房主开始游戏...  |  Q: 离开房间")
        print("=" * 60)

    def render_build_menu(self, player: Player, game_state: GameState):
        """渲染建造菜单"""
        print("\n" + "=" * 50)
        print("  建造菜单 (当前经济: {})".format(player.economy))
        print("=" * 50)
        idx = 1
        for btype, config in BUILDINGS.items():
            cost = config['levels'][1]['cost']
            affordable = "OK" if player.economy >= cost else "X"
            print(f"  {idx}. {config['name']} ({config['symbol']}) - 费用: {cost} [{affordable}]")
            idx += 1
        print("  0. 取消")
        print("=" * 50)

    def render_produce_menu(self, player: Player, barracks_level: int, arms_factory_level: int):
        """渲染生产菜单"""
        print("\n" + "=" * 70)
        print(f"  生产菜单 (经济: {player.economy}, 人口: {player.population}k)")
        print(f"  兵营等级: {barracks_level}, 兵工厂等级: {arms_factory_level}")
        print("=" * 70)

        idx = 1
        unit_list = []

        # 按类别显示
        for category, category_name in UNIT_CATEGORIES.items():
            print(f"\n  【{category_name}】")
            for unit_type, config in UNITS.items():
                if config['category'] != category:
                    continue

                source = get_production_building(unit_type)
                required_level = config['required_level']

                # 检查是否可用
                if source == 'barracks':
                    available = barracks_level >= required_level
                    req_text = f"兵营Lv{required_level}"
                else:
                    available = arms_factory_level >= required_level
                    req_text = f"兵工厂Lv{required_level}"

                status = "OK" if available else req_text
                time_text = f"({config['production_time']}回合)" if config['production_time'] > 0 else ""

                # 侦察类显示隐蔽和侦察能力
                extra_info = ""
                if config.get('stealth', 0) > 0 or config.get('detection', 0) > 0:
                    extra_info = f"隐:{config.get('stealth', 0)} 侦:{config.get('detection', 0)} "

                # 词条显示
                trait_info = ""
                if config.get('trait_name'):
                    trait_info = f"[{config['trait_name']}]"

                # 分两行显示
                print(f"    {idx}. {config['name']} [{status}]")
                print(f"       费用:{config['cost']} 人口:{config['pop_cost']}k 攻:{config['attack']} "
                      f"防:{config['defense']} 速:{config['speed']} {extra_info}{time_text} {trait_info}")
                unit_list.append(unit_type)
                idx += 1

        print("\n  0. 取消")
        print("=" * 70)
        return unit_list

    def render_unit_select_menu(self, units: list):
        """渲染单位选择菜单"""
        print("\n" + "=" * 40)
        print("  选择单位")
        print("=" * 40)
        for i, unit in enumerate(units, 1):
            selected_mark = " [已选中]" if unit.selected else ""
            print(f"  {i}. {unit.name} (移动力: {unit.remaining_moves}/{unit.speed}){selected_mark}")
        print("  0. 取消")
        print("=" * 40)

    def render_game_over(self, winner: Player):
        """渲染游戏结束画面"""
        self.clear_screen()
        print("=" * 60)
        print("                    游戏结束!")
        print("=" * 60)
        print()
        if winner:
            print(f"              获胜者: {winner.name}")
        else:
            print("              游戏结束")
        print()
        print("=" * 60)
        print("  按任意键返回主菜单...")

    def _wait_key(self, prompt: str = "  -- 按回车继续 --"):
        """等待用户按键"""
        input(prompt)

    def render_help(self):
        """渲染帮助界面（分页显示）"""
        refund_pct = int(DEMOLISH_REFUND_RATE * 100)

        # 第一页：基础系统
        self.clear_screen()
        print("=" * 70)
        print("                       游 戏 说 明 (1/3)")
        print("=" * 70)
        print()
        print("【游戏目标】占领所有敌方首都(*)，消灭所有敌人即可获胜。")
        print()
        print("【资源系统】")
        print("  人口: 用于征兵，每回合自然增长，受城市加成")
        print("  经济: 用于建造和生产，工厂提供每回合收入")
        print()
        print("【建筑系统】(X键拆除返还{}%费用)".format(refund_pct))
        print("  工厂F(3级): 经济收入 Lv1:+10 Lv2:+25 Lv3:+50")
        print("  城市C(3级): 人口上限+增长率")
        print("  兵营B(3级): 生产侦察兵、步兵、摩托化")
        print("  兵工厂W(5级): 生产炮兵和坦克(需时间)")
        print("  防线#(3级): 防御加成 Lv1:+30% Lv2:+50% Lv3:+80%")
        print("  桥梁=(1级): 建在河流上，消除渡河惩罚")
        print("  火车站T(3级): 连接铁路，定时发车获取经济")
        print()
        print("【地形】. 平地  ~ 河流(移动x2,防+50%,渡河攻-50%)  = 桥梁")
        print()
        print("【操作】WASD移动 L选择 G派遣 F进攻方向 R防守方向")
        print("       B建造 U升级 X拆除 P生产 M移动 T攻击 N缩编")
        print("       J国策 K核武器 C居中首都 E结束回合 H帮助 Q退出")
        self._wait_key()

        # 第二页：兵种和词条
        self.clear_screen()
        print("=" * 70)
        print("                       游 戏 说 明 (2/3)")
        print("=" * 70)
        print()
        print("【兵种系统】")
        print("  侦察类(兵营Lv1+): 侦察兵、侦察骑兵、特种侦察")
        print("  步兵类(兵营Lv1+): 基础步兵、精锐步兵、特种兵")
        print("  摩托化(兵营Lv2+): 摩托兵、摩托化步兵、机械化步兵")
        print("  炮兵类(兵工厂Lv2+): 装甲车、自行火炮、火箭炮")
        print("  坦克类(兵工厂Lv2+): 轻型坦克、中型坦克、重型坦克")
        print()
        print("【单位词条】")
        print("  侦察兵:潜行(隐蔽+1)     侦察骑兵:袭扰(战后+1移动)")
        print("  特种侦察:渗透(敌领土隐身)  基础步兵:坚守(未动防+20%)")
        print("  精锐步兵:老练(攻防+10%)   特种兵:伏击大师(突袭+60%)")
        print("  摩托兵:撤退(败50%逃)     摩托化步兵:协同(友军+15%)")
        print("  机械化步兵:装甲防护(炮伤-30%)  装甲车:侦察支援(侦察+2)")
        print("  自行火炮:压制(敌防-20%)   火箭炮:齐射(对>5k+25%)")
        print("  轻坦:突破(无视30%防线)    中坦:全能(地形惩罚减半)")
        print("  重坦:碾压(对步兵+30%)")
        print()
        print("【战斗类型】")
        print("  正常战斗: 双方互相可见")
        print("  遭遇战: 双方都没看见对方，双方攻防-30%")
        print("  突袭: 我方看见敌方但敌方没看见，攻+30%/敌防-30%")
        print("  被伏击: 敌方看见我方但我方没看见，攻-30%/敌防+30%")
        self._wait_key()

        # 第三页：高级系统
        self.clear_screen()
        print("=" * 70)
        print("                       游 戏 说 明 (3/3)")
        print("=" * 70)
        print()
        print("【视野系统】")
        print("  领土内全部可见，单位额外提供4格视野")
        print("  侦察兵视野+3格，侦察能力抵消敌方隐蔽值")
        print()
        print("【领土扩张】派遣士兵经过无主之地，下回合占领")
        print(f"  每占领{TERRITORY_BONUS_THRESHOLD}格以上领土，额外人口增长和上限加成")
        print()
        print("【铁路系统】")
        print("  火车站(T): 自动连接附近的城市/工厂/兵营/兵工厂")
        print("  铁路显示: - 水平 | 垂直 + 交叉")
        print("  快速移动: 步兵/摩托化/炮兵/坦克在铁路上移动消耗降低")
        print("  火车经济: 定时发车，每经过1个连接建筑+经济")
        print()
        print("【国策系统】(J键)")
        print("  经济发展: 提升收入、降低建造成本")
        print("  人口政策: 提升增长率和人口上限")
        print("  军事改革: 提升攻击力和防御力")
        print("  科技研发: 解锁核武器等高级技术")
        print()
        print("【核武器系统】(K键)")
        print("  解锁顺序: 核武器 → 核发射井/核拦截 → 移动发射平台")
        print("  核发射井(S): 2000经济，固定，每回合可发射1次")
        print("  移动发射平台(V): 5000经济，可移动，每回合移动或发射")
        print("  核拦截平台(Y): 3000经济，拦截5x5范围，冷却3回合")
        print(f"  核弹费用: {NUKE_MISSILE_COST}经济/枚，爆炸范围3x3")
        print("  效果: 消灭单位、摧毁建筑、命中首都消灭玩家")
        print()
        print("=" * 70)
        print("  按任意键返回...")

    def render_focus_menu(self, player: Player, focus_tree):
        """渲染国策菜单（紧凑显示）"""
        from focus import get_focus_effect_description

        self.clear_screen()
        print("=" * 70)
        print(f"  国策树 (经济: {player.economy})")

        # 显示当前研究
        if focus_tree.current_focus:
            cf = focus_tree.current_focus
            print(f"  当前研究: {cf.name} (剩余{cf.remaining_turns}回合)")

        # 显示累计效果
        if focus_tree.effects:
            effects_text = get_focus_effect_description(focus_tree.effects)
            print(f"  累计: {effects_text}")
        print("=" * 70)

        idx = 1
        focus_list = []

        # 按类别显示（紧凑格式：一行一个国策）
        for category, category_name in FOCUS_CATEGORIES.items():
            print(f"\n【{category_name}】")
            focuses = focus_tree.get_focuses_by_category(category)

            for focus_id, config, status in focuses:
                status_marks = {
                    'completed': '[OK]',
                    'in_progress': '[..]',
                    'available': '[  ]',
                    'locked': '[X]'
                }
                status_mark = status_marks.get(status, '')

                can_select = status == 'available' and focus_tree.current_focus is None
                select_mark = f"{idx}." if can_select else "  "

                # 紧凑效果描述
                effects = config.get('effects', {})
                effect_text = get_focus_effect_description(effects) if effects else ''
                if len(effect_text) > 25:
                    effect_text = effect_text[:22] + "..."

                print(f"  {select_mark}{config['name']}({config['cost']}/{config['time']}回合) "
                      f"{status_mark} {effect_text}")

                if can_select:
                    focus_list.append(focus_id)
                    idx += 1

        print("\n  0. 取消")
        print("=" * 70)
        return focus_list

    def render_nuke_menu(self, player: Player, has_nuke: bool, launchers: list = None):
        """渲染核武器菜单"""
        self.clear_screen()
        print("=" * 60)
        print("  核武器系统")
        print("=" * 60)

        if not has_nuke:
            print("  尚未研发核武器！")
            print("  需要完成国策: 核武器")
            print("\n  按任意键返回...")
            return False, None

        # 检查发射设施
        if not launchers:
            print("  没有可用的核发射设施！")
            print("  需要建造: 核发射井(S) 或 移动发射平台(V)")
            print("\n  按任意键返回...")
            return False, None

        print(f"  当前经济: {player.economy}")
        print(f"  核弹费用: {NUKE_MISSILE_COST}")

        if player.economy < NUKE_MISSILE_COST:
            print("  [经济不足]")
            print("\n  按任意键返回...")
            return False, None

        print("\n  可用发射设施:")
        for i, launcher in enumerate(launchers, 1):
            launcher_type = "核发射井" if launcher.building_type == 'nuclear_silo' else "移动发射平台"
            print(f"    {i}. {launcher_type} 位置:({launcher.x},{launcher.y})")

        print(f"\n  核弹效果 (爆炸范围: 3x3):")
        print("  - 消灭范围内所有单位")
        print("  - 摧毁范围内建筑")
        print("  - 若命中首都则消灭该玩家")
        print("  - 不能对自己领土使用")
        print("  - 可能被敌方核拦截平台(Y)拦截")
        print("\n  先选择发射设施编号，再输入目标坐标")
        print("  0. 取消")
        print("=" * 60)
        return True, launchers
