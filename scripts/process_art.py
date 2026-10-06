"""art/raw → assets/art：背景放大成 1920×1080 webp；國王與日誌綠幕去背後切開；小人縮成 128px。"""
import pathlib, subprocess, sys
import numpy as np
from PIL import Image
from scipy import ndimage
ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW, OUT = ROOT / 'art/raw', ROOT / 'assets/art'
CUT = pathlib.Path.home() / '.claude/skills/cutout/cutout.py'
WIDE = {'bg-capital': 'bg/capital.webp', 'bg-courtyard': 'bg/courtyard.webp', 'bg-throne': 'bg/throne.webp',
        'cg-egg-feet': 'cg/egg-feet.webp', 'cg-hatch': 'cg/hatch.webp', 'cg-egg-rug': 'cg/egg-rug.webp'}


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


def despill(path):
    subprocess.run([sys.executable, str(CUT), 'despill', str(path), '--key', 'green'], check=True, capture_output=True)
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
    cut_sheet('sheet-props', [('props/basket.webp', 256), ('props/poop.webp', 128), ('props/coin.webp', 128)])
    slime = ROOT / 'assets/concept/sprite-test-daily.webp'
    o = OUT / 'walk/slime-daily.png'; o.parent.mkdir(parents=True, exist_ok=True)
    resize_pm(Image.open(slime), (128, 128)).save(o); despill(o)
    Image.open(o).save(o.with_suffix('.webp'), lossless=True); o.unlink(); print('ok walk 128 webp')


if __name__ == '__main__':
    main()
