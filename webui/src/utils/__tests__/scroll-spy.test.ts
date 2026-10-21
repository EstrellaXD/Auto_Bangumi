import { describe, expect, it } from 'vitest';
import { pickActiveSection } from '../scroll-spy';

const tops = [
  { id: 'a', top: -300 },
  { id: 'b', top: 40 },
  { id: 'c', top: 500 },
];

describe('pickActiveSection', () => {
  it('should return the last section crossing the anchor when not at bottom', () => {
    expect(pickActiveSection(tops, false)).toBe('b');
  });

  it('should return the first section when none crossed the anchor', () => {
    expect(pickActiveSection([{ id: 'a', top: 200 }], false)).toBe('a');
  });

  it('should return the last section when scrolled to the bottom', () => {
    expect(pickActiveSection(tops, true)).toBe('c');
  });

  it('should return undefined when there are no sections', () => {
    expect(pickActiveSection([], true)).toBeUndefined();
  });
});
