import { renderToString } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import App from '@/App';
import { appendReasoning } from '@/pages/AssistantPage';

describe('App', () => {
  it('renders a clear workspace loading state', () => {
    const client = new QueryClient();
    const html = renderToString(
      <QueryClientProvider client={client}>
        <App />
      </QueryClientProvider>
    );
    expect(html).toContain('Preparing your workspace');
  });

  it('keeps separate work summaries readable', () => {
    let summaries = appendReasoning([], { itemId: 'reasoning-1', summaryIndex: 0, text: '**Loading skill**' });
    summaries = appendReasoning(summaries, { itemId: 'reasoning-1', summaryIndex: 1, text: '**Inspecting page**' });
    expect(summaries).toHaveLength(2);
    expect(summaries[1].text).toBe('**Inspecting page**');
  });

  it('separates adjacent bold fragments in one summary', () => {
    const summaries = appendReasoning([{ id: 'reasoning-1:0', text: '**Loading skill**' }], {
      itemId: 'reasoning-1',
      summaryIndex: 0,
      text: '**Inspecting page**'
    });
    expect(summaries[0].text).toBe('**Loading skill**\n\n**Inspecting page**');
  });
});
