# -*- coding: utf-8 -*-
"""战斗系统"""

import random
from typing import Tuple, List
from units import Unit
from config import (
    TERRAIN_RIVER, RIVER_DEFENSE_BONUS, RIVER_ATTACK_PENALTY,
    ENCOUNTER_BATTLE_PENALTY, AMBUSH_ATTACK_BONUS, AMBUSH_DEFENSE_PENALTY
)


def apply_trait_modifiers(attacker: Unit, defender: Unit, defender_terrain: str,
                          attacker_crossing_river: bool, battle_type: str,
                          fortification_bonus: float, attacker_allies: int = 0,
                          defender_allies: int = 0) -> dict:
    """
    应用词条效果，返回修正后的攻防数值和战斗信息
    """
    attack_power = attacker.attack
    defense_power = defender.defense
    trait_effects = []

    # ===== 攻击方词条 =====

    # veteran (老练): 攻防+10%
    if attacker.trait == 'veteran':
        attack_power = int(attack_power * 1.1)
        trait_effects.append('老练+10%攻')

    # ambush_master (伏击大师): 突袭加成翻倍
    if attacker.trait == 'ambush_master' and battle_type == 'ambush_attacker':
        # 基础突袭已经是+30%，翻倍变成+60%，额外再加30%
        attack_power = int(attack_power * 1.3)  # 额外30%
        trait_effects.append('伏击大师+30%')

    # support (协同): 同格有友军时攻防+15%
    if attacker.trait == 'support' and attacker_allies > 0:
        attack_power = int(attack_power * 1.15)
        trait_effects.append('协同+15%攻')

    # suppress (压制): 敌方防御-20%
    if attacker.trait == 'suppress':
        defense_power = int(defense_power * 0.8)
        trait_effects.append('压制-20%防')

    # barrage (齐射): 对大规模敌军(>5k)伤害+25%
    if attacker.trait == 'barrage' and defender.count > 5:
        attack_power = int(attack_power * 1.25)
        trait_effects.append('齐射+25%')

    # breakthrough (突破): 攻击防线时无视30%防御加成
    if attacker.trait == 'breakthrough' and fortification_bonus > 1.0:
        # 减少防线效果的30%
        reduced_bonus = 1.0 + (fortification_bonus - 1.0) * 0.7
        defense_power = int(defender.defense * reduced_bonus)
        trait_effects.append('突破-30%防线')

    # versatile (全能): 地形惩罚减半
    versatile_river_penalty = RIVER_ATTACK_PENALTY
    if attacker.trait == 'versatile':
        versatile_river_penalty = (1.0 + RIVER_ATTACK_PENALTY) / 2  # 0.75 instead of 0.5
        if attacker_crossing_river:
            trait_effects.append('全能减半惩罚')

    # crush (碾压): 对步兵类伤害+30%
    if attacker.trait == 'crush' and defender.category == 'infantry':
        attack_power = int(attack_power * 1.3)
        trait_effects.append('碾压+30%')

    # ===== 防守方词条 =====

    # fortify (坚守): 未移动时防御+20%
    if defender.trait == 'fortify' and not defender.has_moved_this_turn():
        defense_power = int(defense_power * 1.2)
        trait_effects.append('坚守+20%防')

    # veteran (老练): 攻防+10%
    if defender.trait == 'veteran':
        defense_power = int(defense_power * 1.1)
        trait_effects.append('敌老练+10%防')

    # support (协同): 同格有友军时攻防+15%
    if defender.trait == 'support' and defender_allies > 0:
        defense_power = int(defense_power * 1.15)
        trait_effects.append('敌协同+15%防')

    # armored (装甲防护): 受炮兵伤害-30%
    armored_reduction = 1.0
    if defender.trait == 'armored' and attacker.category == 'artillery':
        armored_reduction = 0.7
        trait_effects.append('装甲防护-30%伤害')

    return {
        'attack_power': attack_power,
        'defense_power': defense_power,
        'versatile_penalty': versatile_river_penalty,
        'armored_reduction': armored_reduction,
        'trait_effects': trait_effects
    }


def calculate_combat(attacker: Unit, defender: Unit, defender_terrain: str,
                     attacker_crossing_river: bool = False,
                     battle_type: str = 'normal',
                     fortification_bonus: float = 1.0,
                     attacker_allies: int = 0,
                     defender_allies: int = 0) -> Tuple[int, int, List[str]]:
    """
    计算战斗结果
    返回: (攻击方损失, 防守方损失, 词条效果列表)
    battle_type: 'normal' | 'encounter' | 'ambush_attacker' | 'ambush_defender'
    fortification_bonus: 防线防御加成倍数
    """
    # 先应用词条效果
    modifiers = apply_trait_modifiers(
        attacker, defender, defender_terrain, attacker_crossing_river,
        battle_type, fortification_bonus, attacker_allies, defender_allies
    )

    attack_power = modifiers['attack_power']
    defense_power = modifiers['defense_power']
    trait_effects = modifiers['trait_effects']

    # 渡河攻击惩罚（全能词条减半）
    if attacker_crossing_river:
        attack_power = int(attack_power * modifiers['versatile_penalty'])

    # 地形加成（防守方在河流上）
    if defender_terrain == TERRAIN_RIVER:
        defense_power = int(defense_power * RIVER_DEFENSE_BONUS)

    # 防线加成（如果没有被breakthrough词条处理）
    if fortification_bonus > 1.0 and attacker.trait != 'breakthrough':
        defense_power = int(defense_power * fortification_bonus)

    # 遭遇战/突袭修正
    if battle_type == 'encounter':
        attack_power = int(attack_power * ENCOUNTER_BATTLE_PENALTY)
        defense_power = int(defense_power * ENCOUNTER_BATTLE_PENALTY)
    elif battle_type == 'ambush_attacker':
        attack_power = int(attack_power * AMBUSH_ATTACK_BONUS)
        defense_power = int(defense_power * AMBUSH_DEFENSE_PENALTY)
    elif battle_type == 'ambush_defender':
        attack_power = int(attack_power * AMBUSH_DEFENSE_PENALTY)
        defense_power = int(defense_power * AMBUSH_ATTACK_BONUS)

    # 随机因素 (±20%)
    attack_roll = random.uniform(0.8, 1.2)
    defense_roll = random.uniform(0.8, 1.2)

    actual_attack = int(attack_power * attack_roll)
    actual_defense = int(defense_power * defense_roll)

    # 计算伤害
    damage_to_defender = max(1, actual_attack - actual_defense // 2)
    damage_to_attacker = max(1, actual_defense - actual_attack // 2)

    # 应用装甲防护词条
    if modifiers['armored_reduction'] < 1.0:
        damage_to_defender = int(damage_to_defender * modifiers['armored_reduction'])

    return damage_to_attacker, damage_to_defender, trait_effects


def resolve_combat(attacker: Unit, defender: Unit, defender_terrain: str,
                   attacker_crossing_river: bool = False,
                   battle_type: str = 'normal',
                   fortification_bonus: float = 1.0,
                   attacker_allies: int = 0,
                   defender_allies: int = 0) -> dict:
    """
    执行战斗并返回结果
    """
    initial_attacker_count = attacker.count
    initial_defender_count = defender.count

    attacker_damage, defender_damage, trait_effects = calculate_combat(
        attacker, defender, defender_terrain, attacker_crossing_river,
        battle_type, fortification_bonus, attacker_allies, defender_allies
    )

    attacker.take_damage(attacker_damage)
    defender.take_damage(defender_damage)

    # 撤退词条：战败时50%几率逃脱
    retreat_triggered = False
    if attacker.trait == 'retreat' and not attacker.is_alive():
        if random.random() < 0.5:
            attacker.count = 1  # 保留1k单位
            retreat_triggered = True
            trait_effects.append('撤退成功')

    # 袭扰词条：攻击后保留1点移动力
    raid_triggered = False
    if attacker.trait == 'raid' and attacker.is_alive():
        if attacker.remaining_moves < 1:
            attacker.remaining_moves = 1
            raid_triggered = True
            trait_effects.append('袭扰+1移动')

    result = {
        'attacker_id': attacker.id,
        'defender_id': defender.id,
        'attacker_losses': initial_attacker_count - attacker.count,
        'defender_losses': initial_defender_count - defender.count,
        'attacker_survived': attacker.is_alive(),
        'defender_survived': defender.is_alive(),
        'attacker_remaining': attacker.count,
        'defender_remaining': defender.count,
        'crossing_river': attacker_crossing_river,
        'battle_type': battle_type,
        'fortification_bonus': fortification_bonus,
        'trait_effects': trait_effects,
        'retreat_triggered': retreat_triggered,
        'raid_triggered': raid_triggered
    }

    return result


def calculate_battle_preview(attacker: Unit, defender: Unit, defender_terrain: str,
                             attacker_crossing_river: bool = False,
                             battle_type: str = 'normal',
                             fortification_bonus: float = 1.0) -> dict:
    """
    预览战斗结果（不实际执行）
    """
    attack_power = attacker.attack
    defense_power = defender.defense

    penalties = []

    if attacker_crossing_river:
        attack_power = int(attack_power * RIVER_ATTACK_PENALTY)
        penalties.append('渡河攻击-50%')

    if defender_terrain == TERRAIN_RIVER:
        defense_power = int(defense_power * RIVER_DEFENSE_BONUS)
        penalties.append('河流防御+50%')

    if fortification_bonus > 1.0:
        defense_power = int(defense_power * fortification_bonus)
        bonus_pct = int((fortification_bonus - 1) * 100)
        penalties.append(f'防线+{bonus_pct}%')

    if battle_type == 'encounter':
        attack_power = int(attack_power * ENCOUNTER_BATTLE_PENALTY)
        defense_power = int(defense_power * ENCOUNTER_BATTLE_PENALTY)
        penalties.append('遭遇战-30%')
    elif battle_type == 'ambush_attacker':
        attack_power = int(attack_power * AMBUSH_ATTACK_BONUS)
        defense_power = int(defense_power * AMBUSH_DEFENSE_PENALTY)
        penalties.append('突袭+30%/-30%')
    elif battle_type == 'ambush_defender':
        attack_power = int(attack_power * AMBUSH_DEFENSE_PENALTY)
        defense_power = int(defense_power * AMBUSH_ATTACK_BONUS)
        penalties.append('被伏击-30%/+30%')

    # 显示词条效果预览
    if attacker.trait_name:
        penalties.append(f'[{attacker.trait_name}]')

    # 估算平均伤害
    avg_damage_to_defender = max(1, attack_power - defense_power // 2)
    avg_damage_to_attacker = max(1, defense_power - attack_power // 2)

    est_attacker_losses = avg_damage_to_attacker // 10
    est_defender_losses = avg_damage_to_defender // 10

    return {
        'attacker_strength': attack_power,
        'defender_strength': defense_power,
        'terrain_effects': ', '.join(penalties) if penalties else '无',
        'estimated_attacker_losses': f"{est_attacker_losses}k",
        'estimated_defender_losses': f"{est_defender_losses}k",
        'win_chance': '高' if attack_power > defense_power * 1.5 else ('中' if attack_power > defense_power else '低')
    }


def merge_units_at_location(units: List[Unit], x: int, y: int, owner_id: int) -> List[Unit]:
    """
    合并同一位置的同类型单位
    """
    type_groups = {}
    other_units = []

    for unit in units:
        if unit.x == x and unit.y == y and unit.owner_id == owner_id:
            if unit.unit_type not in type_groups:
                type_groups[unit.unit_type] = []
            type_groups[unit.unit_type].append(unit)
        else:
            other_units.append(unit)

    merged = []
    for unit_type, group in type_groups.items():
        if len(group) == 1:
            merged.append(group[0])
        else:
            main_unit = group[0]
            for other in group[1:]:
                main_unit.merge_with(other)
            merged.append(main_unit)

    return other_units + merged
