import { expect, it } from 'vitest';
import { omit } from './omit';

it('test omit', () => {
  const obj = {
    a: 1,
    b: 2,
    c: 3,
    d: 4,
  };

  expect(omit(obj, ['a'])).toStrictEqual({
    b: 2,
    c: 3,
    d: 4,
  });

  expect(omit(obj, ['b', 'c'])).toStrictEqual({
    a: 1,
    d: 4,
  });
});
