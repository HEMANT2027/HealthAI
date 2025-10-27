import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'

function DoctorPanel() {
  const [patients, setPatients] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [query, setQuery] = useState('')

  const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

  useEffect(() => {
    fetchMyPatients()
  }, [])

  const fetchMyPatients = async () => {
    try {
      setLoading(true)
      setError(null)

      const token = localStorage.getItem('token')
      if (!token) {
        setError('Not authenticated')
        setLoading(false)
        return
      }

      const response = await fetch(`${API_BASE_URL}/admin/doctor/my-patients`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Failed to fetch patients')
      }

      setPatients(data.patients || [])
    } catch (err) {
      console.error('Error fetching patients:', err)
      setError(err.message || 'Failed to load patients')
    } finally {
      setLoading(false)
    }
  }

  const filtered = patients.filter(p =>
  (p.pseudonym_id.toLowerCase().includes(query.toLowerCase()) ||
    p.patient_summary.toLowerCase().includes(query.toLowerCase()))
  )

  const getStatusBadge = (patient) => {
    // Determine status based on patient data
    if (patient.visits && patient.visits.length > 0) {
      const lastVisit = patient.visits[patient.visits.length - 1]
      const status = lastVisit.status || 'in_progress'

      const statusStyles = {
        'completed': 'bg-green-50 text-green-700 border border-green-200',
        'in_progress': 'bg-yellow-50 text-yellow-700 border border-yellow-200',
        'awaiting_review': 'bg-blue-50 text-blue-700 border border-blue-200',
        'pending': 'bg-gray-50 text-gray-700 border border-gray-200'
      }

      return (
        <span className={`text-xs font-semibold px-2 py-1 rounded-full ${statusStyles[status] || statusStyles['pending']}`}>
          {status.replace('_', ' ')}
        </span>
      )
    }

    return (
      <span className="text-xs font-semibold px-2 py-1 rounded-full bg-gray-50 text-gray-700 border border-gray-200">
        No visits
      </span>
    )
  }

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A'
    try {
      const date = new Date(dateString)
      return date.toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      })
    } catch {
      return 'Invalid date'
    }
  }

  const getLastVisitDate = (patient) => {
    if (patient.visits && patient.visits.length > 0) {
      const lastVisit = patient.visits[patient.visits.length - 1]
      return formatDate(lastVisit.visit_timestamp)
    }
    return formatDate(patient.created_at)
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-200 via-white to-teal-100 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-vibrant-blue"></div>
          <p className="mt-4 text-gray-700 font-medium">Loading patients...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-200 via-white to-teal-100">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        {/* Header */}
        <div className="flex items-center justify-between flex-wrap gap-3 mb-6">
          <div>
            <h1 className="text-3xl font-extrabold text-gray-900">Doctor Panel</h1>
            <p className="text-gray-600 mt-1">
              {patients.length} {patients.length === 1 ? 'patient' : 'patients'} assigned to you
            </p>
          </div>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by ID or summary"
            className="px-4 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-vibrant-blue shadow-sm"
          />
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl">
            <div className="flex items-center gap-2 text-red-800">
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
              <span className="font-medium">{error}</span>
            </div>
          </div>
        )}

        {/* No Patients Message */}
        {!loading && !error && patients.length === 0 && (
          <div className="bg-white/90 backdrop-blur-sm border border-gray-200 rounded-2xl shadow-sm p-12 text-center">
            <svg className="w-16 h-16 text-gray-400 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
            </svg>
            <h3 className="text-xl font-bold text-gray-900 mb-2">No Patients Assigned</h3>
            <p className="text-gray-600">You don't have any patients assigned to you yet.</p>
            <p className="text-sm text-gray-500 mt-2">Contact the admin to get patients assigned.</p>
          </div>
        )}

        {/* Patients Grid */}
        {!loading && !error && filtered.length === 0 && patients.length > 0 && (
          <div className="bg-white/90 backdrop-blur-sm border border-gray-200 rounded-2xl shadow-sm p-8 text-center">
            <p className="text-gray-600">No patients match your search.</p>
          </div>
        )}

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filtered.map(patient => (
            <div key={patient.id} className="bg-white/90 backdrop-blur-sm border border-gray-200 rounded-2xl shadow-sm p-6 hover:shadow-lg transition-shadow">
              {/* Header */}
              <div className="flex items-start justify-between mb-3">
                <div className="flex-1">
                  <h3 className="text-lg font-bold text-gray-900">{patient.pseudonym_id}</h3>
                  <p className="text-xs text-gray-500 mt-1">Patient ID</p>
                </div>
                {getStatusBadge(patient)}
              </div>

              {/* Patient Summary */}
              <div className="mb-4">
                <p className="text-sm text-gray-700 line-clamp-3">
                  {patient.patient_summary || 'No summary available'}
                </p>
              </div>

              {/* Metadata */}
              <div className="space-y-2 mb-4">
                <div className="flex items-center gap-2 text-xs text-gray-600">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                  <span>Last visit: {getLastVisitDate(patient)}</span>
                </div>
                <div className="flex items-center gap-2 text-xs text-gray-600">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <span>Visits: {patient.visits?.length || 0}</span>
                </div>
              </div>

              {/* Actions */}
              <div className="flex gap-3">
                <Link
                  to={`/profile/${patient.pseudonym_id}`}
                  className="flex-1 px-4 py-2 rounded-lg text-center text-white bg-gradient-to-r from-vibrant-blue to-teal-500 hover:brightness-105 shadow transition-all"
                >
                  View Details
                </Link>
                <Link
                  to={`/reports/${patient.pseudonym_id}`}
                  className="px-4 py-2 rounded-lg border border-vibrant-blue text-vibrant-blue hover:bg-vibrant-blue/10 transition-all flex items-center justify-center"
                  title="View Reports"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </Link>
                <Link
                  to={`/chatbot/${patient.pseudonym_id}`}
                  className="px-4 py-2 rounded-lg border border-vibrant-blue text-vibrant-blue hover:bg-vibrant-blue/10 transition-all flex items-center justify-center"
                  title="ChatBot"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
                    />
                  </svg>                </Link>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default DoctorPanel


