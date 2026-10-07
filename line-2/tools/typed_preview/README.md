# Typed call preview

`typed_preview.py` accepts a canonical Solidity function signature and typed argument values, constructs ABI calldata, previews the unsigned call with `eth_call`, and decodes declared return values. It supports `address`, `bool`, sized and unsized `int`/`uint`, `bytes1`–`bytes32`, `bytes`, and `string`. A revert is named using the existing error catalog when its selector is known. It uses only Python's standard library, sends no transaction, and reads no keys or environment variables.

From the repository root, run this live ZTO balance preview:

```sh
python3 -B line-2/tools/typed_preview/typed_preview.py --demo
```

For a custom call, pass `--to 0x... --signature 'balanceOf(address)' --arg 0x... --returns uint256`. Repeat `--arg` in signature order. `--from`, `--value-wei`, `--gas`, `--block`, and `--rpc` use the same conventions as call preview. For dynamic `bytes`, supply even-length `0x` hex; for `bool`, use `true`, `false`, `1`, or `0`. Integers accept decimal or `0x` hex. The signature must contain canonical ABI types without names or spaces.

Tried against `https://ethereum-rpc.publicnode.com`: the `--demo` ZTO `balanceOf(0x...01)` call succeeded and decoded `0`. A second live preview of `transfer(address,uint256)` from that same empty address reverted with the named `InsufficientBalance(address,uint256,uint256)` error. Offline ABI boundary and malformed-output checks passed in `test/scratch/`.

The codec deliberately excludes arrays, tuples, and fixed point values. A node's preview reflects its chosen block and can differ from a later transaction. Declaring the wrong return types produces a `decode_error` while preserving the raw result.
