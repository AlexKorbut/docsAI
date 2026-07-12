import { useRef, useState } from 'react';
import { uploadDocument } from '../api/client';

export function Upload() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onChange() {
    const file = inputRef.current?.files?.[0];
    if (!file) return;
    setBusy(true);
    setStatus(`Загрузка «${file.name}»...`);
    try {
      const result = await uploadDocument(file);
      setStatus(
        `«${result.title}» (${result.category}): ${result.chunks} фрагментов, ` +
          `${result.payments} платежей`,
      );
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Ошибка загрузки');
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = '';
    }
  }

  return (
    <div className="upload">
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
      {status && <p className="upload-status">{status}</p>}
    </div>
  );
}
