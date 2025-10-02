> [!IMPORTANT]
> このプロジェクトは現在開発中となります。

# VRCEventManager
このプロジェクトは、WebからVRChat上で行われるイベントを管理することを目的としたオープンソースプロジェクトです。

# Features (ToDo)
- [ ] Web Frontend
- [ ] API Backend
  - [ ] Discord Server Management **<- Now**
  - [ ] VRChat Group Management **<- Next**
  - [ ] X Tweet Management
  - [ ] WonderNote Auto Post

# Installatiion
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
apiconf.env
```env
BOT_SOCK_ADDRESS=bot # Bot側で動作するソケットのアドレス
BOT_SOCK_PORT=50000 # Bot側で動作するソケットのポート
GUILD_ID=YOUR_GUILD_ID # DiscordサーバーのID
CHANNEL_ID=YOUR_CHANNEL_ID # チャンネルID(任意)、未使用
```
botconf.env
```env
BOT_TOKEN=YOUR_BOT_TOKEN # DiscordBotの認証情報
RECEIVER_ADDRESS=0.0.0.0 # ソケットの動作アドレス
RECEIVER_PORT=50000 # ソケットの動作ポート
```

#### 実行
```bash
docker compose build
docker compose up
```

# License
このプロジェクトはMIT Licenseで公開されています。  
お問い合わせなどがある場合は、下記の連絡先までご連絡ください。  
* [X(旧Twitter)](https://x.com/haruwaiku)
* [メールアドレス](mailto:haruwaiku@gmail.com)
