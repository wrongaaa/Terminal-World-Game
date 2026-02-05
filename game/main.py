# -*- coding: utf-8 -*-
"""游戏主入口 - 实时按键版"""

import sys
import os
import time
import random
import threading

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from game_state import GameState
from server import GameServer
from client import GameClient
from renderer import Renderer
from config import BUILDINGS, UNITS, DEFAULT_PORT, RECOMMENDED_MAP_SIZES, MAP_SIZE_PRESETS

# Windows 实时按键
if os.name == 'nt':
    import msvcrt


def get_key():
    """获取按键（非阻塞，Windows）"""
    if os.name == 'nt':
        if msvcrt.kbhit():
            ch = msvcrt.getch()
            # 处理方向键等特殊键
            if ch in (b'\x00', b'\xe0'):
                ch2 = msvcrt.getch()
                # 方向键映射到 WASD
                arrow_map = {b'H': 'W', b'P': 'S', b'K': 'A', b'M': 'D'}
                return arrow_map.get(ch2, '')
            # ESC键
            if ch == b'\x1b':
                return 'ESC'
            return ch.decode('utf-8', errors='ignore').upper()
    return None


def get_key_blocking():
    """获取按键（阻塞，等待用户输入）"""
    if os.name == 'nt':
        ch = msvcrt.getch()
        if ch in (b'\x00', b'\xe0'):
            ch2 = msvcrt.getch()
            arrow_map = {b'H': 'W', b'P': 'S', b'K': 'A', b'M': 'D'}
            return arrow_map.get(ch2, '')
        if ch == b'\x1b':
            return 'ESC'
        return ch.decode('utf-8', errors='ignore').upper()
    return input().strip().upper()


def check_ctrl_pressed():
    """检查CTRL键是否按下（Windows）"""
    if os.name == 'nt':
        import ctypes
        return ctypes.windll.user32.GetKeyState(0x11) & 0x8000 != 0
    return False


class Game:
    """游戏主类"""

    def __init__(self):
        self.renderer = Renderer()
        self.server: GameServer = None
        self.client: GameClient = None
        self.game_state: GameState = None
        self.player_id = 0
        self.is_host = False
        self.running = True
        self.message = ""
        self.need_refresh = True
        self.waiting_for_sync = False
        self.input_mode = False  # 是否在输入模式（需要回车）
        self.ctrl_held = False  # CTRL键状态
        self.map_width = None   # 自定义地图宽度
        self.map_height = None  # 自定义地图高度

    def run(self):
        """运行游戏"""
        while self.running:
            self.renderer.render_main_menu()
            choice = input("请选择: ").strip()

            if choice == '1':
                self.create_room()
            elif choice == '2':
                self.join_room()
            elif choice == '3':
                self.single_player_test()
            elif choice == '4':
                self.show_help()
            elif choice == '5':
                self.running = False
                print("再见!")
            else:
                print("无效选择，请重试")
                time.sleep(1)

    def show_help(self):
        """显示帮助"""
        self.renderer.render_help()
        get_key_blocking()

    def create_room(self):
        """创建房间"""
        self.renderer.clear_screen()
        name = input("请输入你的名字: ").strip() or "房主"

        self.server = GameServer()
        local_ip = self.server.start(name)
        self.is_host = True
        self.player_id = 0

        print(f"\n房间已创建!")
        print(f"  局域网IP: {local_ip}:{DEFAULT_PORT}")
        print("  其他玩家输入此IP即可加入")
        print("等待其他玩家加入...\n")

        self.server.on_player_join = lambda n: print(f"[{n}] 加入了房间")

        self._host_lobby(local_ip)

    def _host_lobby(self, room_ip: str):
        """房主等待大厅"""
        while True:
            num_players = self.server.get_player_count()

            # 计算当前地图大小显示
            if self.map_width and self.map_height:
                map_size_text = f"{self.map_width}x{self.map_height}"
            else:
                rec_w, rec_h = RECOMMENDED_MAP_SIZES.get(num_players, (100, 50))
                map_size_text = f"{rec_w}x{rec_h} (推荐)"

            # 构建连接信息
            internet_info = None
            if self.server.internet_mode and self.server.public_ip:
                internet_info = f"{self.server.public_ip}:{DEFAULT_PORT}"

            self.renderer.render_lobby(
                self.server.get_player_names(),
                is_host=True,
                room_ip=f"{room_ip}:{DEFAULT_PORT}",
                map_size_text=map_size_text,
                internet_mode=self.server.internet_mode,
                internet_ip=internet_info
            )

            cmd = input("输入命令: ").strip().upper()

            if cmd == 'S':
                if num_players >= 1:
                    print("开始游戏...")
                    self.server.start_game(
                        random.randint(1, 99999),
                        self.map_width,
                        self.map_height
                    )
                    self.game_state = self.server.game_state
                    self._game_loop_host()
                    break
                else:
                    print("至少需要1个玩家")
                    time.sleep(1)
            elif cmd == 'Z':
                self._select_map_size()
            elif cmd == 'I':
                self._toggle_internet_mode()
            elif cmd == 'Q':
                self.server.stop()
                break

    def _toggle_internet_mode(self):
        """切换互联网连接模式"""
        if self.server.internet_mode:
            self.server.disable_internet_mode()
            print("  已关闭互联网连接模式")
        else:
            success, result = self.server.enable_internet_mode()
            if success:
                print(f"  互联网连接已开启!")
                print(f"  公网IP: {result}:{DEFAULT_PORT}")
                print(f"  [重要] 请确保路由器已设置端口转发: {DEFAULT_PORT} -> 本机IP")
            else:
                print(f"  开启失败: {result}")
        time.sleep(2)

    def _select_map_size(self):
        """选择地图大小"""
        self.renderer.clear_screen()
        num_players = self.server.get_player_count()
        rec_w, rec_h = RECOMMENDED_MAP_SIZES.get(num_players, (100, 50))

        print("=" * 60)
        print("  地图大小设置")
        print("=" * 60)
        print(f"\n  当前玩家数: {num_players}")
        print(f"  推荐大小: {rec_w}x{rec_h}")
        print()
        print("  预设大小:")
        idx = 1
        preset_keys = list(MAP_SIZE_PRESETS.keys())
        for key in preset_keys:
            w, h, name = MAP_SIZE_PRESETS[key]
            rec_mark = " (推荐)" if (w, h) == (rec_w, rec_h) else ""
            print(f"    {idx}. {name} ({w}x{h}){rec_mark}")
            idx += 1
        print(f"    {idx}. 自定义大小")
        print("    0. 使用推荐大小")
        print()
        print("=" * 60)

        choice = input("选择: ").strip()

        if choice == '0':
            self.map_width = None
            self.map_height = None
            print(f"使用推荐大小: {rec_w}x{rec_h}")
        elif choice.isdigit():
            choice_num = int(choice)
            if 1 <= choice_num <= len(preset_keys):
                key = preset_keys[choice_num - 1]
                self.map_width, self.map_height, name = MAP_SIZE_PRESETS[key]
                print(f"已选择: {name} ({self.map_width}x{self.map_height})")
            elif choice_num == len(preset_keys) + 1:
                # 自定义大小
                custom = input("输入自定义大小 (宽x高, 如 120x60): ").strip()
                try:
                    w, h = map(int, custom.lower().split('x'))
                    if 40 <= w <= 300 and 20 <= h <= 150:
                        self.map_width = w
                        self.map_height = h
                        print(f"已设置自定义大小: {w}x{h}")
                    else:
                        print("大小超出范围 (宽度40-300, 高度20-150)")
                except:
                    print("输入格式错误")
        time.sleep(1)

    def join_room(self):
        """加入房间"""
        self.renderer.clear_screen()
        name = input("请输入你的名字: ").strip() or "玩家"
        host_input = input("请输入房主IP (可包含端口如 192.168.1.1:5555): ").strip() or "127.0.0.1"

        # 解析 IP:端口 格式
        if ':' in host_input:
            parts = host_input.rsplit(':', 1)
            host = parts[0]
            try:
                port = int(parts[1])
            except ValueError:
                print("端口格式错误，使用默认端口")
                port = DEFAULT_PORT
        else:
            host = host_input
            port = DEFAULT_PORT

        print(f"正在连接 {host}:{port}...")
        self.client = GameClient()
        success, msg = self.client.connect(host, name, port)

        if not success:
            print(f"连接失败: {msg}")
            input("按回车返回...")
            return

        print(f"连接成功! 你是玩家 #{self.client.get_player_id() + 1}")
        self.player_id = self.client.get_player_id()
        self.is_host = False

        self.client.on_game_start = self._on_game_start
        self.client.on_state_update = self._on_state_update
        self.client.on_player_list_update = lambda pl: None

        self._client_lobby()

    def _client_lobby(self):
        """客户端等待大厅"""
        while self.client.is_connected():
            self.renderer.render_lobby(
                self.client.get_player_list(),
                is_host=False
            )

            if self.client.game_state:
                self.game_state = self.client.game_state
                self._game_loop_client()
                break

            print("等待房主开始游戏... (Q退出)")

            if os.name == 'nt':
                if msvcrt.kbhit():
                    key = msvcrt.getch().decode('utf-8', errors='ignore').upper()
                    if key == 'Q':
                        self.client.disconnect()
                        break
            time.sleep(0.5)

    def _on_game_start(self, state: GameState):
        """游戏开始回调"""
        self.game_state = state
        self.need_refresh = True

    def _on_state_update(self, state: GameState):
        """状态更新回调"""
        self.game_state = state
        self.need_refresh = True
        self.waiting_for_sync = False

    def single_player_test(self):
        """单机测试模式"""
        self.renderer.clear_screen()
        name = input("请输入你的名字: ").strip() or "测试玩家"

        self.game_state = GameState()
        self.game_state.initialize_game([name, "AI对手"], random.randint(1, 99999))
        self.player_id = 0
        self.is_host = True

        self._game_loop_single()

    def _game_loop_single(self):
        """单机游戏循环 - 实时按键"""
        player = self.game_state.get_player(self.player_id)
        self.renderer.selected_x = player.capital_x
        self.renderer.selected_y = player.capital_y
        self.renderer.center_camera_on(player.capital_x, player.capital_y, self.game_state)

        self.need_refresh = True

        while True:
            if self.game_state.game_over:
                winner = self.game_state.get_player(self.game_state.winner_id)
                self.renderer.render_game_over(winner)
                get_key_blocking()
                break

            if self.need_refresh:
                self.renderer.render_game(self.game_state, self.player_id, self.message)
                self.need_refresh = False

            # 实时按键检测
            key = get_key()
            if key is None:
                time.sleep(0.03)  # 30ms 刷新率
                continue

            self._process_key(key)

    def _game_loop_host(self):
        """房主游戏循环 - 实时按键"""
        self.server.on_action = self._handle_client_action

        player = self.game_state.get_player(self.player_id)
        self.renderer.selected_x = player.capital_x
        self.renderer.selected_y = player.capital_y
        self.renderer.center_camera_on(player.capital_x, player.capital_y, self.game_state)

        self.need_refresh = True

        while True:
            if self.game_state.game_over:
                winner = self.game_state.get_player(self.game_state.winner_id)
                self.renderer.render_game_over(winner)
                get_key_blocking()
                break

            if self.need_refresh:
                self.renderer.render_game(self.game_state, self.player_id, self.message)
                self.need_refresh = False

            key = get_key()
            if key is None:
                time.sleep(0.03)
                continue

            self._process_key_host(key)

    def _game_loop_client(self):
        """客户端游戏循环 - 实时按键"""
        player = self.game_state.get_player(self.player_id)
        self.renderer.selected_x = player.capital_x
        self.renderer.selected_y = player.capital_y
        self.renderer.center_camera_on(player.capital_x, player.capital_y, self.game_state)

        self.need_refresh = True

        while self.client.is_connected():
            if self.game_state.game_over:
                winner = self.game_state.get_player(self.game_state.winner_id)
                self.renderer.render_game_over(winner)
                get_key_blocking()
                break

            if self.need_refresh:
                self.renderer.render_game(self.game_state, self.player_id, self.message)
                self.need_refresh = False

            key = get_key()
            if key is None:
                time.sleep(0.03)
                continue

            self._process_key_client(key)

    def _process_key(self, key: str):
        """处理按键（单机模式）"""
        self.message = ""
        self.need_refresh = True

        if key == 'Q':
            self.game_state.game_over = True
        elif key in ['W', 'A', 'S', 'D']:
            self._handle_movement(key)
        elif key == 'B':
            self._handle_build()
        elif key == 'U':
            self._handle_upgrade()
        elif key == 'X':
            self._handle_demolish()
        elif key == 'P':
            self._handle_produce()
        elif key == 'M':
            self._handle_move()
        elif key == 'T':
            self._handle_attack()
        elif key == 'L':
            self._handle_select_unit(add_to_selection=check_ctrl_pressed())
        elif key == 'G':
            self._handle_dispatch()
        elif key == 'F':
            self._handle_set_attack_direction()
        elif key == 'R':
            self._handle_set_defense_direction()
        elif key == 'N':
            self._handle_split_unit()
        elif key == 'J':
            self._handle_focus()
        elif key == 'K':
            self._handle_nuke()
        elif key == 'ESC':
            self.game_state.deselect_all(self.player_id)
            self.message = "取消所有选择"
        elif key == 'C':
            player = self.game_state.get_player(self.player_id)
            self.renderer.selected_x = player.capital_x
            self.renderer.selected_y = player.capital_y
            self.renderer.center_camera_on(player.capital_x, player.capital_y, self.game_state)
        elif key == 'H':
            self.renderer.render_help()
            get_key_blocking()
        elif key == 'E':
            self._end_turn_single()

    def _process_key_host(self, key: str):
        """处理按键（房主模式）"""
        self.message = ""
        self.need_refresh = True

        if key == 'Q':
            self.server.stop()
            self.game_state.game_over = True
        elif key in ['W', 'A', 'S', 'D']:
            self._handle_movement(key)
        elif key == 'B':
            self._handle_build()
            self.server.sync_game_state()
        elif key == 'U':
            self._handle_upgrade()
            self.server.sync_game_state()
        elif key == 'X':
            self._handle_demolish()
            self.server.sync_game_state()
        elif key == 'P':
            self._handle_produce()
            self.server.sync_game_state()
        elif key == 'M':
            self._handle_move()
            self.server.sync_game_state()
        elif key == 'T':
            self._handle_attack()
            self.server.sync_game_state()
        elif key == 'L':
            self._handle_select_unit(add_to_selection=check_ctrl_pressed())
        elif key == 'G':
            self._handle_dispatch()
            self.server.sync_game_state()
        elif key == 'F':
            self._handle_set_attack_direction()
            self.server.sync_game_state()
        elif key == 'R':
            self._handle_set_defense_direction()
            self.server.sync_game_state()
        elif key == 'N':
            self._handle_split_unit()
            self.server.sync_game_state()
        elif key == 'J':
            self._handle_focus()
            self.server.sync_game_state()
        elif key == 'K':
            self._handle_nuke()
            self.server.sync_game_state()
        elif key == 'ESC':
            self.game_state.deselect_all(self.player_id)
            self.message = "取消所有选择"
        elif key == 'C':
            player = self.game_state.get_player(self.player_id)
            self.renderer.selected_x = player.capital_x
            self.renderer.selected_y = player.capital_y
            self.renderer.center_camera_on(player.capital_x, player.capital_y, self.game_state)
        elif key == 'H':
            self.renderer.render_help()
            get_key_blocking()
        elif key == 'E':
            self._end_turn_host()

    def _process_key_client(self, key: str):
        """处理按键（客户端模式）"""
        self.message = ""
        self.need_refresh = True

        if key == 'Q':
            self.client.disconnect()
        elif key in ['W', 'A', 'S', 'D']:
            self._handle_movement(key)
        elif key == 'B':
            self._handle_build_client()
        elif key == 'U':
            self._handle_upgrade_client()
        elif key == 'X':
            self._handle_demolish_client()
        elif key == 'P':
            self._handle_produce_client()
        elif key == 'M':
            self._handle_move_client()
        elif key == 'T':
            self._handle_attack_client()
        elif key == 'L':
            self._handle_select_unit(add_to_selection=check_ctrl_pressed())
        elif key == 'G':
            self._handle_dispatch_client()
        elif key == 'F':
            self._handle_set_attack_direction_client()
        elif key == 'R':
            self._handle_set_defense_direction_client()
        elif key == 'N':
            self._handle_split_unit_client()
        elif key == 'J':
            self._handle_focus_client()
        elif key == 'K':
            self._handle_nuke_client()
        elif key == 'ESC':
            self.game_state.deselect_all(self.player_id)
            self.message = "取消所有选择"
        elif key == 'C':
            player = self.game_state.get_player(self.player_id)
            self.renderer.selected_x = player.capital_x
            self.renderer.selected_y = player.capital_y
            self.renderer.center_camera_on(player.capital_x, player.capital_y, self.game_state)
        elif key == 'H':
            self.renderer.render_help()
            get_key_blocking()
        elif key == 'E':
            self._end_turn_client()

    def _handle_movement(self, direction: str):
        """处理光标移动"""
        dx, dy = 0, 0
        if direction == 'W':
            dy = -1
        elif direction == 'S':
            dy = 1
        elif direction == 'A':
            dx = -1
        elif direction == 'D':
            dx = 1
        self.renderer.move_selection(dx, dy, self.game_state)

    def _handle_select_unit(self, add_to_selection: bool = False):
        """处理选择单位"""
        x, y = self.renderer.selected_x, self.renderer.selected_y
        success, msg = self.game_state.select_units_at(self.player_id, x, y, add_to_selection)
        self.message = msg

    def _handle_dispatch(self):
        """处理派遣单位"""
        selected = self.game_state.get_selected_units(self.player_id)
        if not selected:
            self.message = "没有选中的单位"
            return

        target = input("派遣目标位置 (x,y): ").strip()
        try:
            tx, ty = map(int, target.split(','))
            success, msg = self.game_state.move_selected_units(self.player_id, tx, ty)
            self.message = msg
            if success:
                self.renderer.selected_x = tx
                self.renderer.selected_y = ty
        except (ValueError, TypeError):
            self.message = "无效输入"

    def _handle_dispatch_client(self):
        """处理派遣单位（客户端）"""
        selected = self.game_state.get_selected_units(self.player_id)
        if not selected:
            self.message = "没有选中的单位"
            return

        target = input("派遣目标位置 (x,y): ").strip()
        try:
            tx, ty = map(int, target.split(','))
            # 客户端需要发送每个选中单位的移动请求
            for unit in selected:
                self.client.send_action({
                    'action': 'move',
                    'unit_id': unit.id,
                    'to_x': tx,
                    'to_y': ty
                })
            self.message = f"已发送{len(selected)}个单位的派遣请求"
        except (ValueError, TypeError):
            self.message = "无效输入"

    def _handle_set_attack_direction(self):
        """处理设置进攻方向"""
        selected = self.game_state.get_selected_units(self.player_id)
        if not selected:
            self.message = "没有选中的单位"
            return

        print("\n选择进攻方向:")
        print("  7(西北) 8(北) 9(东北)")
        print("  4(西)   5(无) 6(东)")
        print("  1(西南) 2(南) 3(东南)")
        print("选择: ", end='', flush=True)
        choice = get_key_blocking()
        print(choice)

        direction_map = {
            '7': (-1, -1), '8': (0, -1), '9': (1, -1),
            '4': (-1, 0), '5': (0, 0), '6': (1, 0),
            '1': (-1, 1), '2': (0, 1), '3': (1, 1)
        }

        if choice in direction_map:
            dx, dy = direction_map[choice]
            success, msg = self.game_state.set_units_attack_direction(self.player_id, dx, dy)
            self.message = msg
        else:
            self.message = "无效选择"

    def _handle_set_attack_direction_client(self):
        """处理设置进攻方向（客户端）"""
        selected = self.game_state.get_selected_units(self.player_id)
        if not selected:
            self.message = "没有选中的单位"
            return

        print("\n选择进攻方向:")
        print("  7(西北) 8(北) 9(东北)")
        print("  4(西)   5(无) 6(东)")
        print("  1(西南) 2(南) 3(东南)")
        print("选择: ", end='', flush=True)
        choice = get_key_blocking()
        print(choice)

        direction_map = {
            '7': (-1, -1), '8': (0, -1), '9': (1, -1),
            '4': (-1, 0), '5': (0, 0), '6': (1, 0),
            '1': (-1, 1), '2': (0, 1), '3': (1, 1)
        }

        if choice in direction_map:
            dx, dy = direction_map[choice]
            self.client.send_action({
                'action': 'set_attack_direction',
                'unit_ids': [u.id for u in selected],
                'dx': dx,
                'dy': dy
            })
            self.message = "已发送设置进攻方向请求"
        else:
            self.message = "无效选择"

    def _handle_set_defense_direction(self):
        """处理设置防守方向"""
        selected = self.game_state.get_selected_units(self.player_id)
        if not selected:
            self.message = "没有选中的单位"
            return

        print("\n选择防守方向:")
        print("  7(西北) 8(北) 9(东北)")
        print("  4(西)   5(无) 6(东)")
        print("  1(西南) 2(南) 3(东南)")
        print("选择: ", end='', flush=True)
        choice = get_key_blocking()
        print(choice)

        direction_map = {
            '7': (-1, -1), '8': (0, -1), '9': (1, -1),
            '4': (-1, 0), '5': (0, 0), '6': (1, 0),
            '1': (-1, 1), '2': (0, 1), '3': (1, 1)
        }

        if choice in direction_map:
            dx, dy = direction_map[choice]
            success, msg = self.game_state.set_units_defense_direction(self.player_id, dx, dy)
            self.message = msg
        else:
            self.message = "无效选择"

    def _handle_set_defense_direction_client(self):
        """处理设置防守方向（客户端）"""
        selected = self.game_state.get_selected_units(self.player_id)
        if not selected:
            self.message = "没有选中的单位"
            return

        print("\n选择防守方向:")
        print("  7(西北) 8(北) 9(东北)")
        print("  4(西)   5(无) 6(东)")
        print("  1(西南) 2(南) 3(东南)")
        print("选择: ", end='', flush=True)
        choice = get_key_blocking()
        print(choice)

        direction_map = {
            '7': (-1, -1), '8': (0, -1), '9': (1, -1),
            '4': (-1, 0), '5': (0, 0), '6': (1, 0),
            '1': (-1, 1), '2': (0, 1), '3': (1, 1)
        }

        if choice in direction_map:
            dx, dy = direction_map[choice]
            self.client.send_action({
                'action': 'set_defense_direction',
                'unit_ids': [u.id for u in selected],
                'dx': dx,
                'dy': dy
            })
            self.message = "已发送设置防守方向请求"
        else:
            self.message = "无效选择"

    def _handle_split_unit(self):
        """处理缩编单位"""
        x, y = self.renderer.selected_x, self.renderer.selected_y
        units = [u for u in self.game_state.get_units_at(x, y) if u.owner_id == self.player_id]

        if not units:
            self.message = "该位置没有你的单位"
            return

        if len(units) == 1:
            unit = units[0]
        else:
            self.renderer.render_unit_select_menu(units)
            print("选择单位: ", end='', flush=True)
            choice = get_key_blocking()
            print(choice)

            if choice == '0':
                return
            try:
                idx = int(choice) - 1
                if not (0 <= idx < len(units)):
                    self.message = "无效选择"
                    return
                unit = units[idx]
            except (ValueError, TypeError):
                self.message = "无效输入"
                return

        amount_str = input(f"分割数量 (当前{unit.count}k): ").strip()
        try:
            amount = int(amount_str)
            success, msg = self.game_state.split_unit(self.player_id, unit.id, amount)
            self.message = msg
        except (ValueError, TypeError):
            self.message = "无效输入"

    def _handle_split_unit_client(self):
        """处理缩编单位（客户端）"""
        x, y = self.renderer.selected_x, self.renderer.selected_y
        units = [u for u in self.game_state.get_units_at(x, y) if u.owner_id == self.player_id]

        if not units:
            self.message = "该位置没有你的单位"
            return

        if len(units) == 1:
            unit = units[0]
        else:
            self.renderer.render_unit_select_menu(units)
            print("选择单位: ", end='', flush=True)
            choice = get_key_blocking()
            print(choice)

            if choice == '0':
                return
            try:
                idx = int(choice) - 1
                if not (0 <= idx < len(units)):
                    self.message = "无效选择"
                    return
                unit = units[idx]
            except (ValueError, TypeError):
                self.message = "无效输入"
                return

        amount_str = input(f"分割数量 (当前{unit.count}k): ").strip()
        try:
            amount = int(amount_str)
            self.client.send_action({
                'action': 'split',
                'unit_id': unit.id,
                'amount': amount
            })
            self.message = "已发送缩编请求"
        except (ValueError, TypeError):
            self.message = "无效输入"

    def _handle_build(self):
        """处理建造（单机）"""
        player = self.game_state.get_player(self.player_id)
        self.renderer.render_build_menu(player, self.game_state)

        print("选择建筑 (输入编号, 0取消): ", end='', flush=True)
        choice = get_key_blocking()
        print(choice)

        if choice == '0':
            return

        building_types = list(BUILDINGS.keys())
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(building_types):
                building_type = building_types[idx]
                success, msg = self.game_state.build(
                    self.player_id,
                    building_type,
                    self.renderer.selected_x,
                    self.renderer.selected_y
                )
                self.message = msg
        except (ValueError, TypeError):
            self.message = "无效输入"

    def _handle_build_client(self):
        """处理建造（客户端）"""
        player = self.game_state.get_player(self.player_id)
        self.renderer.render_build_menu(player, self.game_state)

        print("选择建筑 (输入编号, 0取消): ", end='', flush=True)
        choice = get_key_blocking()
        print(choice)

        if choice == '0':
            return

        building_types = list(BUILDINGS.keys())
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(building_types):
                building_type = building_types[idx]
                self.client.send_action({
                    'action': 'build',
                    'building': building_type,
                    'x': self.renderer.selected_x,
                    'y': self.renderer.selected_y
                })
                self.message = "已发送建造请求"
        except (ValueError, TypeError):
            self.message = "无效输入"

    def _handle_upgrade(self):
        """处理升级（单机）"""
        x, y = self.renderer.selected_x, self.renderer.selected_y
        success, msg = self.game_state.upgrade_building(self.player_id, x, y)
        self.message = msg

    def _handle_upgrade_client(self):
        """处理升级（客户端）"""
        self.client.send_action({
            'action': 'upgrade',
            'x': self.renderer.selected_x,
            'y': self.renderer.selected_y
        })
        self.message = "已发送升级请求"

    def _handle_demolish(self):
        """处理拆除（单机）"""
        x, y = self.renderer.selected_x, self.renderer.selected_y
        building = self.game_state.get_building_at(x, y)
        if building and building.owner_id == self.player_id:
            # 检查是否是本回合建造的建筑（全额返还）
            if hasattr(building, 'built_this_turn') and building.built_this_turn:
                refund = building.get_total_invested()
                refund_msg = f"全额返还{refund}经济 (本回合建造)"
            else:
                refund = building.get_demolish_refund()
                refund_msg = f"返还{refund}经济"
            print(f"\n确认拆除 {building.name}? {refund_msg} (Y确认, 其他取消): ", end='', flush=True)
            confirm = get_key_blocking()
            print(confirm)
            if confirm == 'Y':
                success, msg = self.game_state.demolish_building(self.player_id, x, y)
                self.message = msg
            else:
                self.message = "取消拆除"
        else:
            self.message = "该位置没有你的建筑"

    def _handle_demolish_client(self):
        """处理拆除（客户端）"""
        x, y = self.renderer.selected_x, self.renderer.selected_y
        building = self.game_state.get_building_at(x, y)
        if building and building.owner_id == self.player_id:
            # 检查是否是本回合建造的建筑（全额返还）
            if hasattr(building, 'built_this_turn') and building.built_this_turn:
                refund = building.get_total_invested()
                refund_msg = f"全额返还{refund}经济 (本回合建造)"
            else:
                refund = building.get_demolish_refund()
                refund_msg = f"返还{refund}经济"
            print(f"\n确认拆除 {building.name}? {refund_msg} (Y确认, 其他取消): ", end='', flush=True)
            confirm = get_key_blocking()
            print(confirm)
            if confirm == 'Y':
                self.client.send_action({
                    'action': 'demolish',
                    'x': x,
                    'y': y
                })
                self.message = "已发送拆除请求"
            else:
                self.message = "取消拆除"
        else:
            self.message = "该位置没有你的建筑"

    def _handle_produce(self):
        """处理生产（单机）"""
        barracks_level = self.game_state.get_player_barracks_level(self.player_id)
        arms_factory_level = self.game_state.get_player_arms_factory_level(self.player_id)

        if barracks_level == 0 and arms_factory_level == 0:
            self.message = "没有兵营或兵工厂，无法生产单位"
            return

        player = self.game_state.get_player(self.player_id)
        unit_list = self.renderer.render_produce_menu(player, barracks_level, arms_factory_level)

        print("选择兵种 (输入编号, 0取消): ", end='', flush=True)
        choice_str = input().strip()

        if choice_str == '0':
            return

        try:
            idx = int(choice_str) - 1
            if 0 <= idx < len(unit_list):
                unit_type = unit_list[idx]
                count_str = input("生产数量 (k): ").strip() or "1"
                count = int(count_str)

                success, msg = self.game_state.produce_unit(
                    self.player_id,
                    unit_type,
                    count,
                    self.renderer.selected_x,
                    self.renderer.selected_y
                )
                self.message = msg
        except (ValueError, TypeError):
            self.message = "无效输入"

    def _handle_produce_client(self):
        """处理生产（客户端）"""
        barracks_level = self.game_state.get_player_barracks_level(self.player_id)
        arms_factory_level = self.game_state.get_player_arms_factory_level(self.player_id)

        if barracks_level == 0 and arms_factory_level == 0:
            self.message = "没有兵营或兵工厂，无法生产单位"
            return

        player = self.game_state.get_player(self.player_id)
        unit_list = self.renderer.render_produce_menu(player, barracks_level, arms_factory_level)

        print("选择兵种 (输入编号, 0取消): ", end='', flush=True)
        choice_str = input().strip()

        if choice_str == '0':
            return

        try:
            idx = int(choice_str) - 1
            if 0 <= idx < len(unit_list):
                unit_type = unit_list[idx]
                count_str = input("生产数量 (k): ").strip() or "1"
                count = int(count_str)

                self.client.send_action({
                    'action': 'produce',
                    'unit_type': unit_type,
                    'count': count,
                    'x': self.renderer.selected_x,
                    'y': self.renderer.selected_y
                })
                self.message = "已发送生产请求"
        except (ValueError, TypeError):
            self.message = "无效输入"

    def _handle_move(self):
        """处理移动（单机）"""
        units = [u for u in self.game_state.get_units_at(
            self.renderer.selected_x, self.renderer.selected_y
        ) if u.owner_id == self.player_id]

        if not units:
            self.message = "该位置没有你的单位"
            return

        if len(units) == 1:
            unit = units[0]
        else:
            self.renderer.render_unit_select_menu(units)
            print("选择单位: ", end='', flush=True)
            choice = get_key_blocking()
            print(choice)

            if choice == '0':
                return
            try:
                idx = int(choice) - 1
                if not (0 <= idx < len(units)):
                    self.message = "无效选择"
                    return
                unit = units[idx]
            except (ValueError, TypeError):
                self.message = "无效输入"
                return

        target = input("目标位置 (x,y): ").strip()
        try:
            tx, ty = map(int, target.split(','))
            success, msg = self.game_state.move_unit(self.player_id, unit.id, tx, ty)
            self.message = msg
            if success:
                self.renderer.selected_x = tx
                self.renderer.selected_y = ty
        except (ValueError, TypeError):
            self.message = "无效输入"

    def _handle_move_client(self):
        """处理移动（客户端）"""
        units = [u for u in self.game_state.get_units_at(
            self.renderer.selected_x, self.renderer.selected_y
        ) if u.owner_id == self.player_id]

        if not units:
            self.message = "该位置没有你的单位"
            return

        if len(units) == 1:
            unit = units[0]
        else:
            self.renderer.render_unit_select_menu(units)
            print("选择单位: ", end='', flush=True)
            choice = get_key_blocking()
            print(choice)

            if choice == '0':
                return
            try:
                idx = int(choice) - 1
                if not (0 <= idx < len(units)):
                    self.message = "无效选择"
                    return
                unit = units[idx]
            except (ValueError, TypeError):
                self.message = "无效输入"
                return

        target = input("目标位置 (x,y): ").strip()
        try:
            tx, ty = map(int, target.split(','))
            self.client.send_action({
                'action': 'move',
                'unit_id': unit.id,
                'to_x': tx,
                'to_y': ty
            })
            self.message = "已发送移动请求"
        except (ValueError, TypeError):
            self.message = "无效输入"

    def _handle_attack(self):
        """处理攻击（单机）"""
        units = [u for u in self.game_state.get_units_at(
            self.renderer.selected_x, self.renderer.selected_y
        ) if u.owner_id == self.player_id]

        if not units:
            self.message = "该位置没有你的单位"
            return

        if len(units) == 1:
            unit = units[0]
        else:
            self.renderer.render_unit_select_menu(units)
            print("选择单位: ", end='', flush=True)
            choice = get_key_blocking()
            print(choice)

            if choice == '0':
                return
            try:
                idx = int(choice) - 1
                if not (0 <= idx < len(units)):
                    self.message = "无效选择"
                    return
                unit = units[idx]
            except (ValueError, TypeError):
                self.message = "无效输入"
                return

        target = input("攻击目标位置 (x,y): ").strip()
        try:
            tx, ty = map(int, target.split(','))
            success, msg = self.game_state.attack(self.player_id, unit.id, tx, ty)
            self.message = msg
        except (ValueError, TypeError):
            self.message = "无效输入"

    def _handle_attack_client(self):
        """处理攻击（客户端）"""
        units = [u for u in self.game_state.get_units_at(
            self.renderer.selected_x, self.renderer.selected_y
        ) if u.owner_id == self.player_id]

        if not units:
            self.message = "该位置没有你的单位"
            return

        if len(units) == 1:
            unit = units[0]
        else:
            self.renderer.render_unit_select_menu(units)
            print("选择单位: ", end='', flush=True)
            choice = get_key_blocking()
            print(choice)

            if choice == '0':
                return
            try:
                idx = int(choice) - 1
                if not (0 <= idx < len(units)):
                    self.message = "无效选择"
                    return
                unit = units[idx]
            except (ValueError, TypeError):
                self.message = "无效输入"
                return

        target = input("攻击目标位置 (x,y): ").strip()
        try:
            tx, ty = map(int, target.split(','))
            self.client.send_action({
                'action': 'attack',
                'unit_id': unit.id,
                'target_x': tx,
                'target_y': ty
            })
            self.message = "已发送攻击请求"
        except (ValueError, TypeError):
            self.message = "无效输入"

    def _handle_client_action(self, player_id: int, action: dict):
        """处理客户端操作（服务器端）"""
        success, msg = self.server.process_action(player_id, action)
        self.server.send_to_player(player_id, {
            'type': 'action_result',
            'success': success,
            'message': msg
        })

    def _handle_focus(self):
        """处理国策（单机/房主）"""
        player = self.game_state.get_player(self.player_id)
        focus_tree = self.game_state.get_focus_tree(self.player_id)

        if not focus_tree:
            self.message = "国策系统不可用"
            return

        focus_list = self.renderer.render_focus_menu(player, focus_tree)

        if not focus_list:
            if focus_tree.current_focus:
                print("  当前正在研究中，无法开始新国策")
            else:
                print("  没有可研究的国策")
            get_key_blocking()
            return

        print("选择国策 (输入编号, 0取消): ", end='', flush=True)
        choice_str = input().strip()

        if choice_str == '0':
            return

        try:
            idx = int(choice_str) - 1
            if 0 <= idx < len(focus_list):
                focus_id = focus_list[idx]
                success, msg = self.game_state.start_focus(self.player_id, focus_id)
                self.message = msg
            else:
                self.message = "无效选择"
        except (ValueError, TypeError):
            self.message = "无效输入"

    def _handle_focus_client(self):
        """处理国策（客户端）"""
        player = self.game_state.get_player(self.player_id)
        focus_tree = self.game_state.get_focus_tree(self.player_id)

        if not focus_tree:
            self.message = "国策系统不可用"
            return

        focus_list = self.renderer.render_focus_menu(player, focus_tree)

        if not focus_list:
            if focus_tree.current_focus:
                print("  当前正在研究中，无法开始新国策")
            else:
                print("  没有可研究的国策")
            get_key_blocking()
            return

        print("选择国策 (输入编号, 0取消): ", end='', flush=True)
        choice_str = input().strip()

        if choice_str == '0':
            return

        try:
            idx = int(choice_str) - 1
            if 0 <= idx < len(focus_list):
                focus_id = focus_list[idx]
                self.client.send_action({
                    'action': 'start_focus',
                    'focus_id': focus_id
                })
                self.message = "已发送国策研究请求"
            else:
                self.message = "无效选择"
        except (ValueError, TypeError):
            self.message = "无效输入"

    def _handle_nuke(self):
        """处理核武器（单机/房主）"""
        player = self.game_state.get_player(self.player_id)
        focus_tree = self.game_state.get_focus_tree(self.player_id)
        has_nuke = focus_tree.has_nuclear_capability() if focus_tree else False

        # 获取可用发射设施
        launchers = self.game_state.get_player_launchers(self.player_id) if has_nuke else []

        can_launch, launcher_list = self.renderer.render_nuke_menu(player, has_nuke, launchers)
        if not can_launch:
            get_key_blocking()
            return

        # 选择发射设施
        if len(launcher_list) == 1:
            selected_launcher = launcher_list[0]
            print(f"  使用发射设施: ({selected_launcher.x},{selected_launcher.y})")
        else:
            print("选择发射设施编号: ", end='', flush=True)
            choice = get_key_blocking()
            print(choice)
            if choice == '0':
                return
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(launcher_list):
                    selected_launcher = launcher_list[idx]
                else:
                    self.message = "无效选择"
                    return
            except (ValueError, TypeError):
                self.message = "无效输入"
                return

        target = input("目标坐标 (x,y) 或 0取消: ").strip()
        if target == '0':
            return

        try:
            tx, ty = map(int, target.split(','))
            # 显示3x3影响范围
            print(f"\n  核弹将影响以下范围 (3x3):")
            print(f"    ({tx-1},{ty-1}) ({tx},{ty-1}) ({tx+1},{ty-1})")
            print(f"    ({tx-1},{ty})   ({tx},{ty})   ({tx+1},{ty})")
            print(f"    ({tx-1},{ty+1}) ({tx},{ty+1}) ({tx+1},{ty+1})")
            print("  确认发射? (Y确认, 其他取消): ", end='', flush=True)
            confirm = get_key_blocking()
            print(confirm)
            if confirm != 'Y':
                self.message = "取消发射"
                return

            launcher_id = selected_launcher.x * 10000 + selected_launcher.y
            success, msg = self.game_state.launch_nuke(self.player_id, launcher_id, tx, ty)
            self.message = msg
        except (ValueError, TypeError):
            self.message = "无效输入"

    def _handle_nuke_client(self):
        """处理核武器（客户端）"""
        player = self.game_state.get_player(self.player_id)
        focus_tree = self.game_state.get_focus_tree(self.player_id)
        has_nuke = focus_tree.has_nuclear_capability() if focus_tree else False

        # 获取可用发射设施
        launchers = self.game_state.get_player_launchers(self.player_id) if has_nuke else []

        can_launch, launcher_list = self.renderer.render_nuke_menu(player, has_nuke, launchers)
        if not can_launch:
            get_key_blocking()
            return

        # 选择发射设施
        if len(launcher_list) == 1:
            selected_launcher = launcher_list[0]
            print(f"  使用发射设施: ({selected_launcher.x},{selected_launcher.y})")
        else:
            print("选择发射设施编号: ", end='', flush=True)
            choice = get_key_blocking()
            print(choice)
            if choice == '0':
                return
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(launcher_list):
                    selected_launcher = launcher_list[idx]
                else:
                    self.message = "无效选择"
                    return
            except (ValueError, TypeError):
                self.message = "无效输入"
                return

        target = input("目标坐标 (x,y) 或 0取消: ").strip()
        if target == '0':
            return

        try:
            tx, ty = map(int, target.split(','))
            # 显示3x3影响范围
            print(f"\n  核弹将影响以下范围 (3x3):")
            print(f"    ({tx-1},{ty-1}) ({tx},{ty-1}) ({tx+1},{ty-1})")
            print(f"    ({tx-1},{ty})   ({tx},{ty})   ({tx+1},{ty})")
            print(f"    ({tx-1},{ty+1}) ({tx},{ty+1}) ({tx+1},{ty+1})")
            print("  确认发射? (Y确认, 其他取消): ", end='', flush=True)
            confirm = get_key_blocking()
            print(confirm)
            if confirm != 'Y':
                self.message = "取消发射"
                return

            launcher_id = selected_launcher.x * 10000 + selected_launcher.y
            self.client.send_action({
                'action': 'launch_nuke',
                'launcher_id': launcher_id,
                'target_x': tx,
                'target_y': ty
            })
            self.message = "已发送核弹发射请求"
        except (ValueError, TypeError):
            self.message = "无效输入"

    def _end_turn_single(self):
        """结束回合（单机）"""
        self.game_state.process_turn()
        self.message = f"回合 {self.game_state.current_turn} 开始"

    def _end_turn_host(self):
        """结束回合（房主）"""
        player = self.game_state.get_player(self.player_id)
        player.ready_for_next_turn = True
        self.message = "等待其他玩家结束回合..."
        self.server._check_all_ready()

    def _end_turn_client(self):
        """结束回合（客户端）"""
        self.client.send_end_turn()
        self.message = "等待其他玩家结束回合..."


def main():
    """主函数"""
    if os.name == 'nt':
        os.system('chcp 65001 > nul')
        os.system('mode con: cols=100 lines=45')

    game = Game()
    try:
        game.run()
    except KeyboardInterrupt:
        print("\n游戏已退出")
    finally:
        if game.server:
            game.server.stop()
        if game.client:
            game.client.disconnect()


if __name__ == '__main__':
    main()
