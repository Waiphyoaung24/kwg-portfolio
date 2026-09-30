"""Parse/replay saved proposal bytes offline. No inference, registration or evaluation."""
import argparse
import hashlib
import json
from pathlib import Path

from gold_experiment import digest, validate_candidate


MAX_RESPONSE_BYTES = 16384


def parse_proposal(raw: bytes) -> dict:
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate key')
            result[key] = value
        return result

    def reject_constant(value):
        raise ValueError('Nonfinite JSON')

    try:
        if not isinstance(raw, bytes) or len(raw) > MAX_RESPONSE_BYTES:
            raise ValueError('Response size')
        proposal = validate_candidate(json.loads(raw.decode('utf-8'),
            object_pairs_hook=unique_object, parse_constant=reject_constant))
        if len(proposal['hypothesis']) > 2000:
            raise ValueError('Hypothesis size')
        # JSON escapes can decode into lone surrogates that cannot form UTF-8 artifacts.
        proposal['hypothesis'].encode('utf-8')
        return proposal
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise ValueError('Invalid research response') from None


def replay_response(raw: bytes, output_dir: Path) -> dict:
    output_dir.mkdir(mode=0o700)
    result = {'mode': 'offline-response-replay', 'status': 'invalid_response',
              'review_status': 'unreviewed', 'qualification': 'unqualified',
              'promotion_status': 'blocked', 'candidate_registered': False,
              'model_requests': 0}
    if len(raw) > MAX_RESPONSE_BYTES:
        result['status'] = 'response_too_large'
    else:
        with (output_dir / 'response.json').open('xb') as output:
            output.write(raw)
        result['response_sha256'] = hashlib.sha256(raw).hexdigest()
        try:
            proposal = parse_proposal(raw)
        except ValueError:
            pass
        else:
            encoded = (json.dumps(proposal, sort_keys=True, separators=(',', ':'),
                                  allow_nan=False) + '\n').encode('utf-8')
            with (output_dir / 'proposal.json').open('xb') as output:
                output.write(encoded)
            result.update(status='parsed_offline', proposal_sha256=digest(proposal))
    with (output_dir / 'result.json').open('xb') as output:
        output.write((json.dumps(result, sort_keys=True, allow_nan=False) + '\n').encode())
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--response', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        with args.response.open('rb') as source:
            raw = source.read(MAX_RESPONSE_BYTES + 1)
        result = replay_response(raw, args.output)
    except OSError:
        parser.exit(2, 'Offline replay could not read input or create exclusive output.\n')
    print(json.dumps(result, sort_keys=True))
    if result['status'] != 'parsed_offline':
        parser.exit(1)


if __name__ == '__main__':
    main()
