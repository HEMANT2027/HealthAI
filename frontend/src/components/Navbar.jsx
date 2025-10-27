import { Link, useNavigate, NavLink } from 'react-router-dom';
import { useState, useEffect } from 'react';

function Navbar() {
  const navigate = useNavigate();
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);

  // Check authentication status on mount and when localStorage changes
  useEffect(() => {
    const checkAuth = () => {
      const token = localStorage.getItem('token');
      const userData = localStorage.getItem('user');
      
      if (token && userData) {
        setIsAuthenticated(true);
        setUser(JSON.parse(userData));
      } else {
        setIsAuthenticated(false);
        setUser(null);
      }
    };

    // Initial check
    checkAuth();

    // Listen for storage changes (when user logs in/out in another tab)
    window.addEventListener('storage', checkAuth);

    // Custom event for same-tab updates
    window.addEventListener('authChange', checkAuth);

    return () => {
      window.removeEventListener('storage', checkAuth);
      window.removeEventListener('authChange', checkAuth);
    };
  }, []);

  const handleLogout = async () => {
    try {
      await fetch('http://127.0.0.1:8000/auth/logout', {
        method: 'POST',
        credentials: 'include',
      });
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      setIsAuthenticated(false);
      setUser(null);
      
      // Dispatch custom event for auth change
      window.dispatchEvent(new Event('authChange'));
      
      navigate('/login');
    }
  };

  return (
    <header className="sticky z-50 bg-white/70 backdrop-blur-md border-b border-gray-200/70">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-20 flex items-center justify-between">
        <Link to="/" className="text-2xl font-extrabold gradient-text">MedicoTourism</Link>
        
        <nav className="flex items-center gap-6 text-l font-semibold">
          <NavLink 
            to="/" 
            className={({isActive}) => `transition-colors ${isActive ? 'text-vibrant-blue' : 'text-gray-700 hover:text-vibrant-orange'}`}
          >
            Home
          </NavLink>
          
          {/* Patient-only navigation */}
          {isAuthenticated && user?.role === 'patient' && (
            <>
              <NavLink 
                to="/intake" 
                className={({isActive}) => `transition-colors ${isActive ? 'text-vibrant-blue' : 'text-gray-700 hover:text-vibrant-orange'}`}
              >
                Medical Form
              </NavLink>
              
              <NavLink 
                to="/profile" 
                className={({isActive}) => `transition-colors ${isActive ? 'text-vibrant-blue' : 'text-gray-700 hover:text-vibrant-orange'}`}
              >
                Profile
              </NavLink>
            </>
          )}
          
          {/* Doctor-only navigation */}
          {isAuthenticated && user?.role === 'doctor' && (
            <>
              <NavLink 
                to="/doctor" 
                className={({isActive}) => `transition-colors ${isActive ? 'text-vibrant-blue' : 'text-gray-700 hover:text-vibrant-orange'}`}
              >
                Doctor Panel
              </NavLink>
              
            </>
          )}
          
          {/* Admin-only navigation */}
          {isAuthenticated && user?.role === 'admin' && (
            <>
              <NavLink 
                to="/admin" 
                className={({isActive}) => `transition-colors ${isActive ? 'text-vibrant-blue' : 'text-gray-700 hover:text-vibrant-orange'}`}
              >
                Admin Dashboard
              </NavLink>
            </>
          )}
        </nav>

        <div>
          {isAuthenticated ? (
            <button 
              onClick={handleLogout} 
              className="px-4 py-2 rounded-lg text-white bg-gradient-to-r from-red-500 to-orange-400 hover:brightness-105 transition-all shadow-md hover:shadow-md transform hover:scale-105"
            >
              Logout
            </button>
          ) : (
            <NavLink 
              to="/login" 
              className="px-4 py-2 rounded-lg text-white bg-gradient-to-r from-vibrant-blue to-teal-500 hover:brightness-105 transition-all shadow-md hover:shadow-md transform hover:scale-105"
            >
              Login
            </NavLink>
          )}
        </div>
      </div>
    </header>
  )
}

export default Navbar