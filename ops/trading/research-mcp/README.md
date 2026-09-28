# Read-only gold research MCP

This separate Cloudflare Worker exposes two tools to Claude or another MCP
client: `get_gold_status` and `get_baseline_summary`. The model runs in the
client; this Worker does not run an AI model, Vibe-Trading, MT5, a strategy,
or any order command. `cc-connect` is a chat-to-agent bridge and is not needed.

The baseline summary is the sanitized frozen result in
[`2026-09-28-gold-first-experiment-results.md`](../../../docs/superpowers/plans/2026-09-28-gold-first-experiment-results.md).
The status tool fetches the existing private `/status` origin and applies the
same allowlist and 30-second heartbeat expiry as `/vault/trading`. No account
number, balance, credential, raw bars, or private report is returned.

From this directory:

```sh
pnpm install --frozen-lockfile
pnpm test
pnpm exec wrangler deploy --dry-run
```

Deployment uses Worker name `kwg-gold-research-mcp` in the same Cloudflare
account as the status Worker. It is fail-closed until `MCP_BEARER_TOKEN` is a
64-character hexadecimal value generated from 32 random bytes. Put the value
into Cloudflare with `pnpm exec wrangler secret put MCP_BEARER_TOKEN`; keep a
copy only in the owner's local secret store, not in Git or chat. A missing or
malformed token returns HTTP 503; a wrong token returns HTTP 401. Every MCP
request needs `Authorization: Bearer <token>`.

The Worker was deployed on 2026-09-28 at
`https://kwg-gold-research-mcp.nexuslab-dev-mm.workers.dev/mcp`. An anonymous
remote `tools/list` request returns HTTP 401; an authenticated request returns
HTTP 200 and lists only the two tools. The bearer token is stored in the owner's
Windows user profile at `%LOCALAPPDATA%\kwg-gold-mcp\token` and as the Worker
secret `MCP_BEARER_TOKEN`. It must not be pasted into chat or Git.

Live status uses three encrypted Worker variables: `STATUS_ORIGIN_URL`,
`STATUS_ACCESS_CLIENT_ID`, and `STATUS_ACCESS_CLIENT_SECRET`. The origin URL is
`https://status.waiphyoaung.com`; the Client ID and Secret belong to the
one-year `kwg-gold-research-mcp-status` Cloudflare Access service token. The
`KWG gold research MCP status token` Service Auth policy permits that token on
the protected origin. Never put credential values in `wrangler.toml`.

On 2026-09-28, authenticated remote calls to both tools returned HTTP 200.
`get_baseline_summary` reported `qualification=unqualified` and
`promotion=blocked`. After deploying the observer clock offset,
`get_gold_status` reported `status=baseline`, `signal=none`, a connected demo
terminal, and a fresh quote. This confirms the live read-only path; continuous
health across two M15 candle changes remains unverified.

Claude Code is connected locally in the owner's portfolio project. To connect
another Claude Code installation, use its remote HTTP MCP support with the
token supplied locally:

```sh
claude mcp add --transport http gold-research https://<worker-subdomain>/mcp --header "Authorization: Bearer <local-token>"
```

Test that an anonymous request is denied, then use Claude's `/mcp` screen to
connect and invoke each tool. The Worker has no mutation tools. Its baseline
is exploratory: validation lost under all three hypothetical cost scenarios,
historical costs are unverified, and no candidate has been compared. MCP access
does not authorize a research job or any trade.
