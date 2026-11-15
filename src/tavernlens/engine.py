"""Pure log state machine: offered cards and their on-screen lifetime only."""
import re
from .detection import OfferDetector, ChoiceReader, normalize
from .models import Offer, Option

COMBAT = re.compile(r'tag=BACON_CURRENT_COMBAT_PLAYER_ID value=(\d+)')
REROLL = re.compile(r'cardId=TB_BaconShop_8p_Reroll_Button player=(\d+)')


class Engine:
    def __init__(self, catalog):
        self.catalog = catalog
        self.heroes = {cid: {} for cid in catalog['heroes']}
        self.trinkets = {cid: {} for cid in catalog['trinkets']}
        self.detector = OfferDetector(self.heroes,self.trinkets,names=catalog['names'])
        self.choices = ChoiceReader()
        self.phase = 'recruit'
        self.active = None
        self.pending = None

    def name(self, cid, fallback):
        names = self.catalog['names']
        return names.get(normalize(cid,names),fallback)

    def show(self, kind, options):
        self.active = Offer(kind,tuple(Option(cid,self.name(cid,nm),slot) for slot,nm,cid in options))
        return [('offer',self.active)]

    def hide(self):
        if self.active is None:
            return []
        self.active = None
        return [('hide',None)]

    def hero(self, event):
        if event and event[0]=='hero choice':
            slots = [slot for _,_,slot in event[1]]
            if not 2<=len(slots)<=4 or set(slots)!=set(range(1,len(slots)+1)):
                return []
            return self.show('hero',[(slot,nm,cid) for nm,cid,slot in event[1]])
        return []

    def choice(self, block):
        ids = [cid for _,_,cid in block]
        if len(ids)==4 and len(set(ids))==4 and all(cid in self.trinkets for cid in ids):
            ordered = [(i+1,nm,cid) for i,nm,cid in sorted(block)]
            if self.phase=='combat':
                self.pending = ordered
                return []
            return self.show('trinket',ordered)
        # A subsequent discover proves an old trinket dialog has gone away.
        if self.active and self.active.kind=='trinket':
            return self.hide()
        return []

    def recruit(self):
        self.phase = 'recruit'
        if self.pending:
            choice,self.pending = self.pending,None
            return self.show('trinket',choice)
        return []

    def process(self, line):
        events = []
        event = self.detector.feed(line)
        if self.detector.new_game:
            self.detector.new_game = False
            events += self.hide()
            self.pending = None
            self.phase = 'recruit'
        events += self.hero(event)
        if self.detector.refresh:
            events += self.hero(self.detector.refresh)
            self.detector.refresh = None
        block = self.choices.feed(line)
        if block:
            events += self.choice(block)
        if self.active and self.active.kind=='hero' and 'PowerTaskList' in line and 'tag=CARDRACE value=' in line:
            events += self.hide()
            self.detector._live.clear()
        if 'PowerTaskList' in line:
            match = COMBAT.search(line)
            if match:
                if int(match[1]):
                    self.phase = 'combat'
                    events += self.hide()
                else:
                    events += self.recruit()
            # Recover from a missing screen combat-end marker using OUR roll.
            match = REROLL.search(line) if 'BLOCK_START' in line else None
            if match and match[1]==self.detector.player:
                if self.phase=='combat':
                    events += self.recruit()
                elif self.active and self.active.kind=='trinket':
                    events += self.hide()
        return events

    def idle(self):
        events = self.hero(self.detector.flush())
        if self.choices.cur and len(self.choices.cur)==4:
            block,self.choices.cur = self.choices.cur,None
            events += self.choice(block)
        return events
