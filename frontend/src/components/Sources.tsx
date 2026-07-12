import type { Source } from '../types';

export function Sources({ sources }: { sources: Source[] }) {
  if (sources.length === 0) return null;
  return (
    <details className="sources">
      <summary>Источники ({sources.length})</summary>
      <ul>
        {sources.map((s, i) => (
          <li key={i}>
            <strong>{s.document_title}</strong>
            {s.section ? ` — ${s.section}` : ''}
            {s.page ? `, стр. ${s.page}` : ''}
            <blockquote>{s.snippet}</blockquote>
          </li>
        ))}
      </ul>
    </details>
  );
}
