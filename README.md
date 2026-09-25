# 📦 SimpleExtract - Windows用 高機能シンプル解凍・圧縮ソフト

ドラッグ&ドロップでZIP/7Z/RARを一発解凍・圧縮。Windows 11/10対応の軽量GUIツール。

![Python](https://img.shields.io/badge/Python-3.11-blue) ![License](https://img.shields.io/badge/license-MIT-green) ![Version](https://img.shields.io/badge/version-1.5.7-blue)

## ✨ 特徴

### 解凍
- **ドラッグ&ドロップ**（複数ファイル・フォルダ対応、バッチ処理）
- **対応形式**: ZIP / 7Z / TAR / TAR.GZ / TGZ / GZ / BZ2 / RAR
- **パスワード対応**（ZIP/7Z、鍵アイコン表示）
- **内容プレビュー** - 画像サムネイル / テキスト先頭表示 / 暗号化判定
- **出力先選択** - 同じフォルダ / デスクトップ / 任意
- **履歴・お気に入り** - 展開履歴からのワンクリック再オープン

### 圧縮
- **🗜️ 圧縮タブ** - ファイル/フォルダをドロップして ZIP/7Z/TAR.GZ を作成
- 圧縮レベル 1-9、パスワード（7Zのみ）、出力先選択

### 快適性
- **アンチエイリアス** - BIZ UDGothic + ClearType + PerMonitorV2 マニフェストで滑らか
- **ダークモード** - 🌙/☀️ 切替、設定は自動保存
- **インジケーター** - ヘッダーの状態ドット + タスクバー進捗 + キューバッジ + ETA表示
- **関連付け** - 拡張子をダブルクリックで開く、右クリックメニュー（サブメニュー/送る）
- **自動アップデート** - GitHub Releasesをチェックしてバナー表示
- **おまかせ** 🎲 - ランダム解凍/圧縮 + 紙吹雪 + 実績

## 🚀 使い方

### インストール（推奨）
`dist-installer/SimpleExtract-Setup-1.5.7.exe` を実行 → スタートメニューに登録

### ポータブル
```bash
pip install -r requirements.txt
python simple_extract.py
# または
dist/SimpleExtract-OneFile.exe  # 単体ファイル
dist/SimpleExtract/SimpleExtract.exe  # フォルダ版（起動が速い）
```

### 操作
1. アーカイブをドラッグ&ドロップ（または「ファイルを選択...」）
2. 出力先を選択
3. パスワードがあれば入力
4. 「解凍する ▶」→ 完了後フォルダが自動で開きます

## 📦 ビルド

```bash
pip install pyinstaller
# フォルダ版（推奨・起動が速い）
pyinstaller --windowed --name SimpleExtract --icon=assets/icon.ico --manifest assets/app.manifest simple_extract.py
# 単一ファイル版
pyinstaller --windowed --onefile --name SimpleExtract-OneFile --icon=assets/icon.ico --manifest assets/app.manifest simple_extract.py
# インストーラー
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
# 署名（任意）
.\scripts\sign.ps1 -CreateCert
.\scripts\sign.ps1 -Sign "dist\SimpleExtract\SimpleExtract.exe"
```

## 🛠 技術スタック

- Python 3.11 + CustomTkinter + TkinterDnD2 + Pillow
- zipfile / tarfile + py7zr (7Z) + rarfile (RAR)
- PyInstaller + Inno Setup 6

## 📋 対応形式

| 拡張子 | 備考 |
|--------|------|
| .zip | 解凍時パスワード対応。作成時の暗号化は未対応 |
| .7z | 高圧縮、解凍・作成ともパスワード対応 |
| .tar / .tar.gz / .tgz |  |
| .gz / .bz2 | 単体圧縮 |
| .rar | WinRAR/UnRAR 必要 |

## ⚙️ 設定

- `%APPDATA%\SimpleExtract\config.json` に自動保存
- 出力先、テーマ、履歴、関連付けなど

## 📄 ライセンス

MIT License - `LICENSE` を参照
