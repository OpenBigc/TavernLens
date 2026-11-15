"""Copy installed runtime notices into a binary release (not app data)."""
import json
import shutil
import sys
from pathlib import Path

app = Path(sys.argv[1])
destination = app / 'runtime-licenses'
destination.mkdir(exist_ok=True)
prefix = Path(sys.base_prefix)
python_license = next((p for p in (prefix/'LICENSE_PYTHON.txt', prefix/'LICENSE.txt') if p.is_file()), None)
if python_license:
    shutil.copy2(python_license, destination/'PYTHON.txt')

# Conda keeps notices alongside the exact native packages used by the build.
dlls = {p.name.lower() for p in (app/'_internal').glob('*.dll')}
for metadata in (prefix/'conda-meta').glob('*.json'):
    package = json.loads(metadata.read_text(encoding='utf-8'))
    if not dlls.intersection(Path(p).name.lower() for p in package.get('files', [])):
        continue
    source = Path(package.get('link', {}).get('source', ''))/'info/licenses'
    if not source.is_dir():
        continue
    target = destination/(package['name']+'-'+package['version'])
    target.mkdir(exist_ok=True)
    for notice in source.iterdir():
        if notice.is_file():
            shutil.copy2(notice,target/notice.name)

if not any(destination.iterdir()):
    raise SystemExit('Python runtime license not found; supply notices before publishing')
