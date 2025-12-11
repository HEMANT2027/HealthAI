import { Link } from 'react-router-dom'
import { useEffect, useState } from 'react'

function Home() {
  const heroImages = [
    { title: 'Taj Mahal, Agra', img: 'https://images.unsplash.com/photo-1548013146-72479768bada?q=80&w=1920&auto=format&fit=crop' },
    { title: 'Kerala Backwaters', img: 'https://images.unsplash.com/photo-1593693397690-362cb9666fc2?ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&q=80&w=1738' },
    { title: 'Kolkata Boats', img: 'https://images.unsplash.com/photo-1571679654681-ba01b9e1e117?ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&q=80&w=1674' },
  ]

  const [heroIndex, setHeroIndex] = useState(0)
  const [isDropdownOpen, setIsDropdownOpen] = useState(false)

  useEffect(() => {
    const id = setInterval(() => {
      setHeroIndex((i) => (i + 1) % heroImages.length)
    }, 1500)
    return () => clearInterval(id)
  }, [])

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-200 via-white to-teal-100 relative overflow-hidden">
      <div className="pointer-events-none absolute -top-20 -left-10 w-72 h-72 bg-vibrant-blue/10 rounded-full blur-3xl animate-blob" />
      <div className="pointer-events-none absolute top-1/3 -right-20 w-80 h-80 bg-teal-400/10 rounded-full blur-3xl animate-blob animation-delay-2000" />
      <div className="pointer-events-none absolute bottom-0 left-1/3 w-72 h-72 bg-vibrant-orange/10 rounded-full blur-3xl animate-blob animation-delay-4000" />

      {/* Hero Section */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 -z-10 bg-gradient-to-b from-vibrant-blue/10 via-white to-white" />
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
          <div className="grid lg:grid-cols-2 gap-10 items-center">
            <div>
              <h1 className="text-4xl sm:text-5xl font-extrabold text-gray-900 leading-tight">
                Healing Journeys Across India
              </h1>
              <p className="mt-4 text-lg text-gray-600">
                Compare accredited hospitals across India, get transparent pricing, and plan recovery with curated sightseeing—
                all in one place.
              </p>

              {/* Animated hero ticker */}
              <div className="mt-6 overflow-hidden">
                <div className="flex gap-4 marquee-track">
                  {[
                    "Orthopedics", "Cardiology", "Oncology", "Dermatology", "Neurology", "Dental",
                    "Physiotherapy", "Eye Care", "Bariatric", "IVF", "Transplant", "Rehab"
                  ]
                    .concat([
                      "Orthopedics", "Cardiology", "Oncology", "Dermatology", "Neurology", "Dental",
                      "Physiotherapy", "Eye Care", "Bariatric", "IVF", "Transplant", "Rehab"
                    ])
                    .map((t, i) => (
                      <span
                        key={i}
                        className="px-4 py-2 rounded-full text-sm font-semibold bg-gradient-to-r from-vibrant-blue/10 to-teal-500/10 text-vibrant-blue border border-vibrant-blue/20 shadow-sm whitespace-nowrap"
                      >
                        {t}
                      </span>
                    ))}
                </div>
              </div>

              <div className="mt-8 flex gap-4">
                <Link
                  to="/signup"
                  className="inline-flex items-center justify-center px-6 py-3 rounded-lg text-white font-semibold bg-gradient-to-r from-vibrant-blue to-teal-500 hover:brightness-105 transition-all shadow-lg hover:shadow-xl transform hover:scale-105"
                >
                  Get Started
                </Link>
                <Link
                  to="/form"
                  className="inline-flex items-center justify-center px-6 py-3 rounded-lg font-semibold text-vibrant-blue border border-vibrant-blue hover:bg-vibrant-blue/10 transition transform hover:scale-[1.02]"
                >
                  Create Patient
                </Link>
              </div>
            </div>

            <div className="relative">
              <div className="overflow-hidden rounded-3xl shadow-2xl w-full h-80 sm:h-[28rem]">
                <img
                  key={heroImages[heroIndex].img}
                  src={heroImages[heroIndex].img}
                  alt={heroImages[heroIndex].title}
                  className="w-full h-full object-cover"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/40 via-transparent to-transparent" />
                <div className="absolute bottom-3 left-3 text-white font-semibold text-sm sm:text-base">
                  {heroImages[heroIndex].title}
                </div>
              </div>
              <div className="absolute -bottom-6 -left-6 hidden sm:block bg-white/80 backdrop-blur-sm border border-gray-200 rounded-2xl p-4 shadow-xl">
                <p className="text-sm text-gray-700"><span className="font-semibold">300+ </span>accredited hospitals</p>
                <p className="text-sm text-gray-700"><span className="font-semibold">25+ </span>Indian destinations</p>
              </div>
            </div>
          </div>
        </div>
      </section>

     
    


      {/* Features */}
      <section className="py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center">
            <h2 className="text-3xl font-bold text-gray-900">Why choose MedicoTourism?</h2>
            <p className="mt-2 text-gray-600">Seamless medical care paired with meaningful Indian travel experiences.</p>
          </div>
          <div className="mt-10 grid md:grid-cols-3 gap-6">
            {[
              { title: 'Trusted Hospitals', desc: 'Partnered with NABH/JCI accredited specialists and facilities.', icon: (
                <svg className="w-10 h-10 text-vibrant-blue" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6M9 8h6m2 12H7a2 2 0 01-2-2V6a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V18a2 2 0 01-2 2z" /></svg>
              ) },
              { title: 'End-to-end Planning', desc: 'From medical visas to recovery stays and travel logistics.', icon: (
                <svg className="w-10 h-10 text-vibrant-blue" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 1.343-3 3 0 1.657 1.343 3 3 3 1.657 0 3-1.343 3-3 0-1.657-1.343-3-3-3z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 2v2m0 16v2m10-10h-2M4 12H2m15.364 6.364l-1.414-1.414M8.05 8.05L6.636 6.636m10.728 0l-1.414 1.414M8.05 15.95L6.636 17.364" /></svg>
              ) },
              { title: 'Recovery & Sightseeing', desc: 'Personalized, doctor-approved itineraries to recharge and explore.', icon: (
                <svg className="w-10 h-10 text-vibrant-blue" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7l6 6-6 6M21 7l-6 6 6 6" /></svg>
              ) },
            ].map(card => (
              <div key={card.title} className="p-6 bg-white/90 backdrop-blur-sm rounded-2xl shadow-sm border border-gray-100 hover:shadow-md transition-shadow">
                <div className="mb-4">{card.icon}</div>
                <h3 className="text-xl font-semibold text-gray-900">{card.title}</h3>
                <p className="mt-2 text-gray-600">{card.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Scrolling marquee: Indian destinations */}
      <section className="py-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="overflow-hidden rounded-2xl border border-gray-200 bg-white">
            <div className="flex gap-8 marquee-track p-6">
              {["Delhi", "Mumbai", "Bengaluru", "Chennai", "Hyderabad", "Kolkata", "Jaipur", "Kerala", "Varanasi", "Goa", "Rishikesh", "Agra"].concat(["Delhi", "Mumbai", "Bengaluru", "Chennai", "Hyderabad", "Kolkata", "Jaipur", "Kerala", "Varanasi", "Goa", "Rishikesh", "Agra"]).map((city, idx) => (
                <span key={idx} className="text-sm font-semibold text-gray-700 px-4 py-2 rounded-full bg-blue-50 border border-blue-100 whitespace-nowrap">{city}</span>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Destinations (India only) */}
      <section className="py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-end justify-between">
            <h2 className="text-3xl font-bold text-gray-900">Popular destinations in India</h2>
            <Link to="/intake" className="text-vibrant-blue font-semibold hover:text-vibrant-orange transition-colors">Plan my trip</Link>
          </div>
          <div className="mt-8 grid md:grid-cols-3 gap-6">
            {[
              { title: 'Delhi', img: 'https://s7ap1.scene7.com/is/image/incredibleindia/india-gate-delhi-1-attr-hero?qlt=82&ts=1742159856441' },
              { title: 'Kerala', img: 'https://www.holidify.com/images/bgImages/MUNNAR.jpg' },
              { title: 'Mumbai', img: 'https://captureatrip-cms-storage.s3.ap-south-1.amazonaws.com/Chhatrapati_Shivaji_Maharaj_Terminus_9f900a3e3f.webp' },
            ].map(card => (
              <div key={card.title} className="group relative overflow-hidden rounded-2xl shadow-lg">
                <img src={card.img} alt={card.title} className="w-full h-64 object-cover group-hover:scale-105 transition-transform" />
                <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-black/10 to-transparent" />
                <div className="absolute bottom-4 left-4">
                  <p className="text-white text-lg font-semibold">{card.title}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-14">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="rounded-3xl p-8 md:p-12 bg-gradient-to-r from-vibrant-blue to-teal-500 text-white shadow-2xl">
            <h3 className="text-2xl md:text-3xl font-bold">Ready to begin your healing journey?</h3>
            <p className="mt-2 text-blue-100">Tell us your needs and we’ll match you with the best options.</p>
            <div className="mt-6">
              <Link to="/intake" className="inline-flex px-6 py-3 bg-white text-vibrant-blue font-semibold rounded-lg shadow hover:bg-white/90 transition">Fill Medical Profile</Link>
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}



export default Home


