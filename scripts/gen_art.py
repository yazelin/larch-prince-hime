"""序章美術工作清單：每張固定帶畫風定錨，產到 art/raw/<key>.png，已存在就跳過。
用法：python3 scripts/gen_art.py [key ...]   （不帶參數＝全部，三張並行）"""
import subprocess, sys, pathlib, concurrent.futures as cf
ROOT = pathlib.Path(__file__).resolve().parent.parent
GEN = pathlib.Path.home() / '.claude/skills/codex-imagegen/codex-imagegen.sh'
# 定錨的來源都是 repo 裡的 webp，產圖時才轉成 png 放進 art/raw/_ref（codex 吃 png 最穩；art/raw 不進 git）
REF_SRC = {'scene': 'assets/cover/cover-v3.webp', 'style': 'assets/concept/style-test-1.webp', 'slime': 'assets/concept/sprite-raw-green.webp'}
REF = {k: f'art/raw/_ref/{k}.png' for k in REF_SRC}


def refs_ready():
    from PIL import Image
    (ROOT / 'art/raw/_ref').mkdir(parents=True, exist_ok=True)
    for k, src in REF_SRC.items():
        if not (ROOT / REF[k]).exists(): Image.open(ROOT / src).save(ROOT / REF[k])

SCENE = ('Painted in the exact rendering style and palette of the scene reference image (glossy cute anime storybook, warm afternoon light, '
         'soft low-saturation oat cream, honey, peach, mint and mist blue). Calm and uncluttered, healing mood. '
         'WIDE LANDSCAPE 16:9. No people, no text, no letters, no watermark.')
GREEN = ('On a perfectly flat solid pure green #00FF00 background. Even flat lighting, crisp clean edges, NO shadow, NO ground, '
         'NO gradient, NO reflection, nothing touches the image edges. No text, no watermark.')

JOBS = {
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
