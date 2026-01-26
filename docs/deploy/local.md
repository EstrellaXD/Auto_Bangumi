# Local Deployment

::: warning
Local deployment may cause unexpected issues. We strongly recommend using Docker instead.

This documentation may have update delays. If you have questions, please raise them in [Issues](https://github.com/EstrellaXD/Auto_Bangumi/issues).
:::

## Download the Latest Release

```bash
VERSION=$(curl -s "https://api.github.com/repos/EstrellaXD/Auto_Bangumi/releases/latest" | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/')
curl -L -O "https://github.com/EstrellaXD/Auto_Bangumi/releases/download/$VERSION/app-v$VERSION.zip"
```

## Extract the Archive

On Unix/WSL systems, use the following command. On Windows, extract manually.

```bash
unzip app-v$VERSION.zip -d AutoBangumi
cd AutoBangumi
```


## Create Virtual Environment and Install Dependencies

Ensure you have Python 3.10+ and pip installed locally.

```bash
cd src
python3 -m venv env
python3 pip install -r requirements.txt
```

## Create Configuration and Data Directories

```bash
mkdir config
mkdir data
```

## Run AutoBangumi

```bash
python3 main.py
```


## Windows Auto-Start on Boot

You can use `nssm` for auto-start on boot. Example with `nssm`:

```powershell
nssm install AutoBangumi (Get-Command python).Source
nssm set AutoBangumi AppParameters (Get-Item .\main.py).FullName
nssm set AutoBangumi AppDirectory (Get-Item ..).FullName
nssm set AutoBangumi Start SERVICE_DELAYED_AUTO_START
```
