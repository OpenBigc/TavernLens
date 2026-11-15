"""Pure log state machine: offered cards and their on-screen lifetime only."""
import re
from .detection import OfferDetector, ChoiceReader, normalize
from .models import Offer, Option

COMBAT = re.compile(r'tag=BACON_CURRENT_COMBAT_PLAYER_ID value=(\d+)')
REROLL = re.compile(r'cardId=TB_BaconShop_8p_Reroll_Button player=(\d+)')
CHOICE_ID = re.compile(r'GameState\.DebugPrintEntityChoices\(\) - id=(\d+) Player=')
CHOICE_SHOW = re.compile(r'ChoiceCardMgr\.WaitThenShowChoices\(\) - id=(\d+) BEGIN')
CHOICE_HIDE = re.compile(r'ChoiceCardMgr\.WaitThenHideChoicesFromPacket\(\) - id=(\d+) END WAIT')


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
        self.choice_id = None
        self.pending_id = None
        self.active_id = None
        self.dialogs = {}

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
        self.active_id = None
        return [('hide',None)]

    def hero(self, event):
        if event and event[0]=='hero choice':
            slots = [slot for _,_,slot in event[1]]
            if not 2<=len(slots)<=4 or set(slots)!=set(range(1,len(slots)+1)):
                return []
            return self.show('hero',[(slot,nm,cid) for nm,cid,slot in event[1]])
        return []

    def choice(self, block, dialog_id=None):
        ids = [cid for _,_,cid in block]
        if len(ids)==4 and len(set(ids))==4 and all(cid in self.trinkets for cid in ids):
            ordered = [(i+1,nm,cid) for i,nm,cid in sorted(block)]
            if dialog_id is not None:
                self.dialogs[dialog_id] = ordered
                # IDs only need to survive until this dialog is shown/hidden.
                while len(self.dialogs)>8:
                    self.dialogs.pop(next(iter(self.dialogs)))
            if self.phase=='combat':
                self.pending = ordered
                self.pending_id = dialog_id
                return []
            self.active_id = dialog_id
            return self.show('trinket',ordered)
        # Network packets can contain a future discover while the current
        # trinket dialog is still visible. Only its actual UI marker ends it.
        return []

    def recruit(self):
        self.phase = 'recruit'
        if self.pending:
            choice,self.pending = self.pending,None
            self.active_id,self.pending_id = self.pending_id,None
            return self.show('trinket',choice)
        return []

    def process(self, line):
        events = []
        event = self.detector.feed(line)
        if self.detector.new_game:
            self.detector.new_game = False
            events += self.hide()
            self.pending = None
            self.pending_id = self.active_id = self.choice_id = None
            self.dialogs.clear()
            self.phase = 'recruit'
        events += self.hero(event)
        if self.detector.refresh:
            events += self.hero(self.detector.refresh)
            self.detector.refresh = None
        match = CHOICE_ID.search(line)
        if match:
            self.choice_id = int(match[1])
        block = self.choices.feed(line)
        if block:
            events += self.choice(block,self.choice_id)
        match = CHOICE_SHOW.search(line)
        if match:
            dialog_id = int(match[1])
            if dialog_id in self.dialogs:
                # This is the real on-screen start, even when the combat-end
                # tag is missing. Automatic tavern refreshes cannot cancel it.
                self.phase = 'recruit'
                self.pending = self.pending_id = None
                self.active_id = dialog_id
                events += self.show('trinket',self.dialogs[dialog_id])
            elif self.active and self.active.kind=='trinket':
                events += self.hide()
        match = CHOICE_HIDE.search(line)
        if match:
            dialog_id = int(match[1])
            self.dialogs.pop(dialog_id,None)
            if self.pending_id==dialog_id:
                self.pending = self.pending_id = None
            if self.active_id==dialog_id:
                events += self.hide()
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
            # TRIGGER is also emitted by automatic shop setup immediately
            # before a trinket dialog opens. PLAY identifies a real user roll.
            match = REROLL.search(line) if 'BLOCK_START BlockType=PLAY ' in line else None
            if match and match[1]==self.detector.player:
                self.phase = 'recruit'
                self.pending = self.pending_id = None
                if self.active and self.active.kind=='trinket':
                    events += self.hide()
        return events

    def idle(self):
        events = self.hero(self.detector.flush())
        if self.choices.cur and len(self.choices.cur)==4:
            block,self.choices.cur = self.choices.cur,None
            events += self.choice(block,self.choice_id)
        return events
