#!/bin/bash

sh ./getWebUI.sh

exec python3 app.py &
exec python3 api.py
