#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SimpleExtract v1.2.0 - Windows用 高機能シンプル解凍ソフト
対応: ZIP, 7Z, TAR, TAR.GZ, TGZ, GZ, BZ2, RAR
"""
import os
import sys
import json
import zipfile
import tarfile
import pathlib
import threading
import shutil
import subprocess
import traceback
import urllib.request
import urllib.error
import atexit
import logging
logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
from datetime import datetime

import time
import random
import tkinter as tk
import customtkinter as ctk
from tkinter import ttk, filedialog, messagebox, font as tkfont
from tkinterdnd2 import TkinterDnD, DND_FILES
import winreg
import ctypes
from ctypes import wintypes
# 重いモジュールは遅延読み込み（起動高速化）
HAS_PIL = None
Image = None
ImageTk = None
HAS_PY7ZR = None
HAS_RARFILE = None
def _ensure_pil():
    global HAS_PIL, Image, ImageTk
    if HAS_PIL is None:
        try:
            from PIL import Image as _Image, ImageTk as _ImageTk
            Image, ImageTk = _Image, _ImageTk
            HAS_PIL = True
        except ImportError:
            HAS_PIL = False
    return HAS_PIL
def _ensure_py7zr():
    global HAS_PY7ZR
    if HAS_PY7ZR is None:
        try:
            import py7zr as _py7zr
            HAS_PY7ZR = True
        except ImportError:
            HAS_PY7ZR = False
    return HAS_PY7ZR
def _ensure_rarfile():
    global HAS_RARFILE
    if HAS_RARFILE is None:
        try:
            import rarfile as _rarfile
            HAS_RARFILE = True
        except ImportError:
            HAS_RARFILE = False
    return HAS_RARFILE

SUPPORTED_EXTS = {".zip", ".7z", ".tar", ".gz", ".tgz", ".tar.gz", ".bz2", ".rar"}
ASSOC_EXTS = [".zip", ".7z", ".rar", ".tar", ".gz", ".tgz", ".bz2"]
EXT_DESCRIPTIONS = {
    ".zip": "ZIP 圧縮ファイル", ".7z": "7-Zip 圧縮ファイル", ".rar": "RAR 圧縮ファイル",
    ".tar": "TAR アーカイブ", ".gz": "GZIP 圧縮ファイル", ".tgz": "TGZ 圧縮ファイル", ".bz2": "BZIP2 圧縮ファイル",
}
EXT_ICONS = {".zip": "📦", ".7z": "🗜️", ".rar": "📚", ".tar": "📦", ".gz": "🗜️", ".tgz": "🗜️", ".bz2": "🗜️"}

APP_NAME = "SimpleExtract"
APP_VERSION = "1.6.1"
# おまかせメッセージ
OMAKASE_MESSAGES = [
    "🎉 今日の運勢: 大吉！解凍も絶好調！",
    "🍀 ラッキーアーカイブが見つかりました",
    "✨ おまかせパワー全開！",
    "🎲 次は君の番だ！",
    "📦 パンドラの箱を開けます...",
    "🚀 圧縮の彼方へ！",
    "🎊 おまかせ解凍、発動！",
    "💎 レアなファイルが出たかも？",
]
OMAKASE_THEMES = {
    "sakura": {"name": "🌸 さくら", "primary": "#ec4899", "bg": "#fff1f2", "card": "#ffffff"},
    "ocean": {"name": "🌊 オーシャン", "primary": "#0ea5e9", "bg": "#f0f9ff", "card": "#ffffff"},
    "forest": {"name": "🌲 フォレスト", "primary": "#10b981", "bg": "#f0fdf4", "card": "#ffffff"},
    "sunset": {"name": "🌅 サンセット", "primary": "#f97316", "bg": "#fff7ed", "card": "#ffffff"},
    "midnight": {"name": "🌙 ミッドナイト", "primary": "#6366f1", "bg": "#1e1b4b", "card": "#312e81"},
    "default": {"name": "💙 デフォルト", "primary": "#2b6ff0", "bg": "#f5f7fb", "card": "#ffffff"},
}
ORGANIZE_CATEGORIES = {
    "Images": {".png",".jpg",".jpeg",".gif",".bmp",".webp",".tiff",".svg",".psd"},
    "Documents": {".pdf",".docx",".doc",".txt",".md",".rtf",".odt",".tex"},
    "Spreadsheets": {".xlsx",".xls",".csv",".ods"},
    "Presentations": {".pptx",".ppt",".odp"},
    "Archives": {".zip",".7z",".rar",".tar",".gz"},
    "Videos": {".mp4",".avi",".mov",".mkv",".wmv",".flv"},
    "Audio": {".mp3",".wav",".flac",".aac",".ogg"},
    "Code": {".py",".js",".html",".css",".json",".xml",".cpp",".java"},
}
PROGID_PREFIX = "SimpleExtract"

# ── フォントアンチエイリアス & DPI ──
# BIZ UDGothic は小サイズでも最も滑らかに見える日本語UIフォント
FONT_FAMILY_JP = "BIZ UDGothic"  # 試した中で最もギザつかない
FONT_FAMILY_JP_FALLBACK = "BIZ UDGothic"
FONT_FAMILY_EN = "Segoe UI"
FONT_FALLBACK = "Meiryo UI"

# --- システム設定の保存/復元 ---
_original_font_settings = {}  # enable_font_antialiasing で変更前の値を保存

def _restore_font_settings():
    """アプリ起動前に保存したフォント関連のシステム設定を復元する。"""
    orig = _original_font_settings
    if not orig:
        return
    SPI_SETFONTSMOOTHING = 0x004B
    SPI_SETFONTSMOOTHINGTYPE = 0x200B
    SPIF_UPDATEINIFILE = 0x01
    SPIF_SENDCHANGE = 0x02
    # SystemParametersInfo の復元
    if "font_smoothing" in orig:
        try:
            ctypes.windll.user32.SystemParametersInfoW(
                SPI_SETFONTSMOOTHING, int(orig["font_smoothing"]),
                None, SPIF_UPDATEINIFILE | SPIF_SENDCHANGE)
        except Exception: pass
    if "font_smoothing_type" in orig:
        try:
            ctypes.windll.user32.SystemParametersInfoW(
                SPI_SETFONTSMOOTHINGTYPE, int(orig["font_smoothing_type"]),
                None, SPIF_UPDATEINIFILE | SPIF_SENDCHANGE)
        except Exception: pass
    # レジストリの復元
    if "reg_FontSmoothing" in orig:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop",
                                0, winreg.KEY_SET_VALUE) as k:
                winreg.SetValueEx(k, "FontSmoothing", 0, winreg.REG_SZ,
                                  orig["reg_FontSmoothing"])
                winreg.SetValueEx(k, "FontSmoothingType", 0, winreg.REG_DWORD,
                                  orig["reg_FontSmoothingType"])
        except Exception: pass

atexit.register(_restore_font_settings)


def enable_font_antialiasing(root=None):
    """ClearType/アンチエイリアスを有効化 & DPIを調整。
    変更前の値を保存し、アプリ終了時に atexit で復元する。"""
    global _original_font_settings
    SPI_SETFONTSMOOTHING = 0x004B
    SPI_SETFONTSMOOTHINGTYPE = 0x200B
    FE_FONTSMOOTHINGCLEARTYPE = 0x0002
    SPIF_UPDATEINIFILE = 0x01
    SPIF_SENDCHANGE = 0x02
    # --- 変更前の値を保存 ---
    try:
        buf = ctypes.wintypes.DWORD()
        ctypes.windll.user32.SystemParametersInfoW(SPI_SETFONTSMOOTHING, 0, ctypes.byref(buf), 0)
        _original_font_settings["font_smoothing"] = buf.value
    except Exception: pass
    try:
        buf = ctypes.wintypes.DWORD()
        ctypes.windll.user32.SystemParametersInfoW(SPI_SETFONTSMOOTHINGTYPE, 0, ctypes.byref(buf), 0)
        _original_font_settings["font_smoothing_type"] = buf.value
    except Exception: pass
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop", 0,
                            winreg.KEY_READ) as k:
            _original_font_settings["reg_FontSmoothing"], _ = winreg.QueryValueEx(k, "FontSmoothing")
            _original_font_settings["reg_FontSmoothingType"], _ = winreg.QueryValueEx(k, "FontSmoothingType")
    except Exception: pass
    # 1. DPI Awareness - PerMonitor (1) の方が分数スケーリングでギザつきにくい
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)  # PROCESS_SYSTEM_DPI_AWARE
    except Exception:
        try: ctypes.windll.user32.SetProcessDPIAware()
        except Exception: pass
    # 2. ClearTypeフォントスムージングを有効化 (SPI_SETFONTSMOOTHING)
    try:
        ctypes.windll.user32.SystemParametersInfoW(SPI_SETFONTSMOOTHING, 1, None, SPIF_UPDATEINIFILE | SPIF_SENDCHANGE)
        ctypes.windll.user32.SystemParametersInfoW(SPI_SETFONTSMOOTHINGTYPE, FE_FONTSMOOTHINGCLEARTYPE, None, SPIF_UPDATEINIFILE | SPIF_SENDCHANGE)
    except Exception: pass
    # 3. GDIフォントスムージングをレジストリでも有効化
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop", 0, winreg.KEY_SET_VALUE) as k:
            winreg.SetValueEx(k, "FontSmoothing", 0, winreg.REG_SZ, "2")
            winreg.SetValueEx(k, "FontSmoothingType", 0, winreg.REG_DWORD, 2)
    except Exception: pass
    # 4. Tkのスケーリング - 分数スケーリングはギザつくので1.0に固定し、Windowsに任せる
    if root is not None:
        try:
            root.tk.call('tk', 'scaling', 1.0)
            ctk.set_widget_scaling(1.0)
            ctk.set_window_scaling(1.0)
        except Exception: pass
        # Tkフォントのレンダリングを滑らかに - BIZ UDGothicに置換、サイズを1pt大きく
        try:
            for name in ["TkDefaultFont", "TkTextFont", "TkHeadingFont", "TkCaptionFont"]:
                f = tkfont.nametofont(name)
                f.configure(family=FONT_FAMILY_JP, size=10)
        except Exception: pass
        # 追加: GDIのテキストレンダリングを高品質に
        try:
            ctypes.windll.gdi32.SetTextCharacterExtra(ctypes.windll.user32.GetDC(0), 0)
        except Exception: pass

def get_font(family=None, size=11, weight="normal"):
    """アンチエイリアス対応のCTkFontを生成"""
    # Yu Gothic UI は ClearTypeで最も滑らかに描画される日本語フォント
    fam = family or FONT_FAMILY_JP
    try:
        return ctk.CTkFont(family=fam, size=size, weight=weight)
    except Exception:
        return ctk.CTkFont(family=FONT_FALLBACK, size=size, weight=weight)

# --- テーマカラー ---
LIGHT = {
    "BG": "#f5f7fb", "CARD": "#ffffff", "TEXT": "#1e293b", "SUB": "#64748b",
    "BORDER": "#e2e8f0", "DROP_BG": "#eef4ff", "DROP_BORDER": "#2b6ff0",
    "LOG_BG": "#f8fafc", "HOVER": "#f1f5f9"
}
DARK = {
    "BG": "#0f172a", "CARD": "#1e293b", "TEXT": "#f1f5f9", "SUB": "#94a3b8",
    "BORDER": "#334155", "DROP_BG": "#1e293b", "DROP_BORDER": "#3b82f6",
    "LOG_BG": "#0f172a", "HOVER": "#334155"
}
COLOR_PRIMARY = "#2b6ff0"
COLOR_PRIMARY_HOVER = "#1a5bd9"
COLOR_SUCCESS = "#16a34a"
COLOR_WARN = "#f59e0b"
COLOR_DANGER = "#ef4444"

def is_supported(path: str) -> bool:
    p = path.lower()
    if p.endswith(".tar.gz"): return True
    return pathlib.Path(p).suffix.lower() in SUPPORTED_EXTS

def human_size(n: int) -> str:
    for unit in ["B","KB","MB","GB"]:
        if n < 1024: return f"{n:.1f} {unit}" if unit != "B" else f"{n} B"
        n /= 1024
    return f"{n:.1f} TB"

def get_exe_path() -> str:
    if getattr(sys, 'frozen', False): return sys.executable
    return f'"{sys.executable}" "{os.path.abspath(__file__)}"'

def get_exe_path_quoted() -> str:
    p = get_exe_path()
    return p if p.startswith('"') else f'"{p}"'

def get_exe_icon() -> str:
    return sys.executable if getattr(sys, 'frozen', False) else sys.executable

def notify_shell_change():
    try: ctypes.windll.shell32.SHChangeNotify(0x08000000, 0x0000, None, None)
    except Exception: pass

# ── タスクバー & インジケーター ──
class TaskbarProgress:
    """Windowsタスクバー進捗 (ITaskbarList3) - ctypesで実装"""
    CLSID_TaskbarList = "{56FDF344-FD6D-11d0-958A-006097C9A090}"
    IID_ITaskbarList3 = "{EA1AFB91-9E28-4B86-90E9-9E9F8A5EEAF}"
    TBPF_NOPROGRESS = 0
    TBPF_INDETERMINATE = 1
    TBPF_NORMAL = 2
    TBPF_ERROR = 4
    TBPF_PAUSED = 8
    def __init__(self, hwnd):
        self.hwnd = hwnd
        self.taskbar = None
        self._init_com()
    def _init_com(self):
        try:
            import comtypes
            from comtypes import GUID, COMMETHOD, HRESULT
            from comtypes.client import CreateObject
            # comtypesがあればそちらを使う（より安定）
            self._use_comtypes = True
        except ImportError:
            self._use_comtypes = False
        # ctypesフォールバックでもOKだが、簡易的に comtypes が無い場合は何もしない
        if not self._use_comtypes:
            self.taskbar = None
            return
        try:
            from comtypes import GUID as CGUID
            from comtypes.client import CreateObject
            import comtypes.gen
            # 直接CoCreateInstance
            import ctypes
            from ctypes import wintypes
            ole32 = ctypes.windll.ole32
            shell32 = ctypes.windll.shell32
            # 簡易: comtypesで作成
            self.taskbar = CreateObject("{56FDF344-FD6D-11d0-958A-006097C9A090}", interface=None)
            # ITaskbarList3を取得
            self.taskbar.HrInit()
        except Exception as e:
            self.taskbar = None
    def set_progress(self, value, total=100, state=None):
        if not self.taskbar or not self.hwnd:
            return
        try:
            if state is not None:
                self.taskbar.SetProgressState(self.hwnd, state)
            if total > 0:
                self.taskbar.SetProgressValue(self.hwnd, int(value), int(total))
        except Exception: pass
    def set_state(self, state):
        if self.taskbar and self.hwnd:
            try: self.taskbar.SetProgressState(self.hwnd, state)
            except Exception: pass
    def clear(self):
        self.set_state(self.TBPF_NOPROGRESS)

class IndicatorDot:
    """ヘッダー用 ステータスドット（パルスアニメーション付き）"""
    _COLORS = {"idle": "#64748b", "running": "#2b6ff0", "done": "#16a34a", "error": "#ef4444"}
    _PULSE_COLORS = ("#3b82f6", "#1d4ed8")  # 交互に点滅する2色
    _PULSE_INTERVAL_MS = 500  # 点滅間隔（ms）

    def __init__(self, parent, size=14):
        bg = current_colors()["CARD"]
        self.canvas = tk.Canvas(parent, width=size, height=size,
                                highlightthickness=0, bg=bg, bd=0)
        self.size = size
        self.state = "idle"
        self._pulse_after = None
        self._pulse_tick = 0
        self.draw("idle")

    def draw(self, state, color=None):
        """ドットを描画。color を省略则 state から自動選択。"""
        self.state = state
        c = self.canvas
        c.delete("all")
        col = color or self._COLORS.get(state, "#94a3b8")
        s = self.size
        c.create_oval(1, 1, s - 1, s - 1, fill=col, outline="")
        if state == "running":
            c.create_oval(s * 0.3, s * 0.3, s * 0.7, s * 0.7,
                          fill="white", outline="")

    # ── パルスアニメーション ──

    def pulse(self, enable=True):
        """enable=True で点滅開始、False で停止。"""
        self._cancel_pulse()
        if enable:
            self._pulse_tick = 0
            self._schedule_pulse()
        else:
            # 停止時は running の通常色で再描画
            self.draw("running")

    def _cancel_pulse(self):
        if self._pulse_after is not None:
            try:
                self.canvas.after_cancel(self._pulse_after)
            except Exception:
                pass
            self._pulse_after = None

    def _schedule_pulse(self):
        """次のティックをスケジュールする。"""
        self._pulse_after = self.canvas.after(
            self._PULSE_INTERVAL_MS, self._pulse_tick_fn)

    def _pulse_tick_fn(self):
        """1ティック分のアニメーションを実行し、次をスケジュール。"""
        if self.state != "running":
            self._pulse_after = None
            return
        # 交互に2色を切り替え
        color = self._PULSE_COLORS[self._pulse_tick % 2]
        self._pulse_tick += 1
        self.draw("running", color=color)
        self._schedule_pulse()

    def pack(self, **kw):
        self.canvas.pack(**kw)

    def configure(self, **kw):
        pass

# ── Config ──
class _BatchContext:
    """コンテキストマネージャ: バッチ中の save() を抑制"""
    def __init__(self, config):
        self._config = config
    def __enter__(self):
        self._config._batch_depth += 1
        return self
    def __exit__(self, *exc):
        self._config._batch_depth -= 1
        if self._config._batch_depth == 0 and self._config._dirty:
            self._config._dirty = False
            self._config.save()


class ConfigManager:
    def __init__(self):
        self.dir = os.path.join(os.getenv("APPDATA") or os.path.expanduser("~"), "SimpleExtract")
        self.path = os.path.join(self.dir, "config.json")
        self._batch_depth = 0
        self._dirty = False
        self.data = {
            "dest_mode": "same", "custom_dest": "", "open_folder": True,
            "delete_after": False, "overwrite_mode": "smart",  # smart/overwrite/skip
            "auto_extract": False, "notifications": True, "theme": "light",
            "context_menu": False, "history": [], "window_size": "1050x720"
        }
        self.load()
    def load(self):
        try:
            if os.path.exists(self.path):
                with open(self.path, "r", encoding="utf-8") as f:
                    d = json.load(f)
                    self.data.update(d)
        except Exception: pass
    def save(self):
        try:
            os.makedirs(self.dir, exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception: pass
    def get(self, k, default=None): return self.data.get(k, default)
    def set(self, k, v):
        self.data[k] = v
        if self._batch_depth > 0:
            self._dirty = True
        else:
            self.save()
    def batch(self):
        """with CONFIG.batch(): で囲むと、中での set() は即保存されず、
        コンテキスト離脱時にまとめて1回だけ save() される。"""
        return _BatchContext(self)
    def add_history(self, archive, dest, ok):
        h = {"archive": os.path.basename(archive), "path": archive, "dest": dest,
             "time": datetime.now().strftime("%Y-%m-%d %H:%M"), "ok": ok}
        hist = self.data.get("history", [])
        hist.insert(0, h)
        self.data["history"] = hist[:30]
        if self._batch_depth > 0:
            self._dirty = True
        else:
            self.save()
    def clear_history(self):
        self.data["history"] = []
        if self._batch_depth > 0:
            self._dirty = True
        else:
            self.save()

CONFIG = ConfigManager()

def current_colors():
    return DARK if CONFIG.get("theme")=="dark" else LIGHT

# ── Association ──
class AssociationManager:
    @staticmethod
    def _progid(ext): return f"{PROGID_PREFIX}{ext}"
    @staticmethod
    def is_associated(ext):
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, rf"Software\Classes\{ext}") as k:
                v,_=winreg.QueryValueEx(k,""); return v==AssociationManager._progid(ext)
        except FileNotFoundError: return False
        except PermissionError:
            logging.warning("レジストリ読み取り権限がありません: %s", ext); return False
        except Exception as e:
            logging.debug("関連付け確認中にエラー (%s): %s", ext, e); return False
    @staticmethod
    def associate(ext):
        progid=AssociationManager._progid(ext)
        exe_cmd=f'{get_exe_path_quoted()} "%1"'
        icon=get_exe_icon()
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"Software\Classes\{ext}") as k:
            winreg.SetValueEx(k,"",0,winreg.REG_SZ,progid)
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"Software\Classes\{progid}") as k:
            winreg.SetValueEx(k,"",0,winreg.REG_SZ,f"{EXT_DESCRIPTIONS.get(ext,ext)} ({APP_NAME})")
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"Software\Classes\{progid}\DefaultIcon") as k:
            winreg.SetValueEx(k,"",0,winreg.REG_SZ,f"{icon},0")
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"Software\Classes\{progid}\shell\open\command") as k:
            winreg.SetValueEx(k,"",0,winreg.REG_SZ,exe_cmd)
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"Software\Classes\{progid}\shell\extract") as k:
            winreg.SetValueEx(k,"",0,winreg.REG_SZ,"SimpleExtractで解凍"); winreg.SetValueEx(k,"Icon",0,winreg.REG_SZ,icon)
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"Software\Classes\{progid}\shell\extract\command") as k:
            winreg.SetValueEx(k,"",0,winreg.REG_SZ,exe_cmd)
    @staticmethod
    def unassociate(ext):
        progid=AssociationManager._progid(ext)
        try:
            if AssociationManager.is_associated(ext):
                try: winreg.DeleteKey(winreg.HKEY_CURRENT_USER, rf"Software\Classes\{ext}")
                except OSError:
                    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, rf"Software\Classes\{ext}",0,winreg.KEY_SET_VALUE) as k:
                        winreg.SetValueEx(k,"",0,winreg.REG_SZ,"")
        except PermissionError:
            logging.warning("関連付けの解除に権限がありません: %s", ext)
        except Exception as e:
            logging.warning("関連付け解除中にエラー (%s): %s", ext, e)
        def del_tree(root, sub):
            try:
                with winreg.OpenKey(root, sub) as k:
                    while True:
                        try: s=winreg.EnumKey(k,0); del_tree(root, sub+"\\"+s)
                        except OSError: break
                winreg.DeleteKey(root, sub)
            except FileNotFoundError: pass
            except PermissionError:
                logging.warning("レジストリキーの削除に権限がありません: %s\\%s", root, sub)
            except Exception as e:
                logging.debug("レジストリ掃除中にエラー (%s): %s", sub, e)
        del_tree(winreg.HKEY_CURRENT_USER, rf"Software\Classes\{progid}")
    @staticmethod
    def is_context_menu_enabled():
        try: winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\*\shell\SimpleExtract"); return True
        except Exception: return False
    @staticmethod
    def is_submenu_enabled():
        try: winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\*\shell\SimpleExtractSub"); return True
        except Exception: return False
    @staticmethod
    def set_context_menu(enable, submenu=False):
        # シンプル版とサブメニュー版
        # まず既存を削除
        def del_tree(root, sub):
            try:
                with winreg.OpenKey(root, sub) as k:
                    while True:
                        try: s=winreg.EnumKey(k,0); del_tree(root, sub+"\\"+s)
                        except OSError: break
                winreg.DeleteKey(root, sub)
            except FileNotFoundError: pass
            except PermissionError:
                logging.warning("レジストリキーの削除に権限がありません: %s\\%s", root, sub)
            except Exception as e:
                logging.debug("レジストリ掃除中にエラー (%s): %s", sub, e)
        del_tree(winreg.HKEY_CURRENT_USER, r"Software\Classes\*\shell\SimpleExtract")
        del_tree(winreg.HKEY_CURRENT_USER, r"Software\Classes\*\shell\SimpleExtractSub")
        # CommandStore も掃除
        for name in ["SimpleExtract.open","SimpleExtract.here","SimpleExtract.desktop"]:
            del_tree(winreg.HKEY_CURRENT_USER, rf"Software\Microsoft\Windows\CurrentVersion\Explorer\CommandStore\shell\{name}")
        if not enable: return
        exe = get_exe_path_quoted(); icon=get_exe_icon()
        if submenu:
            # サブメニュー親
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\*\shell\SimpleExtractSub") as k:
                winreg.SetValueEx(k,"",0,winreg.REG_SZ,"SimpleExtract")
                winreg.SetValueEx(k,"Icon",0,winreg.REG_SZ,icon)
                winreg.SetValueEx(k,"SubCommands",0,winreg.REG_SZ,"SimpleExtract.open;SimpleExtract.here;SimpleExtract.desktop")
            # CommandStore にコマンド登録
            cmds = {
                "SimpleExtract.open": ("SimpleExtractで開く", exe+' "%1"'),
                "SimpleExtract.here": ("ここに解凍", exe+' "%1" --here'),
                "SimpleExtract.desktop": ("デスクトップに解凍", exe+' "%1" --desktop'),
            }
            for key,(title,cmd) in cmds.items():
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"Software\Microsoft\Windows\CurrentVersion\Explorer\CommandStore\shell\{key}") as k:
                    winreg.SetValueEx(k,"",0,winreg.REG_SZ,title); winreg.SetValueEx(k,"Icon",0,winreg.REG_SZ,icon)
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"Software\Microsoft\Windows\CurrentVersion\Explorer\CommandStore\shell\{key}\command") as k:
                    winreg.SetValueEx(k,"",0,winreg.REG_SZ,cmd)
        else:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\*\shell\SimpleExtract") as k:
                winreg.SetValueEx(k,"",0,winreg.REG_SZ,"SimpleExtractで解凍"); winreg.SetValueEx(k,"Icon",0,winreg.REG_SZ,icon)
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\*\shell\SimpleExtract\command") as k:
                winreg.SetValueEx(k,"",0,winreg.REG_SZ,exe+' "%1"')
    @staticmethod
    def has_sendto():
        sendto = os.path.join(os.getenv("APPDATA") or "", r"Microsoft\Windows\SendTo", "SimpleExtract.lnk")
        return os.path.exists(sendto)
    @staticmethod
    def _sendto_target_and_arguments():
        target = sys.executable
        if getattr(sys, 'frozen', False):
            return target, '"%1"'
        return target, f'"{os.path.abspath(__file__)}" "%1"'

    @staticmethod
    def set_sendto(enable):
        sendto_dir = os.path.join(os.getenv("APPDATA") or "", r"Microsoft\Windows\SendTo")
        lnk = os.path.join(sendto_dir, "SimpleExtract.lnk")
        if enable:
            try:
                exe, arguments = AssociationManager._sendto_target_and_arguments()

                def ps_quote(value):
                    return str(value).replace("'", "''")

                ps = (
                    "$s=(New-Object -COM WScript.Shell).CreateShortcut('"
                    + ps_quote(lnk)
                    + "'); $s.TargetPath='"
                    + ps_quote(exe)
                    + "'; $s.Arguments='"
                    + ps_quote(arguments)
                    + "'; $s.IconLocation='"
                    + ps_quote(exe)
                    + "'; $s.Save()"
                )
                subprocess.run(
                    ["powershell", "-NoProfile", "-Command", ps],
                    capture_output=True,
                    check=False,
                )
                if not os.path.exists(lnk):
                    with open(lnk+".txt", "w", encoding="utf-8") as f:
                        f.write(f"{exe}\n{arguments}\n")
            except PermissionError:
                logging.warning("SendTo ショートカットの作成に権限がありません: %s", lnk)
            except Exception as e:
                logging.warning("SendTo ショートカット作成中にエラー: %s", e)
        else:
            try:
                if os.path.exists(lnk): os.remove(lnk)
                if os.path.exists(lnk+".txt"): os.remove(lnk+".txt")
            except PermissionError:
                logging.warning("SendTo ショートカットの削除に権限がありません: %s", lnk)
            except Exception as e:
                logging.warning("SendTo ショートカット削除中にエラー: %s", e)


# ── Extractor ──
class Extractor:
    cancel_flag = threading.Event()
    # ZipBomb閾値: 100倍 or 10GB
    ZIPBOMB_RATIO = 100
    ZIPBOMB_MAX_UNCOMPRESSED = 10 * 1024 * 1024 * 1024  # 10GB

    @staticmethod
    def _safe_dest_path(dest_dir, member_name):
        """アーカイブ内のmember_nameをdest_dir直下に解決し、
        パストラバーサル（../../etc/passwd 等）を検出する。
        安全なら解決済みパスを、不正なら None を返す。"""
        dest_dir = os.path.realpath(dest_dir)
        target = os.path.realpath(os.path.join(dest_dir, member_name))
        if not (target == dest_dir or target.startswith(dest_dir + os.sep)):
            return None
        return target

    @staticmethod
    def list_contents(archive_path, password=None):
        """(name, size, is_dir, dt, encrypted) を返す。パスワード無しでも一覧は可能な限り返す"""
        lower=archive_path.lower(); results=[]
        try:
            if lower.endswith(".zip"):
                with zipfile.ZipFile(archive_path,'r') as zf:
                    for info in zf.infolist():
                        encrypted = bool(info.flag_bits & 0x1)
                        # ファイル名の文字化け対策: cp932試行
                        try:
                            fname = info.filename
                        except Exception:
                            fname = info.filename
                        results.append((fname, info.file_size, info.is_dir(), info.date_time, encrypted))
            elif lower.endswith(".7z"):
                if not _ensure_py7zr(): return None,"py7zr未インストール"
                try:
                    import py7zr
                    with py7zr.SevenZipFile(archive_path,mode='r',password=password) as z:
                        for f in z.list():
                            enc = bool(getattr(f, 'is_encrypted', False))
                            results.append((f.filename, f.uncompressed if hasattr(f,'uncompressed') else 0, f.is_directory, None, enc))
                except Exception as e:
                    if "password" in str(e).lower() or "encrypted" in str(e).lower():
                        # パスワード無しでは一覧取得不可な7zもあるが、可能な限り返す
                        if password is None:
                            return None, "パスワードが必要です（7Zは暗号化されています）"
                        raise
                    raise
            elif lower.endswith((".tar",".tar.gz",".tgz")) or lower.endswith(".gz") or lower.endswith(".bz2"):
                if (
                    (lower.endswith(".gz") and not lower.endswith(".tar.gz") and not lower.endswith(".tgz"))
                    or lower.endswith(".bz2")
                ):
                    # standalone gzip/bzip2は事前に完全な展開サイズを得られない。
                    # extract() 側でZIPBOMB_MAX_UNCOMPRESSEDを実測バイト数に適用する。
                    results.append((pathlib.Path(archive_path).stem, os.path.getsize(archive_path), False, None, False))
                else:
                    with tarfile.open(archive_path,'r:*') as tf:
                        for m in tf.getmembers(): results.append((m.name,m.size,m.isdir(),None, False))
            elif lower.endswith(".rar"):
                if not _ensure_rarfile(): return None,"rarfile未インストール"
                import rarfile
                with rarfile.RarFile(archive_path) as rf:
                    if password: rf.setpassword(password)
                    for info in rf.infolist():
                        enc = bool(info.needs_password()) if hasattr(info, 'needs_password') else False
                        results.append((info.filename,info.file_size,info.isdir(),info.date_time, enc))
            else: return None,"未対応形式"
        except RuntimeError as e:
            if "password" in str(e).lower() or "encrypted" in str(e).lower(): return None,"パスワードが必要です"
            return None,str(e)
        except zipfile.BadZipFile: return None,"壊れたZIPファイルです"
        except Exception as e: return None,str(e)
        return results,None

    @staticmethod
    def preview_file(archive_path, inner_path, password=None, max_bytes=512*1024):
        """アーカイブ内の1ファイルの先頭max_bytesを返す（テキスト/画像プレビュー用）"""
        lower=archive_path.lower()
        try:
            if lower.endswith(".zip"):
                with zipfile.ZipFile(archive_path,'r') as zf:
                    pwd = password.encode('utf-8') if password else None
                    with zf.open(inner_path, 'r', pwd=pwd) as member:
                        return member.read(max_bytes), None
            elif lower.endswith(".7z"):
                if not _ensure_py7zr(): return None, "py7zr未インストール"
                import tempfile
                tmp = tempfile.mkdtemp()
                try:
                    import py7zr
                    with py7zr.SevenZipFile(archive_path, mode='r', password=password) as z:
                        matched = next((item for item in z.list() if item.filename == inner_path), None)
                        if matched is None:
                            return None, "プレビュー対象が見つかりません"
                        uncompressed = int(getattr(matched, 'uncompressed', 0) or 0)
                        if uncompressed > max_bytes:
                            return None, (
                                f"プレビュー上限を超えています "
                                f"({human_size(uncompressed)} > {human_size(max_bytes)})"
                            )
                        # py7zrにはmember stream APIがないため、上限内の対象だけ一時展開する。
                        z.extract(path=tmp, targets=[inner_path])
                    fp = os.path.join(tmp, inner_path)
                    if os.path.exists(fp):
                        with open(fp, 'rb') as f: return f.read(max_bytes), None
                    for root,_,files in os.walk(tmp):
                        for fn in files:
                            fp2=os.path.join(root,fn)
                            if fn==os.path.basename(inner_path):
                                with open(fp2,'rb') as f: return f.read(max_bytes), None
                    return None, "プレビュー対象が見つかりません"
                finally:
                    try: shutil.rmtree(tmp)
                    except Exception: pass
            elif lower.endswith(".rar"):
                if not _ensure_rarfile(): return None, "rarfile未インストール"
                import rarfile
                with rarfile.RarFile(archive_path) as rf:
                    if password: rf.setpassword(password)
                    with rf.open(inner_path) as member:
                        return member.read(max_bytes), None
            elif lower.endswith((".tar",".tar.gz",".tgz")):
                with tarfile.open(archive_path,'r:*') as tf:
                    m=tf.getmember(inner_path)
                    f=tf.extractfile(m)
                    if f: return f.read(max_bytes), None
                    return None, "読み込めません"
        except Exception as e:
            return None, str(e)
        return None, "未対応"


    @staticmethod
    def extract(archive_path, dest_dir, password, progress_cb, log_cb):
        Extractor.cancel_flag.clear()  # 各操作の開始時にリセット（前回の残留を防止）
        os.makedirs(dest_dir,exist_ok=True)
        lower=archive_path.lower()
        # ZipBomb事前チェック
        try:
            items,_ = Extractor.list_contents(archive_path, password)
            if items:
                total_uncompressed = sum(s for _,s,is_dir,_,enc in items if not is_dir)
                total_compressed = os.path.getsize(archive_path)
                if total_compressed>0 and total_uncompressed/total_compressed > Extractor.ZIPBOMB_RATIO and total_uncompressed > 100*1024*1024:
                    if log_cb: log_cb(f"⚠️ 警告: 圧縮率が異常に高いです ({total_uncompressed//total_compressed}倍) - ZipBombの可能性")
                if total_uncompressed > Extractor.ZIPBOMB_MAX_UNCOMPRESSED:
                    return False, f"展開後のサイズが大きすぎます ({human_size(total_uncompressed)} > 10GB) - 中止しました"
        except Exception: pass
        try:
            if lower.endswith(".zip"):
                with zipfile.ZipFile(archive_path,'r') as zf:
                    members=zf.infolist()
                    total_bytes = sum(m.file_size for m in members if not m.is_dir())
                    done_bytes = 0
                    for i,info in enumerate(members):
                        if Extractor.cancel_flag.is_set():
                            # 部分的に展開されたファイルを掃除
                            return False,"キャンセルされました"
                        if info.is_dir():
                            # ディレクトリは作成のみ（パストラバーサル検証付き）
                            safe = Extractor._safe_dest_path(dest_dir, info.filename)
                            if safe is None:
                                log_cb(f"⚠️ スキップ（パストラバーサル）: {info.filename}")
                                continue
                            try:
                                os.makedirs(safe, exist_ok=True)
                            except Exception: pass
                            continue
                        # パストラバーサル検証: ../../ 等でアウト側に書き出されないか確認
                        dest_path = Extractor._safe_dest_path(dest_dir, info.filename)
                        if dest_path is None:
                            log_cb(f"⚠️ スキップ（パストラバーサル）: {info.filename}")
                            done_bytes += info.file_size
                            if total_bytes > 0 and progress_cb:
                                progress_cb(int(done_bytes / total_bytes * 100))
                            continue
                        log_cb(f"展開中: {info.filename} ({human_size(info.file_size)})")
                        # ストリーミングで大容量対応（1MBチャンク）
                        try:
                            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                            # 上書きチェックは呼び出し側で済ませているが、ここでもサイズで進捗
                            with zf.open(info, pwd=password.encode('utf-8') if password else None) as src, open(dest_path, 'wb') as dst:
                                while True:
                                    if Extractor.cancel_flag.is_set():
                                        try: dst.close(); os.remove(dest_path)
                                        except Exception: pass
                                        return False,"キャンセルされました"
                                    chunk = src.read(1024*1024)
                                    if not chunk: break
                                    dst.write(chunk)
                                    done_bytes += len(chunk)
                                    if total_bytes>0 and progress_cb:
                                        progress_cb(int(done_bytes/total_bytes*100))
                                    else:
                                        progress_cb(int((i+1)/len(members)*100))
                        except RuntimeError as e:
                            if "password" in str(e).lower(): raise RuntimeError("パスワードが違います")
                            raise
                        if total_bytes==0 and progress_cb:
                            progress_cb(int((i+1)/len(members)*100))
            elif lower.endswith(".7z"):
                if not _ensure_py7zr(): raise RuntimeError("py7zr未インストール")
                log_cb("7z展開中..."); progress_cb(10)
                # py7zrは分割進捗が取れないので、事前チェック後は一括
                if Extractor.cancel_flag.is_set(): return False,"キャンセルされました"
                import py7zr
                with py7zr.SevenZipFile(archive_path,mode='r',password=password) as z:
                    z.extractall(path=dest_dir)
                progress_cb(100)
            elif lower.endswith((".tar",".tar.gz",".tgz")):
                with tarfile.open(archive_path,'r:*') as tf:
                    members=tf.getmembers()
                    total_bytes = sum(m.size for m in members if m.isfile())
                    done=0
                    for i,m in enumerate(members):
                        if Extractor.cancel_flag.is_set(): return False,"キャンセルされました"
                        # パストラバーサル検証
                        dest_path = Extractor._safe_dest_path(dest_dir, m.name)
                        if dest_path is None:
                            log_cb(f"⚠️ スキップ（パストラバーサル）: {m.name}")
                            continue
                        log_cb(f"展開中: {m.name}")
                        # 大容量はストリーミング
                        if m.isfile():
                            f=tf.extractfile(m)
                            if f:
                                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                                with open(dest_path,'wb') as out:
                                    while True:
                                        chunk=f.read(1024*1024)
                                        if not chunk: break
                                        out.write(chunk)
                                        done+=len(chunk)
                                        if total_bytes>0 and progress_cb:
                                            progress_cb(int(done/total_bytes*100))
                        elif m.isdir():
                            os.makedirs(dest_path, exist_ok=True)
                            if progress_cb and total_bytes==0:
                                progress_cb(int((i+1)/len(members)*100))
                        else:
                            # Never delegate TAR links or special files to tarfile.extract().
                            # On Python 3.11 there is no data filter, so symlink/hardlink
                            # link targets could otherwise escape the destination directory.
                            log_cb(f"⚠️ スキップ（安全でないTARメンバー）: {m.name}")
            elif lower.endswith(".gz") and not lower.endswith(".tar.gz"):
                import gzip
                out_name=pathlib.Path(archive_path).stem or "output"
                out_path=os.path.join(dest_dir,out_name)
                log_cb(f"展開中: {out_name}")
                total = os.path.getsize(archive_path)
                done=0
                with gzip.open(archive_path,'rb') as fin:
                    with open(out_path,'wb') as fout:
                        while True:
                            if Extractor.cancel_flag.is_set():
                                try: fout.close(); os.remove(out_path)
                                except Exception: pass
                                return False,"キャンセルされました"
                            chunk=fin.read(1024*1024)
                            if not chunk: break
                            done += len(chunk)
                            if done > Extractor.ZIPBOMB_MAX_UNCOMPRESSED:
                                try:
                                    fout.close()
                                    os.remove(out_path)
                                except Exception:
                                    pass
                                return False, (
                                    f"展開後のサイズが大きすぎます "
                                    f"({human_size(done)} > {human_size(Extractor.ZIPBOMB_MAX_UNCOMPRESSED)}) - 中止しました"
                                )
                            fout.write(chunk)
                            if progress_cb and total>0:
                                progress_cb(min(99, int(done/total*100)))
                progress_cb(100)
            elif lower.endswith(".bz2"):
                import bz2
                out_name=pathlib.Path(archive_path).stem or "output"
                out_path=os.path.join(dest_dir,out_name)
                log_cb(f"展開中: {out_name}")
                done=0
                with bz2.open(archive_path,'rb') as fin:
                    with open(out_path,'wb') as fout:
                        while True:
                            if Extractor.cancel_flag.is_set():
                                try: fout.close(); os.remove(out_path)
                                except Exception: pass
                                return False,"キャンセルされました"
                            chunk=fin.read(1024*1024)
                            if not chunk: break
                            done += len(chunk)
                            if done > Extractor.ZIPBOMB_MAX_UNCOMPRESSED:
                                try:
                                    fout.close()
                                    os.remove(out_path)
                                except Exception:
                                    pass
                                return False, (
                                    f"展開後のサイズが大きすぎます "
                                    f"({human_size(done)} > {human_size(Extractor.ZIPBOMB_MAX_UNCOMPRESSED)}) - 中止しました"
                                )
                            fout.write(chunk)
                progress_cb(100)
            elif lower.endswith(".rar"):
                if not _ensure_rarfile(): raise RuntimeError("rarfile未インストール")
                import rarfile
                with rarfile.RarFile(archive_path) as rf:
                    if password: rf.setpassword(password)
                    members=rf.infolist()
                    total_bytes = sum(m.file_size for m in members if not m.isdir())
                    done=0
                    for i,info in enumerate(members):
                        if Extractor.cancel_flag.is_set(): return False,"キャンセルされました"
                        if info.isdir(): continue
                        # パストラバーサル検証
                        if Extractor._safe_dest_path(dest_dir, info.filename) is None:
                            log_cb(f"⚠️ スキップ（パストラバーサル）: {info.filename}")
                            done += info.file_size
                            continue
                        log_cb(f"展開中: {info.filename}")
                        # rarfileはストリーミングが弱いので一括だが、進捗はファイル単位
                        rf.extract(info, path=dest_dir)
                        done+=info.file_size
                        if progress_cb and total_bytes>0:
                            progress_cb(int(done/total_bytes*100))
                        else:
                            progress_cb(int((i+1)/len(members)*100))
            else: raise RuntimeError("未対応形式")
            log_cb(f"完了: {dest_dir}"); return True,None
        except Exception as e:
            # キャンセル時は部分展開を可能なら掃除（dest_dirが空なら削除）
            if "キャンセル" in str(e):
                return False,str(e)
            traceback.print_exc()
            return False,str(e)


class Compressor:
    """圧縮ロジック"""
    cancel_flag = threading.Event()
    @staticmethod
    def compress(files, output_path, fmt="zip", level=5, password=None, progress_cb=None, log_cb=None):
        Compressor.cancel_flag.clear()  # 各操作の開始時にリセット（前回の残留を防止）
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        try:
            if fmt == "zip":
                if password:
                    return False, "ZIPのパスワード付き圧縮は未対応です。暗号化する場合は7Zを選択してください"
                # level 1-9 -> compresslevel
                comp_level = {1:1, 3:3, 5:6, 7:7, 9:9}.get(level, 6)
                with zipfile.ZipFile(output_path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=comp_level) as zf:
                    total = len(files)
                    for i, f in enumerate(files):
                        if Compressor.cancel_flag.is_set(): return False, "キャンセルされました"
                        if os.path.isdir(f):
                            for root, dirs, filenames in os.walk(f):
                                for name in filenames:
                                    fp = os.path.join(root, name)
                                    arc = os.path.relpath(fp, os.path.dirname(f))
                                    if log_cb: log_cb(f"追加: {arc}")
                                    zf.write(fp, arc)
                        else:
                            arc = os.path.basename(f)
                            if log_cb: log_cb(f"追加: {arc}")
                            zf.write(f, arc)
                        if progress_cb: progress_cb(int((i+1)/total*100))
            elif fmt == "7z":
                if not _ensure_py7zr(): return False, "py7zr未インストール"
                if log_cb: log_cb(f"7z作成中: {output_path}")
                if progress_cb: progress_cb(20)
                import py7zr
                with py7zr.SevenZipFile(output_path, 'w', password=password) as z:
                    for f in files:
                        if Compressor.cancel_flag.is_set(): return False, "キャンセルされました"
                        if log_cb: log_cb(f"追加: {os.path.basename(f)}")
                        z.write(f, os.path.basename(f) if not os.path.isdir(f) else os.path.basename(f.rstrip(os.sep)))
                if progress_cb: progress_cb(100)
            elif fmt in ("tar.gz", "tgz", "tar"):
                mode = "w:gz" if fmt in ("tar.gz","tgz") else "w"
                if fmt == "tar": mode = "w"
                with tarfile.open(output_path, mode) as tf:
                    total=len(files)
                    for i,f in enumerate(files):
                        if Compressor.cancel_flag.is_set(): return False, "キャンセルされました"
                        if log_cb: log_cb(f"追加: {os.path.basename(f)}")
                        tf.add(f, arcname=os.path.basename(f))
                        if progress_cb: progress_cb(int((i+1)/total*100))
            else:
                return False, f"未対応形式: {fmt}"
            if log_cb: log_cb(f"作成完了: {output_path} ({human_size(os.path.getsize(output_path))})")
            return True, None
        except Exception as e:
            traceback.print_exc()
            return False, str(e)

class UpdateChecker:
    URL = "https://api.github.com/repos/neoenox/SimpleExtract/releases/latest"
    @staticmethod
    def check(current_version, silent=False, callback=None):
        def worker():
            try:
                req = urllib.request.Request(UpdateChecker.URL, headers={"User-Agent": "SimpleExtract", "Accept":"application/vnd.github+json"})
                with urllib.request.urlopen(req, timeout=6) as res:
                    data = json.loads(res.read().decode('utf-8'))
                    latest = data.get("tag_name", "").lstrip("v")
                    url = data.get("html_url", "")
                    notes = data.get("body", "")[:300]
                    if latest and latest != current_version:
                        # バージョン比較（簡易）
                        def parse(v): return [int(x) for x in v.split(".") if x.isdigit()]
                        if parse(latest) > parse(current_version):
                            if callback: callback(True, latest, url, notes)
                            return
                    if callback: callback(False, current_version, "", "")
            except urllib.error.HTTPError as e:
                if callback:
                    callback(None, current_version, "", f"HTTP {e.code}: {e.reason}")
            except Exception as e:
                if callback:
                    callback(None, current_version, "", str(e))
        threading.Thread(target=worker, daemon=True).start()

# ── Association Window ──
class AssociationWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("関連付け設定 - SimpleExtract")
        self.geometry("580x680")
        self.minsize(560, 620)
        self.configure(fg_color=current_colors()["BG"])
        self.transient(parent); self.grab_set()
        self.vars={}
        self._build(); self._refresh()
    def _build(self):
        C=current_colors()
        header=ctk.CTkFrame(self, fg_color=C["CARD"], corner_radius=0, height=56)
        header.pack(fill="x", side="top"); header.pack_propagate(False)
        ctk.CTkLabel(header, text="🔗 ファイル関連付け", font=("BIZ UDGothic",16,"bold"), text_color=C["TEXT"]).pack(side="left", padx=16, pady=12)
        ctk.CTkLabel(header, text="ダブルクリックで開く", font=("BIZ UDGothic",11), text_color=C["SUB"]).pack(side="left", padx=(8,0))
        desc=ctk.CTkFrame(self, fg_color=C["DROP_BG"], corner_radius=8, border_width=1, border_color=C["BORDER"])
        desc.pack(fill="x", padx=16, pady=12)
        ctk.CTkLabel(desc, text="拡張子に関連付けるとダブルクリックで解凍できます。\nHKCUに登録するため管理者権限は不要です。", font=("BIZ UDGothic",10), text_color=C["TEXT"], justify="left", wraplength=480).pack(padx=12, pady=8, anchor="w")

        list_frame=ctk.CTkFrame(self, fg_color=C["CARD"], corner_radius=10, border_width=1, border_color=C["BORDER"])
        list_frame.pack(fill="both", expand=True, padx=16, pady=(0,8))
        ctk.CTkLabel(list_frame, text="関連付ける拡張子", font=("BIZ UDGothic",12,"bold"), text_color=C["TEXT"]).pack(anchor="w", padx=14, pady=(12,6))
        self.check_container=ctk.CTkScrollableFrame(list_frame, fg_color="transparent", height=180)
        self.check_container.pack(fill="both", expand=True, padx=8, pady=4)
        for ext in ASSOC_EXTS:
            row=ctk.CTkFrame(self.check_container, fg_color="transparent"); row.pack(fill="x", padx=6, pady=3)
            var=ctk.BooleanVar(value=False); self.vars[ext]=var
            cb=ctk.CTkCheckBox(row, text=f"{EXT_ICONS.get(ext,'📄')}  {ext}  —  {EXT_DESCRIPTIONS.get(ext,ext)}", variable=var, font=("BIZ UDGothic",11), text_color=C["TEXT"], fg_color=COLOR_PRIMARY, border_color=C["BORDER"])
            cb.pack(side="left", padx=4)
            lbl=ctk.CTkLabel(row, text="", font=("BIZ UDGothic",10), text_color=C["SUB"]); lbl.pack(side="right", padx=8); var._status_label=lbl
        btn_row=ctk.CTkFrame(list_frame, fg_color="transparent"); btn_row.pack(fill="x", padx=14, pady=(6,10))
        ctk.CTkButton(btn_row, text="すべて選択", width=90, height=26, fg_color="white", text_color=C["TEXT"], hover_color=C["HOVER"], border_width=1, border_color=C["BORDER"], command=lambda:self._set_all(True)).pack(side="left", padx=(0,6))
        ctk.CTkButton(btn_row, text="すべて解除", width=90, height=26, fg_color="white", text_color=C["TEXT"], hover_color=C["HOVER"], border_width=1, border_color=C["BORDER"], command=lambda:self._set_all(False)).pack(side="left")

        # オプション
        opt_frame=ctk.CTkFrame(self, fg_color=C["CARD"], corner_radius=10, border_width=1, border_color=C["BORDER"])
        opt_frame.pack(fill="x", padx=16, pady=6)
        ctk.CTkLabel(opt_frame, text="エクスプローラー連携", font=("BIZ UDGothic",11,"bold"), text_color=C["TEXT"]).pack(anchor="w", padx=14, pady=(10,4))
        self.var_ctx=ctk.BooleanVar(value=AssociationManager.is_context_menu_enabled() or AssociationManager.is_submenu_enabled())
        self.var_submenu=ctk.BooleanVar(value=AssociationManager.is_submenu_enabled())
        self.var_sendto=ctk.BooleanVar(value=AssociationManager.has_sendto())
        self.var_auto=ctk.BooleanVar(value=CONFIG.get("auto_extract", False))
        ctk.CTkCheckBox(opt_frame, text="右クリックメニューに『SimpleExtractで解凍』を追加", variable=self.var_ctx, font=("BIZ UDGothic",11), text_color=C["TEXT"], fg_color=COLOR_PRIMARY, border_color=C["BORDER"]).pack(anchor="w", padx=14, pady=2)
        ctk.CTkCheckBox(opt_frame, text="  └ サブメニュー化（ここに解凍/デスクトップに解凍）", variable=self.var_submenu, font=("BIZ UDGothic",10), text_color=C["TEXT"], fg_color=COLOR_PRIMARY, border_color=C["BORDER"]).pack(anchor="w", padx=34, pady=1)
        ctk.CTkCheckBox(opt_frame, text="送るメニューに追加（SendTo）", variable=self.var_sendto, font=("BIZ UDGothic",11), text_color=C["TEXT"], fg_color=COLOR_PRIMARY, border_color=C["BORDER"]).pack(anchor="w", padx=14, pady=2)
        ctk.CTkCheckBox(opt_frame, text="ダブルクリックで自動解凍（確認なしで即展開）", variable=self.var_auto, font=("BIZ UDGothic",11), text_color=COLOR_DANGER if self.var_auto.get() else C["TEXT"], fg_color=COLOR_PRIMARY, border_color=C["BORDER"]).pack(anchor="w", padx=14, pady=(6,2))
        ctk.CTkLabel(opt_frame, text="ONにすると関連付けファイルを開いた瞬間に解凍が始まります", font=("BIZ UDGothic",9), text_color=C["SUB"]).pack(anchor="w", padx=14, pady=(0,10))

        action=ctk.CTkFrame(self, fg_color="transparent"); action.pack(fill="x", padx=16, pady=8)
        ctk.CTkButton(action, text="選択を関連付け", height=38, font=("BIZ UDGothic",12,"bold"), fg_color=COLOR_PRIMARY, hover_color=COLOR_PRIMARY_HOVER, command=self._apply_assoc).pack(side="left", fill="x", expand=True, padx=(0,6))
        ctk.CTkButton(action, text="関連付けを解除", height=38, font=("BIZ UDGothic",11), fg_color="white", text_color="#dc2626", hover_color="#fef2f2", border_width=1, border_color="#fecaca", command=self._apply_unassoc).pack(side="left", fill="x", expand=True, padx=(6,0))
        # 完了バー（見切れ対策で大きく）
        bottom=ctk.CTkFrame(self, fg_color=C["CARD"], corner_radius=10, border_width=1, border_color=C["BORDER"])
        bottom.pack(fill="x", padx=16, pady=(4,12))
        self.status_label=ctk.CTkLabel(bottom, text="", font=("BIZ UDGothic",9), text_color=C["SUB"])
        self.status_label.pack(side="top", anchor="w", padx=10, pady=(6,2))
        ctk.CTkButton(bottom, text="✓  設定完了して閉じる", height=40, font=("BIZ UDGothic",13,"bold"), fg_color=COLOR_SUCCESS, hover_color="#15803d", corner_radius=8, command=self._done).pack(fill="x", padx=10, pady=(4,10))
        # Escで閉じる
        self.bind("<Escape>", lambda e: self._done())
    def _set_all(self, v):
        for var in self.vars.values(): var.set(v)
    def _refresh(self):
        for ext,var in self.vars.items():
            ok=AssociationManager.is_associated(ext); var.set(ok)
            lbl=var._status_label
            if ok: lbl.configure(text="● 関連付け済み", text_color=COLOR_SUCCESS)
            else: lbl.configure(text="○ 未設定", text_color=current_colors()["SUB"])
        self.var_ctx.set(AssociationManager.is_context_menu_enabled() or AssociationManager.is_submenu_enabled())
        self.var_submenu.set(AssociationManager.is_submenu_enabled())
        exe=sys.executable if getattr(sys,'frozen',False) else os.path.abspath(__file__)
        self.status_label.configure(text=f"実行: {exe[:50]}")
    def _apply_assoc(self):
        sel=[e for e,v in self.vars.items() if v.get()]
        if not sel: messagebox.showwarning("選択なし","少なくとも1つ選択してください", parent=self); return
        try:
            for e in sel: AssociationManager.associate(e)
            AssociationManager.set_context_menu(self.var_ctx.get(), submenu=self.var_submenu.get())
            AssociationManager.set_sendto(self.var_sendto.get())
            with CONFIG.batch():
                CONFIG.set("auto_extract", bool(self.var_auto.get()))
                CONFIG.set("context_menu", bool(self.var_ctx.get()))
            notify_shell_change(); self._refresh()
            messagebox.showinfo("完了", f"関連付けました:\n{', '.join(sel)}", parent=self)
        except Exception as e: messagebox.showerror("エラー",str(e), parent=self)
    def _apply_unassoc(self):
        sel=[e for e,v in self.vars.items() if v.get()]
        if not sel:
            assoc=[e for e in ASSOC_EXTS if AssociationManager.is_associated(e)]
            if not assoc: messagebox.showinfo("情報","解除する関連付けがありません", parent=self); return
            if not messagebox.askyesno("確認", f"すべて解除しますか？\n{', '.join(assoc)}", parent=self): return
            sel=assoc
        else:
            if not messagebox.askyesno("確認", f"解除しますか？\n{', '.join(sel)}", parent=self): return
        try:
            for e in sel: AssociationManager.unassociate(e)
            if not self.var_ctx.get():
                AssociationManager.set_context_menu(False)
            notify_shell_change(); self._refresh()
            messagebox.showinfo("完了", f"解除しました:\n{', '.join(sel)}", parent=self)
        except Exception as e: messagebox.showerror("エラー",str(e), parent=self)
    def _done(self):
        # 設定完了：変更を保存して閉じる（関連付けは適用済みならそのまま、未適用なら自動適用はしないで閉じる）
        try:
            CONFIG.set("auto_extract", bool(self.var_auto.get()))
            # 右クリック等のチェックは即時反映されていない場合もあるので、ここでも反映
            # ただし拡張子関連付けは「選択を関連付け」ボタンで明示的に適用させる
        except Exception: pass
        self.destroy()

class Splash:
    def __init__(self, master):
        self.win = tk.Toplevel(master)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        w, h = 320, 140
        ws = self.win.winfo_screenwidth(); hs = self.win.winfo_screenheight()
        self.win.geometry(f"{w}x{h}+{int(ws/2-w/2)}+{int(hs/2-h/2)}")
        self.win.configure(bg="#1e293b")
        tk.Label(self.win, text="📦 SimpleExtract", font=("BIZ UDGothic", 16, "bold"), bg="#1e293b", fg="white").pack(pady=(24,4))
        tk.Label(self.win, text="起動中...", font=("BIZ UDGothic", 10), bg="#1e293b", fg="#94a3b8").pack()
        self.bar = ttk.Progressbar(self.win, mode="indeterminate", length=240)
        self.bar.pack(pady=16)
        self.bar.start(10)
        self.win.update()
    def close(self):
        try: self.bar.stop(); self.win.destroy()
        except Exception: pass

# ── Main App ──
class SimpleExtractApp(TkinterDnD.Tk):
    def __init__(self):
        # DPI Awareness はウィンドウ生成前に設定（root不要）
        enable_font_antialiasing(None)
        super().__init__()
        # スプラッシュ表示（体感を速く）
        try:
            self.withdraw()
            _splash = Splash(self)
        except Exception: _splash = None
        # 生成後にフォント・スケーリングを適用
        enable_font_antialiasing(self)
        ctk.set_appearance_mode(CONFIG.get("theme","light"))
        # フォント定義（アンチエイリアス最適化）
        self.font_title = get_font(size=20, weight="bold")
        self.font_sub = get_font(size=11)
        self.font_body = get_font(size=11)
        self.font_small = get_font(size=10)
        self.font_mono = get_font(family="Consolas", size=9)
        C=current_colors()
        self.title(f"{APP_NAME} v{APP_VERSION} - シンプル解凍")
        self.geometry(CONFIG.get("window_size","1050x720"))
        self.minsize(1000, 680)
        self.configure(bg=C["BG"])
        self.queue_files=[]  # バッチ用
        self.archive_path=None
        self.compress_files=[]  # 圧縮用
        self.dest_mode=ctk.StringVar(value=CONFIG.get("dest_mode","same"))
        self.custom_dest=CONFIG.get("custom_dest","")
        self.password_visible=False
        self.is_extracting=False
        self.is_compressing=False
        self._build_ui()
        self._bind_dnd()
        self._apply_theme()
        self.taskbar = None
        # スプラッシュを閉じてメイン表示
        try:
            _splash.close()
            self.deiconify()
            self.lift()
            self.focus_force()
        except Exception: pass
        # 軽量化: 履歴と圧縮タブは遅延ロード
        self.after(100, self._load_history_ui)
        self.after(500, self._init_taskbar)
        self.after(800, self._build_compress_tab)
        # 更新チェックはさらに遅延（起動を妨げない）
        self.after(5000, lambda: self.check_update(silent=True))
    def _build_ui(self):
        C=current_colors()
        # Header
        header=ctk.CTkFrame(self, fg_color=C["CARD"], corner_radius=0, height=64)
        header.pack(fill="x", side="top"); header.pack_propagate(False)
        left_h=ctk.CTkFrame(header, fg_color="transparent"); left_h.pack(side="left", padx=20, pady=12)
        ctk.CTkLabel(left_h, text="📦 SimpleExtract", font=("BIZ UDGothic",20,"bold"), text_color=C["TEXT"]).pack(anchor="w")
        ctk.CTkLabel(left_h, text="ZIP / 7Z / TAR / RAR 対応  •  バッチ対応", font=("BIZ UDGothic",11), text_color=C["SUB"]).pack(anchor="w")
        # 中央インジケーター + キューバッジ
        indicator_frame=ctk.CTkFrame(header, fg_color="transparent"); indicator_frame.pack(side="left", padx=24)
        self.indicator_dot = IndicatorDot(indicator_frame)
        self.indicator_dot.pack(side="left", padx=(0,6))
        self.indicator_label = ctk.CTkLabel(indicator_frame, text="待機中", font=("BIZ UDGothic",10), text_color=C["SUB"])
        self.indicator_label.pack(side="left")
        self.indicator_sub = ctk.CTkLabel(indicator_frame, text="", font=("BIZ UDGothic",9), text_color=C["SUB"])
        self.indicator_sub.pack(side="left", padx=(8,0))
        self.queue_badge = ctk.CTkLabel(indicator_frame, text="", font=("BIZ UDGothic",9,"bold"), text_color="white", fg_color=COLOR_PRIMARY, corner_radius=8, width=28, height=18)
        # バッジはキューがあるときだけ表示
        right_h=ctk.CTkFrame(header, fg_color="transparent"); right_h.pack(side="right", padx=16)
        ctk.CTkLabel(right_h, text=f"v{APP_VERSION}", font=("BIZ UDGothic",11), text_color=C["SUB"]).pack(side="left", padx=(0,8))
        self.btn_theme=ctk.CTkButton(right_h, text="🌙" if CONFIG.get("theme")=="light" else "☀️", width=36, height=30, fg_color=C["BG"], text_color=C["TEXT"], hover_color=C["HOVER"], border_width=1, border_color=C["BORDER"], command=self.toggle_theme)
        self.btn_theme.pack(side="left", padx=(0,6))
        ctk.CTkButton(right_h, text="⚙ 関連付け", width=80, height=30, fg_color=C["BG"], text_color=C["TEXT"], hover_color=C["HOVER"], border_width=1, border_color=C["BORDER"], command=self.open_association).pack(side="left", padx=(0,4))
        ctk.CTkButton(right_h, text="更新", width=55, height=30, fg_color=C["BG"], text_color=C["TEXT"], hover_color=C["HOVER"], border_width=1, border_color=C["BORDER"], command=lambda: self.check_update(silent=False)).pack(side="left", padx=(0,4))
        ctk.CTkButton(right_h, text="🎲 おまかせ", width=85, height=30, fg_color="#f59e0b", text_color="white", hover_color="#d97706", font=("BIZ UDGothic",11,"bold"), command=self.omakase_action).pack(side="left", padx=(0,4))
        ctk.CTkButton(right_h, text="使い方", width=65, height=30, fg_color=C["BG"], text_color=C["TEXT"], hover_color=C["HOVER"], border_width=1, border_color=C["BORDER"], command=self.show_help).pack(side="left")

        # 更新バナー（非表示で開始）
        self.update_banner = ctk.CTkFrame(self, fg_color="#fef3c7", corner_radius=0, height=32, border_width=1, border_color="#f59e0b")
        self.update_banner_label = ctk.CTkLabel(self.update_banner, text="", font=("BIZ UDGothic",10,"bold"), text_color="#92400e")
        self.update_banner_label.pack(side="left", padx=12, pady=6)
        self.update_banner_btn = ctk.CTkButton(self.update_banner, text="ダウンロード", width=90, height=24, fg_color=COLOR_WARN, hover_color="#d97706", font=("BIZ UDGothic",10,"bold"), command=self.open_update_url)
        self.update_banner_btn.pack(side="right", padx=8, pady=4)
        ctk.CTkButton(self.update_banner, text="✕", width=24, height=24, fg_color="transparent", text_color="#92400e", hover_color="#fde68a", command=lambda: self.update_banner.pack_forget()).pack(side="right", padx=4)
        self._update_url = ""

        # タブ
        self.tabview = ctk.CTkTabview(self, fg_color=C["BG"], segmented_button_fg_color=C["HOVER"], segmented_button_selected_color=COLOR_PRIMARY, segmented_button_selected_hover_color=COLOR_PRIMARY_HOVER, text_color=C["TEXT"])
        self.tabview.pack(fill="both", expand=True, padx=12, pady=12)
        self.tabview.add("📦 解凍")
        self.tabview.add("🗜️ 圧縮")
        self.tabview.set("📦 解凍")

        # === 解凍タブ ===
        tab_extract = self.tabview.tab("📦 解凍")
        main=ctk.CTkFrame(tab_extract, fg_color="transparent"); main.pack(fill="both", expand=True, padx=6, pady=6)
        left=ctk.CTkFrame(main, fg_color=C["CARD"], corner_radius=12, border_width=1, border_color=C["BORDER"])
        left.pack(side="left", fill="both", expand=True, padx=(0,6))
        right_pane=ctk.CTkFrame(main, fg_color=C["CARD"], corner_radius=12, border_width=1, border_color=C["BORDER"], width=320)
        right_pane.pack(side="right", fill="y", padx=(6,0)); right_pane.pack_propagate(False)

        ctk.CTkLabel(left, text="アーカイブをドロップ（複数OK）", font=("BIZ UDGothic",13,"bold"), text_color=C["TEXT"]).pack(pady=(14,4))
        self.summary_label=ctk.CTkLabel(left, text="⚪ 待機中  •  ファイルをドロップしてください", font=("BIZ UDGothic",10,"bold"), text_color=C["TEXT"], fg_color=C["HOVER"], corner_radius=6, height=26)
        self.summary_label.pack(fill="x", padx=14, pady=(0,4))
        self.drop_frame=ctk.CTkFrame(left, fg_color=C["DROP_BG"], corner_radius=12, border_width=2, border_color=C["DROP_BORDER"])
        self.drop_frame.pack(fill="x", padx=14, pady=4)
        inner=ctk.CTkFrame(self.drop_frame, fg_color="transparent"); inner.pack(padx=14, pady=14, fill="x")
        ctk.CTkLabel(inner, text="⬇️", font=("BIZ UDGothic",28)).pack()
        ctk.CTkLabel(inner, text="ここに ZIP / 7Z / RAR などをドラッグ＆ドロップ", font=("BIZ UDGothic",11), text_color=C["TEXT"], justify="center").pack(pady=(4,8))
        btn_row=ctk.CTkFrame(inner, fg_color="transparent"); btn_row.pack()
        ctk.CTkButton(btn_row, text="ファイルを選択...", fg_color=COLOR_PRIMARY, hover_color=COLOR_PRIMARY_HOVER, corner_radius=8, font=("BIZ UDGothic",11,"bold"), height=34, command=self.pick_files).pack(side="left", padx=4)
        ctk.CTkButton(btn_row, text="フォルダを選択...", fg_color="white", text_color=C["TEXT"], hover_color=C["HOVER"], border_width=1, border_color=C["BORDER"], height=34, command=self.pick_folder).pack(side="left", padx=4)

        queue_header=ctk.CTkFrame(left, fg_color="transparent"); queue_header.pack(fill="x", padx=14, pady=(8,2))
        ctk.CTkLabel(queue_header, text="キュー", font=("BIZ UDGothic",11,"bold"), text_color=C["TEXT"]).pack(side="left")
        self.queue_label=ctk.CTkLabel(queue_header, text="0件", font=("BIZ UDGothic",10), text_color=C["SUB"]); self.queue_label.pack(side="left", padx=8)
        ctk.CTkButton(queue_header, text="クリア", width=60, height=22, fg_color="white", text_color=C["TEXT"], hover_color=C["HOVER"], border_width=1, border_color=C["BORDER"], font=("BIZ UDGothic",9), command=self.clear_queue).pack(side="right")
        self.queue_frame=ctk.CTkScrollableFrame(left, fg_color=C["HOVER"], height=70, corner_radius=8)
        self.queue_frame.pack(fill="x", padx=14, pady=2)
        self.queue_empty_label=ctk.CTkLabel(self.queue_frame, text="ファイル未選択", font=("BIZ UDGothic",10), text_color=C["SUB"])
        self.queue_empty_label.pack(pady=8)

        self.file_label=ctk.CTkLabel(left, text="プレビュー: ファイルを選択してください", font=("BIZ UDGothic",10), text_color=C["SUB"], wraplength=500)
        self.file_label.pack(pady=(4,2), padx=14)

        ctk.CTkLabel(left, text="内容プレビュー", font=("BIZ UDGothic",11,"bold"), text_color=C["TEXT"]).pack(anchor="w", padx=14, pady=(4,2))
        # 検索バー（おまかせ実装）
        search_frame=ctk.CTkFrame(left, fg_color="transparent"); search_frame.pack(fill="x", padx=14, pady=(2,4))
        self.search_entry=ctk.CTkEntry(search_frame, placeholder_text="🔍 アーカイブ内を検索... (ファイル名)", font=("BIZ UDGothic",10), height=28, border_color=C["BORDER"])
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0,6))
        self.search_entry.bind("<KeyRelease>", self.on_search)
        self.search_entry.bind("<Escape>", lambda e: self.clear_search())
        ctk.CTkButton(search_frame, text="✕", width=28, height=28, fg_color="white", text_color=C["TEXT"], hover_color=C["HOVER"], border_width=1, border_color=C["BORDER"], font=("BIZ UDGothic",10), command=self.clear_search).pack(side="right")
        self.search_info=ctk.CTkLabel(left, text="", font=("BIZ UDGothic",9), text_color=C["SUB"], anchor="w")
        self.search_info.pack(fill="x", padx=14, pady=(0,2))
        tree_frame=ctk.CTkFrame(left, fg_color="transparent"); tree_frame.pack(fill="both", expand=True, padx=10, pady=(0,6))
        style=ttk.Style(self); style.theme_use("clam")
        bg = C["CARD"] if CONFIG.get("theme")=="light" else "#1e293b"
        fg = C["TEXT"]; hbg = C["HOVER"]
        style.configure("Treeview", rowheight=22, font=("BIZ UDGothic",9), background=bg, fieldbackground=bg, foreground=fg, bordercolor=C["BORDER"])
        style.configure("Treeview.Heading", font=("BIZ UDGothic",9,"bold"), background=hbg, foreground=fg)
        style.map("Treeview", background=[("selected","#3b82f6")], foreground=[("selected","white")])
        self.tree=ttk.Treeview(tree_frame, columns=("size","type"), show="tree headings", height=7)
        self.tree.heading("#0", text="ファイル名"); self.tree.heading("size", text="サイズ"); self.tree.heading("type", text="種別")
        self.tree.column("#0", width=340); self.tree.column("size", width=90, anchor="e"); self.tree.column("type", width=70, anchor="center")
        self.tree.pack(side="left", fill="both", expand=True)
        sb=ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview); self.tree.configure(yscrollcommand=sb.set); sb.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        # プレビュー（画像サムネイル + テキスト）
        self.preview_frame=ctk.CTkFrame(left, fg_color=C["HOVER"], corner_radius=8, height=110)
        self.preview_frame.pack(fill="x", padx=10, pady=4); self.preview_frame.pack_propagate(False)
        preview_left=ctk.CTkFrame(self.preview_frame, fg_color="transparent"); preview_left.pack(side="left", fill="y", padx=8, pady=8)
        self.preview_img_label=ctk.CTkLabel(preview_left, text="🖼️", font=("BIZ UDGothic",28), width=80, height=80, fg_color=C["CARD"], corner_radius=6)
        self.preview_img_label.pack(pady=2)
        preview_right=ctk.CTkFrame(self.preview_frame, fg_color="transparent"); preview_right.pack(side="left", fill="both", expand=True, padx=4, pady=4)
        self.preview_info_label=ctk.CTkLabel(preview_right, text="ファイルを選択するとプレビューが表示されます\n画像はサムネイル、テキストは先頭を表示", font=("BIZ UDGothic",9), text_color=C["SUB"], justify="left", anchor="w")
        self.preview_info_label.pack(fill="x", anchor="w")
        self.preview_text_box=ctk.CTkTextbox(preview_right, height=60, font=("Consolas",8), fg_color=C["CARD"], text_color=C["TEXT"], border_width=1, border_color=C["BORDER"], wrap="word", cursor="arrow")
        self.preview_text_box.pack(fill="both", expand=True, pady=(4,0)); self.preview_text_box.configure(state="disabled")
        self._preview_img_ref=None  # GC対策

        prog_frame=ctk.CTkFrame(left, fg_color="transparent"); prog_frame.pack(fill="x", padx=14, pady=2)
        self.progress=ctk.CTkProgressBar(prog_frame, height=10, progress_color=COLOR_PRIMARY, fg_color=C["HOVER"])
        self.progress.pack(side="left", fill="x", expand=True, padx=(0,8)); self.progress.set(0)
        self.btn_cancel=ctk.CTkButton(prog_frame, text="✕", width=28, height=22, fg_color="#fee2e2", text_color="#dc2626", hover_color="#fecaca", command=self.cancel_extract, state="disabled")
        self.btn_cancel.pack(side="right")
        # 統合進捗バー（進捗% + ETA）
        self.progress_detail=ctk.CTkLabel(left, text="", font=("BIZ UDGothic",9), text_color=C["SUB"], anchor="w")
        self.progress_detail.pack(fill="x", padx=14, pady=(0,1))

        # 統合ステータスバー（アイドル/実行中/完了/エラーを1行で表示）
        self.status_label=ctk.CTkLabel(left, text="⚪ 待機中", font=("BIZ UDGothic",10,"bold"), text_color=C["TEXT"], anchor="w")
        self.status_label.pack(fill="x", padx=14, pady=(0,2))
        # ログBox（コピー可能に: wrap="word" + "arrow"カーソル）
        self.log_box=ctk.CTkTextbox(left, height=70, font=("Consolas",9), fg_color=C["LOG_BG"], text_color=C["TEXT"], border_width=1, border_color=C["BORDER"], wrap="word", cursor="arrow")
        self.log_box.pack(fill="x", padx=14, pady=(0,10)); self.log_box.configure(state="disabled")

        # 右ペイン設定（解凍）
        ctk.CTkLabel(right_pane, text="展開設定", font=("BIZ UDGothic",13,"bold"), text_color=C["TEXT"]).pack(pady=(14,8))
        ctk.CTkLabel(right_pane, text="出力先", font=("BIZ UDGothic",11,"bold"), text_color=C["TEXT"]).pack(anchor="w", padx=14, pady=(2,2))
        self.rb_same=ctk.CTkRadioButton(right_pane, text="同じフォルダ", variable=self.dest_mode, value="same", font=("BIZ UDGothic",11), text_color=C["TEXT"], fg_color=COLOR_PRIMARY, command=self.on_dest_change)
        self.rb_same.pack(anchor="w", padx=14, pady=2)
        self.rb_desktop=ctk.CTkRadioButton(right_pane, text="デスクトップ", variable=self.dest_mode, value="desktop", font=("BIZ UDGothic",11), text_color=C["TEXT"], fg_color=COLOR_PRIMARY, command=self.on_dest_change)
        self.rb_desktop.pack(anchor="w", padx=14, pady=2)
        self.rb_custom=ctk.CTkRadioButton(right_pane, text="指定フォルダ", variable=self.dest_mode, value="custom", font=("BIZ UDGothic",11), text_color=C["TEXT"], fg_color=COLOR_PRIMARY, command=self.on_dest_change)
        self.rb_custom.pack(anchor="w", padx=14, pady=2)
        self.dest_path_label=ctk.CTkLabel(right_pane, text="", font=("BIZ UDGothic",9), text_color=C["SUB"], wraplength=280, anchor="w", justify="left")
        self.dest_path_label.pack(fill="x", padx=14, pady=(2,4))
        self.btn_choose_dest=ctk.CTkButton(right_pane, text="フォルダを選択", height=28, fg_color="white", text_color=C["TEXT"], hover_color=C["HOVER"], border_width=1, border_color=C["BORDER"], command=self.pick_dest)
        self.btn_choose_dest.pack(fill="x", padx=14, pady=(0,6))

        ctk.CTkLabel(right_pane, text="パスワード", font=("BIZ UDGothic",11,"bold"), text_color=C["TEXT"]).pack(anchor="w", padx=14, pady=(6,2))
        pw_frame=ctk.CTkFrame(right_pane, fg_color="transparent"); pw_frame.pack(fill="x", padx=14, pady=2)
        self.entry_pw=ctk.CTkEntry(pw_frame, placeholder_text="暗号化ZIP/7Z用", show="*", font=("BIZ UDGothic",11), height=32, border_color=C["BORDER"])
        self.entry_pw.pack(side="left", fill="x", expand=True, padx=(0,6))
        self.btn_eye=ctk.CTkButton(pw_frame, text="👁", width=32, height=32, fg_color="white", text_color=C["TEXT"], hover_color=C["HOVER"], border_width=1, border_color=C["BORDER"], command=self.toggle_pw)
        self.btn_eye.pack(side="right")

        self.var_open_folder=ctk.BooleanVar(value=CONFIG.get("open_folder", True))
        self.var_delete=ctk.BooleanVar(value=CONFIG.get("delete_after", False))
        self.var_notify=ctk.BooleanVar(value=CONFIG.get("notifications", True))
        ctk.CTkCheckBox(right_pane, text="展開後にフォルダを開く", variable=self.var_open_folder, font=("BIZ UDGothic",10), text_color=C["TEXT"], fg_color=COLOR_PRIMARY, command=self.save_settings).pack(anchor="w", padx=14, pady=(8,2))
        ctk.CTkCheckBox(right_pane, text="展開後にアーカイブを削除", variable=self.var_delete, font=("BIZ UDGothic",10), text_color=COLOR_DANGER, fg_color=COLOR_DANGER, command=self.save_settings).pack(anchor="w", padx=14, pady=2)
        ctk.CTkCheckBox(right_pane, text="完了時に通知を表示", variable=self.var_notify, font=("BIZ UDGothic",10), text_color=C["TEXT"], fg_color=COLOR_PRIMARY, command=self.save_settings).pack(anchor="w", padx=14, pady=2)
        self.var_organize=ctk.BooleanVar(value=CONFIG.get("organize", False))
        ctk.CTkCheckBox(right_pane, text="✨ おまかせ整理（種類別にフォルダ分け）", variable=self.var_organize, font=("BIZ UDGothic",10), text_color=C["TEXT"], fg_color="#f59e0b", hover_color="#d97706", command=self.save_settings).pack(anchor="w", padx=14, pady=2)

        ctk.CTkLabel(right_pane, text="同名ファイル", font=("BIZ UDGothic",10,"bold"), text_color=C["TEXT"]).pack(anchor="w", padx=14, pady=(8,2))
        self.overwrite_var=ctk.StringVar(value=CONFIG.get("overwrite_mode","smart"))
        ctk.CTkRadioButton(right_pane, text="確認する（推奨）", variable=self.overwrite_var, value="smart", font=("BIZ UDGothic",10), text_color=C["TEXT"], fg_color=COLOR_PRIMARY, command=self.save_settings).pack(anchor="w", padx=14, pady=1)
        ctk.CTkRadioButton(right_pane, text="常に上書き", variable=self.overwrite_var, value="overwrite", font=("BIZ UDGothic",10), text_color=C["TEXT"], fg_color=COLOR_PRIMARY, command=self.save_settings).pack(anchor="w", padx=14, pady=1)
        ctk.CTkRadioButton(right_pane, text="スキップ", variable=self.overwrite_var, value="skip", font=("BIZ UDGothic",10), text_color=C["TEXT"], fg_color=COLOR_PRIMARY, command=self.save_settings).pack(anchor="w", padx=14, pady=1)

        self.btn_extract=ctk.CTkButton(right_pane, text="解凍する ▶", height=46, font=("BIZ UDGothic",13,"bold"), fg_color=COLOR_PRIMARY, hover_color=COLOR_PRIMARY_HOVER, corner_radius=10, state="disabled", command=self.start_extract)
        self.btn_extract.pack(fill="x", padx=14, pady=(10,6))
        ctk.CTkLabel(right_pane, text="対応: .zip .7z .tar .gz .rar など", font=("BIZ UDGothic",9), text_color=C["SUB"]).pack(padx=14, pady=(0,4))

        hist_header=ctk.CTkFrame(right_pane, fg_color="transparent"); hist_header.pack(fill="x", padx=14, pady=(6,2))
        ctk.CTkLabel(hist_header, text="履歴", font=("BIZ UDGothic",11,"bold"), text_color=C["TEXT"]).pack(side="left")
        ctk.CTkButton(hist_header, text="クリア", width=50, height=20, fg_color="white", text_color=C["TEXT"], hover_color=C["HOVER"], border_width=1, border_color=C["BORDER"], font=("BIZ UDGothic",9), command=self.clear_history).pack(side="right")
        self.history_frame=ctk.CTkScrollableFrame(right_pane, fg_color=C["HOVER"], height=110, corner_radius=8)
        self.history_frame.pack(fill="both", expand=True, padx=10, pady=4)

        # === 圧縮タブ（遅延ロード） ===
        tab_compress = self.tabview.tab("🗜️ 圧縮")
        self._compress_tab = tab_compress
        self._compress_built = False
        ctk.CTkLabel(tab_compress, text="読み込み中...", font=("BIZ UDGothic",11), text_color=C["SUB"]).pack(pady=40)

        footer=ctk.CTkFrame(self, fg_color="transparent", height=20); footer.pack(fill="x", padx=12, pady=(0,6))
        ctk.CTkLabel(footer, text="© SimpleExtract  •  ドラッグ＆ドロップで簡単解凍・圧縮  •  設定は自動保存", font=("BIZ UDGothic",9), text_color=C["SUB"]).pack(side="left")
        ctk.CTkLabel(footer, text="Win11/10 対応", font=("BIZ UDGothic",9), text_color=C["SUB"]).pack(side="right")
        self.dest_mode.trace_add("write", lambda *_: self.update_dest_label())

    def _build_compress_tab(self):
        if getattr(self, '_compress_built', False):
            return
        self._compress_built = True
        tab_compress = self._compress_tab
        # Clear placeholder
        for w in tab_compress.winfo_children():
            w.destroy()
        C=current_colors()
        c_main=ctk.CTkFrame(tab_compress, fg_color="transparent"); c_main.pack(fill="both", expand=True, padx=6, pady=6)
        c_left=ctk.CTkFrame(c_main, fg_color=C["CARD"], corner_radius=12, border_width=1, border_color=C["BORDER"])
        c_left.pack(side="left", fill="both", expand=True, padx=(0,6))
        c_right=ctk.CTkFrame(c_main, fg_color=C["CARD"], corner_radius=12, border_width=1, border_color=C["BORDER"], width=320)
        c_right.pack(side="right", fill="y", padx=(6,0)); c_right.pack_propagate(False)

        ctk.CTkLabel(c_left, text="圧縮するファイル/フォルダをドロップ", font=("BIZ UDGothic",13,"bold"), text_color=C["TEXT"]).pack(pady=(14,4))
        self.c_drop_frame=ctk.CTkFrame(c_left, fg_color=C["DROP_BG"], corner_radius=12, border_width=2, border_color=C["DROP_BORDER"])
        self.c_drop_frame.pack(fill="x", padx=14, pady=4)
        c_inner=ctk.CTkFrame(self.c_drop_frame, fg_color="transparent"); c_inner.pack(padx=14, pady=14, fill="x")
        ctk.CTkLabel(c_inner, text="📁", font=("BIZ UDGothic",28)).pack()
        ctk.CTkLabel(c_inner, text="ここにファイルやフォルダをドラッグ＆ドロップ\n（複数OK）", font=("BIZ UDGothic",11), text_color=C["TEXT"], justify="center").pack(pady=(4,8))
        c_btn_row=ctk.CTkFrame(c_inner, fg_color="transparent"); c_btn_row.pack()
        ctk.CTkButton(c_btn_row, text="ファイルを追加...", fg_color=COLOR_PRIMARY, hover_color=COLOR_PRIMARY_HOVER, corner_radius=8, font=("BIZ UDGothic",11,"bold"), height=34, command=self.pick_compress_files).pack(side="left", padx=4)
        ctk.CTkButton(c_btn_row, text="フォルダを追加...", fg_color="white", text_color=C["TEXT"], hover_color=C["HOVER"], border_width=1, border_color=C["BORDER"], height=34, command=self.pick_compress_folder).pack(side="left", padx=4)

        c_queue_header=ctk.CTkFrame(c_left, fg_color="transparent"); c_queue_header.pack(fill="x", padx=14, pady=(8,2))
        ctk.CTkLabel(c_queue_header, text="圧縮リスト", font=("BIZ UDGothic",11,"bold"), text_color=C["TEXT"]).pack(side="left")
        self.c_queue_label=ctk.CTkLabel(c_queue_header, text="0件", font=("BIZ UDGothic",10), text_color=C["SUB"]); self.c_queue_label.pack(side="left", padx=8)
        ctk.CTkButton(c_queue_header, text="クリア", width=60, height=22, fg_color="white", text_color=C["TEXT"], hover_color=C["HOVER"], border_width=1, border_color=C["BORDER"], font=("BIZ UDGothic",9), command=self.clear_compress_queue).pack(side="right")
        self.c_queue_frame=ctk.CTkScrollableFrame(c_left, fg_color=C["HOVER"], height=120, corner_radius=8)
        self.c_queue_frame.pack(fill="x", padx=14, pady=2)
        self.c_status_label=ctk.CTkLabel(c_left, text="⚪ 待機中", font=("BIZ UDGothic",10,"bold"), text_color=C["TEXT"], anchor="w")
        self.c_status_label.pack(fill="x", padx=14, pady=(4,2))
        self.c_progress=ctk.CTkProgressBar(c_left, height=10, progress_color=COLOR_PRIMARY, fg_color=C["HOVER"])
        self.c_progress.pack(fill="x", padx=14, pady=2); self.c_progress.set(0)
        self.c_progress_detail=ctk.CTkLabel(c_left, text="", font=("BIZ UDGothic",9), text_color=C["SUB"], anchor="w")
        self.c_progress_detail.pack(fill="x", padx=14, pady=(0,2))
        self.c_log_box=ctk.CTkTextbox(c_left, height=90, font=("Consolas",9), fg_color=C["LOG_BG"], text_color=C["TEXT"], border_width=1, border_color=C["BORDER"], wrap="word", cursor="arrow")
        self.c_log_box.pack(fill="x", padx=14, pady=(4,10)); self.c_log_box.configure(state="disabled")

        # 圧縮設定 右ペイン
        ctk.CTkLabel(c_right, text="圧縮設定", font=("BIZ UDGothic",13,"bold"), text_color=C["TEXT"]).pack(pady=(14,8))
        ctk.CTkLabel(c_right, text="形式", font=("BIZ UDGothic",11,"bold"), text_color=C["TEXT"]).pack(anchor="w", padx=14, pady=(2,2))
        self.c_fmt_var=ctk.StringVar(value="zip")
        for fmt in [("ZIP  (.zip)", "zip"), ("7Z  (.7z)  高圧縮", "7z"), ("TAR.GZ  (.tar.gz)", "tar.gz")]:
            ctk.CTkRadioButton(c_right, text=fmt[0], variable=self.c_fmt_var, value=fmt[1], font=("BIZ UDGothic",10), text_color=C["TEXT"], fg_color=COLOR_PRIMARY).pack(anchor="w", padx=14, pady=2)
        ctk.CTkLabel(c_right, text="圧縮レベル", font=("BIZ UDGothic",11,"bold"), text_color=C["TEXT"]).pack(anchor="w", padx=14, pady=(8,2))
        self.c_level_var=ctk.IntVar(value=5)
        self.c_level_slider=ctk.CTkSlider(c_right, from_=1, to=9, number_of_steps=8, variable=self.c_level_var, progress_color=COLOR_PRIMARY, button_color=COLOR_PRIMARY, button_hover_color=COLOR_PRIMARY_HOVER)
        self.c_level_slider.pack(fill="x", padx=14, pady=4)
        lvl_row=ctk.CTkFrame(c_right, fg_color="transparent"); lvl_row.pack(fill="x", padx=14)
        ctk.CTkLabel(lvl_row, text="高速", font=("BIZ UDGothic",9), text_color=C["SUB"]).pack(side="left")
        self.c_level_label=ctk.CTkLabel(lvl_row, text="5 / 9", font=("BIZ UDGothic",9,"bold"), text_color=C["TEXT"]); self.c_level_label.pack(side="left", expand=True)
        ctk.CTkLabel(lvl_row, text="最高圧縮", font=("BIZ UDGothic",9), text_color=C["SUB"]).pack(side="right")
        self.c_level_var.trace_add("write", lambda *_: self.c_level_label.configure(text=f"{self.c_level_var.get()} / 9"))

        ctk.CTkLabel(c_right, text="パスワード（7Zのみ）", font=("BIZ UDGothic",11,"bold"), text_color=C["TEXT"]).pack(anchor="w", padx=14, pady=(8,2))
        self.c_pw_entry=ctk.CTkEntry(c_right, placeholder_text="任意", show="*", font=("BIZ UDGothic",11), height=32, border_color=C["BORDER"])
        self.c_pw_entry.pack(fill="x", padx=14, pady=2)

        ctk.CTkLabel(c_right, text="出力先", font=("BIZ UDGothic",11,"bold"), text_color=C["TEXT"]).pack(anchor="w", padx=14, pady=(8,2))
        self.c_output_var=ctk.StringVar(value=os.path.join(os.path.expanduser("~"), "Desktop", "archive.zip"))
        ctk.CTkEntry(c_right, textvariable=self.c_output_var, font=("BIZ UDGothic",10), height=28, border_color=C["BORDER"]).pack(fill="x", padx=14, pady=2)
        ctk.CTkButton(c_right, text="出力先を選択...", height=28, fg_color="white", text_color=C["TEXT"], hover_color=C["HOVER"], border_width=1, border_color=C["BORDER"], command=self.pick_compress_output).pack(fill="x", padx=14, pady=4)

        self.c_btn_compress=ctk.CTkButton(c_right, text="圧縮する ▶", height=46, font=("BIZ UDGothic",13,"bold"), fg_color=COLOR_SUCCESS, hover_color="#15803d", corner_radius=10, state="disabled", command=self.start_compress)
        self.c_btn_compress.pack(fill="x", padx=14, pady=(12,6))
        ctk.CTkLabel(c_right, text="フォルダは再帰的に追加されます", font=("BIZ UDGothic",9), text_color=C["SUB"]).pack(padx=14)


        self.update_dest_label()


    def _apply_theme(self):
        pass
    def _init_taskbar(self):
        try:
            hwnd = self.winfo_id()  # TkのHWND
            # より確実なHWND取得
            try:
                hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
                if hwnd == 0:
                    hwnd = self.winfo_id()
            except Exception: pass
            self.taskbar = TaskbarProgress(hwnd)
        except Exception: self.taskbar = None
    def _set_indicator(self, state, text="", sub=""):
        # state: idle/running/done/error
        try:
            if state == "running":
                self.indicator_dot.pulse(True)
            else:
                self.indicator_dot.pulse(False)
                self.indicator_dot.draw(state)
            self.indicator_label.configure(text=text or {"idle":"待機中","running":"処理中","done":"完了","error":"エラー"}.get(state, text))
            self.indicator_sub.configure(text=sub)
            # タスクバー連動
            if self.taskbar:
                if state=="running":
                    self.taskbar.set_state(TaskbarProgress.TBPF_NORMAL)
                elif state=="done":
                    self.taskbar.set_state(TaskbarProgress.TBPF_NOPROGRESS)
                    self.taskbar.set_progress(100,100)
                    self.after(1000, lambda: self.taskbar.clear() if self.taskbar else None)
                elif state=="error":
                    self.taskbar.set_state(TaskbarProgress.TBPF_ERROR)
                elif state=="idle":
                    self.taskbar.clear()
        except Exception: pass
    def _update_taskbar_progress(self, value, total=100):
        try:
            if self.taskbar:
                self.taskbar.set_progress(value, total)
        except Exception: pass

    def toggle_theme(self):
        new = "dark" if CONFIG.get("theme")=="light" else "light"
        CONFIG.set("theme", new)
        ctk.set_appearance_mode(new)
        # 簡易: 再起動を促すトースト
        self.show_toast(f"テーマを {new} に変更 — 再起動で完全反映")
        self.btn_theme.configure(text="🌙" if new=="light" else "☀️")

    def save_settings(self):
        with CONFIG.batch():
            CONFIG.set("dest_mode", self.dest_mode.get())
            CONFIG.set("custom_dest", self.custom_dest)
            CONFIG.set("open_folder", bool(self.var_open_folder.get()))
            CONFIG.set("delete_after", bool(self.var_delete.get()))
            CONFIG.set("notifications", bool(self.var_notify.get()))
            CONFIG.set("organize", bool(self.var_organize.get()))
            CONFIG.set("overwrite_mode", self.overwrite_var.get())

    def on_dest_change(self):
        self.save_settings(); self.update_dest_label()

    def _bind_dnd(self):
        try: self.drop_target_register(DND_FILES)
        except Exception:
            try: self.drop_register(DND_FILES)
            except Exception: pass
        self.dnd_bind('<<Drop>>', self.on_drop)
        # 圧縮タブのドロップも同じハンドラで処理（タブで分岐）
        try:
            self.c_drop_frame.drop_target_register(DND_FILES)
            self.c_drop_frame.dnd_bind('<<Drop>>', self.on_compress_drop)
        except Exception: pass

    def log(self, msg):
        self.log_box.configure(state="normal")
        ts=datetime.now().strftime("%H:%M:%S")
        self.log_box.insert("end", f"[{ts}] {msg}\n"); self.log_box.see("end"); self.log_box.configure(state="disabled")

    def set_status(self, msg): self.status_label.configure(text=msg)

    def show_toast(self, msg, color=COLOR_SUCCESS):
        # 右下に一時的なトースト
        try:
            toast=ctk.CTkFrame(self, fg_color=color, corner_radius=8)
            toast.place(relx=1.0, rely=1.0, anchor="se", x=-20, y=-40)
            ctk.CTkLabel(toast, text=msg, font=("BIZ UDGothic",11,"bold"), text_color="white").pack(padx=14, pady=8)
            self.after(2500, toast.destroy)
            # システム音
            try: ctypes.windll.user32.MessageBeep(0x00000040)
            except Exception: pass
        except Exception: pass

    def _update_queue_badge(self):
        total = len(self.queue_files) + len(self.compress_files)
        if total>0:
            self.queue_badge.configure(text=f"{total}件")
            self.queue_badge.pack(side="left", padx=(12,0))
        else:
            self.queue_badge.pack_forget()
    # ── キュー管理 ──
    def _refresh_queue_ui(self):
        for w in self.queue_frame.winfo_children(): w.destroy()
        if not self.queue_files:
            ctk.CTkLabel(self.queue_frame, text="ファイル未選択", font=("BIZ UDGothic",10), text_color=current_colors()["SUB"]).pack(pady=8)
            self.queue_label.configure(text="0件")
            self._update_queue_badge()
            return
        self.queue_label.configure(text=f"{len(self.queue_files)}件")
        self._update_queue_badge()
        for idx, p in enumerate(self.queue_files):
            row=ctk.CTkFrame(self.queue_frame, fg_color=current_colors()["CARD"], corner_radius=6)
            row.pack(fill="x", padx=4, pady=2)
            is_cur = (p==self.archive_path)
            bg = "#dbeafe" if is_cur else current_colors()["CARD"]
            row.configure(fg_color=bg)
            ctk.CTkLabel(row, text=f"{idx+1}. {os.path.basename(p)}", font=("BIZ UDGothic",10, "bold" if is_cur else "normal"), text_color=current_colors()["TEXT"], width=200, anchor="w").pack(side="left", padx=8, pady=4)
            ctk.CTkLabel(row, text=human_size(os.path.getsize(p)) if os.path.exists(p) else "-", font=("BIZ UDGothic",9), text_color=current_colors()["SUB"]).pack(side="left")
            ctk.CTkButton(row, text="✕", width=24, height=20, fg_color="#fee2e2", text_color="#dc2626", hover_color="#fecaca", command=lambda i=idx: self.remove_from_queue(i)).pack(side="right", padx=6)
            # クリックで選択
            row.bind("<Button-1>", lambda e, path=p: self.load_archive(path))
            for child in row.winfo_children(): child.bind("<Button-1>", lambda e, path=p: self.load_archive(path))

    def add_to_queue(self, paths):
        added=0
        for p in paths:
            if p not in self.queue_files and os.path.isfile(p) and is_supported(p):
                self.queue_files.append(p); added+=1
        if added: self._refresh_queue_ui()
        # 最新を追加したらそれをプレビュー
        if self.queue_files and not self.archive_path:
            self.load_archive(self.queue_files[-1])

    def remove_from_queue(self, idx):
        if 0<=idx<len(self.queue_files):
            removed=self.queue_files.pop(idx)
            if removed==self.archive_path:
                self.archive_path=self.queue_files[0] if self.queue_files else None
                if self.archive_path: self.load_archive(self.archive_path)
                else:
                    self.tree.delete(*self.tree.get_children()); self.file_label.configure(text="プレビュー: ファイルを選択してください"); self.btn_extract.configure(state="disabled")
            self._refresh_queue_ui()

    def clear_queue(self):
        self.queue_files=[]; self.archive_path=None
        self.tree.delete(*self.tree.get_children()); self.file_label.configure(text="プレビュー: ファイルを選択してください")
        self.btn_extract.configure(state="disabled"); self._refresh_queue_ui(); self.set_status("キューをクリアしました")

    # ── ファイル選択 ──
    def pick_files(self):
        paths=filedialog.askopenfilenames(title="アーカイブを選択（複数可）", filetypes=[("アーカイブ","*.zip *.7z *.tar *.tar.gz *.tgz *.gz *.bz2 *.rar"),("すべてのファイル","*.*")])
        if paths: self.add_to_queue(list(paths)); self.load_archive(paths[0])
    def pick_folder(self):
        d=filedialog.askdirectory(title="フォルダ内のアーカイブを一括追加")
        if d:
            files=[os.path.join(d,f) for f in os.listdir(d) if is_supported(os.path.join(d,f))]
            if files: self.add_to_queue(files); self.load_archive(files[0])
            else: messagebox.showinfo("情報","フォルダ内にアーカイブが見つかりません")
    def pick_dest(self):
        d=filedialog.askdirectory(title="展開先フォルダを選択")
        if d: self.custom_dest=d; self.dest_mode.set("custom"); self.update_dest_label(); self.save_settings(); self.log(f"出力先: {d}")
    def update_dest_label(self):
        m=self.dest_mode.get()
        if m=="same": self.dest_path_label.configure(text="→ アーカイブと同じフォルダ")
        elif m=="desktop": self.dest_path_label.configure(text=f"→ {os.path.join(os.path.expanduser('~'),'Desktop')}")
        else: self.dest_path_label.configure(text=f"→ {self.custom_dest or '未選択'}")
    def toggle_pw(self):
        self.password_visible=not self.password_visible
        self.entry_pw.configure(show="" if self.password_visible else "*")
        self.btn_eye.configure(text="🙈" if self.password_visible else "👁")
    def on_drop(self, event):
        data=self.tk.splitlist(event.data)
        if not data: return
        files=[p for p in data if os.path.isfile(p) and is_supported(p)]
        dirs=[p for p in data if os.path.isdir(p)]
        for d in dirs:
            files.extend([os.path.join(d,f) for f in os.listdir(d) if is_supported(os.path.join(d,f))])
        if not files:
            if data and os.path.isdir(data[0]): messagebox.showwarning("注意","フォルダ内のアーカイブを自動検出しましたが、見つかりませんでした")
            else: messagebox.showwarning("未対応", f"対応していない形式です:\n{data[0] if data else ''}")
            return
        self.add_to_queue(files); self.load_archive(files[0])

    def load_archive(self, path):
        # UI準備待ち（関連付け起動でprogress未生成の場合）
        if not hasattr(self, 'progress') or not hasattr(self, 'tree'):
            self.after(200, lambda: self.load_archive(path))
            return
        self.archive_path=path
        # キューにも追加（関連付け起動用）
        if path not in self.queue_files:
            self.queue_files.append(path)
            self._refresh_queue_ui()
            self._update_queue_badge()
        fname=os.path.basename(path)
        try: fsize=os.path.getsize(path)
        except Exception: fsize=0
        self.file_label.configure(text=f"📄 {fname}  ({human_size(fsize)})  —  {len(self.queue_files)}件中 {self.queue_files.index(path)+1 if path in self.queue_files else 1}件目", text_color=current_colors()["TEXT"])
        self.log(f"読み込み: {path}"); self.set_status("解析中...");
        try: self.progress.set(0.1)
        except Exception: pass
        self.tree.delete(*self.tree.get_children()); self._refresh_queue_ui()
        pw=self.entry_pw.get().strip() or None
        def worker():
            items,err=Extractor.list_contents(path,pw)
            self.after(0, lambda: self.on_list_done(items,err))
        threading.Thread(target=worker,daemon=True).start()
        # 履歴ではないが、キュー強調を更新
        self.after(300, self._refresh_queue_ui)

    def on_list_done(self, items, err):
        self.progress.set(0)
        if err:
            self.set_status(f"プレビューエラー: {err}"); self.log(f"プレビューエラー: {err} - ただし解凍は試せます")
            if "パスワード" in err:
                messagebox.showinfo("パスワード","パスワード保護されています。右側に入力して再読み込みしてください。")
            else:
                # プレビュー失敗でも解凍は試せるようにボタンを有効化
                self.log("プレビューに失敗しましたが、解凍ボタンは有効のままにします")
            # ファイル自体は有効なのでボタンは有効化（押せない問題の修正）
            if self.archive_path and os.path.exists(self.archive_path) and is_supported(self.archive_path):
                self.btn_extract.configure(state="normal", fg_color=COLOR_PRIMARY)
                self._set_indicator("idle", "プレビュー失敗", "解凍は可能")
                # ツリーにエラーメッセージを表示
                self.tree.insert("", "end", text=f"⚠️ プレビュー取得失敗: {err}", values=("-", "-"))
                self.tree.insert("", "end", text="→ 解凍ボタンで直接解凍を試してください", values=("-", "-"))
                return
            self.btn_extract.configure(state="disabled"); return
        if not items: self.set_status("ファイルなし"); self.btn_extract.configure(state="disabled"); return
        # 保存してプレビューで使う
        self.current_items = items
        total_size = sum(s for _,s,is_dir,_,enc in items if not is_dir)
        enc_count = sum(1 for _,_,_,_,enc in items if enc)
        # Treeに投入
        for name,size,is_dir,dt,enc in items[:500]:
            if is_dir: icon="📁"
            elif enc: icon="🔒"
            else: icon="📄"
            typ="フォルダ" if is_dir else ("暗号化" if enc else "ファイル")
            sz="-" if is_dir else human_size(size)
            tag = "enc" if enc else ""
            self.tree.insert("", "end", text=f"{icon} {name}", values=(sz, typ), tags=(tag,))
        # 暗号化行を色付け
        try: self.tree.tag_configure("enc", foreground="#dc2626")
        except Exception: pass
        if len(items)>500: self.tree.insert("", "end", text=f"... 他 {len(items)-500} 件", values=("-", "-"))
        summary=f"{len(items)}項目  •  合計 {human_size(total_size)}"
        if enc_count: summary+=f"  •  🔒 {enc_count}件暗号化"
        # 大容量警告表示
        if total_size > 2*1024*1024*1024:
            summary += "  ⚠️ 大容量"
            self.summary_label.configure(text=summary, text_color="#dc2626")
        elif total_size > 500*1024*1024:
            self.summary_label.configure(text=summary, text_color="#d97706")
        else:
            self.summary_label.configure(text=summary, text_color=current_colors()["SUB"])
        self.set_status(f"{len(items)}項目  |  解凍準備完了")
        self.log(f"{len(items)}件を検出 (合計{human_size(total_size)})")
        self.btn_extract.configure(state="normal", fg_color=COLOR_PRIMARY)
        # プレビュー初期化
        self.preview_info_label.configure(text=f"{len(items)}件  •  合計{human_size(total_size)}\nファイルを選択するとプレビュー")
        self.preview_text_box.configure(state="normal"); self.preview_text_box.delete("1.0","end"); self.preview_text_box.insert("end", "画像はサムネイル、テキストは先頭1KBを表示\n🔒はパスワードが必要"); self.preview_text_box.configure(state="disabled")
        # 自動解凍モード
        if CONFIG.get("auto_extract") and len(sys.argv)>1:
            self.after(600, self.start_extract)

    def on_tree_select(self, event):
        sel=self.tree.selection()
        if not sel or not hasattr(self,'current_items'): return
        idx=self.tree.index(sel[0])
        if idx>=len(self.current_items): return
        name,size,is_dir,dt,enc = self.current_items[idx]
        if is_dir:
            self.preview_info_label.configure(text=f"📁 {name}\nフォルダ")
            self.preview_text_box.configure(state="normal"); self.preview_text_box.delete("1.0","end"); self.preview_text_box.insert("end", "フォルダはプレビューできません"); self.preview_text_box.configure(state="disabled")
            self.preview_img_label.configure(text="📁", image="")
            return
        # 暗号化はパスワード無しではプレビュー不可
        if enc and not self.entry_pw.get().strip():
            self.preview_info_label.configure(text=f"🔒 {name}\n{human_size(size)} • 暗号化")
            self.preview_text_box.configure(state="normal"); self.preview_text_box.delete("1.0","end"); self.preview_text_box.insert("end", "🔒 暗号化されています。\n右側にパスワードを入力して再読み込みしてください。"); self.preview_text_box.configure(state="disabled")
            return
        self.preview_info_label.configure(text=f"{name}\n{human_size(size)} {'• 🔒' if enc else ''}")
        # プレビュー取得（非同期）
        def worker():
            data,err=Extractor.preview_file(self.archive_path, name, self.entry_pw.get().strip() or None)
            self.after(0, lambda: self._show_preview(data, err, name))
        threading.Thread(target=worker, daemon=True).start()

    def _show_preview(self, data, err, name):
        if err:
            self.preview_text_box.configure(state="normal"); self.preview_text_box.delete("1.0","end"); self.preview_text_box.insert("end", f"プレビュー失敗: {err}"); self.preview_text_box.configure(state="disabled")
            return
        if not data:
            self.preview_text_box.configure(state="normal"); self.preview_text_box.delete("1.0","end"); self.preview_text_box.insert("end", "空ファイル"); self.preview_text_box.configure(state="disabled")
            return
        lower=name.lower()
        is_image = any(lower.endswith(ext) for ext in [".png",".jpg",".jpeg",".gif",".bmp",".webp",".tiff"])
        is_text = any(lower.endswith(ext) for ext in [".txt",".md",".json",".xml",".csv",".log",".py",".js",".html",".css",".ini",".yaml",".yml",".toml",".cfg"])
        if is_image and HAS_PIL:
            try:
                from io import BytesIO
                from PIL import Image as _PILImage; Image = _PILImage
                im=Image.open(BytesIO(data))
                im.thumbnail((80,80), Image.LANCZOS)
                tkimg=ImageTk.PhotoImage(im)
                self.preview_img_label.configure(text="", image=tkimg)
                self._preview_img_ref=tkimg
                self.preview_text_box.configure(state="normal"); self.preview_text_box.delete("1.0","end"); self.preview_text_box.insert("end", f"🖼️ 画像プレビュー\n{im.size[0]}x{im.size[1]}  {im.format}"); self.preview_text_box.configure(state="disabled")
                return
            except Exception as e:
                pass
        if is_text or not is_image:
            # テキストとして試す
            try:
                text=data[:2048].decode('utf-8', errors='replace')
                # バイナリ判定: \x00が含まれるならバイナリ
                if "\x00" in text:
                    raise ValueError("binary")
                self.preview_img_label.configure(text="📄", image="")
                self.preview_text_box.configure(state="normal"); self.preview_text_box.delete("1.0","end")
                self.preview_text_box.insert("end", text[:800]); self.preview_text_box.configure(state="disabled")
                return
            except Exception:
                pass
        # バイナリ
        self.preview_img_label.configure(text="📦", image="")
        self.preview_text_box.configure(state="normal"); self.preview_text_box.delete("1.0","end"); self.preview_text_box.insert("end", f"バイナリファイル ({human_size(len(data))})\nプレビューできません"); self.preview_text_box.configure(state="disabled")

    def on_search(self, event=None):
        q=self.search_entry.get().strip().lower()
        if not hasattr(self, 'current_items') or not self.current_items:
            return
        self.tree.delete(*self.tree.get_children())
        if not q:
            # 全件表示
            for name,size,is_dir,dt,enc in self.current_items[:500]:
                icon="📁" if is_dir else ("🔒" if enc else "📄")
                typ="フォルダ" if is_dir else ("暗号化" if enc else "ファイル")
                sz="-" if is_dir else human_size(size)
                tag="enc" if enc else ""
                self.tree.insert("", "end", text=f"{icon} {name}", values=(sz, typ), tags=(tag,))
            self.search_info.configure(text="")
            return
        # フィルタ
        matched=[]
        for item in self.current_items:
            name=item[0]
            if q in name.lower():
                matched.append(item)
        for name,size,is_dir,dt,enc in matched[:500]:
            icon="📁" if is_dir else ("🔒" if enc else "📄")
            typ="フォルダ" if is_dir else ("暗号化" if enc else "ファイル")
            sz="-" if is_dir else human_size(size)
            self.tree.insert("", "end", text=f"{icon} {name}", values=(sz, typ))
        self.search_info.configure(text=f"🔍 {len(matched)}件ヒット / {len(self.current_items)}件中")
        if not matched:
            self.search_info.configure(text=f"🔍 該当なし: '{q}'")

    def clear_search(self):
        self.search_entry.delete(0, "end")
        self.on_search()
        self.search_info.configure(text="")

    def get_dest_dir(self):
        m=self.dest_mode.get()
        if m=="same": return os.path.dirname(self.archive_path) if self.archive_path else os.getcwd()
        elif m=="desktop": return os.path.join(os.path.expanduser("~"),"Desktop")
        else:
            if not self.custom_dest or not os.path.isdir(self.custom_dest):
                messagebox.showwarning("出力先エラー","有効な出力フォルダを選択してください"); return None
            return self.custom_dest

    def start_extract(self):
        if not self.queue_files: 
            if not self.archive_path or not os.path.exists(self.archive_path): messagebox.showwarning("エラー","アーカイブが選択されていません"); return
            targets=[self.archive_path]
        else:
            targets=list(self.queue_files)
        dest_base=self.get_dest_dir()
        if not dest_base: return
        # 大容量・ディスク容量チェック
        try:
            if hasattr(self,'current_items') and self.current_items:
                total_needed = sum(s for _,s,is_dir,_,enc in self.current_items if not is_dir)
                if total_needed > 500*1024*1024:
                    free = shutil.disk_usage(dest_base).free
                    if total_needed > free:
                        messagebox.showerror("容量不足", f"展開に {human_size(total_needed)} 必要ですが、空き容量は {human_size(free)} しかありません")
                        return
                    if total_needed > 2*1024*1024*1024:
                        if not messagebox.askyesno("大容量警告", f"展開後のサイズが {human_size(total_needed)} と大きいです。\n続行しますか？\n\n（ZipBombチェック済み）"):
                            return
        except Exception as e:
            pass
        # 上書きモードの事前確認は各ファイルで行う
        pw=self.entry_pw.get().strip() or None
        self.is_extracting=True; Extractor.cancel_flag.clear()
        self.btn_extract.configure(state="disabled", text="解凍中..."); self.btn_cancel.configure(state="normal")
        self.progress.set(0); self._set_indicator("running", f"{len(targets)}件 解凍中", "0%")
        self.save_settings()
        start_time = time.time()
        def prog(v):
            # v: 0-100
            def update():
                self.progress.set(v/100)
                self._update_taskbar_progress(v, 100)
                # 統一ステータスバーに進捗 + ETA
                elapsed = time.time() - start_time
                if elapsed > 0.5 and v>0:
                    pct = v
                    eta = int(elapsed * (100 - pct) / pct) if pct>0 else 0
                    self.status_label.configure(text=f"⏳ {pct}% • 経過 {int(elapsed)}秒 • 残り ~{eta}秒")
                    self.indicator_sub.configure(text=f"{pct}%")
                else:
                    self.status_label.configure(text=f"⏳ {v}%")
            self.after(0, update)
        def log_cb(m): self.after(0, lambda: self.log(m))
        def worker():
            total=len(targets); success=0; failed=[]
            for idx, arch in enumerate(targets):
                if Extractor.cancel_flag.is_set(): break
                self.after(0, lambda i=idx, t=total, a=arch: self.set_status(f"{i+1}/{t}  解凍中: {os.path.basename(a)}"))
                stem=pathlib.Path(arch).name
                if stem.lower().endswith(".tar.gz"): stem=stem[:-7]
                elif stem.lower().endswith(".tgz"): stem=stem[:-4]
                else: stem=pathlib.Path(stem).stem
                dest_dir=os.path.join(dest_base, stem)
                # 上書き/スキップ処理
                if os.path.exists(dest_dir) and os.listdir(dest_dir):
                    mode=self.overwrite_var.get()
                    if mode=="skip":
                        log_cb(f"スキップ: {dest_dir} は既存"); continue
                    elif mode=="smart":
                        # 確認ダイアログ（メインスレッドで）
                        # 簡易: 連番で回避（既存の smart は連番）
                        counter=1; orig=dest_dir
                        while os.path.exists(dest_dir) and os.listdir(dest_dir):
                            dest_dir=f"{orig}_{counter}"; counter+=1; 
                            if counter>99: break
                    # overwrite はそのまま
                ok,err=Extractor.extract(arch, dest_dir, pw, prog, log_cb)
                CONFIG.add_history(arch, dest_dir, ok)
                if ok:
                    success+=1
                    # おまかせ整理
                    try:
                        do_org = CONFIG.get("organize", False)
                    except Exception: do_org = False
                    if do_org:
                        self.after(0, lambda d=dest_dir: self.organize_extracted(d))
                    if self.var_delete.get() and os.path.exists(arch):
                        try: os.remove(arch); log_cb(f"元アーカイブを削除: {arch}")
                        except Exception as e: log_cb(f"削除失敗: {e}")
                else:
                    failed.append(f"{os.path.basename(arch)}: {err}")
                self.after(0, lambda: self._load_history_ui())
            self.after(0, lambda: self.on_batch_done(success, total, failed, dest_base))
        threading.Thread(target=worker,daemon=True).start()

    def cancel_extract(self):
        if self.is_extracting:
            Extractor.cancel_flag.set(); self.log("キャンセル要求..."); self.set_status("キャンセル中...")

    def on_batch_done(self, success, total, failed, dest_base):
        self.is_extracting=False; self.btn_extract.configure(state="normal", text="解凍する ▶"); self.btn_cancel.configure(state="disabled")
        if Extractor.cancel_flag.is_set():
            self.progress.set(0); self._set_indicator("idle", "キャンセルされました", ""); self._update_taskbar_progress(0,100)
            self.show_toast("キャンセルしました", COLOR_WARN); return
        self.progress.set(1); self._update_taskbar_progress(100,100)
        if failed:
            self._set_indicator("error", f"{success}/{total} 成功", f"失敗 {len(failed)}件")
            messagebox.showwarning("一部失敗", f"{success}/{total} 成功\n\n失敗:\n" + "\n".join(failed[:5]))
        else:
            self._set_indicator("done", f"{success}件 完了", "100%")
            self.progress_detail.configure(text=f"✅ 完了 • {success}件 • {dest_base}")
            if CONFIG.get("notifications", True):
                self.show_toast(f"✅ {success}件の解凍が完了しました", COLOR_SUCCESS)
            else:
                messagebox.showinfo("完了", f"{success}件の解凍が完了しました:\n{dest_base}")
            if self.var_open_folder.get():
                try: os.startfile(dest_base)
                except Exception: subprocess.Popen(f'explorer "{dest_base}"')
        # 3秒後にインジケーターをidleに戻す
        self.after(3000, lambda: self._set_indicator("idle", "待機中", ""))
        # 成功したものをキューから除去（削除設定なら既に消えている）
        if not failed and not Extractor.cancel_flag.is_set():
            # 削除モードでなければキューは保持、完了したらクリアするかは選択
            pass
        self._load_history_ui()

    def _load_history_ui(self):
        for w in self.history_frame.winfo_children(): w.destroy()
        hist=CONFIG.get("history", [])
        if not hist:
            ctk.CTkLabel(self.history_frame, text="履歴なし", font=("BIZ UDGothic",9), text_color=current_colors()["SUB"]).pack(pady=8)
            return
        for h in hist[:10]:
            row=ctk.CTkFrame(self.history_frame, fg_color=current_colors()["CARD"], corner_radius=6); row.pack(fill="x", padx=4, pady=2)
            icon="✅" if h.get("ok") else "❌"
            ctk.CTkLabel(row, text=f"{icon} {h['archive']}", font=("BIZ UDGothic",9,"bold"), text_color=current_colors()["TEXT"], width=150, anchor="w").pack(side="left", padx=6, pady=4)
            ctk.CTkLabel(row, text=h["time"], font=("BIZ UDGothic",8), text_color=current_colors()["SUB"]).pack(side="left")
            ctk.CTkButton(row, text="開く", width=36, height=18, font=("BIZ UDGothic",8), fg_color=COLOR_PRIMARY, command=lambda d=h["dest"]: self._open_path(d)).pack(side="right", padx=4)

    def _open_path(self, p):
        if os.path.exists(p):
            try: os.startfile(p)
            except Exception: subprocess.Popen(f'explorer \"{p}\"')
        else: messagebox.showwarning("見つかりません", f"パスが存在しません:\n{p}")

    def clear_history(self):
        CONFIG.clear_history(); self._load_history_ui(); self.log("履歴をクリアしました")

    # ── 圧縮機能 ──
    def c_log(self, msg):
        self.c_log_box.configure(state="normal")
        ts=datetime.now().strftime("%H:%M:%S")
        self.c_log_box.insert("end", f"[{ts}] {msg}\n"); self.c_log_box.see("end"); self.c_log_box.configure(state="disabled")
    def c_set_status(self, msg): self.c_status_label.configure(text=msg)
    def _refresh_compress_ui(self):
        for w in self.c_queue_frame.winfo_children(): w.destroy()
        if not self.compress_files:
            ctk.CTkLabel(self.c_queue_frame, text="ファイル未追加", font=("BIZ UDGothic",10), text_color=current_colors()["SUB"]).pack(pady=8)
            self.c_queue_label.configure(text="0件"); self.c_btn_compress.configure(state="disabled"); self._update_queue_badge(); return
        self.c_queue_label.configure(text=f"{len(self.compress_files)}件"); self._update_queue_badge()
        total = sum(os.path.getsize(f) if os.path.isfile(f) else sum(os.path.getsize(os.path.join(r,f)) for r,_,files in os.walk(f) for f in files) for f in self.compress_files)
        for idx, p in enumerate(self.compress_files):
            row=ctk.CTkFrame(self.c_queue_frame, fg_color=current_colors()["CARD"], corner_radius=6); row.pack(fill="x", padx=4, pady=2)
            name=os.path.basename(p.rstrip(os.sep))
            sz = os.path.getsize(p) if os.path.isfile(p) else "フォルダ"
            if isinstance(sz,int): sz=human_size(sz)
            ctk.CTkLabel(row, text=f"{idx+1}. {name}", font=("BIZ UDGothic",10), text_color=current_colors()["TEXT"], width=180, anchor="w").pack(side="left", padx=8, pady=4)
            ctk.CTkLabel(row, text=sz, font=("BIZ UDGothic",9), text_color=current_colors()["SUB"]).pack(side="left")
            ctk.CTkButton(row, text="✕", width=24, height=20, fg_color="#fee2e2", text_color="#dc2626", hover_color="#fecaca", command=lambda i=idx: self.remove_compress_file(i)).pack(side="right", padx=6)
        self.c_btn_compress.configure(state="normal")
        # 出力名を自動生成（最初のファイル名から）
        if self.compress_files:
            base=os.path.basename(self.compress_files[0].rstrip(os.sep))
            base=os.path.splitext(base)[0] if os.path.isfile(self.compress_files[0]) else base
            fmt=self.c_fmt_var.get()
            ext={"zip":".zip","7z":".7z","tar.gz":".tar.gz"}.get(fmt,".zip")
            self.c_output_var.set(os.path.join(os.path.dirname(self.compress_files[0]) if os.path.isfile(self.compress_files[0]) else self.compress_files[0], base+ext))
            # デスクトップが無難ならデスクトップに
            if not os.path.exists(os.path.dirname(self.c_output_var.get())):
                self.c_output_var.set(os.path.join(os.path.expanduser("~"),"Desktop", base+ext))
    def add_compress_files(self, paths):
        added=0
        for p in paths:
            if p not in self.compress_files and os.path.exists(p):
                self.compress_files.append(p); added+=1
        if added: self._refresh_compress_ui(); self.c_log(f"{added}件追加")
    def remove_compress_file(self, idx):
        if 0<=idx<len(self.compress_files): self.compress_files.pop(idx); self._refresh_compress_ui()
    def clear_compress_queue(self):
        self.compress_files=[]; self._refresh_compress_ui(); self.c_set_status("待機中"); self.c_progress.set(0)
    def pick_compress_files(self):
        paths=filedialog.askopenfilenames(title="圧縮するファイルを選択（複数可）")
        if paths: self.add_compress_files(list(paths))
    def pick_compress_folder(self):
        d=filedialog.askdirectory(title="圧縮するフォルダを選択")
        if d: self.add_compress_files([d])
    def pick_compress_output(self):
        fmt=self.c_fmt_var.get()
        exts=[("ZIP","*.zip"),("7Z","*.7z"),("TAR.GZ","*.tar.gz")]
        default_ext={".zip":".zip",".7z":".7z",".tar.gz":".tar.gz"}[{".zip":".zip","7z":".7z","tar.gz":".tar.gz"}[fmt]] if False else {".zip":".zip","7z":".7z","tar.gz":".tar.gz"}.get(fmt,".zip")
        # 簡易: zipで保存ダイアログ
        p=filedialog.asksaveasfilename(title="保存先", defaultextension=fmt, initialfile=os.path.basename(self.c_output_var.get()))
        if p: self.c_output_var.set(p)
    def on_compress_drop(self, event):
        data=self.tk.splitlist(event.data)
        files=[p for p in data if os.path.exists(p)]
        if files: self.add_compress_files(files); self.tabview.set("🗜️ 圧縮")
    def start_compress(self):
        if not self.compress_files: messagebox.showwarning("エラー","圧縮するファイルがありません"); return
        out=self.c_output_var.get().strip()
        if not out: messagebox.showwarning("エラー","出力先を指定してください"); return
        # 拡張子をfmtに合わせる
        fmt=self.c_fmt_var.get()
        # 出力先が既存なら確認
        if os.path.exists(out):
            if not messagebox.askyesno("確認", f"既に存在します。上書きしますか？\n{out}"): return
        level=self.c_level_var.get(); pw=self.c_pw_entry.get().strip() or None
        if fmt=="zip" and pw:
            messagebox.showerror(
                "未対応",
                "ZIPのパスワード付き圧縮は現在未対応です。\n暗号化する場合は7Zを選択してください。",
            )
            return
        self.is_compressing=True; Compressor.cancel_flag.clear()
        self.c_btn_compress.configure(state="disabled", text="圧縮中..."); self.c_progress.set(0); self.c_set_status("圧縮中...")
        self.c_progress_detail.configure(text="準備中...")
        self._set_indicator("running", "圧縮中", "0%")
        start_t=time.time()
        def prog(v):
            def upd():
                self.c_progress.set(v/100); self._update_taskbar_progress(v,100)
                elapsed=time.time()-start_t
                if elapsed>0.5 and v>0:
                    eta=int(elapsed*(100-v)/v) if v>0 else 0
                    self.c_progress_detail.configure(text=f"{v}% • 経過 {int(elapsed)}秒 • 残り~{eta}秒")
                    self.indicator_sub.configure(text=f"{v}%")
                else:
                    self.c_progress_detail.configure(text=f"{v}%")
            self.after(0, upd)
        def log_cb(m): self.after(0, lambda: self.c_log(m))
        def worker():
            ok,err=Compressor.compress(self.compress_files, out, fmt, level, pw, prog, log_cb)
            self.after(0, lambda: self.on_compress_done(ok,err,out))
        threading.Thread(target=worker, daemon=True).start()
    def on_compress_done(self, ok, err, out):
        self.is_compressing=False; self.c_btn_compress.configure(state="normal", text="圧縮する ▶")
        self.c_progress_detail.configure(text="")
        if ok:
            self.c_progress.set(1); self._update_taskbar_progress(100,100); self.c_set_status(f"完了: {out}"); self.c_log("圧縮完了！")
            self._set_indicator("done", "圧縮完了", "100%")
            self.c_progress_detail.configure(text=f"✅ 完了 • {os.path.basename(out)}")
            self.show_toast(f"✅ 圧縮完了: {os.path.basename(out)}", COLOR_SUCCESS)
            CONFIG.add_history(out, out, True)
            self._load_history_ui()
            if messagebox.askyesno("完了", f"圧縮が完了しました:\n{out}\n\nフォルダを開きますか？"):
                try: os.startfile(os.path.dirname(out))
                except Exception: subprocess.Popen(f'explorer "{os.path.dirname(out)}"')
            self.after(3000, lambda: self._set_indicator("idle","待機中",""))
        else:
            self.c_progress.set(0); self.c_set_status(f"失敗: {err}"); self.c_log(f"失敗: {err}")
            self._set_indicator("error", "圧縮失敗", "")
            self.c_progress_detail.configure(text=f"失敗: {err[:40]}")
            messagebox.showerror("圧縮失敗", err)
            self.after(3000, lambda: self._set_indicator("idle","待機中",""))

    # ── 更新チェック ──
    def check_update(self, silent=True):
        def cb(has_update, latest, url, notes):
            if has_update:
                self._update_url = url
                self.update_banner_label.configure(text=f"🎉 新バージョン v{latest} が利用可能です！")
                self.update_banner.pack(fill="x", side="top", before=self.tabview)
                self.show_toast(f"新バージョン v{latest} があります", COLOR_WARN)
            elif not silent:
                if has_update is None:
                    messagebox.showinfo("更新確認", f"確認に失敗しました:\n{notes}")
                else:
                    messagebox.showinfo("更新確認", f"最新バージョンです (v{APP_VERSION})")
        UpdateChecker.check(APP_VERSION, silent=silent, callback=cb)
    def open_update_url(self):
        if self._update_url:
            import webbrowser; webbrowser.open(self._update_url)
        else:
            messagebox.showinfo("更新", "ダウンロードページを開きます")

    def open_association(self): AssociationWindow(self)
    def show_confetti(self):
        """紙吹雪アニメーション"""
        try:
            canvas = tk.Canvas(self, highlightthickness=0, bg="", bd=0)
            canvas.place(relx=0, rely=0, relwidth=1, relheight=1)
            canvas.configure(bg=self.cget("bg"))
            # 透明に見せるため、親と同じ背景で一時的に
            w = self.winfo_width(); h = self.winfo_height()
            colors = ["#f59e0b", "#ef4444", "#10b981", "#3b82f6", "#8b5cf6", "#ec4899"]
            particles = []
            for _ in range(60):
                x = random.randint(0, w)
                y = random.randint(-40, 0)
                size = random.randint(6, 12)
                col = random.choice(colors)
                shape = random.choice(["rect", "circle"])
                if shape == "rect":
                    pid = canvas.create_rectangle(x, y, x+size, y+size, fill=col, outline="")
                else:
                    pid = canvas.create_oval(x, y, x+size, y+size, fill=col, outline="")
                particles.append((pid, random.uniform(2, 6), random.uniform(-1, 1), random.uniform(2, 5)))
            def animate(step=0):
                if step > 80:
                    canvas.destroy(); return
                for pid, vy, vx, rot in particles:
                    try:
                        canvas.move(pid, vx, vy)
                        # 回転は簡易
                    except Exception: pass
                self.after(30, lambda: animate(step+1))
            animate()
            try: ctypes.windll.user32.MessageBeep(0x00000040)
            except Exception: pass
        except Exception: pass

    def omakase_action(self):
        """おまかせボタン: キューがあればランダム解凍、なければ運勢とTips"""
        msg = random.choice(OMAKASE_MESSAGES)
        # キューがある場合: ランダムに1件を即解凍 or シャッフル
        if self.queue_files:
            # シャッフルして1件ピックアップ
            target = random.choice(self.queue_files)
            self.load_archive(target)
            self.show_toast(f"{msg} → {os.path.basename(target)} を選択", "#f59e0b")
            self.show_confetti()
            # 1秒後に自動解凍（おまかせ）
            self.after(800, self.start_extract)
            # 実績カウンタ
            cnt = CONFIG.get("omakase_count", 0) + 1
            CONFIG.set("omakase_count", cnt)
            if cnt in [5, 10, 20]:
                self.after(2000, lambda: messagebox.showinfo("実績解除", f"🎉 おまかせ {cnt}回達成！\nあなたはおまかせマスターです"))
            return
        if self.compress_files:
            self.tabview.set("🗜️ 圧縮")
            self.show_toast(f"{msg} → 圧縮おまかせで実行", "#f59e0b")
            self.show_confetti()
            self.after(600, self.start_compress)
            return
        # キューなし: 履歴からランダム or 運勢
        hist = CONFIG.get("history", [])
        if hist and random.random() > 0.5:
            h = random.choice(hist)
            self.show_toast(f"{msg}", "#f59e0b")
            if os.path.exists(h["dest"]):
                if messagebox.askyesno("おまかせ", f"{msg}\n\n履歴からランダムに開きます:\n{h['archive']} → {h['dest']}\n\n開きますか？"):
                    self._open_path(h["dest"])
                    self.show_confetti()
            else:
                messagebox.showinfo("おまかせ", f"{msg}\n\n履歴: {h['archive']}")
                self.show_confetti()
        else:
            tips = [
                "💡 Tips: フォルダをドロップすると中のアーカイブを一括登録できます",
                "💡 Tips: 7ZはZIPより高圧縮！パスワードも強力です",
                "💡 Tips: 右クリックメニューから直接解凍できます（関連付け設定）",
                "💡 Tips: ダークモードは🌙ボタンで切り替え",
                "💡 Tips: 大きなファイルは進捗がバイト単位で正確に表示されます",
            ]
            tip = random.choice(tips)
            messagebox.showinfo("おまかせ", f"{msg}\n\n{tip}")
            self.show_confetti()
            # 裏コマンド: 5回おまかせで隠しテーマ？
            cnt = CONFIG.get("omakase_count", 0) + 1
            CONFIG.set("omakase_count", cnt)
            # 5回ごとにテーマおまかせ
            if cnt % 5 == 0:
                self.after(1000, self.apply_omakase_theme)

    def organize_extracted(self, dest_dir):
        try:
            moved=0
            for fname in os.listdir(dest_dir):
                fpath=os.path.join(dest_dir, fname)
                if os.path.isdir(fpath): continue
                ext=pathlib.Path(fname).suffix.lower()
                cat=None
                for c, exts in ORGANIZE_CATEGORIES.items():
                    if ext in exts:
                        cat=c; break
                if cat:
                    d=os.path.join(dest_dir, cat)
                    os.makedirs(d, exist_ok=True)
                    dst=os.path.join(d, fname)
                    if os.path.exists(dst):
                        base, e=os.path.splitext(fname)
                        dst=os.path.join(d, f"{base}_1{e}")
                    shutil.move(fpath, dst); moved+=1
            if moved>0:
                self.log(f"✨ おまかせ整理: {moved}件を種類別に整理")
                self.show_toast(f"✨ {moved}件を整理しました", "#f59e0b")
        except Exception as e:
            self.log(f"整理失敗: {e}")

    def apply_omakase_theme(self):
        try:
            key=random.choice(list(OMAKASE_THEMES.keys()))
            th=OMAKASE_THEMES[key]
            # ボタンの色を変える
            try:
                self.btn_extract.configure(fg_color=th["primary"])
                self.c_btn_compress.configure(fg_color=th["primary"])
            except Exception: pass
            self.show_toast(f"🎨 テーマ: {th['name']}", th["primary"])
            self.show_confetti()
            CONFIG.set("omakase_theme", key)
        except Exception: pass

    def show_help(self):
        messagebox.showinfo("使い方",
            "【使い方】\n1. ZIP等をドラッグ＆ドロップ（複数OK）\n   または「ファイルを選択...」\n2. 出力先を選択\n3. パスワードがあれば入力\n4. 「解凍する」をクリック\n\n【圧縮】\n🗜️圧縮タブでファイル/フォルダをドロップ→形式と出力先を選択→「圧縮する」\nZIP/7Z/TAR.GZ対応、7Zはパスワード付き高圧縮が可能\n\n【バッチ】\nフォルダをドロップすると中のアーカイブを一括登録\nキューから不要なファイルを✕で除外可能\n\n【関連付け】\n⚙関連付け → 拡張子を選択 → サブメニュー/送る も設定可\n自動解凍ONでダブルクリック即解凍\n\n【おまかせ】\n🎲おまかせはランダムに解凍/圧縮を実行＆紙吹雪！履歴からランダムに開くことも\n\n【設定】\nテーマ切替（🌙/☀️）、履歴、削除、通知などは自動保存\n履歴の「開く」で展開先を即オープン\n\n対応: ZIP, 7Z, TAR, TAR.GZ, TGZ, GZ, BZ2, RAR")
    def handle_cli_arg(self):
        # 起動引数のログ（デバッグ用）
        try:
            with open(os.path.join(os.getenv("TEMP") or ".", "SimpleExtract_debug.log"), "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now()}] handle_cli_arg argv={sys.argv}\n")
        except Exception: pass
        args=[a.strip('"') for a in sys.argv[1:] if not a.startswith("--")]
        flags=[a for a in sys.argv[1:] if a.startswith("--")]
        if args:
            p=args[0]
            # パスを絶対パスに正規化
            p=os.path.abspath(p)
            if os.path.isfile(p) and is_supported(p):
                if "--here" in flags: self.dest_mode.set("same")
                elif "--desktop" in flags: self.dest_mode.set("desktop")
                # afterで確実にUI生成後に実行（lambdaの遅延束縛を修正）
                self.after(800, lambda p=p: self.load_archive(p))
                if CONFIG.get("auto_extract"):
                    self.after(1600, lambda: self.start_extract() if self.archive_path else None)
            elif os.path.isdir(p):
                files=[os.path.join(p,f) for f in os.listdir(p) if is_supported(os.path.join(p,f))]
                if files:
                    self.add_to_queue(files); self.after(800, lambda p=files[0]: self.load_archive(p))
            else:
                # ファイルが見つからない場合はログ
                self.after(1000, lambda: self.log(f"関連付けファイルが見つかりません: {p}"))
        if len(args)>1:
            files=[a for a in args if os.path.isfile(os.path.abspath(a)) and is_supported(os.path.abspath(a))]
            files=[os.path.abspath(a) for a in files]
            if len(files)>1: self.add_to_queue(files)

if __name__=="__main__":
    if _ensure_rarfile():
        import rarfile
        for p in [r"C:\Program Files\WinRAR\UnRAR.exe", r"C:\Program Files (x86)\WinRAR\UnRAR.exe"]:
            if os.path.exists(p): rarfile.UNRAR_TOOL=p; break
    app=SimpleExtractApp()
    app.handle_cli_arg()
    app.mainloop()
