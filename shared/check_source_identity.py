"""Reject source-provider identity mismatches before compiler comparisons."""
from unittest.mock import patch
from tools import compiler_trailer as t


def check():
    code = bytes.fromhex('00a164736f6c634300081a000a')
    source = {'chainId': '1', 'address': t.ZTO, 'match': 'exact_match',
              'compilation': {'compilerVersion': '0.8.26'}}
    with patch.object(t, 'pinned_code', return_value=({'number': 100, 'hash': '0x' + 'ab' * 32}, code)), \
         patch.object(t, 'read', return_value=source) as read:
        assert t.inspect(t.ZTO)['sourcify']['status'] == 'consistent'
        for bad in ({**source, 'chainId': '137'},
                    {**source, 'address': '0x' + '11' * 20},
                    {'match': 'exact_match'}, []):
            read.return_value = bad
            result = t.inspect(t.ZTO)
            assert result['sourcify']['status'] == 'lookup_failed'
            assert 'chain or address' in result['sourcify']['error']
    print('PASS: matching identity, wrong chain, wrong address, missing identity, non-object')


if __name__ == '__main__':
    check()
