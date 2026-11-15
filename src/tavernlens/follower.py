import time
import os
from pathlib import Path
from .engine import Engine


def newest_log(root):
    try:
        return max(Path(root).glob('Hearthstone_*/Power.log'),key=lambda p:p.stat().st_mtime,default=None)
    except OSError:
        return None


def follow(root, catalog, queue, stop):
    current, file = None,None
    engine = Engine(catalog)
    fragment, last_read, last_scan = '',0.,0.
    dirty, initial = False,True
    health = None

    def status(value):
        nonlocal health
        if value != health:
            queue.put(('log_status',value))
            health = value

    try:
        while not stop.is_set():
            now = time.monotonic()
            if now-last_scan>=2:
                last_scan = now
                path = newest_log(root) if root else None
                if path and path != current:
                    if file:
                        file.close()
                    file = path.open(encoding='utf-8',errors='replace')
                    engine = Engine(catalog)
                    current,fragment,dirty = path,'',False
                    queue.put(('hide',None))
                    if initial:
                        # Learn the local player without showing historical
                        # choices when starting in the middle of a game.
                        for line in file:
                            if stop.is_set():
                                return
                            if line.endswith('\n'):
                                engine.process(line)
                            else:
                                fragment = line
                        engine.idle()
                        engine.active = None
                        initial = False
                    status('正在读取日志')
                if not path:
                    status('未找到游戏日志')
            if file:
                if os.fstat(file.fileno()).st_size < file.tell():
                    file.seek(0)
                    fragment = ''
                    engine = Engine(catalog)
                    queue.put(('hide',None))
                line = file.readline()
                if line:
                    fragment += line
                    if fragment.endswith('\n'):
                        for event in engine.process(fragment):
                            queue.put(event)
                        fragment = ''
                    dirty,last_read = True,now
                    continue
                if dirty and now-last_read>.35 and not fragment:
                    dirty = False
                    for event in engine.idle():
                        queue.put(event)
            stop.wait(.1)
    except OSError as e:
        status(f'日志读取失败：{e}')
    finally:
        if file:
            file.close()
