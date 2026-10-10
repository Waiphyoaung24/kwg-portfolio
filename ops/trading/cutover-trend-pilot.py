"""Pinned trend-stage cutover using the verified M1 backup/stop/migrate workflow."""
from pathlib import Path
import runpy
import sys


def main():
    if sys.argv[1:] != ['--enable-demo-execution']:
        raise SystemExit('Explicit --enable-demo-execution is required for the reviewed 25% spread upgrade')
    cutover = runpy.run_path(str(Path(__file__).with_name('cutover-m1-pilot.py')))
    tag = 'kwg-mt5-desktop:trend-spread25-20261009'
    image = cutover['run'](['docker', 'image', 'inspect', tag, '--format', '{{.Id}}'])
    previous = cutover['run'](['docker', 'image', 'inspect', 'kwg-mt5-desktop:trend-20261009', '--format', '{{.Id}}'])
    # The shared cutover verifies the image's source hashes before stopping anything.
    cutover['main'].__globals__.update(
        STAGE=cutover['ROOT'] / 'm1-review-20261009T175402Z-58626dae',
        CODE='4e00c3fa04b2f130a26fc46f754b1380e2a4891c5b23eba3b2c56f71ef955eb1',
        OLD_CODE='6f34c5f608156bb367a9c0c4938ef85741121c9cf440c16953af7b4f3e98cc34',
        OLD_IMAGE=previous,
        IMAGE=image, IMAGE_TAG=tag, TARGET_STRATEGY='gold-ema-v1-m1-trend-3',
        MIGRATION_FLAGS=' --trend --spread-upgrade')
    cutover['main']()


if __name__ == '__main__':
    try:
        main()
    except Exception:
        print('CUTOVER_INCOMPLETE: preserve backups; do not rerun or resume the old supervisor blindly', flush=True)
        raise
