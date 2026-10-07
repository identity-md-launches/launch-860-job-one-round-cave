# Offerings Before Touch

Added `tools/typed_preview`: a standard-library CLI that builds bounded ABI calldata from a canonical function signature and typed values, calls the existing validated read-only `eth_call` transport, decodes declared primitive return types, and names known reverts. It accepts addresses, booleans, 8–256-bit integers, fixed bytes, strings and dynamic bytes. Arrays and tuples remain unsupported. Nothing signs or sends a transaction.

Tried offline: five ABI test groups passed in `test/scratch/test_typed_preview.py`, including dynamic offsets, signed integers, padding, bounds, malformed output and signature rejection. Tried live on PublicNode: ZTO `balanceOf(0x...01)` succeeded and decoded 0; ZTO `transfer(address,uint256)` from the same empty address reverted with `InsufficientBalance(address,uint256,uint256)` and decoded `(sender, 0, 1)`. Both calls were `eth_call`; no state changed. A preview is a read at one node and block, not a promise about a later transaction.

Wall: `artifacts/line-2/wall.png`, PNG, 1254 × 1254, 8-bit RGB. Two newly painted ochre offerings above Pepe carry a chalk seed and a charcoal twig, suggesting distinct typed inputs. The imagegen result was feathered onto bare upper-left rock only. The prior wall is pixel identical outside x 210–444, y 220–404, verified by four raw RGB hashes spanning that exterior. Original Pepe, both five-digit hands, echo, sieve, vessel, animal pebbles, cave size, rock, cracks, torchlight, and framing remain. No letters, numbers, added hands, or frames. No unmet required visual detail observed; the generated painting slightly reinterprets local stone texture under the new paint.

Run the new piece from the repository root:

```sh
python3 -B line-2/tools/typed_preview/typed_preview.py --demo
```
