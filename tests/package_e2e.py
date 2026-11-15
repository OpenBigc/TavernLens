"""Run against the ZIP that will be released; requires HDT to be closed.

python tests/package_e2e.py dist/TavernLens-HDT.zip
"""
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def main(archive):
    root = Path(__file__).resolve().parents[1]
    (root / 'work').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='安装 E2E ', dir=root / 'work') as temporary:
        folder = Path(temporary).resolve()
        unpack = folder / '完整解压 with spaces'
        with zipfile.ZipFile(archive) as package:
            check(package.testzip() is None, 'Corrupt archive')
            script = package.read('安装.cmd')
            check(b'\n' not in script.replace(b'\r\n', b''), 'CMD must use CRLF')
            check(not script.startswith(b'\xef\xbb\xbf'), 'CMD must not have a BOM')
            package.extractall(unpack)
        env = dict(os.environ, APPDATA=str(folder / '用户数据'),
                   LOCALAPPDATA=str(folder / '本地数据'))
        command = ['cmd.exe', '/d', '/c', str(unpack / '安装.cmd'), '--quiet']
        target = Path(env['APPDATA']) / 'HearthstoneDeckTracker/Plugins/TavernLens'
        for update in (False, True):
            if update:
                (target / 'keep.txt').write_text('keep')
            result = subprocess.run(command, cwd=folder, env=env, capture_output=True, timeout=60)
            check(result.returncode == 0, repr((result.returncode, result.stdout, result.stderr)))
            for source in (unpack / 'TavernLens').rglob('*'):
                if source.is_file():
                    installed = target / source.relative_to(unpack / 'TavernLens')
                    check(installed.is_file() and hashlib.sha256(source.read_bytes()).digest() ==
                          hashlib.sha256(installed.read_bytes()).digest(), f'File mismatch: {source.name}')
            if update:
                check((target / 'keep.txt').read_text() == 'keep', 'Update lost existing file')
        print('PASS: ZIP -> cmd.exe -> fresh install -> update; all packaged files match', flush=True)

        # Execute the installed binary, without Python or a pre-existing cache.
        with socket.socket() as probe:
            check(probe.connect_ex(('127.0.0.1', 27183)) != 0, 'Close the existing backend before E2E')
        state = folder / '全新服务数据'
        logs = folder / 'Logs/Hearthstone_E2E'
        logs.mkdir(parents=True)
        power = logs / 'Power.log'
        power.write_text('')
        state.mkdir()
        (state / 'settings.json').write_text(json.dumps({'logs': str(logs.parent)}), encoding='utf-8')
        process = subprocess.Popen([str(target / 'TavernLensBackend.exe'), '--state-dir', str(state),
                                    '--idle-timeout', '10'], env=env)
        def wait_for(predicate, timeout=90):
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                check(process.poll() is None, f'Installed backend exited: {process.returncode}')
                try:
                    with urllib.request.urlopen('http://127.0.0.1:27183/state', timeout=2) as response:
                        value = json.load(response)
                    if predicate(value):
                        return value
                except OSError:
                    pass
                time.sleep(.25)
            raise AssertionError('Timed out waiting for installed backend')
        try:
            value = wait_for(lambda v: len(v.get('tables', {})) == 2 and v.get('log_status') == '正在读取日志')
            for kind in ('hero', 'trinket'):
                table = value['tables'][kind]
                check(table['rows'] > 0 and not table['error'] and not table['stale'], repr(value))
            print('PASS: installed backend starts; fresh hero/trinket data from real API: ' +
                  json.dumps(value['tables']), flush=True)
            fixture = (root / 'tests/fixtures/offers.log').read_text(encoding='utf-8')
            hero = '\n'.join(fixture.splitlines()[:4]) + '\n'
            with power.open('a', encoding='utf-8') as output:
                output.write(hero)
            value = wait_for(lambda v: v.get('active') and v.get('kind') == 'hero')
            check(len(value['options']) == 4, repr(value))
            print('PASS: installed service reads appended hero choice and emits 4 overlay rows', flush=True)
            # Simulate only the game log input; all displayed statistics still
            # come from the real, freshly downloaded API response.
            known = json.loads((root / 'src/tavernlens/data/catalog.json').read_text(encoding='utf-8'))['trinkets']
            cards = []
            for cache in (state / 'cache').glob('*.json'):
                for row in json.loads(cache.read_text())['data'].get('trinketStats', []):
                    card = row.get('trinketCardId')
                    if card in known and row.get('dataPoints', 0) > 0:
                        cards.append(card)
            check(len(cards) >= 4, 'No matching real trinket data')
            prefix = ['D 10:00:01.0000000 GameState.DebugPrintEntityChoices() - id=1 Player=3\n']
            prefix += [f'D 10:00:01.0000000 GameState.DebugPrintEntityChoices() -   Entities[{i}]=[entityName={card} id={200+i} zone=SETASIDE zonePos=0 cardId={card} player=3]\n'
                       for i, card in enumerate(cards[:4])]
            prefix += ['D 10:00:01.1000000 GameState.End()\n']
            with power.open('a', encoding='utf-8') as output:
                output.write(''.join(prefix))
            value = wait_for(lambda v: v.get('active') and v.get('kind') == 'trinket')
            check(len(value['options']) == 4, repr(value))
            print('PASS: installed service reads trinket choice and emits 4 overlay rows', flush=True)
        except Exception:
            log = state / 'tavernlens.log'
            if log.exists():
                print(log.read_text(encoding='utf-8', errors='replace'), flush=True)
            raise
        finally:
            process.terminate()
            process.wait(timeout=15)

        # Missing payload follows the human-readable error branch, not broken commands.
        missing = folder / '安装.cmd'
        missing.write_bytes(script)
        result = subprocess.run(['cmd.exe', '/d', '/c', str(missing)], input=b'\r\n',
                                cwd=folder, env=env, capture_output=True, timeout=10)
        check(result.returncode == 1 and '请完整解压'.encode() in result.stdout, repr(result))
        check(b'not recognized' not in result.stderr, repr(result.stderr))
        print('PASS: incomplete extraction reports a readable error', flush=True)


if __name__ == '__main__':
    main(Path(sys.argv[1]).resolve())
