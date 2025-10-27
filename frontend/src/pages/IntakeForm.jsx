import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

function IntakeForm() {
  const navigate = useNavigate()
  const [step, setStep] = useState(0) // NEW: two-step flow
  const [form, setForm] = useState({
    fullName: '',
    age: '',
    phone: '',
    country: '',
    budget: '',
    hasSightseeing: 'no',
    sightseeingDays: '',
    sightseeingPrefs: [],
    notes: '',
  })
  const [prescriptionFile, setPrescriptionFile] = useState(null)
  const [pathologyFile, setPathologyFile] = useState(null)
  const [scanFiles, setScanFiles] = useState([]) // multiple scans allowed
  const [uploadedDocuments, setUploadedDocuments] = useState([])
  const [showModal, setShowModal] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [error, setError] = useState('')

  const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

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
    setError('')
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

  // File type validation helper
  const isValidFileType = (filename) => {
    const ext = filename.toLowerCase().split('.').pop()
    const allowedTypes = ['pdf', 'jpg', 'jpeg', 'png', 'doc', 'docx', 'dcm','tiff']
    return allowedTypes.includes(ext)
  }

  // NEW: file-specific handlers with type validation
  const handlePrescriptionFile = (e) => {
    const f = e.target.files?.[0] || null
    if (!f) return
    if (f.size > 50 * 1024 * 1024) { 
      setError('Prescription file too large (max 50MB)')
      return 
    }
    if (!isValidFileType(f.name)) {
      setError('Invalid file type. Please upload PDF, JPG, PNG, DOC, or DOCX files')
      return
    }
    setPrescriptionFile(f)
    setError('')
  }
  
  const handlePathologyFile = (e) => {
    const f = e.target.files?.[0] || null
    if (!f) return
    if (f.size > 50 * 1024 * 1024) { 
      setError('Pathology file too large (max 50MB)')
      return 
    }
    if (!isValidFileType(f.name)) {
      setError('Invalid file type. Please upload PDF, JPG, PNG, DOC, or DOCX files')
      return
    }
    setPathologyFile(f)
    setError('')
  }
  
  const handleScanFiles = (e) => {
    const selected = Array.from(e.target.files || [])
    if (selected.length === 0) return
    
    // Validate file types
    const invalidTypes = selected.filter(f => !isValidFileType(f.name))
    if (invalidTypes.length > 0) {
      setError(`Invalid file types: ${invalidTypes.map(f => f.name).join(', ')}. Please upload PDF, JPG, PNG, or DICOM files`)
      return
    }
    
    const tooLarge = selected.find(f => f.size > 50 * 1024 * 1024)
    if (tooLarge) { 
      setError(`File ${tooLarge.name} is too large (max 50MB)`)
      return 
    }
    setScanFiles(selected)
    setError('')
  }

  // UPDATED: accept explicit types array
  const uploadFilesToS3 = async (files, types) => {
    if (!files || files.length === 0) return [];

    const formData = new FormData();
    const userData = JSON.parse(localStorage.getItem('user') || '{}');

    files.forEach(file => formData.append('files', file));
    formData.append('pseudonym_id', userData.pseudonym_id || userData.email || 'GUEST-USER');

    // file types must be comma separated and correspond to files order
    const fileTypes = (types || files.map(() => 'clinical_notes')).join(',');
    formData.append('file_types', fileTypes);

    try {
      const response = await fetch(`${API_BASE_URL}/files/upload-intake-documents`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: formData
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Upload failed');
      }

      const data = await response.json();

      if (!data.success) {
        throw new Error('Upload failed: ' + (data.detail || 'Unknown error'));
      }

      return data.uploaded_files.map(file => ({
        url: file.url || file.uri,
        fileName: file.original_filename,
        uploadedAt: file.upload_timestamp,
        type: file.file_type || 'clinical_notes' // Include file type
      }));
    } catch (error) {
      console.error('Upload error:', error);
      throw error;
    }
  }

  const validateStep1 = () => {
    if (!form.fullName || !form.age || !form.phone || !form.country || form.budget === '') {
      setError('Please fill required fields before proceeding.')
      return false
    }
    if (form.hasSightseeing === 'yes' && (!form.sightseeingDays || parseInt(form.sightseeingDays) < 1)) {
      setError('Please provide sightseeing days.')
      return false
    }
    return true
  }

  const handleSubmit = async (e) => {
    e?.preventDefault()
    setError('')

    try {
      const userData = JSON.parse(localStorage.getItem('user') || '{}')
      if (userData.role !== 'patient') {
        throw new Error('Only patients can submit intake forms')
      }

      // Step 1 -> move to step 2
      if (step === 0) {
        if (!validateStep1()) return
        setStep(1)
        return
      }

      // Step 2 -> final submit
      setIsSubmitting(true)

      // prepare file list and types in order
      const filesToUpload = []
      const types = []
      if (prescriptionFile) { filesToUpload.push(prescriptionFile); types.push('prescription') }
      if (pathologyFile) { filesToUpload.push(pathologyFile); types.push('pathology') }
      if (scanFiles && scanFiles.length > 0) {
        scanFiles.forEach(f => { filesToUpload.push(f); types.push('scan') })
      }

      let documents = []
      if (filesToUpload.length > 0) {
        setIsUploading(true)
        const uploaded = await uploadFilesToS3(filesToUpload, types)
        documents = uploaded.map(u => ({ url: u.url, fileName: u.fileName, uploadedAt: u.uploadedAt, type: u.type }))
        setIsUploading(false)
      }

      // Form payload
      const token = localStorage.getItem('token')
      const intakeFormData = {
        fullName: form.fullName,
        age: parseInt(form.age),
        phone: form.phone,
        country: form.country,
        budget: parseFloat(form.budget),
        hasSightseeing: form.hasSightseeing,
        sightseeingDays: form.hasSightseeing === 'yes' ? parseInt(form.sightseeingDays) : null,
        sightseeingPrefs: form.hasSightseeing === 'yes' ? form.sightseeingPrefs : [],
        notes: form.notes || null,
        documents: documents,
        pseudonym_id: userData.pseudonym_id
      }

      const response = await fetch(`${API_BASE_URL}/intake/submit`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(intakeFormData)
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to submit form')
      }

      const result = await response.json()
      console.log('✅ Form submitted successfully:', result)

      // Reset
      setStep(0)
      setPrescriptionFile(null)
      setPathologyFile(null)
      setScanFiles([])
      setUploadedDocuments([])
      setForm({
        fullName: '',
        age: '',
        phone: '',
        country: '',
        budget: '',
        hasSightseeing: 'no',
        sightseeingDays: '',
        sightseeingPrefs: [],
        notes: '',
      })

      setShowModal(true)
      setTimeout(() => navigate('/profile'), 2000)

    } catch (err) {
      console.error('❌ Submission error:', err)
      setError(err.message || 'Failed to submit form. Please try again.')
    } finally {
      setIsSubmitting(false)
      setIsUploading(false)
    }
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

        <form onSubmit={handleSubmit} className="mt-8 space-y-6">
          {step === 0 && (
            <>
              <div className="grid md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700" htmlFor="fullName">Full name *</label>
                  <input 
                    id="fullName" 
                    name="fullName" 
                    type="text" 
                    value={form.fullName} 
                    onChange={handleChange}
                    className="mt-1 block w-full px-4 py-3 border border-gray-300 rounded-xl shadow-sm focus:outline-none focus:ring-2 focus:ring-vibrant-blue focus:border-vibrant-blue transition-all duration-200 hover:border-gray-400" 
                    required 
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700" htmlFor="age">Age *</label>
                  <input 
                    id="age" 
                    name="age" 
                    type="number" 
                    min="1" 
                    max="120"
                    value={form.age} 
                    onChange={handleChange}
                    className="mt-1 block w-full px-4 py-3 border border-gray-300 rounded-xl shadow-sm focus:outline-none focus:ring-2 focus:ring-vibrant-blue focus:border-vibrant-blue transition-all duration-200 hover:border-gray-400" 
                    required 
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700" htmlFor="phone">Phone number *</label>
                  <input 
                    id="phone" 
                    name="phone" 
                    type="tel" 
                    value={form.phone} 
                    onChange={handleChange}
                    placeholder="+1-234-567-8900"
                    className="mt-1 block w-full px-4 py-3 border border-gray-300 rounded-xl shadow-sm focus:outline-none focus:ring-2 focus:ring-vibrant-blue focus:border-vibrant-blue transition-all duration-200 hover:border-gray-400" 
                    required 
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700" htmlFor="country">Country *</label>
                  <input 
                    id="country" 
                    name="country" 
                    type="text" 
                    value={form.country} 
                    onChange={handleChange}
                    className="mt-1 block w-full px-4 py-3 border border-gray-300 rounded-xl shadow-sm focus:outline-none focus:ring-2 focus:ring-vibrant-blue focus:border-vibrant-blue transition-all duration-200 hover:border-gray-400" 
                    required 
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700" htmlFor="budget">Budget (USD) *</label>
                  <input 
                    id="budget" 
                    name="budget" 
                    type="number" 
                    min="0" 
                    step="0.01"
                    value={form.budget} 
                    onChange={handleChange}
                    className="mt-1 block w-full px-4 py-3 border border-gray-300 rounded-xl shadow-sm focus:outline-none focus:ring-2 focus:ring-vibrant-blue focus:border-vibrant-blue transition-all duration-200 hover:border-gray-400" 
                    required 
                  />
                </div>
              </div>

              <div className="grid md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Time for sightseeing?</label>
                  <div className="mt-2 flex items-center gap-6">
                    <label className="inline-flex items-center gap-2 cursor-pointer">
                      <input 
                        type="radio" 
                        name="hasSightseeing" 
                        value="yes" 
                        checked={form.hasSightseeing==='yes'} 
                        onChange={handleChange}
                        className="w-4 h-4 text-vibrant-blue focus:ring-vibrant-blue" 
                      />
                      <span>Yes</span>
                    </label>
                    <label className="inline-flex items-center gap-2 cursor-pointer">
                      <input 
                        type="radio" 
                        name="hasSightseeing" 
                        value="no" 
                        checked={form.hasSightseeing==='no'} 
                        onChange={handleChange}
                        className="w-4 h-4 text-vibrant-blue focus:ring-vibrant-blue" 
                      />
                      <span>No</span>
                    </label>
                  </div>
                </div>
                {form.hasSightseeing === 'yes' && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700" htmlFor="sightseeingDays">How many days? *</label>
                    <input 
                      id="sightseeingDays" 
                      name="sightseeingDays" 
                      type="number" 
                      min="1" 
                      max="30"
                      value={form.sightseeingDays} 
                      onChange={handleChange}
                      className="mt-1 block w-full px-4 py-3 border border-gray-300 rounded-xl shadow-sm focus:outline-none focus:ring-2 focus:ring-vibrant-blue focus:border-vibrant-blue transition-all duration-200 hover:border-gray-400"
                      required={form.hasSightseeing === 'yes'}
                    />
                  </div>
                )}
              </div>

              {form.hasSightseeing === 'yes' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700">Preferred places</label>
                  <div className="mt-2 grid sm:grid-cols-3 gap-3">
                    {sightseeingOptions.map(opt => (
                      <label 
                        key={opt.value} 
                        className="inline-flex items-center gap-2 p-3 border border-gray-200 rounded-xl hover:bg-gray-50 cursor-pointer transition-all duration-200 hover:border-vibrant-blue hover:shadow-sm"
                      >
                        <input 
                          type="checkbox" 
                          checked={form.sightseeingPrefs.includes(opt.value)} 
                          onChange={() => handleMultiSelect(opt.value)}
                          className="w-4 h-4 text-vibrant-blue focus:ring-vibrant-blue rounded" 
                        />
                        <span>{opt.label}</span>
                      </label>
                    ))}
                  </div>
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-700" htmlFor="notes">Additional details</label>
                <textarea 
                  id="notes" 
                  name="notes" 
                  rows="4" 
                  value={form.notes} 
                  onChange={handleChange}
                  className="mt-1 block w-full px-4 py-3 border border-gray-300 rounded-xl shadow-sm focus:outline-none focus:ring-2 focus:ring-vibrant-blue focus:border-vibrant-blue transition-all duration-200 hover:border-gray-400"
                  placeholder="Existing conditions, allergies, medications, preferred travel dates, companions, etc."
                />
              </div>
            </>
          )}

          {step === 1 && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Prescription Document <span className="text-gray-500">(PDF, JPG, PNG, DOC, DOCX)</span>
                </label>
                <input 
                  type="file" 
                  accept=".pdf,.jpg,.jpeg,.png,.doc,.docx"
                  onChange={handlePrescriptionFile}
                  disabled={isUploading || isSubmitting}
                  className="mt-2 block w-full text-sm text-gray-700 border border-gray-300 rounded-lg p-2 bg-white hover:bg-gray-50 transition-colors cursor-pointer"
                />
                {prescriptionFile && (
                  <div className="mt-2 p-2 bg-green-50 border border-green-200 rounded-lg">
                    <p className="text-sm text-green-800">✓ {prescriptionFile.name}</p>
                  </div>
                )}
              </div>

              <div className="mt-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Pathology Report <span className="text-gray-500">(PDF, JPG, PNG, DOC, DOCX)</span>
                </label>
                <input 
                  type="file" 
                  accept=".pdf,.jpg,.jpeg,.png,.doc,.docx"
                  onChange={handlePathologyFile}
                  disabled={isUploading || isSubmitting}
                  className="mt-2 block w-full text-sm text-gray-700 border border-gray-300 rounded-lg p-2 bg-white hover:bg-gray-50 transition-colors cursor-pointer"
                />
                {pathologyFile && (
                  <div className="mt-2 p-2 bg-green-50 border border-green-200 rounded-lg">
                    <p className="text-sm text-green-800">✓ {pathologyFile.name}</p>
                  </div>
                )}
              </div>

              <div className="mt-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Scans / Imaging Reports <span className="text-gray-500">(PDF, JPG, PNG, DICOM)</span>
                </label>
                <input 
                  type="file" 
                  multiple
                  accept=".jpg,.jpeg,.png,.dcm,.pdf"
                  onChange={handleScanFiles}
                  disabled={isUploading || isSubmitting}
                  className="mt-2 block w-full text-sm text-gray-700 border border-gray-300 rounded-lg p-2 bg-white hover:bg-gray-50 transition-colors cursor-pointer"
                />
                {scanFiles.length > 0 && (
                  <div className="mt-2 p-2 bg-green-50 border border-green-200 rounded-lg">
                    <p className="text-sm font-medium text-green-800 mb-1">✓ {scanFiles.length} file(s) selected:</p>
                    <ul className="text-sm text-green-700 list-disc list-inside">
                      {scanFiles.map((f,i) => <li key={i}>{f.name}</li>)}
                    </ul>
                  </div>
                )}
              </div>
            </>
          )}

          <div className="pt-2 flex gap-4">
            <div className="flex-1 md:flex-initial">
              {step === 0 ? (
                <button 
                  type="submit"
                  className="w-full px-8 py-4 rounded-xl text-white font-semibold bg-gradient-to-r from-vibrant-blue to-teal-500 hover:brightness-105 transition-all shadow-lg"
                >
                  Continue to Uploads →
                </button>
              ) : (
                <button 
                  type="submit" 
                  disabled={isUploading || isSubmitting}
                  className="w-full px-8 py-4 rounded-xl text-white font-semibold bg-gradient-to-r from-vibrant-blue to-teal-500 hover:brightness-105 transition-all shadow-lg"
                >
                  {isSubmitting ? 'Submitting...' : 'Submit Profile'}
                </button>
              )}
            </div>

            <button
              type="button"
              onClick={() => {
                if (step === 0) return navigate('/')
                setStep(s => Math.max(0, s - 1))
              }}
              className="px-6 py-4 rounded-xl font-semibold text-gray-700 bg-gray-100 hover:bg-gray-200 transition-all"
            >
              {step === 0 ? 'Cancel' : '← Back'}
            </button>
          </div>
        </form>
      </div>

      {/* Success Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={() => setShowModal(false)} />
          <div className="relative w-full max-w-md rounded-2xl bg-white shadow-2xl border border-gray-200 p-6 animate-fadeIn">
            <div className="w-16 h-16 bg-gradient-to-r from-green-400 to-teal-500 rounded-full flex items-center justify-center mx-auto">
              <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h3 className="mt-4 text-2xl font-bold text-center text-gray-900">Profile Submitted!</h3>
            <p className="mt-2 text-center text-gray-600">
              Our healthcare team is reviewing your profile. We'll contact you within 24-48 hours.
            </p>
            <div className="mt-6 flex justify-center gap-3">
              <button
                type="button"
                onClick={() => {
                  setShowModal(false)
                  navigate('/profile')
                }}
                className="px-6 py-2 rounded-lg text-white font-semibold bg-gradient-to-r from-vibrant-blue to-teal-500 hover:brightness-105 shadow-md"
              >
                View Profile
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default IntakeForm