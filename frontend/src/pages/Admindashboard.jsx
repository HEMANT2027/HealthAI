import { useState } from 'react';

function AdminDashboard() {
  const [doctors, setDoctors] = useState([
    { id: 1, name: 'Dr. Meera Sharma', specialization: 'Cardiology', status: 'In Progress', patients: [] },
    { id: 2, name: 'Dr. Arjun Patel', specialization: 'Orthopedics', status: 'Completed', patients: [] },
    { id: 3, name: 'Dr. Kavita Rao', specialization: 'Neurology', status: 'In Progress', patients: [] },
  ]);

  const [newPatient, setNewPatient] = useState({ name: '', condition: '', doctorId: null });

  const updateStatus = (id, status) => {
    setDoctors(doctors.map(doc => (doc.id === id ? { ...doc, status } : doc)));
  };

  const handleAddPatient = (doctorId) => {
    if (!newPatient.name || !newPatient.condition) return alert('Please fill all patient details');
    setDoctors(doctors.map(doc => {
      if (doc.id === doctorId) {
        return { ...doc, patients: [...doc.patients, { name: newPatient.name, condition: newPatient.condition }] };
      }
      return doc;
    }));
    setNewPatient({ name: '', condition: '', doctorId: null });
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-200 via-white to-teal-100 p-8">
      <h1 className="text-4xl font-bold text-vibrant-blue mb-8 text-center">Admin Dashboard</h1>

      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
        {doctors.map((doc) => (
          <div key={doc.id} className="bg-white rounded-2xl shadow-lg p-6 border border-gray-100">
            <h2 className="text-2xl font-semibold text-gray-800">{doc.name}</h2>
            <p className="text-gray-500">{doc.specialization}</p>

            <div className="mt-4">
              <label className="text-sm font-semibold text-gray-700">Approval Status:</label>
              <select
                value={doc.status}
                onChange={(e) => updateStatus(doc.id, e.target.value)}
                className="mt-1 w-full border border-gray-300 rounded-lg p-2 focus:ring-vibrant-blue focus:border-vibrant-blue"
              >
                <option>In Progress</option>
                <option>Completed</option>
              </select>
            </div>

            <div className="mt-6 border-t pt-4">
              <h3 className="text-lg font-semibold text-gray-800 mb-2">Patients</h3>
              {doc.patients.length > 0 ? (
                <ul className="list-disc ml-5 text-gray-700 space-y-1">
                  {doc.patients.map((p, i) => (
                    <li key={i}>{p.name} — {p.condition}</li>
                  ))}
                </ul>
              ) : (
                <p className="text-gray-500 text-sm">No patients added yet.</p>
              )}

              {newPatient.doctorId === doc.id ? (
                <div className="mt-3 space-y-2">
                  <input
                    type="text"
                    placeholder="Patient Name"
                    className="w-full border rounded-lg p-2"
                    value={newPatient.name}
                    onChange={(e) => setNewPatient({ ...newPatient, name: e.target.value })}
                  />
                  <input
                    type="text"
                    placeholder="Condition"
                    className="w-full border rounded-lg p-2"
                    value={newPatient.condition}
                    onChange={(e) => setNewPatient({ ...newPatient, condition: e.target.value })}
                  />
                  <button
                    onClick={() => handleAddPatient(doc.id)}
                    className="w-full mt-2 bg-vibrant-blue text-white rounded-lg py-2 font-semibold hover:brightness-110 transition"
                  >
                    Add Patient
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => setNewPatient({ ...newPatient, doctorId: doc.id })}
                  className="mt-3 w-full text-ivibrant-blue border border-vibrant-blue rounded-lg py-2 font-semibold hover:bg-vibrant-blue/10 transition"
                >
                  + Add Patient
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default AdminDashboard;
