import { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate, Outlet } from 'react-router-dom'
import Signup from './pages/Signup'
import Login from './pages/Login'
import Home from './pages/Home'
import IntakeForm from './pages/IntakeForm'
import Navbar from './components/Navbar'
import DoctorPanel from './pages/DoctorPanel'
import Report from './pages/Report'
import Profile from './pages/Profile'
import Chatbot from './pages/Chatbot'
import  AdminDashboard  from './pages/Admindashboard'
import PatientForm from './pages/CreatePatient'
import Main from './pages/Main'
// Protected Route Component
function ProtectedRoute({ children, allowedRoles }) {
  const token = localStorage.getItem('token')
  const user = JSON.parse(localStorage.getItem('user') || '{}')

  if (!token) {
    return <Navigate to="/login" replace />
  }

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    return <Navigate to="/" replace />
  }

  return children
}

function Layout() {
  return (
    <div className="min-h-screen flex flex-col bg-white">
      <Navbar />
      <main className="flex-1"><Outlet /></main>
      <div className="py-4 text-center text-xs text-gray-500">© {new Date().getFullYear()} MedicoTourism. All rights reserved.</div>
    </div>
  );
}

function App() {
  const [user, setUser] = useState(null)
  const [isLoading, setIsLoading] = useState(true)

  const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

  // Check authentication on mount
  useEffect(() => {
    checkAuth()
    
    // Listen for auth changes
    window.addEventListener('authChange', checkAuth)
    
    return () => {
      window.removeEventListener('authChange', checkAuth)
    }
  }, [])

  const checkAuth = async () => {
    const token = localStorage.getItem('token')
    
    if (!token) {
      setUser(null)
      setIsLoading(false)
      return
    }

    try {
      const response = await fetch(`${API_BASE_URL}/auth/me`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })

      if (response.ok) {
        const data = await response.json()
        // Extract user data from the response (it's nested in data.user)
        const userData = data.user || data
        setUser(userData)
        localStorage.setItem('user', JSON.stringify(userData))
      } else {
        localStorage.removeItem('token')
        localStorage.removeItem('user')
        setUser(null)
      }
    } catch (error) {
      console.error('Auth check failed:', error)
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      setUser(null)
    } finally {
      setIsLoading(false)
    }
  }

  const handleLogout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    setUser(null)
    window.dispatchEvent(new Event('authChange'))
  }

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <svg className="animate-spin h-12 w-12 text-vibrant-blue mx-auto" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
          <p className="mt-4 text-gray-600">Loading...</p>
        </div>
      </div>
    )
  }

  return (
    <Router>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Home />} />
          <Route path="/home" element={<Main />} />
          {/* Patient Only Routes */}
          <Route 
            path="/intake" 
            element={
              <ProtectedRoute allowedRoles={['patient']}>
                <IntakeForm />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/profile/:id" 
            element={
              <ProtectedRoute allowedRoles={['patient','doctor','admin']}>
                <Profile />
              </ProtectedRoute>
            } 
          />
          
          /* Doctor Only Routes */
                <Route 
                path="/doctor" 
                element={
                  <ProtectedRoute allowedRoles={['doctor']}>
                  <DoctorPanel />
                  </ProtectedRoute>
                } 
                />
                <Route 
                path="/form" 
                element={
                  <ProtectedRoute allowedRoles={['doctor']}>
                  <PatientForm />
                  </ProtectedRoute>
                } 
                />
                <Route 
                path="/reports/:patientId" 
                element={
                  <ProtectedRoute allowedRoles={['doctor']}>
                  <Report />
                  </ProtectedRoute>
                } 
                />
                
                {/* Admin Only Routes */}
          <Route 
            path="/admin" 
            element={
              <ProtectedRoute allowedRoles={['admin']}>
                <AdminDashboard />
              </ProtectedRoute>
            } 
          />
          
          {/* Chatbot - accessible to all authenticated users */}
          <Route 
            path="/chatbot/:id" 
            element={
              <ProtectedRoute>
                <Chatbot />
              </ProtectedRoute>
            } 
          />
        </Route>
        
        <Route path="/signup" element={<Signup />} />
        <Route path="/login" element={<Login />} />
      </Routes>
    </Router>
  )
}

export default App