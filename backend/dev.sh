#!/usr/bin/env bash

# This script is used to run the development environment.

python3 -m venv venv

./venv/bin/python3 -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements-dev.txt

# install git-hooks for pre-commit before committing.
./venv/bin/pre-commit install

cd src || exit

CONFIG_DIR="config"

if [ ! -d "$CONFIG_DIR" ]; then
	echo "The directory '$CONFIG_DIR' is missing."
	mkdir config
fi

VERSION_FILE="module/__version__.py"

if [ ! -f "$VERSION_FILE" ]; then
	echo "The file '$VERSION_FILE' is missing."
	echo "VERSION='DEV_VERSION'" >>"$VERSION_FILE"
fi

../venv/bin/uvicorn main:app --reload --port 7892 --host 0.0.0.0
