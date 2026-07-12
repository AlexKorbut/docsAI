import type { Answer, IngestResult } from '../types';

export async function askQuestion(question: string): Promise<Answer> {
  const response = await fetch('/api/query', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  });
  if (!response.ok) throw new Error(`Query failed: ${response.status}`);
  return response.json();
}

export async function uploadDocument(file: File): Promise<IngestResult> {
  const form = new FormData();
  form.append('file', file);
  const response = await fetch('/api/documents', { method: 'POST', body: form });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? `Upload failed: ${response.status}`);
  }
  return response.json();
}
