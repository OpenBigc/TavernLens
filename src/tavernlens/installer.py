"""Install the packaged plugin into the current user's persistent HDT folder."""
import csv
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path


class InstallError(Exception):
    pass


def hdt_running():
    result = subprocess.run(
        ['tasklist.exe', '/FI', 'IMAGENAME eq HearthstoneDeckTracker.exe', '/FO', 'CSV', '/NH'],
        capture_output=True, text=True, errors='replace', timeout=10,
        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
    )
    if result.returncode:
        raise InstallError('无法检查 HDT 状态，请稍后重试。')
    return any(row and row[0].casefold() == 'hearthstonedecktracker.exe'
               for row in csv.reader(result.stdout.splitlines()))


def _child(path, parent):
    """Validate every directory rename/delete against the intended plugin root."""
    if path.resolve().parent != parent.resolve():
        raise InstallError('插件目录异常，安装已停止。')


def install(payload, appdata, is_running=hdt_running):
    source = Path(payload).resolve()
    if not appdata:
        raise InstallError('无法确定当前用户的 AppData 目录。')
    base = Path(appdata).resolve()
    parent = base / 'HearthstoneDeckTracker' / 'Plugins'
    target = parent / 'TavernLens'
    if not parent.resolve().is_relative_to(base):
        raise InstallError('插件目录异常，安装已停止。')
    _child(target, parent)
    required = ('TavernLens.Hdt.dll', 'TavernLensBackend.exe', '_internal')
    if not all((source / name).exists() for name in required):
        raise InstallError('安装文件不完整，请完整解压后重试。')
    if source == target.resolve():
        return target
    if source.is_relative_to(target.resolve()) or target.resolve().is_relative_to(source):
        raise InstallError('安装文件所在位置异常，请重新解压后重试。')
    if is_running():
        raise InstallError('请先退出 HDT，再运行安装。')
    if target.exists() and not target.is_dir():
        raise InstallError('插件目录已被同名文件占用。')

    parent.mkdir(parents=True, exist_ok=True)
    token = uuid.uuid4().hex
    stage = parent / ('.TavernLens-install-' + token)
    backup = parent / ('.TavernLens-backup-' + token)
    for path in (stage, backup):
        _child(path, parent)
    old_saved = False
    committed = False
    try:
        # Retain extra files in an existing plugin folder. Actual user settings
        # and statistics caches live elsewhere and are never opened here.
        if target.exists():
            shutil.copytree(target, stage)
        shutil.copytree(source, stage, dirs_exist_ok=True)
        if target.exists():
            _child(target, parent)
            _child(backup, parent)
            target.rename(backup)
            old_saved = True
        _child(stage, parent)
        _child(target, parent)
        stage.rename(target)
        committed = True
    except Exception as error:
        if old_saved and not target.exists():
            try:
                _child(backup, parent)
                _child(target, parent)
                backup.rename(target)
                old_saved = False
            except OSError:
                raise InstallError(f'安装未完成，原文件保留在：{backup}') from error
        raise InstallError('安装未完成，请退出相关程序后重试。') from error
    finally:
        for path in ((stage, backup) if committed else (stage,)):
            if path.exists():
                _child(path, parent)
                try:
                    shutil.rmtree(path)
                except OSError:
                    pass  # A retained backup is preferable to a destructive retry.
    return target


def main(quiet=False):
    if sys.platform != 'win32':
        return 1
    payload = (Path(sys.executable).parent if getattr(sys, 'frozen', False)
               else Path(__file__).resolve().parents[2] / 'dist' / 'TavernLens')
    try:
        install(payload, os.environ.get('APPDATA'))
        message, icon, result = '安装完成。请启动 HDT，并在插件设置中启用 TavernLens。', 0x40, 0
    except Exception as error:
        message = str(error) if isinstance(error, InstallError) else '安装失败，请重试。'
        icon, result = 0x10, 1
    if not quiet:
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, message, 'TavernLens', icon)
    return result
