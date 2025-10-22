> [!IMPORTANT]
> このプロジェクトは現在開発中となります。

# VRCEventManager
このプロジェクトは、WebからVRChat上で行われるイベントを管理することを目的としたオープンソースプロジェクトです。

# Features (ToDo)
- [ ] Web Frontend
- [ ] API Backend
  - [x] Discord Login
  - [x] Discord Server Management
  - [ ] VRChat Group Management
  - [ ] X Tweet Management
  - [ ] WonderNote Auto Post

# Installation
### 前提要件
* Docker環境
* エディタ環境
* Git環境

#### プロジェクトをダウンロード
```bash
git clone https://github.com/haruyq/VRCEventManager.git
cd VRCEventManager
```

#### 設定ファイルの作成
```bash
vim apiconf.env
vim botconf.env
```
##### *設定ファイルは以下の内容を含む必要があります。
```env
# apiconf.env
BOT_SOCK_ADDRESS=bot               # Bot側ソケットのアドレス
BOT_SOCK_PORT=50000                # Bot側ソケットのポート
GUILD_ID=YOUR_GUILD_ID             # サーバーID
CHANNEL_ID=YOUR_CHANNEL_ID         # チャンネルID(任意)
CLIENT_ID=YOUR_CLIENT_ID           # Client Id
CLIENT_SECRET=YOUR_CLIENT_SECRET   # Client Secret
REDIRECT_URL=YOUR_REDIRECT_URL     # リダイレクト先のリンク(/api/login/callback)
FRONTEND_URL=http://localhost:4321 # フロントエンドのURL
DOMAIN=example.com                 # 使用するドメイン
JWT_SECRET=YOUR_SECRET_PASSWORD    # JWTのSECRETキー生成に使用するパスワード

# botconf.env
BOT_TOKEN=YOUR_BOT_TOKEN # Botの認証トークン
RECEIVER_ADDRESS=0.0.0.0 # ソケットのアドレス
RECEIVER_PORT=50000      # ソケットのポート
```

#### 実行
```bash
docker compose build
docker compose up
```

# Contact
お問い合わせなどがある場合は、下記の連絡先までご連絡ください。  
* [X(旧Twitter)](https://x.com/haruwaiku)
* [メールアドレス](mailto:haruwaiku@gmail.com)

# License
このプロジェクトはMIT Licenseで公開されています。  
