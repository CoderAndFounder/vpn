import React from 'react';
import { Menu, User, Bell, ChevronDown } from 'lucide-react';

interface LayoutProps {
  children: React.ReactNode;
  currentPage: string;
  onPageChange: (page: string) => void;
}

export default function Layout({ children, currentPage, onPageChange }: LayoutProps) {
  const [sidebarOpen, setSidebarOpen] = React.useState(false);

  return (
    <div className="min-h-screen bg-gray-900">
      {/* Header */}
      <header className="bg-gray-800 shadow-lg">
        <div className="flex items-center justify-between px-4 py-3">
          <div className="flex items-center">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="p-2 rounded-md lg:hidden text-gray-300 hover:text-white"
            >
              <Menu className="w-6 h-6" />
            </button>
            <h1 className="ml-2 text-xl font-semibold text-white">Админ панель</h1>
          </div>
          <div className="flex items-center space-x-4">
            <button className="p-2 text-gray-300 hover:text-white">
              <Bell className="w-6 h-6" />
            </button>
            <div className="flex items-center">
              <img
                src="https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?ixlib=rb-1.2.1&auto=format&fit=facearea&facepad=2&w=256&h=256&q=80"
                alt="Profile"
                className="w-8 h-8 rounded-full border-2 border-gray-600"
              />
              <ChevronDown className="w-4 h-4 ml-2 text-gray-300" />
            </div>
          </div>
        </div>
      </header>

      <div className="flex">
        {/* Sidebar */}
        <aside className={`w-64 bg-gray-800 shadow-lg ${sidebarOpen ? 'block' : 'hidden'} lg:block`}>
          <nav className="mt-5 px-2">
            <button
              onClick={() => onPageChange('dashboard')}
              className={`w-full flex items-center px-4 py-2 text-gray-300 hover:bg-gray-700 rounded-md ${
                currentPage === 'dashboard' ? 'bg-gray-700 text-white' : ''
              }`}
            >
              Панель управления
            </button>
            <button
              onClick={() => onPageChange('promocodes')}
              className={`w-full flex items-center px-4 py-2 text-gray-300 hover:bg-gray-700 rounded-md ${
                currentPage === 'promocodes' ? 'bg-gray-700 text-white' : ''
              }`}
            >
              Промокоды
            </button>
            <button
              onClick={() => onPageChange('users')}
              className={`w-full flex items-center px-4 py-2 text-gray-300 hover:bg-gray-700 rounded-md ${
                currentPage === 'users' ? 'bg-gray-700 text-white' : ''
              }`}
            >
              Пользователи
            </button>
            <button
              onClick={() => onPageChange('settings')}
              className={`w-full flex items-center px-4 py-2 text-gray-300 hover:bg-gray-700 rounded-md ${
                currentPage === 'settings' ? 'bg-gray-700 text-white' : ''
              }`}
            >
              Настройки
            </button>
          </nav>
        </aside>

        {/* Main Content */}
        <main className="flex-1 p-6">
          {children}
        </main>
      </div>
    </div>
  );
}