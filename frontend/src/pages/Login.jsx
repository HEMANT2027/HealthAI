import { Link } from 'react-router-dom';
// import { useDispatch } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import { useState } from 'react';

function Login() {
  const [form, setForm] = useState({ email: '', password: '' });
  const [successMessage, setSuccessMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const navigate = useNavigate();

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    setErrorMessage('');
    setSuccessMessage('');
    
    fetch('http://127.0.0.1:8000/auth/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(form),
      credentials: 'include',
    }).then(async response => {
      const data = await response.json();
      
      if (response.ok) {
        console.log(data);
        // Store token in localStorage
        localStorage.setItem('token', data.token);
        localStorage.setItem('user', JSON.stringify(data.user));
        
        // Dispatch custom event for Navbar to update
        window.dispatchEvent(new Event('authChange'));
        
        setSuccessMessage("Login successful!");
        setTimeout(() => {
            navigate('/');
        }, 2000);
      } else {
        const errorMsg = typeof data.detail === 'string' 
          ? data.detail 
          : 'Login failed. Please try again.';
        setErrorMessage(errorMsg);
      }
    })
      .catch(error => {
        console.error('Login error:', error);
        setErrorMessage('An error occurred during login. Please try again.');
      });
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-gradient-to-br from-blue-200 via-white to-teal-200">
      <div className="w-full max-w-6xl mx-auto lg:grid lg:grid-cols-2 shadow-2xl rounded-3xl overflow-hidden bg-white">
        
        {/* Left Side: Branding and Image */}
        <div className="relative hidden lg:block">
          <img 
            src="https://www.orissa-international.com/wp-content/uploads/2024/10/medical-tourism-1.jpg" 
            alt="Content creation workspace" 
            className="absolute inset-0 w-full h-full object-cover"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-black/30 via-black/10 to-transparent"></div>
          <div className="relative p-12 text-white flex flex-col justify-end h-full">
            <div className="transform hover:scale-105 transition-transform duration-300">
              <h1 className="text-5xl font-extrabold leading-tight">
                Welcome Back To{' '}
                <Link
                  to="/"
                  className="text-teal-300 hover:text-vibrant-orange transition-colors duration-300 underline-offset-4 hover:underline"
                >
                  MedicoTourism
                </Link>
              </h1>
              <p className="mt-4 text-xl text-blue-100">Continue exploring the world along with treatment and recovery.</p>
            </div>
          </div>
        </div>

        {/* Right Side: Form */}
        <div className="p-8 md:p-16 bg-white relative">
          <div className="w-full max-w-md mx-auto">
            <div className="text-center mb-8">
              <div className="w-16 h-16 bg-gradient-to-r from-vibrant-blue to-teal-500 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
              </div>
              <h2 className="text-3xl font-bold text-gray-900 mb-2">Welcome Back</h2>
              <p className="text-gray-600">
                Don't have an account? <Link to="/signup" className="font-semibold text-vibrant-blue hover:text-vibrant-orange transition-colors">Create one</Link>
              </p>
            </div>

            <form className="space-y-6" onSubmit={handleSubmit}>
              <div>
                <label htmlFor="email" className="block text-sm font-medium text-gray-700">
                  Email
                </label>
                <div className="mt-1">
                  <input
                    id="email"
                    name="email"
                    type="email"
                    autoComplete="email"
                    required
                    value={form.email}
                    onChange={handleChange}
                    className="appearance-none block w-full px-4 py-3 border border-gray-300 rounded-xl shadow-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-vibrant-blue focus:border-vibrant-blue sm:text-sm transition-all duration-200 hover:border-gray-400"
                    placeholder="you@example.com"
                  />
                </div>
              </div>

              <div>
                <label htmlFor="password" className="block text-sm font-medium text-gray-700">
                  Password
                </label>
                <div className="mt-1">
                  <input
                    id="password"
                    name="password"
                    type="password"
                    autoComplete="current-password"
                    required
                    value={form.password}
                    onChange={handleChange}
                    className="appearance-none block w-full px-4 py-3 border border-gray-300 rounded-xl shadow-sm placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-vibrant-blue focus:border-vibrant-blue sm:text-sm transition-all duration-200 hover:border-gray-400"
                    placeholder="••••••••"
                  />
                </div>
              </div>

              <div className="flex items-center justify-between">
                <div className="text-sm">
                  <a href="#" className="font-medium text-vibrant-blue hover:text-vibrant-orange transition-colors">
                    Forgot your password?
                  </a>
                </div>
              </div>

              <div>
                <button
                  type="submit"
                  className="w-full flex justify-center py-3 px-4 border border-transparent rounded-xl shadow-lg text-lg font-semibold text-white bg-gradient-to-r from-vibrant-blue to-teal-500 hover:brightness-105 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-vibrant-blue transition-all transform hover:scale-105 hover:shadow-xl"
                >
                  Sign In
                </button>
              </div>
            </form>
            <div className="mt-8 relative">
              <div className="absolute inset-0 flex items-center" aria-hidden="true">
                <div className="w-full border-t border-gray-300" />
              </div>
              </div>
              {/* <div className="relative flex justify-center text-sm">
                <span className="px-2 bg-white bg-opacity-80 text-gray-500">OR</span>
              </div>
            
            <div className="mt-6 flex justify-center gap-4">
              <GoogleLoginButton />
            </div> */}
          </div>
        </div>
      </div>
    </div>
  );
}

export default Login;