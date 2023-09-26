# 如何在本地运行 AutoBangumi

## 克隆项目

```bash
git clone https://github.com/EstrellaXD/Auto_Bangumi.git
```

## 安装依赖
确认你的电脑本地已经安装了 `python3.10` 以上的版本，以及 `pip` 包管理工具。

```bash
python3 pip install -r requirements.txt
```

## 进入源代码目录并且创建版本信息

```bash
cd backend/src

echo "VERSION = 'local'" > module/__version__.py
```

## 下载 WebUI

```bash
wget https://github.com/EstrellaXD/Auto_Bangumi/releases/download/latest/dist.zip

unzip dist.zip

mv dist templates
```

## 创建配置文件夹以及数据文件夹并运行

```bash
mkdir "config"
mkdir "data"

python3 main.py
```
