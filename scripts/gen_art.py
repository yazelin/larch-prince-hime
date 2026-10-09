"""序章美術工作清單：每張固定帶畫風定錨，產到 art/raw/<key>.png，已存在就跳過。
用法：python3 scripts/gen_art.py [key ...]   （不帶參數＝全部，三張並行）"""
import subprocess, sys, pathlib, concurrent.futures as cf
ROOT = pathlib.Path(__file__).resolve().parent.parent
GEN = pathlib.Path.home() / '.claude/skills/codex-imagegen/codex-imagegen.sh'
# 定錨的來源都是 repo 裡的 webp，產圖時才轉成 png 放進 art/raw/_ref（codex 吃 png 最穩；art/raw 不進 git）
TAOYUAN = pathlib.Path.home() / 'larch-taoyuan'   # 聯動造型照《三結義》的兵器對照表與三姊妹定錨（只當參考，不進本 repo）
REF_SRC = {'scene': 'assets/cover/cover-v3.webp', 'style': 'assets/concept/style-test-1.webp', 'slime': 'assets/concept/sprite-raw-green.webp',
           'weapons': TAOYUAN / 'buchan/cg_v/sheet_weapons_yuanmen_v2.webp', 'liubei': TAOYUAN / 'cast/anchor_liubei.webp',
           'guanyu': TAOYUAN / 'cast/anchor_guanyu.webp', 'liubei_armor': TAOYUAN / 'cast/v_劉備-戰甲_user_norm.webp',
           'guanyu_armor': TAOYUAN / 'cast/v_關羽-戰甲_user_norm.webp', 'zhangfei_armor': TAOYUAN / 'cast/v_張飛-戰甲_user_norm.webp',
           'liubei_pose': pathlib.Path.home() / 'xianquan-musou/assets/boss_posters/sanying.webp',
           'diaochan': TAOYUAN / 'cast/lubu/定錨_貂蟬_全圖.webp', 'handkerchief': TAOYUAN / 'cast/lubu/定錨_道具_冷梅帕.webp',
           'lubu_baihua': TAOYUAN / 'cast/lubu/百花戰甲_raw.webp', 'lubu_heijin': TAOYUAN / 'buchan/cg_v/anchor_lubu_flatboots_2_v2.webp', 'zhangfei': TAOYUAN / 'cast/anchor_zhangfei.webp',
           # 香布纏另外三件（#5）：兵器用原作的道具圖示（buchan/items.py 產的），衣服用素材庫選定造型的 Q 版
           'w_weixu': TAOYUAN / 'buchan/items_raw/w-weixu_v1.webp', 'w_quan': TAOYUAN / 'buchan/items_raw/w-quan_v1.webp', 'w_xiang': TAOYUAN / 'buchan/items_raw/w-xiang_v1.webp',
           'weixu': TAOYUAN / 'buchan/cg_v/qa_weixu_1_v2.webp', 'quan': TAOYUAN / 'buchan/cg_v/qa_quan16_10_v2.webp', 'xiang': TAOYUAN / 'buchan/cg_v/qa_xiang_2_v2.webp'}
REF = {k: f'art/raw/_ref/{k}.png' for k in REF_SRC}
REF.update({f'form-{n}': f'art/raw/form-{n}.png' for n in ('prince', 'hime')})   # 成年禮 CG 用分化後的樣子當定錨
REF.update({f'raw-{n}': f'art/raw/outfit-{n}.png' for n in ('lubu-baihua', 'liubei', 'guanyu', 'zhangfei', 'diaochan', 'weixu', 'quan', 'xiang')})   # 徽章改圖用作者認可過的原圖


def refs_ready():
    from PIL import Image
    (ROOT / 'art/raw/_ref').mkdir(parents=True, exist_ok=True)
    for k, src in REF_SRC.items():
        if (ROOT / REF[k]).exists(): continue
        im = Image.open(ROOT / src).convert('RGB')
        if k == 'liubei_pose': im = im.crop((0, 0, im.width * 2 // 5, im.height))   # 《無雙》三英海報只取左邊的劉備
        im.save(ROOT / REF[k])

SCENE = ('Painted in the exact rendering style and palette of the scene reference image (glossy cute anime storybook, warm afternoon light, '
         'soft low-saturation oat cream, honey, peach, mint and mist blue). Calm and uncluttered, healing mood. '
         'WIDE LANDSCAPE 16:9. No people, no text, no letters, no watermark.')
GREEN = ('On a perfectly flat solid pure green #00FF00 background. Even flat lighting, crisp clean edges, NO shadow, NO ground, '
         'NO gradient, NO reflection, nothing touches the image edges. No text, no watermark.')

def plate(hexcode, name):
    return (f'On a perfectly flat solid pure {name} {hexcode} background. Even flat lighting, crisp clean edges, NO shadow, NO ground, '
            'NO gradient, NO reflection, nothing touches the image edges. No text, no watermark.')

# 聯動造型小人：照 image 1 右邊飛將那隻的畫法（同一隻奶白果凍穿上整套衣服＋兵器），一張一隻
OUTFIT = ('Image 1 shows our pet slime: LEFT is its everyday look, RIGHT is its crossover costume "Flying General". '
          'Draw ONE new crossover costume for the SAME slime in exactly the same way as the right one in image 1: same body shape, size, outline, '
          'glossy cute rendering, star-pupil sparkling eyes, small open happy mouth, rosy blush, small round nub hands, three-quarter view facing the viewer. '
          'The body is OPAQUE milky pearl white like mochi (not transparent, very little rainbow sheen). No crown. '
          'The whole slime with its weapon must fit inside the frame with wide margin, square composition, single character only. ')

ROUND = 'The top of the body is a smooth low round dome exactly like the slimes in image 1 (NOT pointed, NOT a teardrop, NOT taller than them). '
# 王子／公主分化（2026-10-09）：照 image 1 左邊平常那隻，同一隻長大一點點、加上身分配件；聯動造型兩種共用，只換平常的樣子
FORM = ('Image 1 LEFT shows our pet slime in its everyday look. Draw the SAME slime, same body shape, size, outline, glossy pearl-white mochi body '
        '(opaque milky white, very little rainbow sheen), star-pupil sparkling eyes, small open happy mouth, rosy blush, small round nub hands, '
        'three-quarter view facing the viewer, now dressed as ')

JOBS = {
    'outfit-lubu-baihua': (['slime', 'weapons', 'lubu_baihua'], OUTFIT + 'Costume of Lu Bu from image 3 (the hundred-flower battle robe) turned into a cute slime outfit: '
                    'a short dark crimson robe-cape printed with small pale pink flower blossoms, black and gold armor trim and a black-gold waist belt, '
                    'a small gold war ornament on top of its head with two long red braided cords hanging down behind (not a royal crown), red eyes. ' + 'Weapon: Lu Bu\'s Sky Piercer halberd exactly as in image 2 (leftmost; the halberd drawn in image 1 is WRONG, ignore it): a long dark pole, a straight spear tip on top, '
                    'and TWO identical crescent moon blades mirrored symmetrically on BOTH sides just below the tip, a red tassel under the blades, a pointed metal butt at the bottom. '
                    'Held upright by one nub hand beside the body, blades at the top. ' + ROUND + plate('#00FF00', 'green')),
    'outfit-lubu-heijin': (['slime', 'weapons', 'lubu_heijin'], OUTFIT + 'Costume of Lu Bu from image 3 (the black and gold armor) turned into a cute slime outfit: '
                    'a small black lamellar chest armor with ornate gold trim and a gold beast-face shoulder guard, a red robe-skirt with gold pattern hanging from the waist, '
                    'a small gold war ornament on top of its head with two long red braided cords hanging down behind (not a royal crown), red eyes. ' + 'Weapon: Lu Bu\'s Sky Piercer halberd exactly as in image 2 (leftmost; the halberd drawn in image 1 is WRONG, ignore it): a long dark pole, a straight spear tip on top, '
                    'and TWO identical crescent moon blades mirrored symmetrically on BOTH sides just below the tip, a red tassel under the blades, a pointed metal butt at the bottom. '
                    'Held upright by one nub hand beside the body, blades at the top. ' + ROUND + plate('#00FF00', 'green')),
    'outfit-liubei': (['slime', 'weapons', 'liubei_armor', 'liubei_pose'], OUTFIT + 'Costume of Liu Bei from image 3 (her short battle armor) turned into a cute slime outfit: '
                      'a small green metal chest plate, ONE green shoulder guard on the slime\'s left side only, small green bracers on both nub hands, '
                      'a short white single-layer skirt with green-trimmed belt around the lower body, a light green ribbon tying a small black hair tuft at the back, warm brown eyes. '
                      'Weapon like Liu Bei in image 4: the twin swords of Liu Bei exactly as in image 2 (third from left, two straight double-edged jian swords with gold guards and '
                      'dark green grips), drawn, ONE sword in EACH nub hand: the left hand on the left side of the body and the right hand on the right side, each nub hand wrapped firmly around its sword grip, '
                      'both swords held upright and parallel with blades pointing straight up beside the body, the swords do NOT cross and do NOT overlap the face or body. ' + ROUND + plate('#0000FF', 'blue')),
    'outfit-guanyu': (['slime', 'weapons', 'guanyu_armor'], OUTFIT + 'Costume of Guan Yu from image 3 (her battle armor) turned into a cute slime outfit: '
                      'a deep green fitted robe-armor with gold dragon embroidery and a gold waist belt with a small red knot, ONE ornate gold shoulder guard, '
                      'a long red cape with gold trim flowing behind, a very long black braid with a red tassel hanging down one side, amber eyes with a slightly proud brave look but still smiling. '
                      'Weapon: the Green Dragon Crescent Blade exactly as in image 2 (fourth from left: a long pole with one large curved crescent glaive blade on top, '
                      'gold dragon on the blade, red tassel under the blade), held upright by one nub hand beside the body, blade at the top. ' + ROUND + plate('#0000FF', 'blue')),
    'outfit-zhangfei': (['slime', 'weapons', 'zhangfei_armor'], OUTFIT + 'Costume of Zhang Fei from image 3 (her battle armor) turned into a cute slime outfit: '
                        'a small black leather chest armor with gold rivets, a black choker collar, black bracers on both nub hands, a gold lion-face belt buckle with a red cord, '
                        'a short black lamellar armor skirt around the lower body, a red hair ribbon tying a high dark brown ponytail on top, amber eyes, a cheeky grin showing one tiny fang. '
                        'Weapon: the Serpent Spear exactly as in image 2 (rightmost: a long pole with ONE wavy snake-shaped blade only at the top, a red tassel under it, '
                        'red lower shaft, and a plain blunt round metal cap at the bottom end, NOT a second blade), held upright by one nub hand beside the body. ' + ROUND + plate('#00FF00', 'green')),
    'outfit-diaochan': (['slime', 'diaochan', 'handkerchief'], OUTFIT + 'Costume of Diaochan from image 2 (her elegant lavender and white robes) turned into a cute slime outfit: '
                        'a soft white layered robe-skirt with pale lavender sash and flowing translucent lavender ribbons around the lower body, '
                        'a small dark brown hair bun on top with a delicate silver hairpin and tiny dangling ornament, dark brown eyes, gentle shy smile. '
                        'No weapon. Instead one nub hand holds up the handkerchief from image 3 beside the body: a small square of white silk with red plum blossoms '
                        'embroidered in one corner and a red tassel with a white jade bead hanging from that corner. ' + ROUND + plate('#00FF00', 'green')),
    'outfit-weixu': (['slime', 'weixu', 'w_weixu'], OUTFIT + 'Costume of Wei Xu from image 2 (a veteran soldier in iron-grey lamellar armor) turned into a cute slime outfit: '
                     'a small iron-grey lamellar chest armor made of little riveted plates, shoulder plates on both sides, an earth-brown rough cloth robe-skirt under the armor '
                     'around the lower body, a dark brown leather belt, a small messy dark brown hair topknot on top tied with a brown cord, dark brown eyes, a steady kind smile. '
                     'Weapon: the ring-pommel saber exactly as in image 3: a straight single-edged iron-grey blade with forge marks, NO hand guard, dark cord-wrapped grip, '
                     'a plain iron ring at the end of the grip, no decoration. Held upright by one nub hand beside the body, blade pointing up, ring at the bottom. ' + ROUND + plate('#00FF00', 'green')),
    'outfit-quan': (['slime', 'quan', 'w_quan'], OUTFIT + 'Costume of Lu Quan from image 2 (a sixteen-year-old archer girl) turned into a cute slime outfit: '
                    'a short cream-white cross-collar top with green leaf embroidery, a sage green short layered skirt around the lower body, a brown leather belt, '
                    'small dark brown leather bracers on both nub hands, a high dark brown ponytail on top tied with a long green ribbon, amber eyes, a bright confident smile. '
                    'Weapon: the small wooden bow exactly as in image 3: a dark brown carved wooden bow with a light green cloth wrap at the grip and a thin string, already strung. '
                    'Held upright by one nub hand gripping the middle of the bow, beside the body, like an archer holding a bow at rest: the STRING is on the side facing the slime body (between the bow and the body), '
                    'and the curved wooden limbs bulge OUTWARD away from the body. No arrows, no quiver. ' + ROUND + plate('#0000FF', 'blue')),   # 洋紅幕會吃掉帶粉的奶白身體（內部半透明 7.9 萬 px）   # 2026-10-10 作者：弓拿反了（第一版弦朝外、弓背朝身體）
    'outfit-xiang': (['slime', 'xiang', 'w_xiang'], OUTFIT + 'Costume of Yan Xiang from image 2 (a calm woman in plain grey-blue and earth-brown cloth robes) turned into a cute slime outfit: '
                     'a plain grey-blue cross-collar robe top with cream inner collar, a long earth-brown wrap skirt with a brown sash around the lower body, '
                     'only a small dark brown hair bun on the very top held by one simple wooden hairpin, the rest of the round dome stays bare pearl white (NO hair covering the head, NO bangs, like the bun in image 1 style), '
                     'warm tea-brown eyes, a gentle quiet smile. No jewelry. '
                     'Weapon: the iron scissors exactly as in image 3: Han dynasty spring scissors made of one bent iron strip, a round ring at the end wrapped with hemp cord, '
                     'TWO flat dark iron blades clearly visible as a pair, slightly open in a narrow V so they read as scissors (not a knife). Held upright by one nub hand beside the body, blades pointing up, ring at the bottom. ' + ROUND + plate('#00FF00', 'green')),
    # 姓氏玉珮：縮到地圖大小只認得出「奶白圓球＋大兵器」，作者要一個明顯的標誌；大字胸章作者嫌廉價，2026-10-08 改成腰間垂掛的雕花玉珮
    **{f'pendant-{n}': ([f'raw-{n}'], 'Edit image 1. Keep EVERYTHING exactly the same: the slime, face, costume, hair, weapon, pose, colors, framing, size and the flat '
                        f'background color. Only ADD one elegant noble pendant hanging from the front center of the waist belt: a small round {mat} disc pendant '
                        f'with a finely carved gold filigree rim of cloud scrolls, the single Traditional Chinese character 「{ch}」 carved in delicate low relief in its center '
                        f'(small, refined, like an heirloom seal, NOT a big sign), hanging on a short {cord} cord with a knot, and a long silky {cord} tassel below it. '
                        'Luxurious, precious, jewelry quality. The pendant is about one quarter of the body width. The character must be exactly '
                        f'「{ch}」, written correctly, no other text anywhere.')
       for n, ch, mat, cord in (('lubu-baihua', '呂', 'polished gold with a crimson enamel center', 'crimson red'), ('liubei', '劉', 'white jade', 'jade green'),
                                ('guanyu', '關', 'deep green jade', 'crimson red'), ('zhangfei', '張', 'black onyx with gold', 'crimson red'),
                                ('diaochan', '貂', 'pale lavender jade', 'soft purple'),
                                ('weixu', '魏', 'smoky grey jade', 'dark brown'), ('quan', '呂', 'pale green jade', 'leaf green'), ('xiang', '嚴', 'blue-grey jade', 'slate blue'))},
    'bg-capital': (['scene'], 'A floating cloud kingdom seen from a distance in the morning: white castle towers and small houses on floating islands among soft clouds, '
                   'and in the very center a huge gentle tree of life with pale golden leaves; hanging from one branch is a single small translucent rainbow jelly egg '
                   'with a tiny golden crown on top. ' + SCENE),
    'bg-courtyard': (['scene'], 'A peaceful palace courtyard under the huge tree of life: green lawn with scattered pale golden fallen leaves, a small round stone fountain, '
                     'a wooden broom leaning against a bench, warm dappled sunlight through the leaves. ' + SCENE),
    'cg-egg-feet': (['scene'], 'Low close-up on a lawn with scattered pale golden fallen leaves: a small translucent rainbow jelly egg with a tiny golden crown stuck on its top '
                    'rests right beside the toe of one small brown leather shoe; the bristles of a wooden broom lie at the edge of the frame. '
                    'Only the shoe tip is visible, no person. ' + SCENE),
    'bg-throne': (['scene'], 'A cozy small throne room, not grand: a low round throne made of an enormous soft honey-colored cushion with a gentle golden frame, '
                  'cream walls, pastel banners with a small crown emblem, tall window with clouds, a few potted plants, warm light. The throne is empty. ' + SCENE),
    'cg-hatch': (['slime', 'scene'], 'Inside a cozy nursery on a fluffy white cloud-shaped rug: a translucent rainbow jelly egg has just split into two shell halves, '
                 'and the baby slime from image 1 (left character: opaque milky pearl-white round slime, big sparkling star-pupil eyes, small open happy mouth, rosy blush, '
                 'tiny golden crown tilted on its head) pops out between the halves with a few sparkles, blinking up at the viewer. '
                 'Honey oak floor and soft cushions around, warm afternoon sunbeams. Scene style from image 2. WIDE LANDSCAPE 16:9. No people, no text, no watermark.'),
    'cg-egg-rug': (['scene'], 'Inside the same cozy nursery as the scene reference: a single small translucent rainbow jelly egg with a tiny golden crown on top '
                   'sits alone in the middle of a fluffy white cloud-shaped rug; inside the egg a tiny warm light glows softly. The egg is whole and unbroken, '
                   'nothing has hatched, no creature anywhere. Honey oak floor, pink and cream cushions, round crib in the background, warm afternoon sunbeams. ' + SCENE),
    'sheet-king': (['style', 'slime'], 'Two separate items side by side with wide empty space between them. '
                   'Left: an old King Slime character portrait, large round opaque jelly slime colored like warm amber honey, with a fluffy white mustache and bushy white eyebrows, '
                   'sleepy kind half-closed eyes, a slightly too big golden crown with rounded ball tips sitting a bit crooked, a tiny red velvet cape with white ermine trim; '
                   'same glossy cute rendering, outline and face style as the slimes in the references, three-quarter view facing the viewer. '
                   'Right: a thick royal diary book, closed, pink leather cover with a small golden crown emblem and a red ribbon bookmark hanging out, slightly angled. ' + GREEN),
    'sheet-props': (['style'], 'Three separate small game props in a row with wide empty space between them, top-down three-quarter view, same glossy cute rendering as the reference. '
                    'Left: a round wicker snack basket with a pink gingham cloth, holding a strawberry pudding and a small stack of honey pancakes. '
                    'Middle: one glowing golden star-shaped konpeito candy, honey-gold, glossy, with a few tiny sparkles, cute and clean (this is the pet\'s golden poop, it must look like candy). '
                    'Right: a single shiny gold coin with a small crown emblem embossed on it. ' + GREEN),
    'sheet-gift': (['style'], 'One single cute game prop, three-quarter top-down view, same glossy cute rendering as the reference: a small royal gift box wrapped in cream paper '
                   'with a pink satin ribbon bow on top and a round golden wax seal with a tiny crown, a few soft sparkles around it. ' + GREEN),
    'form-prince': (['slime'], FORM + 'a little PRINCE: the same small gold crown with a red gem a bit taller and grander, a short royal blue velvet cape with gold trim '
                    'draped over its back and fastened at the front with a round gold clasp, deep blue eyes. Cute and dignified. Single character only, whole slime inside the frame with wide margin, square composition. '
                    + ROUND + plate('#00FF00', 'green')),
    'form-hime': (['slime'], FORM + 'a little PRINCESS: instead of the crown a small delicate gold tiara with a pink heart gem, a pink satin ribbon bow on one side of the head, '
                    'a soft frilly pastel pink lace skirt-frill around the bottom of the body, warm rose-pink eyes. Cute and elegant. Single character only, whole slime inside the frame with wide margin, square composition. '
                    + ROUND + plate('#00FF00', 'green')),   # 粉色緞帶跟洋紅幕撞色，用綠幕
    # 競技場成年禮（2026-10-09）：背景一張、表演 CG 依分化各一張
    'bg-arena': (['scene'], 'A small round royal arena in the cloud kingdom, cute and festive, not violent: pale stone ring of tiered seats decorated with pastel banners and flower garlands, '
                 'a fluffy white cloud-shaped rug laid in the center of the sandy floor, a small honey-colored cushion seat for the king at the front row, blue sky with soft clouds, '
                 'confetti and sparkles in the air, warm morning light. The seats are filled with many tiny round pastel slimes as the audience, all small and far away. ' + SCENE),
    'cg-adult-prince': (['form-prince', 'scene'], 'The little prince slime from image 1 (keep it exactly: opaque milky pearl-white round body, gold crown with red gem, short royal blue cape with gold clasp, '
                 'deep blue sparkling star-pupil eyes) stands proudly on a fluffy white cloud-shaped rug in the center of a small festive royal arena, holding up a soft toy wooden sword '
                 'in one nub hand; a straw training dummy beside it is tipped over. Tiers of tiny pastel slime spectators cheering in the background, confetti, blue sky. '
                 'Scene style from image 2. WIDE LANDSCAPE 16:9. No humans, no text, no watermark.'),
    'cg-adult-hime': (['form-hime', 'scene'], 'The little princess slime from image 1 (keep it exactly: opaque milky pearl-white round body, small gold tiara with a pink heart gem, pink satin ribbon bow, '
                 'pink lace skirt-frill, rose-pink sparkling star-pupil eyes) sits neatly on a fluffy white cloud-shaped rug in the center of a small festive royal arena, '
                 'pouring tea from a tiny porcelain teapot into a little teacup, a tray of star-shaped cookies beside it, the tea slightly overflowing the cup rim. '
                 'Tiers of tiny pastel slime spectators cheering in the background, confetti, blue sky. Scene style from image 2. WIDE LANDSCAPE 16:9. No humans, no text, no watermark.'),
}


def run(key):
    out = ROOT / 'art/raw' / f'{key}.png'
    if out.exists(): return f'skip {key}'
    refs, prompt = JOBS[key]
    r = subprocess.run(['bash', str(GEN), prompt, str(out)] + [str(ROOT / REF[x]) for x in refs],
                       cwd=ROOT / 'art/raw', stdin=subprocess.DEVNULL, capture_output=True, text=True)
    return f'{key}: {"ok" if out.exists() else "FAIL " + r.stderr[-300:]}'


if __name__ == '__main__':
    keys = sys.argv[1:] or list(JOBS)
    refs_ready()
    with cf.ThreadPoolExecutor(3) as ex:
        for msg in ex.map(run, keys): print(msg, flush=True)
