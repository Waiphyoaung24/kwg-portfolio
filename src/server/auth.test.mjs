import assert from 'node:assert';
process.env.APP_SECRET = 'test-secret';
process.env.APP_PASSWORD = 'hunter2';
const { checkPassword, sessionCookie, isAuthed } = await import('./auth.mjs');

// password check
assert.strictEqual(checkPassword('hunter2'), true);
assert.strictEqual(checkPassword('wrong'), false);
assert.strictEqual(checkPassword(''), false);

// a valid cookie authenticates; a tampered one does not
const setCookie = sessionCookie();
const value = setCookie.split(';')[0].split('=').slice(1).join('=');
const authed = new Request('http://x', { headers: { cookie: `kwg_pw=${value}` } });
assert.strictEqual(isAuthed(authed), true);

const tampered = new Request('http://x', { headers: { cookie: `kwg_pw=${value}x` } });
assert.strictEqual(isAuthed(tampered), false);
assert.strictEqual(isAuthed(new Request('http://x')), false);

// fail closed: with APP_SECRET unset, a previously-valid cookie must NOT authenticate,
// and no new cookie can be minted (no guessable fallback secret to forge with).
delete process.env.APP_SECRET;
assert.strictEqual(isAuthed(authed), false);
assert.throws(() => sessionCookie());
process.env.APP_SECRET = 'test-secret';

console.log('auth.test OK');
