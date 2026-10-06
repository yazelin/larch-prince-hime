import json,urllib.request,os,time,base64,io,sys
from PIL import Image
K=open(os.path.expanduser('~/.config/larch/key')).read().strip()
P='https://larch.ink/api/agent/projects/project-6516bec7-4053-4a7c-a45e-2d739be40b12'
def req(m,path='',body=None,et=None):
    h={'Authorization':'Bearer '+K,'Content-Type':'application/json'}
    if et: h['If-Match']=et
    for t in range(8):
        r=urllib.request.Request(P+path,method=m,data=json.dumps(body).encode() if body is not None else None,headers=h)
        try:
            with urllib.request.urlopen(r,timeout=600) as x: return x.headers.get('ETag'),json.loads(x.read() or b'{}')
        except urllib.error.HTTPError as e:
            msg=e.read()[:300]
            if e.code==429: time.sleep(30); continue
            print(e.code,msg); raise
src,name,summary=sys.argv[1],sys.argv[2],sys.argv[3]
which=sys.argv[4] if len(sys.argv)>4 else 'both'   # thumb：只換專案縮圖；cover：只換標題畫面封面
bio=io.BytesIO(); Image.open(src).save(bio,'WEBP',quality=90)
_,j=req('POST','/media',{"name":name,"mimeType":"image/webp","category":"ui","base64":base64.b64encode(bio.getvalue()).decode()}); url=j['asset']['url']
time.sleep(4)
canon=lambda x: json.dumps(x,ensure_ascii=False,sort_keys=True)
et,p=req('GET'); p=p.get('project',p)
json.dump(p,open(f'snapshots/cover_{int(time.time())}.json','w'),ensure_ascii=False)
boards=json.loads(json.dumps(p.get('boards') or [])); keep={k:canon(p.get(k)) for k in ('characters','variables','languages','name','description','nodes','edges')}  # ponytail: 舊格式專案沒有 boards，nodes/edges 一起比對; pl=canon(p['settings'].get('plugins'))
if which in ('both','cover'): p['settings']['titleCoverImage']=url
if which in ('both','thumb'): p['settings']['projectThumbnail']=url
et,_=req('PUT','',{"project":p,"summary":summary},et)
for b in boards: et,_=req('PUT','/boards/'+b['id'],{"name":b['name'],"nodes":b['nodes'],"edges":b['edges'],"summary":"換封面後把版子原樣推回"},et)
_,q=req('GET'); q=q.get('project',q); g={b['id']:b for b in q.get('boards') or []}
for b in boards: assert canon(g[b['id']]['nodes'])==canon(b['nodes']) and canon(g[b['id']]['edges'])==canon(b['edges']),b['id']
for k,v in keep.items(): assert canon(q.get(k))==v,k
assert canon(q['settings'].get('plugins'))==pl
print('OK','cover',q['settings'].get('titleCoverImage','')[-26:],'thumb',q['settings'].get('projectThumbnail','')[-26:],len(boards),'boards verified')
