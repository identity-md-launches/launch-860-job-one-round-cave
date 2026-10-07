"""Bounded read-only RPC reliability sampling; Python standard library only."""
import argparse
import importlib.util
import json
import math
from pathlib import Path
import time

from . import rpc_health as health


def sample(endpoints, rounds=3, interval=1, timeout=12, max_age=120,
           probe=None, sleep=None):
    if isinstance(endpoints, (str, bytes)):
        raise ValueError('endpoints must be an iterable of endpoint strings')
    endpoints = list(endpoints)
    if not endpoints or len(endpoints) > 8 or any(not isinstance(e, str) or not e.strip() for e in endpoints) or len(set(endpoints)) != len(endpoints):
        raise ValueError('require 1..8 distinct nonempty endpoints')
    if type(rounds) is not int or not 1 <= rounds <= 20:
        raise ValueError('rounds must be an integer in 1..20')
    for value, low, high in [(interval, 0, 60), (timeout, 0.001, 30), (max_age, 0, 3600)]:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
            raise ValueError('invalid interval, timeout or maximum age')
    probe, sleep = probe or health.probe, sleep or time.sleep
    rows = {e: [] for e in endpoints}
    for index in range(rounds):
        for endpoint in endpoints:
            observation = probe(endpoint, timeout, max_age)
            rows[endpoint].append({'sample': index + 1, **observation})
        if index + 1 < rounds:
            sleep(interval)
    reports = []
    for endpoint, observations in rows.items():
        fresh = sum(o['status'] == 'fresh' for o in observations)
        latencies = sorted(o['latency_ms'] for o in observations)
        # Nearest-rank p95 includes failed attempts: failures also cost time.
        reports.append({'endpoint': endpoint, 'samples': rounds,
                        'fresh_samples': fresh, 'fresh_fraction': fresh / rounds,
                        'stale_samples': sum(o['status'] == 'stale' for o in observations),
                        'error_samples': sum(o['status'] == 'error' for o in observations),
                        'latency_p95_ms': latencies[math.ceil(.95 * rounds) - 1],
                        'max_latency_ms': max(latencies), 'observations': observations})
    return {'status': 'all_fresh' if all(r['fresh_samples'] == rounds for r in reports) else 'degraded',
            'interval_after_each_round_seconds': interval, 'reports': reports}


def demo():
    counts, sleeps = {}, []
    def fixture(endpoint, timeout, max_age):
        index = counts.get(endpoint, 0)
        counts[endpoint] = index + 1
        status = ['fresh', 'error', 'stale'][index] if endpoint == 'flaky' else 'fresh'
        return {'status': status, 'latency_ms': [10, 300, 20][index]}
    result = sample(iter(['steady', 'flaky']), probe=fixture, sleep=sleeps.append)
    assert result['status'] == 'degraded'
    assert result['reports'][0]['fresh_fraction'] == 1
    flaky = result['reports'][1]
    assert (flaky['fresh_samples'], flaky['error_samples'], flaky['stale_samples']) == (1, 1, 1)
    assert flaky['latency_p95_ms'] == 300 and sleeps == [1, 1]
    def forbidden(*args):
        raise AssertionError('invalid arguments reached probe')
    invalid = [{'endpoints': 'ab'}, {'endpoints': []}, {'endpoints': ['a', 'a']},
               {'endpoints': [None]}, {'rounds': True}, {'rounds': 21},
               {'interval': float('nan')}, {'timeout': 0}, {'max_age': -1}]
    for options in invalid:
        try:
            sample(**({'endpoints': ['a'], 'probe': forbidden} | options))
        except ValueError:
            continue
        raise AssertionError(options)
    one = sample(['steady'], rounds=1, probe=lambda *a: {'status': 'fresh', 'latency_ms': 1}, sleep=forbidden)
    assert one['status'] == 'all_fresh'
    print(json.dumps({'demo': 'passed', 'checks': ['mixed health counts', 'failure latency', 'generator', 'round waits', 'single sample', 'nine rejected inputs']}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--demo', action='store_true')
    parser.add_argument('--endpoint', action='append')
    parser.add_argument('--rounds', type=int, default=3)
    parser.add_argument('--interval', type=float, default=1)
    parser.add_argument('--timeout', type=float, default=12)
    parser.add_argument('--max-age', type=float, default=120)
    args = parser.parse_args()
    if args.demo:
        demo()
        return 0
    endpoints = args.endpoint or health.DEFAULTS
    if any(not e.startswith('https://') for e in endpoints):
        parser.error('require HTTPS endpoints')
    try:
        result = sample(endpoints, args.rounds, args.interval, args.timeout, args.max_age)
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2))
    return 0 if result['status'] == 'all_fresh' else 1


if __name__ == '__main__':
    raise SystemExit(main())
