"""UI-free data service. HDT owns the only overlay canvas."""
import logging
import queue
import threading
import time
from .bridge import Bridge
from .config import Config, catalog
from .follower import follow
from .models import badges
from .providers.firestone import Firestone


class LogQueue:
    def __init__(self, target, generation):
        self.target,self.generation = target,generation

    def put(self, event):
        self.target.put(('log',(self.generation,event)))


class Service:
    def __init__(self, folder, port=27183):
        self.folder = folder
        self.path = folder/'settings.json'
        self.config = Config.load(self.path)
        self.bridge = Bridge(port)
        self.queue = queue.Queue()
        self.stop = threading.Event()
        self.reader_stop = threading.Event()
        self.active,self.until = None,0.
        self.tables = {}
        self.generation,self.log_generation = 0,0
        self.log_status = '等待日志'
        self.started,self.refreshed = time.monotonic(),0.
        self.last_mtime = None
        self.config.save(self.path)
        self.start_reader()
        self.refresh()

    def start_reader(self):
        self.reader_stop.set()
        self.reader_stop = threading.Event()
        self.log_generation += 1
        self.active = None
        sink = LogQueue(self.queue,self.log_generation)
        threading.Thread(target=follow,args=(self.config.logs,catalog(),sink,self.reader_stop),daemon=True).start()

    def refresh(self):
        self.generation += 1
        self.tables = {}
        generation,config = self.generation,self.config
        def load(kind):
            try:
                table = Firestone(self.folder/'cache').load(kind,config.mmr,config.period,config.mode)
                if table.error:
                    logging.warning('%s: %s',kind,table.error)
                self.queue.put(('table',(generation,table)))
            except Exception:
                logging.exception('Stats worker failed')
        for kind in ('hero','trinket'):
            threading.Thread(target=load,args=(kind,),daemon=True).start()
        self.refreshed = time.monotonic()

    def config_changed(self):
        try:
            mtime = self.path.stat().st_mtime_ns
            if mtime==self.last_mtime:
                return
            self.last_mtime = mtime
            candidate = Config.load(self.path)
            old,self.config = self.config,candidate
            if candidate.logs!=old.logs:
                self.start_reader()
            if (candidate.mmr,candidate.period,candidate.mode)!=(old.mmr,old.period,old.mode):
                self.refresh()
        except (OSError,ValueError):
            logging.exception('Invalid settings; retaining previous configuration')

    def tick(self):
        self.config_changed()
        if time.monotonic()-self.refreshed>=3600:
            self.refresh()
        while True:
            try:
                event,payload = self.queue.get_nowait()
            except queue.Empty:
                break
            if event=='log':
                generation,(event,payload) = payload
                if generation!=self.log_generation:
                    continue
            if event=='offer':
                same = self.active and self.active.kind==payload.kind and {o.card_id for o in self.active.options}=={o.card_id for o in payload.options}
                self.active = payload
                if not same:
                    self.until = time.monotonic()+120
            elif event=='hide':
                self.active = None
            elif event=='log_status':
                self.log_status = payload
            elif event=='table':
                generation,table = payload
                if generation==self.generation:
                    self.tables[table.kind] = table
        if self.active and time.monotonic()>=self.until:
            self.active = None
        value = {'version':1,'active':bool(self.active),'scale':self.config.scale,
                 'log_status':self.log_status,'tables':{k:{'rows':len(t.rows),
                    'updated_at':t.updated_at,'stale':t.stale,'error':bool(t.error)} for k,t in self.tables.items()}}
        if self.active:
            table = self.tables.get(self.active.kind)
            value.update(kind=self.active.kind,offset=self.config.offsets[self.active.kind],
                options=[{'slot':b.slot,'average':b.average,'details':b.details,'color':b.color}
                         for b in badges(self.active,table)])
        self.bridge.publish(value)

    def run(self, idle_timeout=0):
        try:
            while not self.stop.wait(.1):
                self.tick()
                last_seen = self.bridge.last_seen or self.started
                if idle_timeout and time.monotonic()-last_seen>idle_timeout:
                    break
        except KeyboardInterrupt:
            pass
        finally:
            self.close()

    def close(self):
        self.stop.set()
        self.reader_stop.set()
        self.bridge.close()
