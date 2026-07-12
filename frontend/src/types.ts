export interface Source {
  document_id: number;
  document_title: string;
  page: number | null;
  section: string | null;
  snippet: string;
}

export interface Answer {
  answer: string;
  sources: Source[];
  confidence: number;
  warnings: string[];
}

export interface IngestResult {
  document_id: number;
  title: string;
  category: string;
  chunks: number;
  entities: number;
  payments: number;
  pages: number;
  warnings: string[];
}

export interface FileInfo {
  id: number;
  filename: string;
  mime_type: string | null;
  size_bytes: number | null;
  position: number;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  text: string;
  answer?: Answer;
}

export interface DocumentInfo {
  id: number;
  title: string;
  category: string;
  family_member: string | null;
  source_filename: string | null;
  size_bytes: number | null;
  created_at: string;
}

export interface EntityInfo {
  kind: string;
  value: string;
  normalized: string | null;
}

export interface PaymentInfo {
  amount: number;
  currency: string;
  due_date: string | null;
  description: string | null;
}

export interface DocumentDetail extends DocumentInfo {
  markdown: string;
  entities: EntityInfo[];
  payments: PaymentInfo[];
  files: FileInfo[];
}

export interface FamilyMember {
  id: number;
  name: string;
  relation: string | null;
  birth_date: string | null;
  notes: string | null;
}

export interface Reminder {
  document_id: number;
  document_title: string;
  category: string;
  amount: number;
  currency: string;
  due_date: string;
  description: string | null;
  days_left: number;
}

export const CATEGORY_LABELS: Record<string, string> = {
  loan: 'Кредит',
  utilities: 'ЖКХ',
  medical: 'Медицина',
  property: 'Собственность',
  other: 'Другое',
};
