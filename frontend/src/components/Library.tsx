import { useCallback, useEffect, useState } from 'react';
import { deleteDocument, fileUrl, getDocument, listDocuments } from '../api/client';
import type { DocumentDetail, DocumentInfo } from '../types';
import { CATEGORY_LABELS } from '../types';
import { Reminders } from './Reminders';

function formatSize(bytes: number | null): string {
  if (!bytes) return '';
  if (bytes < 1024) return `${bytes} Б`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} КБ`;
  return `${(bytes / 1024 / 1024).toFixed(1)} МБ`;
}

export function Library() {
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [category, setCategory] = useState('');
  const [search, setSearch] = useState('');
  const [selected, setSelected] = useState<DocumentDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(() => {
    listDocuments({ category: category || undefined, q: search || undefined })
      .then(setDocuments)
      .catch((e) => setError(e instanceof Error ? e.message : 'Ошибка загрузки списка'));
  }, [category, search]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function open(id: number) {
    try {
      setSelected(await getDocument(id));
    } catch {
      setError('Не удалось открыть документ');
    }
  }

  async function remove(id: number) {
    if (!window.confirm('Удалить документ безвозвратно?')) return;
    try {
      await deleteDocument(id);
      setSelected(null);
      refresh();
    } catch {
      setError('Не удалось удалить документ');
    }
  }

  return (
    <div className="library">
      <Reminders />
      <div className="library-filters">
        <select value={category} onChange={(e) => setCategory(e.target.value)}>
          <option value="">Все категории</option>
          {Object.entries(CATEGORY_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
        <input
          placeholder="Поиск по названию…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>
      {error && <p className="warning">{error}</p>}

      {selected ? (
        <div className="doc-detail">
          <button className="link-button" onClick={() => setSelected(null)}>
            ← к списку
          </button>
          <h2>{selected.title}</h2>
          <p className="doc-meta">
            {CATEGORY_LABELS[selected.category] ?? selected.category}
            {selected.family_member ? ` · ${selected.family_member}` : ''}
            {selected.source_filename ? ` · ${selected.source_filename}` : ''}
            {selected.size_bytes ? ` · ${formatSize(selected.size_bytes)}` : ''}
          </p>
          <div className="doc-actions">
            {selected.files.map((f) => (
              <a key={f.id} href={fileUrl(selected.id, f.id)} download>
                {selected.files.length > 1 ? `Стр. ${f.position + 1}` : 'Скачать оригинал'}
              </a>
            ))}
            <button className="danger" onClick={() => remove(selected.id)}>
              Удалить
            </button>
          </div>

          {selected.files.some((f) => f.mime_type?.startsWith('image/')) && (
            <div className="photo-strip">
              {selected.files
                .filter((f) => f.mime_type?.startsWith('image/'))
                .map((f) => (
                  <a key={f.id} href={fileUrl(selected.id, f.id)} target="_blank" rel="noreferrer">
                    <img src={fileUrl(selected.id, f.id)} alt={f.filename} loading="lazy" />
                  </a>
                ))}
            </div>
          )}

          {selected.payments.length > 0 && (
            <>
              <h3>Платежи</h3>
              <table>
                <thead>
                  <tr>
                    <th>Сумма</th>
                    <th>Дата</th>
                    <th>Назначение</th>
                  </tr>
                </thead>
                <tbody>
                  {selected.payments.map((p, i) => (
                    <tr key={i}>
                      <td>
                        {p.amount.toLocaleString('ru-RU')} {p.currency}
                      </td>
                      <td>{p.due_date ?? '—'}</td>
                      <td>{p.description ?? '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}

          {selected.entities.length > 0 && (
            <>
              <h3>Извлечённые данные</h3>
              <ul className="entity-list">
                {selected.entities.map((e, i) => (
                  <li key={i}>
                    <span className="entity-kind">{e.kind}</span> {e.value}
                    {e.normalized && e.normalized !== e.value ? ` (${e.normalized})` : ''}
                  </li>
                ))}
              </ul>
            </>
          )}

          <h3>Содержимое</h3>
          <pre className="doc-markdown">{selected.markdown}</pre>
        </div>
      ) : (
        <ul className="doc-list">
          {documents.length === 0 && <p className="hint">Документов пока нет — загрузите первый.</p>}
          {documents.map((d) => (
            <li key={d.id} onClick={() => open(d.id)}>
              <strong>{d.title}</strong>
              <span className="doc-meta">
                {CATEGORY_LABELS[d.category] ?? d.category}
                {d.family_member ? ` · ${d.family_member}` : ''}
                {' · '}
                {new Date(d.created_at).toLocaleDateString('ru-RU')}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
