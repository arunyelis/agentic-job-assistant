export function parseSseBlock(block) {
  let event = 'message';
  const data = [];

  for (const line of block.split(/\r?\n/)) {
    if (line.startsWith('event:')) event = line.slice(6).trim();
    if (line.startsWith('data:')) data.push(line.slice(5).trimStart());
  }

  if (!data.length) return null;
  return { event, data: JSON.parse(data.join('\n')) };
}

export async function readSse(response, onEvent) {
  if (!response.body) throw new Error('Streaming is not supported by this browser.');

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
    const blocks = buffer.split(/\r?\n\r?\n/);
    buffer = blocks.pop() || '';

    for (const block of blocks) {
      const parsed = parseSseBlock(block);
      if (parsed) onEvent(parsed);
    }

    if (done) break;
  }

  if (buffer.trim()) {
    const parsed = parseSseBlock(buffer);
    if (parsed) onEvent(parsed);
  }
}
