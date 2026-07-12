import { useEffect, useState } from 'react';
import { listReminders } from '../api/client';
import type { Reminder } from '../types';

export function Reminders() {
  const [reminders, setReminders] = useState<Reminder[]>([]);

  useEffect(() => {
    listReminders(30)
      .then(setReminders)
      .catch(() => setReminders([]));
  }, []);

  if (reminders.length === 0) return null;

  return (
    <div className="reminders">
      <h3>⏰ Ближайшие платежи (30 дней)</h3>
      <ul>
        {reminders.map((r, i) => (
          <li key={i} className={r.days_left <= 3 ? 'reminder-urgent' : ''}>
            <strong>
              {r.amount.toLocaleString('ru-RU')} {r.currency}
            </strong>{' '}
            — {r.due_date} ({r.days_left === 0 ? 'сегодня' : `через ${r.days_left} дн.`})
            <br />
            <span className="reminder-doc">
              {r.document_title}
              {r.description ? ` · ${r.description}` : ''}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
