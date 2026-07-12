import { useEffect, useRef, useState } from 'react';
import { addFamilyMember, listFamily, uploadBatch, uploadDocument } from '../api/client';
import type { FamilyMember } from '../types';

const NEW_MEMBER = '__new__';

export function Upload({ onUploaded }: { onUploaded?: () => void }) {
  const cameraRef = useRef<HTMLInputElement>(null);
  const filesRef = useRef<HTMLInputElement>(null);
  const batchRef = useRef<HTMLInputElement>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [batchResults, setBatchResults] = useState<string[]>([]);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [family, setFamily] = useState<FamilyMember[]>([]);
  const [member, setMember] = useState('');
  // Photos taken one-by-one with the camera accumulate here until "send".
  const [pendingPhotos, setPendingPhotos] = useState<File[]>([]);

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

  async function send(files: File[]) {
    if (files.length === 0) return;
    setBusy(true);
    setWarnings([]);
    setBatchResults([]);
    setStatus(
      files.length === 1
        ? `Обработка «${files[0].name}»…`
        : `Распознавание ${files.length} страниц… это может занять минуту`,
    );
    try {
      const result = await uploadDocument(files, member || undefined, (job) => {
        if (job.status === 'processing') setStatus('Распознаю документ…');
      });
      setStatus(
        `«${result.title}» (${result.category}): ${result.pages} стр., ` +
          `${result.payments} платежей`,
      );
      setWarnings(result.warnings);
      setPendingPhotos([]);
      onUploaded?.();
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Ошибка загрузки');
    } finally {
      setBusy(false);
      if (cameraRef.current) cameraRef.current.value = '';
      if (filesRef.current) filesRef.current.value = '';
    }
  }

  function onCameraShot() {
    const file = cameraRef.current?.files?.[0];
    if (!file) return;
    setPendingPhotos((prev) => [...prev, file]);
    setStatus(null);
    if (cameraRef.current) cameraRef.current.value = '';
  }

  function onFilesPicked() {
    const files = Array.from(filesRef.current?.files ?? []);
    if (files.length === 0) return;
    void send(files);
  }

  async function onBatchPicked() {
    const files = Array.from(batchRef.current?.files ?? []);
    if (files.length === 0) return;
    setBusy(true);
    setWarnings([]);
    setBatchResults([]);
    setStatus(`Распознаю пачку со сканера… (${files.length} файлов, это займёт время)`);
    try {
      const result = await uploadBatch(files, member || undefined, (job) => {
        if (job.status === 'processing') {
          setStatus(`Распознано страниц: ${job.progress.done} из ${job.progress.total}…`);
        }
      });
      setStatus(`Из пачки сохранено документов: ${result.documents.length}`);
      setBatchResults(
        result.documents.map(
          (d) => `«${d.title}» — ${d.category}, ${d.pages} стр., платежей: ${d.payments}`,
        ),
      );
      setWarnings([...result.warnings, ...result.documents.flatMap((d) => d.warnings)]);
      onUploaded?.();
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Ошибка пакетной загрузки');
    } finally {
      setBusy(false);
      if (batchRef.current) batchRef.current.value = '';
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
          📷 Сфотографировать
          <input
            ref={cameraRef}
            type="file"
            accept="image/*"
            capture="environment"
            onChange={onCameraShot}
            disabled={busy}
            hidden
          />
        </label>

        <label className="upload-button secondary">
          {busy ? 'Обработка…' : 'Выбрать фото/файл'}
          <input
            ref={filesRef}
            type="file"
            accept="image/*,.heic,.heif,.pdf,.txt,.md"
            multiple
            onChange={onFilesPicked}
            disabled={busy}
            hidden
          />
        </label>

        <label className="upload-button secondary">
          📚 Пачка со сканера
          <input
            ref={batchRef}
            type="file"
            accept="image/*,.heic,.heif"
            multiple
            onChange={() => void onBatchPicked()}
            disabled={busy}
            hidden
          />
        </label>
      </div>

      <p className="upload-hint">
        Одна загрузка = <strong>один</strong> документ: несколько фото считаются страницами
        одного документа. Разные документы загружайте по отдельности. Если отсканировали
        пачку разных документов разом — используйте «Пачка со сканера»: система разделит
        страницы по документам автоматически (границы стоит проверить).
      </p>

      {pendingPhotos.length > 0 && (
        <div className="pending-photos">
          <span>
            Снято страниц: {pendingPhotos.length}
            {' — '}сфотографируйте следующую или отправьте
          </span>
          <button disabled={busy} onClick={() => void send(pendingPhotos)}>
            Отправить документ ({pendingPhotos.length} стр.)
          </button>
          <button className="link-button" disabled={busy} onClick={() => setPendingPhotos([])}>
            отмена
          </button>
        </div>
      )}

      {status && <p className="upload-status">{status}</p>}
      {batchResults.length > 0 && (
        <ul className="batch-results">
          {batchResults.map((r, i) => (
            <li key={i}>{r}</li>
          ))}
        </ul>
      )}
      {warnings.map((w, i) => (
        <p key={i} className="warning">
          ⚠️ {w}
        </p>
      ))}
    </div>
  );
}
