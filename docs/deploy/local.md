# 本地部署运行

::: warning 警告
本地部署可能会产生一些不可预料的问题，我们强烈推荐您使用 Docker 部署。

本地文档更新可能会有延迟，如有疑问请先在 [ISSUE](https://github.com/EstrellaXD/Auto_Bangumi/issues) 中提出。
:::

## 下载最新版本文件

```bash
VERSION=$(curl -s "https://api.github.com/repos/EstrellaXD/Auto_Bangumi/releases/latest" | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/')
curl -L -O "https://github.com/EstrellaXD/Auto_Bangumi/releases/download/$VERSION/app-v$VERSION.zip"
```

## 解压代码压缩包

Unix 与 WSL 系统可以使用如下命令，Windows 系统请自行解压。

```bash
unzip app-v$VERSION.zip -d AutoBangumi
cd AutoBangumi
```


## 创建虚拟环境并且安装依赖
确认你的电脑本地已经安装了 `python3.10` 以上的版本，以及 `pip` 包管理工具。

```bash
cd src
python3 -m venv env
python3 pip install -r requirements.txt
```

## 创建配置和数据文件夹

```bash
mkdir config
mkdir data
```

## 运行 AutoBangumi

```bash
python3 main.py
```


## Windows 开机自启

可以用 `nssm` 来实现开机自启，以下以 `nssm` 为例：

```powershell
nssm install AutoBangumi (Get-Command python).Source
nssm set AutoBangumi AppParameters (Get-Item .\main.py).FullName
nssm set AutoBangumi AppDirectory (Get-Item ..).FullName
nssm set AutoBangumi Start SERVICE_DELAYED_AUTO_START
```
