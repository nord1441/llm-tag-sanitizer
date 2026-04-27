# llm-tag-sanitizer

Ollama の LLM を使って音楽ファイルのタグを自動で最適化する CLI ツール。

指定ディレクトリ以下の音楽ファイルをスキャンし、アーティスト名の表記揺れ統一・マルチディスクアルバムの統合・タグの入れ替わり修正を行う。

## 前提条件

- Python 3.10 以上
- [Ollama](https://ollama.com/) がインストール済みで起動していること

```bash
# Ollama のインストール (Linux)
curl -fsSL https://ollama.com/install.sh | sh

# モデルのダウンロード (例)
ollama pull llama3.1
ollama pull gemma2:9b

# Ollama サーバーの起動
ollama serve
```

## インストール

```bash
git clone https://github.com/nord1441/llm-tag-sanitizer.git
cd llm-tag-sanitizer
pip install -e .
```

開発用の依存パッケージ (pytest 等) も含める場合:

```bash
pip install -e ".[dev]"
```

## 基本的な使い方

```bash
llm-tag-sanitizer <ディレクトリパス> [オプション]
```

デフォルトでは **dry-run モード** で動作し、変更内容のプレビューのみを表示する。実際にタグを書き換えるには `--apply` を付ける。

### 変更をプレビューする (dry-run)

```bash
llm-tag-sanitizer /path/to/music
```

出力例:

```
Using model: llama3.1

Scanning: /path/to/music
Found 128 music files.

Grouped into 12 artist group(s).

Running artist normalizer...
Running disc merger...
Running swap detector...

┌──────────────────┬───────────┬──────────────────┬──────────────┬────────────────────────┐
│ File             │ Field     │ Old Value        │ New Value    │ Reason                 │
├──────────────────┼───────────┼──────────────────┼──────────────┼────────────────────────┤
│ 02.mp3           │ artist    │ T-スクェア       │ T-SQUARE     │ Artist normalization   │
│ 01.mp3           │ album     │ Truth disc 1     │ Truth        │ Disc merge             │
│                  │ discnumber│ (empty)          │ 1            │ Disc merge             │
│ track.mp3        │ artist    │ Bohemian Rhapsody│ Queen        │ Tag swap fix           │
│                  │ title     │ Queen            │ Bohemian ... │ Tag swap fix           │
└──────────────────┴───────────┴──────────────────┴──────────────┴────────────────────────┘

Summary:
  Files affected: 3
  Total changes: 5
    artist_normalizer: 1
    disc_merger: 2
    swap_detector: 2

Dry-run mode. No changes applied. Use --apply to apply changes.
```

### 変更を実行する

```bash
llm-tag-sanitizer /path/to/music --apply
```

確認プロンプトが表示される。`-y` で確認をスキップできる:

```bash
llm-tag-sanitizer /path/to/music --apply -y
```

## オプション一覧

| オプション | デフォルト | 説明 |
|---|---|---|
| `--model TEXT` | `llama3.1` | 使用する Ollama モデル名 |
| `--dry-run` / `--apply` | `--dry-run` | 変更のプレビューのみ / 実際に適用 |
| `--web-search` | off | Web 検索でアーティスト情報を取得 |
| `--rename` | off | タグ変更後にファイル名・ディレクトリも変更 |
| `--naming-template TEXT` | (後述) | リネーム時のファイル命名テンプレート |
| `--optimizers TEXT` | 全て | 実行するオプティマイザをカンマ区切りで指定 |
| `--backup` | off | 変更前に `.bak` バックアップを作成 |
| `-v, --verbose` | off | 詳細ログを表示 |
| `--log-file PATH` | なし | ログファイルの出力先 |
| `-y, --yes` | off | 確認プロンプトをスキップ |
| `--version` | - | バージョン表示 |

## 最適化機能の詳細

### 1. アーティスト名の正規化 (`artist_normalizer`)

同一アーティストの異なる表記を LLM で判定し、公式名に統一する。

**対応する表記揺れの例:**

| 変更前 | 変更後 |
|---|---|
| T-Square, T-スクェア, T-SQUARE | T-SQUARE |
| Bjork, Björk | Björk |
| L'Arc~en~Ciel, L'Arc-en-Ciel, ラルクアンシエル | L'Arc~en~Ciel |

仕組み:

1. アーティスト名を正規化 (小文字化・Unicode NFC・空白除去) し、レーベンシュタイン距離が近い名前をグルーピング
2. 同一グループ内に複数のバリアントがある場合、LLM に公式名を問い合わせ
3. `--web-search` 有効時は Web 検索結果も LLM への入力に含める

### 2. マルチディスクアルバムの統合 (`disc_merger`)

ディスク番号がアルバム名に含まれているケースを検出し、アルバム名を統一してディスク番号タグを設定する。

**対応するパターン:**

| 変更前のアルバム名 | 変更後 | discnumber |
|---|---|---|
| `Greatest Hits disc 1` | `Greatest Hits` | `1` |
| `Greatest Hits disc 2` | `Greatest Hits` | `2` |
| `Album CD1` | `Album` | `1` |
| `Album (Disc 2)` | `Album` | `2` |
| `Album [Disk 3]` | `Album` | `3` |

仕組み:

1. アルバム名末尾のディスク番号パターン (`disc N`, `CD N`, `Disk N` 等) を正規表現で検出
2. ディスク番号を除去したアルバム名でグルーピング
3. 複数バリアントがある場合、LLM に同一アルバムかどうかを確認
4. 単一バリアントでもディスクサフィックスがあれば自動でアルバム名をクリーンアップ

### 3. タグ入れ替わりの検出 (`swap_detector`)

アーティストとタイトルが逆に入っている等のタグの入れ替わりを検出・修正する。

**検出パターンの例:**

| artist (変更前) | title (変更前) | artist (変更後) | title (変更後) |
|---|---|---|---|
| Bohemian Rhapsody | Queen | Queen | Bohemian Rhapsody |
| Stairway to Heaven | Led Zeppelin | Led Zeppelin | Stairway to Heaven |

仕組み:

1. ヒューリスティクスで疑わしいトラックを事前フィルタ:
   - 全トラックで title が同一なのに artist が異なる場合
   - artist フィールドにトラック番号や `(feat. ...)` が含まれる場合
   - title フィールドが他トラックの artist と一致する場合
2. 疑わしいトラックを LLM に送信して確認・修正

## 使い方の例

### モデルを選んで実行

```bash
# llama3.1 (デフォルト)
llm-tag-sanitizer /path/to/music

# gemma2 を使用
llm-tag-sanitizer /path/to/music --model gemma2:9b

# qwen2.5 を使用
llm-tag-sanitizer /path/to/music --model qwen2.5:14b
```

使用可能なモデルは `ollama list` で確認できる。

### Web 検索を有効にして精度を上げる

```bash
llm-tag-sanitizer /path/to/music --web-search
```

DuckDuckGo でアーティスト情報を検索し、LLM への入力コンテキストに含める。公式名の判定精度が向上する。

### 特定のオプティマイザだけ実行

```bash
# アーティスト名の正規化だけ
llm-tag-sanitizer /path/to/music --optimizers artist_normalizer

# ディスク統合とスワップ検出
llm-tag-sanitizer /path/to/music --optimizers disc_merger,swap_detector
```

### バックアップ付きで適用

```bash
llm-tag-sanitizer /path/to/music --apply --backup
```

各ファイルの変更前に `.bak` コピーが作成される (例: `song.mp3` → `song.mp3.bak`)。

### タグ変更後にファイル名・ディレクトリも整理

```bash
llm-tag-sanitizer /path/to/music --apply --rename
```

デフォルトのファイル命名規則:

```
{albumartist}/{album}/{tracknumber} - {title}{ext}
```

マルチディスクアルバムの場合:

```
{albumartist}/{album}/{discnumber}-{tracknumber} - {title}{ext}
```

**リネーム例:**

```
変更前: T-Square/Truth disc 1/02.mp3
変更後: T-SQUARE/Truth/02 - Forgotten Saga.mp3
```

### カスタム命名テンプレート

```bash
llm-tag-sanitizer /path/to/music --apply --rename \
  --naming-template "{artist}/{date} - {album}/{tracknumber}. {title}{ext}"
```

使用可能な変数:

| 変数 | 説明 | 例 |
|---|---|---|
| `{artist}` | アーティスト名 | `T-SQUARE` |
| `{albumartist}` | アルバムアーティスト (空なら artist) | `T-SQUARE` |
| `{album}` | アルバム名 | `Truth` |
| `{title}` | トラックタイトル | `Omens of Love` |
| `{tracknumber}` | トラック番号 (2桁ゼロ埋め) | `01` |
| `{discnumber}` | ディスク番号 | `1` |
| `{genre}` | ジャンル | `Jazz` |
| `{date}` | 年 | `1987` |
| `{ext}` | ファイル拡張子 | `.mp3` |

### スクリプトでの自動実行

```bash
llm-tag-sanitizer /path/to/music --apply --rename --backup -y \
  --log-file sanitizer.log
```

`-y` で確認プロンプトをスキップし、`--log-file` で実行ログを記録する。

## 対応ファイル形式

| 形式 | 拡張子 | タグ規格 |
|---|---|---|
| MP3 | `.mp3` | ID3v2 |
| FLAC | `.flac` | Vorbis Comments |
| OGG Vorbis | `.ogg` | Vorbis Comments |
| AAC/ALAC | `.m4a` | MP4 Atoms |

## 処理の流れ

```
1. SCAN    ─ ディレクトリを再帰スキャンしてタグを読み取り
2. GROUP   ─ アーティスト名・アルバム名で類似トラックをグルーピング
3. ANALYZE ─ 各オプティマイザが LLM にクエリして修正案を生成
4. PLAN    ─ 変更一覧をテーブル表示 (dry-run はここで終了)
5. APPLY   ─ タグを書き込み、必要ならファイルをリネーム
```

## 開発

```bash
# テストの実行
pytest tests/ -v

# カバレッジ付き
pytest tests/ --cov=llm_tag_sanitizer
```

## ライセンス

MIT
