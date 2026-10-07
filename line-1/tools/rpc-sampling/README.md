# RPC Sampling

Measure a bounded series of Ethereum mainnet RPC health observations before relying on an endpoint. Reports fresh, stale and error counts, the observed fresh fraction, and nearest-rank p95/max request-pair latency including failures. Each observation retains the original health evidence. Python standard library only; reuses ../rpc-health/probe.py, with its read-only methods, bounded responses, own User-Agent and disabled proxy discovery. No installation, configuration, credentials or transactions.

From the workspace root, see it work offline:

```sh
python3 -B line-1/tools/rpc-sampling/sample.py --demo
```

For real reads:

```sh
python3 -B line-1/tools/rpc-sampling/sample.py --rounds 3 --interval 1
```

Defaults: PublicNode first and dRPC second, three rounds, one-second pause after each complete round, 12-second per-request timeout, 120-second freshness threshold. Repeat --endpoint for custom HTTPS providers. Bounds: 1..8 distinct endpoints, 1..20 rounds, 0..60 second interval, 0.001..30 second timeout, 0..3600 second maximum age. Exit 0 means every sample was fresh; exit 1 means degraded observations; invalid arguments exit 2. JSON goes to stdout only. The reusable sample function supports injected probes and waits for offline use.

## Tried

2026-10-07: offline checks passed mixed fresh/error/stale accounting, failure-inclusive p95, generator consumption, waits between rounds only, one-round success, and nine invalid inputs rejected before transport. Both predecessor demos passed unchanged. Three live rounds with interval 0 returned fresh mainnet block 26136869 for both providers in every sample. PublicNode max/p95 latency was 69.57 ms; dRPC was 83.46 ms. Hash: 0x4884b74df92848ed5e3cdfaf8d48be2bfbc6362cb1377fd2b6c11d8cd43b8475.

## Limits

Observed fresh fraction is a short sample, not an uptime guarantee. Zero-interval samples may hit the same cached block. p95 with few samples is usually the maximum. Providers run sequentially; interval is a pause after a round, not a fixed sampling frequency. Each health sample makes two sequential requests; the timeout applies separately to each request. Local clock error affects freshness. These checks do not prove honesty, independence, cross-provider agreement, or future availability. RPC Agreement remains the separate common-height comparison tool. Endpoint URLs appear in output: use public URLs without credentials. No coin is needed to measure public RPC reliability.
