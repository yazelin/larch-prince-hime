"""組出 dist/project.json：序章（劇情卡）＋培育室地圖。劇本就寫在這個檔裡。
用法：python3 scripts/build.py && python3 ~/larch-preview/serve.py dist/project.json"""
import json, pathlib, itertools, os, shutil
ROOT = pathlib.Path(__file__).resolve().parent.parent
import sys
# 圖片網址：本機預覽用 /files/assets/（serve.py 從 dist/ 提供）；推上 Larch 用 jsDelivr，釘在已 push 的 commit SHA 上，換圖不會卡快取
CDN_SHA = next((a.split('=', 1)[1] for a in sys.argv if a.startswith('--cdn=')), '')
A = f'https://cdn.jsdelivr.net/gh/yazelin/larch-prince-hime@{CDN_SHA}/assets/' if CDN_SHA else '/files/assets/'
R2 = 'https://pub-4b20b43f5acf4dfaa3f6ab842daa51cf.r2.dev/2d3b0242-9a6d-4051-9825-46aa4efd064a/larch/built-in-assets/audio/larch-creatures/'
BGM_STORY, BGM_HOME = R2 + '1784841727962_sproutlight-path.mp3', R2 + '1784841721002_dewdrops-heart.mp3'
ART = {k: A + 'art/' + v for k, v in {
    'capital': 'bg/capital.webp', 'courtyard': 'bg/courtyard.webp', 'egg-feet': 'cg/egg-feet.webp', 'throne': 'bg/throne.webp',
    'hatch': 'cg/hatch.webp', 'egg-rug': 'cg/egg-rug.webp', 'king': 'portrait/king.webp', 'journal': 'props/journal.webp', 'nursery': 'maps/nursery.webp',
    'slime': 'walk/slime-daily.webp'}.items()}
ART['cover'] = A + 'cover/cover-v3.webp'   # 封面沿用 assets/cover，不另存一份
KING = '國王'
VARS = {'saved_once': ('boolean', False, '寫過第一頁日誌'), 'intro_done': ('boolean', False, '看完培育室開場')}
RPG_VARS = [('hp', 'rpgHp', 'number', 100), ('bag', 'inventory', 'string', '[]'), ('equipment', 'rpgEquipment', 'string', '{}'),
            ('state', 'rpgState', 'string', ''), ('used', 'inventoryLastUsed', 'string', ''), ('count', 'inventoryCount', 'number', 0)]

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
]
# 選項卡：(id, 標題, 背景, 問句, [(選項, 去哪張卡)])
CHOICES = [
    ('c-egg', '蛋停在腳邊', 'egg-feet', '蛋停在你腳邊，晃了兩下。', [('撿起來', 'p-pickup'), ('假裝沒看到，繼續掃地', 'p-ignore')]),
    ('c-king', '國王看著你', 'throne', '國王看著你。', [('可是我只是來掃落葉的……', 'p-reluctant'), ('我會好好照顧牠。', 'p-willing')]),
    ('c-poke', '光點', 'egg-rug', '要怎麼做？', [('輕輕戳一下', 'p-poke'), ('先等等看', 'p-wait')]),
]
FLOW = [('p-capital', 'p-courtyard'), ('p-courtyard', 'c-egg'), ('p-ignore', 'p-throne'), ('p-pickup', 'p-throne'),
        ('p-throne', 'c-king'), ('p-reluctant', 'p-rules'), ('p-willing', 'p-rules'), ('p-rules', 'p-nursery'),
        ('p-nursery', 'c-poke'), ('p-poke', 'p-hatch'), ('p-wait', 'p-hatch'), ('p-hatch', 'm-nursery')]
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
def say(t, speaker='narrator', pres='text'): return act('dialogue', text=t, presentation=pres, speaker=speaker)
def setv(k, v): return act('variable', variable=k, value=str(v).lower() if isinstance(v, bool) else str(v))
def cond(k, v, op='eq'): return {'kind': 'variable', 'variable': k, 'op': op, 'value': str(v).lower() if isinstance(v, bool) else str(v), 'itemId': '', 'count': 1}
INVISIBLE = {'url': '', 'width': 32, 'height': 32, 'frames': 1, 'rows': 1, 'offsetX': 0, 'offsetY': 0, 'idleFrame': 0}
def ev(id, x, y, **kw):
    e = {'id': id, 'name': id, 'x': x, 'y': y, 'actor': 'none', 'trigger': 'action', 'movement': 'still', 'solid': False,
         'once': False, 'conditions': [], 'actions': [], 'direction': 'down', 'sprite': INVISIBLE}
    e.update(kw); return e

W, H = 24, 18
def walls():
    # ponytail: 依 nursery.webp 目測框出擋路的家具，換地圖圖要重框
    rects = [(0, 0, 23, 1),            # 上牆
             (0, 2, 4, 6), (1, 7, 3, 10), (0, 11, 5, 17),      # 左：貝殼鏡與小凳、植物小桌、玩具箱
             (17, 0, 23, 4), (19, 5, 23, 7), (20, 8, 23, 17),  # 右：嬰兒床、邊桌、沙發
             (0, 17, 23, 17)]          # 下緣欄杆
    return {(x, y) for x0, y0, x1, y1 in rects for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)}

def nursery():
    hero = ev('hero', 12, 9, actor='player', actorId='ph', direction='down',
              sprite={'url': ART['slime'], 'width': 128, 'height': 128, 'frames': 1, 'rows': 1, 'offsetX': 0, 'offsetY': 0, 'idleFrame': 0, 'scale': 3, 'faces': 'right'})
    intro = ev('intro', 12, 12, trigger='auto', once=True, actions=[
        act('name', text='幫牠取個名字吧。', naming={'who': '', 'max': 8}),
        say('噗啾！', speaker='player', pres='bubble'),
        say('{{hero}}好像很喜歡這個名字。'),
        say('房間左邊的小桌子上，放著一本王室日誌。'),
        say('照顧完{{hero}}，記得去寫一頁。沒寫進日誌的日子，下次回來就不算數。'),
        setv('intro_done', True)])
    journal = ev('journal', 3, 9, solid=True,   # 書放在植物旁的小桌上，小人站在 (4,9) 不會蓋住它
                 free={'url': ART['journal'], 'x': 1.9, 'y': 7.9, 'w': 1.3, 'h': 1.3},
                 marker={'label': '王室日誌', 'kind': 'talk'}, actions=[
        act('dialogue', text='王室日誌。今天的事要寫進去嗎？', presentation='text', speaker='narrator', confirm={'accept': '寫進去', 'cancel': '等一下'}),
        setv('saved_once', True),   # 要在存檔前設好，存下來的那一刻才會是「寫過了」，讀檔回來任務提示才會收掉
        act('save'),
        say('寫好了。{{hero}}在旁邊打了一個小呵欠。')])
    guidance = [{'text': '去王室日誌寫下第一頁', 'eventId': 'journal', 'conditions': [cond('intro_done', True), cond('saved_once', True, 'neq')]}]
    m = {'version': 1, 'name': '皇家育嬰室', 'width': W, 'height': H, 'tileSize': 48,
         'tilesets': [{'id': 'kn-dungeon', 'name': '地城', 'url': 'https://pub-4b20b43f5acf4dfaa3f6ab842daa51cf.r2.dev/2d3b0242-9a6d-4051-9825-46aa4efd064a/larch/built-in-assets/packs/kenney-rpg/tilesets/1790278984532_tiny-dungeon.png', 'tileSize': 16, 'columns': 12, 'rows': 11}],
         'layers': [{'id': 'walk', 'name': '通行設定', 'visible': False, 'locked': False, 'collision': True, 'damage': 0, 'above': False,
                     'tiles': ['kn-dungeon:0' if (i % W, i // W) in walls() else None for i in range(W * H)]}],
         'events': [hero, intro, journal], 'hp': 100, 'hpVariable': 'rpgHp', 'bagVariable': 'inventory', 'stateVariable': 'rpgState',
         'hideDesktopControls': False, 'combat': 'none', 'view': {'mode': '2d', 'tilt': 48, 'zoom': 1, 'depthOfField': 0, 'atmosphere': 'day'},
         'picture': {'url': ART['nursery']}, 'guidance': guidance,
         'environment': {'weather': 'clear', 'intensity': 0, 'darkness': 0, 'shake': 0, 'lights': [],
                         'ambience': {'particles': 'sparkles', 'density': 0.3, 'rays': 0.5, 'tint': '#FFF7EE', 'tintStrength': 0.2}}}
    names = list(VARS) + [n for _, n, _, _ in RPG_VARS]
    return {'id': 'm-nursery', 'type': 'story', 'position': pos(), 'data': {
        'type': 'plugin', 'title': '皇家育嬰室', 'text': '', 'pluginId': 'larch-rpg-system', 'pluginCardId': 'map', 'pluginVersion': '0.4.0',
        'pluginName': 'RPG 系統', 'pluginCardName': 'RPG 地圖', 'pluginIcon': 'map', 'pluginColor': '#4a7358', 'pluginPresentation': 'fullscreen',
        'pluginFrame': {'showTitle': False, 'showButton': False}, 'pluginSkippable': False, 'pluginReadVars': names, 'pluginWriteVars': names,
        'pluginAssets': [], 'platforms': ['web'], 'pluginValues': {'map': json.dumps(m, ensure_ascii=False)},
        'bgm': BGM_HOME, 'bgmVolume': 0.35, 'bgmLoop': True}}

def database():
    walk = {'url': ART['slime'], 'width': 128, 'height': 128, 'frames': 1, 'rows': 1, 'offsetX': 0, 'offsetY': 0, 'idleFrame': 0, 'scale': 3, 'faces': 'right'}
    return {'version': 1, 'heroId': 'ph', 'leadSwitch': False, 'actors': [
        {'id': 'ph', 'name': '王子姬', 'title': '', 'profile': '', 'role': 'party', 'walk': {'sprite': walk}, 'portrait': ART['slime'],
         'kit': 'none', 'rig': 'slime', 'joinVariable': ''}]}

def build():
    p = json.loads((ROOT / 'skeleton/project.json').read_text())
    b = p['boards'][0]; N = b['nodes']; E = b['edges']
    for i, s in enumerate(STORY):
        N.append(story_card(*s))
        if i == 0: N[-1]['data']['start'] = True
    for c in CHOICES:
        N.append(choice_card(*c))
        E += [edge(c[0], dst, f'choice-{i}') for i, (_, dst) in enumerate(c[4])]
    N.append(nursery())
    E += [edge(a, b2) for a, b2 in FLOW]
    by = {n['id']: n for n in N}
    home = False
    for n in N:   # 依劇情順序掛音樂：育嬰室之前用 sproutlight，之後用 dewdrops
        if n['id'] == HOME_BGM_FROM: home = True
        if n['data']['type'] != 'plugin' and n['id'] in ('p-capital', HOME_BGM_FROM):
            n['data'].update(bgm=BGM_HOME if home else BGM_STORY, bgmVolume=0.45, bgmLoop=True)
    p['nodes'], p['edges'] = N, E
    p['variables'] = ([{'id': k, 'name': k, 'label': lab, 'type': t, 'defaultValue': d} for k, (t, d, lab) in VARS.items()]
                      + [{'id': i, 'name': n, 'label': n, 'type': t, 'defaultValue': d} for i, n, t, d in RPG_VARS])
    s = p['settings']
    s['plugins']['larch-rpg-system']['settings']['database'] = json.dumps(database(), ensure_ascii=False)
    s.update(titleCoverImage=ART['cover'], projectThumbnail=ART['cover'], stageFit='auto', keepActorsInFrame=False, titleScreenEnabled=True,
             titleScreen={'bgm': BGM_HOME, 'bgmVolume': 0.35, 'layers': [
                 {'x': 76, 'y': 84, 'id': 'action-start', 'icon': True, 'kind': 'button', 'size': 1.25, 'width': 22, 'action': 'start', 'text': '王子姬的故事', 'label': '王子姬的故事'},
                 {'x': 76, 'y': 90.5, 'id': 'action-continue', 'icon': True, 'kind': 'button', 'size': 1.25, 'width': 22, 'action': 'continue', 'text': '回到培育室', 'label': '回到培育室'}]})
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
