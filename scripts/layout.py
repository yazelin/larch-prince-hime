"""分層地圖設計檔（art/objects_<名>.yaml）→ 物件、碰撞、色塊。照《仙泉．香布纏．續》xu/game 的 layout.py＋blocks.py（2026-10-08 作者：地圖照那套流程做）。
單位細格；引擎前後順序：自由圖片用 free.y+free.h-1、人用自己站的列，小的先畫，同值圖片先畫。
所以每個物件的圖框下緣＝佔地最下一列的下緣：站在南邊的寵物畫在上面，站在圖框裡北邊的被蓋住。碰撞照佔地格，不用 free.block。
用法：python3 scripts/layout.py nursery   → assets/art/blocks/nursery/*.png＋art/check/blocks-nursery-plan.png"""
import pathlib, sys, yaml
from PIL import Image, ImageDraw, ImageFont
ROOT = pathlib.Path(__file__).resolve().parent.parent
PX = 24   # 色塊每細格幾 px（引擎照 free 的格數縮放，不需要高解析）
FONT = lambda s: ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', s)
GROUND = {'border': (60, 50, 50), 'floor': (214, 170, 110), 'rug': (245, 238, 225), 'rug2': (240, 200, 205), 'mat': (150, 185, 220), 'wall': (225, 215, 195)}
KIND = {'牆': (225, 215, 195), '櫃': (190, 150, 120), '盆栽': (90, 150, 90), '鏡': (240, 160, 170), '凳': (235, 150, 170), '桌': (210, 180, 120),
        '箱': (120, 170, 210), '床': (245, 200, 210), '籃': (200, 150, 90), '沙發': (235, 220, 200), '墊': (240, 150, 140), '欄杆': (250, 250, 245)}


def load(name):
    return yaml.safe_load((ROOT / f'art/objects_{name}.yaml').read_text(encoding='utf-8'))


def objects(d):
    for o in d['objects']:
        x, y, w, h = o['foot']; up = o.get('up', 0)
        o['frame'] = (x, y - up, w, h + up); o['sort'] = y + h - 1
    return d['objects']


def foot_cells(o):
    x, y, w, h = o['foot']
    return {(i, j) for j in range(y, y + h) for i in range(x, x + w)}


def walls(d):
    out = set()
    for g in d['ground']:
        if g['kind'] == 'border' or g.get('block'):
            for x, y, w, h in g['rects']: out |= {(i, j) for j in range(y, y + h) for i in range(x, x + w)}
    for o in objects(d): out |= foot_cells(o)
    return out


def check(d):
    W, H = d['map']['w'], d['map']['h']; obs = objects(d); errs = []; seen = {}
    for o in obs:
        fx, fy, fw, fh = o['frame']
        if fx < 0 or fy < 0 or fx + fw > W or fy + fh > H: errs.append(f"{o['name']} 圖框出界 {o['frame']}")
        for c in foot_cells(o):
            if c in seen: errs.append(f"{o['name']} 跟 {seen[c]} 佔地重疊 {c}")
            seen[c] = o['name']
    for o in obs:   # 整個落在排得比較後面的物件圖框裡：會被完全蓋掉
        ox, oy, ow, oh = o['frame']
        for q in obs:
            if q is o or q['sort'] <= o['sort']: continue
            qx, qy, qw, qh = q['frame']
            if qx <= ox and qy <= oy and ox + ow <= qx + qw and oy + oh <= qy + qh: errs.append(f"{o['name']} 整個落在 {q['name']} 的圖框裡")
    wl = walls(d)
    for k in d['walk_points']:
        if tuple(d['points'][k]) in wl: errs.append(f"站點 {k} {d['points'][k]} 在牆上")
    return errs


def block(o):
    """一個物件一張：佔地深色、往上長的部分淺色加斜線（不佔地），標名字"""
    fx, fy, fw, fh = o['frame']; x, y, w, h = o['foot']; c = KIND[o['kind']]
    im = Image.new('RGBA', (fw * PX, fh * PX)); dr = ImageDraw.Draw(im)
    if y > fy: dr.rectangle((0, 0, fw * PX - 1, (y - fy) * PX - 1), fill=tuple(min(255, int(v * 1.1 + 20)) for v in c) + (225,))
    for k in range(-fh * PX, fw * PX, 10): dr.line((k, 0, k + fh * PX, fh * PX), fill=(255, 255, 255, 80), width=2)
    dr.rectangle((0, (y - fy) * PX, fw * PX - 1, fh * PX - 1), fill=tuple(int(v * .7) for v in c) + (240,))
    dr.rectangle((0, 0, fw * PX - 1, fh * PX - 1), outline=(255, 255, 255, 255), width=2)
    dr.text((3, 2), o['name'], fill=(255, 255, 255, 255), font=FONT(14), stroke_width=2, stroke_fill=(0, 0, 0, 255))
    return im


def ground(d):
    W, H = d['map']['w'], d['map']['h']
    im = Image.new('RGB', (W * PX, H * PX), GROUND['floor']); dr = ImageDraw.Draw(im)
    for g in d['ground']:
        for x, y, w, h in g['rects']: dr.rectangle((x * PX, y * PX, (x + w) * PX - 1, (y + h) * PX - 1), fill=GROUND[g['kind']])
    for x in range(W): dr.line((x * PX, 0, x * PX, H * PX), fill=(150, 130, 110))
    for y in range(H): dr.line((0, y * PX, W * PX, y * PX), fill=(150, 130, 110))
    return im


def plan(d, gim):
    """整張設計圖：格線、佔地（實色）、圖框（白框）、排序列（紅線）、站點（黃點）"""
    W, H = d['map']['w'], d['map']['h']; S = 30
    im = gim.resize((W * S, H * S), Image.NEAREST).convert('RGBA'); lay = Image.new('RGBA', im.size); dr = ImageDraw.Draw(lay); f = FONT(13)
    for o in objects(d):
        fx, fy, fw, fh = o['frame']
        dr.rectangle((fx * S, fy * S, (fx + fw) * S - 1, (fy + fh) * S - 1), outline=(255, 255, 255, 230), width=1)
        for (i, j) in foot_cells(o): dr.rectangle((i * S + 1, j * S + 1, (i + 1) * S - 2, (j + 1) * S - 2), fill=KIND[o['kind']] + (200,))
        dr.line((fx * S, (o['sort'] + 1) * S - 1, (fx + fw) * S, (o['sort'] + 1) * S - 1), fill=(255, 60, 60, 255), width=2)
        dr.text((fx * S + 2, fy * S + 1), o['name'], fill=(255, 255, 255, 255), font=f, stroke_width=2, stroke_fill=(0, 0, 0, 255))
    for k in d['walk_points']:
        x, y = d['points'][k]
        dr.ellipse((x * S + 6, y * S + 6, x * S + S - 6, y * S + S - 6), fill=(255, 220, 0, 255))
        dr.text((x * S + S, y * S + 2), k, fill=(255, 240, 120, 255), font=f, stroke_width=2, stroke_fill=(0, 0, 0, 255))
    for x in range(0, W, 2): dr.text((x * S + 2, 2), str(x), fill=(255, 255, 255, 255), font=f, stroke_width=2, stroke_fill=(0, 0, 0, 255))
    for y in range(0, H, 2): dr.text((2, y * S + 2), str(y), fill=(255, 255, 255, 255), font=f, stroke_width=2, stroke_fill=(0, 0, 0, 255))
    im.alpha_composite(lay); return im.convert('RGB')


def main(name):
    d = load(name); errs = check(d)
    if errs: raise SystemExit('設計檔有問題：\n' + '\n'.join(errs))
    od = ROOT / f'assets/art/blocks/{name}'; od.mkdir(parents=True, exist_ok=True)
    for f in od.iterdir(): f.unlink()
    g = ground(d); g.save(od / '_ground.png')
    for o in objects(d): block(o).save(od / f"{o['name']}.png")
    (ROOT / 'art/check').mkdir(exist_ok=True); plan(d, g).save(ROOT / f'art/check/blocks-{name}-plan.png')
    print('OK', len(d['objects']), '個物件', ROOT / f'art/check/blocks-{name}-plan.png')


if __name__ == '__main__':
    # 自我檢查的負控制：重疊的佔地、站在牆上的點要被抓到
    bad = {'map': {'w': 10, 'h': 10}, 'ground': [], 'points': {'p': [1, 1]}, 'walk_points': ['p'],
           'objects': [{'name': 'a', 'kind': '桌', 'foot': [0, 0, 3, 3]}, {'name': 'b', 'kind': '桌', 'foot': [2, 2, 2, 2]}]}
    e = check(bad); assert any('重疊' in x for x in e) and any('在牆上' in x for x in e), e
    main(sys.argv[1] if len(sys.argv) > 1 else 'nursery')
