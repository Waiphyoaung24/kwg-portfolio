"""Pinned trend-stage cutover using the verified M1 backup/stop/migrate workflow."""
from pathlib import Path
import runpy
import sys


def main():
    if sys.argv[1:] != ['--enable-demo-execution']:
        raise SystemExit('Explicit --enable-demo-execution is required; deploy the matching dashboard and Worker first')
    cutover = runpy.run_path(str(Path(__file__).with_name('cutover-m1-pilot.py')))
    tag = 'kwg-mt5-desktop:trend-20261009'
    image = cutover['run'](['docker', 'image', 'inspect', tag, '--format', '{{.Id}}'])
    # The shared cutover verifies the image's source hashes before stopping anything.
    cutover['main'].__globals__.update(
        STAGE=cutover['ROOT'] / 'm1-review-20261009T141607Z-69e01b51',
        CODE='c1a2c965fc1bba6c7834d25c1977e79418208491874d9c7e6509c56e94da165b',
        OLD_CODE='2495766af1cda52e60ac7b9c7fd3e0e2bb34f49c69323723c2add0a09653c19e',
        OLD_IMAGE='sha256:d43ae354f76bbfb2e3a4e2c39edff8bfd1e7deabd55be95873ea19c3e4d06cfe',
        IMAGE=image, IMAGE_TAG=tag, TARGET_STRATEGY='gold-ema-v1-m1-trend-3',
        MIGRATION_FLAGS=' --trend')
    cutover['main']()


if __name__ == '__main__':
    try:
        main()
    except Exception:
        print('CUTOVER_INCOMPLETE: preserve backups; do not rerun or resume the old supervisor blindly', flush=True)
        raise
