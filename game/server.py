# -*- coding: utf-8 -*-
"""游戏服务器"""

import socket
import threading
import json
import time
import subprocess
import os
from typing import Dict, List, Optional, Callable
from game_state import GameState
from config import DEFAULT_PORT, MAX_PLAYERS


def get_local_ip() -> str:
    """可靠地获取本机局域网IP"""
    try:
        # 通过UDP连接外部地址来确定本机IP（不会真正发送数据）
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(2)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        pass
    # 备用方案
    try:
        hostname = socket.gethostname()
        ips = socket.getaddrinfo(hostname, None, socket.AF_INET)
        for info in ips:
            ip = info[4][0]
            if ip != '127.0.0.1':
                return ip
    except Exception:
        pass
    # 最后备用
    try:
        return socket.gethostbyname(socket.gethostname())
    except Exception:
        return '127.0.0.1'


def get_public_ip() -> Optional[str]:
    """获取公网IP"""
    import urllib.request
    services = [
        'https://api.ipify.org',
        'https://ifconfig.me/ip',
        'https://icanhazip.com',
    ]
    for url in services:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as resp:
                ip = resp.read().decode().strip()
                # 验证IP格式
                socket.inet_aton(ip)
                return ip
        except Exception:
            continue
    return None


def open_firewall_port(port: int) -> bool:
    """在Windows防火墙中开放端口"""
    if os.name != 'nt':
        return False
    try:
        rule_name = f"IronFrontLine_TCP_{port}"
        # 先删除旧规则（忽略错误）
        subprocess.run(
            ['netsh', 'advfirewall', 'firewall', 'delete', 'rule', f'name={rule_name}'],
            capture_output=True, timeout=10
        )
        # 添加入站规则
        result = subprocess.run(
            ['netsh', 'advfirewall', 'firewall', 'add', 'rule',
             f'name={rule_name}', 'dir=in', 'action=allow', 'protocol=TCP',
             f'localport={port}', 'profile=any'],
            capture_output=True, timeout=10
        )
        return result.returncode == 0
    except Exception:
        return False


class GameServer:
    """游戏服务器类"""

    def __init__(self, port: int = DEFAULT_PORT):
        self.port = port
        self.server_socket: Optional[socket.socket] = None
        self.clients: Dict[int, socket.socket] = {}  # player_id -> socket
        self.client_threads: Dict[int, threading.Thread] = {}
        self.player_names: List[str] = []
        self.game_state: Optional[GameState] = None
        self.running = False
        self.game_started = False
        self.internet_mode = False  # 互联网模式
        self.public_ip: Optional[str] = None  # 公网IP

        # 回调函数
        self.on_player_join: Optional[Callable[[str], None]] = None
        self.on_player_leave: Optional[Callable[[int], None]] = None
        self.on_action: Optional[Callable[[int, dict], None]] = None
        self.on_all_ready: Optional[Callable[[], None]] = None

        self._lock = threading.Lock()

    def start(self, host_name: str) -> str:
        """启动服务器，返回服务器IP"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(('0.0.0.0', self.port))
        self.server_socket.listen(MAX_PLAYERS)
        self.running = True

        # 房主作为第一个玩家
        self.player_names.append(host_name)

        # 获取本机局域网IP
        local_ip = get_local_ip()

        # 尝试开放防火墙端口
        firewall_ok = open_firewall_port(self.port)
        if not firewall_ok:
            print("  [提示] 无法自动开放防火墙，请手动允许端口或关闭防火墙")

        # 启动接受连接的线程
        accept_thread = threading.Thread(target=self._accept_connections, daemon=True)
        accept_thread.start()

        return local_ip

    def enable_internet_mode(self) -> tuple:
        """开启互联网连接模式，返回 (成功, 公网IP或错误信息)"""
        print("  正在获取公网IP...")
        public_ip = get_public_ip()
        if public_ip:
            self.internet_mode = True
            self.public_ip = public_ip
            return True, public_ip
        else:
            return False, "无法获取公网IP，请检查网络连接"

    def disable_internet_mode(self):
        """关闭互联网连接模式"""
        self.internet_mode = False
        self.public_ip = None

    def _accept_connections(self):
        """接受新连接"""
        while self.running and not self.game_started:
            try:
                self.server_socket.settimeout(1.0)
                client_socket, address = self.server_socket.accept()

                if len(self.player_names) >= MAX_PLAYERS:
                    client_socket.send(json.dumps({'type': 'error', 'message': '房间已满'}).encode())
                    client_socket.close()
                    continue

                if self.game_started:
                    client_socket.send(json.dumps({'type': 'error', 'message': '游戏已开始'}).encode())
                    client_socket.close()
                    continue

                # 接收玩家名称
                data = client_socket.recv(4096).decode()
                msg = json.loads(data)
                player_name = msg.get('name', f'玩家{len(self.player_names) + 1}')

                with self._lock:
                    player_id = len(self.player_names)
                    self.player_names.append(player_name)
                    self.clients[player_id] = client_socket

                # 发送确认和当前玩家列表
                response = {
                    'type': 'joined',
                    'player_id': player_id,
                    'players': self.player_names
                }
                client_socket.send(json.dumps(response).encode())

                # 通知其他玩家
                self._broadcast({
                    'type': 'player_joined',
                    'players': self.player_names
                }, exclude=player_id)

                # 启动该客户端的处理线程
                client_thread = threading.Thread(
                    target=self._handle_client,
                    args=(player_id, client_socket),
                    daemon=True
                )
                self.client_threads[player_id] = client_thread
                client_thread.start()

                if self.on_player_join:
                    self.on_player_join(player_name)

            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"接受连接错误: {e}")
                break

    def _handle_client(self, player_id: int, client_socket: socket.socket):
        """处理单个客户端"""
        while self.running:
            try:
                client_socket.settimeout(1.0)
                data = client_socket.recv(4096).decode()
                if not data:
                    break

                msg = json.loads(data)
                self._process_message(player_id, msg)

            except socket.timeout:
                continue
            except Exception as e:
                print(f"客户端 {player_id} 错误: {e}")
                break

        # 玩家断开连接
        with self._lock:
            if player_id in self.clients:
                del self.clients[player_id]
        if self.on_player_leave:
            self.on_player_leave(player_id)

    def _process_message(self, player_id: int, msg: dict):
        """处理客户端消息"""
        msg_type = msg.get('type')

        if msg_type == 'action':
            if self.on_action:
                self.on_action(player_id, msg)

        elif msg_type == 'end_turn':
            if self.game_state:
                player = self.game_state.get_player(player_id)
                if player:
                    player.ready_for_next_turn = True
                    self._check_all_ready()

        elif msg_type == 'chat':
            self._broadcast({
                'type': 'chat',
                'player_id': player_id,
                'message': msg.get('message', '')
            })

    def _check_all_ready(self):
        """检查是否所有玩家都准备好了"""
        if not self.game_state:
            return

        all_ready = all(
            p.ready_for_next_turn or not p.is_alive
            for p in self.game_state.players.values()
        )

        if all_ready:
            self.game_state.process_turn()
            self.sync_game_state()
            if self.on_all_ready:
                self.on_all_ready()

    def _broadcast(self, msg: dict, exclude: int = None):
        """广播消息给所有客户端"""
        data = json.dumps(msg).encode()
        with self._lock:
            for pid, sock in list(self.clients.items()):
                if pid != exclude:
                    try:
                        sock.send(data)
                    except:
                        pass

    def start_game(self, map_seed: int = None, map_width: int = None, map_height: int = None):
        """开始游戏"""
        self.game_started = True
        self.game_state = GameState()
        self.game_state.initialize_game(self.player_names, map_seed, map_width, map_height)

        # 通知所有客户端
        self._broadcast({
            'type': 'game_start',
            'state': self.game_state.to_dict()
        })

    def sync_game_state(self):
        """同步游戏状态给所有客户端"""
        if self.game_state:
            self._broadcast({
                'type': 'sync',
                'state': self.game_state.to_dict()
            })

    def send_to_player(self, player_id: int, msg: dict):
        """发送消息给特定玩家"""
        with self._lock:
            if player_id in self.clients:
                try:
                    self.clients[player_id].send(json.dumps(msg).encode())
                except:
                    pass

    def process_action(self, player_id: int, action: dict) -> tuple:
        """处理玩家操作"""
        if not self.game_state:
            return False, "游戏未开始"

        action_type = action.get('action')

        if action_type == 'build':
            success, msg = self.game_state.build(
                player_id,
                action['building'],
                action['x'],
                action['y']
            )
        elif action_type == 'upgrade':
            success, msg = self.game_state.upgrade_building(
                player_id,
                action['x'],
                action['y']
            )
        elif action_type == 'produce':
            success, msg = self.game_state.produce_unit(
                player_id,
                action['unit_type'],
                action['count'],
                action['x'],
                action['y']
            )
        elif action_type == 'move':
            success, msg = self.game_state.move_unit(
                player_id,
                action['unit_id'],
                action['to_x'],
                action['to_y']
            )
        elif action_type == 'attack':
            success, msg = self.game_state.attack(
                player_id,
                action['unit_id'],
                action['target_x'],
                action['target_y']
            )
        elif action_type == 'demolish':
            success, msg = self.game_state.demolish_building(
                player_id,
                action['x'],
                action['y']
            )
        elif action_type == 'split':
            success, msg = self.game_state.split_unit(
                player_id,
                action['unit_id'],
                action['amount']
            )
        elif action_type == 'set_attack_direction':
            # 为多个单位设置进攻方向
            unit_ids = action.get('unit_ids', [])
            dx, dy = action['dx'], action['dy']
            for uid in unit_ids:
                for u in self.game_state.units:
                    if u.id == uid and u.owner_id == player_id:
                        u.set_attack_direction(dx, dy)
            success, msg = True, f"已设置{len(unit_ids)}个单位的进攻方向"
        elif action_type == 'set_defense_direction':
            # 为多个单位设置防守方向
            unit_ids = action.get('unit_ids', [])
            dx, dy = action['dx'], action['dy']
            for uid in unit_ids:
                for u in self.game_state.units:
                    if u.id == uid and u.owner_id == player_id:
                        u.set_defense_direction(dx, dy)
            success, msg = True, f"已设置{len(unit_ids)}个单位的防守方向"
        elif action_type == 'start_focus':
            success, msg = self.game_state.start_focus(
                player_id,
                action['focus_id']
            )
        elif action_type == 'launch_nuke':
            launcher_id = action.get('launcher_id')
            if launcher_id is not None:
                success, msg = self.game_state.launch_nuke(
                    player_id,
                    launcher_id,
                    action['target_x'],
                    action['target_y']
                )
            else:
                # 兼容旧版本：自动选择发射器
                success, msg = self.game_state.launch_nuke_simple(
                    player_id,
                    action['target_x'],
                    action['target_y']
                )
        else:
            return False, "未知操作"

        # 同步状态
        self.sync_game_state()

        return success, msg

    def stop(self):
        """停止服务器"""
        self.running = False
        with self._lock:
            for sock in self.clients.values():
                try:
                    sock.close()
                except:
                    pass
            self.clients.clear()

        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass

    def get_player_count(self) -> int:
        return len(self.player_names)

    def get_player_names(self) -> List[str]:
        return self.player_names.copy()
