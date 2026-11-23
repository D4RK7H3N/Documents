import { useState, useEffect } from 'react'
import {
  GraduationCap, Users, Wallet, Building2, BarChart3,
  Settings, Shield, Download, ArrowRight, Check, Plus,
  Star, ChevronDown, Menu, X, BookOpen,
  HomeIcon, CreditCard, BedDouble, FileText, BookMarked
} from 'lucide-react'
import PesoSign from '../components/PesoSign'

function Navbar() {
  const [menuOpen, setMenuOpen] = useState(false)

  const scrollTo = (id) => {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' })
    setMenuOpen(false)
  }

  return (
    <nav className="navbar">
      <div className="navbar-inner">
        <a href="#" className="navbar-brand" onClick={(e) => { e.preventDefault(); window.scrollTo({ top: 0, behavior: 'smooth' }) }}>
          <svg className="navbar-brand-icon" viewBox="0 0 36 36" xmlns="http://www.w3.org/2000/svg">
            <circle cx="18" cy="18" r="17" fill="#1a3a5c" stroke="#c9a84c" strokeWidth="2"/>
            <text x="18" y="23" textAnchor="middle" fontFamily="Segoe UI" fontSize="12" fontWeight="700" fill="#c9a84c">SMS</text>
          </svg>
          <span className="navbar-brand-text">School Management System</span>
        </a>

        <ul className="navbar-links">
          <li><a href="#features" onClick={(e) => { e.preventDefault(); scrollTo('features') }}>Features</a></li>
          <li><a href="#screenshots" onClick={(e) => { e.preventDefault(); scrollTo('screenshots') }}>Screenshots</a></li>
          <li><a href="#pricing" onClick={(e) => { e.preventDefault(); scrollTo('pricing') }}>Pricing</a></li>
          <li><a href="#faq" onClick={(e) => { e.preventDefault(); scrollTo('faq') }}>FAQ</a></li>
          <li><a href="#pricing" className="navbar-cta" onClick={(e) => { e.preventDefault(); scrollTo('pricing') }}>Get Started</a></li>
        </ul>
      </div>
    </nav>
  )
}

function Hero() {
  return (
    <section className="hero">
      <div className="hero-inner">
        <div className="hero-text">
          <div className="hero-badge">
            <Star size={10} fill="currentColor" />
            Version 1.0.0 Now Available
          </div>
          <h1 className="hero-title">
            Streamline Your<br />
            <span>School Operations</span><br />
            With Confidence
          </h1>
          <p className="hero-desc">
            A powerful, all-in-one desktop application for managing student records,
            academic tracks, dormitory assignments, and financial transactions — designed
            for Philippine educational institutions.
          </p>
          <div className="hero-actions">
            <a href="#pricing" className="btn-primary" onClick={(e) => { e.preventDefault(); document.getElementById('pricing')?.scrollIntoView({ behavior: 'smooth' }) }}>
              <Download size={16} />
              Get Started
            </a>
            <a href="#features" className="btn-secondary" onClick={(e) => { e.preventDefault(); document.getElementById('features')?.scrollIntoView({ behavior: 'smooth' }) }}>
              <ArrowRight size={16} />
              Explore Features
            </a>
          </div>
          <div className="hero-stats">
            <div>
              <div className="hero-stat-value">500+</div>
              <div className="hero-stat-label">Active Installations</div>
            </div>
            <div>
              <div className="hero-stat-value">99.9%</div>
              <div className="hero-stat-label">Uptime Guarantee</div>
            </div>
            <div>
              <div className="hero-stat-value">24/7</div>
              <div className="hero-stat-label">Local Support</div>
            </div>
          </div>
        </div>

        <div className="hero-visual">
          <div className="hero-window">
            <div className="hero-window-header">
              <div className="hero-window-dot dot-red" />
              <div className="hero-window-dot dot-yellow" />
              <div className="hero-window-dot dot-green" />
              <span className="hero-window-title">School Management System</span>
            </div>
            <div className="hero-window-body">
              <div className="hero-window-sidebar">
                <div className="hero-sidebar-item w60" />
                <div className="hero-sidebar-item w80 active" />
                <div className="hero-sidebar-item w60" />
                <div className="hero-sidebar-item w80" />
                <div className="hero-sidebar-item w60 active-short" />
                <div className="hero-sidebar-item w80" />
                <div className="hero-sidebar-item w60" />
              </div>
              <div className="hero-window-content">
                <div className="hero-content-row">
                  <div className="hero-card">
                    <div className="hero-card-label">Total Students</div>
                    <div className="hero-card-value">1,248</div>
                    <div className="hero-card-sub">+42 this semester</div>
                  </div>
                  <div className="hero-card">
                    <div className="hero-card-label">Collection</div>
                    <div className="hero-card-value">₱842K</div>
                    <div className="hero-card-sub">of ₱1.2M target</div>
                  </div>
                </div>
                <div className="hero-bar-row">
                  <span className="hero-bar-label">Collection</span>
                  <div className="hero-bar-track"><div className="hero-bar-fill" style={{width: '70%'}}/></div>
                </div>
                <div className="hero-bar-row">
                  <span className="hero-bar-label">Enrollment</span>
                  <div className="hero-bar-track"><div className="hero-bar-fill" style={{width: '85%'}}/></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

function Features() {
  const features = [
    {
      icon: <Users size={24} />,
      title: 'Student Information System',
      desc: 'Complete student档案 with enrollment history, academic records, contact info, and guardian details — searchable and sortable in seconds.'
    },
    {
      icon: <BookOpen size={24} />,
      title: 'Academic Track Management',
      desc: 'Manage tracks, strands, sections, and courses with ease. Assign teachers and schedule classes without the paperwork.'
    },
    {
      icon: <Wallet size={24} />,
      title: 'Financial & Tuition Management',
      desc: 'Track payments, manage tuition fees, generate receipts, and monitor student balances. Supports various payment methods and fee structures.'
    },
    {
      icon: <BedDouble size={24} />,
      title: 'Dormitory Management',
      desc: 'Assign dormitory buildings, rooms, and beds to students. Track occupancy, move-ins, and move-outs with real-time availability views.'
    },
    {
      icon: <BarChart3 size={24} />,
      title: 'Dashboard & Reporting',
      desc: 'Real-time statistics on enrollment, collections, and dorm occupancy. Export reports to PDF and Excel for auditing and compliance.'
    },
    {
      icon: <Shield size={24} />,
      title: 'Role-Based Access Control',
      desc: 'Secure admin and staff accounts with granular permissions. Sensitive data stays protected while your team has exactly the access they need.'
    },
    {
      icon: <CreditCard size={24} />,
      title: 'Point of Sale (POS)',
      desc: 'Process school store purchases, manage inventory, and track sales. Perfect for bookstores, canteens, and uniform shops.'
    },
    {
      icon: <FileText size={24} />,
      title: 'Activity & Event Management',
      desc: 'Manage campus tours, enrollment events, and graduation ceremonies. Track attendance and generate event reports effortlessly.'
    },
    {
      icon: <Settings size={24} />,
      title: 'School Configuration',
      desc: 'Customize school name, logo, tagline, and academic year settings. Make the system truly yours with branded identity.'
    },
  ]

  return (
    <section className="section features" id="features">
      <div className="section-inner">
        <div className="section-header">
          <span className="section-label">Features</span>
          <h2 className="section-title">Everything You Need to Run<br />Your School Efficiently</h2>
          <p className="section-desc">
            From enrollment to graduation, manage every aspect of your institution
            with a single, powerful application built for Philippine schools.
          </p>
        </div>
        <div className="features-grid">
          {features.map((f, i) => (
            <div className="feature-card" key={i}>
              <div className="feature-icon">{f.icon}</div>
              <h3 className="feature-title">{f.title}</h3>
              <p className="feature-desc">{f.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

function Screenshots() {
  const [selectedImage, setSelectedImage] = useState(null)

  const screenshots = [
    { img: '/screenshots/Screenshot 2026-06-08 232112.png', title: 'Log-in', desc: 'Secure access to the application' },
    { img: '/screenshots/Screenshot 2026-06-08 224530.png', title: 'Dashboard', desc: 'Real-time statistics and key metrics at a glance' },
    { img: '/screenshots/Screenshot 2026-06-08 225035.png', title: 'Student List', desc: 'Complete student enrollment records and search' },
    { img: '/screenshots/Screenshot 2026-06-08 225054.png', title: 'Section', desc: 'Comprehensive student section management' },
    { img: '/screenshots/Screenshot 2026-06-08 225110.png', title: 'Academic Tracks', desc: 'Manage tracks, strands, and academic programs' },
    { img: '/screenshots/Screenshot 2026-06-08 225121.png', title: 'Course Management', desc: 'Organize courses and class schedules efficiently' },
    { img: '/screenshots/Screenshot 2026-06-08 225450.png', title: 'Enrollment', desc: 'Streamlined student enrollment workflow' },
    { img: '/screenshots/Screenshot 2026-06-08 225458.png', title: 'Drop Outs', desc: 'Track Dropout students and their information' },
    { img: '/screenshots/Screenshot 2026-06-08 225515.png', title: 'Cashier', desc: 'Process payments and manage transactions' },
    { img: '/screenshots/Screenshot 2026-06-08 225521.png', title: 'Tuition fees', desc: 'Track tuition payments and student balances' },
    { img: '/screenshots/Screenshot 2026-06-08 225533.png', title: 'Revenue Reports', desc: 'Financial overview and revenue analytics' },
    { img: '/screenshots/Screenshot 2026-06-08 225540.png', title: 'Pending', desc: 'View and manage pending payment actions or requests' },
    { img: '/screenshots/Screenshot 2026-06-08 225546.png', title: 'Sales', desc: 'Manage sales transactions and customer interactions' },
    { img: '/screenshots/Screenshot 2026-06-08 225556.png', title: 'Assessments', desc: 'Student assessments and grade tracking' },
    { img: '/screenshots/Screenshot 2026-06-08 225613.png', title: 'Graduation', desc: 'Graduation events and ceremony management' },
    { img: '/screenshots/Screenshot 2026-06-08 225621.png', title: 'Tours', desc: 'Educational tours and trip management' },
    { img: '/screenshots/Screenshot 2026-06-08 225628.png', title: 'Dormitory', desc: 'Room allocation and occupancy management' },
    { img: '/screenshots/Screenshot 2026-06-08 225637.png', title: 'Settings', desc: 'Application settings and preferences' },
    { img: '/screenshots/Screenshot 2026-06-08 225647.png', title: 'User Profile', desc: 'Account settings and profile management' },
    { img: '/screenshots/Screenshot 2026-06-08 232038.png', title: 'School Configuration', desc: 'Configure school-specific settings and branding' },
  ]

  useEffect(() => {
    const handleKeyDown = (event) => {
      if (event.key === 'Escape') {
        setSelectedImage(null)
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  return (
    <section className="section" id="screenshots">
      <div className="section-inner">
        <div className="section-header">
          <span className="section-label">Screenshots</span>
          <h2 className="section-title">Built for Clarity<br />and Ease of Use</h2>
          <p className="section-desc">
            Clean, intuitive interfaces designed for school administrators
            who need efficiency without complexity.
          </p>
        </div>
        <div className="screenshots-photo-grid">
          {screenshots.map((s, i) => (
            <button type="button" className="screenshot-photo-card" key={i} onClick={() => setSelectedImage(s)}>
              <div className="screenshot-photo-wrapper">
                <img src={s.img} alt={s.title} loading="lazy" />
              </div>
              <div className="screenshot-photo-caption">
                <h3>{s.title}</h3>
                <p>{s.desc}</p>
              </div>
            </button>
          ))}
        </div>
      </div>

      {selectedImage && (
        <div className="screenshot-lightbox" role="dialog" aria-modal="true" onClick={() => setSelectedImage(null)}>
          <div className="screenshot-lightbox-content" onClick={(event) => event.stopPropagation()}>
            <button type="button" className="screenshot-lightbox-close" onClick={() => setSelectedImage(null)} aria-label="Close preview">
              ×
            </button>
            <img src={selectedImage.img} alt={selectedImage.title} />
            <div className="screenshot-lightbox-caption">
              <h3>{selectedImage.title}</h3>
              <p>{selectedImage.desc}</p>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}

function HowItWorks() {
  const steps = [
    {
      n: '1',
      title: 'Download & Install',
      desc: 'Download the installer for Windows. Run the setup and follow the wizard — takes under 2 minutes. No internet required after installation.'
    },
    {
      n: '2',
      title: 'Configure Your School',
      desc: 'Set up your school name, logo, and branding. Add academic tracks, dormitory buildings, and fee structures to match your institution.'
    },
    {
      n: '3',
      title: 'Start Managing',
      desc: 'Add students, record payments, assign dorm rooms, and generate reports. Everything is accessible from the sidebar navigation.'
    },
  ]

  return (
    <section className="section how-it-works">
      <div className="section-inner">
        <div className="section-header">
          <span className="section-label">How It Works</span>
          <h2 className="section-title">Up and Running<br />in Under 5 Minutes</h2>
          <p className="section-desc">
            No complex setup, no external servers, no recurring subscriptions.
            Install, configure, and start managing your school.
          </p>
        </div>
        <div className="steps-grid">
          {steps.map((s, i) => (
            <div className="step-card" key={i}>
              <div className="step-number">{s.n}</div>
              <h3 className="step-title">{s.title}</h3>
              <p className="step-desc">{s.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

function Pricing() {
  return (
    <section className="section pricing" id="pricing">
      <div className="section-inner">
        <div className="section-header">
          <span className="section-label">Pricing</span>
          <h2 className="section-title">Simple, Transparent Pricing</h2>
          <p className="section-desc">
            One-time purchase, lifetime license. No monthly fees, no hidden costs.
            The application runs exclusively on your local area network.
          </p>
        </div>
        <div className="pricing-grid">
          <div className="pricing-card popular" style={{ maxWidth: 480, margin: '0 auto' }}>
            <div className="pricing-popular-badge-center">One-Time Purchase</div>
            <div className="pricing-tier">Professional</div>
            <div className="pricing-price">₱800,000 <span>PHP</span></div>
            <div className="pricing-period">Lifetime license — no subscriptions</div>
            <ul className="pricing-features">
              <li><Check size={16} className="check-icon" /> Unlimited students</li>
              <li><Check size={16} className="check-icon" /> Student information system</li>
              <li><Check size={16} className="check-icon" /> Academic track management</li>
              <li><Check size={16} className="check-icon" /> Dormitory management</li>
              <li><Check size={16} className="check-icon" /> Financial & tuition tracking</li>
              <li><Check size={16} className="check-icon" /> Point of Sale (POS)</li>
              <li><Check size={16} className="check-icon" /> Activity & event management</li>
              <li><Check size={16} className="check-icon" /> School branding customization</li>
              <li><Check size={16} className="check-icon" /> Role-based access (admin & staff)</li>
              <li><Check size={16} className="check-icon" /> Dashboard & reporting</li>
              <li><Check size={16} className="check-icon" /> Free remote installation support</li>
              <li><Check size={16} className="check-icon" /> Free updates for 1 year</li>
            </ul>
            <a href="mailto:espanoldan8@gmail.com?subject=Professional%20License%20Inquiry" className="pricing-btn pricing-btn-primary">Contact Sales</a>
          </div>
        </div>
      </div>
    </section>
  )
}

function Testimonials() {
  const testimonials = [
    {
      stars: 5,
      text: '"SMS has transformed how we manage student records and collections. What used to take hours now takes minutes. The dormitory module alone saved us countless hours of manual work."',
      name: 'Maria Teresa Reyes',
      role: "Registrar, St. Mary's Academy"
    },
    {
      stars: 5,
      text: '"The financial tracking is incredibly thorough. We can see exactly where every peso goes, track overdue balances, and generate audit-ready reports with a single click."',
      name: 'Roberto Santos',
      role: 'Accountant, Naga City College'
    },
    {
      stars: 5,
      text: '"Installation was seamless and the interface is so intuitive that our non-tech-savvy staff picked it up immediately. Highly recommended for any Philippine school."',
      name: 'Carmen Lim',
      role: 'Principal, Cebu Academy'
    },
  ]

  return (
    <section className="section" id="testimonials">
      <div className="section-inner">
        <div className="section-header">
          <span className="section-label">Testimonials</span>
          <h2 className="section-title">Trusted by Schools<br />Across the Philippines</h2>
          <p className="section-desc">
            Join hundreds of educational institutions that have modernized
            their operations with School Management System.
          </p>
        </div>
        <div className="testimonials-grid">
          {testimonials.map((t, i) => (
            <div className="testimonial-card" key={i}>
              <div className="testimonial-stars">
                {Array.from({ length: t.stars }).map((_, j) => (
                  <Star key={j} size={14} fill="currentColor" />
                ))}
              </div>
              <p className="testimonial-text">{t.text}</p>
              <div className="testimonial-author">
                <div className="testimonial-avatar">{t.name.split(' ').map(w => w[0]).slice(0, 2).join('')}</div>
                <div>
                  <div className="testimonial-name">{t.name}</div>
                  <div className="testimonial-role">{t.role}</div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

function FAQ() {
  const [openIndex, setOpenIndex] = useState(null)

  const faqs = [
    {
      q: 'What are the system requirements?',
      a: 'School Management System runs on Windows 7 and above. It requires at least 4GB of RAM, 500MB of disk space, and a PostgreSQL database (included with the installer). No internet connection is required.'
    },
    {
      q: 'Does the app work on the internet?',
      a: 'No. School Management System is designed exclusively for local area network (LAN) deployment. The application and database run on a local server within your school campus, ensuring your data never leaves your premises. All computers on the same network can access the system simultaneously.'
    },
    {
      q: 'Can I customize the school branding?',
      a: 'Absolutely. You can upload your school logo, set your school name, short name, and tagline. All of these appear throughout the application, including reports and receipts — giving your school a professional, branded experience.'
    },
    {
      q: 'Is my data secure?',
      a: 'Yes. All data is stored locally on your own server. The app uses role-based access control with separate admin and staff accounts. Admin-only areas are protected, and all sensitive financial data is confined to your local network.'
    },
    {
      q: 'What are valid reasons to choose this system over cloud solutions?',
      a: 'School Management System is ideal if you: (1) need complete data ownership and privacy — no cloud dependency, (2) have unreliable or no internet access, (3) prefer one-time payment over recurring subscriptions, (4) operate in areas with strict data privacy regulations, or (5) want a system that works reliably under high load without internet latency.'
    },
    {
      q: 'What payment methods do you accept?',
      a: 'We accept bank transfers (BPI, BDO, UnionBank), GCash, and PayMaya. For school-wide deployments, we also offer invoicing. Volume discounts and site licenses are available — contact us for a custom quotation.'
    },
    {
      q: 'Do you offer installation support?',
      a: 'Yes. All purchases include free remote installation support via TeamViewer or AnyDesk. We will set up the application, configure your school settings, and help you import existing student data if available.'
    },
    {
      q: 'Are updates included?',
      a: 'All minor version updates (e.g., 1.0 to 1.1) are free for licensed users. Major version upgrades (e.g., 1.x to 2.0) are available at a discounted upgrade price. We also provide bug fixes and security patches as needed.'
    },
  ]

  return (
    <section className="section faq" id="faq">
      <div className="section-inner">
        <div className="section-header">
          <span className="section-label">FAQ</span>
          <h2 className="section-title">Frequently Asked<br />Questions</h2>
          <p className="section-desc">
            Have questions? We have answers. If you don't find what
            you're looking for, reach out to our support team.
          </p>
        </div>
        <div className="faq-list">
          {faqs.map((faq, i) => (
            <div className="faq-item" key={i}>
              <button
                className={`faq-question ${openIndex === i ? 'open' : ''}`}
                onClick={() => setOpenIndex(openIndex === i ? null : i)}
              >
                {faq.q}
                <Plus size={18} className="faq-icon" />
              </button>
              <div className={`faq-answer ${openIndex === i ? 'open' : ''}`}>
                <div className="faq-answer-inner">{faq.a}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

function CTA() {
  return (
    <section className="cta">
      <div className="cta-inner">
        <h2 className="cta-title">
          Ready to Modernize<br />
          Your <span>School Operations</span>?
        </h2>
        <p className="cta-desc">
          Contact us today for a personalized demo and quotation.
          School Management System is designed for Philippine institutions
          that need a reliable, offline-first solution.
        </p>
        <div className="cta-actions">
          <a href="mailto:espanoldan8@gmail.com?subject=School%20Management%20System%20Inquiry" className="btn-primary">
            <Download size={16} />
            Contact Sales
          </a>
          <a href="mailto:support@schoolmanagementsystem.ph" className="btn-secondary">
            Get Support
          </a>
        </div>
      </div>
    </section>
  )
}

function Footer() {
  return (
    <footer className="footer">
      <div className="footer-inner">
        <div className="footer-top">
          <div className="footer-brand">
            <div className="footer-brand-header">
              <svg width="36" height="36" viewBox="0 0 36 36" xmlns="http://www.w3.org/2000/svg">
                <circle cx="18" cy="18" r="17" fill="#1a3a5c" stroke="#c9a84c" strokeWidth="2"/>
                <text x="18" y="23" textAnchor="middle" fontFamily="Segoe UI" fontSize="12" fontWeight="700" fill="#c9a84c">SMS</text>
              </svg>
              <h3 className="footer-brand-title"></h3>
            </div>
            <p>
              School Management System is a secure, offline-first desktop platform built for Philippine schools.
              It helps administrators manage student records, academic programs, dormitory assignments, payments,
              reports, and daily operations from one reliable system.
            </p>
          </div>
        </div>
        <div className="footer-bottom">
          <span className="footer-copyright">© 2026 School Management System. All rights reserved.</span>
          <ul className="footer-links">
            <li><a href="#">Privacy</a></li>
            <li><a href="#">Terms</a></li>
            <li><a href="#">Cookies</a></li>
          </ul>
        </div>
      </div>
    </footer>
  )
}

export default function App() {
  return (
    <>
      <Navbar />
      <Hero />
      <Features />
      <Screenshots />
      <HowItWorks />
      <Pricing />
      <FAQ />
      <CTA />
      <Footer />
    </>
  )
}