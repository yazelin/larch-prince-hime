"""分層育嬰室的真圖：照設計檔（art/objects_nursery.yaml）產純地面底圖＋每件家具單獨生成（照《續》xu/game/art/objects_gen.py）。
定錨＝舊整張俯視畫 assets/art/maps/nursery.webp：每件家具送它附近那一塊裁切（畫風、俯角、外觀）。
不從整張圖摳物件（邊緣會出問題）；地面是「同一張圖拿掉家具」，再 ECC 對齊回原圖。
王城中央廣場（--map=plaza）沒有舊整張圖：家具帶育嬰室整張（畫風、俯角）＋競技場背景（王國的建築風格），地面照設計檔的色塊配置圖生成。
用法：python3 scripts/map_art.py gen [鍵…] [--map=plaza]   產圖到 art/raw/map-<鍵>.png（廣場是 map-plaza-<鍵>.png；已有的跳過）
      python3 scripts/map_art.py cut [--map=plaza]          去背、縮進圖框、下緣貼齊 → assets/art/objects/<地圖>/<名>.png＋ground.webp"""
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
MAP = 'plaza' if '--map=plaza' in sys.argv else 'nursery'
OUT = ROOT / f'assets/art/objects/{MAP}'
PRE = 'map-' if MAP == 'nursery' else f'map-{MAP}-'
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
ARENA = RAW / 'bg-arena.png'
STYLE = None   # 育嬰室：Image 1 是舊整張圖那一塊；廣場在下面換成整張參考
if MAP == 'plaza':
    ITEMS = {
        'fountain': ('三層白色大理石圓形噴水池，池邊鑲金，最上層站著一隻金色的小圓史萊姆雕像在往上噴水，水花晶亮', 'magenta', []),
        'bench': ('一張長椅：白色鑄鐵捲花扶手、淺蜂蜜色木條椅面與椅背，長邊朝左右', 'magenta', []),
        'tree': ('一棵圓冠的開花樹：茂密的淺綠樹冠上開滿粉白小花，樹幹短而胖，樹根處一圈小草', 'blue', []),   # 綠葉配粉花，綠幕洋紅幕都撞
        'flowerbed': ('白色石塊圍邊的橢圓形花圃，裡面種滿粉、黃、白的小花', 'blue', []),
        'lamp': ('一盞金色鑄鐵路燈：細長燈柱，頂端燈罩是一顆星星形狀、發著暖黃的光', 'green', []),
        'flag': ('一根白色旗桿，頂端金色圓球，掛著一面藍底金色小王冠的長旗，旗子微微飄動', 'green', []),
        'notice': ('一座木框公告欄，兩根木柱撐著小屋頂，板子上釘著幾張畫了圓圓小史萊姆的告示紙', 'green', []),
    }
    USE = {'噴水池': 'fountain', **{f'長椅{d}': 'bench' for d in ('西北', '東北', '西南', '東南')}, **{f'樹{d}': 'tree' for d in ('西北', '東北', '西南', '東南')},
           **{f'花圃{d}': 'flowerbed' for d in ('西北', '東北', '西南', '東南')}, **{f'路燈{d}': 'lamp' for d in ('西北', '東北', '西南', '東南')},
           '旗桿西': 'flag', '旗桿東': 'flag', '公告欄': 'notice'}
    MIRROR = {'樹東北', '樹東南', '花圃東北', '花圃東南', '旗桿東'}   # 東邊那幾件左右翻，畫面不會一模一樣
    FILL_W = set()
    STYLE = ('**畫風完全照 Image 1**：Image 1 是我們遊戲的另一張俯視地圖（育嬰室），光澤可愛的動漫繪本風、暖光、低彩度的燕麥奶白、蜂蜜、蜜桃、薄荷與晨霧藍；'
             '**同一個俯角**（從南邊斜上方高角度往下看，看得到頂面和朝南的正面）。Image 2 是同一個雲端王國的建築與裝飾風格（白色大理石、金色細節、粉藍旗幟、花）。'
             '這件東西放在戶外的王城中央廣場，晴天上午。\n')


def objs():
    return {o['name']: o for o in layout.objects(layout.load(MAP))}


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
    hexc = {'green': '#00FF00', 'magenta': '#FF00FF', 'blue': '#0000FF'}[plate]
    head = STYLE or ('**畫風完全照 Image 1**：Image 1 是同一張俯視遊戲地圖的一小塊，光澤可愛的動漫繪本風、午後暖光、'
            '低彩度的燕麥奶白、蜂蜜、蜜桃、薄荷與晨霧藍；**同一個俯角**（從南邊斜上方高角度往下看，看得到頂面和朝南的正面）。'
            'Image 1 裡同一件家具的樣子照它，但重新畫成獨立、完整、乾淨的一件。\n')
    return ('遊戲地圖的家具素材（只畫一件）。' + head +
            f'畫：{desc}。{CUTE}\n'
            f'比例：整件的外框寬 {fw} 格、高 {fh} 格（寬:高＝{fw}:{fh}）；最下面 {d} 格是它放在地上的底面，上面 {fh - d} 格是往上的高度。\n'
            '只畫這一件，不畫地板、不畫投在地上的影子、不畫其他家具、不畫人或寵物。邊緣清楚，不要霧、不要光暈。\n'
            f'背景：整張不透明的純{ {"green": "綠", "magenta": "洋紅", "blue": "藍"}[plate]}色 {hexc} 平塗，沒有漸層、沒有陰影；家具不碰到畫面邊緣。無文字、無浮水印。')


GROUND = ('Image 1 是一間育嬰室的俯視遊戲地圖。畫**同一張圖、同一個構圖與畫風**，但把所有家具和擺設拿掉，只留房間本身：'
          '保留北牆（奶白護牆板、金框、正中拱形大窗、兩側淺藍窗簾、兩面藍底金鳶尾旗）、左右兩側的牆、蜂蜜色木地板與窗光、'
          '中間的白色雲朵地毯、右上角粉色圓形地毯、最下方正中的藍底金鳶尾門口地墊。\n'
          '**拿掉**：書櫃、所有盆栽、貝殼鏡、粉色矮凳、小圓桌、玩具箱、嬰兒床與紗帳、檯燈邊桌、沙發、粉色坐墊與星星抱枕、最下方的白色欄杆與欄柱。'
          '拿掉的地方補上同樣的木地板（右上角粉色圓毯補完整的圓），最下方欄杆的位置補木地板。無文字、無浮水印。')


PLAZA_GROUND = ('Image 1 是一張俯視遊戲地圖的**地面配置色塊圖**，構圖照它：每一塊顏色的位置與大小就是那種地面。顏色對照：'
                '最上面一整條淡米色＝王宮正門（白色大理石寬台階往上通到一座有金邊的大拱門，台階兩側金色欄杆、掛藍底金冠旗）；'
                '米白＝奶白與淺金色的圓弧石板地，以畫面正中偏上為圓心一圈一圈鋪開；四塊綠＝修剪整齊的嫩綠草坪；'
                '左右兩條深色細邊與最下面的深色條＝廣場邊緣外的雲海（白雲）；最下面正中一小塊藍＝往南的石板小路出口。\n'
                'Image 2 是我們遊戲的另一張地圖，**只參考它的畫風、俯角與光線**（光澤可愛的動漫繪本風、從南邊斜上方高角度往下看）。'
                'Image 3 是同一個王國的建築風格。\n'
                '**每一塊的位置、大小與邊界都要跟 Image 1 一致**：雲海只有 Image 1 深色那幾條那麼窄（左右兩邊各一條細邊、下緣兩段），石板地要一直鋪到最下面那條深色條旁邊；草坪的位置照四塊綠。\n'
                '畫一張**只有地面與王宮正門**的俯視遊戲地圖，填滿整個畫面，晴天上午、陽光溫暖。'
                '**絕對不要畫噴水池、長椅、樹、花圃、路燈、旗桿、公告欄、人、動物**，那些之後會另外疊上去。不同地面之間自然過渡，不要畫出色塊的硬邊。無文字、無格線、無浮水印。')


def plaza_layout():
    """廣場地面的色塊配置圖（沒有格線，給生圖當構圖）"""
    d = layout.load('plaza'); S = 24; from PIL import ImageDraw
    im = Image.new('RGB', (48 * S, 36 * S), layout.GROUND['stone']); dr = ImageDraw.Draw(im)
    for g in d['ground']:
        for x, y, w, h in g['rects']: dr.rectangle((x * S, y * S, (x + w) * S - 1, (y + h) * S - 1), fill=layout.GROUND[g['kind']])
    out = RAW / '_ref/plaza-layout.png'; im.resize((1536, 1024), Image.NEAREST).save(out); return out   # 拉成跟生圖一樣的 3:2，生回來再拉回 4:3，位置才對得上


def jobs():
    o = objs(); out = {}
    for name, key in USE.items():
        if key in out: continue
        refs = ([SRC, ARENA] if MAP == 'plaza' else [ref_crop(o[name], key)]) + [ROOT / x for x in ITEMS[key][2]]
        out[key] = (prompt(key, o[name]), size(*o[name]['frame'][2:]), refs)
    out['ground'] = (PLAZA_GROUND, '1536x1024', [plaza_layout(), SRC, ARENA]) if MAP == 'plaza' else (GROUND, '1536x1024', [SRC])
    return out


def run(item):
    key, (p, sz, refs) = item; out = RAW / f'{PRE}{key}.png'
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
    src = RAW / f'{PRE}{key}.png'; tmp = RAW / f'{PRE}{key}-key.png'
    subprocess.run([sys.executable, str(CUTOUT), 'key', str(src), '-o', str(tmp), '--key', {'blue': '#0000FF'}.get(ITEMS[key][1], ITEMS[key][1]), '--fuzz', '18', '--erode', '1'], check=True, capture_output=True)
    im = Image.open(tmp).convert('RGBA'); tmp.unlink()
    return im.crop(im.getbbox())


def premul_resize(im, sz):
    a = np.asarray(im, np.float32); al = a[..., 3:4] / 255.0
    r = np.asarray(Image.fromarray(np.concatenate([a[..., :3] * al, a[..., 3:4]], -1).round().astype(np.uint8), 'RGBA').resize(sz, Image.LANCZOS), np.float32)
    al2 = np.clip(r[..., 3:4] / 255.0, 1e-4, 1.0)
    return Image.fromarray(np.concatenate([np.clip(r[..., :3] / al2, 0, 255), r[..., 3:4]], -1).round().astype(np.uint8), 'RGBA')


def fit(fig, fw, fh, fill_w=False):
    """等比縮進 fw×fh 格的圖框；下緣貼齊（＝佔地最下一列的下緣）、水平置中；一長排的拉滿寬度，太高就報錯（2026-10-09 作者：欄杆兩端的花和柱頂被切掉）"""
    W, Hh = fw * PX, fh * PX
    s = W / fig.width if fill_w else min(W / fig.width, Hh / fig.height)
    nw, nh = max(1, round(fig.width * s)), max(1, round(fig.height * s))
    f = premul_resize(fig, (nw, nh))
    assert nh <= Hh, f'圖比圖框高 {nh}>{Hh}px，設計檔的 up 要加高（裁掉會切到盆栽和欄柱頂）'
    c = Image.new('RGBA', (W, Hh)); c.alpha_composite(f, ((W - nw) // 2, Hh - nh)); return c


def ground():
    """生成的地面拉回原圖大小、ECC 仿射對齊原圖（牆腳要對到第 6 列），再放大到 48×36 格 × PX；廣場照配置圖生成，直接拉到地圖大小"""
    if MAP == 'plaza':
        Image.open(RAW / f'{PRE}ground.png').convert('RGB').resize((48 * PX, 36 * PX), Image.LANCZOS).save(OUT / 'ground.webp', quality=90); return
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
    args = [a for a in sys.argv[1:] if not a.startswith('--')]; cmd = args[0] if args else ''
    if cmd == 'gen': gen(args[1:])
    elif cmd == 'cut': cut()
