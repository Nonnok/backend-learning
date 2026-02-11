# Markdown to HTML Converter
コマンドライン引数を使用して、マークダウンファイルをHTMLファイルに変換するプログラムです。

### 学習したこと
- ファイル操作
- コマンドライン引数の取得：`sys.argv`
- 外部ライブラリの導入と利用
- エラーでのプログラム終了操作：`sys.exit(1)`

## 機能
ユーザーは、コマンド`python3 file-converter.py markdown inputfile outputfile`を実行することで、マークダウンファイル（inputfile）をHTMLファイルに変換してoutputファイルに出力することができます。

## 工夫
- ファイルの読み込み処理・書き込み処理、処理の判別、ファイル形式の変換を関数化しました。
- ユーザーが正しい入力を理解しやすいように、都度、標準出力で案内を表示するようにしました。

## 実行方法
```
python3 file-converter.py markdown inputfile outputfile
```

## 動作環境
- Python 3.x
- ターミナル
