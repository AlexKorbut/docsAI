import { useEffect, useRef, useState } from 'react';
import { addFamilyMember, listFamily, uploadDocument } from '../api/client';
import type { FamilyMember } from '../types';

const NEW_MEMBER = '__new__';

export function Upload({ onUploaded }: { onUploaded?: () => void }) {
  const cameraRef = useRef<HTMLInputElement>(null);
  const filesRef = useRef<HTMLInputElement>(null);
  const [status, setStatus] = useState<string | null>(null);
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
    setStatus(
      files.length === 1
        ? `Обработка «${files[0].name}»…`
        : `Распознавание ${files.length} страниц… это может занять минуту`,
    );
    try {
      const result = await uploadDocument(files, member || undefined);
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
      </div>

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
      {warnings.map((w, i) => (
        <p key={i} className="warning">
          ⚠️ {w}
        </p>
      ))}
    </div>
  );
}
