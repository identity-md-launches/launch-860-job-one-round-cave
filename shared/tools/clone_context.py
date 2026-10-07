#!/usr/bin/env python3
"""Follow exact EIP-1167 clones without confusing code and storage addresses."""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import sys

# Reuse the reviewed bounded, direct HTTP reader and strict parsers.
from . import proxy_route as route


def trace(address, read_code, limit=8):
    if type(limit) is not int or not 1 <= limit <= 32:
        raise ValueError('limit must be 1..32 code addresses')
    current, seen, nodes = address.lower(), set(), []
    while True:
        if current in seen:
            return {'nodes': nodes, 'stop': 'cycle', 'next_code_address': current}
        if len(nodes) == limit:
            return {'nodes': nodes, 'stop': 'limit', 'next_code_address': current}
        seen.add(current)
        code = route.hex_bytes(read_code(current))
        match = re.fullmatch(route.PREFIX + '([0-9a-f]{40})' + route.SUFFIX, code.hex())
        target = '0x' + match.group(1) if match else None
        nodes.append({'code_address': current, 'storage_address': address.lower(),
                      'code_bytes': len(code), 'exact_clone_target': target})
        if not target:
            return {'nodes': nodes, 'stop': 'empty_code' if not code else 'not_exact_clone',
                    'next_code_address': None}
        current = target


def inspect(endpoint, address, limit=8, call=route.rpc):
    if call(endpoint, 'eth_chainId', []) != '0x1':
        raise ValueError('Expected Ethereum mainnet chainId 1')
    number, block_hash = route.block_ref(call(endpoint, 'eth_getBlockByNumber', ['latest', False]))
    result = trace(address, lambda a: call(endpoint, 'eth_getCode', [a, number]), limit)
    # Every DELEGATECALL in an exact clone preserves the caller's storage context.
    slots = {key: call(endpoint, 'eth_getStorageAt', [address, slot, number])
             for key, slot in route.SLOTS.items()}
    candidates = {key: route.slot_address(value) for key, value in slots.items()}
    end_number, end_hash = route.block_ref(call(endpoint, 'eth_getBlockByNumber', [number, False]))
    if (end_number, end_hash) != (number, block_hash):
        raise ValueError('Block changed during read; retry')
    return {'chain_id': 1, 'address': address, 'block_number': int(number, 16),
            'block_hash': block_hash, **result, 'context_raw_slots': slots,
            'context_route_candidates': candidates,
            'limitations': 'Only exact 45-byte EIP-1167 runtime targets are followed. A target is not proof of successful execution. Slots belong to the original storage context; their values do not prove dispatch. Terminal custom proxies, beacon getters, authority and called contracts are not resolved. Cycles and limits are incomplete scans; RPC evidence requires an honest provider.'}


def self_test():
    a, b, c = ['0x' + x * 40 for x in '123']
    def clone(target):
        return '0x' + route.PREFIX + target[2:] + route.SUFFIX
    codes = {a: clone(b), b: clone(c), c: '0x600000'}
    result = trace(a, codes.__getitem__)
    assert result['stop'] == 'not_exact_clone'
    assert [n['code_address'] for n in result['nodes']] == [a, b, c]
    assert all(n['storage_address'] == a for n in result['nodes'])
    assert trace(a, codes.__getitem__, 1)['stop'] == 'limit'
    codes[b] = clone(a)
    assert trace(a, codes.__getitem__)['stop'] == 'cycle'
    codes[b] = '0x'
    assert trace(a, codes.__getitem__)['stop'] == 'empty_code'
    codes[a] += '00'
    assert len(trace(a, codes.__getitem__)['nodes']) == 1
    for invalid in (0, 33, True):
        try:
            trace(a, codes.__getitem__, invalid)
        except ValueError:
            pass
        else:
            raise AssertionError('invalid limit accepted')
    codes[a] = clone(b)
    block_hash = '0x' + 'ab' * 32
    queries = []
    def fake(endpoint, method, params):
        queries.append((method, params))
        if method == 'eth_chainId': return '0x1'
        if method == 'eth_getBlockByNumber': return {'number': '0x10', 'hash': block_hash}
        if method == 'eth_getCode':
            assert params[1] == '0x10'
            return codes[params[0]]
        if method == 'eth_getStorageAt':
            assert params[0] == a and params[2] == '0x10'
            return '0x' + '00' * 12 + c[2:]
        raise AssertionError(method)
    observed = inspect('offline', a, call=fake)
    assert observed['context_route_candidates']['implementation'] == c
    assert queries[-1] == ('eth_getBlockByNumber', ['0x10', False])
    def reorg(endpoint, method, params):
        value = fake(endpoint, method, params)
        if method == 'eth_getBlockByNumber' and params[0] != 'latest':
            value['hash'] = '0x' + 'cd' * 32
        return value
    try:
        inspect('offline', a, call=reorg)
    except ValueError:
        pass
    else:
        raise AssertionError('reorg accepted')
    print('PASS: clone chain, storage context, cycle, limit, empty target, exact match, pinned reads, reorg rejection')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--address', default=route.ZTO)
    parser.add_argument('--rpc', default='https://ethereum-rpc.publicnode.com')
    parser.add_argument('--limit', type=int, default=8)
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    if not re.fullmatch(r'0x[0-9a-fA-F]{40}', args.address):
        parser.error('address must be 20-byte hexadecimal')
    if not 1 <= args.limit <= 32:
        parser.error('limit must be 1..32 code addresses')
    if not args.rpc.startswith('https://'):
        parser.error('RPC must use HTTPS')
    try:
        print(json.dumps(inspect(args.rpc, args.address.lower(), args.limit), indent=2))
    except (ValueError, OSError, TypeError, KeyError) as exc:
        print('clone-context: ' + str(exc), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
