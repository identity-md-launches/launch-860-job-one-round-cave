#!/usr/bin/env python3
"""Build a typed ABI call, preview it with eth_call, and decode its outcome."""

import argparse
import importlib.util
import json
import re
import sys
import urllib.error
from pathlib import Path


def sibling(folder, filename):
    path = Path(__file__).resolve().parents[1] / folder / filename
    spec = importlib.util.spec_from_file_location(folder, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


preview = sibling("call_preview", "call_preview.py")
names = sibling("revert_names", "revert_names.py")
SIGNATURE = re.compile(r"[A-Za-z_$][A-Za-z0-9_$]*\(([a-z0-9,]*)\)")
MAX_DATA_BYTES = 65536


def parse_types(csv):
    types = csv.split(",") if csv else []
    for kind in types:
        if kind in ("int", "uint") or not names.TYPE.fullmatch(kind):
            raise ValueError(f"unsupported ABI type: {kind!r}")
    return types


def function(signature):
    match = SIGNATURE.fullmatch(signature)
    if not match:
        raise ValueError("function signature must be canonical, e.g. balanceOf(address)")
    return parse_types(match.group(1))


def dynamic(kind):
    return kind in ("string", "bytes")


def integer_width(kind):
    if kind.startswith("uint"):
        return False, int(kind[4:] or 256)
    if kind.startswith("int"):
        return True, int(kind[3:] or 256)
    return None


def encode_static(kind, value):
    if kind == "address":
        if not re.fullmatch(r"0x[0-9a-fA-F]{40}", value):
            raise ValueError("address must be 20-byte 0x hex")
        return bytes.fromhex(value[2:]).rjust(32, b"\0")
    if kind == "bool":
        if value not in ("true", "false", "1", "0"):
            raise ValueError("bool must be true, false, 1 or 0")
        return (1 if value in ("true", "1") else 0).to_bytes(32, "big")
    if kind.startswith("bytes"):
        size = int(kind[5:])
        if not re.fullmatch(r"0x(?:[0-9a-fA-F]{2})*", value):
            raise ValueError(f"{kind} must be 0x hex")
        raw = bytes.fromhex(value[2:])
        if len(raw) != size:
            raise ValueError(f"{kind} requires {size} bytes")
        return raw.ljust(32, b"\0")
    signed, width = integer_width(kind)
    try:
        number = int(value, 0) if value.lower().startswith(("0x", "-0x")) else int(value, 10)
    except ValueError as exc:
        raise ValueError(f"{kind} requires an integer") from exc
    low = -(1 << (width - 1)) if signed else 0
    high = (1 << (width - 1)) - 1 if signed else (1 << width) - 1
    if not low <= number <= high:
        raise ValueError(f"{kind} value out of range")
    return (number % (1 << 256)).to_bytes(32, "big")


def encode_dynamic(kind, value):
    if kind == "string":
        raw = value.encode("utf-8")
    else:
        if not re.fullmatch(r"0x(?:[0-9a-fA-F]{2})*", value):
            raise ValueError("bytes must be even-length 0x hex")
        raw = bytes.fromhex(value[2:])
    return len(raw).to_bytes(32, "big") + raw + bytes(-len(raw) % 32)


def encode_args(types, values):
    if len(types) != len(values):
        raise ValueError(f"expected {len(types)} argument(s), got {len(values)}")
    head, tail = [], bytearray()
    for kind, value in zip(types, values):
        if dynamic(kind):
            head.append((32 * len(types) + len(tail)).to_bytes(32, "big"))
            tail.extend(encode_dynamic(kind, value))
        else:
            head.append(encode_static(kind, value))
    result = b"".join(head) + tail
    if len(result) > MAX_DATA_BYTES:
        raise ValueError("ABI arguments exceed size limit")
    return result


def decode_static(kind, word):
    n = int.from_bytes(word, "big")
    if kind == "address":
        if n >> 160:
            raise ValueError("address has nonzero high bytes")
        return "0x" + word[12:].hex()
    if kind == "bool":
        if n not in (0, 1):
            raise ValueError("bool is neither 0 nor 1")
        return bool(n)
    if kind.startswith("bytes"):
        size = int(kind[5:])
        if any(word[size:]):
            raise ValueError(f"{kind} has nonzero padding")
        return "0x" + word[:size].hex()
    signed, width = integer_width(kind)
    if signed:
        value = n - (1 << 256) if n >> 255 else n
        if not -(1 << (width - 1)) <= value < 1 << (width - 1):
            raise ValueError(f"{kind} out of range")
        return str(value)
    if n >> width:
        raise ValueError(f"{kind} out of range")
    return str(n)


def decode_args(types, raw):
    if not re.fullmatch(r"0x(?:[0-9a-fA-F]{2})*", raw):
        raise ValueError("result is not even-length 0x hex")
    data = bytes.fromhex(raw[2:])
    if len(data) > MAX_DATA_BYTES or len(data) % 32 or len(data) < 32 * len(types):
        raise ValueError("ABI result length is invalid")
    values = []
    for i, kind in enumerate(types):
        word = data[32 * i:32 * (i + 1)]
        if not dynamic(kind):
            values.append(decode_static(kind, word))
            continue
        offset = int.from_bytes(word, "big")
        if offset % 32 or offset < 32 * len(types) or offset + 32 > len(data):
            raise ValueError("dynamic result offset is invalid")
        length = int.from_bytes(data[offset:offset + 32], "big")
        end = offset + 32 + length
        padded_end = (end + 31) // 32 * 32
        if padded_end > len(data) or any(data[end:padded_end]):
            raise ValueError("dynamic result is truncated or has nonzero padding")
        value = data[offset + 32:end]
        values.append(value.decode("utf-8") if kind == "string" else "0x" + value.hex())
    return values


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true", help="read ZTO balanceOf(0x...01) on mainnet")
    parser.add_argument("--to", type=preview.address, help="contract address")
    parser.add_argument("--signature", help="canonical function signature, e.g. balanceOf(address)")
    parser.add_argument("--arg", action="append", default=[], help="one argument in signature order; repeat")
    parser.add_argument("--returns", default="", help="comma-separated return types, e.g. uint256,bool")
    parser.add_argument("--from", dest="sender", type=preview.address)
    parser.add_argument("--value-wei", type=preview.nonnegative_int, default=0)
    parser.add_argument("--gas", type=preview.nonnegative_int)
    parser.add_argument("--block", type=preview.block_tag, default="latest")
    parser.add_argument("--rpc", default=preview.DEFAULT_RPC)
    args = parser.parse_args(argv)
    if args.demo:
        if args.to or args.signature or args.arg or args.returns or args.sender or args.value_wei or args.gas is not None:
            parser.error("--demo cannot be combined with call fields")
        args.to = preview.ZTO
        args.signature = "balanceOf(address)"
        args.arg = [preview.DEMO_FROM]
        args.returns = "uint256"
    if not args.to or not args.signature:
        parser.error("--to and --signature are required unless --demo is used")
    if not args.rpc.startswith("https://"):
        parser.error("--rpc must be an HTTPS URL")
    try:
        types = function(args.signature)
        returns = parse_types(args.returns)
        calldata = names.selector(args.signature) + encode_args(types, args.arg).hex()
    except ValueError as exc:
        parser.error(str(exc))
    tx = {"to": args.to, "data": calldata, "value": hex(args.value_wei)}
    if args.sender:
        tx["from"] = args.sender
    if args.gas is not None:
        tx["gas"] = hex(args.gas)
    report = {"method": "eth_call", "sent": False, "block": args.block,
              "signature": args.signature, "return_types": returns, "transaction": tx}
    try:
        response = preview.rpc_call(args.rpc, tx, args.block)
        if "result" in response:
            report["status"] = "succeeded"
            report["return_data"] = response["result"].lower()
            if returns:
                try:
                    report["decoded_return"] = decode_args(returns, report["return_data"])
                except (ValueError, UnicodeDecodeError) as exc:
                    report["decode_error"] = str(exc)
        else:
            error = response["error"]
            raw = preview.revert_data(error)
            report["status"] = "reverted" if raw or "revert" in error["message"].lower() else "rpc_error"
            report["error"] = {"message": error["message"]}
            if raw:
                report["error"]["data"] = raw
                report["error"]["named"] = names.name_revert(raw, names.build_index())
    except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError, RecursionError) as exc:
        report["status"] = "rpc_error"
        report["error"] = {"message": str(exc)}
    print(json.dumps(report, indent=2))
    return 0 if report["status"] in ("succeeded", "reverted") else 2


if __name__ == "__main__":
    sys.exit(main())
