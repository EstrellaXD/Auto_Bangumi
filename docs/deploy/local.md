# 本地部署

::: warning
本地部署可能会导致意外问题。我们强烈建议使用 Docker 代替。

此文档可能存在更新延迟。如有问题，请在 [Issues](https://github.com/EstrellaXD/Auto_Bangumi/issues) 中提出。
:::

## 下载最新版本

```bash
VERSION=$(curl -s "https://api.github.com/repos/EstrellaXD/Auto_Bangumi/releases/latest" | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/')
curl -L -O "https://github.com/EstrellaXD/Auto_Bangumi/releases/download/$VERSION/app-v$VERSION.zip"
```

## 解压压缩包

在 Unix/WSL 系统上，使用以下命令。在 Windows 上，请手动解压。

```bash
unzip app-v$VERSION.zip -d AutoBangumi
cd AutoBangumi
```


## 创建虚拟环境并安装依赖

确保本地已安装 Python 3.10+ 和 pip。

```bash
cd src
python3 -m venv env
python3 pip install -r requirements.txt
```

## 创建配置和数据目录

```bash
mkdir config
mkdir data
```

## 运行 AutoBangumi

```bash
python3 main.py
```


## Windows 开机自启

可以使用 `nssm` 实现开机自启。使用 `nssm` 的示例：

```powershell
nssm install AutoBangumi (Get-Command python).Source
nssm set AutoBangumi AppParameters (Get-Item .\main.py).FullName
nssm set AutoBangumi AppDirectory (Get-Item ..).FullName
nssm set AutoBangumi Start SERVICE_DELAYED_AUTO_START
```
