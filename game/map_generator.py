# -*- coding: utf-8 -*-
"""地图生成器"""

import random
from typing import List, Tuple, Set
from config import MAP_WIDTH, MAP_HEIGHT, TERRAIN_PLAIN, TERRAIN_RIVER


class GameMap:
    """游戏地图类"""

    def __init__(self, width: int = MAP_WIDTH, height: int = MAP_HEIGHT):
        self.width = width
        self.height = height
        self.terrain = [[TERRAIN_PLAIN for _ in range(width)] for _ in range(height)]
        self.territory = [[None for _ in range(width)] for _ in range(height)]  # 领土归属

    def generate(self, river_count: int = 5, seed: int = None):
        """生成地图，包含河流"""
        if seed is not None:
            random.seed(seed)

        # 生成河流
        for _ in range(river_count):
            self._generate_river()

    def _generate_river(self):
        """生成一条蜿蜒的河流（两格宽）"""
        # 随机选择河流起点（从地图边缘开始）
        side = random.randint(0, 3)
        if side == 0:  # 上边
            x, y = random.randint(0, self.width - 1), 0
            direction = (0, 1)
        elif side == 1:  # 下边
            x, y = random.randint(0, self.width - 1), self.height - 1
            direction = (0, -1)
        elif side == 2:  # 左边
            x, y = 0, random.randint(0, self.height - 1)
            direction = (1, 0)
        else:  # 右边
            x, y = self.width - 1, random.randint(0, self.height - 1)
            direction = (-1, 0)

        # 河流长度
        length = random.randint(self.width // 2, self.width)

        for _ in range(length):
            if 0 <= x < self.width and 0 <= y < self.height:
                self.terrain[y][x] = TERRAIN_RIVER
                # 两格宽：在垂直于流向的方向添加一格
                if direction[0] == 0:  # 垂直流动，水平扩展
                    if x + 1 < self.width:
                        self.terrain[y][x + 1] = TERRAIN_RIVER
                else:  # 水平流动，垂直扩展
                    if y + 1 < self.height:
                        self.terrain[y + 1][x] = TERRAIN_RIVER

            # 随机改变方向（蜿蜒效果）
            if random.random() < 0.3:
                if direction[0] == 0:  # 垂直移动
                    direction = (random.choice([-1, 1]), direction[1])
                else:  # 水平移动
                    direction = (direction[0], random.choice([-1, 1]))

            # 移动
            x += direction[0]
            y += direction[1]

            # 边界检查
            if x < 0 or x >= self.width or y < 0 or y >= self.height:
                break

    def get_terrain(self, x: int, y: int) -> str:
        """获取指定位置的地形"""
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.terrain[y][x]
        return None

    def get_territory_owner(self, x: int, y: int) -> int:
        """获取指定位置的领土归属"""
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.territory[y][x]
        return None

    def set_territory(self, x: int, y: int, owner_id: int):
        """设置领土归属（河流不可占领）"""
        if 0 <= x < self.width and 0 <= y < self.height:
            if self.terrain[y][x] != TERRAIN_RIVER:
                self.territory[y][x] = owner_id

    def claim_territory_radius(self, center_x: int, center_y: int, radius: int, owner_id: int):
        """占领以某点为中心的圆形区域（河流不可占领）"""
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                if dx * dx + dy * dy <= radius * radius:
                    x, y = center_x + dx, center_y + dy
                    if 0 <= x < self.width and 0 <= y < self.height:
                        if self.terrain[y][x] != TERRAIN_RIVER:
                            self.territory[y][x] = owner_id

    def get_spawn_positions(self, num_players: int) -> List[Tuple[int, int]]:
        """为玩家生成分散的出生点"""
        positions = []
        margin = 8  # 距离边缘的最小距离

        # 根据玩家数量选择分布方式
        if num_players <= 2:
            # 两人对角
            positions = [
                (margin, margin),
                (self.width - margin - 1, self.height - margin - 1)
            ]
        elif num_players <= 4:
            # 四角
            positions = [
                (margin, margin),
                (self.width - margin - 1, margin),
                (margin, self.height - margin - 1),
                (self.width - margin - 1, self.height - margin - 1)
            ]
        else:
            # 更多玩家，均匀分布
            cols = 3 if num_players <= 6 else 4
            rows = (num_players + cols - 1) // cols
            cell_w = (self.width - 2 * margin) // cols
            cell_h = (self.height - 2 * margin) // rows

            for i in range(num_players):
                row = i // cols
                col = i % cols
                x = margin + col * cell_w + cell_w // 2
                y = margin + row * cell_h + cell_h // 2
                positions.append((x, y))

        # 确保出生点不在河流上
        final_positions = []
        for x, y in positions[:num_players]:
            # 如果在河流上，寻找附近的平地
            if self.terrain[y][x] == TERRAIN_RIVER:
                found = False
                for r in range(1, 10):
                    for dy in range(-r, r + 1):
                        for dx in range(-r, r + 1):
                            nx, ny = x + dx, y + dy
                            if 0 <= nx < self.width and 0 <= ny < self.height:
                                if self.terrain[ny][nx] == TERRAIN_PLAIN:
                                    x, y = nx, ny
                                    found = True
                                    break
                        if found:
                            break
                    if found:
                        break
            final_positions.append((x, y))

        return final_positions

    def get_adjacent_cells(self, x: int, y: int) -> List[Tuple[int, int]]:
        """获取相邻的格子（上下左右）"""
        adjacent = []
        for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.width and 0 <= ny < self.height:
                adjacent.append((nx, ny))
        return adjacent

    def to_dict(self) -> dict:
        return {
            'width': self.width,
            'height': self.height,
            'terrain': self.terrain,
            'territory': self.territory
        }

    @staticmethod
    def from_dict(data: dict) -> 'GameMap':
        game_map = GameMap(data['width'], data['height'])
        game_map.terrain = data['terrain']
        game_map.territory = data['territory']
        return game_map
