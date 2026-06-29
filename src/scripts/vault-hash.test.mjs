import assert from 'node:assert/strict';
import { sha256Hex } from './vault-hash.ts';

// Known vector: SHA-256("abc")
assert.equal(
  await sha256Hex('abc'),
  'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad',
);
console.log('ok: sha256Hex matches known vector');
