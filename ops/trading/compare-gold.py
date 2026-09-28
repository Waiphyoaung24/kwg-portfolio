"""Prepare and compare one private, read-only gold experiment."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from gold_experiment import (compare_reports, digest, prepare_experiment, register_candidate,
                             research_input, source_hashes, validate_candidate,
                             validate_registration)


def read_json(path: Path):
    return json.loads(path.read_bytes())


def write_once(path: Path, value):
    encoded = (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()
    with path.open('xb') as output:
        output.write(encoded)
    return hashlib.sha256(encoded).hexdigest()


def checked_dataset(path: Path, expected_hash: str):
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_hash.lower():
        raise ValueError('Dataset checksum mismatch')
    return json.loads(raw)


def finalize(prepared: dict, dataset: dict, dataset_hash: str) -> dict:
    current = prepare_experiment(dataset, dataset_hash, source_hashes())
    if prepared != current:
        raise ValueError('Prepared manifest differs from dataset or current evaluator')
    return {**current, 'status': 'frozen'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('prepare', 'finalize'):
        command = sub.add_parser(name)
        command.add_argument('--dataset', type=Path, required=True)
        command.add_argument('--sha256', required=True)
        command.add_argument('--output', type=Path, required=True)
        if name == 'finalize':
            command.add_argument('--prepared', type=Path, required=True)
    command = sub.add_parser('research-input')
    for name in ('dataset', 'sha256', 'manifest', 'baseline', 'output'):
        command.add_argument('--' + name, type=Path if name != 'sha256' else str, required=True)
    command = sub.add_parser('register')
    for name in ('manifest', 'proposal', 'output'):
        command.add_argument('--' + name, type=Path, required=True)
    command = sub.add_parser('compare')
    for name in ('baseline', 'candidate', 'manifest', 'proposal', 'registration', 'output'):
        command.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'prepare':
        result = prepare_experiment(checked_dataset(args.dataset, args.sha256),
                                    args.sha256, source_hashes())
    elif args.command == 'finalize':
        result = finalize(read_json(args.prepared), checked_dataset(args.dataset, args.sha256),
                          args.sha256)
    elif args.command == 'research-input':
        manifest = read_json(args.manifest)
        data = checked_dataset(args.dataset, args.sha256)
        if ({**manifest, 'status': 'prepared'}
                != prepare_experiment(data, args.sha256, source_hashes())):
            raise ValueError('Manifest, dataset or evaluator mismatch')
        result = research_input(data, manifest, read_json(args.baseline))
    elif args.command == 'register':
        manifest = read_json(args.manifest)
        if manifest.get('code_sha256') != source_hashes():
            raise ValueError('Evaluator changed after freeze')
        result = register_candidate(manifest, read_json(args.proposal),
                                    datetime.now(timezone.utc).isoformat())
    else:
        manifest = read_json(args.manifest)
        if manifest['code_sha256'] != source_hashes():
            raise ValueError('Evaluator changed after freeze')
        proposal = validate_candidate(read_json(args.proposal))
        registration = validate_registration(read_json(args.registration), manifest, proposal)
        candidate = read_json(args.candidate)
        if candidate.get('registration_sha256') != digest(registration):
            raise ValueError('Candidate registration mismatch')
        result = compare_reports(read_json(args.baseline), candidate,
                                 manifest, proposal)
    output_hash = write_once(args.output, result)
    print(json.dumps({'status': result.get('verdict', result.get('status')),
                      'output_sha256': output_hash}, sort_keys=True))


if __name__ == '__main__':
    main()
