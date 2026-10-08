"""分層育嬰室的真圖：照設計檔（art/objects_nursery.yaml）產純地面底圖＋每件家具單獨生成（照《續》xu/game/art/objects_gen.py）。
定錨＝舊整張俯視畫 assets/art/maps/nursery.webp：每件家具送它附近那一塊裁切（畫風、俯角、外觀）。
不從整張圖摳物件（邊緣會出問題）；地面是「同一張圖拿掉家具」，再 ECC 對齊回原圖。
用法：python3 scripts/map_art.py gen [鍵…]   產圖到 art/raw/map-<鍵>.png（已有的跳過）
      python3 scripts/map_art.py cut          去背、縮進圖框、下緣貼齊 → assets/art/objects/nursery/<名>.png＋ground.webp"""
import subprocess, sys, pathlib, concurrent.futures as cf
import numpy as np
from PIL import Image
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import layout
ROOT = layout.ROOT
GEN = pathlib.Path.home() / '.claude/skills/codex-imagegen/codex-imagegen.sh'
CUTOUT = pathlib.Path.home() / '.claude/skills/cutout/cutout.py'
RAW = ROOT / 'art/raw'
SRC = ROOT / 'assets/art/maps/nursery.webp'
OUT = ROOT / 'assets/art/objects/nursery'
PX = 40   # 每細格 px＝build.py 分層版的 TILE_PX，圖 1:1 不糊

# 鍵 → (描述, 幕色, 額外參考)；同一張圖給好幾件家具用的寫在 USE
CUTE = '形狀圓潤飽滿、比例偏矮胖可愛、細節少而大塊，縮小到遊戲地圖上也一眼認得出來。'
ITEMS = {
    'bookcase': ('奶白描金的矮書櫃，上層擺一頂小金冠和幾本粉藍書，下層兩個粉藍帽盒，頂上垂著一點常春藤', 'magenta', []),
    'plant': ('白瓷描金花盆裡一叢綠葉盆栽，開幾朵小白花', 'magenta', []),
    'mirror': ('粉色扇貝殼框的落地穿衣鏡，鏡面是淡藍的玻璃反光，金色鏡框', 'green', []),
    'stool': ('粉色絨面的圓矮凳，鈕扣拉釦，金色彎彎小腳', 'green', []),
    'table': ('金邊圓形小邊桌，桌上一盤星星糖，旁邊放著 Image 2 那本粉紅皮面的王室日誌', 'green', ['assets/art/props/journal.webp']),
    'toybox': ('打開的淺藍描金木箱，箱裡露出彩色條紋球、粉色小城堡、黃色星星玩偶，白毛巾掛在箱邊', 'magenta', []),
    'crib': ('圓形白金色嬰兒床，粉白紗帳從頂上垂下、頂端一個粉紅大蝴蝶結，床裡有粉色圓枕、黃色星星抱枕，淡藍毯子從床邊垂下', 'green', []),
    'basket': ('照 Image 2 的藤編點心籃：粉格子布、草莓布丁和鬆餅', 'green', ['assets/art/props/basket.webp']),
    'lamp': ('奶白描金的小邊桌，上面一盞金色星星檯燈', 'green', []),
    'sofa': ('靠牆的奶白長沙發（從上往下看是直的、長邊朝畫面上下），花朵抱枕、星星抱枕、淡藍格子毯垂下來；座墊中段放著 Image 2 那個奶油色包裝、粉緞帶的王室禮物箱', 'green', ['assets/art/props/gift.webp']),
    'pouf': ('一個粉色大圓坐墊，旁邊靠著一黃一藍兩顆星星抱枕，三樣緊緊擺成一組', 'green', []),
    'railing': ('一長排白色欄杆，金色圓頭的欄柱；右端是一根較粗的金頂欄柱（門口），左端擺一盆小白花綠葉盆栽', 'magenta', []),
}
USE = {'書櫃': 'bookcase', '書櫃旁盆栽': 'plant', '西牆盆栽': 'plant', '東牆盆栽': 'plant', '貝殼鏡': 'mirror', '矮凳': 'stool', '糖果小桌': 'table',
       '玩具箱': 'toybox', '嬰兒床': 'crib', '點心籃': 'basket', '檯燈邊桌': 'lamp', '沙發': 'sofa', '圓墊': 'pouf', '南欄西': 'railing', '南欄東': 'railing'}
MIRROR = {'南欄東'}   # 東段欄杆＝西段左右翻（門口在中間）
FILL_W = {'railing'}  # 一長排的東西寬度拉滿圖框


def objs():
    return {o['name']: o for o in layout.objects(layout.load('nursery'))}


def ref_crop(o, key):
    """舊整張俯視畫上這件家具附近的一塊（圖框外加 2 格）"""
    out = RAW / f'_ref/map-{key}.png'
    if out.exists(): return out
    im = Image.open(SRC).convert('RGB'); s = im.width / 48; fx, fy, fw, fh = o['frame']
    im.crop((max(0, (fx - 2) * s), max(0, (fy - 2) * s), min(im.width, (fx + fw + 2) * s), min(im.height, (fy + fh + 2) * s))).save(out)
    return out


def size(fw, fh):
    r = fw / fh
    return '1536x1024' if r > 1.25 else '1024x1536' if r < .8 else '1024x1024'


def prompt(key, o):
    desc, plate, extra = ITEMS[key]; fx, fy, fw, fh = o['frame']; d = o['foot'][3]
    hexc = {'green': '#00FF00', 'magenta': '#FF00FF'}[plate]
    return ('遊戲地圖的家具素材（只畫一件）。**畫風完全照 Image 1**：Image 1 是同一張俯視遊戲地圖的一小塊，光澤可愛的動漫繪本風、午後暖光、'
            '低彩度的燕麥奶白、蜂蜜、蜜桃、薄荷與晨霧藍；**同一個俯角**（從南邊斜上方高角度往下看，看得到頂面和朝南的正面）。'
            'Image 1 裡同一件家具的樣子照它，但重新畫成獨立、完整、乾淨的一件。\n'
            f'畫：{desc}。{CUTE}\n'
            f'比例：整件的外框寬 {fw} 格、高 {fh} 格（寬:高＝{fw}:{fh}）；最下面 {d} 格是它放在地上的底面，上面 {fh - d} 格是往上的高度。\n'
            '只畫這一件，不畫地板、不畫投在地上的影子、不畫其他家具、不畫人或寵物。邊緣清楚，不要霧、不要光暈。\n'
            f'背景：整張不透明的純{"綠" if plate == "green" else "洋紅"}色 {hexc} 平塗，沒有漸層、沒有陰影；家具不碰到畫面邊緣。無文字、無浮水印。')


GROUND = ('Image 1 是一間育嬰室的俯視遊戲地圖。畫**同一張圖、同一個構圖與畫風**，但把所有家具和擺設拿掉，只留房間本身：'
          '保留北牆（奶白護牆板、金框、正中拱形大窗、兩側淺藍窗簾、兩面藍底金鳶尾旗）、左右兩側的牆、蜂蜜色木地板與窗光、'
          '中間的白色雲朵地毯、右上角粉色圓形地毯、最下方正中的藍底金鳶尾門口地墊。\n'
          '**拿掉**：書櫃、所有盆栽、貝殼鏡、粉色矮凳、小圓桌、玩具箱、嬰兒床與紗帳、檯燈邊桌、沙發、粉色坐墊與星星抱枕、最下方的白色欄杆與欄柱。'
          '拿掉的地方補上同樣的木地板（右上角粉色圓毯補完整的圓），最下方欄杆的位置補木地板。無文字、無浮水印。')


def jobs():
    o = objs(); out = {}
    for name, key in USE.items():
        if key in out: continue
        refs = [ref_crop(o[name], key)] + [ROOT / x for x in ITEMS[key][2]]
        out[key] = (prompt(key, o[name]), size(*o[name]['frame'][2:]), refs)
    out['ground'] = (GROUND, '1536x1024', [SRC])
    return out


def run(item):
    key, (p, sz, refs) = item; out = RAW / f'map-{key}.png'
    if out.exists(): return f'skip {key}'
    pngs = []
    for r in refs:   # codex 吃 png 最穩
        q = RAW / '_ref' / (pathlib.Path(r).stem + '.png')
        if not q.exists(): Image.open(r).convert('RGB').save(q)
        pngs.append(str(q))
    r = subprocess.run(['bash', str(GEN), f'畫布 {sz}。\n' + p, str(out)] + pngs, cwd=RAW, stdin=subprocess.DEVNULL, capture_output=True, text=True)
    return f'{key}: {"ok" if out.exists() else "FAIL " + r.stderr[-300:]}'


def gen(keys):
    (RAW / '_ref').mkdir(parents=True, exist_ok=True); js = jobs()
    with cf.ThreadPoolExecutor(3) as ex:
        for m in ex.map(run, [(k, js[k]) for k in (keys or js)]): print(m, flush=True)


def key_out(key):
    src = RAW / f'map-{key}.png'; tmp = RAW / f'map-{key}-key.png'
    subprocess.run([sys.executable, str(CUTOUT), 'key', str(src), '-o', str(tmp), '--key', ITEMS[key][1], '--fuzz', '18', '--erode', '1'], check=True, capture_output=True)
    im = Image.open(tmp).convert('RGBA'); tmp.unlink()
    return im.crop(im.getbbox())


def premul_resize(im, sz):
    a = np.asarray(im, np.float32); al = a[..., 3:4] / 255.0
    r = np.asarray(Image.fromarray(np.concatenate([a[..., :3] * al, a[..., 3:4]], -1).round().astype(np.uint8), 'RGBA').resize(sz, Image.LANCZOS), np.float32)
    al2 = np.clip(r[..., 3:4] / 255.0, 1e-4, 1.0)
    return Image.fromarray(np.concatenate([np.clip(r[..., :3] / al2, 0, 255), r[..., 3:4]], -1).round().astype(np.uint8), 'RGBA')


def fit(fig, fw, fh, fill_w=False):
    """等比縮進 fw×fh 格的圖框；下緣貼齊（＝佔地最下一列的下緣）、水平置中；一長排的拉滿寬度，太高就切頂"""
    W, Hh = fw * PX, fh * PX
    s = W / fig.width if fill_w else min(W / fig.width, Hh / fig.height)
    nw, nh = max(1, round(fig.width * s)), max(1, round(fig.height * s))
    f = premul_resize(fig, (nw, nh))
    if nh > Hh: f = f.crop((0, nh - Hh, nw, nh)); nh = Hh
    c = Image.new('RGBA', (W, Hh)); c.alpha_composite(f, ((W - nw) // 2, Hh - nh)); return c


def ground():
    """生成的地面拉回原圖大小、ECC 仿射對齊原圖（牆腳要對到第 6 列），再放大到 48×36 格 × PX"""
    import cv2
    ref = np.asarray(Image.open(SRC).convert('L').resize((724, 543)), np.float32)
    g = Image.open(RAW / 'map-ground.png').convert('RGB').resize(Image.open(SRC).size, Image.LANCZOS)
    mov = np.asarray(g.convert('L').resize((724, 543)), np.float32)
    warp = np.eye(2, 3, dtype=np.float32)
    cc, warp = cv2.findTransformECC(ref, mov, warp, cv2.MOTION_AFFINE, (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 200, 1e-6), None, 5)
    warp[:, 2] *= 2
    a = cv2.warpAffine(np.asarray(g), warp, g.size, flags=cv2.INTER_LANCZOS4 + cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REPLICATE)
    Image.fromarray(a).resize((48 * PX, 36 * PX), Image.LANCZOS).save(OUT / 'ground.webp', quality=90)
    print('地面 ECC', round(cc, 3))


def cut():
    OUT.mkdir(parents=True, exist_ok=True); cache = {}
    for name, o in objs().items():
        key = USE[name]
        if key not in cache: cache[key] = key_out(key)
        fig = cache[key].transpose(Image.FLIP_LEFT_RIGHT) if name in MIRROR else cache[key]
        fit(fig, *o['frame'][2:], fill_w=key in FILL_W).save(OUT / f'{name}.png')
    ground(); print(OUT, len(cache), '張生成圖')


if __name__ == '__main__':
    # 自我檢查：縮進圖框後下緣貼齊、水平置中
    t = fit(Image.new('RGBA', (100, 50), (255, 0, 0, 255)), 4, 4)
    a = np.asarray(t)[..., 3]; ys, xs = np.nonzero(a)
    assert ys.max() == 4 * PX - 1 and abs((xs.min() + xs.max()) / 2 - 2 * PX + .5) <= 1, (ys.max(), xs.min(), xs.max())
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    if cmd == 'gen': gen(sys.argv[2:])
    elif cmd == 'cut': cut()
