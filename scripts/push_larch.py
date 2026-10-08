"""把 build.py 的結果推上 Larch，圖片走 jsDelivr（釘在已 push 的 commit SHA）。
用法：python3 scripts/push_larch.py "改了什麼"
推之前：先 commit 並 push；推完要作者重新整理開著的編輯器分頁，舊分頁會把專案存回舊版。"""
import json, os, re, subprocess, sys, time, urllib.request, urllib.parse, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
PID = 'project-6516bec7-4053-4a7c-a45e-2d739be40b12'
API = f'https://larch.ink/api/agent/projects/{PID}'
KEY = open(os.path.expanduser('~/.config/larch/key')).read().strip()
# 只由產生器負責的設定鍵；其他設定（名稱、介紹、作者在網頁上調的）保留線上的
OWNED_SETTINGS = ['titleCoverImage', 'projectThumbnail', 'stageFit', 'keepActorsInFrame', 'titleScreenEnabled', 'titleScreen', 'customInterfaces']
OWNED_PLUGINS = ['larch-rpg-system', 'prince-hime']   # 產生器整份負責的插件設定（RPG 系統、時鐘 HUD）


def git(*a): return subprocess.run(['git', *a], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()


def req(method, body=None, etag=None, path=''):
    h = {'Authorization': 'Bearer ' + KEY, 'Content-Type': 'application/json'}
    if etag: h['If-Match'] = etag
    for _ in range(8):
        try:
            r = urllib.request.urlopen(urllib.request.Request(API + path, method=method, headers=h,
                                       data=json.dumps(body).encode() if body is not None else None), timeout=300)
            return r.headers.get('ETag'), json.loads(r.read() or b'{}')
        except urllib.error.HTTPError as e:
            if e.code == 429: time.sleep(30); continue
            print(e.code, e.read()[:300]); raise


def main(summary):
    if git('status', '--porcelain'): sys.exit('工作目錄有沒 commit 的修改，先 commit 並 push')
    git('fetch', '-q', 'origin')
    sha = git('rev-parse', 'HEAD')
    if sha != git('rev-parse', 'origin/main'): sys.exit('HEAD 還沒 push 到 origin/main，jsDelivr 讀不到')
    sys.argv.append(f'--cdn={sha}')
    sys.path.insert(0, str(ROOT / 'scripts')); import build
    built = build.build()
    urls = sorted(set(re.findall(r'https://cdn\.jsdelivr\.net/[^"\\]+', json.dumps(built, ensure_ascii=False))))   # 家具圖檔名是中文，ensure_ascii 會把網址切在 \u 那裡
    bad = []
    for u in urls:
        try: urllib.request.urlopen(urllib.request.Request(urllib.parse.quote(u, safe=':/@'), method='HEAD'), timeout=60)
        except Exception as e: bad.append((u, e))
    if bad: sys.exit(f'jsDelivr 讀不到：{bad}')
    print(f'{len(urls)} 個圖片網址都讀得到（@{sha[:7]}）')

    etag, live = req('GET'); live = live.get('project', live)
    (ROOT / 'snapshots').mkdir(exist_ok=True)
    (ROOT / f'snapshots/push_{int(time.time())}.json').write_text(json.dumps(live, ensure_ascii=False))
    p = json.loads(json.dumps(live))
    for k in ('boards', 'nodes', 'edges', 'variables', 'activeBoardId'): p[k] = built[k]
    for k in OWNED_SETTINGS: p['settings'][k] = built['settings'][k]
    for k in OWNED_PLUGINS: p['settings'].setdefault('plugins', {})[k] = built['settings']['plugins'][k]
    etag, _ = req('PUT', {'project': p, 'summary': summary}, etag)
    # 整包 PUT 會把同一出口的多條連線去重（開機分流就是兩條），白板一定要再用 PUT board 整張覆蓋一次
    for b in built['boards']:
        etag, _ = req('PUT', {'name': b['name'], 'nodes': b['nodes'], 'edges': b['edges'], 'summary': summary + '（白板）'}, etag, f'/boards/{b["id"]}')

    _, q = req('GET'); q = q.get('project', q)
    c = lambda x: json.dumps(x, ensure_ascii=False, sort_keys=True)
    qb = {b['id']: b for b in q.get('boards') or []}
    for b in built['boards']:
        assert c(qb[b['id']]['nodes']) == c(b['nodes']) and c(qb[b['id']]['edges']) == c(b['edges']), f'白板 {b["id"]} 讀回來不一樣'
    for k in OWNED_SETTINGS: assert c(q['settings'].get(k)) == c(built['settings'][k]), k
    for k in OWNED_PLUGINS: assert c(q['settings']['plugins'].get(k)) == c(built['settings']['plugins'][k]), f'插件設定 {k}'
    for k in ('name', 'description'): assert c(q.get(k)) == c(live.get(k)), f'{k} 被改到了'
    print('OK 推上 Larch：', len(built['nodes']), '張卡，讀回比對一致')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith('--') else '更新序章')
