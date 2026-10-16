import assert from 'node:assert/strict';
import { test } from 'node:test';
import {
  amountInputValue,
  formatAmount,
  isCurrency,
  isZeroText,
  minorDigits,
  parseAmount,
} from './money.ts';

test('currency codes are validated against ISO 4217', () => {
  for (const c of ['THB', 'MMK', 'USD', 'JPY']) assert.ok(isCurrency(c), c);
  for (const c of ['thb', 'XYZ', 'BAHT', '', 'TH'])
    assert.ok(!isCurrency(c), c);
});

test('minor digits follow everyday use', () => {
  assert.equal(minorDigits('THB'), 2);
  assert.equal(minorDigits('USD'), 2);
  assert.equal(minorDigits('MMK'), 0);
  assert.equal(minorDigits('KWD'), 3);
});

test('parses amounts as typed', () => {
  assert.equal(parseAmount('60', 'THB'), 6000n);
  assert.equal(parseAmount('1,284.50', 'THB'), 128450n);
  assert.equal(parseAmount(' 0.5 ', 'USD'), 50n);
  assert.equal(parseAmount('4,500', 'MMK'), 4500n);
  assert.equal(parseAmount('1234567', 'MMK'), 1234567n);
  assert.equal(parseAmount('1.234', 'KWD'), 1234n);
});

test('rejects amounts that are not valid positive values in the currency', () => {
  for (const bad of [
    '',
    '0',
    '0.00',
    '-5',
    '1,2,3',
    '12,34',
    '1.',
    '.5',
    '0.001',
    '1e3',
    '١٢',
    'abc',
    '1 000',
  ]) {
    assert.equal(parseAmount(bad, 'THB'), null, bad);
  }
  assert.equal(parseAmount('4500.5', 'MMK'), null);
  assert.equal(parseAmount('9999999999999999', 'THB'), null);
});

test('formats with grouping, decimals and a real minus sign', () => {
  assert.equal(formatAmount(128450n, 'THB'), '1,284.50');
  assert.equal(formatAmount(5n, 'THB'), '0.05');
  assert.equal(formatAmount(0n, 'USD'), '0.00');
  assert.equal(formatAmount(-300000n, 'THB'), '−3,000.00');
  assert.equal(formatAmount(247000n, 'MMK'), '247,000');
  assert.equal(amountInputValue(-128450n, 'THB'), '-1284.50');
});

test('parse and format round-trip', () => {
  for (const s of ['1,284.50', '0.05', '12,000.00'])
    assert.equal(formatAmount(parseAmount(s, 'THB')!, 'THB'), s);
});

test('explicit zero is recognised separately from invalid input', () => {
  for (const z of ['0', '0.00', ' 00.0 ']) assert.ok(isZeroText(z), z);
  for (const nz of ['', '0.01', '-0', 'zero', '.0'])
    assert.ok(!isZeroText(nz), nz);
});
