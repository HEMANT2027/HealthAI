import { Link } from 'react-router-dom';
import { useNavigate } from 'react-router-dom';
import { useState } from 'react';
import GoogleLoginButton from '../components/GoogleLoginButton.jsx';
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
  const [successMessage, setSuccessMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const navigate = useNavigate();

  const handleRoleChange = (e) => {
    setForm({ ...form, role: e.target.value });
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    setErrorMessage('');
    setSuccessMessage('');

    // Validate doctor fields
    if (form.role === 'doctor') {
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
        
        // Redirect based on role and verification status
        setTimeout(() => {
          if (data.user.role === 'doctor') {
            navigate('/');
          } else {
            navigate('/intake');
          }
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

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-gradient-to-br from-blue-200 via-white to-teal-200">
      <div className="w-full max-w-6xl mx-auto lg:grid lg:grid-cols-2 shadow-2xl rounded-3xl overflow-hidden bg-white">
        
        {/* Left Side: Branding and Image */}
        <div className="relative hidden lg:block">
          <img
            src={signupPhoto}
            alt="Medical tourism"
            className="absolute inset-0 w-full h-full object-cover"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-black/30 via-black/10 to-transparent"></div>
          <div className="relative p-12 text-white flex flex-col justify-end h-full">
            <div className="transform hover:scale-105 transition-transform duration-300">
              <h1 className="text-5xl font-extrabold leading-tight">Join Us Today!</h1>
              <p className="mt-4 text-xl text-orange-100">Start your healthcare journey with us.</p>
            </div>
          </div>
        </div>

        {/* Right Side: Form */}
        <div className="p-8 md:p-16 bg-white relative max-h-screen overflow-y-auto">
          <div className="w-full max-w-md mx-auto">
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
              <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded mb-6 text-center">
                {successMessage}
              </div>
            ) : (
              <form className="space-y-6" onSubmit={handleSubmit}>
                {errorMessage && (
                  <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded text-center">
                    {errorMessage}
                  </div>
                )}

                {/* Role Selection */}
                <div>
                  <label htmlFor="role" className="block text-sm font-medium text-gray-700">
                    I am a
                  </label>
                  <select
                    id="role"
                    name="role"
                    value={form.role}
                    onChange={handleRoleChange}
                    className="mt-1 block w-full px-4 py-3 border border-gray-300 rounded-xl shadow-sm focus:outline-none focus:ring-2 focus:ring-vibrant-blue focus:border-vibrant-blue sm:text-sm transition-all duration-200 hover:border-gray-400"
                  >
                    <option value="patient">Patient</option>
                    <option value="doctor">Doctor</option>
                  </select>
                </div>

                {/* Common Fields */}
                <div>
                  <label htmlFor="username" className="block text-sm font-medium text-gray-700">
                    Username
                  </label>
                  <input
                    id="username"
                    name="username"
                    type="text"
                    required
                    className="mt-1 block w-full px-4 py-3 border border-gray-300 rounded-xl shadow-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-vibrant-blue focus:border-vibrant-blue sm:text-sm transition-all duration-200 hover:border-gray-400"
                    placeholder="johndoe"
                    onChange={(e) => setForm({ ...form, username: e.target.value })}
                  />
                </div>

                <div>
                  <label htmlFor="email" className="block text-sm font-medium text-gray-700">
                    Email
                  </label>
                  <input
                    id="email"
                    name="email"
                    type="email"
                    autoComplete="email"
                    required
                    className="mt-1 block w-full px-4 py-3 border border-gray-300 rounded-xl shadow-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-vibrant-blue focus:border-vibrant-blue sm:text-sm transition-all duration-200 hover:border-gray-400"
                    placeholder="you@example.com"
                    onChange={(e) => setForm({ ...form, email: e.target.value })}
                  />
                </div>

                <div>
                  <label htmlFor="password" className="block text-sm font-medium text-gray-700">
                    Password
                  </label>
                  <input
                    id="password"
                    name="password"
                    type="password"
                    autoComplete="new-password"
                    required
                    className="mt-1 block w-full px-4 py-3 border border-gray-300 rounded-xl shadow-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-vibrant-blue focus:border-vibrant-blue sm:text-sm transition-all duration-200 hover:border-gray-400"
                    placeholder="Create a strong password"
                    onChange={(e) => setForm({ ...form, password: e.target.value })}
                  />
                </div>

                {/* Doctor-Specific Fields */}
                {form.role === 'doctor' && (
                  <>
                    <div className="pt-4 border-t border-gray-200">
                      <h3 className="text-lg font-semibold text-gray-900 mb-4">Doctor Information</h3>
                    </div>

                    <div>
                      <label htmlFor="license_id" className="block text-sm font-medium text-gray-700">
                        Medical License ID <span className="text-red-500">*</span>
                      </label>
                      <input
                        id="license_id"
                        name="license_id"
                        type="text"
                        required={form.role === 'doctor'}
                        className="mt-1 block w-full px-4 py-3 border border-gray-300 rounded-xl shadow-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-vibrant-blue focus:border-vibrant-blue sm:text-sm transition-all duration-200 hover:border-gray-400"
                        placeholder="e.g., IND12345"
                        onChange={(e) => setForm({ ...form, license_id: e.target.value })}
                      />
                    </div>

                    <div>
                      <label htmlFor="specialization" className="block text-sm font-medium text-gray-700">
                        Specialization <span className="text-red-500">*</span>
                      </label>
                      <input
                        id="specialization"
                        name="specialization"
                        type="text"
                        required={form.role === 'doctor'}
                        className="mt-1 block w-full px-4 py-3 border border-gray-300 rounded-xl shadow-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-vibrant-blue focus:border-vibrant-blue sm:text-sm transition-all duration-200 hover:border-gray-400"
                        placeholder="e.g., Cardiology, Orthopedics"
                        onChange={(e) => setForm({ ...form, specialization: e.target.value })}
                      />
                    </div>

                    <div>
                      <label htmlFor="hospital" className="block text-sm font-medium text-gray-700">
                        Hospital / Clinic Name <span className="text-red-500">*</span>
                      </label>
                      <input
                        id="hospital"
                        name="hospital"
                        type="text"
                        required={form.role === 'doctor'}
                        className="mt-1 block w-full px-4 py-3 border border-gray-300 rounded-xl shadow-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-vibrant-blue focus:border-vibrant-blue sm:text-sm transition-all duration-200 hover:border-gray-400"
                        placeholder="e.g., Apollo Hospital"
                        onChange={(e) => setForm({ ...form, hospital: e.target.value })}
                      />
                    </div>

                    <div className="bg-blue-50 p-4 rounded-lg">
                      <p className="text-sm text-blue-700">
                        <strong>Note:</strong> Doctor accounts require verification. You'll be able to access the platform once your credentials are verified by our team.
                      </p>
                    </div>
                  </>
                )}

                <button
                  type="submit"
                  className="w-full flex justify-center py-3 px-4 border border-transparent rounded-xl shadow-lg text-lg font-semibold text-white bg-gradient-to-r from-vibrant-blue to-teal-500 hover:brightness-105 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-vibrant-blue transition-all transform hover:scale-105 hover:shadow-xl"
                >
                  {form.role === 'doctor' ? 'Register as Doctor' : 'Create Account'}
                </button>
              </form>
            )}

            <div className="mt-8 relative">
              <div className="absolute inset-0 flex items-center" aria-hidden="true">
                <div className="w-full border-t border-gray-300" />
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="px-2 bg-white bg-opacity-80 text-gray-500">OR</span>
              </div>
            </div>

            <div className="mt-6 flex justify-center gap-4">
              <GoogleLoginButton />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Signup;