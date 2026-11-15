# Adapted from BattlegroundsHelp/bgtracker (MIT), commit 2dd836f.
# Copyright (c) 2026 the bgtracker contributors. See THIRD_PARTY_NOTICES.md.
import re
TRINKET_OPTIONS = 4

TS_RE = re.compile('^D ([\\d:.]+)')

TAGPOS_RE = re.compile('^D (?P<ts>[\\d:.]+).*?TAG_CHANGE Entity=\\[entityName=.+? id=(?P<id>\\d+) zone=HAND [^\\]]*\\] tag=ZONE_POSITION value=(?P<pos>\\d+)')

CHANGE_RE = re.compile('CHANGE_ENTITY - Updating Entity=\\[entityName=.+? id=(?P<id>\\d+) zone=HAND [^\\]]*\\] CardID=(?P<card>[\\w_]+)')

CHOICE_HDR_RE = re.compile('^D [\\d:.]+ GameState\\.DebugPrintEntityChoices\\(\\) - id=\\d+ Player=')

CHOICE_ENT_RE = re.compile('DebugPrintEntityChoices\\(\\) -   Entities\\[(?P<idx>\\d+)\\]=\\[entityName=(?P<name>.+?) id=\\d+ [^\\]]*cardId=(?P<card>[\\w_]+)')

class ChoiceReader:

    def __init__(self):
        self.cur = None

    def feed(self, line: str):
        if 'DebugPrintEntityChoices' not in line:
            if self.cur:
                done, self.cur = (self.cur, None)
                return done or None
            return None
        if CHOICE_HDR_RE.match(line):
            self.cur = []
        m = CHOICE_ENT_RE.search(line)
        if m and self.cur is not None:
            self.cur.append((int(m.group('idx')), m.group('name'), m.group('card')))
        return None

ENTITY_RE = re.compile('^D (?P<ts>[\\d:.]+).*?FULL_ENTITY - Updating \\[entityName=(?P<name>.*?) id=(?P<id>\\d+) zone=(?P<zone>\\w+) zonePos=(?P<pos>\\d+) cardId=(?P<card>[\\w_]+) player=(?P<player>\\d+)\\]')

def normalize(card_id: str, table: dict) -> str:
    if card_id in table:
        return card_id
    base = re.sub('_SKIN_.*$', '', card_id)
    return base if base in table else card_id

class OfferDetector:

    def __init__(self, heroes: dict, trinkets: dict, universe: dict | None=None, names: dict | None=None):
        self.heroes = universe if universe is not None else heroes
        self.trinkets = trinkets
        self.names = names or {}
        self.ts = None
        self.buf = []
        self.player = None
        self.known = set()
        self.new_game = False
        self._live = {}
        self._live_ts = None
        self.refresh = None

    def feed(self, line: str):
        m = ENTITY_RE.match(line)
        if not m:
            if self.buf or self._live:
                ch = CHANGE_RE.search(line)
                if ch:
                    eid, newc = (int(ch.group('id')), ch.group('card'))
                    newn = self.names.get(newc, newc)
                    for ent in self.buf:
                        if ent[4] == eid:
                            ent[1], ent[2] = (newn, newc)
                    if eid in self._live:
                        e = self._live[eid]
                        e[0], e[1] = (newn, newc)
                        poss = [q for _, _, q in self._live.values()]
                        if min(poss) >= 1 and len(set(poss)) == len(poss):
                            self.refresh = ('hero choice', [(n, c, q) for n, c, q in self._live.values()])
                g = TAGPOS_RE.match(line)
                if g:
                    eid, p = (int(g.group('id')), int(g.group('pos')))
                    for ent in self.buf:
                        if ent[4] == eid:
                            ent[3] = p
                    if eid in self._live:
                        ent = self._live[eid]
                        if p != ent[2]:
                            ent[2] = p
                            poss = [q for _, _, q in self._live.values()]
                            if min(poss) >= 1 and len(set(poss)) == len(poss):
                                self.refresh = ('hero choice', [(n, c, q) for n, c, q in self._live.values()])
            t = TS_RE.match(line)
            if t and self.buf and (t.group(1) != self.ts):
                return self.flush()
            return None
        card, zone = (m['card'], m['zone'])
        kind = None
        if zone == 'HAND' and normalize(card, self.heroes) in self.heroes:
            self.player = m['player']
            kind = 'hero choice'
        elif zone == 'SETASIDE' and card in self.trinkets:
            if self.player is not None and m['player'] != self.player:
                return None
            kind = 'trinket choice'
        else:
            return None
        flushed = None
        if m['ts'] != self.ts:
            flushed = self.flush()
            self.ts = m['ts']
            if kind == 'hero choice':
                self.known = set()
                self.new_game = True
        if m['id'] in self.known:
            return flushed
        self.known.add(m['id'])
        self.buf.append([kind, m['name'], card, int(m['pos'] or 0), int(m['id'])])
        return flushed

    def flush(self):
        buf, self.buf = (self.buf, [])
        if len(buf) < 2:
            return None
        kind = buf[0][0]
        if kind == 'trinket choice' and len(buf) != TRINKET_OPTIONS:
            return None
        if kind == 'hero choice':
            self._live = {i: [n, c, p] for _, n, c, p, i in buf}
        else:
            self._live = {}
        self._live_ts = None
        return (kind, [(n, c, p) for _, n, c, p, i in buf])

    def reset(self):
        self.ts = None
        self.buf = []
        self.player = None
        self.known = set()
        self._live = {}
        self._live_ts = None
        self.refresh = None
