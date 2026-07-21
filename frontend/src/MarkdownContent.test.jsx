import { renderToString } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import MarkdownContent from './MarkdownContent.jsx';

describe('MarkdownContent', () => {
  it('renders headings, emphasis, lists, and tables', () => {
    const markdown = [
      '## Match summary',
      '',
      '**Strong match**',
      '',
      '1. Python',
      '2. React',
      '',
      '| Skill | Fit |',
      '| --- | --- |',
      '| MCP | Strong |'
    ].join('\n');

    const html = renderToString(<MarkdownContent>{markdown}</MarkdownContent>);

    expect(html).toContain('<h2>Match summary</h2>');
    expect(html).toContain('<strong>Strong match</strong>');
    expect(html).toContain('<ol>');
    expect(html).toContain('<table>');
  });
});
