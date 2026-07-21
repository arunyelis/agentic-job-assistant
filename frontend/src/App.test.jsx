import { renderToString } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import App, { appendReasoning } from './App.jsx';

describe('App', () => {
  it('renders before a resume is uploaded', () => {
    const html = renderToString(<App />);

    expect(html).toContain('Choose a resume');
    expect(html).toContain('Resume required');
  });

  it('keeps separate reasoning summaries readable', () => {
    let summaries = appendReasoning([], {
      itemId: 'reasoning-1',
      summaryIndex: 0,
      text: '**Loading skill**'
    });
    summaries = appendReasoning(summaries, {
      itemId: 'reasoning-1',
      summaryIndex: 1,
      text: '**Inspecting page**'
    });

    expect(summaries).toHaveLength(2);
    expect(summaries[1].text).toBe('**Inspecting page**');
  });

  it('separates adjacent bold fragments in one summary', () => {
    const initial = [{ id: 'reasoning-1:0', text: '**Loading skill**' }];
    const summaries = appendReasoning(initial, {
      itemId: 'reasoning-1',
      summaryIndex: 0,
      text: '**Inspecting page**'
    });

    expect(summaries[0].text).toBe('**Loading skill**\n\n**Inspecting page**');
  });
});
