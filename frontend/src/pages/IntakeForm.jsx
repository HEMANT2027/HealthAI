import { useState } from 'react'

function IntakeForm() {
  const [form, setForm] = useState({
    fullName: '',
    age: '',
    phone: '',
    country: '',
    budget: '',
    treatmentType: '',
    hasSightseeing: 'no',
    sightseeingDays: '',
    sightseeingPrefs: [],
    notes: '',
  })
  const [files, setFiles] = useState([])
  const [showModal, setShowModal] = useState(false)

  const sightseeingOptions = [
    { value: 'temples', label: 'Temples' },
    { value: 'historical', label: 'Historic places' },
    { value: 'nature', label: 'Nature & parks' },
    { value: 'beaches', label: 'Beaches' },
    { value: 'shopping', label: 'Shopping' },
    { value: 'museums', label: 'Museums' },
  ]

  const handleChange = (e) => {
    const { name, value } = e.target
    setForm(prev => ({ ...prev, [name]: value }))
  }

  const handleMultiSelect = (value) => {
    setForm(prev => {
      const exists = prev.sightseeingPrefs.includes(value)
      return {
        ...prev,
        sightseeingPrefs: exists
          ? prev.sightseeingPrefs.filter(v => v !== value)
          : [...prev.sightseeingPrefs, value]
      }
    })
  }

  const handleFiles = (e) => {
    setFiles(Array.from(e.target.files || []))
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    // TODO: POST to backend when endpoint is ready
    console.log({ ...form, files });
    setFiles([]);
    setForm({
      fullName: '',
      age: '',
      phone: '',
      country: '',
      budget: '',
      treatmentType: '',
      hasSightseeing: 'no',
      sightseeingDays: '',
      sightseeingPrefs: [],
      notes: '',
    });
    setShowModal(true)
  }

  return (
    <div className="min-h-screen py-10 px-4 bg-gradient-to-br from-blue-200 via-white to-teal-200 relative">
      <div className="max-w-4xl mx-auto bg-white/90 backdrop-blur-sm border border-gray-200 rounded-3xl shadow-2xl p-6 md:p-10">
        <div className="text-center mb-8">
          <div className="w-20 h-20 bg-gradient-to-r from-vibrant-blue to-teal-500 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <h1 className="text-4xl font-bold text-gray-900">Patient Intake Form</h1>
          <p className="mt-2 text-lg text-gray-600">Provide your details to personalize medical options and recovery plans.</p>
        </div>

        <form onSubmit={handleSubmit} className="mt-8 space-y-6">
          <div className="grid md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700" htmlFor="fullName">Full name</label>
              <input id="fullName" name="fullName" type="text" value={form.fullName} onChange={handleChange}
                     className="mt-1 block w-full px-4 py-3 border border-gray-300 rounded-xl shadow-sm focus:outline-none focus:ring-2 focus:ring-vibrant-blue focus:border-vibrant-blue transition-all duration-200 hover:border-gray-400" required />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700" htmlFor="age">Age</label>
              <input id="age" name="age" type="number" min="0" value={form.age} onChange={handleChange}
                     className="mt-1 block w-full px-4 py-3 border border-gray-300 rounded-xl shadow-sm focus:outline-none focus:ring-2 focus:ring-vibrant-blue focus:border-vibrant-blue transition-all duration-200 hover:border-gray-400" required />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700" htmlFor="phone">Phone number</label>
              <input id="phone" name="phone" type="tel" value={form.phone} onChange={handleChange}
                     className="mt-1 block w-full px-4 py-3 border border-gray-300 rounded-xl shadow-sm focus:outline-none focus:ring-2 focus:ring-vibrant-blue focus:border-vibrant-blue transition-all duration-200 hover:border-gray-400" required />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700" htmlFor="country">Country of residence</label>
              <input id="country" name="country" type="text" value={form.country} onChange={handleChange}
                     className="mt-1 block w-full px-4 py-3 border border-gray-300 rounded-xl shadow-sm focus:outline-none focus:ring-2 focus:ring-vibrant-blue focus:border-vibrant-blue transition-all duration-200 hover:border-gray-400" required />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700" htmlFor="budget">Budget (USD)</label>
              <input id="budget" name="budget" type="number" min="0" value={form.budget} onChange={handleChange}
                     className="mt-1 block w-full px-4 py-3 border border-gray-300 rounded-xl shadow-sm focus:outline-none focus:ring-2 focus:ring-vibrant-blue focus:border-vibrant-blue transition-all duration-200 hover:border-gray-400" required />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700" htmlFor="treatmentType">Treatment</label>
              <input id="treatmentType" name="treatmentType" type="text" value={form.treatmentType} onChange={handleChange}
                     className="mt-1 block w-full px-4 py-3 border border-gray-300 rounded-xl shadow-sm focus:outline-none focus:ring-2 focus:ring-vibrant-blue focus:border-vibrant-blue transition-all duration-200 hover:border-gray-400" placeholder="e.g., Knee replacement" />
            </div>
          </div>

          <div className="grid md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700">Time for sightseeing after treatment?</label>
              <div className="mt-2 flex items-center gap-6">
                <label className="inline-flex items-center gap-2">
                  <input type="radio" name="hasSightseeing" value="yes" checked={form.hasSightseeing==='yes'} onChange={handleChange} />
                  <span>Yes</span>
                </label>
                <label className="inline-flex items-center gap-2">
                  <input type="radio" name="hasSightseeing" value="no" checked={form.hasSightseeing==='no'} onChange={handleChange} />
                  <span>No</span>
                </label>
              </div>
            </div>
            {form.hasSightseeing === 'yes' && (
              <div>
                <label className="block text-sm font-medium text-gray-700" htmlFor="sightseeingDays">How many days?</label>
                <input id="sightseeingDays" name="sightseeingDays" type="number" min="1" value={form.sightseeingDays} onChange={handleChange}
                       className="mt-1 block w-full px-4 py-3 border border-gray-300 rounded-xl shadow-sm focus:outline-none focus:ring-2 focus:ring-vibrant-blue focus:border-vibrant-blue transition-all duration-200 hover:border-gray-400" />
              </div>
            )}
          </div>

          {form.hasSightseeing === 'yes' && (
            <div>
              <label className="block text-sm font-medium text-gray-700">Preferred places</label>
              <div className="mt-2 grid sm:grid-cols-3 gap-3">
                {sightseeingOptions.map(opt => (
                  <label key={opt.value} className="inline-flex items-center gap-2 p-3 border border-gray-200 rounded-xl hover:bg-gray-50 cursor-pointer transition-all duration-200 hover:border-vibrant-blue hover:shadow-sm">
                    <input type="checkbox" checked={form.sightseeingPrefs.includes(opt.value)} onChange={() => handleMultiSelect(opt.value)} />
                    <span>{opt.label}</span>
                  </label>
                ))}
              </div>
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700" htmlFor="notes">Additional details</label>
            <textarea id="notes" name="notes" rows="4" value={form.notes} onChange={handleChange}
                      className="mt-1 block w-full px-4 py-3 border border-gray-300 rounded-xl shadow-sm focus:outline-none focus:ring-2 focus:ring-vibrant-blue focus:border-vibrant-blue transition-all duration-200 hover:border-gray-400"
                      placeholder="Existing conditions, allergies, preferred travel window, companions, etc." />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">Upload reports (X-ray, prescriptions, scans, etc.)</label>
            <input type="file" multiple onChange={handleFiles}
                   className="mt-2 block w-full text-sm text-gray-700 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-vibrant-blue file:text-white hover:file:brightness-105" />
            {files.length > 0 && (
              <ul className="mt-2 text-sm text-gray-600 list-disc list-inside">
                {files.map((f, i) => <li key={i}>{f.name}</li>)}
              </ul>
            )}
          </div>

          <div className="pt-2">
            <button type="submit" className="w-full md:w-auto px-8 py-4 rounded-xl text-white font-semibold bg-gradient-to-r from-vibrant-blue to-teal-500 hover:brightness-105 transition-all shadow-lg hover:shadow-xl transform hover:scale-105">
              Submit Profile
            </button>
          </div>
        </form>
      </div>

      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={() => setShowModal(false)} />
          <div className="relative w-full max-w-md rounded-2xl bg-white shadow-2xl border border-gray-200 p-6">
            <div className="w-14 h-14 bg-gradient-to-r from-vibrant-blue to-teal-500 rounded-full flex items-center justify-center mx-auto">
              <svg className="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6M9 8h6m2 12H7a2 2 0 01-2-2V6a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V18a2 2 0 01-2 2z" />
              </svg>
            </div>
            <h3 className="mt-4 text-xl font-bold text-center text-gray-900">Profile submitted</h3>
            <p className="mt-2 text-center text-gray-600">Our health team is looking into your profile, We will contact you shortly.</p>
            <div className="mt-6 flex justify-center">
              <button
                type="button"
                onClick={() => setShowModal(false)}
                className="px-6 py-2 rounded-lg text-white font-semibold bg-gradient-to-r from-vibrant-blue to-teal-500 hover:brightness-105 shadow-md"
              >
                Okay
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default IntakeForm


