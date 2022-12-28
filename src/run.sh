#!/bin/bash

sh ./getWebUI.sh

sh ./setID.sh

umask ${UMASK}
exec su-exec auto_bangumi:auto_bangumi python3 app.py &
exec su-exec auto_bangumi:auto_bangumi python3 api.py
