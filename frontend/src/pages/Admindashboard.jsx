import { useState, useEffect } from 'react';

function AdminDashboard() {
  const [pendingDoctors, setPendingDoctors] = useState([]);
  const [unassignedPatients, setUnassignedPatients] = useState([]);
  const [verifiedDoctors, setVerifiedDoctors] = useState([]);
  const [selectedPatient, setSelectedPatient] = useState(null);
  const [selectedDoctor, setSelectedDoctor] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    const token = localStorage.getItem('token');
    try {
      const [pendingRes, patientsRes, doctorsRes] = await Promise.all([
        fetch(`${API_BASE_URL}/admin/pending-doctors`, {
          headers: { 'Authorization': `Bearer ${token}` }
        }),
        fetch(`${API_BASE_URL}/admin/unassigned-patients`, {
          headers: { 'Authorization': `Bearer ${token}` }
        }),
        fetch(`${API_BASE_URL}/admin/verified-doctors`, {
          headers: { 'Authorization': `Bearer ${token}` }
        })
      ]);

      const pendingData = await pendingRes.json();
      const patientsData = await patientsRes.json();
      const doctorsData = await doctorsRes.json();

      setPendingDoctors(pendingData.doctors || []);
      setUnassignedPatients(patientsData.patients || []);
      setVerifiedDoctors(doctorsData.doctors || []);
    } catch (err) {
      setError('Failed to load data');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const verifyDoctor = async (doctorId) => {
    const token = localStorage.getItem('token');
    
    try {
      const response = await fetch(`${API_BASE_URL}/admin/verify-doctor/${doctorId}`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.ok) {
        await fetchData();
      } else {
        setError('Failed to verify doctor');
      }
    } catch (err) {
      setError('Failed to verify doctor');
      console.error(err);
    }
  };

  const assignDoctor = async () => {
    if (!selectedPatient || !selectedDoctor) {
      setError('Please select both patient and doctor');
      return;
    }

    const token = localStorage.getItem('token');
    
    try {
      const response = await fetch(`${API_BASE_URL}/admin/assign-doctor`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          patient_pseudonym_id: selectedPatient,
          doctor_email: selectedDoctor
        })
      });

      if (response.ok) {
        setSelectedPatient(null);
        setSelectedDoctor('');
        await fetchData();
      } else {
        setError('Failed to assign doctor');
      }
    } catch (err) {
      setError('Failed to assign doctor');
      console.error(err);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p>Loading...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-200 via-white to-teal-100 p-8">
      <h1 className="text-4xl font-bold text-vibrant-blue mb-8 text-center">Admin Dashboard</h1>

      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl text-red-800">
          {error}
        </div>
      )}

      <div className="grid md:grid-cols-2 gap-6 mb-8">
        {/* Pending Doctor Verifications */}
        <div className="bg-white rounded-2xl shadow-lg p-6 border border-gray-100">
          <h2 className="text-2xl font-semibold text-gray-800 mb-4">
            Pending Doctor Verifications ({pendingDoctors.length})
          </h2>
          
          {pendingDoctors.length === 0 ? (
            <p className="text-gray-500">No pending verifications</p>
          ) : (
            <div className="space-y-3">
              {pendingDoctors.map((doctor) => (
                <div key={doctor.id} className="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
                  <div>
                    <p className="font-semibold text-gray-800">{doctor.username}</p>
                    <p className="text-sm text-gray-500">{doctor.email}</p>
                  </div>
                  <button
                    onClick={() => verifyDoctor(doctor.id)}
                    className="px-4 py-2 bg-vibrant-blue text-white rounded-lg font-semibold hover:brightness-110 transition"
                  >
                    Verify
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Unassigned Patients */}
        <div className="bg-white rounded-2xl shadow-lg p-6 border border-gray-100">
          <h2 className="text-2xl font-semibold text-gray-800 mb-4">
            Unassigned Patients ({unassignedPatients.length})
          </h2>
          
          {unassignedPatients.length === 0 ? (
            <p className="text-gray-500">No unassigned patients</p>
          ) : (
            <div className="space-y-3">
              {unassignedPatients.map((patient) => (
                <div key={patient.id} className="p-4 border border-gray-200 rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <p className="font-semibold text-gray-800">{patient.pseudonym_id}</p>
                    <button
                      onClick={() => setSelectedPatient(patient.pseudonym_id)}
                      className="text-sm px-3 py-1 bg-blue-50 text-vibrant-blue rounded-lg hover:bg-blue-100"
                    >
                      Assign Doctor
                    </button>
                  </div>
                  <p className="text-sm text-gray-600">{patient.patient_summary}</p>
                  
                  {selectedPatient === patient.pseudonym_id && (
                    <div className="mt-3 space-y-2">
                      <select
                        value={selectedDoctor}
                        onChange={(e) => setSelectedDoctor(e.target.value)}
                        className="w-full border border-gray-300 rounded-lg p-2"
                      >
                        <option value="">Select Doctor</option>
                        {verifiedDoctors.map((doc) => (
                          <option key={doc.id} value={doc.email}>
                            {doc.username} ({doc.email})
                          </option>
                        ))}
                      </select>
                      <div className="flex gap-2">
                        <button
                          onClick={assignDoctor}
                          className="flex-1 bg-vibrant-blue text-white rounded-lg py-2 font-semibold hover:brightness-110"
                        >
                          Confirm
                        </button>
                        <button
                          onClick={() => {
                            setSelectedPatient(null);
                            setSelectedDoctor('');
                          }}
                          className="flex-1 bg-gray-100 text-gray-700 rounded-lg py-2 font-semibold hover:bg-gray-200"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default AdminDashboard;
