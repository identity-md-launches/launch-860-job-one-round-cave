"""Offline ABI and integration checks for the typed, agreement-gated preview."""
from unittest.mock import patch
import typed_agreed as p


def check():
    codec = p.codec
    types = codec.parse_types('address,bool,int8,uint8,bytes2,string,bytes')
    values = ['0x' + '12' * 20, 'true', '-128', '255', '0xabcd', 'torch', '0x0102']
    encoded = codec.encode_args(types, values)
    assert codec.decode_args(types, '0x' + encoded.hex()) == [
        values[0], True, '-128', '255', '0xabcd', 'torch', '0x0102']
    for kind, value in [('int8', '-129'), ('uint8', '256'), ('bool', 'yes'), ('bytes2', '0xab')]:
        try:
            codec.encode_args([kind], [value])
        except ValueError:
            pass
        else:
            raise AssertionError('out-of-range argument accepted')
    for types, raw in [(['bool'], '0x' + (2).to_bytes(32, 'big').hex()),
                       (['string'], '0x' + (32).to_bytes(32, 'big').hex()),
                       (['bytes2'], '0x' + 'abcd' + '00' * 29 + '01')]:
        try:
            codec.decode_args(types, raw)
        except ValueError:
            pass
        else:
            raise AssertionError('malformed return accepted')
    endpoints = ['https://a.invalid', 'https://b.invalid']
    block_hash = '0x' + 'ab' * 32
    agreed = {'status': 'agreement', 'common_height': 100,
              'common_blocks': [{'block_hash': block_hash}] * 2}
    with patch.object(p.agreed_preview.agreement, 'compare', return_value=agreed) as agreement, \
         patch.object(p.call_preview, 'rpc_call', return_value={'result': '0x' + '00' * 32}) as call, \
         patch.object(p.agreed_preview.rpc_health, 'rpc', return_value={'number': '0x64', 'hash': block_hash}):
        result = p.preview(iter(endpoints), p.call_preview.ZTO, 'balanceOf(address)',
                           [p.call_preview.DEMO_FROM], 'uint256')
        assert result['preview']['decoded_return'] == ['0'] and result['sent'] is False
        tx = call.call_args.args[1]
        assert tx['data'] == '0x70a08231' + '00' * 31 + '01'
        assert call.call_args.args[2] == '0x64'
        assert tx['value'] == '0x0'
        call.return_value = {'result': '0x01'}
        malformed = p.preview(endpoints, p.call_preview.ZTO, 'totalSupply()', [], 'uint256')
        assert malformed['preview']['return_data'] == '0x01'
        assert 'decode_error' in malformed['preview']
        for status in ('disagreement', 'inconclusive', 'lagging'):
            agreement.return_value = {'status': status}
            call.reset_mock()
            assert p.preview(endpoints, p.call_preview.ZTO, 'totalSupply()', [], 'uint256')['status'] == 'blocked'
            call.assert_not_called()
    print('PASS: mixed ABI roundtrip, argument bounds, malformed returns, typed selector, pinned call, raw retention, agreement gating')


if __name__ == '__main__':
    check()
