import React from 'react';
import { Plus, Edit2, Trash2 } from 'lucide-react';

export default function Promocodes() {
  const [showModal, setShowModal] = React.useState(false);

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-semibold">Промокоды</h1>
        <button
          onClick={() => setShowModal(true)}
          className="px-4 py-2 bg-blue-600 text-white rounded-md flex items-center"
        >
          <Plus className="w-4 h-4 mr-2" />
          Добавить промокод
        </button>
      </div>

      <div className="bg-white rounded-lg shadow">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="text-left bg-gray-50">
                <th className="px-6 py-3">ID</th>
                <th className="px-6 py-3">Код</th>
                <th className="px-6 py-3">Скидка</th>
                <th className="px-6 py-3">Лимит</th>
                <th className="px-6 py-3">Использовано</th>
                <th className="px-6 py-3">Начало</th>
                <th className="px-6 py-3">Конец</th>
                <th className="px-6 py-3">Действия</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-t">
                <td className="px-6 py-4">#1</td>
                <td className="px-6 py-4">WELCOME2024</td>
                <td className="px-6 py-4">20%</td>
                <td className="px-6 py-4">100</td>
                <td className="px-6 py-4">45</td>
                <td className="px-6 py-4">01.03.2024</td>
                <td className="px-6 py-4">31.03.2024</td>
                <td className="px-6 py-4">
                  <div className="flex space-x-2">
                    <button className="p-1 text-blue-600 hover:bg-blue-50 rounded">
                      <Edit2 className="w-4 h-4" />
                    </button>
                    <button className="p-1 text-red-600 hover:bg-red-50 rounded">
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Add Promocode Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h2 className="text-xl font-semibold mb-4">Добавить промокод</h2>
            <form>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Код</label>
                  <input type="text" className="mt-1 block w-full rounded-md border-gray-300 shadow-sm" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Скидка (%)</label>
                  <input type="number" className="mt-1 block w-full rounded-md border-gray-300 shadow-sm" />
                </div>
                <div className="flex space-x-4">
                  <button
                    type="submit"
                    className="flex-1 bg-blue-600 text-white px-4 py-2 rounded-md"
                  >
                    Сохранить
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowModal(false)}
                    className="flex-1 bg-gray-100 text-gray-700 px-4 py-2 rounded-md"
                  >
                    Отмена
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}