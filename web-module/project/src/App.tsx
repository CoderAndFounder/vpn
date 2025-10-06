import React from 'react';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Promocodes from './pages/Promocodes';
import Settings from './pages/Settings';
import Users from './pages/Users';

function App() {
  // Получаем текущую страницу из URL или используем 'dashboard' по умолчанию
  const [currentPage, setCurrentPage] = React.useState(() => {
    const hash = window.location.hash.slice(1) || 'dashboard';
    return hash;
  });

  // Обновляем URL при смене страницы
  React.useEffect(() => {
    window.location.hash = currentPage;
  }, [currentPage]);

  // Слушаем изменения URL
  React.useEffect(() => {
    const handleHashChange = () => {
      const hash = window.location.hash.slice(1) || 'dashboard';
      setCurrentPage(hash);
    };

    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  const renderPage = () => {
    switch (currentPage) {
      case 'dashboard':
        return <Dashboard />;
      case 'promocodes':
        return <Promocodes />;
      case 'settings':
        return <Settings />;
      case 'users':
        return <Users />;
      default:
        return <Dashboard />;
    }
  };

  return (
    <Layout currentPage={currentPage} onPageChange={setCurrentPage}>
      {renderPage()}
    </Layout>
  );
}

export default App