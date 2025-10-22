import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

function DoctorPanel() {
  const patients = useMemo(() => ([
    {
      id: 'P-1A2B-3C4D',
      name: 'Alex Johnson',
      age: 54,
      condition: 'Right knee osteoarthritis',
      lastVisit: '2025-10-10 11:00',
      status: 'awaiting_review',
    },
    {
      id: 'P-5E6F-7G8H',
      name: 'Priya Shah',
      age: 42,
      condition: 'Lumbar disc herniation',
      lastVisit: '2025-10-11 09:30',
      status: 'in_progress',
    },
    {
      id: 'P-9J1K-2L3M',
      name: 'Marco Ruiz',
      age: 61,
      condition: 'Cataract (left eye)',
      lastVisit: '2025-10-12 16:45',
      status: 'completed',
    },
  ]), [])

  const [query, setQuery] = useState('')
  const filtered = patients.filter(p =>
    (p.name.toLowerCase().includes(query.toLowerCase()) || p.id.toLowerCase().includes(query.toLowerCase()))
  )

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-200 via-white to-teal-100">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <h1 className="text-3xl font-extrabold text-gray-900">Doctor Panel</h1>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by name or ID"
            className="px-4 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-vibrant-blue"
          />
        </div>

        <div className="mt-6 grid md:grid-cols-3 gap-6">
          {filtered.map(p => (
            <div key={p.id} className="bg-white/90 backdrop-blur-sm border border-gray-200 rounded-2xl shadow-sm p-6">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-bold text-gray-900">{p.name}</h3>
                <span className={`text-xs font-semibold px-2 py-1 rounded-full ${p.status === 'completed' ? 'bg-green-50 text-green-700 border border-green-200' : p.status === 'in_progress' ? 'bg-yellow-50 text-yellow-700 border border-yellow-200' : 'bg-blue-50 text-blue-700 border border-blue-200'}`}>{p.status.replace('_', ' ')}</span>
              </div>
              <p className="text-sm text-gray-600 mt-1">ID: {p.id}</p>
              <p className="text-sm text-gray-600 mt-1">Age: {p.age}</p>
              <p className="text-sm text-gray-700 mt-2">{p.condition}</p>
              <p className="text-xs text-gray-500 mt-2">Last visit: {p.lastVisit}</p>
              <div className="mt-4 flex gap-3">
                <Link to={`/reports?id=${encodeURIComponent(p.id)}`} className="px-4 py-2 rounded-lg text-white bg-gradient-to-r from-vibrant-blue to-teal-500 hover:brightness-105 shadow">Open reports</Link>
                <Link to={`/profile`} className="px-4 py-2 rounded-lg border border-vibrant-blue text-vibrant-blue hover:bg-vibrant-blue/10">View profile</Link>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default DoctorPanel


