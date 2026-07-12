import { Chat } from './components/Chat';
import { Upload } from './components/Upload';

export default function App() {
  return (
    <div className="app">
      <header>
        <h1>docsAI</h1>
        <p>Проверенные ответы по семейным документам — кредиты, ЖКХ, медицина, недвижимость</p>
        <Upload />
      </header>
      <main>
        <Chat />
      </main>
    </div>
  );
}
