#!/bin/bash

sh ./getWebUI.sh

sh ./setID.sh

su-exec auto_bangumi:auto_bangumi python3 app.py &
su-exec auto_bangumi:auto_bangumi python3 api.py