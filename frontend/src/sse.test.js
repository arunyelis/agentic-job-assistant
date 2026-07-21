import { describe, expect, it } from 'vitest';
import { parseSseBlock } from './sse.js';

describe('parseSseBlock', () => {
  it('parses a named event with JSON data', () => {
    expect(parseSseBlock('event: token\ndata: {"text":"hello"}')).toEqual({
      event: 'token',
      data: { text: 'hello' }
    });
  });

  it('returns null when an SSE block has no data', () => {
    expect(parseSseBlock(': keep alive')).toBeNull();
  });
});
