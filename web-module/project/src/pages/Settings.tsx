import React from 'react';

export default function Settings() {
  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow">
        <div className="p-6">
          <h2 className="text-xl font-semibold mb-4">Настройки YooKassa</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">API Ключ</label>
              <input
                type="password"
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">ID магазина</label>
              <input
                type="text"
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
              />
            </div>
            <div className="flex items-center">
              <input
                type="checkbox"
                className="rounded border-gray-300 text-blue-600 shadow-sm"
              />
              <label className="ml-2 text-sm text-gray-700">Тестовый режим</label>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow">
        <div className="p-6">
          <h2 className="text-xl font-semibold mb-4">Настройки Telegram бота</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">Токен бота</label>
              <input
                type="password"
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Имя бота</label>
              <input
                type="text"
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Webhook URL</label>
              <input
                type="text"
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}