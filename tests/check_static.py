"""靜態檢查：組出專案後掃一遍會讓播放器壞掉、或會靜默失效的寫法。
用法：python3 tests/check_static.py（正常與 --fast 兩種都檢查）"""
import json, sys, pathlib, importlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))


def steps(actions):
    for a in actions:
        yield a
        for k in ('choice', 'random'):
            for o in (a.get(k) or {}).get('options', []): yield from steps(o.get('actions', []))


def check(flags):
    sys.argv = ['build.py'] + flags
    import build; importlib.reload(build)
    p = build.build()
    bad = []
    ids = {n['id'] for n in p['nodes']}
    bad += [f'連線指到不存在的卡：{e}' for e in p['edges'] if e['source'] not in ids or e['target'] not in ids]
    declared = {v['name'] for v in p['variables']}
    for n in p['nodes']:
        if n['data'].get('pluginCardId') != 'map': continue
        m = json.loads(n['data']['pluginValues']['map'])
        gate = set(n['data']['pluginReadVars']) & set(n['data']['pluginWriteVars'])
        for e in m['events']:
            acts = e.get('actions', []) + [a for pg in e.get('pages', []) for a in pg.get('actions', [])]
            conds = e.get('conditions', []) + [c for pg in e.get('pages', []) for c in pg.get('conditions', [])]
            for a in steps(acts):
                if a['kind'] == 'wait' and not 0 <= a['amount'] <= 9999: bad.append(f'{e["id"]}：wait {a["amount"]} 超過 0–9999（播放器會整個壞掉）')
                if a['kind'] == 'variable' and a['variable'] not in gate: bad.append(f'{e["id"]}：寫 {a["variable"]} 但地圖卡的讀寫名單沒有它（會被靜默丟掉）')
                if 'loop' in a: conds += a['loop'].get('until', [])
            bad += [f'{e["id"]}：條件用到沒宣告的變數 {c["variable"]}' for c in conds if c['kind'] == 'variable' and c['variable'] not in declared]
        bad += [f'任務提示用到沒宣告的變數 {c["variable"]}' for g in m.get('guidance', []) for c in g['conditions'] if c['variable'] not in declared]
        W = m['width']; wall = {(i % W, i // W) for i, t in enumerate(m['layers'][0]['tiles']) if t}
        for e in m['events']:
            xy = (e['x'], e['y'])
            standable = e.get('actor') == 'player' or e['id'].startswith('poop_') or e['trigger'] == 'auto' and e['id'] == 'intro'
            if standable and xy in wall: bad.append(f'{e["id"]} 在牆格 {xy}，站不上去')
            if e['trigger'] == 'action' and (e.get('actions') or e.get('pages')) and e.get('marker'):
                free = [(e['x'] + dx, e['y'] + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
                        if 0 <= e['x'] + dx < W and 0 <= e['y'] + dy < m['height'] and (e['x'] + dx, e['y'] + dy) not in wall]
                if not free: bad.append(f'{e["id"]} {xy} 四周都是牆，走不到')
    for pid, pl in p['settings']['plugins'].items():
        for h in (pl.get('playback') or {}).get('huds', []):
            bad += [f'HUD {h["id"]} 讀寫沒宣告的變數 {v}' for v in h.get('readVariables', []) + h.get('writeVariables', []) if v not in declared]
    return bad


if __name__ == '__main__':
    problems = check([]) + check(['--fast'])
    print('\n'.join(problems) if problems else 'OK 靜態檢查通過')
    sys.exit(1 if problems else 0)
