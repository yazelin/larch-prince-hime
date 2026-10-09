"""art/raw → assets/art：背景放大成 1920×1080 webp；國王與日誌綠幕去背後切開；小人縮成 128px。"""
import pathlib, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW, OUT = ROOT / 'art/raw', ROOT / 'assets/art'
CUT = pathlib.Path.home() / '.claude/skills/cutout/cutout.py'
WIDE = {'bg-capital': 'bg/capital.webp', 'bg-courtyard': 'bg/courtyard.webp', 'bg-throne': 'bg/throne.webp',
        'cg-egg-feet': 'cg/egg-feet.webp', 'cg-hatch': 'cg/hatch.webp', 'cg-egg-rug': 'cg/egg-rug.webp',
        'bg-arena': 'bg/arena.webp', 'cg-adult-prince': 'cg/adult-prince.webp', 'cg-adult-hime': 'cg/adult-hime.webp'}


def resize_pm(im, size):
    """premultiplied alpha 縮放，避免幕色混回邊緣。"""
    f = np.asarray(im.convert('RGBA'), np.float32); al = f[..., 3:4] / 255
    pre = np.concatenate([f[..., :3] * al, f[..., 3:4]], -1)
    r = np.asarray(Image.fromarray(pre.round().astype(np.uint8), 'RGBA').resize(size, Image.LANCZOS), np.float32)
    al2 = np.clip(r[..., 3:4] / 255, 1e-4, 1)
    return Image.fromarray(np.concatenate([np.clip(r[..., :3] / al2, 0, 255), r[..., 3:4]], -1).round().astype(np.uint8), 'RGBA')


def square(im, pad=0.06):
    a = np.asarray(im); ys, xs = np.where(a[..., 3] > 10)
    b = im.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)); s = max(b.size); p = int(s * pad); S = s + 2 * p
    c = Image.new('RGBA', (S, S), (0, 0, 0, 0)); c.paste(b, ((S - b.width) // 2, S - p - b.height)); return c


LUBU = 'baihua'   # 呂布造型：baihua 百花戰袍／heijin 黑金戰甲


# 造型小人身體（奶白圓頂在眼睛那一列）的寬度與中心 x，量的是去背後的 pendant-*-cut.png（玉珮版沒動構圖，跟 outfit-*-cut.png 一樣；1254px）。
# ponytail: 手量的校正表；自動量會被兵器桿、髮繩、披風干擾（試過兩種都差到 3 成）。重產哪張就重量哪張
BODY_PX = {'lubu-baihua': (585, 580), 'lubu-heijin': (540, 520), 'liubei': (640, 588), 'guanyu': (581, 608), 'zhangfei': (572, 570), 'diaochan': (600, 615),
           'weixu': (607, 643), 'quan': (570, 593), 'xiang': (646, 651)}   # 呂荃右半身被頭髮蓋住，寬度照眼距推的
# 玉珮圓盤（圓心 x、y、半徑），量的是 pendant-*-cut.png；翻面時把這一圈換回沒翻過的，字才不會變鏡像字
BADGE = {'lubu-baihua': (612, 1058, 53), 'liubei': (594, 991, 58), 'guanyu': (572, 1063, 52), 'zhangfei': (617, 1027, 45), 'diaochan': (707, 877, 42),
         'weixu': (598, 1018, 56), 'quan': (657, 1043, 46), 'xiang': (599, 1014, 96)}
FORM_PX = {'prince': (790, 638), 'hime': (745, 612)}   # 分化後兩隻的身體寬與中心 x（眼睛那一列，form-*-cut.png 手量）
ART_LEFT = {'lubu-baihua', 'lubu-heijin', 'liubei', 'guanyu', 'weixu', 'quan', 'xiang'}   # 圖上朝左的造型（作者實際走過看的），其餘朝右
# 小人大小（2026-10-08 作者要縮回正常大小，原本身體約兩格、放大後糊）：身體約一格寬。
# 引擎顯示寬度＝sprite.scale 格（不管圖幾 px），1920 寬視窗一格約 80 螢幕 px；build.py 把 scale 設成 圖寬/80，圖 1 px＝螢幕 1 px 才不糊
DAILY = 116   # 平常那隻的圖寬（原圖身體佔 88/128）
BODY = 80     # 身體寬度，造型都縮到一樣寬


def extent(im, cx):
    """以身體中心為準，左右各要多寬（取大的一邊×2）與整體高度。"""
    ys, xs = np.where(np.asarray(im)[..., 3] > 10)
    return 2 * max(cx - xs.min(), xs.max() - cx), ys.max() - ys.min() + 1


# 造型是四列走路圖，引擎會在腳下畫陰影（rows===4 才畫；中心在格子 0.93 處、寬只有約 0.7 格，細格地圖上更小）。
# 身體底留 7px 會像浮在陰影上（2026-10-08 作者：換完造型陰影離得更遠）→ 造型只留 2px，身體壓在陰影中心
SHADOW_GAP = 2


def ground(f, gap=7):
    """整張上下平移，讓身體底部（中間六成寬每一欄最低點的中位數，細的兵器桿、流蘇不算）離畫布底邊 gap px，
    跟平常那隻一樣；本來用最低的像素對齊，兵器尾端比身體低的那幾隻就浮起來。比身體低超過 gap 的兵器尾端會被裁掉。"""
    a = np.asarray(f)[..., 3] > 128; S = f.width
    low = [np.where(a[:, x])[0].max() for x in range(int(S / 2 - 0.3 * BODY), int(S / 2 + 0.3 * BODY)) if a[:, x].any()]
    g = Image.new('RGBA', f.size); g.alpha_composite(f, (0, f.height - 1 - gap - int(np.median(low)))); return g


# 走路動畫：引擎移動時輪播同一列的幾格，停下來看 idleFrame（第 1 格）。果凍彈跳＝原樣→壓扁→拉高往上跳→離地一點
# ponytail: 用同一張圖縮放位移做四格，沒有重新生圖；要更生動（眨眼、晃王冠）再畫真的走路格
HOP = ((1, 1, 0), (1.08, .9, 0), (.95, 1.07, .035), (1, 1, .015))   # (寬倍率, 高倍率, 往上跳幾成畫布)


def hop(f):
    """一格變四格：以底邊中點為準縮放，再往上提。"""
    ys, xs = np.where(np.asarray(f)[..., 3] > 10); S = f.width
    box = f.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)); cx = (xs.min() + xs.max() + 1) / 2
    out = []
    for sx, sy, lift in HOP:
        r = resize_pm(box, (round(box.width * sx), round(box.height * sy)))
        g = Image.new('RGBA', f.size); g.alpha_composite(r, (round(cx - (cx - xs.min()) * sx), ys.max() + 1 - r.height - round(lift * S))); out.append(g)
    return out


def strip(rows):
    """每列一個方向、每列四格（HOP）。"""
    S = rows[0].width; sheet = Image.new('RGBA', (S * len(HOP), S * len(rows)))
    for j, f in enumerate(rows):
        for i, g in enumerate(hop(f)): sheet.paste(g, (i * S, j * S))
    return sheet


def mirror(im, badge):
    """左右翻面，但徽章那一圈貼回沒翻過的原樣（徽章是圓的，翻不翻外形都一樣，只有字會反）。"""
    f = im.transpose(Image.FLIP_LEFT_RIGHT)
    if badge:
        x, y, r = badge; r += 4
        disc = im.crop((x - r, y - r, x + r, y + r)); mask = Image.new('L', disc.size, 0)
        ImageDraw.Draw(mask).ellipse((0, 0, 2 * r - 1, 2 * r - 1), fill=255)
        f.paste(disc, (im.width - 1 - x - r, y - r), mask)
    return f


def place(im, k, cx, S=128, foot=123):
    """縮 k 倍後身體中心對齊畫布中線、底部對齊 foot。"""
    ys, xs = np.where(np.asarray(im)[..., 3] > 10)
    b = im.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
    r = resize_pm(b, (max(1, round(b.width * k)), max(1, round(b.height * k))))
    c = Image.new('RGBA', (S, S), (0, 0, 0, 0)); c.alpha_composite(r, (round(S / 2 - (cx - xs.min()) * k), foot - r.height)); return c


def despill(path, key='green'):
    subprocess.run([sys.executable, str(CUT), 'despill', str(path), '--key', key], check=True, capture_output=True)
    fixed = path.with_name(path.stem + '-fixed.png'); fixed.replace(path)


def cut_sheet(key, outs):
    """綠幕道具表：去背後依連通區域由左到右切開，各自置中成正方形。"""
    sheet = RAW / f'{key}.png'
    if not sheet.exists(): print('缺', key); return
    cut = RAW / f'{key}-cut.png'
    subprocess.run([sys.executable, str(CUT), 'key', str(sheet), '-o', str(cut)], check=True, capture_output=True)
    print(subprocess.run([sys.executable, str(CUT), 'check', str(cut), '--key', 'green'], capture_output=True, text=True).stdout.splitlines()[-3:])
    im = Image.open(cut); a = np.asarray(im)
    lab, n = ndimage.label(ndimage.binary_dilation(a[..., 3] > 10, iterations=12))   # 膨脹後再分群，閃光碎點併進主體
    big = sorted(range(1, n + 1), key=lambda i: -(lab == i).sum())[:len(outs)]
    for i, (name, size) in zip(sorted(big, key=lambda i: np.where(lab == i)[1].mean()), outs):
        ys, xs = np.where(lab == i)
        part = Image.fromarray(np.where((lab == i)[..., None], a, 0).astype(np.uint8), 'RGBA').crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
        o = OUT / name; o.parent.mkdir(parents=True, exist_ok=True)
        tmp = o.with_suffix('.png'); resize_pm(square(part), (size, size)).save(tmp); despill(tmp)
        Image.open(tmp).save(o, quality=90); tmp.unlink(); print('ok', name)


def main():
    for k, dst in WIDE.items():
        src = RAW / f'{k}.png'
        if not src.exists(): print('缺', k); continue
        o = OUT / dst; o.parent.mkdir(parents=True, exist_ok=True)
        Image.open(src).convert('RGB').resize((1920, 1080), Image.LANCZOS).save(o, quality=88); print('ok', dst)
    sheet = RAW / 'sheet-king.png'
    if sheet.exists():
        cut = ROOT / 'art/raw/sheet-king-cut.png'
        subprocess.run([sys.executable, str(CUT), 'key', str(sheet), '-o', str(cut)], check=True)
        print(subprocess.run([sys.executable, str(CUT), 'check', str(cut), '--key', 'green'], capture_output=True, text=True).stdout)
        im = Image.open(cut); a = np.asarray(im)
        lab, n = ndimage.label(a[..., 3] > 10)
        big = sorted(range(1, n + 1), key=lambda i: -(lab == i).sum())[:2]
        parts = sorted(big, key=lambda i: np.where(lab == i)[1].mean())   # 左＝國王、右＝日誌
        for i, (name, size) in zip(parts, [('portrait/king.png', None), ('props/journal.png', 256)]):
            ys, xs = np.where(lab == i)
            # 外接框放大一點，把細碎的部件（王冠珠子、緞帶）一起收進來
            x0, y0, x1, y1 = max(xs.min() - 20, 0), max(ys.min() - 20, 0), min(xs.max() + 21, im.width), min(ys.max() + 21, im.height)
            part = im.crop((x0, y0, x1, y1))
            if size: part = resize_pm(square(part), (size, size))
            o = OUT / name; o.parent.mkdir(parents=True, exist_ok=True); part.save(o); despill(o)
            w = o.with_suffix('.webp'); Image.open(o).save(w, quality=90); o.unlink(); print('ok', w.name, part.size)   # 帶透明的 webp，比 png 小很多
    cut_sheet('sheet-props', [('props/basket.webp', 256), ('props/poop.webp', 64), ('props/coin.webp', 128)])
    cut_sheet('sheet-gift', [('props/gift.webp', 256)])
    for name, src in (('slime-daily', 'sprite-test-daily'),):   # 平常的地圖小人（呂布造型改走下面的聯動造型）
        o = OUT / f'walk/{name}.png'; o.parent.mkdir(parents=True, exist_ok=True)
        strip([resize_pm(Image.open(ROOT / f'assets/concept/{src}.webp'), (DAILY, DAILY))]).save(o); despill(o)
        im4 = Image.open(o); im4.save(o.with_suffix('.webp'), lossless=True); im4.crop((0, 0, DAILY, DAILY)).save(o.with_name(o.stem + '-still.webp'), lossless=True); o.unlink(); print('ok walk', name)   # 頭像用單格
    # 聯動造型小人：關羽身上有綠也有紅（綠幕、洋紅幕都會撞色），關羽與劉備（綠甲）用藍幕；呂布兩套都產，LUBU 選哪套
    cuts = {}
    for name, key in (('lubu-baihua', 'green'), ('lubu-heijin', 'green'), ('liubei', '#0000FF'), ('guanyu', '#0000FF'), ('zhangfei', 'green'), ('diaochan', 'green'),
                      ('weixu', 'green'), ('quan', '#0000FF'), ('xiang', 'green')):   # 呂荃穿綠又帶粉，用藍幕
        raw = RAW / f'pendant-{name}.png'   # 加了姓氏玉珮的版本（沒有就用原圖，例如黑金呂布）
        if not raw.exists(): raw = RAW / f'outfit-{name}.png'
        if not raw.exists(): print('缺', raw.name); continue
        cut = RAW / f'{raw.stem}-cut.png'
        subprocess.run([sys.executable, str(CUT), 'key', str(raw), '-o', str(cut), '--key', key], check=True, capture_output=True)
        print(name, subprocess.run([sys.executable, str(CUT), 'check', str(cut), '--key', key], capture_output=True, text=True).stdout.strip().splitlines()[-4:])
        cuts[name] = (Image.open(cut), key)
    # 兵器長短不一，整張塞進 128 會讓身體忽大忽小（方天畫戟那隻身體只剩 44px）。改成身體寬度跟平常那隻一樣，
    # 畫布放大到裝得下最長的兵器；身體置中，所以小人站的位置跟平常那隻一致（build.py 照圖檔尺寸宣告 sprite 寬高）
    body = {n: BODY_PX[n] for n in cuts}
    need = max(max(extent(im, body[n][1])) * BODY / body[n][0] for n, (im, _) in cuts.items())
    S = int(-(-(need + 8) // 16) * 16)
    for name, (im, key) in cuts.items():
        o = OUT / f'walk/slime-{name}.png'
        k, cx = BODY / body[name][0], body[name][1]
        own = ground(place(im, k, cx, S, S - 5), SHADOW_GAP); other = ground(place(mirror(im, BADGE.get(name)), k, im.width - cx, S, S - 5), SHADOW_GAP)
        left, right = (own, other) if name in ART_LEFT else (other, own)
        sheet = strip([own, left, right, own])   # 列序＝下、左、右、上
        sheet.save(o); despill(o, key)
        im4 = Image.open(o); im4.save(o.with_suffix('.webp'), lossless=True)
        im4.crop((0, 0, S, S)).save(o.with_name(o.stem + '-still.webp'), lossless=True); o.unlink(); print('ok walk', name, 'body', BODY, 'canvas', S)   # 頭像用單格（選單的立繪欄會把四列整張疊著畫）
    # 小王子／小公主（分化後平常的樣子）：跟平常那隻一樣是單列、引擎左右翻面、沒有腳下陰影，身體寬 BODY、畫布至少 DAILY
    for name in FORM_PX:
        raw = RAW / f'form-{name}.png'
        if not raw.exists(): print('缺', raw.name); continue
        cut = RAW / f'form-{name}-cut.png'
        subprocess.run([sys.executable, str(CUT), 'key', str(raw), '-o', str(cut), '--key', 'green'], check=True, capture_output=True)
        im = Image.open(cut).convert('RGBA'); k, cx = BODY / FORM_PX[name][0], FORM_PX[name][1]
        arr = np.asarray(im).copy(); lab, n = ndimage.label(arr[..., 3] > 10); sizes = ndimage.sum(np.ones_like(lab), lab, range(1, n + 1))
        arr[..., 3][np.isin(lab, [i + 1 for i, s in enumerate(sizes) if s < 200])] = 0; im = Image.fromarray(arr)   # 去背留下的零星小點
        S = max(DAILY, int(-(-(max(extent(im, cx)) * k + 8) // 4) * 4))
        o = OUT / f'walk/slime-{name}.png'
        strip([ground(place(im, k, cx, S, S - 5))]).save(o); despill(o)
        im4 = Image.open(o); im4.save(o.with_suffix('.webp'), lossless=True); im4.crop((0, 0, S, S)).save(o.with_name(o.stem + '-still.webp'), lossless=True); o.unlink(); print('ok walk', name, 'canvas', S)
    for suffix in ('', '-still'):
        src = OUT / f'walk/slime-lubu-{LUBU}{suffix}.webp'
        if src.exists(): src.replace(OUT / f'walk/slime-lubu{suffix}.webp')



if __name__ == '__main__':
    main()
