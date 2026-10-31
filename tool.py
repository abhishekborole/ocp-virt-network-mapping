"""Offline analysis; consumes normalized JSON, never connects to infrastructure."""
import argparse
import ipaddress
import json
import math
from pathlib import Path
import sys


def positive(value):
    if value <= 0:
        raise ValueError('Expected a positive value')
    return value


def integer_positive(value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError('Expected a positive integer')
    return positive(value)


def validate(value, schema, path='input'):
    """Validate required fields and primitive types; allow extra keys."""
    if isinstance(schema, dict):
        if not isinstance(value, dict): raise ValueError(path + ': expected object')
        for key, child in schema.items():
            if key not in value: raise ValueError(path + ': missing ' + key)
            validate(value[key], child, path + '.' + key)
    elif isinstance(schema, list):
        if not isinstance(value, list): raise ValueError(path + ': expected list')
        if schema:
            for index, item in enumerate(value): validate(item, schema[0], path + '[' + str(index) + ']')
    elif isinstance(schema, bool):
        if not isinstance(value, bool): raise ValueError(path + ': expected boolean')
    elif isinstance(schema, (int, float)):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(path + ': expected finite number')
        if isinstance(schema, int) and not isinstance(value, int): raise ValueError(path + ': expected integer')
        if schema >= 0 and value < 0: raise ValueError(path + ': expected nonnegative number')
    elif not isinstance(value, str):
        raise ValueError(path + ': expected string')


def analyze(data):
    validate(data, SCHEMA)
    return _analyze(data)


def main():
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument('input', type=Path, help='Normalized JSON file; see examples/sample.json')
    args = parser.parse_args()
    try:
        with args.input.open(encoding='utf-8-sig') as stream:
            data = json.load(stream)
        print(json.dumps(analyze(data), indent=2, sort_keys=True, allow_nan=False))
    except (OSError, ValueError, TypeError, KeyError) as error:
        print('Input error: ' + str(error), file=sys.stderr)
        return 2
    return 0


SCHEMA = {'available_networks': ['apps/production'], 'vms': [{'name': 'web-01', 'networks': ['apps/production']}]}
DESCRIPTION = 'Find VM network attachment names missing from a target namespace catalog.'

def _analyze(data):
    missing = []
    for vm in data['vms']:
        for network in vm['networks']:
            if network not in data['available_networks']: missing.append({'vm':vm['name'], 'network':network})
    return {'missing':missing, 'mapped':not missing}

if __name__ == '__main__':
    raise SystemExit(main())
