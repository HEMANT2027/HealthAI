import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

function IntakeForm() {
  const navigate = useNavigate()
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
  const [files, setFiles] = useState([])
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

  const handleFiles = (e) => {
    const selectedFiles = Array.from(e.target.files || [])
    
    // Validate file size (max 10MB per file)
    const validFiles = selectedFiles.filter(file => {
      if (file.size > 10 * 1024 * 1024) {
        setError(`File ${file.name} is too large (max 10MB)`)
        return false
      }
      return true
    })
    
    setFiles(validFiles)
    setError('')
  }

  const uploadFilesToS3 = async (files) => {
    if (!files || files.length === 0) return [];

    const formData = new FormData();
    
    // Get user data from localStorage
    const userData = JSON.parse(localStorage.getItem('user') || '{}');
    console.log(userData.pseudonym_id);
    // Append each file
    files.forEach(file => {
      formData.append('files', file);
    });
    
    // Append pseudonym_id from user data
    formData.append('pseudonym_id', userData.pseudonym_id || userData.email || 'GUEST-USER');
    
    // Append file_types as comma-separated string (default to 'clinical_notes')
    const fileTypes = files.map(() => 'clinical_notes').join(',');
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

      // Transform uploaded_files to match DocumentInfo format
      return data.uploaded_files.map(file => ({
        url: file.url || file.uri,
        fileName: file.original_filename,
        uploadedAt: file.upload_timestamp
      }));
    } catch (error) {
      console.error('Upload error:', error);
      throw error;
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setIsSubmitting(true)

    try {
      // Get user data from localStorage
      const userData = JSON.parse(localStorage.getItem('user') || '{}')
      
      // Check if user is a patient on frontend
      if (userData.role !== 'patient') {
        throw new Error('Only patients can submit intake forms')
      }

      // Step 1: Upload files to S3 if any
      let documents = []
      if (files.length > 0) {
        setIsUploading(true)
        documents = await uploadFilesToS3(files)
        setIsUploading(false)
      }

      // Step 2: Submit form data with S3 URIs to MongoDB via /intake/submit
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
        documents: documents,  // Array of {url, fileName, uploadedAt}
        pseudonym_id: userData.pseudonym_id  // Add pseudonym_id from localStorage
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

      // Reset form
      setFiles([])
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

      // Show success modal
      setShowModal(true)

      // Redirect after 2 seconds
      setTimeout(() => {
        navigate('/profile')
      }, 2000)

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

          {/* File Upload Section */}
          <div>
            <label className="block text-sm font-medium text-gray-700">
              Upload medical documents
            </label>
            <p className="text-xs text-gray-500 mt-1">Max 50MB per file. Supported: PDF, JPG, PNG, DOC, DOCX</p>
            <input 
              type="file" 
              multiple 
              accept=".pdf,.jpg,.jpeg,.png,.doc,.docx"
              onChange={handleFiles}
              disabled={isUploading || isSubmitting}
              className="mt-2 block w-full text-sm text-gray-700 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-vibrant-blue file:text-white hover:file:brightness-105 disabled:opacity-50 disabled:cursor-not-allowed" 
            />
            {files.length > 0 && (
              <div className="mt-3 space-y-2">
                <p className="text-sm font-medium text-gray-700">Selected files ({files.length}):</p>
                <ul className="text-sm text-gray-600 space-y-1">
                  {files.map((f, i) => (
                    <li key={i} className="flex items-center gap-2">
                      <svg className="w-4 h-4 text-vibrant-blue" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clipRule="evenodd" />
                      </svg>
                      <span>{f.name} ({(f.size / 1024 / 1024).toFixed(2)} MB)</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {isUploading && (
              <div className="mt-3">
                <div className="flex items-center justify-between text-sm text-gray-600 mb-1">
                  <span>Uploading to S3...</span>
                  <span>{uploadProgress}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div 
                    className="bg-vibrant-blue h-2 rounded-full transition-all duration-300"
                    style={{ width: `${uploadProgress}%` }}
                  />
                </div>
              </div>
            )}
          </div>

          {/* Submit Button */}
          <div className="pt-2 flex gap-4">
            <button 
              type="submit" 
              disabled={isUploading || isSubmitting}
              className="flex-1 md:flex-initial px-8 py-4 rounded-xl text-white font-semibold bg-gradient-to-r from-vibrant-blue to-teal-500 hover:brightness-105 transition-all shadow-lg hover:shadow-xl transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
            >
              {isSubmitting ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  Submitting...
                </span>
              ) : (
                'Submit Profile'
              )}
            </button>
            <button
              type="button"
              onClick={() => navigate('/')}
              className="px-6 py-4 rounded-xl font-semibold text-gray-700 bg-gray-100 hover:bg-gray-200 transition-all"
            >
              Cancel
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