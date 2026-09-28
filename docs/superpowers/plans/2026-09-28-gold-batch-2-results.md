# Batch 2 implementation state

The offline simulator now accepts fixed timestamp windows and a dated,
historically covered cost profile. The previous hypothetical scenarios remain
available. The daily entry pause uses the previous sampled equity when a new
UTC day begins, preserving adverse overnight gaps. An offline evaluator and
draft policy contain candidate gates and a deterministic paired bootstrap.
All of this remains diagnostic; the draft policy cannot make a candidate
eligible for shadow observation.

Local checks: 36 Python tests passed on 2026-09-28. The original frozen
dataset is private on the VPS, so a new baseline rerun was not completed from
this workspace. Actual historical commission/swap coverage, fresh Batch 1
data, an approved prospective policy, a registered candidate and sufficient
validation observations are all missing. State: **prepared_but_blocked**.
Prior baseline losses and 30–31 validation trades remain the only observed
results; they do not satisfy the proposed 100-trade gate. No Vibe-Trading job,
candidate selection, shadow promotion or orders were started.

The 2026-09-28 live verifier showed both tick and bar raw timestamps roughly
three hours ahead of synchronized VPS UTC. The frozen historical dataset
retains raw MT5 epochs and is explicitly unqualified; calendar-day funding,
daily-pause and date labels must not be interpreted as broker-accurate until
the timestamp basis is established. The old hypothetical outcomes remain
diagnostics only.
