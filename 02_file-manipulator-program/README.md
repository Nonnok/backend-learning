# File Manipulator Program
OSとやり取りしてファイルシステムを操作するプログラムです。Pythonでのファイル操作の理解を目的として作成しました。

### 学習したこと
- コマンドライン引数の取得：`sys.argv`
- 文字列操作
- ファイルの読み込み・書き込み<br>
  withキーワードを使用したコードブロックでの記述方法（ブロックの実行が終了するとファイルが自動的に閉じられるため安全）
  ```
  open( filepath, 'mode' ) as file:
    file.write( contents )
  ```
- エラーでのプログラム終了：`sys.exit(1)`

## 機能
ユーザーはコマンドを指定し、以下のファイル操作を行うことができます。<br>
（RecursionCSから引用）
- `reverse input path`：<br>
  inputpathにあるファイルを受け取り、outputpath に inputpath の内容を逆にした新しいファイルを作成します。
- `copy inputpath outputpath`：<br>
  inputpath にあるファイルのコピーを作成し、outputpath として保存します。
- `duplicate-contents inputpath n`：<br>
  inputpath にあるファイルの内容を読み込み、その内容を複製し、複製された内容を inputpath に n 回複製します。
- `replace-string inputpath needle newstring`：<br>
  inputpath にあるファイルの内容から文字列 'needle' を検索し、'needle' の全てを 'newstring' に置き換えます。


## 工夫
- 共通処理を関数化しました。
- ユーザーが正しい入力を理解しやすいように、都度、標準出力で案内を表示するようにしました。

## 実行方法
```
# reverse
python3 file-manipulator.py reverse inputpath outputpath

# copy
python3 file-manipulator.py copy inputpath outputpath

# duplicate-contents
python3 file-manipulator.py duplicate-contents inputpath n

# replace-string
python3 file-manipulator.py replace-string inputpath needle newstring
```

## 動作環境
- Python 3.10以上
- ターミナル