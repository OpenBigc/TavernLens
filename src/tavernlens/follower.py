import time
import os
import re
from pathlib import Path
from .engine import Engine

GAME_START = re.compile(rb'^D [\d:.]+ GameState\.DebugPrintPower\(\) -\s+CREATE_GAME\b',re.MULTILINE)


def latest_game_offset(path, block_size=2*1024*1024):
    """Seek to the last GameState CREATE_GAME, not the delayed screen copy."""
    with path.open('rb') as file:
        end = path.stat().st_size
        while end:
            start = max(0,end-block_size)
            file.seek(start)
            matches = list(GAME_START.finditer(file.read(end-start)))
            if matches:
                return start+matches[-1].start()
            if start==0:
                break
            end = start+min(512,block_size//2)
    return 0


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
                        status('正在回填本局日志')
                        file.seek(latest_game_offset(path))
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
