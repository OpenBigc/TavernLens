"""Read-only Firestone client feeds, with explicit freshness and rank scopes."""
import gzip
import hashlib
import json
import math
import time
import threading
import urllib.request
from pathlib import Path
from ..models import Table, Stat

BASE = 'https://static.zerotoheroes.com/api/bgs'


def number(value):
    return isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value)


def parse(kind, data, mmr):
    key = 'heroStats' if kind == 'hero' else 'trinketStats'
    if not isinstance(data,dict) or not isinstance(data.get(key),list):
        raise ValueError('统计接口格式变化')
    rows = {}
    for r in data[key]:
        if not isinstance(r,dict):
            continue
        cid = r.get('heroCardId' if kind == 'hero' else 'trinketCardId')
        if not isinstance(cid,str):
            continue
        n, avg = r.get('dataPoints',0), r.get('averagePosition' if kind == 'hero' else 'averagePlacement')
        pick, scope = None, 'selected'
        if kind == 'hero':
            offered, picked = r.get('totalOffered',0), r.get('totalPicked',0)
            if number(offered) and number(picked) and offered>0 and 0<=picked<=offered:
                pick = picked / offered * 100
        else:
            scope = 'all' if mmr != '100' else 'selected'
            rate = r.get('pickRate')
            if number(rate) and 0<=rate<=1:
                pick = rate * 100
            inline = r.get('averagePlacementAtMmr') or []
            match = next((x for x in inline if isinstance(x,dict) and str(x.get('mmr'))==mmr),None)
            if match is not None:
                avg,n = match.get('placement'),match.get('dataPoints',0)
            elif mmr != '100':
                avg,n = None,0
        if not number(avg) or not 1<=avg<=8:
            avg = None
        n = int(n) if number(n) and n>=0 else 0
        if n == 0:
            avg = None
        rows[cid] = Stat(avg,n,pick,scope)
    return rows


class Firestone:
    def __init__(self, cache: Path, ttl=3600, fetch=None):
        self.cache,self.ttl,self.fetch = cache,ttl,fetch or self._fetch

    @staticmethod
    def _fetch(url):
        request = urllib.request.Request(url,headers={'User-Agent':'TavernLens/0.1 (+personal BG stats overlay)','Accept-Encoding':'gzip'})
        with urllib.request.urlopen(request,timeout=15) as r:
            raw = r.read(8_000_001)
        if len(raw)>8_000_000:
            raise ValueError('统计响应过大')
        if raw[:2]==b'\x1f\x8b':
            raw = gzip.decompress(raw)
        return json.loads(raw)

    def load(self, kind, mmr, period, mode='solo', refresh=False):
        if kind=='trinket' and mode=='duo':
            return Table(kind,error='尚未配置双人饰品统计')
        route = ('duo/' if mode=='duo' else '') + f'hero-stats/mmr-{mmr}/{period}' if kind=='hero' else f'trinket-stats/{period}'
        url = f'{BASE}/{route}/overview-from-hourly.gz.json'
        path = self.cache / (hashlib.sha256(url.encode()).hexdigest()[:20]+'.json')
        old = None
        try:
            old = json.loads(path.read_text(encoding='utf-8'))
            parse(kind,old['data'],mmr)
            if not refresh and 0<=time.time()-old['fetched_at']<self.ttl:
                return self._table(kind,old,mmr)
        except (OSError,ValueError,KeyError,TypeError):
            old = None
        try:
            blob = {'fetched_at':time.time(),'data':self.fetch(url)}
            parse(kind,blob['data'],mmr)
            self.cache.mkdir(parents=True,exist_ok=True)
            temporary = path.with_suffix(f'.{threading.get_ident()}.tmp')
            temporary.write_text(json.dumps(blob),encoding='utf-8')
            temporary.replace(path)
            return self._table(kind,blob,mmr)
        except Exception as e:
            # Keep data usable when the feed is temporarily unavailable, but
            # expose stale=True so UI never silently labels it fresh.
            if old:
                return self._table(kind,old,mmr,stale=True,error=str(e))
            return Table(kind,error=str(e))

    @staticmethod
    def _table(kind, blob, mmr, stale=False, error=None):
        data = blob['data']
        updated = data.get('lastUpdateDate')
        return Table(kind,parse(kind,data,mmr),updated if isinstance(updated,str) else None,blob['fetched_at'],stale,error)
