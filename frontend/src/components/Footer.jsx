function Footer() {
  return (
    <footer className="mb-8 border-t border-gray-200 bg-white/80 backdrop-blur-sm relative overflow-hidden">
      <div className="pointer-events-none absolute -top-10 -left-10 w-40 h-40 bg-vibrant-blue/10 rounded-full blur-3xl animate-blob"></div>
      <div className="pointer-events-none absolute -bottom-10 -right-10 w-40 h-40 bg-vibrant-orange/10 rounded-full blur-3xl animate-blob animation-delay-2000"></div>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 grid md:grid-cols-4 gap-8 text-sm relative">
        <div>
          <p className="text-xl font-extrabold gradient-text">MedicoTourism</p>
          <p className="mt-3 text-gray-600">World-class care with meaningful recovery experiences.</p>
        </div>
        <div className="text-gray-600">
          <p className="font-semibold text-gray-900">Explore</p>
          <ul className="mt-2 space-y-1">
            <li><a className="hover:text-vibrant-orange" href="#">Destinations</a></li>
            <li><a className="hover:text-vibrant-orange" href="#">Hospitals</a></li>
            <li><a className="hover:text-vibrant-orange" href="#">Pricing</a></li>
          </ul>
        </div>
        <div className="text-gray-600">
          <p className="font-semibold text-gray-900">Support</p>
          <ul className="mt-2 space-y-1">
            <li><a className="hover:text-vibrant-orange" href="#">FAQ</a></li>
            <li><a className="hover:text-vibrant-orange" href="#">Contact</a></li>
            <li><a className="hover:text-vibrant-orange" href="#">Privacy</a></li>
          </ul>
        </div>
        <div>
          <p className="font-semibold text-gray-900">Stay in the loop</p>
          <form className="mt-3 flex gap-2">
            <input type="email" placeholder="Your email" className="flex-1 px-4 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-vibrant-blue focus:border-vibrant-blue"/>
            <button type="button" className="px-4 py-2 rounded-lg text-white bg-gradient-to-r from-vibrant-blue to-teal-500 hover:brightness-105 transition-all shadow-lg hover:shadow-xl transform hover:scale-105">Subscribe</button>
          </form>
        </div>
      </div>
      <div className="py-4 text-center text-xs text-gray-500">© {new Date().getFullYear()} MedicoTourism. All rights reserved.</div>
    </footer>
  )
}

export default Footer


