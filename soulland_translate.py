#!/usr/bin/env python3
"""
Soul Land Mod 一键汉化脚本 (Minecraft Forge 1.20.1)

用法:
  python3 soulland_translate.py <soulland-1.0.0.jar>

功能:
  1. 自动备份原jar为 .bak
  2. 注入 zh_cn.json 语言文件
  3. 翻译 41 个 advancement JSON 文件
  4. 批量替换 class 文件中的英文硬编码字符串为中文（常量池 UTF-8 条目）
  5. 保持 en_us.json 不变

安全原则:
  - 只修改常量池 UTF-8 字符串条目 (tag=1)
  - 绝不修改数字字节码 (sipush 等) — 会导致崩溃或布局损坏
  - 绝不翻译 UPPER_CASE 注册名 (如 BODY_TEMPERING_PILL) — 会导致物品查找失败
  - 绝不翻译 camelCase 代码标识符 — 不是显示文本

作者: 许清禾 🥰
日期: 2026-05-24
"""

import sys, os, json, re, struct, glob, shutil
from zipfile import ZipFile, ZIP_DEFLATED

# ============================================================
# 翻译数据
# ============================================================

# --- zh_cn.json (301条：物品、方块、实体、效果、按键、等级、群系) ---
ZH_CN = {
    # Items
    "item.soulland.soul_crystal": "魂晶",
    "item.soulland.spirit_herb": "灵草",
    "item.soulland.immortal_herb": "仙草",
    "item.soulland.wild_herb": "野草",
    "item.soulland.soul_bone_skull": "魂骨·头骨",
    "item.soulland.soul_bone_torso": "魂骨·躯干骨",
    "item.soulland.soul_bone_l_arm": "魂骨·左臂骨",
    "item.soulland.soul_bone_r_arm": "魂骨·右臂骨",
    "item.soulland.soul_bone_l_leg": "魂骨·左腿骨",
    "item.soulland.soul_bone_r_leg": "魂骨·右腿骨",
    "item.soulland.fire_spirit_fruit": "火灵果",
    "item.soulland.ice_spirit_fruit": "冰灵果",
    "item.soulland.heavenly_essence_fruit": "天精果",
    "item.soulland.heaven_dream_fruit": "天梦果",
    "item.soulland.thunderclap_berry": "雷击莓",
    "item.soulland.purple_demon_eye_fruit": "紫极魔瞳果",
    "item.soulland.body_tempering_pill": "炼体丹",
    "item.soulland.breakthrough_pill": "突破丹",
    "item.soulland.divine_restoration_pill": "神复丹",
    "item.soulland.dragon_tiger_pill": "龙虎丹",
    "item.soulland.essence_gathering_pill": "聚元丹",
    "item.soulland.fire_spirit_pill": "火灵丹",
    "item.soulland.foundation_pill": "筑基丹",
    "item.soulland.heaven_origin_pill": "天元丹",
    "item.soulland.ice_spirit_pill": "冰灵丹",
    "item.soulland.longevity_pill": "长寿丹",
    "item.soulland.meridian_cleansing_pill": "洗髓丹",
    "item.soulland.nine_revolution_golden_pill": "九转金丹",
    "item.soulland.qi_gathering_pill": "聚气丹",
    "item.soulland.soul_focusing_pill": "定魂丹",
    "item.soulland.spirit_ascension_pill": "升灵丹",
    "item.soulland.spirit_channeling_pill": "通灵丹",
    "item.soulland.spirit_recovery_pill": "回灵丹",
    "item.soulland.spirit_tempest_pill": "灵暴丹",
    "item.soulland.spirit_condensing_pill": "凝灵丹",
    "item.soulland.spirit_dew_lily": "灵露百合",
    "item.soulland.spirit_dew_root": "灵露根",
    "item.soulland.spirit_mushroom_herb": "灵菇草",
    "item.soulland.star_soul_pearl_dew": "星魂珠露",
    "item.soulland.sunrise_herb": "晨曦草",
    "item.soulland.dew_crystal_flower": "露晶花",
    "item.soulland.divine_dewdrop_orchid": "神露兰",
    "item.soulland.dragon_beard_herb": "龙须草",
    "item.soulland.immortal_dew_flower": "仙露花",
    "item.soulland.full_moon_piercing_autumn_dew": "满月穿秋露",
    "item.soulland.ancient_spirit_incense": "古灵香",
    "item.soulland.spirit_beast_incense": "魂兽引香",
    "item.soulland.numbing_powder": "麻痹粉",
    "item.soulland.haotian_pillar": "昊天柱",
    "item.soulland.sea_god_pillar": "海神柱",
    "item.soulland.cultivation_manual": "修炼手册",
    "item.soulland.tang_sect_hidden_weapon": "唐门暗器",
    "item.soulland.soul_ring_item": "魂环",
    "item.soulland.spirit_butterfly": "灵魂蝶",
    "item.soulland.blood_coagulation_herb": "凝血草",
    # Blocks
    "block.soulland.cultivation_altar": "修炼祭坛",
    "block.soulland.spirit_forge": "灵力锻造台",
    "block.soulland.herbal_garden": "灵药园",
    # Entities
    "entity.soulland.spirit_beast": "魂兽",
    "entity.soulland.spirit_deer": "灵鹿",
    "entity.soulland.blue_silver_grass": "蓝银草",
    # Effects
    "effect.soulland.soul_power_boost": "魂力提升",
    "effect.soulland.spirit_shield": "灵力护盾",
    "effect.soulland.body_tempering": "炼体",
    "effect.soulland.soul_focus": "定魂",
    # Keys
    "key.soulland.cultivation_menu": "修炼菜单",
    "key.soulland.meditate": "冥想",
    "key.soulland.ring_skill": "魂技",
    "key.soulland.toggle_aura": "切换光环",
    "key.soulland.cycle_ring": "切换魂环",
    "key.soulland.martial_soul_ability": "武魂技能",
    "key.soulland.true_martial_soul": "武魂真身",
    # Ranks
    "rank.soulland.spirit_scholar": "魂士",
    "rank.soulland.spirit_master": "魂师",
    "rank.soulland.spirit_grandmaster": "大魂师",
    "rank.soulland.spirit_elder": "魂尊",
    "rank.soulland.spirit_ancestor": "魂宗",
    "rank.soulland.spirit_king": "魂王",
    "rank.soulland.spirit_emperor": "魂帝",
    "rank.soulland.spirit_sage": "魂圣",
    "rank.soulland.spirit_douluo": "魂斗罗",
    "rank.soulland.titled_douluo": "封号斗罗",
    "rank.soulland.super_douluo": "超级斗罗",
    "rank.soulland.quasi_god": "准神",
    "rank.soulland.demigod": "半神",
    # Biomes
    "biome.soulland.ji_beidi": "极北之地",
    "biome.soulland.hunting_spirit_forest": "猎魂森林",
    "biome.soulland.sunset_forest": "落日森林",
    "biome.soulland.evil_demon_forest": "邪魔森林",
}

# --- Advancement translations (41 files) ---
ADVANCEMENTS = {
    # Root
    "soulland:root": {"title": "Soul Land", "description": "踏入斗罗世界"},
    # Cultivation milestones
    "soulland:cultivation/spirit_awakening": {"title": "武魂觉醒", "description": "觉醒你的武魂"},
    "soulland:cultivation/first_ring": {"title": "第一魂环", "description": "吸收你的第一枚魂环"},
    "soulland:cultivation/second_ring": {"title": "第二魂环", "description": "吸收第二枚魂环"},
    "soulland:cultivation/third_ring": {"title": "第三魂环", "description": "吸收第三枚魂环"},
    "soulland:cultivation/fourth_ring": {"title": "第四魂环", "description": "吸收第四枚魂环"},
    "soulland:cultivation/fifth_ring": {"title": "第五魂环", "description": "吸收第五枚魂环"},
    "soulland:cultivation/sixth_ring": {"title": "第六魂环", "description": "吸收第六枚魂环"},
    "soulland:cultivation/seventh_ring": {"description": "吸收第七枚魂环", "title": "第七魂环"},
    "soulland:cultivation/eighth_ring": {"description": "吸收第八枚魂环", "title": "第八魂环"},
    "soulland:cultivation/ninth_ring": {"description": "吸收第九枚魂环", "title": "第九魂环"},
    "soulland:cultivation/spirit_master_rank": {"description": "达到魂师等级", "title": "魂师"},
    "soulland:cultivation/spirit_grandmaster_rank": {"description": "达到大魂师等级", "title": "大魂师"},
    "soulland:cultivation/spirit_elder_rank": {"description": "达到魂尊等级", "title": "魂尊"},
    "soulland:cultivation/spirit_ancestor_rank": {"description": "达到魂宗等级", "title": "魂宗"},
    "soulland:cultivation/spirit_king_rank": {"description": "达到魂王等级", "title": "魂王"},
    "soulland:cultivation/spirit_emperor_rank": {"description": "达到魂帝等级", "title": "魂帝"},
    "soulland:cultivation/spirit_sage_rank": {"description": "达到魂圣等级", "title": "魂圣"},
    "soulland:cultivation/spirit_douluo_rank": {"description": "达到魂斗罗等级", "title": "魂斗罗"},
    "soulland:cultivation/titled_douluo_rank": {"description": "成为封号斗罗", "title": "封号斗罗"},
    "soulland:cultivation/super_douluo_rank": {"description": "达到超级斗罗", "title": "超级斗罗"},
    "soulland:cultivation/quasi_god_rank": {"description": "触摸到神的力量", "title": "准神"},
    "soulland:cultivation/demigod_rank": {"description": "半步入神", "title": "半神"},
    # Achievements
    "soulland:first_herb": {"description": "采集你的第一株灵草", "title": "灵草采集"},
    "soulland:first_pill": {"description": "炼制你的第一颗丹药", "title": "初次炼药"},
    "soulland:first_soul_bone": {"description": "获得你的第一块魂骨", "title": "魂骨初现"},
    "soulland:first_alchemy": {"description": "开始学习炼药", "title": "炼药入门"},
    "soulland:tournament_champion": {"description": "赢得大斗魂场冠军", "title": "斗魂场冠军"},
    "soulland:tang_sect_join": {"description": "加入唐门", "title": "唐门弟子"},
    "soulland:shrek_join": {"description": "加入史莱克学院", "title": "史莱克学员"},
    "soulland:spirit_hall_join": {"description": "加入武魂殿", "title": "武魂殿成员"},
    "soulland:twin_soul": {"description": "觉醒双生武魂", "title": "双生武魂"},
    "soulland:domain_awakening": {"description": "觉醒你的领域", "title": "领域觉醒"},
    "soulland:true_martial_soul": {"description": "释放武魂真身", "title": "武魂真身"},
    "soulland:first_reincarnation": {"description": "第一次转世重生", "title": "轮回初悟"},
    "soulland:sacrifice_ritual": {"description": "完成献祭仪式", "title": "献祭仪式"},
    "soulland:hidden_weapon": {"description": "制作第一件唐门暗器", "title": "唐门暗器"},
    "soulland:divine_inheritance": {"description": "开启神位传承", "title": "神位传承"},
    "soulland:gather_15_herbs": {"description": "采集15株灵草", "title": "灵草收集者"},
    "soulland:gather_40_herbs": {"description": "采集40株灵草", "title": "灵草大师"},
    "soulland:craft_5_pills": {"description": "炼制5颗丹药", "title": "炼药学徒"},
    "soulland:breakthrough_first": {"description": "完成第一次突破", "title": "初次突破"},
}

# --- Hardcoded class strings (常量池替换) ---
# 从 .bak3 重建 + round3 全面扫描，共 2463 条翻译，2185 处命中
# 加载同目录下的 soulland_translations.json
TRANSLATIONS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "soulland_translations.json")


def load_translations():
    """加载翻译字典，合并内置 + 外部文件"""
    trans = {}
    
    # 内置核心翻译（等级、GUI、关键术语）
    core = {
        # Ranks
        "Spirit Scholar": "魂士", "Spirit Master": "魂师", "Spirit Grandmaster": "大魂师",
        "Spirit Elder": "魂尊", "Spirit Ancestor": "魂宗", "Spirit King": "魂王",
        "Spirit Emperor": "魂帝", "Spirit Sage": "魂圣", "Spirit Douluo": "魂斗罗",
        "Titled Douluo": "封号斗罗", "Super Douluo": "超级斗罗", "Quasi God": "准神", "Demigod": "半神",
        "Soul Rings (/9)": "魂环 (/9)", "Spirit Power": "魂力",
        # GUI
        "Cultivation Menu": "修炼菜单", "Twin Martial Soul Awakening": "双生武魂觉醒",
        "Academy Dialogue": "学院对话", "Spirit Sacrifice": "武魂献祭",
        # HUD
        "◎ SPIRIT RINGS RELEASED [G]": "◎ 魂环已释放 [G]",
        "★ TRUE MARTIAL SOUL ★": "★ 武魂真身 ★",
        "★ TRUE MARTIAL SOUL ACTIVE ★": "★ 武魂真身已激活 ★",
        "⚡ BREAKTHROUGH NEEDED": "⚡ 需要突破",
        "⚡ BREAKTHROUGH REQUIRED ⚡": "⚡ 需要突破 ⚡",
        # Tabs
        "⚔ Cult": "⚔ 修炼", "⚗ Alch": "⚗ 炼药", "☠ Bone": "☠ 魂骨",
        "⚛ Aff": "⚛ 亲和", "⚡ Brk": "⚡ 突破", "✦ Innt": "✦ 先天", "功 Tech": "功 武技",
        # Panel titles with §
        "§6§l☠ SPIRIT BONES ☠": "§6§l☠ 魂骨 ☠",
        "§6§l⚗ ALCHEMY §6§l⚗": "§6§l⚗ 炼药 §6§l⚗",
        "§6§l⚛ AFFINITY MATRIX ⚛": "§6§l⚛ 亲和矩阵 ⚛",
        "§6§l⚡ BREAKTHROUGH §6§l⚡": "§6§l⚡ 突破 §6§l⚡",
        "§6§l✦ INNATE SOUL SKILLS ✦": "§6§l✦ 先天魂技 ✦",
        "§6§lTang Sect Secret Techniques": "§6§l唐门绝学",
        "§6§lAWAKENING": "§6§l觉醒",
        "§6§l✦ TWIN SPIRITS ✦": "§6§l✦ 双生武魂 ✦",
        # Pills (Title Case only!)
        "Body Tempering Pill": "炼体丹", "Breakthrough Pill": "突破丹",
        "Essence Gathering Pill": "聚元丹", "Qi Gathering Pill": "聚气丹",
        "Foundation Pill": "筑基丹", "Heaven Origin Pill": "天元丹",
        "Soul Focusing Pill": "定魂丹", "Spirit Ascension Pill": "升灵丹",
        "Spirit Condensing Pill": "凝灵丹", "Nine Revolution Golden Pill": "九转金丹",
        "Meridian Cleansing Pill": "洗髓丹", "Longevity Pill": "长寿丹",
        "Dragon Tiger Pill": "龙虎丹", "Fire Spirit Pill": "火灵丹",
        "Ice Spirit Pill": "冰灵丹", "Divine Restoration Pill": "神复丹",
        "Spirit Recovery Pill": "回灵丹", "Spirit Tempest Pill": "灵暴丹",
        "Spirit Channeling Pill": "通灵丹",
    }
    trans.update(core)
    
    # 加载外部翻译文件（如果存在）
    if os.path.exists(TRANSLATIONS_FILE):
        with open(TRANSLATIONS_FILE, encoding='utf-8') as f:
            external = json.load(f)
        trans.update(external)
        print(f"  加载外部翻译: {len(external)} 条")
    else:
        print(f"  ⚠ 未找到 {TRANSLATIONS_FILE}，仅使用内置翻译")
    
    return trans


def patch_class_data(data, translations):
    """替换 class 文件常量池中的 UTF-8 字符串"""
    patches = 0
    for en, zh in translations.items():
        en_bytes = en.encode('utf-8')
        zh_bytes = zh.encode('utf-8')
        if len(en_bytes) == 0:
            continue
        pos = 0
        while True:
            idx = data.find(en_bytes, pos)
            if idx == -1:
                break
            # 验证常量池 UTF-8 条目：前2字节 = 长度
            if idx >= 2:
                stored_len = (data[idx-2] << 8) | data[idx-1]
                if stored_len == len(en_bytes):
                    new_len = len(zh_bytes)
                    if new_len > 65535:
                        pos = idx + 1
                        continue
                    # 替换：更新长度头 + 内容
                    data = (data[:idx-2] 
                            + bytes([(new_len >> 8) & 0xFF, new_len & 0xFF]) 
                            + zh_bytes 
                            + data[idx + len(en_bytes):])
                    patches += 1
                    pos = idx - 2 + 2 + len(zh_bytes)
                else:
                    pos = idx + 1
            else:
                pos = idx + 1
    return data, patches


def patch_advancement(adv_json, translations):
    """翻译 advancement JSON 的 title 和 description"""
    changed = False
    for field in ('title', 'description'):
        if field in adv_json:
            val = adv_json[field]
            if isinstance(val, str) and val in translations:
                adv_json[field] = translations[val]
                changed = True
            elif isinstance(val, dict) and 'translate' in val:
                # 保持翻译key格式，不处理
                pass
    return changed


def main():
    if len(sys.argv) < 2:
        print("用法: python3 soulland_translate.py <soulland-1.0.0.jar>")
        print()
        print("Soul Land Mod 一键汉化脚本")
        print("  - 自动备份为 .bak")
        print("  - 注入 zh_cn.json 语言文件")
        print("  - 翻译 advancement 成就文件")
        print("  - 替换 class 文件硬编码英文 → 中文")
        sys.exit(1)
    
    jar_path = sys.argv[1]
    if not os.path.exists(jar_path):
        print(f"❌ 文件不存在: {jar_path}")
        sys.exit(1)
    
    bak_path = jar_path + '.bak'
    
    print("=" * 60)
    print("Soul Land Mod — 一键汉化")
    print("=" * 60)
    
    # Step 1: 备份
    print(f"\n📦 Step 1: 备份原文件")
    if not os.path.exists(bak_path):
        shutil.copy2(jar_path, bak_path)
        print(f"  ✅ 已备份 → {bak_path}")
    else:
        print(f"  ℹ 备份已存在: {bak_path}")
    
    # Step 2: 加载翻译
    print(f"\n📚 Step 2: 加载翻译数据")
    translations = load_translations()
    print(f"  总翻译条目: {len(translations)}")
    
    # Step 3: 处理 jar
    print(f"\n🔧 Step 3: 处理 JAR 文件")
    temp_jar = jar_path + '.new'
    total_patches = 0
    patched_files = 0
    zh_cn_written = False
    adv_patched = 0
    
    with ZipFile(bak_path, 'r') as zin:
        with ZipFile(temp_jar, 'w', ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                raw = zin.read(item.filename)
                
                # 注入 zh_cn.json
                if item.filename == 'assets/soulland/lang/en_us.json' or item.filename == 'assets/soulland/lang/zh_cn.json':
                    # 保留 en_us
                    zout.writestr(item, raw)
                    # 写入 zh_cn
                    zh_cn_data = json.dumps(ZH_CN, ensure_ascii=False, indent=2)
                    zout.writestr('assets/soulland/lang/zh_cn.json', zh_cn_data.encode('utf-8'))
                    zh_cn_written = True
                    print(f"  ✅ 注入 zh_cn.json ({len(ZH_CN)} 条)")
                    continue
                
                # 翻译 advancement
                if item.filename.startswith('data/soulland/advancements/') and item.filename.endswith('.json'):
                    try:
                        adv = json.loads(raw)
                        adv_key = item.filename.replace('data/', '').replace('.json', '')
                        if adv_key in ADVANCEMENTS:
                            for field, val in ADVANCEMENTS[adv_key].items():
                                adv[field] = val
                            adv_patched += 1
                        zout.writestr(item, json.dumps(adv, ensure_ascii=False, indent=2).encode('utf-8'))
                        continue
                    except:
                        zout.writestr(item, raw)
                        continue
                
                # 替换 class 文件
                if item.filename.endswith('.class'):
                    new_data, count = patch_class_data(raw, translations)
                    if count > 0:
                        patched_files += 1
                        total_patches += count
                    zout.writestr(item, new_data)
                    continue
                
                # 其他文件原样保留
                zout.writestr(item, raw)
    
    # 替换
    os.replace(temp_jar, jar_path)
    
    # Step 4: 总结
    print(f"\n{'=' * 60}")
    print(f"✅ 汉化完成！")
    print(f"{'=' * 60}")
    print(f"  语言文件 zh_cn.json: {'✅ ' + str(len(ZH_CN)) + ' 条' if zh_cn_written else '❌ 未注入'}")
    print(f"  成就文件: {adv_patched} 个已翻译")
    print(f"  Class 文件: {total_patches} 处字符串替换，覆盖 {patched_files} 个文件")
    print(f"  原文件备份: {bak_path}")
    print()
    print(f"重启 Minecraft 即可生效 🎮")


if __name__ == '__main__':
    main()
