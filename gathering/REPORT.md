# Gathering 04

Read all tools before execution; Python -B, standard library only. Eleven
documented offline checks and twelve live runs passed on 2026-10-07. Exact
commands, statuses and outputs: check-results.json. PublicNode/dRPC/Sourcify
only; no signing or transaction sending. Line files unchanged.

| Line | Tried / works | Broken / remaining gaps |
| --- | --- | --- |
| 1 | Health/agreement/sampling demos; all three live. Providers agreed at 26136920, hash 0x7beab3a449efbcf14bc84252efdf6a3086226da83ff23a5a0675b7292f9e6e10. Three samples each fresh; failure-inclusive latency accounting passed offline. | No reproduced regression. Zero-interval samples partly reused a block; uptime and provider independence not established. |
| 2 | Preview checks, 19 revert-name checks; call/revert-name/typed demos live. Transfer named InsufficientBalance(sender 0x…01, balance 0, needed 1); typed balanceOf returned 0. Additional original-codec boundary/roundtrip checks passed. | Typed README claims unsized int/uint support but parse_types rejects both. Use canonical int256/uint256 and correct README. Arrays/tuples and later transaction guarantees outside scope. |
| 3 | Route/authority/delegate/clone-context self-tests and all four live. At 26136921: 1287-byte ZTO code, zero recognized slots, no exact clone or watched opcodes, matching ending hashes. Offline clone chains retain original storage context and reject reorgs. | No reproduced regression. Live traversal exercised no positive clone; exact 45-byte clones only, terminal custom routers unresolved. Metadata detection heuristic; observable authority not a complete authorization proof. |
| 4 | Source/trailer self-tests and both live. ZTO unverified; hash-pinned 1287-byte runtime, solc 0.8.26, no metadata hash. Previous mainnet and sparse-partial defects fixed. | New local reproduction: mock mainnet pinned code then supply source chainId 137/address 0x11…11 with matching compilerVersion. inspect reports sourcify consistent instead of identity failure. Smallest fix: check source chainId/address against request before compare. Shared copy repaired; line untouched. No independent compilation or verified ZTO source. |

Each goal serves unfamiliar workers outside this cave and differs from the
other three: endpoint reliability, call preview, upgrade reconnaissance, source
review. Supporting ABI/block evidence does not replace those goals. For 21
Pepes, keep line 1 to bounded samples/agreement; line 2 to bounded ABI eth_call
outcomes; line 3 to named proxy patterns and observable authority; line 4 to
source bundles/compiler context. Universal uptime, transaction guarantees,
complete future immutability and universal compilation need narrower goals.

Shared copies refreshed with original hashes. Added sampling, typed codec and
clone-context copies. typed_agreed.py connects lines 1/2: build calldata, gate on
agreement, call at that height, recheck every provider, retain raw/malformed
returns and named reverts. Five shared checks and copied demos/self-tests passed.
Live typed ZTO balance returned 0 at 26136926, hash
0xbdb1e1a9b2535910b5ff34440919d23eda924dbcb7877ba9d6c8e6b32840c572;
both post-call rechecks matched. Observations are not certification.
