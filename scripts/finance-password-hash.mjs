#!/usr/bin/env node
// Prints a FINANCE_PASSWORD_HASH value for the Vault Finance sign-in.
// Usage: node scripts/finance-password-hash.mjs
// The password is typed without echo and never written anywhere; paste only
// the printed hash into Dokploy → Environment (or a local .env).
import { randomBytes, scryptSync } from 'node:crypto';

function ask(question) {
  return new Promise((resolve) => {
    const { stdin, stderr } = process;
    stderr.write(question);
    if (!stdin.isTTY) {
      let data = '';
      stdin.setEncoding('utf8');
      stdin.on('data', (c) => (data += c));
      stdin.on('end', () => resolve(data.split(/\r?\n/)[0]));
      return;
    }
    let text = '';
    stdin.setRawMode(true);
    stdin.resume();
    stdin.setEncoding('utf8');
    const onData = (ch) => {
      if (ch === '\u0003') process.exit(130);
      if (ch === '\r' || ch === '\n') {
        stdin.setRawMode(false);
        stdin.pause();
        stdin.off('data', onData);
        stderr.write('\n');
        resolve(text);
      } else if (ch === '\u007f') text = text.slice(0, -1);
      else text += ch;
    };
    stdin.on('data', onData);
  });
}

const password = await ask('Finance password: ');
if (password.length < 12) {
  console.error('Use at least 12 characters.');
  process.exit(1);
}
if (process.stdin.isTTY && (await ask('Repeat password: ')) !== password) {
  console.error('The two passwords did not match.');
  process.exit(1);
}
// Same parameters and format as hashPassword() in src/lib/finance/auth.ts.
const N = 2 ** 15,
  r = 8,
  p = 1;
const salt = randomBytes(16);
const key = scryptSync(password, salt, 32, { N, r, p, maxmem: 256 * N * r });
console.log(
  [
    'scrypt',
    N,
    r,
    p,
    salt.toString('base64url'),
    key.toString('base64url'),
  ].join(':'),
);
