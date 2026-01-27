# ローカルデプロイ

::: warning
ローカルデプロイは予期しない問題を引き起こす可能性があります。代わりにDockerの使用を強く推奨します。

このドキュメントには更新の遅れがある可能性があります。質問がある場合は、[Issues](https://github.com/EstrellaXD/Auto_Bangumi/issues)で提起してください。
:::

## 最新リリースのダウンロード

```bash
VERSION=$(curl -s "https://api.github.com/repos/EstrellaXD/Auto_Bangumi/releases/latest" | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/')
curl -L -O "https://github.com/EstrellaXD/Auto_Bangumi/releases/download/$VERSION/app-v$VERSION.zip"
```

## アーカイブの展開

Unix/WSLシステムでは、以下のコマンドを使用します。Windowsでは手動で展開してください。

```bash
unzip app-v$VERSION.zip -d AutoBangumi
cd AutoBangumi
```


## 仮想環境の作成と依存関係のインストール

ローカルにPython 3.10以上とpipがインストールされていることを確認してください。

```bash
cd src
python3 -m venv env
python3 pip install -r requirements.txt
```

## 設定とデータディレクトリの作成

```bash
mkdir config
mkdir data
```

## AutoBangumiの実行

```bash
python3 main.py
```


## Windows起動時の自動起動

`nssm`を使用して起動時の自動起動を設定できます。`nssm`を使用した例：

```powershell
nssm install AutoBangumi (Get-Command python).Source
nssm set AutoBangumi AppParameters (Get-Item .\main.py).FullName
nssm set AutoBangumi AppDirectory (Get-Item ..).FullName
nssm set AutoBangumi Start SERVICE_DELAYED_AUTO_START
```
