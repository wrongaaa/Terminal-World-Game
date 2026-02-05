# -*- coding: utf-8 -*-
"""游戏配置常量"""

# 游戏名称
GAME_NAME = "铁血战线 - 局域网对战"

# 地图配置
MAP_WIDTH = 80
MAP_HEIGHT = 40

# 根据玩家数量推荐的地图大小 (玩家数: (宽度, 高度))
RECOMMENDED_MAP_SIZES = {
    1: (60, 30),    # 单人测试
    2: (100, 50),   # 2人对战 - 大地图
    3: (120, 60),   # 3人对战
    4: (140, 70),   # 4人对战
    5: (150, 75),   # 5人对战
    6: (160, 80),   # 6人对战
    7: (170, 85),   # 7人对战
    8: (180, 90),   # 8人对战
}

# 预设地图大小选项
MAP_SIZE_PRESETS = {
    'small': (60, 30, '小型'),
    'medium': (80, 40, '中型'),
    'large': (100, 50, '大型'),
    'huge': (120, 60, '巨大'),
    'epic': (150, 75, '史诗'),
}

# 地形类型
TERRAIN_PLAIN = '.'  # 平地
TERRAIN_RIVER = '~'  # 河流
TERRAIN_BRIDGE = '='  # 桥梁（建在河流上）

# 河流移动消耗倍数
RIVER_MOVE_COST = 2
# 河流防御加成
RIVER_DEFENSE_BONUS = 1.5
# 过江攻击惩罚（攻击力倍数）
RIVER_ATTACK_PENALTY = 0.5

# 视野系统
BASE_VISIBILITY_RANGE = 3  # 基础视野范围
UNIT_VISIBILITY_BONUS = 1  # 单位额外提供的视野
SCOUT_VISIBILITY_BONUS = 3  # 侦察兵额外视野加成

# 隐蔽性系统
# 隐蔽值越高，越难被发现（需要更近的距离才能发现）
# 实际侦察距离 = 基础视野 + 单位视野 - 目标隐蔽值

# 遭遇战惩罚（双方都看不见对方时）
ENCOUNTER_BATTLE_PENALTY = 0.7  # 双方攻防都降低30%
# 突袭加成（我方看见敌方，敌方看不见我方）
AMBUSH_ATTACK_BONUS = 1.3  # 突袭方攻击+30%
AMBUSH_DEFENSE_PENALTY = 0.7  # 被突袭方防御-30%

# 防线加成
FORTIFICATION_DEFENSE_BONUS = 1.5  # 防线防御+50%

# 建筑拆除返还比例
DEMOLISH_REFUND_RATE = 0.5  # 返还50%

# 网络配置
DEFAULT_PORT = 5555
MAX_PLAYERS = 8

# 初始资源
INITIAL_ECONOMY = 200
INITIAL_POPULATION = 50  # 50k
INITIAL_POP_CAP = 100    # 100k
BASE_POP_GROWTH_RATE = 0.02  # 2%

# 初始领土半径
INITIAL_TERRITORY_RADIUS = 3

# 建筑配置
BUILDINGS = {
    'factory': {
        'name': '工厂',
        'symbol': 'F',
        'levels': {
            1: {'cost': 100, 'economy': 10},
            2: {'cost': 250, 'economy': 25},
            3: {'cost': 500, 'economy': 50},
        }
    },
    'city': {
        'name': '城市',
        'symbol': 'C',
        'levels': {
            1: {'cost': 150, 'pop_cap': 50, 'growth_bonus': 0.01},
            2: {'cost': 400, 'pop_cap': 150, 'growth_bonus': 0.02},
            3: {'cost': 800, 'pop_cap': 300, 'growth_bonus': 0.03},
        }
    },
    'barracks': {
        'name': '兵营',
        'symbol': 'B',
        'levels': {
            1: {'cost': 100},   # 解锁基础步兵、摩托兵
            2: {'cost': 300},   # 解锁精锐步兵、摩托化步兵
            3: {'cost': 600},   # 解锁特种兵、机械化步兵
        }
    },
    'arms_factory': {
        'name': '兵工厂',
        'symbol': 'W',
        'levels': {
            1: {'cost': 200},   # 解锁装甲车、轻型坦克
            2: {'cost': 400},   # 解锁自行火炮
            3: {'cost': 600},   # 解锁中型坦克
            4: {'cost': 900},   # 解锁火箭炮
            5: {'cost': 1200},  # 解锁重型坦克
        }
    },
    'bridge': {
        'name': '桥梁',
        'symbol': '=',
        'levels': {
            1: {'cost': 200},  # 只有1级，建在河流上
        }
    },
    'fortification': {
        'name': '防线',
        'symbol': '#',
        'levels': {
            1: {'cost': 80, 'defense_bonus': 1.3},   # 防御+30%
            2: {'cost': 200, 'defense_bonus': 1.5},  # 防御+50%
            3: {'cost': 400, 'defense_bonus': 1.8},  # 防御+80%
        }
    },
    'nuclear_silo': {
        'name': '核发射井',
        'symbol': 'S',
        'levels': {
            1: {'cost': 2000},  # 固定核发射平台
        }
    },
    'mobile_launcher': {
        'name': '移动发射平台',
        'symbol': 'V',
        'levels': {
            1: {'cost': 5000},  # 可移动核发射平台
        }
    },
    'nuclear_interceptor': {
        'name': '核拦截平台',
        'symbol': 'Y',
        'levels': {
            1: {'cost': 3000},  # 拦截范围5x5
        }
    },
    'train_station': {
        'name': '火车站',
        'symbol': 'T',
        'levels': {
            1: {'cost': 300, 'connect_radius': 5, 'train_interval': 5, 'train_income': 5},
            2: {'cost': 600, 'connect_radius': 7, 'train_interval': 4, 'train_income': 10},
            3: {'cost': 1000, 'connect_radius': 10, 'train_interval': 3, 'train_income': 15},
        }
    }
}

# 单位类别
UNIT_CATEGORIES = {
    'scout': '侦察',
    'infantry': '步兵',
    'motorized': '摩托化',
    'artillery': '炮兵',
    'tank': '坦克'
}

# 单位生产来源
UNIT_PRODUCTION_SOURCE = {
    'scout': 'barracks',         # 兵营生产
    'infantry': 'barracks',      # 兵营生产
    'motorized': 'barracks',     # 兵营生产
    'artillery': 'arms_factory', # 兵工厂生产
    'tank': 'arms_factory'       # 兵工厂生产
}

# 兵种配置 (以k为单位)
# category: 类别, required_level: 需要的建筑等级, production_time: 生产回合数(0=即时)
# stealth: 隐蔽性(0=普通, 越高越难被发现), detection: 侦察能力(提升发现隐蔽单位的能力)
# trait: 特殊词条
UNITS = {
    # ========== 侦察类 (兵营生产) ==========
    'scout': {
        'name': '侦察兵',
        'category': 'scout',
        'required_level': 1,
        'cost': 8,
        'pop_cost': 1,
        'attack': 5,
        'defense': 5,
        'speed': 4,
        'production_time': 0,
        'stealth': 2,
        'detection': 3,
        'symbol': 'i',
        'trait': 'stealth',  # 潜行：更难被发现，隐蔽+1
        'trait_name': '潜行',
        'trait_desc': '隐蔽能力+1'
    },
    'recon_cavalry': {
        'name': '侦察骑兵',
        'category': 'scout',
        'required_level': 2,
        'cost': 15,
        'pop_cost': 1,
        'attack': 8,
        'defense': 6,
        'speed': 5,
        'production_time': 0,
        'stealth': 2,
        'detection': 4,
        'symbol': 'c',
        'trait': 'raid',  # 袭扰：攻击后保留1点移动力
        'trait_name': '袭扰',
        'trait_desc': '攻击后保留1点移动力'
    },
    'special_recon': {
        'name': '特种侦察',
        'category': 'scout',
        'required_level': 3,
        'cost': 25,
        'pop_cost': 1,
        'attack': 12,
        'defense': 8,
        'speed': 4,
        'production_time': 0,
        'stealth': 3,
        'detection': 5,
        'symbol': 'r',
        'trait': 'infiltrate',  # 渗透：可进入敌方领土不被自动发现
        'trait_name': '渗透',
        'trait_desc': '进入敌方领土时不会被自动发现'
    },

    # ========== 步兵类 (兵营生产) ==========
    'basic_infantry': {
        'name': '基础步兵',
        'category': 'infantry',
        'required_level': 1,
        'cost': 10,
        'pop_cost': 1,
        'attack': 10,
        'defense': 15,
        'speed': 2,
        'production_time': 0,
        'stealth': 0,
        'detection': 0,
        'symbol': 'I',
        'trait': 'fortify',  # 坚守：未移动时防御+20%
        'trait_name': '坚守',
        'trait_desc': '本回合未移动时防御+20%'
    },
    'elite_infantry': {
        'name': '精锐步兵',
        'category': 'infantry',
        'required_level': 2,
        'cost': 20,
        'pop_cost': 1,
        'attack': 18,
        'defense': 22,
        'speed': 2,
        'production_time': 0,
        'stealth': 0,
        'detection': 1,
        'symbol': 'E',
        'trait': 'veteran',  # 老练：攻防各+10%
        'trait_name': '老练',
        'trait_desc': '攻击和防御各+10%'
    },
    'special_forces': {
        'name': '特种兵',
        'category': 'infantry',
        'required_level': 3,
        'cost': 35,
        'pop_cost': 1,
        'attack': 28,
        'defense': 20,
        'speed': 3,
        'production_time': 0,
        'stealth': 1,
        'detection': 2,
        'symbol': 'S',
        'trait': 'ambush_master',  # 伏击大师：突袭加成翻倍
        'trait_name': '伏击大师',
        'trait_desc': '突袭时攻击加成翻倍(+60%)'
    },

    # ========== 摩托化类 (兵营生产, 2级起) ==========
    'motorcycle': {
        'name': '摩托兵',
        'category': 'motorized',
        'required_level': 2,
        'cost': 15,
        'pop_cost': 1,
        'attack': 12,
        'defense': 8,
        'speed': 5,
        'production_time': 0,
        'stealth': 0,
        'detection': 1,
        'symbol': 'M',
        'trait': 'retreat',  # 撤退：战败时有50%几率逃跑
        'trait_name': '撤退',
        'trait_desc': '战败时50%几率逃脱(保留1k单位)'
    },
    'motorized_infantry': {
        'name': '摩托化步兵',
        'category': 'motorized',
        'required_level': 2,
        'cost': 25,
        'pop_cost': 1,
        'attack': 16,
        'defense': 14,
        'speed': 4,
        'production_time': 0,
        'stealth': 0,
        'detection': 1,
        'symbol': 'O',
        'trait': 'support',  # 协同：同格有友军时攻防+15%
        'trait_name': '协同',
        'trait_desc': '同格有其他友军时攻防+15%'
    },
    'mechanized_infantry': {
        'name': '机械化步兵',
        'category': 'motorized',
        'required_level': 3,
        'cost': 40,
        'pop_cost': 1,
        'attack': 22,
        'defense': 20,
        'speed': 3,
        'production_time': 1,
        'stealth': 0,
        'detection': 1,
        'symbol': 'Z',
        'trait': 'armored',  # 装甲防护：受到炮兵伤害-30%
        'trait_name': '装甲防护',
        'trait_desc': '受到炮兵类单位伤害-30%'
    },

    # ========== 炮兵类 (兵工厂生产, 2级起) ==========
    'armored_car': {
        'name': '装甲车',
        'category': 'artillery',
        'required_level': 2,
        'cost': 30,
        'pop_cost': 1,
        'attack': 15,
        'defense': 18,
        'speed': 3,
        'production_time': 1,
        'stealth': 0,
        'detection': 2,
        'symbol': 'R',
        'trait': 'recon_support',  # 侦察支援：额外+2侦察范围
        'trait_name': '侦察支援',
        'trait_desc': '提供额外+2侦察范围'
    },
    'self_propelled_gun': {
        'name': '自行火炮',
        'category': 'artillery',
        'required_level': 3,
        'cost': 60,
        'pop_cost': 1,
        'attack': 35,
        'defense': 10,
        'speed': 2,
        'production_time': 2,
        'stealth': 0,
        'detection': 0,
        'symbol': 'G',
        'trait': 'suppress',  # 压制：攻击时敌方防御-20%
        'trait_name': '压制',
        'trait_desc': '攻击时敌方防御-20%'
    },
    'rocket_artillery': {
        'name': '火箭炮',
        'category': 'artillery',
        'required_level': 4,
        'cost': 100,
        'pop_cost': 1,
        'attack': 50,
        'defense': 5,
        'speed': 1,
        'production_time': 3,
        'stealth': 0,
        'detection': 0,
        'symbol': 'K',
        'trait': 'barrage',  # 齐射：对大规模敌军(>5k)伤害+25%
        'trait_name': '齐射',
        'trait_desc': '攻击规模>5k的敌军时伤害+25%'
    },

    # ========== 坦克类 (兵工厂生产, 2级起) ==========
    'light_tank': {
        'name': '轻型坦克',
        'category': 'tank',
        'required_level': 2,
        'cost': 50,
        'pop_cost': 1,
        'attack': 25,
        'defense': 20,
        'speed': 3,
        'production_time': 2,
        'stealth': 0,
        'detection': 1,
        'symbol': 'L',
        'trait': 'breakthrough',  # 突破：攻击防线时无视30%防御加成
        'trait_name': '突破',
        'trait_desc': '攻击防线时无视30%防御加成'
    },
    'medium_tank': {
        'name': '中型坦克',
        'category': 'tank',
        'required_level': 4,
        'cost': 80,
        'pop_cost': 1,
        'attack': 40,
        'defense': 35,
        'speed': 2,
        'production_time': 3,
        'stealth': 0,
        'detection': 0,
        'symbol': 'D',
        'trait': 'versatile',  # 全能：地形惩罚减半
        'trait_name': '全能',
        'trait_desc': '所有地形惩罚减半'
    },
    'heavy_tank': {
        'name': '重型坦克',
        'category': 'tank',
        'required_level': 5,
        'cost': 150,
        'pop_cost': 2,
        'attack': 60,
        'defense': 50,
        'speed': 1,
        'production_time': 4,
        'stealth': 0,
        'detection': 0,
        'symbol': 'H',
        'trait': 'crush',  # 碾压：对步兵类伤害+30%
        'trait_name': '碾压',
        'trait_desc': '对步兵类单位伤害+30%'
    }
}

# 玩家颜色/标识
PLAYER_SYMBOLS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
PLAYER_COLORS = [
    '\033[91m',  # 红
    '\033[94m',  # 蓝
    '\033[92m',  # 绿
    '\033[93m',  # 黄
    '\033[95m',  # 紫
    '\033[96m',  # 青
    '\033[97m',  # 白
    '\033[90m',  # 灰
]
COLOR_RESET = '\033[0m'

# 显示符号
SYMBOL_CAPITAL = '*'   # 首都
SYMBOL_ARMY = 'o'      # 军队
SYMBOL_SELECTED = '@'  # 选中的单位


def get_units_by_category(category: str) -> dict:
    """获取某类别的所有单位"""
    return {k: v for k, v in UNITS.items() if v['category'] == category}


def get_production_building(unit_type: str) -> str:
    """获取单位的生产建筑类型"""
    category = UNITS[unit_type]['category']
    return UNIT_PRODUCTION_SOURCE.get(category, 'barracks')


# ==================== 国策系统 ====================

# 国策分类
FOCUS_CATEGORIES = {
    'economy': '经济发展',
    'population': '人口政策',
    'military': '军事改革',
    'technology': '科技研发'
}

# 国策树配置
# cost: 经济花费, time: 研究回合数, prerequisites: 前置国策, effects: 完成后效果
FOCUS_TREE = {
    # ========== 经济发展 ==========
    'basic_industry': {
        'name': '基础工业',
        'category': 'economy',
        'cost': 100,
        'time': 2,
        'prerequisites': [],
        'effects': {'economy_bonus': 0.1},  # 经济收入+10%
        'description': '发展基础工业体系'
    },
    'industrial_expansion': {
        'name': '工业扩张',
        'category': 'economy',
        'cost': 200,
        'time': 3,
        'prerequisites': ['basic_industry'],
        'effects': {'economy_bonus': 0.15, 'building_cost_reduction': -0.1},
        'description': '扩大工业规模，降低建筑成本'
    },
    'heavy_industry': {
        'name': '重工业',
        'category': 'economy',
        'cost': 400,
        'time': 4,
        'prerequisites': ['industrial_expansion'],
        'effects': {'economy_bonus': 0.2, 'production_speed': 0.2},
        'description': '发展重工业，加快生产速度'
    },
    'free_trade': {
        'name': '自由贸易',
        'category': 'economy',
        'cost': 150,
        'time': 2,
        'prerequisites': ['basic_industry'],
        'effects': {'economy_bonus': 0.2},
        'description': '开放贸易，增加经济收入'
    },
    'war_economy': {
        'name': '战时经济',
        'category': 'economy',
        'cost': 300,
        'time': 3,
        'prerequisites': ['heavy_industry', 'free_trade'],
        'effects': {'economy_bonus': 0.25, 'unit_cost_reduction': -0.15},
        'description': '全面转向战时经济体制'
    },

    # ========== 人口政策 ==========
    'population_growth': {
        'name': '鼓励生育',
        'category': 'population',
        'cost': 80,
        'time': 2,
        'prerequisites': [],
        'effects': {'pop_growth_bonus': 0.02},  # 人口增长+2%
        'description': '鼓励国民生育'
    },
    'immigration_policy': {
        'name': '移民政策',
        'category': 'population',
        'cost': 150,
        'time': 2,
        'prerequisites': ['population_growth'],
        'effects': {'pop_growth_bonus': 0.02, 'pop_cap_bonus': 50},
        'description': '吸引外来移民'
    },
    'baby_boom': {
        'name': '婴儿潮',
        'category': 'population',
        'cost': 250,
        'time': 3,
        'prerequisites': ['immigration_policy'],
        'effects': {'pop_growth_bonus': 0.03, 'pop_cap_bonus': 100},
        'description': '迎来人口爆发式增长'
    },
    'education_reform': {
        'name': '教育改革',
        'category': 'population',
        'cost': 120,
        'time': 2,
        'prerequisites': ['population_growth'],
        'effects': {'pop_cap_bonus': 30},
        'description': '提升国民素质'
    },
    'university_system': {
        'name': '大学体系',
        'category': 'population',
        'cost': 200,
        'time': 3,
        'prerequisites': ['education_reform'],
        'effects': {'pop_cap_bonus': 50},
        'description': '建立完善的高等教育体系'
    },

    # ========== 军事改革 ==========
    'basic_training': {
        'name': '基础训练',
        'category': 'military',
        'cost': 100,
        'time': 2,
        'prerequisites': [],
        'effects': {'attack_bonus': 0.05, 'defense_bonus': 0.05},
        'description': '加强军队基础训练'
    },
    'combat_experience': {
        'name': '实战经验',
        'category': 'military',
        'cost': 180,
        'time': 3,
        'prerequisites': ['basic_training'],
        'effects': {'attack_bonus': 0.1},
        'description': '通过实战提升战斗力'
    },
    'elite_forces': {
        'name': '精锐部队',
        'category': 'military',
        'cost': 300,
        'time': 4,
        'prerequisites': ['combat_experience'],
        'effects': {'attack_bonus': 0.15, 'defense_bonus': 0.1},
        'description': '培养精锐作战部队'
    },
    'armor_doctrine': {
        'name': '装甲学说',
        'category': 'military',
        'cost': 200,
        'time': 3,
        'prerequisites': ['basic_training'],
        'effects': {'attack_bonus': 0.1},
        'description': '发展装甲作战理论'
    },
    'mechanized_warfare': {
        'name': '机械化战争',
        'category': 'military',
        'cost': 350,
        'time': 4,
        'prerequisites': ['armor_doctrine', 'combat_experience'],
        'effects': {'attack_bonus': 0.2, 'production_speed': 0.1},
        'description': '全面机械化改革'
    },
    'total_war': {
        'name': '全面战争',
        'category': 'military',
        'cost': 500,
        'time': 5,
        'prerequisites': ['elite_forces', 'mechanized_warfare'],
        'effects': {'attack_bonus': 0.25, 'defense_bonus': 0.15},
        'description': '动员全国进行全面战争'
    },

    # ========== 科技研发 ==========
    'research_labs': {
        'name': '研究实验室',
        'category': 'technology',
        'cost': 150,
        'time': 2,
        'prerequisites': [],
        'effects': {},
        'description': '建立基础研究设施'
    },
    'advanced_research': {
        'name': '高级研究',
        'category': 'technology',
        'cost': 250,
        'time': 3,
        'prerequisites': ['research_labs'],
        'effects': {'production_speed': 0.1},
        'description': '进行更深入的科技研究'
    },
    'secret_projects': {
        'name': '秘密计划',
        'category': 'technology',
        'cost': 400,
        'time': 4,
        'prerequisites': ['advanced_research'],
        'effects': {},
        'description': '启动绝密军事研究项目'
    },
    'nuclear_program': {
        'name': '核计划',
        'category': 'technology',
        'cost': 300,
        'time': 3,
        'prerequisites': ['research_labs'],
        'effects': {},
        'description': '启动核能研究计划'
    },
    'nuclear_research': {
        'name': '核武研究',
        'category': 'technology',
        'cost': 500,
        'time': 5,
        'prerequisites': ['nuclear_program', 'secret_projects'],
        'effects': {},
        'description': '进行核武器理论研究'
    },
    'nuclear_weapons': {
        'name': '核武器',
        'category': 'technology',
        'cost': 1000,
        'time': 6,
        'prerequisites': ['nuclear_research'],
        'effects': {'nuclear_capability': 1},
        'description': '研发核武器技术，解锁核发射井'
    },
    'nuclear_silo': {
        'name': '核发射井',
        'category': 'technology',
        'cost': 500,
        'time': 3,
        'prerequisites': ['nuclear_weapons'],
        'effects': {'can_build_silo': 1},
        'description': '可建造核发射井（固定）'
    },
    'mobile_launch_platform': {
        'name': '移动发射平台',
        'category': 'technology',
        'cost': 800,
        'time': 4,
        'prerequisites': ['nuclear_silo'],
        'effects': {'can_build_mobile_launcher': 1},
        'description': '可建造移动核发射平台'
    },
    'nuclear_interception': {
        'name': '核拦截',
        'category': 'technology',
        'cost': 600,
        'time': 4,
        'prerequisites': ['nuclear_weapons'],
        'effects': {'can_build_interceptor': 1},
        'description': '可建造核拦截平台'
    }
}

# 核武器配置
NUKE_MISSILE_COST = 750  # 每枚核弹的经济消耗
NUKE_DAMAGE = 9999  # 核弹伤害（足以消灭任何单位）
NUKE_RADIUS = 1  # 核弹爆炸半径（1表示3x3范围）
NUKE_BUILDING_DESTROY = True  # 核弹是否摧毁建筑
NUKE_CAPITAL_DESTROY = True  # 核弹是否可以摧毁首都（消灭玩家）
INTERCEPTOR_RANGE = 2  # 拦截范围（2表示5x5范围）
INTERCEPTOR_COOLDOWN = 3  # 拦截后冷却回合数

# ==================== 铁路系统配置 ====================
# 可连接铁路的建筑类型
RAILWAY_CONNECTABLE_BUILDINGS = ['city', 'factory', 'barracks', 'arms_factory', 'train_station']
# 铁路移动速度倍数
RAILWAY_SPEED_MULTIPLIER = 3
# 可使用铁路快速移动的单位类别
RAILWAY_USABLE_CATEGORIES = ['infantry', 'motorized', 'artillery', 'tank']
# 铁路显示符号
RAILWAY_SYMBOL_H = '-'  # 水平铁路
RAILWAY_SYMBOL_V = '|'  # 垂直铁路
RAILWAY_SYMBOL_CROSS = '+'  # 交叉点
# 火车符号
TRAIN_SYMBOL = '>'

# ==================== 领土加成配置 ====================
# 每N格领土增加的人口增长率
TERRITORY_POP_GROWTH_BONUS = 0.0005  # 每格+0.05%
# 每N格领土增加的人口上限
TERRITORY_POP_CAP_BONUS = 0.5  # 每格+0.5k人口上限
# 领土加成生效的最小格数（超过此值才开始加成）
TERRITORY_BONUS_THRESHOLD = 50
