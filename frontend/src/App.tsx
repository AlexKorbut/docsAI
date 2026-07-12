import { useState } from 'react';
import { Chat } from './components/Chat';
import { Library } from './components/Library';
import { Upload } from './components/Upload';

type Tab = 'chat' | 'library';

export default function App() {
  const [tab, setTab] = useState<Tab>('chat');
  // Bump to force Library remount after a new upload.
  const [libraryVersion, setLibraryVersion] = useState(0);

  return (
    <div className="app">
      <header>
        <h1>docsAI</h1>
        <p>Семейный архив документов — медицина, ЖКХ, кредиты, недвижимость — с проверенными ответами</p>
        <Upload onUploaded={() => setLibraryVersion((v) => v + 1)} />
        <nav className="tabs">
          <button className={tab === 'chat' ? 'tab active' : 'tab'} onClick={() => setTab('chat')}>
            Чат
          </button>
          <button
            className={tab === 'library' ? 'tab active' : 'tab'}
            onClick={() => setTab('library')}
          >
            Документы
          </button>
        </nav>
      </header>
      <main>{tab === 'chat' ? <Chat /> : <Library key={libraryVersion} />}</main>
    </div>
  );
}
