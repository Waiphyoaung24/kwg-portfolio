# M1 trend demo release

## Pending 25% spread update

The owner approved a 25% ATR14 spread ceiling for the M1 trend demo. Local code
and boundary tests use 25%; the deployed 15% code below remains unchanged until
a new reviewed cutover. Size, stop/target, cooldown, loss limits and expiry remain
unchanged. No guaranteed minimum profit or new profit target is introduced.
VPS review passed for `m1-review-20261009T175402Z-58626dae`, code
`4e00c3fa04b2f130a26fc46f754b1380e2a4891c5b23eba3b2c56f71ef955eb1`.
`cutover-trend-pilot.py` now pins that stage, uses image tag
`kwg-mt5-desktop:trend-spread25-20261009`, and requires the previous trend image
and 15% journal identity. Three cutover tests passed; remote cutover is pending.
Stage with `stage-m1-pilot.ps1 -Trend -SpreadUpgrade`. This verifies the deployed
15% journal identity and reviews the new code without placing orders. Do not run
the historical cutover commands below for this update: they pin the older stage.

## Previous 15% deployment

Owner-selected behavior: EMA20 above EMA50 buys; below sells, with the existing
three-bar EMA20 slope confirmation. Evaluate only new completed M1 candles.
After each broker-confirmed close, wait 300 seconds before another entry.
One 0.01-lot position, protected stops/targets, loss limits and original expiry
remain unchanged. The trend demo allows spread at most 15% of ATR14; crossover modes retain 10%. No entry is promised.

Reviewed 15% VPS stage: `/opt/kwg-mt5-qualification/m1-review-20261009T145700Z-4aa81f9b`.
Previous code: `c1a2c965fc1bba6c7834d25c1977e79418208491874d9c7e6509c56e94da165b`.
Approved 15% code: `6f34c5f608156bb367a9c0c4938ef85741121c9cf440c16953af7b4f3e98cc34`; VPS review passed without orders.
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
stage=/opt/kwg-mt5-qualification/m1-review-20261009T145700Z-4aa81f9b
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
