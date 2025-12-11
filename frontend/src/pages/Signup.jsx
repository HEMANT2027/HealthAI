import { Link } from 'react-router-dom';
import { useNavigate } from 'react-router-dom';
import { useState } from 'react';
import signupPhoto from '../assets/signupPhoto.jpg';

function Signup() {
  const [form, setForm] = useState({ 
    username: '', 
    email: '', 
    password: '',
    role: 'patient',
    // Doctor-specific fields
    license_id: '',
    specialization: '',
    hospital: ''
  });
  const [currentStep, setCurrentStep] = useState(1);
  const [successMessage, setSuccessMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const navigate = useNavigate();

  const handleNext = () => {
    // Validate step 1 fields
    if (!form.username || !form.email || !form.password) {
      setErrorMessage('Please fill all required fields');
      return;
    }
    if (form.password.length < 6) {
      setErrorMessage('Password must be at least 6 characters long');
      return;
    }
    setErrorMessage('');
    setCurrentStep(2);
  };

  const handleBack = () => {
    setErrorMessage('');
    setCurrentStep(1);
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    setErrorMessage('');
    setSuccessMessage('');

    // Validate doctor fields if on step 2
    if (form.role === 'doctor' && currentStep === 2) {
      if (!form.license_id || !form.specialization || !form.hospital) {
        setErrorMessage('Please fill all doctor-specific fields');
        return;
      }
    }

    fetch('http://127.0.0.1:8000/auth/register', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(form),
    }).then(async response => {
      const data = await response.json();
      
      if (response.ok) {
        console.log(data);
        
        // Store token and user data
        localStorage.setItem('token', data.token);
        localStorage.setItem('user', JSON.stringify(data.user));
        
        // Dispatch custom event for Navbar to update
        window.dispatchEvent(new Event('authChange'));
        
        setSuccessMessage(data.message);
        
        // Redirect based on role
        setTimeout(() => {
          navigate('/');
        }, 2000);
      } else {
        const errorMsg = typeof data.detail === 'string' 
          ? data.detail 
          : 'Registration failed. Please try again.';
        setErrorMessage(errorMsg);
      }
    })
      .catch(error => {
        console.error('Registration error:', error);
        setErrorMessage('An error occurred during registration. Please try again.');
      });
  };

  const handleRoleChange = (role) => {
    setForm({ ...form, role });
    setErrorMessage('');
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-gradient-to-br from-blue-200 via-white to-teal-200">
      <div className="w-full max-w-6xl mx-auto lg:grid lg:grid-cols-2 shadow-2xl rounded-3xl overflow-hidden bg-white">
        
        {/* Left Side: Branding and Image */}
        <div className="relative hidden lg:block">
          <img 
            src={signupPhoto} 
            alt="Team collaborating" 
            className="absolute inset-0 w-full h-full object-cover"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-black/30 via-black/10 to-transparent"></div>
          <div className="relative p-12 text-white flex flex-col justify-end h-full">
            <div className="transform hover:scale-105 transition-transform duration-300">
              <h1 className="text-5xl font-extrabold leading-tight">
                Join{' '}
                <Link
                  to="/"
                  className="text-teal-300 hover:text-vibrant-orange transition-colors duration-300 underline-offset-4 hover:underline"
                >
                  HealthAI
                </Link>{' '}
                Today
              </h1>
              <p className="mt-4 text-xl text-orange-100">
                Start exploring the world along with the treatment and recovery.
              </p>
            </div>
          </div>
        </div>

        {/* Right Side: Form */}
        <div className="p-8 md:p-16 bg-white relative max-h-screen overflow-y-auto">
          <div className="w-full max-w-md mx-auto">
            {/* Header */}
            <div className="text-center mb-8">
              <div className="w-16 h-16 bg-gradient-to-r from-vibrant-blue to-teal-500 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" />
                </svg>
              </div>
              <h2 className="text-3xl font-bold text-gray-900 mb-2">Create Account</h2>
              <p className="text-gray-600">
                Already have an account? <Link to="/login" className="font-semibold text-vibrant-blue hover:text-vibrant-orange transition-colors">Sign in</Link>
              </p>
            </div>

            {successMessage ? (
              <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded-xl mb-6 text-center">
                <div className="flex items-center justify-center gap-2">
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                  <span>{successMessage}</span>
                </div>
              </div>
            ) : (
              <form className="space-y-6" onSubmit={handleSubmit}>
                {errorMessage && (
                  <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded-xl text-center">
                    <div className="flex items-center justify-center gap-2">
                      <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                      </svg>
                      <span>{errorMessage}</span>
                    </div>
                  </div>
                )}

                {/* Step 1: Basic Information */}
                {currentStep === 1 && (
                  <div className="space-y-6">
                    {/* Role Selection */}
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-3">Account Type</label>
                      <div className="flex gap-4">
                        {['patient', 'doctor'].map((role) => (
                          <button
                            key={role}
                            type="button"
                            onClick={() => handleRoleChange(role)}
                            className={`flex-1 py-3 rounded-xl border text-sm font-semibold capitalize transition-all duration-200
                              ${
                                form.role === role
                                  ? 'bg-gradient-to-r from-vibrant-blue to-teal-500 text-white shadow-md scale-105 border-transparent'
                                  : 'bg-white text-gray-700 border-gray-300 hover:border-vibrant-blue hover:text-vibrant-blue hover:shadow-md'
                              }`}
                          >
                            {role === 'patient' ? (
                              <div className="flex items-center justify-center gap-2">
                                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                                  <path d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" />
                                </svg>
                                Patient
                              </div>
                            ) : (
                              <div className="flex items-center justify-center gap-2">
                                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                                  <path fillRule="evenodd" d="M10 2a1 1 0 011 1v1.323l3.954 1.582 1.599-.8a1 1 0 01.894 1.79l-1.233.616 1.738 5.42a1 1 0 01-.285 1.05A3.989 3.989 0 0115 15a3.989 3.989 0 01-2.667-1.019 1 1 0 01-.285-1.05l1.715-5.349L11 6.477V16h2a1 1 0 110 2H7a1 1 0 110-2h2V6.477L6.237 7.582l1.715 5.349a1 1 0 01-.285 1.05A3.989 3.989 0 015 15a3.989 3.989 0 01-2.667-1.019 1 1 0 01-.285-1.05l1.738-5.42-1.233-.617a1 1 0 01.894-1.788l1.599.799L9 4.323V3a1 1 0 011-1z" clipRule="evenodd" />
                                </svg>
                                Doctor
                              </div>
                            )}
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* Username */}
                    <div>
                      <label htmlFor="username" className="block text-sm font-medium text-gray-700 mb-2">
                        Username <span className="text-red-500">*</span>
                      </label>
                      <input
                        id="username"
                        name="username"
                        type="text"
                        required
                        value={form.username}
                        className="block w-full px-4 py-3 border border-gray-300 rounded-xl shadow-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-vibrant-blue focus:border-vibrant-blue transition-all duration-200 hover:border-gray-400"
                        placeholder="johndoe"
                        onChange={(e) => setForm({ ...form, username: e.target.value })}
                      />
                    </div>

                    {/* Email */}
                    <div>
                      <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-2">
                        Email <span className="text-red-500">*</span>
                      </label>
                      <input
                        id="email"
                        name="email"
                        type="email"
                        autoComplete="email"
                        required
                        value={form.email}
                        className="block w-full px-4 py-3 border border-gray-300 rounded-xl shadow-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-vibrant-blue focus:border-vibrant-blue transition-all duration-200 hover:border-gray-400"
                        placeholder="you@example.com"
                        onChange={(e) => setForm({ ...form, email: e.target.value })}
                      />
                    </div>

                    {/* Password */}
                    <div>
                      <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-2">
                        Password <span className="text-red-500">*</span>
                      </label>
                      <input
                        id="password"
                        name="password"
                        type="password"
                        autoComplete="new-password"
                        required
                        value={form.password}
                        className="block w-full px-4 py-3 border border-gray-300 rounded-xl shadow-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-vibrant-blue focus:border-vibrant-blue transition-all duration-200 hover:border-gray-400"
                        placeholder="Min. 6 characters"
                        onChange={(e) => setForm({ ...form, password: e.target.value })}
                      />
                      <p className="mt-1 text-xs text-gray-500">Must be at least 6 characters long</p>
                    </div>

                    {/* Next/Submit Button */}
                    {form.role === 'doctor' ? (
                      <button
                        type="button"
                        onClick={handleNext}
                        className="w-full flex justify-center items-center gap-2 py-3 px-4 border border-transparent rounded-xl shadow-lg text-lg font-semibold text-white bg-gradient-to-r from-vibrant-blue to-teal-500 hover:brightness-105 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-vibrant-blue transition-all transform hover:scale-105 hover:shadow-xl"
                      >
                        Next: Doctor Credentials
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                        </svg>
                      </button>
                    ) : (
                      <button
                        type="submit"
                        className="w-full flex justify-center py-3 px-4 border border-transparent rounded-xl shadow-lg text-lg font-semibold text-white bg-gradient-to-r from-vibrant-blue to-teal-500 hover:brightness-105 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-vibrant-blue transition-all transform hover:scale-105 hover:shadow-xl"
                      >
                        Create Account
                      </button>
                    )}
                  </div>
                )}

                {/* Step 2: Doctor Credentials */}
                {currentStep === 2 && form.role === 'doctor' && (
                  <div className="space-y-6">
                    <div className="bg-blue-50 border-l-4 border-vibrant-blue p-4 rounded-lg">
                      <div className="flex">
                        <svg className="w-5 h-5 text-vibrant-blue mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                        </svg>
                        <p className="text-sm text-blue-700">
                          <strong>Verification Required:</strong> Your credentials will be reviewed by our team. You'll receive email confirmation once verified.
                        </p>
                      </div>
                    </div>

                    {/* License ID */}
                    <div>
                      <label htmlFor="license_id" className="block text-sm font-medium text-gray-700 mb-2">
                        Medical License ID <span className="text-red-500">*</span>
                      </label>
                      <input
                        id="license_id"
                        name="license_id"
                        type="text"
                        required
                        value={form.license_id}
                        className="block w-full px-4 py-3 border border-gray-300 rounded-xl shadow-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-vibrant-blue focus:border-vibrant-blue transition-all duration-200 hover:border-gray-400"
                        placeholder="e.g., IND12345"
                        onChange={(e) => setForm({ ...form, license_id: e.target.value })}
                      />
                    </div>

                    {/* Specialization */}
                    <div>
                      <label htmlFor="specialization" className="block text-sm font-medium text-gray-700 mb-2">
                        Specialization <span className="text-red-500">*</span>
                      </label>
                      <input
                        id="specialization"
                        name="specialization"
                        type="text"
                        required
                        value={form.specialization}
                        className="block w-full px-4 py-3 border border-gray-300 rounded-xl shadow-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-vibrant-blue focus:border-vibrant-blue transition-all duration-200 hover:border-gray-400"
                        placeholder="e.g., Cardiology, Orthopedics"
                        onChange={(e) => setForm({ ...form, specialization: e.target.value })}
                      />
                    </div>

                    {/* Hospital */}
                    <div>
                      <label htmlFor="hospital" className="block text-sm font-medium text-gray-700 mb-2">
                        Hospital / Clinic Name <span className="text-red-500">*</span>
                      </label>
                      <input
                        id="hospital"
                        name="hospital"
                        type="text"
                        required
                        value={form.hospital}
                        className="block w-full px-4 py-3 border border-gray-300 rounded-xl shadow-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-vibrant-blue focus:border-vibrant-blue transition-all duration-200 hover:border-gray-400"
                        placeholder="e.g., Apollo Hospital"
                        onChange={(e) => setForm({ ...form, hospital: e.target.value })}
                      />
                    </div>

                    {/* Navigation Buttons */}
                    <div className="flex gap-4">
                      <button
                        type="button"
                        onClick={handleBack}
                        className="flex-1 flex justify-center items-center gap-2 py-3 px-4 border border-gray-300 rounded-xl text-lg font-semibold text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-400 transition-all"
                      >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 17l-5-5m0 0l5-5m-5 5h12" />
                        </svg>
                        Back
                      </button>
                      <button
                        type="submit"
                        className="flex-1 flex justify-center items-center gap-2 py-3 px-4 border border-transparent rounded-xl shadow-lg text-lg font-semibold text-white bg-gradient-to-r from-vibrant-blue to-teal-500 hover:brightness-105 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-vibrant-blue transition-all transform hover:scale-105 hover:shadow-xl"
                      >
                        Register as Doctor
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                      </button>
                    </div>
                  </div>
                )}
              </form>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default Signup;