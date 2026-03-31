# Video compressor service
サーバ操作の基本を身につけるために、Pythonのsocketモジュールを用いて実装したクライアント・サーバ型アプリケーションです。

### 学習したこと
- クライアント・サーバモデルの基本構造
- socket通信の基本（[TCP] bind → listen → accept → recv / send, [UDP] recvfrom / sendto ）
- `uuid`を用いた重複しないIDの生成
- 外部ライブラリの導入と利用
- カスタムプロトコルの実装

## 機能
このシステムはCLIで動作します。
クライアントは1TB以内の動画ファイルに対して、以下の処理を行うことができます。
- 圧縮
- リサイズ
- アスペクト比変更
- mp3変換
- 指定の時間範囲でGIF・WEBM化

## 工夫
- クライアントが望ましい値を入力できるまで、入力に再挑戦できるようにしました。

## 実行方法
1. サーバの起動
```
python3 server.py
```

2. 別ターミナルでクライアントを起動
```
python3 client.py
```

3. 処理を選んで入力する。

4. `Control` + `C` の割り込みで終了することができます。

## 動作環境
- Python 3.10以降
- ターミナル

## 使用技術
- Python
- socket（AF_INET）
- threading
- subprocess
