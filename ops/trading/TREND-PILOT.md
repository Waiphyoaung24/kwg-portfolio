# M1 trend demo release

Owner-selected behavior: EMA20 above EMA50 buys; below sells, with the existing
three-bar EMA20 slope confirmation. Evaluate only new completed M1 candles.
After each broker-confirmed close, wait 300 seconds before another entry.
One 0.01-lot position, protected stops/targets, loss limits and original expiry
remain unchanged. Spread must still be at most 10% of ATR14. No entry is promised.

Reviewed VPS stage: `/opt/kwg-mt5-qualification/m1-review-20261009T141607Z-69e01b51`.
Code: `c1a2c965fc1bba6c7834d25c1977e79418208491874d9c7e6509c56e94da165b`.
Review passed with an ATR/spread entry block; no orders sent. Current M1 crossover
code is `2495766af1cda52e60ac7b9c7fd3e0e2bb34f49c69323723c2add0a09653c19e`.

Deploy the matching portfolio and trading Worker before switching. If the
research MCP Worker is used, deploy it too: it shares the pilot validator.
Keep the current runner running until the cutover script stops it.

Upload the two cutover files from normal PowerShell:

```powershell
scp C:\Users\wai19\Desktop\kwg-portfolio\ops\trading\cutover-m1-pilot.py C:\Users\wai19\Desktop\kwg-portfolio\ops\trading\cutover-trend-pilot.py root@187.52.117.116:/root/
```

Build the reviewed stage on the VPS:

```bash
stage=/opt/kwg-mt5-qualification/m1-review-20261009T141607Z-69e01b51
docker tag sha256:d43ae354f76bbfb2e3a4e2c39edff8bfd1e7deabd55be95873ea19c3e4d06cfe kwg-mt5-desktop:rollback-before-trend-20261009
printf '%s\n' \
  'FROM kwg-mt5-desktop:rollback-before-trend-20261009' \
  'COPY --chmod=0644 demo_pilot.py demo_one_shot.py mt5_data.py gold_signal.py gold_experiment.py /opt/trading/' \
  > "$stage/Dockerfile"
docker build --pull=false --network=none -t kwg-mt5-desktop:trend-20261009 "$stage"
```

After confirming the matching UI/Worker deployment, run once:

```bash
python3 -B /root/cutover-trend-pilot.py --enable-demo-execution
```

The cutover verifies the old image and staged source hashes, saves deployment
and SQLite backups, stops the exact runner and restart supervisor, requires a
flat account, migrates the journal under the execution lock, and recreates the
containers. It preserves expiry `1792096151`. A failure after stopping the runner
requires inspection; do not blindly rerun or resume the old supervisor against a
migrated journal. Never restore a pre-trade journal over newer broker activity.

Verify the final receipt reports `gold-ema-v1-m1-trend-3`, a current timestamp,
the original expiry, and the actual pilot/entry state. A blocked spread condition
is still possible. Confirm any subsequent order against MT5 Trade/History.
