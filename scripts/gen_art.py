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
           'lubu_baihua': TAOYUAN / 'cast/lubu/百花戰甲_raw.webp', 'lubu_heijin': TAOYUAN / 'buchan/cg_v/anchor_lubu_flatboots_2_v2.webp', 'zhangfei': TAOYUAN / 'cast/anchor_zhangfei.webp'}
REF = {k: f'art/raw/_ref/{k}.png' for k in REF_SRC}


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
                      'Weapon and pose like Liu Bei in image 4: the twin swords of Liu Bei exactly as in image 2 (third from left, two straight double-edged jian swords with gold guards and '
                      'dark green grips), drawn, ONE sword gripped in EACH nub hand, the two blades crossed in an X in front of the lower body, tips pointing outward. ' + ROUND + plate('#0000FF', 'blue')),
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
