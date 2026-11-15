# Build with: python -m PyInstaller TavernLens.spec --noconfirm
from pathlib import Path
root = Path(SPECPATH)
a = Analysis([str(root/'run.py')],pathex=[str(root/'src')],
    datas=[(str(root/'src/tavernlens/data/catalog.json'),'tavernlens/data')],
    hiddenimports=[],
    excludes=['tkinter','_tkinter','numpy','scipy','pandas','matplotlib','PIL','IPython','pytest','setuptools'],
    noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz,a.scripts,[],exclude_binaries=True,name='TavernLensBackend',console=False,upx=False)
coll = COLLECT(exe,a.binaries,a.datas,name='TavernLens',upx=False)
