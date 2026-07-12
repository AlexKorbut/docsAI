import { useEffect, useRef, useState } from 'react';
import { addFamilyMember, listFamily, uploadDocument } from '../api/client';
import type { FamilyMember } from '../types';

const NEW_MEMBER = '__new__';

export function Upload({ onUploaded }: { onUploaded?: () => void }) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [family, setFamily] = useState<FamilyMember[]>([]);
  const [member, setMember] = useState('');

  useEffect(() => {
    listFamily()
      .then(setFamily)
      .catch(() => setFamily([]));
  }, []);

  async function onMemberChange(value: string) {
    if (value !== NEW_MEMBER) {
      setMember(value);
      return;
    }
    const name = window.prompt('Имя члена семьи:')?.trim();
    if (!name) return;
    try {
      const created = await addFamilyMember(name);
      setFamily((prev) => [...prev, created]);
      setMember(created.name);
    } catch {
      setStatus('Не удалось добавить члена семьи');
    }
  }

  async function onChange() {
    const file = inputRef.current?.files?.[0];
    if (!file) return;
    setBusy(true);
    setStatus(`Загрузка «${file.name}»…`);
    try {
      const result = await uploadDocument(file, member || undefined);
      setStatus(
        `«${result.title}» (${result.category}): ${result.chunks} фрагментов, ` +
          `${result.payments} платежей`,
      );
      onUploaded?.();
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Ошибка загрузки');
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = '';
    }
  }

  return (
    <div className="upload">
      <div className="upload-row">
        <select value={member} onChange={(e) => onMemberChange(e.target.value)}>
          <option value="">Вся семья</option>
          {family.map((m) => (
            <option key={m.id} value={m.name}>
              {m.name}
              {m.relation ? ` (${m.relation})` : ''}
            </option>
          ))}
          <option value={NEW_MEMBER}>+ добавить члена семьи…</option>
        </select>
        <label className="upload-button">
          {busy ? 'Обработка…' : '+ Загрузить документ'}
          <input
            ref={inputRef}
            type="file"
            accept=".pdf,.txt,.md"
            onChange={onChange}
            disabled={busy}
            hidden
          />
        </label>
      </div>
      {status && <p className="upload-status">{status}</p>}
    </div>
  );
}
