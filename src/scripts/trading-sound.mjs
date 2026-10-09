// A fresh page/reconnection establishes a baseline; polling must not replay old entries.
export function entryNotifications() {
  let baseline = false;
  let latestOpened = 0;
  return (report, now, visible = true) => {
    if (!visible || !report || report.mode !== 'autonomous-demo' ||
        report.symbol !== 'XAUUSD-VIP' || !Number.isFinite(report.checked_at) ||
        now - report.checked_at < 0 || now - report.checked_at > 30) {
      baseline = false;
      return false;
    }
    const execution = report.execution;
    const opened = execution?.opened_at;
    const filled = ['open', 'closed'].includes(execution?.status) &&
      Number.isFinite(opened) && opened > 0 && opened <= report.checked_at &&
      Number.isFinite(execution.updated_at) && now - execution.updated_at >= 0 &&
      now - execution.updated_at <= 30;
    const notify = baseline && filled && opened > latestOpened;
    if (filled) latestOpened = Math.max(latestOpened, opened);
    baseline = true;
    return notify;
  };
}
