import { describe, expect, it } from 'vitest';

import { extractProposal, looksLikeApplicationConfirmation } from './extract';

function page(html: string) {
  document.documentElement.innerHTML = html;
  return document;
}

describe('application page extraction', () => {
  it.each([
    ['Workday', 'https://acme.wd5.myworkdayjobs.com/en-US/jobs/job/123'],
    ['Greenhouse', 'https://boards.greenhouse.io/acme/jobs/123'],
    ['Lever', 'https://jobs.lever.co/acme/123'],
    ['Generic', 'https://careers.acme.example/jobs/123']
  ])('extracts structured job data from a %s-style page', (_name, url) => {
    const proposal = extractProposal(
      page(`
        <head>
          <script type="application/ld+json">
            {"@type":"JobPosting","title":"AI Platform Engineer","hiringOrganization":{"name":"Acme Labs"}}
          </script>
        </head>
        <body><h1>AI Platform Engineer</h1><p>Thank you for applying. Your application has been received.</p></body>
      `),
      new URL(url)
    );
    expect(proposal.company).toBe('Acme Labs');
    expect(proposal.role).toBe('AI Platform Engineer');
    expect(proposal.confidence).toBeGreaterThan(0.9);
  });

  it('detects a common submission confirmation', () => {
    const current = page('<body><main><h1>Application submitted</h1><p>We received your application.</p></main></body>');
    expect(looksLikeApplicationConfirmation(current, new URL('https://jobs.example.com/complete'))).toBe(true);
  });

  it('does not treat a normal job page as a completed application', () => {
    const current = page('<body><h1>Software Engineer</h1><button>Apply now</button></body>');
    expect(looksLikeApplicationConfirmation(current, new URL('https://jobs.example.com/123'))).toBe(false);
  });

  it('blocks automatic LinkedIn capture', () => {
    const current = page('<body><h1>Application submitted</h1></body>');
    const url = new URL('https://www.linkedin.com/jobs/view/123');
    expect(extractProposal(current, url).blocked).toBe(true);
    expect(looksLikeApplicationConfirmation(current, url)).toBe(false);
  });
});
