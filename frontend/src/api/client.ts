import type {
  Answer,
  DocumentDetail,
  DocumentInfo,
  FamilyMember,
  IngestResult,
  Reminder,
} from '../types';

async function json<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? `Request failed: ${response.status}`);
  }
  return response.json();
}

export async function askQuestion(question: string): Promise<Answer> {
  return json(
    await fetch('/api/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
    }),
  );
}

export async function uploadDocument(file: File, familyMember?: string): Promise<IngestResult> {
  const form = new FormData();
  form.append('file', file);
  const params = familyMember ? `?family_member=${encodeURIComponent(familyMember)}` : '';
  return json(await fetch(`/api/documents${params}`, { method: 'POST', body: form }));
}

export async function listDocuments(filters: {
  category?: string;
  familyMember?: string;
  q?: string;
}): Promise<DocumentInfo[]> {
  const params = new URLSearchParams();
  if (filters.category) params.set('category', filters.category);
  if (filters.familyMember) params.set('family_member', filters.familyMember);
  if (filters.q) params.set('q', filters.q);
  return json(await fetch(`/api/documents?${params}`));
}

export async function getDocument(id: number): Promise<DocumentDetail> {
  return json(await fetch(`/api/documents/${id}`));
}

export function documentFileUrl(id: number): string {
  return `/api/documents/${id}/file`;
}

export async function deleteDocument(id: number): Promise<void> {
  const response = await fetch(`/api/documents/${id}`, { method: 'DELETE' });
  if (!response.ok) throw new Error(`Delete failed: ${response.status}`);
}

export async function listFamily(): Promise<FamilyMember[]> {
  return json(await fetch('/api/family'));
}

export async function addFamilyMember(name: string, relation?: string): Promise<FamilyMember> {
  return json(
    await fetch('/api/family', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, relation: relation || null }),
    }),
  );
}

export async function listReminders(days = 30): Promise<Reminder[]> {
  return json(await fetch(`/api/reminders?days=${days}`));
}
