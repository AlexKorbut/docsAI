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
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  text: string;
  answer?: Answer;
}
