import json
import queue
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from tavernlens.config import Config
from tavernlens.detection import OfferDetector
from tavernlens.engine import Engine
from tavernlens.models import badges, Offer, Option, Stat, Table
from tavernlens.providers.firestone import Firestone, parse
from tavernlens.follower import follow

FIXTURES = Path(__file__).parent/'fixtures'
CATALOG = {'heroes':['H1','H2','H3','H4'],'trinkets':['T1','T2','T3','T4'],
           'names':{'H1':'英雄一','H2':'英雄二','T1':'饰品一'}}


def hero_line(card, entity, pos, ts='10:00:00.0000000'):
    return f'D {ts} GameState.DebugPrintPower() - FULL_ENTITY - Updating [entityName={card} id={entity} zone=HAND zonePos={pos} cardId={card} player=3]\n'


def choice_lines(cards=('T1','T2','T3','T4')):
    return ['D 10:00:01.0000000 GameState.DebugPrintEntityChoices() - id=1 Player=3\n']+[
        f'D 10:00:01.0000000 GameState.DebugPrintEntityChoices() -   Entities[{i}]=[entityName={c} id={200+i} zone=SETASIDE zonePos=0 cardId={c} player=3]\n'
        for i,c in enumerate(cards)]+['D 10:00:01.1000000 GameState.End()\n']


def combat(value):
    return f'D 10:00:02.0000000 PowerTaskList.DebugPrintPower() - TAG_CHANGE Entity=PlayerName tag=BACON_CURRENT_COMBAT_PLAYER_ID value={value}\n'


class DetectionTests(unittest.TestCase):
    def test_upstream_19_hero_36_trinket_regression(self):
        heroes = dict.fromkeys(json.loads((FIXTURES/'hero_ids.json').read_text()),{})
        trinkets = dict.fromkeys(json.loads((FIXTURES/'trinket_ids.json').read_text()),{})
        detector = OfferDetector(heroes,trinkets)
        counts = {'hero choice':0,'trinket choice':0}
        with (FIXTURES/'offers.log').open(encoding='utf-8') as f:
            for line in f:
                event = detector.feed(line)
                if event: counts[event[0]]+=1
        event = detector.flush()
        if event: counts[event[0]]+=1
        self.assertEqual(counts,{'hero choice':19,'trinket choice':36})


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.engine = Engine(CATALOG)

    def draft(self):
        for i,c in enumerate(['H3','H1','H4','H2']):
            self.engine.process(hero_line(c,90+i,i+1))
        return self.engine.idle()

    def trinkets(self):
        events=[]
        for line in choice_lines():events+=self.engine.process(line)
        return events

    def test_chinese_names_and_original_card_order(self):
        offer=self.draft()[0][1]
        self.assertEqual([o.card_id for o in offer.options],['H3','H1','H4','H2'])
        self.assertEqual(offer.options[1].name,'英雄一')

    def test_trinket_does_not_open_during_combat(self):
        self.engine.process(combat(6))
        self.assertEqual(self.trinkets(),[])
        self.assertIsNone(self.engine.active)
        event=self.engine.process(combat(0))
        self.assertEqual(event[0][1].kind,'trinket')
        self.assertEqual([o.slot for o in event[0][1].options],[1,2,3,4])

    def test_combat_hides_choice(self):
        self.trinkets()
        self.assertEqual(self.engine.process(combat(2)),[('hide',None)])

    def test_discover_is_not_trinket(self):
        events=[]
        for line in choice_lines(('M1','M2','M3','M4')):events+=self.engine.process(line)
        self.assertEqual(events,[])

    def test_duplicate_cards_cannot_be_a_real_trinket_offer(self):
        for line in choice_lines(('T1','T1','T3','T4')):self.engine.process(line)
        self.assertIsNone(self.engine.active)

    def test_idle_flushes_final_complete_choice(self):
        for line in choice_lines()[:-1]:self.engine.process(line)
        self.assertEqual(self.engine.idle()[0][1].kind,'trinket')

    def test_tavern_closes_hero(self):
        self.draft()
        events=self.engine.process('D 10:00:03 PowerTaskList.DebugPrintPower() - tag=CARDRACE value=BEAST\n')
        self.assertEqual(events,[('hide',None)])

    def test_local_reroll_recovers_missing_end_marker(self):
        self.draft()
        self.engine.process(combat(2))
        self.trinkets()
        event=self.engine.process('D 10:00:03 PowerTaskList.DebugPrintPower() - BLOCK_START Entity=[entityName=Roll id=1 zone=PLAY zonePos=0 cardId=TB_BaconShop_8p_Reroll_Button player=3]\n')
        self.assertEqual(event[0][1].kind,'trinket')

    def test_new_game_clears_pending_choice(self):
        self.engine.process(combat(2))
        self.trinkets()
        self.engine.process(hero_line('H1',91,1))
        self.assertIsNone(self.engine.pending)

    def test_opponent_setaside_reveals_are_not_used_for_ui(self):
        for i,c in enumerate(CATALOG['trinkets']):
            self.engine.process(f'D 10:00:00 GameState.DebugPrintPower() - FULL_ENTITY - Updating [entityName={c} id={200+i} zone=SETASIDE zonePos=0 cardId={c} player=8]\n')
        self.assertEqual(self.engine.idle(),[])


class ProviderTests(unittest.TestCase):
    def data(self):
        return {'lastUpdateDate':'2026-11-15T00:00:00Z','trinketStats':[{
            'trinketCardId':'T1','dataPoints':5000,'averagePlacement':4.5,'pickRate':.25,
            'averagePlacementAtMmr':[{'mmr':1,'placement':3.8,'dataPoints':12}]}]}

    def test_bracket_average_uses_bracket_samples(self):
        row=parse('trinket',self.data(),'1')['T1']
        self.assertEqual((row.average,row.samples),(3.8,12))
        self.assertEqual(row.pick_scope,'all')

    def test_missing_bracket_never_uses_global_average(self):
        row=parse('trinket',self.data(),'10')['T1']
        self.assertIsNone(row.average)
        self.assertEqual(row.samples,0)

    def test_missing_all_inline_row_can_use_global(self):
        row=parse('trinket',self.data(),'100')['T1']
        self.assertEqual(row.average,4.5)
        self.assertEqual(row.samples,5000)

    def test_zero_and_nonfinite_values_have_no_average(self):
        data=self.data();data['trinketStats'][0]['averagePlacement']=float('nan')
        self.assertIsNone(parse('trinket',data,'100')['T1'].average)
        data['trinketStats'][0]['averagePlacement']=3.5
        data['trinketStats'][0]['dataPoints']=0
        self.assertIsNone(parse('trinket',data,'100')['T1'].average)

    def test_wrong_schema_rejected(self):
        with self.assertRaises(ValueError):parse('hero',{'trinketStats':[]},'100')

    def test_fresh_cache_skips_network(self):
        with tempfile.TemporaryDirectory() as d:
            count=[]
            provider=Firestone(Path(d),fetch=lambda u:count.append(u) or self.data())
            provider.load('trinket','100','last-patch')
            provider.load('trinket','100','last-patch')
            self.assertEqual(len(count),1)

    def test_failed_refresh_marks_cached_rows_stale(self):
        with tempfile.TemporaryDirectory() as d:
            provider=Firestone(Path(d),fetch=lambda u:self.data())
            provider.load('trinket','100','last-patch')
            def fail(u):raise OSError('offline')
            provider.fetch=fail
            table=provider.load('trinket','100','last-patch',refresh=True)
            self.assertTrue(table.stale)
            self.assertEqual(table.error,'offline')
            self.assertEqual(table.rows['T1'].samples,5000)

    def test_different_hero_brackets_never_share_cache(self):
        calls=[]
        with tempfile.TemporaryDirectory() as d:
            provider=Firestone(Path(d),fetch=lambda u:calls.append(u) or {'heroStats':[]})
            provider.load('hero','100','last-patch')
            provider.load('hero','1','last-patch')
            self.assertEqual(len(calls),2)
            self.assertIn('mmr-1/',calls[1])

    def test_duo_trinket_does_not_request_solo(self):
        table=Firestone(Path('unused'),fetch=lambda u:self.fail('network called')).load('trinket','100','last-patch','duo')
        self.assertEqual(table.rows,{})
        self.assertIsNotNone(table.error)


class PresentationTests(unittest.TestCase):
    def offer(self):
        return Offer('hero',tuple(Option(f'H{i}',f'英雄{i}',i) for i in (4,2,1,3)))

    def test_skin_stat_lookup_and_chinese_text(self):
        offer=Offer('hero',(Option('H1_SKIN_01','英雄',1),))
        result=badges(offer,Table('hero',{'H1':Stat(3.8,12,25)}))[0]
        self.assertEqual(result.average,'均次 3.80')
        self.assertIn('样本少',result.details)

    def test_missing_stats_differ_from_loading(self):
        offer=self.offer()
        self.assertEqual(badges(offer,None)[0].details,'加载中')
        self.assertEqual(badges(offer,Table('hero'))[0].details,'暂无数据')


class FollowerTests(unittest.TestCase):
    def test_startup_backfill_is_silent_and_partial_lines_are_buffered(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);session=root/'Hearthstone_test';session.mkdir()
            path=session/'Power.log'
            path.write_text(''.join(hero_line(c,90+i,i+1) for i,c in enumerate(CATALOG['heroes'])),encoding='utf-8')
            q,stop=queue.Queue(),threading.Event()
            worker=threading.Thread(target=follow,args=(root,CATALOG,q,stop),daemon=True)
            worker.start()
            try:
                deadline=time.time()+2
                while time.time()<deadline:
                    event=q.get(timeout=2)
                    if event[0]=='log_status':break
                history=[]
                while not q.empty():history.append(q.get())
                self.assertFalse(any(e=='offer' for e,_ in history))
                lines=''.join(choice_lines())
                with path.open('a',encoding='utf-8') as f:
                    f.write(lines[:75]);f.flush()
                time.sleep(.2)
                self.assertFalse(any(e=='offer' for e,_ in list(q.queue)))
                with path.open('a',encoding='utf-8') as f:f.write(lines[75:])
                deadline=time.time()+3
                found=None
                while time.time()<deadline:
                    event=q.get(timeout=3)
                    if event[0]=='offer':found=event[1];break
                self.assertIsNotNone(found)
                self.assertEqual(found.kind,'trinket')
            finally:
                stop.set();worker.join(timeout=3)
                self.assertFalse(worker.is_alive())


if __name__=='__main__':unittest.main()
