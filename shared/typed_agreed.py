"""Build typed calldata and preview it only after public-provider agreement."""
import argparse
import json
from tools import typed_preview as codec, call_preview, rpc_health
import agreed_preview


def preview(endpoints, address, signature, arguments, returns=''):
    types = codec.function(signature)
    return_types = codec.parse_types(returns)
    data = codec.names.selector(signature) + codec.encode_args(types, arguments).hex()
    report = agreed_preview.preview(endpoints, address, data, 'raw')
    report.update(signature=signature, return_types=return_types)
    if report['status'] == 'observed' and report['preview']['status'] == 'succeeded' and return_types:
        outcome = report['preview']
        try:
            outcome['decoded_return'] = codec.decode_args(return_types, outcome['return_data'])
        except ValueError as exc:
            outcome['decode_error'] = str(exc)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--endpoint', action='append')
    parser.add_argument('--address', default=call_preview.ZTO, type=call_preview.address)
    parser.add_argument('--signature', default='balanceOf(address)')
    parser.add_argument('--arg', action='append')
    parser.add_argument('--returns', default='uint256')
    args = parser.parse_args()
    arguments = args.arg if args.arg is not None else (
        [call_preview.DEMO_FROM] if args.signature == 'balanceOf(address)' else [])
    try:
        result = preview(args.endpoint or rpc_health.DEFAULTS, args.address,
                         args.signature, arguments, args.returns)
        print(json.dumps(result, indent=2))
        return 0 if result['status'] == 'observed' and result['preview']['status'] != 'rpc_error' else 1
    except (ValueError, OSError, TypeError, KeyError, RecursionError, argparse.ArgumentTypeError) as exc:
        print(json.dumps({'status': 'error', 'sent': False, 'error': str(exc)}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
