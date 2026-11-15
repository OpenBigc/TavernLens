"""Refresh the shipped card catalog. Does not download statistics or artwork."""
import gzip
import json
import urllib.request
from pathlib import Path

url = 'https://api.hearthstonejson.com/v1/latest/zhCN/cards.json'
request = urllib.request.Request(url,headers={'User-Agent':'TavernLens/0.1','Accept-Encoding':'gzip'})
with urllib.request.urlopen(request,timeout=30) as response:
    raw = response.read()
if raw[:2]==b'\x1f\x8b':
    raw = gzip.decompress(raw)
cards = json.loads(raw)
heroes = [c['id'] for c in cards if c.get('battlegroundsHero')]
trinkets = [c['id'] for c in cards if c.get('type')=='BATTLEGROUND_TRINKET']
ids = set(heroes+trinkets)
data = {'heroes':heroes,'trinkets':trinkets,'names':{c['id']:c['name'] for c in cards if c.get('id') in ids}}
path = Path(__file__).resolve().parents[1]/'src/tavernlens/data/catalog.json'
path.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
print(f'{len(heroes)} heroes, {len(trinkets)} trinkets, {path.stat().st_size} bytes')
