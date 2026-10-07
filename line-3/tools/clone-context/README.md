# Clone Context

Follow exact EIP-1167 minimal-proxy code targets while retaining the original contract's storage address. This helps a worker avoid reading an implementation's own EIP-1967 slots when its code is being delegated to by a clone. Reports each code address, its byte length, the shared storage context, cycles, empty targets and truncation at a bounded limit. Reads the original context's implementation/beacon slots as candidates, never as proven dispatch.

Python standard library only; uses the existing sibling `proxy-route` reader and parsers. Keep both folders together. No installation needed. From the repository root, run this network-free demonstration:

```sh
python3 -B line-3/tools/clone-context/clone_context.py --self-test
```

For read-only real Ethereum evidence (ZTO by default):

```sh
python3 -B line-3/tools/clone-context/clone_context.py
```

`--address 0x...` selects another contract; `--limit 8` caps code addresses (1–32). `--rpc https://eth.drpc.org` selects the alternative endpoint. All reads use one block number and a start/end hash recheck. HTTP uses a dedicated User-Agent, no environment proxy discovery and bounded responses. Nothing signs or sends a transaction, posts, accesses a wallet or reads credentials.

## Tried

Self-test passed: a two-hop clone chain, common storage context, cycle detection, depth limit, empty implementation, rejection of a clone with extra bytes, pinned RPC reads, and reorganization rejection. The fake RPC deliberately asserts that slots are never read from the implementation addresses.

Live ZTO scan on PublicNode at block 26136865, hash `0x470a98217604d2651ff253e70c07362f58589f996f3e465fefd3f26e484cc138`, returned 1287 code bytes, no exact clone target and zero implementation/beacon slots. The ending block hash matched. This is a real negative observation, not evidence of a live clone chain or a proof of immutability.

## Limits

Only exact 45-byte clones are followed. Terminal code may itself be a custom proxy, library or other router; it is not resolved. The original context's slot values are unverified routing candidates even if terminal code ignores them. A cycle or limit means an incomplete traversal. Empty target code is not a working implementation. No authority or future upgrade safety is established. Provider honesty and hash-recheck race limitations remain. Contract creation, selfdestruct and called contracts are outside this scan.
