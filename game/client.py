# -*- coding: utf-8 -*-
"""游戏客户端"""

import socket
import threading
import json
from typing import Optional, Callable, List
from game_state import GameState
from config import DEFAULT_PORT


class GameClient:
    """游戏客户端类"""

    def __init__(self):
        self.socket: Optional[socket.socket] = None
        self.player_id: int = -1
        self.player_name: str = ""
        self.connected = False
        self.game_state: Optional[GameState] = None
        self.player_list: List[str] = []

        # 回调函数
        self.on_game_start: Optional[Callable[[GameState], None]] = None
        self.on_state_update: Optional[Callable[[GameState], None]] = None
        self.on_player_list_update: Optional[Callable[[List[str]], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        self.on_chat: Optional[Callable[[int, str], None]] = None
        self.on_disconnect: Optional[Callable[[], None]] = None

        self._receive_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def connect(self, host: str, name: str, port: int = DEFAULT_PORT) -> tuple:
        """连接到服务器"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(15.0)  # 增加超时时间以支持互联网连接
            self.socket.connect((host, port))
            self.player_name = name

            # 发送玩家名称
            self.socket.send(json.dumps({'name': name}).encode())

            # 接收响应
            data = self.socket.recv(4096).decode()
            msg = json.loads(data)

            if msg.get('type') == 'error':
                self.socket.close()
                return False, msg.get('message', '连接失败')

            if msg.get('type') == 'joined':
                self.player_id = msg['player_id']
                self.player_list = msg['players']
                self.connected = True

                # 启动接收线程
                self.socket.settimeout(None)
                self._receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
                self._receive_thread.start()

                return True, "连接成功"

            return False, "未知响应"

        except socket.timeout:
            return False, "连接超时"
        except ConnectionRefusedError:
            return False, "无法连接到服务器"
        except Exception as e:
            return False, f"连接错误: {e}"

    def _receive_loop(self):
        """接收消息循环"""
        buffer = ""
        while self.connected:
            try:
                self.socket.settimeout(1.0)
                data = self.socket.recv(4096).decode()
                if not data:
                    break

                buffer += data

                # 处理可能的多条消息
                while buffer:
                    try:
                        msg, idx = json.JSONDecoder().raw_decode(buffer)
                        buffer = buffer[idx:].lstrip()
                        self._process_message(msg)
                    except json.JSONDecodeError:
                        break

            except socket.timeout:
                continue
            except Exception as e:
                if self.connected:
                    print(f"接收错误: {e}")
                break

        self.connected = False
        if self.on_disconnect:
            self.on_disconnect()

    def _process_message(self, msg: dict):
        """处理服务器消息"""
        msg_type = msg.get('type')

        if msg_type == 'player_joined':
            self.player_list = msg['players']
            if self.on_player_list_update:
                self.on_player_list_update(self.player_list)

        elif msg_type == 'game_start':
            self.game_state = GameState.from_dict(msg['state'])
            if self.on_game_start:
                self.on_game_start(self.game_state)

        elif msg_type == 'sync':
            self.game_state = GameState.from_dict(msg['state'])
            if self.on_state_update:
                self.on_state_update(self.game_state)

        elif msg_type == 'error':
            if self.on_error:
                self.on_error(msg.get('message', '未知错误'))

        elif msg_type == 'chat':
            if self.on_chat:
                self.on_chat(msg['player_id'], msg['message'])

        elif msg_type == 'action_result':
            # 操作结果由主循环处理
            pass

    def send_action(self, action: dict):
        """发送操作"""
        if self.connected and self.socket:
            try:
                msg = {'type': 'action', **action}
                self.socket.send(json.dumps(msg).encode())
            except Exception as e:
                print(f"发送错误: {e}")

    def send_end_turn(self):
        """发送回合结束"""
        if self.connected and self.socket:
            try:
                self.socket.send(json.dumps({'type': 'end_turn'}).encode())
            except Exception as e:
                print(f"发送错误: {e}")

    def send_chat(self, message: str):
        """发送聊天消息"""
        if self.connected and self.socket:
            try:
                self.socket.send(json.dumps({'type': 'chat', 'message': message}).encode())
            except Exception as e:
                print(f"发送错误: {e}")

    def disconnect(self):
        """断开连接"""
        self.connected = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass

    def is_connected(self) -> bool:
        return self.connected

    def get_player_id(self) -> int:
        return self.player_id

    def get_player_list(self) -> List[str]:
        return self.player_list.copy()
