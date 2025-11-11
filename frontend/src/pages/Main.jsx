import { Link } from 'react-router-dom'
import { useEffect, useState } from 'react'

function Main() {
  const [user, setUser] = useState(null)

  useEffect(() => {
    const userData = localStorage.getItem('user')
    if (userData) {
      setUser(JSON.parse(userData))
    }
  }, [])

  const tools = [
    {
      title: 'AI-Powered OCR',
      description: 'Extract text from prescriptions and pathology reports with high accuracy using advanced optical character recognition.',
      icon: (
        <svg className="w-12 h-12 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      ),
      gradient: 'from-blue-500 to-cyan-500'
    },
    {
      title: 'Medical Image Analysis',
      description: 'Analyze pathology images with region-specific insights powered by MedGemma and advanced vision models.',
      icon: (
        <svg className="w-12 h-12 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
      ),
      gradient: 'from-purple-500 to-pink-500'
    },
    {
      title: 'Intelligent Chatbot',
      description: 'Get instant answers about patient reports, medical history, and treatment recommendations using RAG-powered AI.',
      icon: (
        <svg className="w-12 h-12 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
        </svg>
      ),
      gradient: 'from-green-500 to-teal-500'
    },
    {
      title: 'Comprehensive Reports',
      description: 'Generate detailed medical reports combining prescription analysis, pathology findings, and clinical insights.',
      icon: (
        <svg className="w-12 h-12 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      ),
      gradient: 'from-orange-500 to-red-500'
    },
  ]

  const models = [
    { name: 'MedGemma', description: 'Medical-specialized language model for clinical analysis' },
    { name: 'GPT-4 Vision', description: 'Advanced vision model for medical image interpretation' },
    { name: 'LangChain RAG', description: 'Retrieval-augmented generation for contextual responses' },
    { name: 'Custom OCR Pipeline', description: 'Optimized text extraction for medical documents' }
  ]

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-200 via-white to-teal-100 relative overflow-hidden">
      {/* Animated Background Blobs */}
      <div className="pointer-events-none absolute -top-20 -left-10 w-72 h-72 bg-vibrant-blue/10 rounded-full blur-3xl animate-blob" />
      <div className="pointer-events-none absolute top-1/3 -right-20 w-80 h-80 bg-teal-400/10 rounded-full blur-3xl animate-blob animation-delay-2000" />
      <div className="pointer-events-none absolute bottom-0 left-1/3 w-72 h-72 bg-vibrant-orange/10 rounded-full blur-3xl animate-blob animation-delay-4000" />
      
      {/* Decorative SVG Graphics */}
      <div className="pointer-events-none absolute top-20 left-10 opacity-10 animate-[float_6s_ease-in-out_infinite]">
        <svg width="120" height="120" viewBox="0 0 120 120" fill="none">
          <path d="M60 10L70 40L100 50L70 60L60 90L50 60L20 50L50 40L60 10Z" fill="url(#grad1)" />
          <defs>
            <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" style={{stopColor: '#2563eb', stopOpacity: 1}} />
              <stop offset="100%" style={{stopColor: '#14b8a6', stopOpacity: 1}} />
            </linearGradient>
          </defs>
        </svg>
      </div>
      
      <div className="pointer-events-none absolute top-1/2 right-20 opacity-10 animate-[float_7s_ease-in-out_infinite]">
        <svg width="100" height="100" viewBox="0 0 100 100" fill="none">
          <circle cx="50" cy="50" r="40" stroke="url(#grad2)" strokeWidth="3" strokeDasharray="10 5" className="animate-spin" style={{animationDuration: '20s'}} />
          <circle cx="50" cy="50" r="25" stroke="url(#grad2)" strokeWidth="2" strokeDasharray="5 3" className="animate-spin" style={{animationDuration: '15s', animationDirection: 'reverse'}} />
          <defs>
            <linearGradient id="grad2" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" style={{stopColor: '#8b5cf6', stopOpacity: 1}} />
              <stop offset="100%" style={{stopColor: '#ec4899', stopOpacity: 1}} />
            </linearGradient>
          </defs>
        </svg>
      </div>
      
      <div className="pointer-events-none absolute bottom-40 left-1/4 opacity-10 animate-[float_5s_ease-in-out_infinite]">
        <svg width="80" height="80" viewBox="0 0 80 80" fill="none">
          <rect x="10" y="10" width="60" height="60" rx="15" stroke="url(#grad3)" strokeWidth="3" className="animate-pulse" />
          <rect x="25" y="25" width="30" height="30" rx="8" fill="url(#grad3)" className="animate-pulse" style={{animationDelay: '0.5s'}} />
          <defs>
            <linearGradient id="grad3" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" style={{stopColor: '#f97316', stopOpacity: 1}} />
              <stop offset="100%" style={{stopColor: '#eab308', stopOpacity: 1}} />
            </linearGradient>
          </defs>
        </svg>
      </div>
      
      <div className="pointer-events-none absolute top-1/3 left-1/2 opacity-10 animate-[float_8s_ease-in-out_infinite]">
        <svg width="90" height="90" viewBox="0 0 90 90" fill="none">
          <path d="M45 5L50 35L80 40L50 45L45 75L40 45L10 40L40 35L45 5Z" stroke="url(#grad4)" strokeWidth="2" fill="none" className="animate-pulse" />
          <defs>
            <linearGradient id="grad4" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" style={{stopColor: '#10b981', stopOpacity: 1}} />
              <stop offset="100%" style={{stopColor: '#14b8a6', stopOpacity: 1}} />
            </linearGradient>
          </defs>
        </svg>
      </div>
      
      <div className="pointer-events-none absolute bottom-20 right-1/3 opacity-10 animate-[float_6.5s_ease-in-out_infinite]">
        <svg width="70" height="70" viewBox="0 0 70 70" fill="none">
          <polygon points="35,5 60,25 50,55 20,55 10,25" stroke="url(#grad5)" strokeWidth="2.5" fill="none" className="animate-spin" style={{animationDuration: '25s'}} />
          <defs>
            <linearGradient id="grad5" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" style={{stopColor: '#2563eb', stopOpacity: 1}} />
              <stop offset="100%" style={{stopColor: '#f97316', stopOpacity: 1}} />
            </linearGradient>
          </defs>
        </svg>
      </div>

      {/* Hero Section */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 -z-10 bg-gradient-to-b from-vibrant-blue/10 via-white to-white" />
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            {/* Left Content */}
            <div>
              <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-blue-50 border border-blue-200 mb-6">
                <span className="w-2 h-2 bg-vibrant-blue rounded-full animate-pulse"></span>
                <span className="text-sm font-semibold text-vibrant-blue">AI-Powered Medical Intelligence</span>
              </div>
              
              <h1 className="text-5xl sm:text-6xl font-extrabold text-gray-900 leading-tight">
                Welcome to <span className="gradient-text">HealthAI</span>
              </h1>
              
              <p className="mt-6 text-xl text-gray-600 leading-relaxed">
                Empowering doctors with cutting-edge AI tools for faster diagnosis, 
                comprehensive analysis, and better patient outcomes.
              </p>

              {user?.role === 'doctor' && (
                <div className="mt-8 flex gap-4">
                  <Link
                    to="/doctor"
                    className="inline-flex items-center justify-center px-6 py-3 rounded-lg text-white font-semibold bg-gradient-to-r from-vibrant-blue to-teal-500 hover:brightness-105 transition-all shadow-lg hover:shadow-xl transform hover:scale-105"
                  >
                    Go to Dashboard
                    <svg className="w-5 h-5 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                    </svg>
                  </Link>
                  <Link
                    to="/form"
                    className="inline-flex items-center justify-center px-6 py-3 rounded-lg font-semibold text-vibrant-blue border-2 border-vibrant-blue hover:bg-vibrant-blue/10 transition transform hover:scale-[1.02]"
                  >
                    Create Patient
                  </Link>
                </div>
              )}
            </div>

            {/* Right Hero Graphic - 3D Medical Network */}
            <div className="relative h-[500px]">
              {/* Central Brain/Network Hub */}
              <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-20">
                <div className="relative">
                  {/* Main central circle */}
                  <div className="w-32 h-32 rounded-full bg-gradient-to-br from-vibrant-blue via-purple-500 to-teal-500 flex items-center justify-center shadow-2xl animate-pulse">
                    <svg className="w-16 h-16 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                    </svg>
                  </div>
                  
                  {/* Orbiting ring */}
                  <div className="absolute inset-0 animate-spin" style={{animationDuration: '20s'}}>
                    <div className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1/2 w-3 h-3 rounded-full bg-cyan-400"></div>
                  </div>
                  <div className="absolute inset-0 animate-spin" style={{animationDuration: '15s', animationDirection: 'reverse'}}>
                    <div className="absolute bottom-0 left-1/2 -translate-x-1/2 translate-y-1/2 w-3 h-3 rounded-full bg-pink-400"></div>
                  </div>
                </div>
              </div>

              {/* Floating Cards Around Center */}
              {/* Top Left - OCR */}
              <div className="absolute top-8 left-8 animate-[float_4s_ease-in-out_infinite]">
                <div className="bg-white/95 backdrop-blur-sm rounded-2xl shadow-xl p-4 border border-blue-100 w-40">
                  <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center mb-2">
                    <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                  </div>
                  <p className="text-xs font-bold text-gray-900">OCR Engine</p>
                  <p className="text-xs text-gray-500 mt-1">Text Extraction</p>
                </div>
                {/* Connection line */}
                <svg className="absolute top-16 left-32 w-24 h-24 opacity-20" viewBox="0 0 100 100">
                  <line x1="0" y1="0" x2="100" y2="100" stroke="url(#lineGrad1)" strokeWidth="2" strokeDasharray="5,5" className="animate-pulse"/>
                  <defs>
                    <linearGradient id="lineGrad1">
                      <stop offset="0%" stopColor="#3b82f6" />
                      <stop offset="100%" stopColor="#8b5cf6" />
                    </linearGradient>
                  </defs>
                </svg>
              </div>

              {/* Top Right - Vision AI */}
              <div className="absolute top-8 right-8 animate-[float_5s_ease-in-out_infinite]">
                <div className="bg-white/95 backdrop-blur-sm rounded-2xl shadow-xl p-4 border border-purple-100 w-40">
                  <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center mb-2">
                    <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                    </svg>
                  </div>
                  <p className="text-xs font-bold text-gray-900">Vision AI</p>
                  <p className="text-xs text-gray-500 mt-1">Image Analysis</p>
                </div>
                {/* Connection line */}
                <svg className="absolute top-16 right-32 w-24 h-24 opacity-20" viewBox="0 0 100 100">
                  <line x1="100" y1="0" x2="0" y2="100" stroke="url(#lineGrad2)" strokeWidth="2" strokeDasharray="5,5" className="animate-pulse"/>
                  <defs>
                    <linearGradient id="lineGrad2">
                      <stop offset="0%" stopColor="#8b5cf6" />
                      <stop offset="100%" stopColor="#ec4899" />
                    </linearGradient>
                  </defs>
                </svg>
              </div>

              {/* Bottom Left - NER */}
              <div className="absolute bottom-8 left-8 animate-[float_4.5s_ease-in-out_infinite]">
                <div className="bg-white/95 backdrop-blur-sm rounded-2xl shadow-xl p-4 border border-green-100 w-40">
                  <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-green-500 to-teal-500 flex items-center justify-center mb-2">
                    <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
                    </svg>
                  </div>
                  <p className="text-xs font-bold text-gray-900">NER System</p>
                  <p className="text-xs text-gray-500 mt-1">Entity Extraction</p>
                </div>
                {/* Connection line */}
                <svg className="absolute bottom-16 left-32 w-24 h-24 opacity-20" viewBox="0 0 100 100">
                  <line x1="0" y1="100" x2="100" y2="0" stroke="url(#lineGrad3)" strokeWidth="2" strokeDasharray="5,5" className="animate-pulse"/>
                  <defs>
                    <linearGradient id="lineGrad3">
                      <stop offset="0%" stopColor="#10b981" />
                      <stop offset="100%" stopColor="#14b8a6" />
                    </linearGradient>
                  </defs>
                </svg>
              </div>

              {/* Bottom Right - Chatbot */}
              <div className="absolute bottom-8 right-8 animate-[float_3.5s_ease-in-out_infinite]">
                <div className="bg-white/95 backdrop-blur-sm rounded-2xl shadow-xl p-4 border border-orange-100 w-40">
                  <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-orange-500 to-red-500 flex items-center justify-center mb-2">
                    <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                    </svg>
                  </div>
                  <p className="text-xs font-bold text-gray-900">AI Chatbot</p>
                  <p className="text-xs text-gray-500 mt-1">Smart Assistant</p>
                </div>
                {/* Connection line */}
                <svg className="absolute bottom-16 right-32 w-24 h-24 opacity-20" viewBox="0 0 100 100">
                  <line x1="100" y1="100" x2="0" y2="0" stroke="url(#lineGrad4)" strokeWidth="2" strokeDasharray="5,5" className="animate-pulse"/>
                  <defs>
                    <linearGradient id="lineGrad4">
                      <stop offset="0%" stopColor="#f97316" />
                      <stop offset="100%" stopColor="#ef4444" />
                    </linearGradient>
                  </defs>
                </svg>
              </div>

              {/* Animated particles */}
              <div className="absolute top-1/4 left-1/4 w-2 h-2 rounded-full bg-blue-400 animate-ping"></div>
              <div className="absolute top-3/4 right-1/4 w-2 h-2 rounded-full bg-purple-400 animate-ping" style={{animationDelay: '1s'}}></div>
              <div className="absolute top-1/2 right-1/3 w-2 h-2 rounded-full bg-teal-400 animate-ping" style={{animationDelay: '2s'}}></div>
            </div>
          </div>
        </div>
      </section>

      {/* Tools & Features Section */}
      <section className="py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h2 className="text-4xl font-bold text-gray-900">Powerful AI Tools at Your Fingertips</h2>
            <p className="mt-3 text-lg text-gray-600">
              Comprehensive suite of AI-powered tools designed specifically for medical professionals
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-2 gap-6">
            {tools.map((tool, index) => (
              <div
                key={index}
                className="group bg-white/90 backdrop-blur-sm rounded-2xl shadow-sm border border-gray-200 p-6 hover:shadow-xl hover:scale-[1.02] transition-all duration-300"
              >
                <div className={`w-16 h-16 rounded-xl bg-gradient-to-br ${tool.gradient} flex items-center justify-center mb-4 group-hover:scale-110 transition-transform`}>
                  {tool.icon}
                </div>
                <h3 className="text-xl font-bold text-gray-900 mb-2">{tool.title}</h3>
                <p className="text-gray-600 text-sm leading-relaxed">{tool.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Models Section */}
      <section className="py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="bg-white/90 backdrop-blur-sm rounded-3xl shadow-xl border border-gray-200 p-8 md:p-12">
            <div className="text-center mb-10">
              <h2 className="text-3xl font-bold text-gray-900">Powered by Advanced AI Models</h2>
              <p className="mt-2 text-gray-600">State-of-the-art machine learning models working together</p>
            </div>

            <div className="grid md:grid-cols-2 gap-6">
              {models.map((model, index) => (
                <div
                  key={index}
                  className="flex items-start gap-4 p-5 rounded-xl bg-gradient-to-br from-blue-50 to-teal-50 border border-blue-100 hover:border-vibrant-blue transition-colors"
                >
                  <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-vibrant-blue flex items-center justify-center">
                    <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                    </svg>
                  </div>
                  <div>
                    <h4 className="font-bold text-gray-900">{model.name}</h4>
                    <p className="text-sm text-gray-600 mt-1">{model.description}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Scrolling Marquee - Specialties */}
      <section className="py-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="overflow-hidden rounded-2xl border border-gray-200 bg-white/90 backdrop-blur-sm">
            <div className="flex gap-6 marquee-track p-6">
              {[
                "Cardiology", "Neurology", "Oncology", "Orthopedics", "Radiology", 
                "Pathology", "Dermatology", "Pediatrics", "Surgery", "Internal Medicine",
                "Cardiology", "Neurology", "Oncology", "Orthopedics", "Radiology", 
                "Pathology", "Dermatology", "Pediatrics", "Surgery", "Internal Medicine"
              ].map((specialty, idx) => (
                <span 
                  key={idx} 
                  className="text-sm font-semibold text-vibrant-blue px-5 py-2 rounded-full bg-gradient-to-r from-blue-50 to-teal-50 border border-blue-200 whitespace-nowrap"
                >
                  {specialty}
                </span>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-16">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="rounded-3xl p-10 md:p-14 bg-gradient-to-r from-vibrant-blue via-teal-500 to-cyan-500 text-white shadow-2xl relative overflow-hidden">
            {/* Decorative elements */}
            <div className="absolute top-0 right-0 w-64 h-64 bg-white/10 rounded-full blur-3xl"></div>
            <div className="absolute bottom-0 left-0 w-48 h-48 bg-white/10 rounded-full blur-3xl"></div>
            
            <div className="relative z-10">
              <h3 className="text-3xl md:text-4xl font-bold">Ready to Transform Your Practice?</h3>
              <p className="mt-3 text-blue-100 text-lg">
                Join hundreds of doctors using HealthAI to provide better, faster care to their patients.
              </p>
              
              {user?.role === 'doctor' ? (
                <div className="mt-8 flex flex-wrap gap-4">
                  <Link 
                    to="/doctor" 
                    className="inline-flex items-center px-8 py-4 bg-white text-vibrant-blue font-bold rounded-xl shadow-lg hover:bg-gray-50 transition transform hover:scale-105"
                  >
                    View My Patients
                    <svg className="w-5 h-5 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
                    </svg>
                  </Link>
                  <Link 
                    to="/form" 
                    className="inline-flex items-center px-8 py-4 bg-transparent border-2 border-white text-white font-bold rounded-xl hover:bg-white/10 transition"
                  >
                    Add New Patient
                  </Link>
                </div>
              ) : (
                <div className="mt-8">
                  <Link 
                    to="/login" 
                    className="inline-flex items-center px-8 py-4 bg-white text-vibrant-blue font-bold rounded-xl shadow-lg hover:bg-gray-50 transition transform hover:scale-105"
                  >
                    Get Started Today
                    <svg className="w-5 h-5 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                    </svg>
                  </Link>
                </div>
              )}
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}

export default Main