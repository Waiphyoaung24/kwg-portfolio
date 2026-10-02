param([switch]$DryRun, [switch]$ReviewOnly, [switch]$RetentionTrial, [switch]$RetentionReview)
$ErrorActionPreference = 'Stop'
if (([int]$ReviewOnly.IsPresent + [int]$RetentionTrial.IsPresent + [int]$RetentionReview.IsPresent) -gt 1) { throw 'Choose one review or trial route.' }
$taskSourceRoot = $PSScriptRoot
$taskBundle = @{}
$taskNames = @('capture-observer.py', 'review_observer_log.py', 'desktop.sh')
if ($RetentionTrial -or $RetentionReview) { $taskNames += 'retention_supervisor.py' }
foreach ($taskName in $taskNames) {
    $taskPath = Join-Path $taskSourceRoot $taskName
    $taskBytes = [System.IO.File]::ReadAllBytes($taskPath)
    $taskBundle[$taskName] = @{
        data = [Convert]::ToBase64String($taskBytes)
        sha256 = (Get-FileHash -LiteralPath $taskPath -Algorithm SHA256).Hash.ToLowerInvariant()
    }
}
$taskJson = $taskBundle | ConvertTo-Json -Depth 4 -Compress
$taskPayload = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($taskJson))
$taskRemote = @'
import base64, hashlib, json, os, pathlib, subprocess, sys, time, uuid
bundle = json.loads(base64.b64decode("PAYLOAD"))
retention_trial = RETENTION
os.umask(0o077)
def state():
    return subprocess.check_output(['docker','inspect','--format',
        '{{.State.Status}} {{.State.StartedAt}} {{.RestartCount}}','kwg-mt5-desktop'], timeout=10).decode().strip()
before = state()
if not before.startswith('running '):
    raise SystemExit('Trial refused: desktop container is not running.')
launcher = subprocess.check_output(['docker','exec','kwg-mt5-desktop','sha256sum',
    '/opt/trading/desktop.sh'], timeout=10).decode().split()[0]
if launcher != bundle['desktop.sh']['sha256']:
    raise SystemExit('Trial refused: deployed launcher identity differs.')
root = pathlib.Path('/root/kwg-gold-research/evidence')
if not root.is_dir() or root.is_symlink():
    raise SystemExit('Trial refused: expected evidence directory missing or symlinked.')
prefix = 'retention-handoff-' if retention_trial else 'diagnostic-trial-'
run = root / (prefix + time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()) + '-' + uuid.uuid4().hex[:8])
run.mkdir(mode=0o700)
code = run / 'code'
code.mkdir(mode=0o700)
names = ('capture-observer.py','review_observer_log.py') + (('retention_supervisor.py',) if retention_trial else ())
for name in names:
    raw = base64.b64decode(bundle[name]['data'], validate=True)
    if hashlib.sha256(raw).hexdigest() != bundle[name]['sha256']:
        raise SystemExit('Trial refused: source byte identity mismatch.')
    with (code/name).open('xb') as target:
        target.write(raw)
        target.flush()
        os.fsync(target.fileno())
    if hashlib.sha256((code/name).read_bytes()).hexdigest() != bundle[name]['sha256']:
        raise SystemExit('Trial refused: saved source identity mismatch.')
print('Private trial directory:', run, flush=True)
if retention_trial:
    sys.path.insert(0,str(code))
    import retention_supervisor
    result = retention_supervisor.supervise(run/'supervision',110,60,10,1073741824)
    summary = {'mode':'supervised_retention_trial','container_state_unchanged':before==state(),
        'segment_count':len(result['segments']),'blockers':result['blockers'],
        'unique_samples':result['review'].get('unique_samples',0),
        'qualification':result['qualification'],'observed_days':result['observed_days'],
        'model_requests':result['model_requests'],
        'supervisor_receipt_sha256':hashlib.sha256((run/'supervision'/'supervisor.json').read_bytes()).hexdigest()}
    print(json.dumps(summary,sort_keys=True),flush=True)
    raise SystemExit(2 if result['blockers'] or not summary['container_state_unchanged'] else 0)
subprocess.run([sys.executable,'-B',str(code/'capture-observer.py'),'--seconds','60',
    '--output',str(run/'capture')], check=True, timeout=75)
receipt = json.loads((run/'capture'/'receipt.json').read_bytes())
raw = (run/'capture'/'diagnostics.jsonl').read_bytes()
if hashlib.sha256(raw).hexdigest() != receipt['sha256'] or len(raw) != receipt['bytes']:
    raise SystemExit('Trial failed: receipt byte identity mismatch.')
after = state()
print(json.dumps({'container_state_unchanged': before == after,
    'receipt_hash_verified': True, 'stop_reason': receipt['stop_reason'],
    'sample_count': receipt['sample_count'], 'gap_count': receipt['gap_count'],
    'rejected_frame_count': receipt['rejected_frame_count'],
    'trailing_unparsed_bytes': receipt['trailing_unparsed_bytes'],
    'qualification': receipt['qualification'], 'model_requests': receipt['model_requests']}, sort_keys=True))
'@
if ($ReviewOnly) {
    $taskRemote = @'
import base64, collections, datetime, hashlib, json, math, pathlib, stat
bundle = json.loads(base64.b64decode("PAYLOAD"))
run = pathlib.Path('/root/kwg-gold-research/evidence/diagnostic-trial-20261002T083518Z-840efc3b')
expected = '32b15c2054d491e217ebb5322f8e2029719414a8c960e08a5aa5fc2bfdac1b45'
if run.is_symlink() or not run.is_dir():
    raise SystemExit('Review refused: trial directory unavailable or symlinked.')
paths = [run/'capture'/'receipt.json', run/'capture'/'diagnostics.jsonl']
for path, limit in zip(paths, (1024*1024, 64*1024*1024)):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > limit:
        raise SystemExit('Review refused: artifact shape or size invalid.')
receipt = json.loads(paths[0].read_bytes())
raw = paths[1].read_bytes()
if hashlib.sha256(raw).hexdigest() != expected or receipt['sha256'] != expected or receipt['bytes'] != len(raw):
    raise SystemExit('Review failed: diagnostic byte identity differs.')
for name in ('capture-observer.py','review_observer_log.py'):
    path = run/'code'/name
    if path.is_symlink() or not path.is_file():
        raise SystemExit('Review failed: saved source unavailable.')
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != bundle[name]['sha256'] or digest != receipt['code_sha256'][name]:
        raise SystemExit('Review failed: saved source identity differs.')
rows = [json.loads(line) for line in raw.splitlines()]
samples = [row for row in rows if row.get('kind') == 'sample']
stamps = [row['health']['sampled_at'] for row in samples]
received = [row['received_at'] for row in samples]
if not all(type(t) in (int,float) and math.isfinite(t) for t in stamps+received):
    raise SystemExit('Review failed: sample timestamps invalid.')
gaps = sum(b <= a or b-a > 30 for a,b in zip(stamps, stamps[1:]))
rejects = sum(row.get('kind') == 'rejected_frame' for row in rows)
if len(samples) != receipt['sample_count'] or gaps != receipt['gap_count'] or rejects != receipt['rejected_frame_count']:
    raise SystemExit('Review failed: receipt counts differ from actual rows.')
if (receipt['qualification'] != 'unqualified' or receipt['completeness_verified'] is not False
        or receipt['promotion_status'] != 'blocked'
        or type(receipt['model_requests']) is not int or receipt['model_requests'] != 0
        or type(receipt['observed_days']) is not int or receipt['observed_days'] != 0):
    raise SystemExit('Review failed: evidence boundary differs.')
utc = lambda t: datetime.datetime.fromtimestamp(t, datetime.timezone.utc).isoformat()
print(json.dumps({'mode':'read_only_receipt_review','bytes_verified':True,'source_hashes_verified':True,
    'receipt_sha256':hashlib.sha256(paths[0].read_bytes()).hexdigest(),
    'elapsed_seconds':receipt['ended_at']-receipt['started_at'],
    'start_utc':utc(receipt['started_at']),'end_utc':utc(receipt['ended_at']),
    'first_sample_utc':utc(stamps[0]) if stamps else None,
    'last_sample_utc':utc(stamps[-1]) if stamps else None,
    'max_sample_interval_seconds':max((b-a for a,b in zip(stamps,stamps[1:])),default=None),
    'max_receive_lag_seconds':max((r-s for r,s in zip(received,stamps)),default=None),
    'sample_count':len(samples),'gap_count':gaps,'rejected_frame_count':rejects,
    'status_counts':dict(collections.Counter(row['status'] for row in samples)),
    'quote_counts':dict(collections.Counter(row['health'].get('quote','unknown') for row in samples)),
    'artifact_permissions_private':all(stat.S_IMODE(p.stat().st_mode)==0o600 and p.stat().st_uid==0 for p in paths),
    'stop_reason':receipt['stop_reason'],'trailing_unparsed_bytes':receipt['trailing_unparsed_bytes'],
    'qualification':'unqualified','observed_days':0,'model_requests':0},sort_keys=True,allow_nan=False))
'@
}
if ($RetentionReview) {
    $taskRemote = @'
import base64, datetime, hashlib, json, pathlib, stat, types
bundle = json.loads(base64.b64decode("PAYLOAD"))
trials = [['/root/kwg-gold-research/evidence/retention-handoff-20261002T092809Z-d1e5fda8', 'e9f299d55b5c81f6d47456cac44a3a799c066bc946947277bd7e479eb1da7636'], ['/root/kwg-gold-research/evidence/retention-handoff-20261002T093048Z-df5db154', '6bb0dc77240f6e125c7e185f193147d034828b12d9b9960cb2646ee633c53772']]
attempts = []
for directory, expected in trials:
    run = pathlib.Path(directory)
    root = run/'supervision'
    code = run/'code'
    paths = [run, root, code, root/'supervisor.json']
    for path in paths:
        if path.is_symlink() or not path.exists():
            print(json.dumps({'mode':'read_only_retention_path_check','attempt':run.name,
                'required_paths':[{'relative':str(p.relative_to(run)),'exists':p.exists(),
                    'symlink':p.is_symlink()} for p in paths]},sort_keys=True))
            raise SystemExit('Review refused: saved path unavailable or symlinked.')
    def read(path, limit):
        if path.is_symlink() or not path.is_file():
            raise SystemExit('Review refused: artifact shape invalid.')
        with path.open('rb') as source:
            raw = source.read(limit+1)
        if len(raw) > limit:
            raise SystemExit('Review refused: artifact limit.')
        return raw
    sources = {}
    for name in ('capture-observer.py','review_observer_log.py','retention_supervisor.py'):
        path = code/name
        sources[name] = read(path,1024*1024)
        if hashlib.sha256(sources[name]).hexdigest() != bundle[name]['sha256']:
            raise SystemExit('Review failed: saved source identity differs.')
        paths.append(path)
    # Execute only the reviewed, hash-matched module; no import cache writes.
    module = types.ModuleType('saved_retention_review')
    module.__file__ = str(code/'retention_supervisor.py')
    exec(compile(sources['retention_supervisor.py'],module.__file__,'exec'),module.__dict__)
    raw = read(root/'supervisor.json',1024*1024)
    if hashlib.sha256(raw).hexdigest() != expected:
        raise SystemExit('Review failed: pinned supervisor receipt differs.')
    receipt = module.load(raw)
    if (receipt['mode'] != 'bounded_supervision' or receipt['evidence_mode'] != 'docker_follow'
            or receipt['code_sha256'] != module.source_hashes()
            or receipt['supervisor_sha256'] != bundle['retention_supervisor.py']['sha256']
            or receipt['qualification'] != 'unqualified' or receipt['promotion_status'] != 'blocked'
            or any(type(receipt[k]) is not int or receipt[k] != 0 for k in ('observed_days','model_requests'))):
        raise SystemExit('Review failed: supervisor evidence boundary differs.')
    folders = [root/'segment-00',root/'segment-01']
    if receipt['segments'] != [str(f) for f in folders]:
        raise SystemExit('Review failed: trial segment identities differ.')
    for folder in folders:
        if folder.is_symlink() or not folder.is_dir():
            raise SystemExit('Review refused: segment directory invalid.')
        for path in (folder/'receipt.json',folder/'diagnostics.jsonl'):
            if path.is_symlink() or not path.is_file():
                raise SystemExit('Review refused: artifact shape invalid.')
        paths.extend([folder,folder/'receipt.json',folder/'diagnostics.jsonl'])
    checked = module.review(folders,receipt['started_at'],receipt['ended_at'])
    if module.encode(checked) != module.encode(receipt['review']) or checked['blockers'] or receipt['blockers']:
        raise SystemExit('Review failed: actual segment reconciliation differs or has blockers.')
    private = all(not p.is_symlink() and p.stat().st_uid == 0 and
        stat.S_IMODE(p.stat().st_mode) == (0o700 if p.is_dir() else 0o600) for p in paths)
    utc = lambda t: datetime.datetime.fromtimestamp(t,datetime.timezone.utc).isoformat()
    attempts.append({'directory':str(run),'receipt_sha256':expected,
        'start_utc':utc(receipt['started_at']),'end_utc':utc(receipt['ended_at']),
        'elapsed_seconds':receipt['ended_at']-receipt['started_at'],
        'source_hashes_verified':True,'bytes_verified':True,'artifact_permissions_private':private,
        'segment_count':len(folders),'unique_samples':checked['unique_samples'],
        'blockers':checked['blockers'],'qualification':'unqualified','observed_days':0,'model_requests':0})
print(json.dumps({'mode':'read_only_retention_review','attempts':attempts},sort_keys=True,allow_nan=False))
if not all(a['artifact_permissions_private'] for a in attempts):
    raise SystemExit('Review failed: private artifact permissions differ.')
'@
}
$taskRemote = $taskRemote.Replace('PAYLOAD', $taskPayload)
$taskRemote = $taskRemote.Replace('RETENTION', $(if ($RetentionTrial) { 'True' } else { 'False' }))
if ($DryRun) {
    $taskRemote | python -B -c 'import sys; compile(sys.stdin.read(), sys.argv[1], sys.argv[2])' diagnostic-trial exec
    if ($LASTEXITCODE -eq 0) {
        Write-Output 'PASS: transfer script compiles; no SSH or remote capture started.'
    }
} else {
    $taskRemote | ssh -o ConnectTimeout=8 -o ServerAliveInterval=15 -o ServerAliveCountMax=2 root@187.52.117.116 python3 -
}
if ($LASTEXITCODE -ne 0) {
    throw 'Diagnostic trial failed. Preserve any partial remote directory; do not restart MT5.'
}
