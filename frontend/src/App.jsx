import { useState } from 'react'
import Signup from './pages/Signup'
import Login from './pages/Login'
import Home from './pages/Home'
import IntakeForm from './pages/IntakeForm'
import Navbar from './components/Navbar'
import Footer from './components/Footer'
import DoctorPanel from './pages/DoctorPanel'
import Reports from './pages/Reports'
import Profile from './pages/Profile'
import Chatbot from './pages/Chatbot'
import { BrowserRouter as Router, Routes, Route, Outlet } from 'react-router-dom'
import  AdminDashboard  from './pages/Admindashboard'

function Layout() {
  return (
    <div className="min-h-screen flex flex-col bg-white">
      <Navbar />
      <main className="flex-1"><Outlet /></main>
      {/* <Footer /> */}
    <div className="py-4 text-center text-xs text-gray-500">© {new Date().getFullYear()} MedicoTourism. All rights reserved.</div>
    </div>
  );
}

function App() {
  return (
    <>
      <Router>
        <Routes>
          <Route element={<Layout />}>
          <Route path="/" element={<Home />} />
          <Route path="/intake" element={<IntakeForm />} />
          <Route path="/profile" element={<Profile/>} />
          <Route path="/doctor" element={<DoctorPanel/>} />
          <Route path="/reports" element={<Reports/>} />
          <Route path="/chatbot" element={<Chatbot/>} />
          <Route path="/admin" element={<AdminDashboard/>} />          
          </Route>
          <Route path="/signup" element={<Signup />} />
          <Route path="/login" element={<Login />} />
        </Routes>
      </Router>
    </>
  )
}

export default App