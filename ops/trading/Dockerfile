FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive WINEDEBUG=-all WINEARCH=win64 \
    DISPLAY=:99 WINEPREFIX=/home/mt5/.wine
RUN apt-get update -qq && apt-get install -y --no-install-recommends \
    wine wine64 xvfb xauth x11-utils openbox x11vnc novnc websockify \
    curl unzip ca-certificates fonts-liberation xterm \
    && useradd --create-home --uid 10001 mt5 \
    && mkdir -p /opt/python /opt/trading /opt/status \
    && curl -fL --retry 2 https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip -o /tmp/python.zip \
    && unzip -q /tmp/python.zip -d /opt/python \
    && sed -i 's/^#import site/import site/' /opt/python/python312._pth \
    && echo '../trading' >> /opt/python/python312._pth \
    && curl -fL --retry 2 https://bootstrap.pypa.io/get-pip.py -o /opt/python/get-pip.py \
    && curl -fL --retry 2 https://download.mql5.com/cdn/web/metaquotes.software.corp/mt5/mt5setup.exe -o /opt/trading/mt5setup.exe \
    && chown -R mt5:mt5 /opt/python /opt/status
COPY desktop.sh verify-demo.py mt5_data.py gold_signal.py gold_qualification.py observe-gold.py export-gold.py demo_one_shot.py /opt/trading/
USER mt5
WORKDIR /home/mt5
RUN xvfb-run -a script -q -e -c "bash -ec '\
    timeout 60s wineboot -u; \
    timeout 60s wineserver -w; \
    timeout 120s wine /opt/python/python.exe /opt/python/get-pip.py --disable-pip-version-check; \
    timeout 120s wine /opt/python/python.exe -m pip install --disable-pip-version-check MetaTrader5==5.0.6180 numpy==1.26.4; \
    timeout 30s wine /opt/python/python.exe -c \"import MetaTrader5; print(MetaTrader5.__version__)\"'" /dev/null
CMD ["bash", "/opt/trading/desktop.sh"]
