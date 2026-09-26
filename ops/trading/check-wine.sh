#!/usr/bin/env bash
# Credential-free SDK smoke test; no ports, host mounts, or broker connection.
set -euo pipefail
docker run -dt --name kwg-mt5-probe --cpus=1 --memory=2g --pids-limit=512 \
  --security-opt=no-new-privileges --log-opt max-size=2m \
  ubuntu:24.04 bash -lc '
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive WINEDEBUG=-all WINEARCH=win64
apt-get update -qq
apt-get install -y --no-install-recommends wine wine64 xvfb xauth curl unzip ca-certificates
mkdir -p /opt/python
curl --fail --location --retry 2 https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip -o /tmp/python.zip
unzip -q /tmp/python.zip -d /opt/python
sed -i "s/^#import site/import site/" /opt/python/python312._pth
curl --fail --location --retry 2 https://bootstrap.pypa.io/get-pip.py -o /opt/python/get-pip.py
cat > /opt/python/probe.py << "PY"
import platform
import MetaTrader5 as mt5
assert platform.system() == "Windows"
print("SDK_IMPORT_OK", mt5.__version__, platform.python_version())
PY
xvfb-run -a bash -c "
  set -e
  timeout 60s wineboot -u
  timeout 60s wineserver -w
  timeout 120s wine /opt/python/python.exe /opt/python/get-pip.py --disable-pip-version-check
  # Wine 9 lacks ucrtbase.crealf used by NumPy 2.5.3.
  timeout 120s wine /opt/python/python.exe -m pip install --disable-pip-version-check MetaTrader5==5.0.6180 numpy==1.26.4
  timeout 30s wine /opt/python/python.exe /opt/python/probe.py
"
'
