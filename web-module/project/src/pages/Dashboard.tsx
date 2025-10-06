import React from 'react';
import { Users, Crown, DollarSign } from 'lucide-react';

export default function Dashboard() {
  return (
    <div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        <div className="bg-gray-800 rounded-lg shadow-lg p-6">
          <div className="flex items-center">
            <div className="p-3 bg-blue-900 rounded-full">
              <Users className="w-6 h-6 text-blue-400" />
            </div>
            <div className="ml-4">
              <h3 className="text-gray-400 text-sm">Всего пользователей</h3>
              <p className="text-2xl font-semibold text-white">1,234</p>
            </div>
          </div>
        </div>
        
        <div className="bg-gray-800 rounded-lg shadow-lg p-6">
          <div className="flex items-center">
            <div className="p-3 bg-green-900 rounded-full">
              <Crown className="w-6 h-6 text-green-400" />
            </div>
            <div className="ml-4">
              <h3 className="text-gray-400 text-sm">Популярный план</h3>
              <p className="text-2xl font-semibold text-white">Премиум</p>
            </div>
          </div>
        </div>
        
        <div className="bg-gray-800 rounded-lg shadow-lg p-6">
          <div className="flex items-center">
            <div className="p-3 bg-purple-900 rounded-full">
              <DollarSign className="w-6 h-6 text-purple-400" />
            </div>
            <div className="ml-4">
              <h3 className="text-gray-400 text-sm">Общий доход</h3>
              <p className="text-2xl font-semibold text-white">₽123,456</p>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-gray-800 rounded-lg shadow-lg">
        <div className="p-6">
          <h2 className="text-lg font-semibold mb-4 text-white">Последние платежи</h2>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left bg-gray-700">
                  <th className="px-6 py-3 text-gray-300">ID транзакции</th>
                  <th className="px-6 py-3 text-gray-300">Пользователь</th>
                  <th className="px-6 py-3 text-gray-300">Сумма</th>
                  <th className="px-6 py-3 text-gray-300">Дата</th>
                  <th className="px-6 py-3 text-gray-300">Статус</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-t border-gray-700">
                  <td className="px-6 py-4 text-gray-300">#123456</td>
                  <td className="px-6 py-4 text-gray-300">Иван Иванов</td>
                  <td className="px-6 py-4 text-gray-300">₽1,999</td>
                  <td className="px-6 py-4 text-gray-300">2024-03-14</td>
                  <td className="px-6 py-4">
                    <span className="px-2 py-1 bg-green-900 text-green-300 rounded-full text-sm">
                      Выполнен
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}