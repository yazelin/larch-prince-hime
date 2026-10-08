"""介面 Skills：拿官方「小島日和」當底，顏色換成王子姬色系（docs/05 的馬卡龍定色）。
官方原檔不進 repo：第一次跑會從測試沙盒（作者在網頁套用過小島日和）讀到 art/ui-ref/（已 gitignore）。
build.py 呼叫 skin() 把結果放進 settings.customInterfaces；只做對話、選項、選單、RPG 四塊，標題沿用本作自己的。"""
import json, os, pathlib, re, urllib.request
ROOT = pathlib.Path(__file__).resolve().parent.parent
REF = ROOT / 'art/ui-ref'
SANDBOX = 'project-5aae449c-12f0-46d3-8c2c-dbcde62b0769'
SURFACES = ('dialogue', 'choices', 'menu', 'rpg')

# 小島日和 → 王子姬。左邊是官方用到的色，右邊是 docs/05：燕麥奶白、蜜桃暖粉、蜂蜜奶黃、薄荷粉綠、晨霧天藍，字用暖可可棕
HEX = {
    # 字與深色
    '#4a3526': '#6b4a3a', '#3a2718': '#5a3d30', '#6e5442': '#8a6a58', '#6e5a46': '#8a6a58', '#5f4c3a': '#7a5a4a', '#8a7560': '#a08474',
    # 紙
    '#fffaf0': '#fff9f2', '#fffdf6': '#fffcf8', '#fdf3df': '#fff3ea', '#fff8e0': '#fff6e8', '#f7efdf': '#fbf1ea',
    # 葉子綠（主色）→ 蜜桃
    # 小島日和拿深綠同時當邊框與小標字，換成的深玫瑰棕在奶白上要 4.5:1 以上
    '#2f6b34': '#a8504c', '#1f3a1c': '#6a2f2c', '#7cc96a': '#f4a7a3', '#eaf7df': '#ffe9e6',
    # 黃 → 蜂蜜金
    '#fff1c2': '#fff1cc', '#ffd666': '#f2c66d', '#ffc94a': '#e8b85c', '#fff3b0': '#ffe8a3', '#a87b3c': '#c99a5b',
    # 珊瑚與粉
    '#ff9f86': '#f4a7a3', '#ffc2d4': '#ffd3d0',
    # 天藍 → 晨霧藍
    '#9bd7ef': '#a9d3f0', '#bfe6f5': '#c4e2f8', '#dff1f8': '#d8eefe', '#e3f3fa': '#e3f2fe', '#e6f5fb': '#ecf6ff',
    '#1f4a66': '#4a6a8a', '#2f7fa6': '#6a93b8',
}
RGB = {  # rgba() 裡的同一批顏色
    (74, 53, 38): (107, 74, 58), (31, 58, 28): (106, 47, 44), (47, 107, 52): (168, 80, 76), (255, 250, 240): (255, 249, 242),
    (255, 214, 102): (242, 198, 109), (155, 215, 239): (169, 211, 240), (243, 140, 120): (244, 167, 163), (30, 50, 25): (90, 50, 45),
    (30, 50, 20): (90, 50, 45), (20, 40, 20): (80, 40, 38), (223, 241, 248): (216, 238, 254),
}


def fetch():
    key = open(os.path.expanduser('~/.config/larch/key')).read().strip()
    r = urllib.request.urlopen(urllib.request.Request(f'https://larch.ink/api/agent/projects/{SANDBOX}', headers={'Authorization': 'Bearer ' + key}), timeout=30)
    p = json.load(r); p = p.get('project', p); ci = p['settings']['customInterfaces']
    REF.mkdir(parents=True, exist_ok=True)
    for k in SURFACES:
        assert ci[k]['skin']['id'] == 'skill-island-days', f'沙盒的 {k} 不是小島日和'
        (REF / f'{k}.html').write_text(ci[k]['html'])


def recolor(t):
    t = re.sub(r'#[0-9a-fA-F]{6}\b', lambda m: HEX.get(m.group(0).lower(), m.group(0)), t)
    def rgba(m):
        c = tuple(int(x) for x in m.group(2).split(','))
        return f'{m.group(1)}({",".join(map(str, RGB.get(c, c)))}{m.group(3)}'
    return re.sub(r'(rgba?)\((\d+,\s*\d+,\s*\d+)([,)])', lambda m: rgba(re.match(r'(rgba?)\((\d+,\d+,\d+)([,)])', m.group(0).replace(' ', ''))), t)


def skin():
    if not all((REF / f'{k}.html').exists() for k in SURFACES): fetch()
    return {k: {'enabled': True, 'html': recolor((REF / f'{k}.html').read_text()),
                'skin': {'id': 'prince-hime-island', 'name': '王子姬・小島日和改色', 'author': 'Larch（小島日和）＋王子姬', 'version': '1.0'}}
            for k in SURFACES}


def contrast(a, b):
    def lum(h):
        c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        c = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in c]
        return .2126 * c[0] + .7152 * c[1] + .0722 * c[2]
    x, y = sorted((lum(a), lum(b)))
    return (y + .05) / (x + .05)


if __name__ == '__main__':
    # 對比（規格書要求文字 4.5:1）：字色 × 底色，小島日和原本的配對換色後要照樣過
    for fg, bg in (('#6b4a3a', '#fff9f2'), ('#8a6a58', '#fff9f2'), ('#a8504c', '#fff9f2'), ('#6a2f2c', '#f4a7a3'), ('#5a3d30', '#f4a7a3'), ('#5a3d30', '#f2c66d')):
        assert contrast(fg, bg) >= 4.5, (fg, bg, round(contrast(fg, bg), 2))
    assert recolor('a{color:#2F6B34;background:rgba(74, 53, 38,.4)}') == 'a{color:#a8504c;background:rgba(107,74,58,.4)}', recolor('a{color:#2F6B34;background:rgba(74, 53, 38,.4)}')
    s = skin(); left = set()
    for v in s.values(): left |= {m.lower() for m in re.findall(r'#[0-9a-fA-F]{6}\b', v['html'])} & {'#2f6b34', '#7cc96a', '#1f3a1c', '#ffd666'}
    assert not left, left
    print('OK', {k: len(v['html']) for k, v in s.items()})
