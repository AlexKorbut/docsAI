import type {
  Answer,
  BatchIngestResult,
  DocumentDetail,
  DocumentInfo,
  FamilyMember,
  IngestResult,
  JobOut,
  Reminder,
} from '../types';

async function json<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? `Request failed: ${response.status}`);
  }
  return response.json();
}

export async function askQuestion(
  question: string,
  filters: { category?: string; familyMember?: string } = {},
): Promise<Answer> {
  return json(
    await fetch('/api/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        question,
        category: filters.category || null,
        family_member: filters.familyMember || null,
      }),
    }),
  );
}

async function enqueueUpload(
  endpoint: string,
  files: File[],
  familyMember?: string,
): Promise<string> {
  const form = new FormData();
  for (const file of files) form.append('files', file);
  const params = familyMember ? `?family_member=${encodeURIComponent(familyMember)}` : '';
  const data = await json<{ job_id: string }>(
    await fetch(`${endpoint}${params}`, { method: 'POST', body: form }),
  );
  return data.job_id;
}

export async function getJob(id: string): Promise<JobOut> {
  return json(await fetch(`/api/jobs/${id}`));
}

async function waitForJob(jobId: string, onProgress?: (job: JobOut) => void): Promise<JobOut> {
  for (;;) {
    const job = await getJob(jobId);
    onProgress?.(job);
    if (job.status === 'done' || job.status === 'error') return job;
    await new Promise((resolve) => setTimeout(resolve, 2000));
  }
}

export async function uploadDocument(
  files: File[],
  familyMember?: string,
  onProgress?: (job: JobOut) => void,
): Promise<IngestResult> {
  const jobId = await enqueueUpload('/api/documents', files, familyMember);
  const job = await waitForJob(jobId, onProgress);
  if (job.status === 'error' || !job.result) throw new Error(job.error ?? 'Обработка не удалась');
  return job.result as IngestResult;
}

export async function uploadBatch(
  files: File[],
  familyMember?: string,
  onProgress?: (job: JobOut) => void,
): Promise<BatchIngestResult> {
  const jobId = await enqueueUpload('/api/documents/batch', files, familyMember);
  const job = await waitForJob(jobId, onProgress);
  if (job.status === 'error' || !job.result) throw new Error(job.error ?? 'Обработка не удалась');
  return job.result as BatchIngestResult;
}

export async function updateDocument(
  id: number,
  update: { title?: string; category?: string; family_member?: string },
): Promise<DocumentInfo> {
  return json(
    await fetch(`/api/documents/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(update),
    }),
  );
}

export async function updateMarkdown(id: number, markdown: string): Promise<DocumentDetail> {
  return json(
    await fetch(`/api/documents/${id}/markdown`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ markdown }),
    }),
  );
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

export function fileUrl(documentId: number, fileId: number): string {
  return `/api/documents/${documentId}/files/${fileId}`;
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
