import React from 'react';
import { MoreVertical } from 'lucide-react';

export default function Users() {
  const [showUserModal, setShowUserModal] = React.useState(false);

  return (
    <div>
      <h1 className="text-2xl font-semibold mb-6">Пользователи</h1>

      <div className="bg-white rounded-lg shadow">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="text-left bg-gray-50">
                <th className="px-6 py-3">ID</th>
                <th className="px-6 py-3">Имя пользователя</th>
                <th className="px-6 py-3">Email</th>
                <th className="px-6 py-3">Дата регистрации</th>
                <th className="px-6 py-3">Текущий план</th>
                <th className="px-6 py-3">Статус</th>
                <th className="px-6 py-3">Последний вход</th>
                <th className="px-6 py-3">Действия</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-t">
                <td className="px-6 py-4">#1</td>
                <td className="px-6 py-4">Иван Иванов</td>
                <td className="px-6 py-4">ivan@example.com</td>
                <td className="px-6 py-4">01.03.2024</td>
                <td className="px-6 py-4">Премиум</td>
                <td className="px-6 py-4">
                  <span className="px-2 py-1 bg-green-100 text-green-800 rounded-full text-sm">
                    Активный
                  </span>
                </td>
                <td className="px-6 py-4">14.03.2024</td>
                <td className="px-6 py-4">
                  <button
                    onClick={() => setShowUserModal(true)}
                    className="p-1 hover:bg-gray-100 rounded"
                  >
                    <MoreVertical className="w-4 h-4" />
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* User Details Modal */}
      {showUserModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
          <div className="bg-white rounded-lg p-6 w-full max-w-2xl">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-semibold">Информация о пользователе</h2>
              <button
                onClick={() => setShowUserModal(false)}
                className="text-gray-500 hover:text-gray-700"
              >
                ×
              </button>
            </div>
            
            <div className="space-y-6">
              <div>
                <h3 className="font-medium mb-2">Личная информация</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-gray-500">Имя</p>
                    <p>Иван Иванов</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">Email</p>
                    <p>ivan@example.com</p>
                  </div>
                </div>
              </div>

              <div>
                <h3 className="font-medium mb-2">История платежей</h3>
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left bg-gray-50">
                      <th className="px-4 py-2">Дата</th>
                      <th className="px-4 py-2">Сумма</th>
                      <th className="px-4 py-2">Статус</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr className="border-t">
                      <td className="px-4 py-2">14.03.2024</td>
                      <td className="px-4 py-2">₽1,999</td>
                      <td className="px-4 py-2">Оплачен</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <div>
                <h3 className="font-medium mb-2">Детали подписки</h3>
                <div className="bg-gray-50 p-4 rounded">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-sm text-gray-500">Текущий план</p>
                      <p>Премиум</p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-500">Дата окончания</p>
                      <p>14.04.2024</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}