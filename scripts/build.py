"""組出 dist/project.json：序章（劇情卡）＋培育室地圖。劇本就寫在這個檔裡。
用法：python3 scripts/build.py && python3 ~/larch-preview/serve.py dist/project.json"""
import json, pathlib, itertools, os, shutil
ROOT = pathlib.Path(__file__).resolve().parent.parent
import sys
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ui, layout
# 圖片網址：本機預覽用 /files/assets/（serve.py 從 dist/ 提供）；推上 Larch 用 jsDelivr，釘在已 push 的 commit SHA 上，換圖不會卡快取
CDN_SHA = next((a.split('=', 1)[1] for a in sys.argv if a.startswith('--cdn=')), '')
A = f'https://cdn.jsdelivr.net/gh/yazelin/larch-prince-hime@{CDN_SHA}/assets/' if CDN_SHA else '/files/assets/'
R2 = 'https://pub-4b20b43f5acf4dfaa3f6ab842daa51cf.r2.dev/2d3b0242-9a6d-4051-9825-46aa4efd064a/larch/built-in-assets/audio/larch-creatures/'
BGM_STORY, BGM_HOME = R2 + '1784841727962_sproutlight-path.mp3', R2 + '1784841721002_dewdrops-heart.mp3'
ART = {k: A + 'art/' + v for k, v in {
    'capital': 'bg/capital.webp', 'courtyard': 'bg/courtyard.webp', 'egg-feet': 'cg/egg-feet.webp', 'throne': 'bg/throne.webp',
    'arena': 'bg/arena.webp', 'adult-prince': 'cg/adult-prince.webp', 'adult-hime': 'cg/adult-hime.webp',
    'hatch': 'cg/hatch.webp', 'egg-rug': 'cg/egg-rug.webp', 'king': 'portrait/king.webp', 'journal': 'props/journal.webp', 'nursery': 'maps/nursery.webp',
    'slime': 'walk/slime-daily.webp', 'basket': 'props/basket.webp', 'poop': 'props/poop.webp', 'coin': 'props/coin.webp', 'gift': 'props/gift.webp',
    **{f'slime-{o}{x}': f'walk/slime-{o}{x}.webp' for o in ('lubu', 'lubu-heijin', 'liubei', 'guanyu', 'zhangfei', 'diaochan') for x in ('', '-still')},
    **{f'slime-{f}{x}': f'walk/slime-{f}{x}.webp' for f in ('prince', 'hime') for x in ('', '-still')}, 'slime-still': 'walk/slime-daily-still.webp'}.items()}
ART['cover'] = A + 'cover/cover-v3.webp'   # 封面沿用 assets/cover，不另存一份
KING = '國王'
VARS = {'intro_done': ('boolean', False, '看過序章、領養了（跨週目）'), 'booted': ('boolean', False, '開機分流用'),
        'hunger': ('number', 30, '肚子餓（0–100）'), 'affection': ('number', 0, '親密度'),
        'poop_a': ('boolean', False, '便便 A 在不在'), 'poop_b': ('boolean', False, '便便 B 在不在'), 'poop_c': ('boolean', False, '便便 C 在不在'),
        'last_seen': ('string', '', '最後在場時間'), 'away_minutes': ('number', 0, '上次離開了幾分鐘'),   # last_seen 用字串：選單「角色狀態」只列數字變數，毫秒數不該給玩家看
        'sulky': ('boolean', False, '在鬧脾氣（餵了就和好）'), 'very_sulky': ('boolean', False, '大鬧脾氣（要先陪玩）'),
        'fed': ('boolean', False, '鬧脾氣後餵過'), 'played': ('boolean', False, '鬧脾氣後玩過')}
# 作品聯動：原作品在「取得道具」卡打開 crossover，玩家在原作拿到過，這裡的 cross_<鍵> 就會是 "true"（引擎設的字串）。
# 數值跟著原作品走；這 8 件是背包道具，本身沒有戰鬥數值，在本作是禮物與造型解鎖。格式照《無雙》已經在用的寫法。
BUCHAN, TAOYUAN = 'project-1980dcc9-13b3-451c-8bf6-71b05bd5bfa9', 'project-6e031e3a-f508-4d77-aaa2-795edb6a80f4'
CROSS = [  # (鍵, 原作品, 原道具 id, 名稱, 送禮地點, 拆開時的一句, 解鎖的造型)
    ('lubu', BUCHAN, 'w-lubu', '方天畫戟', '仙泉谷', '暗紅的長杆，刃下一束紅纓。', 'lubu'),
    ('weixu', BUCHAN, 'w-weixu', '環首刀', '仙泉谷', '刀柄末端有一個鐵環。', ''),
    ('quan', BUCHAN, 'w-quan', '小木弓', '仙泉谷', '一把很小的木弓，弦上還纏著布條。', ''),
    ('xiang', BUCHAN, 'w-xiang', '鐵剪刀', '仙泉谷', '兩片刃，尾端一個鐵環。', ''),
    ('diaochan', BUCHAN, 'handkerchief', '冷梅帕', '仙泉谷', '一方帕子，角上繡著冷梅。', 'diaochan'),
    ('liubei', TAOYUAN, 'w-liubei', '雙股劍', '涿郡桃園', '一雌一雄兩把劍。', 'liubei'),
    ('guanyu', TAOYUAN, 'w-guanyu', '青龍偃月刀', '涿郡桃園', '刀身削成一彎新月。', 'guanyu'),
    ('zhangfei', TAOYUAN, 'w-zhangfei', '丈八蛇矛', '涿郡桃園', '矛頭彎彎的，像一條蛇。', 'zhangfei'),
]
WORKS = {BUCHAN: '仙泉．香布纏', TAOYUAN: '咒泉．三結義'}
OUTFITS = {'lubu': ('ph-lubu', '方天畫戟・百花', 'slime-lubu', 'lubu'), 'heijin': ('ph-lubu-heijin', '方天畫戟・黑金', 'slime-lubu-heijin', 'lubu'),
           'liubei': ('ph-liubei', '雙股劍', 'slime-liubei', 'liubei'),
           'guanyu': ('ph-guanyu', '青龍偃月刀', 'slime-guanyu', 'guanyu'), 'zhangfei': ('ph-zhangfei', '丈八蛇矛', 'slime-zhangfei', 'zhangfei'),
           'diaochan': ('ph-diaochan', '冷梅帕', 'slime-diaochan', 'diaochan')}   # 造型鍵 → (資料庫角色 id, 名稱, 小人圖, 解鎖它的聯動禮物)；方天畫戟一件解鎖呂布兩套
UNLOCKS = list(dict.fromkeys(v[3] for v in OUTFITS.values()))   # 解鎖造型的禮物（穿衣鏡依「拿到哪幾件」分頁）
for k, *_ in CROSS:
    VARS[f'got_{k}'] = ('boolean', False, f'領過聯動禮物 {k}')
VARS['outfit'] = ('string', '', '目前的造型（空字串＝平常）')
VARS['mirror_new'] = ('boolean', False, '有新造型還沒去穿衣鏡')
VARS['pet_name'] = ('string', '', '寵物的名字（時鐘 HUD 從 rpgState 抄出來，換造型也不變）')
# 王子／公主分化（2026-10-09 作者：照顧的方式決定，docs/03 開頭〈分化（拍板版）〉）：玩具箱選的遊戲累積傾向，親密度到 GROW_AT 時分化
VARS['lean'] = ('number', 0, '小王子(+)／小公主(−)傾向')
VARS['last_play'] = ('string', '', '最後一次玩的遊戲（prince／hime；傾向打平時照它）')
VARS['form'] = ('string', '', '分化後的樣子（空字串＝還沒分化、prince、hime）')
VARS['grow_hint'] = ('boolean', False, '分化前的預告說過了')
VARS['base_ok'] = ('boolean', True, '平常的樣子已經換成分化後的那隻（換回平常時設 false，條件事件接手）')
GROW_AT, GROW_HINT, LEAN_SHOW = 300, 260, 2
ADULT_AT = 400   # 分化後親密度再到這裡，國王的使者送來成年禮的邀請（約再陪玩 12 次）
VARS['invited'] = ('boolean', False, '收到成年禮的邀請')
VARS['adult'] = ('boolean', False, '辦過競技場成年禮')   # ponytail: 只看親密度（陪玩 +8、餵食 +3～5，約玩 30 次）；要照天數算再加時鐘 HUD 的天數
FORMS = {'prince': ('ph-prince', '小王子', 'slime-prince'), 'hime': ('ph-hime', '小公主', 'slime-hime')}   # 分化鍵 → (資料庫角色 id, 稱呼, 小人圖)
CROSS_PERSIST = {f'got_{k}' for k, *_ in CROSS} | {'outfit', 'mirror_new', 'pet_name', 'rpgState', 'lean', 'last_play', 'form', 'grow_hint', 'invited', 'adult'}   # rpgState 裡有名字與位置（實測 166 字，上限 2000）   # 併進下面的 PERSIST
CROSS_VARS = [f'cross_{k}' for k, *_ in CROSS]   # 引擎依玩家收藏設的字串變數，id 照《無雙》加 rpg- 前綴

BASE_DEFAULTS = {k: d for k, (_, d, _) in VARS.items()}   # 正式版的預設值：重新領養一律還原成這些，不受下面測試旗標影響
# 核心循環的節奏（只算開著遊戲的時間）
HUNGER_TICK_MS, HUNGER_STEP, HUNGRY_AT = 30000, 10, 60
POOP_TICK_MS = 40000
POOP_CELLS = {'poop_a': (9, 13), 'poop_b': (15, 12), 'poop_c': (13, 5)}
# 跨週目保留（編輯器「玩家變數 → 跨週目保留」）：寵物的狀態都留著，關掉再開就接著養，不用手動存檔。
# 字串超過 2000 字會被截斷（播放器 Xt=2e3），背包要注意。
PERSIST = {'intro_done', 'hunger', 'affection', 'poop_a', 'poop_b', 'poop_c', 'last_seen', 'sulky', 'very_sulky', 'fed', 'played', 'inventory'}
PERSIST |= CROSS_PERSIST
# 離線時間（時鐘 HUD）：離開每 1 小時餓 10，每 2 小時一坨便便（最多三坨）；在場時每 60 秒記一次時間
OFF_HUNGER_MS, OFF_HUNGER_STEP, OFF_POOP_MS, BEAT_MS = 3600000, 10, 7200000, 60000
AWAY_HI, AWAY_SULK, AWAY_VERY = 60, 480, 4320   # 分鐘：1 小時、8 小時、3 天
CROSS_TEST = [x for a in sys.argv if a.startswith('--cross=') for x in a.split('=', 1)[1].split(',')]   # 測試用：假裝收藏裡已經有這些（例如 --cross=lubu）
LAYERED = '--old-map' not in sys.argv   # 分層版育嬰室（art/objects_nursery.yaml，2026-10-08 作者確認轉正）；--old-map 回到舊整張地圖
AWAY_TEST = next((int(a.split('=', 1)[1]) for a in sys.argv if a.startswith('--away=')), None)   # 測試用：假裝上次離開了幾分鐘
if AWAY_TEST is not None:
    import time
    VARS.update(intro_done=('boolean', True, VARS['intro_done'][2]),
                last_seen=('string', str(int(time.time() * 1000) - AWAY_TEST * 60000), VARS['last_seen'][2]))
GROW_TEST = next((int(a.split('=', 1)[1]) for a in sys.argv if a.startswith('--grow=')), None)   # 測試用：開局親密度（例如 --grow=295，玩一次就分化）
if GROW_TEST is not None:
    VARS['intro_done'] = ('boolean', True, VARS['intro_done'][2]); VARS['affection'] = ('number', GROW_TEST, VARS['affection'][2])
if '--fast' in sys.argv:   # 測試用：幾秒就餓、就有便便；開局當作已寫過日誌、肚子很餓，任務提示直接指向點心籃
    HUNGER_TICK_MS, POOP_TICK_MS, BEAT_MS = 3000, 4000, 5000
    VARS['intro_done'] = ('boolean', True, VARS['intro_done'][2]); VARS['hunger'] = ('number', 80, VARS['hunger'][2])
RPG_VARS = [('hp', 'rpgHp', 'number', 100), ('bag', 'inventory', 'string', '[]'), ('equipment', 'rpgEquipment', 'string', '{}'),
            ('state', 'rpgState', 'string', ''), ('used', 'inventoryLastUsed', 'string', ''), ('count', 'inventoryCount', 'number', 0)]
RPG_LABELS = {'inventoryCount': '道具數量', 'rpgHp': '生命值'}

# ---------- 劇本 ----------
# 每張卡：(id, 標題, 背景, 台詞[字串＝旁白，(講者, 文字)], 有沒有國王立繪)
STORY = [
    ('p-capital', '雲端王都', 'capital', [
        '雲端王都的正中央，長著一棵生命聖樹。',
        '它一百年才結一顆果實：一顆半透明的蛋，蛋頂黏著一頂很小的金冠。',
        '王室的下一位繼承人，就睡在那顆蛋裡。',
        '今年剛好滿一百年。整個王都都在等它熟。'], False),
    ('p-courtyard', '聖樹底下', 'courtyard', [
        '那天早上，你在聖樹底下掃落葉。你是王宮的見習生，進宮第三天。',
        '頭頂傳來很輕的一聲「啵」。',
        '蛋掉下來了。',
        '它彈過草地，彈過噴水池的邊，從三位正在吵「到底該由誰來養」的大臣中間滾過去，',
        '最後停在你的鞋子旁邊。'], False),
    ('p-ignore', '假裝沒看到', 'egg-feet', [
        '你把掃把往旁邊挪了一點，繼續掃。',
        '蛋自己滾了回來，又停在你的鞋子旁邊。這次貼得更近。',
        '你只好把它撿起來。'], False),
    ('p-pickup', '撿起來', 'egg-feet', [
        '蛋比看起來輕，摸起來涼涼軟軟的，像剛從冰箱拿出來的布丁。',
        '三位大臣同時轉過頭來看你。'], False),
    ('p-throne', '王座廳', 'throne', [
        (KING, '撿到的人負責養。'),
        '國王是一隻很大的史萊姆，淡淡的蜂蜜色，留著一大把白鬍子。說完這句，他又往王座的軟墊裡陷下去一點。'], True),
    ('p-reluctant', '只是來掃落葉的', 'throne', [
        (KING, '本王一百年前，也是被一個掃落葉的撿到的。'),
        (KING, '那個人後來當了宰相。')], True),
    ('p-willing', '會好好照顧', 'throne', [
        (KING, '很好。'),
        (KING, '本王一百年前，也是被一個掃落葉的撿到的。')], True),
    ('p-rules', '三條規矩', 'throne', [
        (KING, '規矩只有三條：餵牠、陪牠、幫牠收拾。'),
        (KING, '牠拉出來的東西會發光。那個可以拿去換錢，不要丟。'),
        (KING, '至於牠長大以後是王子，還是公主……'),
        (KING, '看你怎麼養。本王不管。'),
        (KING, '等牠長大，要上競技場辦成年禮，到時候整個王都的人都會來看。'),
        (KING, '從今天起，你是皇家御用導師。掃把交給別人吧。')], True),
    ('p-nursery', '育嬰室', 'egg-rug', [
        '你被帶到一間朝南的小房間，地上鋪著一塊雲朵形狀的地毯。',
        '你把蛋放在地毯正中央。蛋裡有一個小小的光點，一閃一閃，跟心跳差不多快。'], False),
    ('p-poke', '戳一下', 'egg-rug', ['整顆蛋像布丁一樣，抖了三下。'], False),
    ('p-wait', '等等看', 'egg-rug', ['你等了一下。蛋好像等不及了。'], False),
    ('p-hatch', '破殼', 'hatch', [
        '啵。',
        '蛋殼裂成兩半，一團白白軟軟的東西彈了出來，頭上歪歪地戴著那頂小金冠。',
        '牠看著你，眨了兩下眼睛。'], False),
    # 競技場成年禮（分化後，從育嬰室門口出發）：表演依分化分兩張，再回到同一張
    ('a-arena', '競技場', 'arena', [
        '王都的競技場坐滿了來看熱鬧的史萊姆。三位大臣坐在最前排，這次沒有在吵架。',
        '你抱著{{pet_name}}走進場中央。地上鋪了一塊雲朵形狀的地毯，跟育嬰室那塊一模一樣。',
        (KING, '本王一百年前的成年禮，也是在這裡辦的。'),
        (KING, '那時候本王表演的是……算了，不重要。換牠。')], True),
    ('a-prince', '比劍', 'adult-prince', [
        '{{pet_name}}從地毯上彈起來，舉著那把軟軟的木劍。',
        '牠對著場邊的稻草人揮了三下。第三下太用力，稻草人倒了，牠自己也滾了兩圈。',
        '全場安靜了一下，然後大家都在拍手。'], False),
    ('a-hime', '茶會', 'adult-hime', [
        '{{pet_name}}端端正正地坐在地毯中央，面前擺著一套小茶杯和一盤星星餅乾。',
        '牠替國王倒了一杯茶，倒得有點滿，茶從杯緣溢出來一點點。',
        '國王一口喝完。全場都在拍手。'], False),
    ('a-crown', '成年禮', 'arena', [
        (KING, '很好。從今天起，{{pet_name}}是王都正式的王族了。'),
        (KING, '至於你。'),
        (KING, '導師的位子，繼續坐著吧。本王不管。'),
        '回到育嬰室的路上，{{pet_name}}在你懷裡睡著了。'], True),
]
# 選項卡：(id, 標題, 背景, 問句, [(選項, 去哪張卡)])
CHOICES = [
    ('c-egg', '蛋停在腳邊', 'egg-feet', '蛋停在你腳邊，晃了兩下。', [('撿起來', 'p-pickup'), ('假裝沒看到，繼續掃地', 'p-ignore')]),
    ('c-king', '國王看著你', 'throne', '國王看著你。', [('可是我只是來掃落葉的……', 'p-reluctant'), ('我會好好照顧牠。', 'p-willing')]),
    ('c-poke', '光點', 'egg-rug', '要怎麼做？', [('輕輕戳一下', 'p-poke'), ('先等等看', 'p-wait')]),
]
FLOW = [('route', 'p-capital'), ('p-capital', 'p-courtyard'), ('p-courtyard', 'c-egg'), ('p-ignore', 'p-throne'), ('p-pickup', 'p-throne'),
        ('p-throne', 'c-king'), ('p-reluctant', 'p-rules'), ('p-willing', 'p-rules'), ('p-rules', 'p-nursery'),
        ('p-nursery', 'c-poke'), ('p-poke', 'p-hatch'), ('p-wait', 'p-hatch'), ('p-hatch', 'm-nursery'),
        ('a-prince', 'a-crown'), ('a-hime', 'a-crown'), ('a-crown', 'a-done'), ('a-done', 'm-nursery')]
HOME_BGM_FROM = 'p-nursery'   # 從育嬰室開始換成培育室的音樂

# ---------- 卡片 ----------
_pos = itertools.count()
def pos():
    i = next(_pos); return {'x': (i % 6) * 380, 'y': (i // 6) * 280}

def story_card(id, title, bg, lines, king):
    dl = [{'id': f'{id}-l{i}', 'speaker': l[0] if isinstance(l, tuple) else '', 'text': l[1] if isinstance(l, tuple) else l} for i, l in enumerate(lines)]
    actors = [{'id': 'actor-king', 'name': KING, 'url': ART['king'], 'slot': 'right', 'offsetX': 0, 'offsetY': 0, 'scale': 1}] if king else []
    return {'id': id, 'type': 'story', 'position': pos(), 'data': {'type': 'dialogue', 'title': title, 'speaker': dl[0]['speaker'], 'text': dl[0]['text'],
            'dialogueLines': dl, 'background': ART[bg], 'stage': {'actors': actors}}}

def choice_card(id, title, bg, question, opts):
    return {'id': id, 'type': 'story', 'position': pos(), 'data': {'type': 'choice', 'title': title, 'text': question, 'background': ART[bg],
            'choices': [o for o, _ in opts], 'choiceMode': 'branch', 'stage': {'actors': []}}}

def edge(a, b, handle='right'):
    return {'id': f'{a}--{b}', 'source': a, 'target': b, 'sourceHandle': handle, 'targetHandle': 'left'}

# ---------- 培育室地圖 ----------
_aid = itertools.count(1)
def act(kind, **kw):
    a = {'id': f'a{next(_aid)}', 'kind': kind, 'text': '', 'cardId': '', 'itemId': '', 'itemName': '', 'variable': '', 'value': '', 'amount': 1}
    a.update(kw); return a
def say(t, speaker='narrator', pres='bubble'):   # 地圖上的話一律用泡泡框，掛在寵物頭上（2026-10-08 作者：底部文字改泡泡）；who 沒寫會掛在觸發的事件上，自動事件放在牆格會飄到牆上
    return act('dialogue', text=t, presentation=pres, speaker=speaker, who='hero')
def setv(k, v): return act('variable', variable=k, value=str(v).lower() if isinstance(v, bool) else str(v))
def waits(ms):   # wait 步驟上限 9999 毫秒，長的等待拆成幾段
    return [act('wait', amount=min(9999, ms - i)) for i in range(0, ms, 9999)]
def addv(k, n): return act('variable', variable=k, value=str(abs(n)), op='add' if n >= 0 else 'subtract')
def balloon(icon, ms=2400): return act('balloon', balloon={'icon': icon, 'target': 'player', 'durationMs': ms})
def pic_sprite(url, scale, px=64): return {'url': url, 'width': px, 'height': px, 'frames': 1, 'rows': 1, 'offsetX': 0, 'offsetY': 0, 'idleFrame': 0, 'scale': scale}
def cond(k, v, op='eq'): return {'kind': 'variable', 'variable': k, 'op': op, 'value': str(v).lower() if isinstance(v, bool) else str(v), 'itemId': '', 'count': 1}
INVISIBLE = {'url': '', 'width': 32, 'height': 32, 'frames': 1, 'rows': 1, 'offsetX': 0, 'offsetY': 0, 'idleFrame': 0}
def ev(id, x, y, **kw):
    e = {'id': id, 'name': id, 'x': x, 'y': y, 'actor': 'none', 'trigger': 'action', 'movement': 'still', 'solid': False,
         'once': False, 'conditions': [], 'actions': [], 'direction': 'down', 'sprite': INVISIBLE}
    e.update(kw); return e

W, H = 24, 18
def walls():
    # 照 nursery.webp 疊 24×18 格線對出來的（每格 60.3px）。換地圖圖要重對；互動點都放在只有一面走得到的格子。
    rects = [(0, 0, 23, 2), (0, 3, 6, 3),                 # 上牆、書櫃與盆栽
             (0, 4, 2, 8), (3, 5, 3, 8),                  # 貝殼鏡、矮凳（含鏡子下緣）
             (0, 9, 1, 10), (2, 9, 3, 10),                # 盆栽、糖果小桌
             (0, 11, 3, 15),                              # 玩具箱
             (18, 3, 23, 6), (22, 6, 23, 7),              # 嬰兒床（含床下圓毯）、檯燈邊桌；點心籃在床左下角 (18,5)，只能從 (17,5) 靠近
             (22, 8, 23, 9), (21, 10, 23, 16),            # 盆栽、沙發
             (15, 10, 16, 11),                            # 地毯上的圓墊
             (0, 16, 9, 17), (15, 16, 23, 17), (10, 17, 14, 17)]   # 下緣欄杆；(10..14,16) 是門口地墊，之後接別的地圖
    return {(x, y) for x0, y0, x1, y1 in rects for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)}

FRAMES = 4     # 走路圖每列幾格（process_art.HOP）
TILE_PX = 40 if LAYERED else 80   # 分層版切成細格，一格只有原本一半寬； 1920 寬視窗一格約幾個螢幕 px；scale＝圖寬/TILE_PX，小人圖 1 px＝螢幕 1 px（引擎不平滑，放大會糊）


def walk_sprite(key):
    W, H = Image.open(ROOT / 'assets/art' / ART[key].split('art/', 1)[1]).size
    w = W // FRAMES; rows = H // w   # 每列 FRAMES 格（走路時輪播的果凍彈跳）；造型小人是四列（下、左、右、上），引擎遇到四列就不翻面，玉珮上的字才不會變鏡像字
    return {'url': ART[key], 'width': w, 'height': w, 'frames': FRAMES, 'rows': rows, 'offsetX': 0, 'offsetY': 0, 'idleFrame': 0,
            'scale': round(w / TILE_PX, 3), 'faces': 'right'}   # 引擎顯示寬度＝scale 格，跟圖幾 px 無關


def nursery():
    # 主角事件不綁 actorId：引擎畫的是資料庫 heroId 那位，hero 步驟換人（換裝）地圖上才會跟著換。sprite 只是佔位（照《無雙》的寫法）
    # 主角：引擎畫資料庫 heroId 那位（換裝＝hero 步驟換人）；事件上的 sprite 是資料庫讀不到時的備用
    hero = ev('hero', 12, 9, name='王子姬', actor='player', direction='down',
              sprite=walk_sprite('slime'))
    intro = ev('intro', 12, 12, trigger='auto', once=True, conditions=[cond('intro_done', True, 'neq')], actions=[
        act('name', text='幫牠取個名字吧。', naming={'who': '', 'max': 8}),
        say('噗啾！', speaker='player', pres='bubble'),
        say('{{hero}}好像很喜歡這個名字。'),
        say('房間左邊的小桌子上有一本王室日誌，翻開就看得到{{hero}}今天的狀況。'),
        say('點心籃在嬰兒床旁邊，玩具箱在左下角。{{hero}}的便便會發光，看到了就去撿。'),
        setv('intro_done', True)])
    reset = [setv(k, BASE_DEFAULTS[k]) for k in VARS if k in PERSIST] + [setv('inventory', '[]'), setv('rpgState', ''), act('jump', cardId='p-capital')]
    def journal_acts(line):
        return [say('{{pet_name}}　肚子餓的程度：{{hunger}}／100　親密度：{{affection}}'), say(line),
            act('choice', text='要做什麼？', speaker='narrator', choice={'cancel': 'close', 'options': [
                {'id': 'close', 'label': '闔上日誌', 'actions': []},
                {'id': 'replay', 'label': '重看序章', 'actions': [act('jump', cardId='p-capital')]},
                {'id': 'reset', 'label': '重新領養（從頭開始）', 'actions': [
                    act('dialogue', text='重新領養之後，{{pet_name}}的名字、飽足、親密度和金幣都會歸零，小王子、小公主也會變回剛出生的樣子。確定嗎？', presentation='text', speaker='narrator',
                        confirm={'accept': '確定，從頭開始', 'cancel': '再想想'}),
                    *reset]}]})]
    journal_page = lambda id, cs, line: {'id': id, 'conditions': cs, 'actor': 'none', 'sprite': INVISIBLE, 'movement': 'still', 'solid': True,
                                         'trigger': 'action', 'once': False, 'actions': journal_acts(line)}
    journal = ev('journal', 3, 9, solid=True,   # 糖果小桌右半；只能從右邊 (4,9) 靠近，按左鍵只會轉身
                 free={'url': ART['journal'], 'x': 2.4, 'y': 7.9, 'w': 1.3, 'h': 1.3},
                 marker={'label': '王室日誌', 'kind': 'talk'}, actions=journal_acts('還看不出來{{pet_name}}會變成小王子還是小公主。'),
                 pages=[journal_page(id, cs, line) for id, cs, line in (   # 後面的分頁優先
                     ('lean-prince', [cond('form', ''), cond('lean', LEAN_SHOW, 'gte')], '最近的{{pet_name}}，比較像一位小王子。'),
                     ('lean-hime', [cond('form', ''), cond('lean', -LEAN_SHOW, 'lte')], '最近的{{pet_name}}，比較像一位小公主。'),
                     ('is-prince', [cond('form', 'prince')], '{{pet_name}}是王都的小王子。'),
                     ('is-hime', [cond('form', 'hime')], '{{pet_name}}是王都的小公主。'),
                     ('adult-prince', [cond('form', 'prince'), cond('adult', True)], '{{pet_name}}辦過成年禮了，是王都正式的小王子。'),
                     ('adult-hime', [cond('form', 'hime'), cond('adult', True)], '{{pet_name}}辦過成年禮了，是王都正式的小公主。'))])
    loop = lambda: act('loop', loop={})
    # 時鐘：開著遊戲時每 30 秒餓一點；上下限另外兩個事件夾住
    clock = ev('clock', 0, 0, trigger='parallel',   # 不掛 intro_done：背景事件只在進地圖時看條件，開場中途才成立的話要離開再回來才會跑
               actions=waits(HUNGER_TICK_MS) + [addv('hunger', HUNGER_STEP), loop()])
    cap = ev('hunger-cap', 1, 0, trigger='condition', conditions=[cond('hunger', 101, 'gte')], actions=[setv('hunger', 100)])
    floor = ev('hunger-floor', 2, 0, trigger='condition', conditions=[cond('hunger', -1, 'lte')], actions=[setv('hunger', 0)])
    hungry = ev('hungry', 3, 0, trigger='parallel', conditions=[cond('hunger', HUNGRY_AT, 'gte')],
                actions=[balloon('rice', 2500), act('wait', amount=6000), act('loop', loop={'until': [cond('hunger', HUNGRY_AT - 1, 'lte')]})])
    def eat(name, food, fill, love):
        return {'id': f'eat-{food}', 'label': name, 'actions': [addv('hunger', -fill), addv('affection', love), setv('fed', True),
                balloon('heart'), say(f'{{{{pet_name}}}}一口吞下了{name}。')]}
    basket = ev('basket', 18, 5, solid=True, free={'url': ART['basket'], 'x': 17.6, 'y': 3.9, 'w': 1.3, 'h': 1.3},   # 嬰兒床左下角；只能從左邊 (17,5) 靠近，按右鍵只會轉身
                marker={'label': '點心籃', 'kind': 'talk'}, actions=[
        act('choice', text='要吃什麼？', speaker='narrator', choice={'options': [eat('草莓布丁', 'pudding', 40, 3), eat('蜂蜜鬆餅', 'pancake', 30, 5),
                                                                       {'id': 'no', 'label': '現在不餓', 'actions': []}], 'cancel': 'no'})])
    def play(id, label, line, lean):   # 兩種遊戲一樣加親密度；選哪種累積小王子／小公主的傾向
        return {'id': id, 'label': label, 'actions': [say(line), addv('affection', 8), addv('hunger', 10), setv('played', True),
                addv('lean', 1 if lean == 'prince' else -1), setv('last_play', lean), balloon('music')]}
    toys = ev('toys', 3, 13, solid=True, marker={'label': '玩具箱', 'kind': 'talk'}, actions=[   # 箱子右緣那一格；小人站 (4,13) 面向左
        act('choice', text='要玩什麼？', speaker='narrator', choice={'cancel': 'no', 'options': [
            play('sword', '騎木馬比劍', '你拿出木馬和兩把軟軟的木劍。{{pet_name}}跳上木馬，揮著劍衝了三圈。', 'prince'),
            play('tea', '辦小茶會', '你在地毯上擺好小茶杯和星星餅乾。{{pet_name}}端端正正地坐好，等你倒茶。', 'hime'),
            {'id': 'no', 'label': '先不玩', 'actions': []}]})])
    # 黃金便便：三個固定位置，計時器隨機點亮一個；走過去就撿起來換金幣
    poop_timer = ev('poop-timer', 4, 0, trigger='parallel', actions=[
        *waits(POOP_TICK_MS),
        act('random', random={'min': 1, 'max': 3, 'options': [{'id': f'r{i}', 'from': i, 'to': i, 'actions': [setv(k, True)]}
                                                             for i, k in enumerate(POOP_CELLS, 1)]}),
        loop()])
    poops = [ev(k, x, y, pages=[{'id': 'here', 'conditions': [cond(k, True)], 'actor': 'npc', 'sprite': pic_sprite(ART['poop'], 1.6 if LAYERED else 0.8),
                                 'movement': 'still', 'direction': 'down', 'solid': False, 'trigger': 'touch', 'once': False, 'actions': [
                act('sound', sound='item', audio={'url': '', 'volume': 0.8}), setv(k, False),
                act('item', itemId='coin', itemName='王室金幣', amount=1), balloon('happy', 1600)]}])
             for k, (x, y) in POOP_CELLS.items()]
    # 禮物箱：放在沙發上（牆格），小人只能從左邊 (20,12) 靠近，按右鍵只會轉身。每件一個分頁，一次領一件。
    def gift_page(k, work, ref, name, place, line, outfit):
        acts = [say(f'國王的使者送來一個包裹，封蠟上寫著「{place}」。'), say(f'裡面是{name}。{line}'),
                act('item', itemId=f'cx-{k}', itemName=name, amount=1), setv(f'got_{k}', True), balloon('heart')]
        if outfit:
            got = [v[1] for v in OUTFITS.values() if v[3] == k]
            acts += [say(f'穿衣鏡那邊多了{"兩" if len(got) == 2 else "一"}套造型：{"、".join(got)}。'), setv('mirror_new', True)]
        return {'id': f'gift-{k}', 'conditions': [cond(f'cross_{k}', 'true'), cond(f'got_{k}', True, 'neq')], 'actor': 'none', 'sprite': INVISIBLE,
                'movement': 'still', 'solid': True, 'trigger': 'action', 'once': False, 'actions': acts}
    gift = ev('gift', 21, 12, solid=True, free={'url': ART['gift'], 'x': 20.6, 'y': 10.9, 'w': 1.3, 'h': 1.3},
              marker={'label': '禮物箱', 'kind': 'talk'}, actions=[say('禮物箱現在是空的。別的王國送東西來的時候，會先放在這裡。')],
              pages=[gift_page(*c) for c in reversed(CROSS)])   # 後面的分頁優先：照清單順序一件一件給
    # 穿衣鏡：貝殼鏡上緣 (2,4)（牆格），小人只能從右邊 (3,4) 靠近，按左鍵只會轉身。
    wear = lambda okey: [act('hero', value=OUTFITS[okey][0] if okey else 'ph'), setv('outfit', okey)] + ([] if okey else [setv('base_ok', False)])   # 換回平常：分化過的由 base-*-now 接手
    # 選項不能各自帶條件，所以「拿到哪幾件」的每種組合各一個分頁，選單只列拿到的造型（4 件＝15 頁，引擎上限 98）
    def mirror_page(have):
        opts = [{'id': 'plain', 'label': '平常', 'actions': wear('')}] + [
            {'id': f'o-{o}', 'label': v[1], 'actions': wear(o)} for o, v in OUTFITS.items() if v[3] in have] + [{'id': 'keep', 'label': '不換', 'actions': []}]
        return {'id': 'mirror-' + '-'.join(have), 'conditions': [cond(f'got_{u}', True, 'eq' if u in have else 'neq') for u in UNLOCKS],
                'actor': 'none', 'sprite': INVISIBLE, 'movement': 'still', 'solid': True, 'trigger': 'action', 'once': False,
                'actions': [setv('mirror_new', False), act('choice', text='要換哪一套？', speaker='narrator', choice={'cancel': 'keep', 'options': opts})]}
    combos = [[u for i, u in enumerate(UNLOCKS) if n >> i & 1] for n in range(1, 2 ** len(UNLOCKS))]
    mirror = ev('mirror', 2, 4, solid=True, marker={'label': '穿衣鏡', 'kind': 'talk'}, actions=[
        say('鏡子裡是{{pet_name}}平常的樣子。'), say('收到別的王國送來的兵器以後，可以在這裡換造型。')],
        pages=[mirror_page(h) for h in combos])
    # 換裝跨週目保留：進地圖時照 outfit 換回去（主角換人存在本輪存檔裡，跨週目只留得住變數）
    restores = [ev(f'outfit-{o}', 11 + i, 0, trigger='auto', conditions=[cond('outfit', o)], actions=[act('hero', value=OUTFITS[o][0])])
                for i, o in enumerate(OUTFITS)]
    # 分化：親密度到 GROW_AT，傾向正→小王子、負→小公主、打平照最後一次玩的遊戲（還沒玩過就等）。事件放在第 1 列（新舊地圖都是牆）
    grow_c = [cond('form', ''), cond('affection', GROW_AT, 'gte')]
    grow = lambda id, x, f, cs: ev(id, x, 1, trigger='condition', conditions=grow_c + cs, actions=[
        balloon('music'), say('噗……啾？', speaker='player'), say('{{pet_name}}全身亮起柔柔的光，光裡傳來小小的、很開心的笑聲。'),
        setv('form', f), setv('base_ok', False), say(f'光散開的時候，{{{{pet_name}}}}變成了一位{FORMS[f][1]}。'), balloon('heart'),
        say('穿衣鏡的「平常」也換成了新的樣子。聯動造型照樣穿得上。')])
    grows = [grow('grow-p1', 1, 'prince', [cond('lean', 1, 'gte')]), grow('grow-p2', 2, 'prince', [cond('lean', 0), cond('last_play', 'prince')]),
             grow('grow-h1', 3, 'hime', [cond('lean', -1, 'lte')]), grow('grow-h2', 4, 'hime', [cond('lean', 0), cond('last_play', 'hime')])]
    hint = ev('grow-hint', 5, 1, trigger='condition', conditions=[cond('form', ''), cond('grow_hint', True, 'neq'), cond('affection', GROW_HINT, 'gte')], actions=[
        say('……啾。身體好像熱熱的。', speaker='player'), say('{{pet_name}}最近很常發呆，好像快要長大了。'), setv('grow_hint', True)])
    # 成年禮：分化後親密度到 ADULT_AT，使者送邀請；從門口出發（門口在地圖最下面正中的地墊上，寵物站在上面一格往下按）
    invite = ev('invite', 10, 1, trigger='condition', conditions=[cond('form', '', 'neq'), cond('adult', True, 'neq'), cond('invited', True, 'neq'), cond('affection', ADULT_AT, 'gte')], actions=[
        balloon('exclamation'), say('門口傳來敲門聲。國王的使者送來一封信，封蠟上是那頂小金冠。'),
        say('「{{pet_name}}的成年禮，在競技場舉行。準備好了，就從育嬰室門口出發。」'), setv('invited', True)])
    door = ev('door', 11, 17, solid=True, marker={'label': '門口', 'kind': 'talk'}, actions=[say('門外是王宮的長廊。國王說過，沒事不要帶牠亂跑。')], pages=[
        {'id': 'go', 'conditions': [cond('invited', True), cond('adult', True, 'neq')], 'actor': 'none', 'sprite': INVISIBLE, 'movement': 'still', 'solid': True,
         'trigger': 'action', 'once': False, 'actions': [act('choice', text='要出發去競技場嗎？', speaker='narrator', choice={'cancel': 'wait', 'options': [
             {'id': 'go', 'label': '出發', 'actions': [act('jump', cardId='a-arena')]}, {'id': 'wait', 'label': '再等一下', 'actions': []}]})]},
        {'id': 'done', 'conditions': [cond('adult', True)], 'actor': 'none', 'sprite': INVISIBLE, 'movement': 'still', 'solid': True,
         'trigger': 'action', 'once': False, 'actions': [say('門外是王宮的長廊。{{pet_name}}的成年禮已經辦完了，今天就待在育嬰室吧。')]}])
    # 平常的樣子：進地圖時（auto）與從穿衣鏡換回平常時（condition，看 base_ok）都換成分化後那隻
    bases = [ev(f'base-{f}', 6 + i, 1, trigger='auto', conditions=[cond('outfit', ''), cond('form', f)], actions=[act('hero', value=aid), setv('base_ok', True)])
             for i, (f, (aid, _, _)) in enumerate(FORMS.items())] + [
            ev(f'base-{f}-now', 8 + i, 1, trigger='condition', conditions=[cond('outfit', ''), cond('form', f), cond('base_ok', True, 'neq')],
               actions=[act('hero', value=aid), setv('base_ok', True)]) for i, (f, (aid, _, _)) in enumerate(FORMS.items())]
    away = lambda lo, hi=None: [cond('away_minutes', lo, 'gte')] + ([cond('away_minutes', hi, 'lte')] if hi else [])
    bubble = lambda t: say(t, speaker='player', pres='bubble')
    welcome = ev('back-hi', 6, 0, trigger='condition', conditions=away(AWAY_HI, AWAY_SULK - 1), actions=[
        balloon('heart'), bubble('你回來了！'), setv('away_minutes', 0)])
    sulk = ev('back-sulk', 7, 0, trigger='condition', conditions=away(AWAY_SULK, AWAY_VERY - 1), actions=[
        balloon('anger'), bubble('本宮等很久了。'), say('{{pet_name}}把臉轉開。餵牠吃點東西，大概就會和好。'),
        setv('fed', False), setv('sulky', True), setv('away_minutes', 0)])
    very = ev('back-very', 8, 0, trigger='condition', conditions=away(AWAY_VERY), actions=[
        balloon('anger'), say('{{pet_name}}縮在房間角落，背對著你，怎麼叫都不回頭。'),
        say('地上有一張歪歪扭扭的紙條：「本宮不理你了。」'), say('先陪牠玩一下吧。'),
        setv('played', False), setv('fed', False), setv('very_sulky', True), setv('sulky', True), setv('away_minutes', 0)])
    makeup_play = ev('makeup-play', 9, 0, trigger='condition', conditions=[cond('very_sulky', True), cond('played', True)], actions=[
        bubble('……好啦，陪你玩一下而已。'), setv('very_sulky', False), setv('fed', False)])
    makeup_eat = ev('makeup-eat', 10, 0, trigger='condition', conditions=[cond('sulky', True), cond('very_sulky', True, 'neq'), cond('fed', True)], actions=[
        balloon('heart'), bubble('……這次就原諒你。'), setv('sulky', False)])
    guidance = [{'text': '牠在鬧脾氣，先陪牠玩（玩具箱）', 'eventId': 'toys', 'conditions': [cond('very_sulky', True)]},
                {'text': '牠還在生氣，餵牠吃點東西', 'eventId': 'basket', 'conditions': [cond('sulky', True)]}] + [
                {'text': '有遠方送來的禮物', 'eventId': 'gift', 'conditions': [cond(f'cross_{k}', 'true'), cond(f'got_{k}', True, 'neq')]} for k, *_ in CROSS] + [
                {'text': '去穿衣鏡換上新造型', 'eventId': 'mirror', 'conditions': [cond('mirror_new', True)]},
                {'text': '成年禮：從門口出發去競技場', 'eventId': 'door', 'conditions': [cond('invited', True), cond('adult', True, 'neq')]}] + [   # 每套各一條會超過任務提示上限 16 條
                {'text': '肚子餓了，去點心籃', 'eventId': 'basket', 'conditions': [cond('hunger', HUNGRY_AT, 'gte')]}] + [
                {'text': '有黃金便便，去撿起來', 'eventId': k, 'conditions': [cond(k, True)]} for k in POOP_CELLS]
    m = {'version': 1, 'name': '皇家育嬰室', 'width': W, 'height': H, 'tileSize': 48,
         'tilesets': [{'id': 'kn-dungeon', 'name': '地城', 'url': 'https://pub-4b20b43f5acf4dfaa3f6ab842daa51cf.r2.dev/2d3b0242-9a6d-4051-9825-46aa4efd064a/larch/built-in-assets/packs/kenney-rpg/tilesets/1790278984532_tiny-dungeon.png', 'tileSize': 16, 'columns': 12, 'rows': 11}],
         'layers': [{'id': 'walk', 'name': '通行設定', 'visible': False, 'locked': False, 'collision': True, 'damage': 0, 'above': False,
                     'tiles': ['kn-dungeon:0' if (i % W, i // W) in walls() else None for i in range(W * H)]}],
         'events': [hero, intro, journal, clock, cap, floor, hungry, basket, toys, poop_timer, welcome, sulk, very, makeup_play, makeup_eat, gift, mirror] + restores + poops + grows + [hint] + bases + [invite, door], 'hp': 100, 'hpVariable': 'rpgHp', 'bagVariable': 'inventory', 'stateVariable': 'rpgState',
         'hideDesktopControls': False, 'combat': 'none', 'view': {'mode': '2d', 'tilt': 48, 'zoom': 1, 'depthOfField': 0, 'atmosphere': 'day'},
         'picture': {'url': ART['nursery']}, 'guidance': guidance,
         'environment': {'weather': 'clear', 'intensity': 0, 'darkness': 0, 'shake': 0, 'lights': [],
                         'ambience': {'particles': 'sparkles', 'density': 0.3, 'rays': 0.5, 'tint': '#FFF7EE', 'tintStrength': 0.2}}}
    if LAYERED: layered(m)
    names = list(VARS) + CROSS_VARS + [n for _, n, _, _ in RPG_VARS]
    return {'id': 'm-nursery', 'type': 'story', 'position': pos(), 'data': {
        'type': 'plugin', 'title': '皇家育嬰室', 'text': '', 'pluginId': 'larch-rpg-system', 'pluginCardId': 'map', 'pluginVersion': '0.4.0',
        'pluginName': 'RPG 系統', 'pluginCardName': 'RPG 地圖', 'pluginIcon': 'map', 'pluginColor': '#4a7358', 'pluginPresentation': 'fullscreen',
        'pluginFrame': {'showTitle': False, 'showButton': False}, 'pluginSkippable': False, 'pluginReadVars': names, 'pluginWriteVars': names,
        'pluginAssets': [], 'platforms': ['web'], 'pluginValues': {'map': json.dumps(m, ensure_ascii=False)},
        'bgm': BGM_HOME, 'bgmVolume': 0.35, 'bgmLoop': True}}

def layered(m):
    """分層版育嬰室：48×36 細格、純地面底圖、每件家具一個自由圖片事件（前後遮擋照圖框下緣排序）、碰撞照設計檔佔地格。
    互動點與便便位置照設計檔 points；現在底圖和家具都是色塊（scripts/layout.py），產完圖換成真的。"""
    d = layout.load('nursery'); Wn, Hn = d['map']['w'], d['map']['h']; pt = d['points']; wl = layout.walls(d)
    real = (ROOT / 'assets/art/objects/nursery/ground.webp').exists()   # 真圖產好（scripts/map_art.py）就用真圖，否則用色塊
    url = (lambda f: A + f'art/objects/nursery/{f}.png') if real else (lambda f: A + f'art/blocks/nursery/{f}.png')
    m.update(width=Wn, height=Hn, picture={'url': A + 'art/objects/nursery/ground.webp' if real else url('_ground')})
    m['layers'][0]['tiles'] = ['kn-dungeon:0' if (i % Wn, i // Wn) in wl else None for i in range(Wn * Hn)]
    at = {'hero': pt['hero_start'], 'intro': (pt['hero_start'][0], pt['hero_start'][1] + 6), **{k: pt[k] for k in POOP_CELLS},
          # 互動事件掛在家具的佔地格上，寵物從站點那一格靠近（站點在家具右邊或左邊一格）
          'mirror': (4, 12), 'journal': (7, 19), 'toys': (7, 27), 'basket': (34, 12), 'gift': (41, 26), 'door': (24, 35)}
    for e in m['events']:
        if e['id'] in at: e['x'], e['y'] = at[e['id']]
        e.pop('free', None) if e['id'] in ('basket', 'journal', 'gift') else None   # 點心籃是家具；日誌、禮物箱畫進糖果小桌、沙發（分開放會排在家具後面被蓋掉）
    hold = [(0, y) for y in range(1, Hn)] + [(Wn - 1, y) for y in range(1, Hn)]   # 家具事件放在地圖兩邊的邊界格（每格只能一個事件）
    obs = layout.objects(d); assert len(hold) >= len(obs)
    m['events'] += [ev(f'obj-{i}', *hold[i], name=o['name'], free={'url': url(o['name']), 'x': o['frame'][0], 'y': o['frame'][1], 'w': o['frame'][2], 'h': o['frame'][3]})
                    for i, o in enumerate(obs)]
    taken = {}
    for e in m['events']: assert (e['x'], e['y']) not in taken, f"{e['id']} 跟 {taken.get((e['x'], e['y']))} 同一格"; taken[(e['x'], e['y'])] = e['id']


def clock_plugin():
    """看不見的時鐘 HUD：記最後在場時間，讀檔時補上離線期間的飢餓與便便。直接寫 playback，玩家不必安裝。"""
    html = (ROOT / 'scripts/plugin/clock.html').read_text()
    for k, v in {'OFF_HUNGER_MS': OFF_HUNGER_MS, 'OFF_HUNGER_STEP': OFF_HUNGER_STEP, 'OFF_POOP_MS': OFF_POOP_MS, 'BEAT_MS': BEAT_MS, 'OUTFIT_IDS': json.dumps([v[0] for v in OUTFITS.values()] + [v[0] for v in FORMS.values()])}.items():
        html = html.replace(f'__{k}__', str(v))
    read = ['intro_done', 'last_seen', 'hunger', 'poop_a', 'poop_b', 'poop_c', 'rpgState', 'pet_name']
    hud = {'id': 'clock', 'title': '時鐘', 'anchor': 'bottom-left', 'width': 32, 'height': 32, 'offsetX': 0, 'offsetY': 0,
           'interactive': False, 'readVariables': read, 'writeVariables': ['last_seen', 'away_minutes', 'hunger', 'poop_a', 'poop_b', 'poop_c', 'pet_name', 'rpgState'], 'html': html}
    return {'enabled': True, 'playback': {'version': '0.1.0', 'permissions': ['player:ui', 'variables:read', 'variables:write'], 'defaults': {}, 'huds': [hud]}}


def database():
    def actor(id, sprite, role='party'):
        walk = walk_sprite(sprite)
        return {'id': id, 'name': '王子姬', 'title': '', 'profile': '', 'role': role, 'walk': walk, 'portrait': ART.get(sprite + '-still', ART[sprite]),   # walk 直接放 sprite 物件（包一層 {sprite} 引擎讀不到，會退回事件上的小人圖）
                'kit': 'none', 'rig': 'slime', 'joinVariable': '', **({'speed': 2} if LAYERED else {})}   # 細格一步只有半格，速度加倍手感不變
    # 造型＝另一個資料庫角色，換裝用 hero 步驟整個換掉（名字一樣叫王子姬）
    return {'version': 1, 'heroId': 'ph', 'leadSwitch': False,
            'actors': [actor('ph', 'slime')] + [actor(v[0], v[2], 'npc') for v in OUTFITS.values()] + [actor(v[0], v[2], 'npc') for v in FORMS.values()]}   # 造型角色要 npc：party 又沒 joinVariable 會被當成已同行的隊友

def build():
    p = json.loads((ROOT / 'skeleton/project.json').read_text())
    b = p['boards'][0]; N = b['nodes']; E = b['edges']
    for i, s in enumerate(STORY):
        N.append(story_card(*s))
    for c in CHOICES:
        N.append(choice_card(*c))
        E += [edge(c[0], dst, f'choice-{i}') for i, (_, dst) in enumerate(c[4])]
    N.append(nursery())
    # 開機分流（起點）：有條件的線先判，第一條無條件的當預設。同一出口兩條線，推送一定要走 PUT board（整包 PUT 會去重）
    N.insert(0, {'id': 'route', 'type': 'story', 'position': {'x': -400, 'y': 0}, 'data': {'type': 'setVariable', 'title': '開機分流', 'text': '', 'start': True,
                 'variableOps': [{'id': 'route-0', 'variable': 'booted', 'kind': 'set', 'value': 'true'}]}})
    E.append({**edge('route', 'm-nursery'), 'data': {'condition': {'kind': 'variable', 'variable': 'intro_done', 'op': 'eq', 'value': 'true'}}})
    N.append({'id': 'a-done', 'type': 'story', 'position': pos(), 'data': {'type': 'setVariable', 'title': '成年禮辦完', 'text': '',
              'variableOps': [{'id': 'a-done-0', 'variable': 'adult', 'kind': 'set', 'value': 'true'}]}})
    E.append({**edge('a-arena', 'a-prince'), 'data': {'condition': {'kind': 'variable', 'variable': 'form', 'op': 'eq', 'value': 'prince'}}})   # 有條件的線先判
    E.append(edge('a-arena', 'a-hime'))
    E += [edge(a, b2) for a, b2 in FLOW]
    by = {n['id']: n for n in N}
    home = False
    for n in N:   # 依劇情順序掛音樂：育嬰室之前用 sproutlight，之後用 dewdrops
        if n['id'] == HOME_BGM_FROM: home = True
        if n['id'] == 'a-arena': n['data'].update(bgm=BGM_STORY, bgmVolume=0.45, bgmLoop=True); continue   # 成年禮用序章的音樂，回育嬰室由地圖卡換回
        if n['data']['type'] != 'plugin' and n['id'] in ('p-capital', HOME_BGM_FROM):
            n['data'].update(bgm=BGM_HOME if home else BGM_STORY, bgmVolume=0.45, bgmLoop=True)
    p['nodes'], p['edges'] = N, E
    p['variables'] = ([{'id': k, 'name': k, 'label': lab, 'type': t, 'defaultValue': d} for k, (t, d, lab) in VARS.items()]
                      + [{'id': i, 'name': n, 'label': RPG_LABELS.get(n, n), 'type': t, 'defaultValue': d} for i, n, t, d in RPG_VARS])
    p['variables'] += [{'id': f'rpg-{n}', 'name': n, 'label': n, 'type': 'string', 'scope': 'project',
                        'defaultValue': 'true' if n[6:] in CROSS_TEST else ''} for n in CROSS_VARS]
    for v in p['variables']:
        if v['name'] in PERSIST: v['persistent'] = True
    s = p['settings']
    s['plugins']['prince-hime'] = clock_plugin()
    rpg = s['plugins']['larch-rpg-system']['settings']
    rpg['database'] = json.dumps(database(), ensure_ascii=False)
    # 狀態靠跨週目變數保留，選單不放存檔／讀檔：讀舊檔和跨週目值打架的情況就不會發生
    rpg['menuUi'] = json.dumps({'preset': 'sakura', 'buttons': ['status', 'bag', 'settings', 'title']}, ensure_ascii=False)
    rpg['items'] = json.dumps([{'id': 'coin', 'name': '王室金幣', 'icon': ART['coin'], 'note': '黃金便便換來的金幣。', 'heal': 0,
                                'bag': {'consumable': False, 'effectKind': 'none', 'effectVar': '', 'effectValue': '',
                                        'useConditionVariable': '', 'useConditionValue': '', 'useConditionMessage': ''}}]
                              + [{'id': f'cx-{k}', 'name': name, 'note': f'從《{WORKS[work]}》送來的。{line}', 'heal': 0, 'crossProject': work, 'crossRef': ref,
                                  'crossWork': WORKS[work], 'crossLater': True, 'crossVar': f'cross_{k}'} for k, work, ref, name, place, line, _ in CROSS], ensure_ascii=False)
    s.update(titleCoverImage=ART['cover'], projectThumbnail=ART['cover'], stageFit='auto', keepActorsInFrame=False, titleScreenEnabled=True,
             titleScreen={'bgm': BGM_HOME, 'bgmVolume': 0.35, 'layers': [
                 {'x': 76, 'y': 88, 'id': 'action-start', 'icon': True, 'kind': 'button', 'size': 1.25, 'width': 22, 'action': 'start', 'text': '進入王宮', 'label': '進入王宮'}]})
    s['customInterfaces'] = ui.skin()   # 介面 Skills：小島日和改成王子姬色系（scripts/ui.py；標題沿用上面的 titleScreen）
    assert {e['target'] for e in E} <= set(by) and {e['source'] for e in E} <= set(by), '有連線指到不存在的卡'
    return p

def main():
    p = build()
    out = ROOT / 'dist/project.json'; out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(p, ensure_ascii=False))
    dst = out.parent / 'assets'   # serve.py 不跟符號連結，用硬連結鏡像 assets
    shutil.rmtree(dst, ignore_errors=True)
    def link(a, b):
        try: os.link(a, b)
        except OSError: shutil.copy2(a, b)
    shutil.copytree(ROOT / 'assets', dst, copy_function=link)
    print('wrote', out, len(p['nodes']), 'cards')

if __name__ == '__main__':
    main()
