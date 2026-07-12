import { FormEvent, useEffect, useState } from 'react';
import { askQuestion, listFamily } from '../api/client';
import type { ChatMessage, FamilyMember } from '../types';
import { CATEGORY_LABELS } from '../types';
import { ConfidenceBadge } from './ConfidenceBadge';
import { Sources } from './Sources';

export function Chat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [category, setCategory] = useState('');
  const [member, setMember] = useState('');
  const [family, setFamily] = useState<FamilyMember[]>([]);

  useEffect(() => {
    listFamily()
      .then(setFamily)
      .catch(() => setFamily([]));
  }, []);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    const question = input.trim();
    if (!question || busy) return;
    setInput('');
    setMessages((prev) => [...prev, { role: 'user', text: question }]);
    setBusy(true);
    try {
      const answer = await askQuestion(question, {
        category: category || undefined,
        familyMember: member || undefined,
      });
      setMessages((prev) => [...prev, { role: 'assistant', text: answer.answer, answer }]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', text: 'Не удалось получить ответ. Попробуйте ещё раз.' },
      ]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="chat">
      <div className="chat-filters">
        <select value={category} onChange={(e) => setCategory(e.target.value)}>
          <option value="">Все категории</option>
          {Object.entries(CATEGORY_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
        <select value={member} onChange={(e) => setMember(e.target.value)}>
          <option value="">Вся семья</option>
          {family.map((m) => (
            <option key={m.id} value={m.name}>
              {m.name}
            </option>
          ))}
        </select>
      </div>
      <div className="messages">
        {messages.length === 0 && (
          <p className="hint">
            Задайте вопрос по семейным документам, например: «Сколько у нас всего долгов по
            кредитам на июль 2026?»
          </p>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`message message-${m.role}`}>
            <p>{m.text}</p>
            {m.answer && (
              <>
                <ConfidenceBadge value={m.answer.confidence} />
                {m.answer.warnings.map((w, j) => (
                  <p key={j} className="warning">
                    ⚠️ {w}
                  </p>
                ))}
                <Sources sources={m.answer.sources} />
              </>
            )}
          </div>
        ))}
        {busy && <div className="message message-assistant">Агенты работают…</div>}
      </div>
      <form onSubmit={onSubmit} className="input-row">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ваш вопрос…"
          disabled={busy}
        />
        <button type="submit" disabled={busy || !input.trim()}>
          Спросить
        </button>
      </form>
    </div>
  );
}
