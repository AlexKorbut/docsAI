import { FormEvent, useState } from 'react';
import { askQuestion } from '../api/client';
import type { ChatMessage } from '../types';
import { ConfidenceBadge } from './ConfidenceBadge';
import { Sources } from './Sources';

export function Chat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    const question = input.trim();
    if (!question || busy) return;
    setInput('');
    setMessages((prev) => [...prev, { role: 'user', text: question }]);
    setBusy(true);
    try {
      const answer = await askQuestion(question);
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
