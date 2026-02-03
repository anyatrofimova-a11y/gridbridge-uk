// GridBridge UI - MVP Dashboard (single-file React component)
// Filename suggestion: src/components/GridBridgeDashboard.jsx
// Tailwind CSS required. Uses recharts for charts and react-router for routing.
// Designed as an opinionated, production-ready single-file starter for the
// Developer Portal, Network Operator Portal, and Regulator Dashboard.

import React, { useEffect, useState } from 'react'
import { BrowserRouter as Router, Routes, Route, Link, useNavigate, useLocation } from 'react-router-dom'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, BarChart, Bar, Legend } from 'recharts'
import clsx from 'clsx'
import GridMapOverlay from './GridMapOverlay'
import GridSimulator from './GridSimulator'
import GridSimulatorMap from './GridSimulatorMap'

// Mock API helpers (replace with real endpoints)
const api = {
  async fetchHeadroom(substationId = 'all') {
    // GET /api/headroom?substation=...
    return fetch(`/api/headroom?substation=${substationId}`).then(r => r.ok ? r.json() : Promise.resolve(mockHeadroom()))
  },
  async fetchScenarios(siteId = 'demo') {
    return fetch(`/api/scenarios?site=${siteId}`).then(r => r.ok ? r.json() : Promise.resolve(mockScenarios()))
  },
  async fetchQueue() {
    return fetch('/api/queue').then(r => r.ok ? r.json() : Promise.resolve(mockQueue()))
  },
}

// ------------------------
// Small design system
// ------------------------
function Icon({ name }) {
  const icons = {
    dashboard: (<svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" d="M3 13h8V3H3v10zM3 21h8v-6H3v6zM13 21h8V11h-8v10zM13 3v6h8V3h-8z"/></svg>),
    search: (<svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path strokeWidth="1.5" d="M21 21l-4.35-4.35"/><circle cx="11" cy="11" r="6" strokeWidth="1.5"/></svg>),
    bolt: (<svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path strokeWidth="1.5" d="M13 2L3 14h7l-1 8 10-12h-7l1-8z"/></svg>),
  }
  return icons[name] || null
}

function TopNav({ title }) {
  return (
    <header className="bg-white border-b">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center gap-3">
            <div className="text-2xl font-semibold text-slate-800">GridBridge</div>
            <div className="text-sm text-slate-500">AI-Accelerated Connections — UK</div>
          </div>
          <div className="flex items-center gap-4">
            <nav className="hidden md:flex items-center gap-3 text-sm text-slate-600">
              <Link to="/">Dashboard</Link>
              <Link to="/simulator">Simulator</Link>
              <Link to="/map">Grid Map</Link>
              <Link to="/developer">Developer Portal</Link>
              <Link to="/operator">Network Operator</Link>
              <Link to="/regulator">Regulator</Link>
            </nav>
            <div className="text-xs text-slate-500">v1.0</div>
          </div>
        </div>
      </div>
    </header>
  )
}

function Sidebar() {
  return (
    <aside className="w-64 border-r bg-slate-50 p-4 hidden md:block">
      <div className="mb-4 text-xs uppercase text-slate-400">Tools</div>
      <ul className="space-y-2 text-sm">
        <li><Link to="/" className="flex items-center gap-2 p-2 rounded hover:bg-white"> <Icon name="dashboard"/>Overview</Link></li>
        <li><Link to="/search" className="flex items-center gap-2 p-2 rounded hover:bg-white"><Icon name="search"/>Site Search</Link></li>
        <li><Link to="/scenarios" className="flex items-center gap-2 p-2 rounded hover:bg-white"><Icon name="bolt"/>Scenario Builder</Link></li>
      </ul>
    </aside>
  )
}

// ------------------------
// Pages
// ------------------------
function Home() {
  const [headroom, setHeadroom] = useState(null)
  const [queue, setQueue] = useState([])
  useEffect(() => {
    api.fetchHeadroom().then(setHeadroom)
    api.fetchQueue().then(setQueue)
  }, [])

  return (
    <div className="p-6 grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div className="lg:col-span-2 space-y-6">
        <section className="bg-white p-4 rounded shadow-sm">
          <h2 className="text-lg font-semibold">System Headroom — snapshot</h2>
          <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Card title="Total Probabilistic Headroom" value={headroom ? `${headroom.total_p95} MW` : '—'} subtitle="P95 across modelled GSPs" />
            <Card title="Hidden (Queue-adjusted)" value={headroom ? `${headroom.hidden_mw} MW` : '—'} subtitle="Estimated available non-firm MW" />
          </div>

          <div className="mt-6">
            <h3 className="text-sm text-slate-600 mb-2">Top candidate GSPs</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {(headroom?.top_gsps || mockHeadroom().top_gsps).map(g => (
                <div key={g.id} className="p-3 border rounded flex justify-between items-center">
                  <div>
                    <div className="font-medium">{g.name}</div>
                    <div className="text-xs text-slate-500">{g.voltage} • {g.region}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-lg font-semibold">{g.hidden_mw} MW</div>
                    <div className="text-xs text-slate-500">Confidence: {g.confidence}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="bg-white p-4 rounded shadow-sm">
          <h2 className="text-lg font-semibold">Queue & Attrition — live feed</h2>
          <div className="mt-4">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-slate-400 border-b">
                  <th className="py-2">Project</th>
                  <th>MW</th>
                  <th>State</th>
                  <th>Completion Prob</th>
                </tr>
              </thead>
              <tbody>
                {(queue || mockQueue()).slice(0,8).map(q=> (
                  <tr key={q.id} className="border-b hover:bg-slate-50">
                    <td className="py-2">{q.name} <div className="text-xs text-slate-400">{q.developer}</div></td>
                    <td>{q.request_mw}</td>
                    <td>{q.state}</td>
                    <td>{Math.round(q.prob*100)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>

      <aside className="space-y-6">
        <section className="bg-white p-4 rounded shadow-sm">
          <h3 className="text-sm font-semibold">Quick Search</h3>
          <p className="text-xs text-slate-500 mt-1">Postcode, substation, or GSP name</p>
          <SearchBox />
        </section>

        <section className="bg-white p-4 rounded shadow-sm">
          <h3 className="text-sm font-semibold">Scenario Snapshot</h3>
          <div className="h-36 mt-3">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={mockScenarioChart()}>
                <XAxis dataKey="t" tick={{fontSize:10}} />
                <YAxis tick={{fontSize:10}} />
                <Tooltip />
                <Area type="monotone" dataKey="headroom" stroke="#10b981" fill="#bbf7d0" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </section>

        <section className="bg-white p-4 rounded shadow-sm">
          <h3 className="text-sm font-semibold">Actions</h3>
          <div className="mt-3 grid gap-2">
            <button className="py-2 px-3 rounded bg-sky-600 text-white text-sm">Start a site analysis</button>
            <button className="py-2 px-3 rounded border text-sm">Request DNO data refresh</button>
          </div>
        </section>
      </aside>
    </div>
  )
}

function GridMapPage() {
  return (
    <div className="p-6">
      <h1 className="text-2xl font-semibold mb-4">Grid Map Overlay</h1>
      <p className="text-slate-600 mb-6">
        Multi-source data integration from Kilowatts Grid, National Grid Data Portal,
        Carbon Intensity API, CfD Watch, Octopy Energy, and ETS Watch.
      </p>
      <GridMapOverlay />
    </div>
  )
}

function DeveloperPortal() {
  const [site, setSite] = useState('Cambridge-AI')
  const [scenarios, setScenarios] = useState(null)
  useEffect(()=>{ api.fetchScenarios(site).then(setScenarios) }, [site])

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-semibold">Developer Portal</h1>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-4">
          <section className="bg-white p-4 rounded shadow-sm">
            <h3 className="font-medium">Connection Builder</h3>
            <p className="text-sm text-slate-500">Assemble a connection offer: firm MW, flexible MW, BESS, backup.</p>
            <ConnectionBuilder />
          </section>

          <section className="bg-white p-4 rounded shadow-sm">
            <h3 className="font-medium">Scenario Stress Tests</h3>
            <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="p-3 border rounded">
                <div className="text-xs text-slate-500">Scenarios analysed</div>
                <div className="text-lg font-semibold">{scenarios ? scenarios.total : '—'}</div>
              </div>
              <div className="p-3 border rounded">
                <div className="text-xs text-slate-500">P90 Curtailment</div>
                <div className="text-lg font-semibold">{scenarios ? `${scenarios.p90} MW` : '—'}</div>
              </div>
            </div>
            <div className="mt-4">
              <StressChart data={scenarios?.distribution || []} />
            </div>
          </section>
        </div>

        <aside className="space-y-4">
          <section className="bg-white p-4 rounded shadow-sm">
            <h4 className="text-sm font-medium">Site</h4>
            <select className="mt-2 p-2 border rounded w-full" value={site} onChange={e=>setSite(e.target.value)}>
              <option>Cambridge-AI</option>
              <option>Didcot-400kV</option>
              <option>Manchester-BSP</option>
            </select>
            <div className="mt-3 text-xs text-slate-500">Estimated time-to-power with FlexConnect: <b>12 months</b></div>
          </section>

          <section className="bg-white p-4 rounded shadow-sm">
            <h4 className="text-sm font-medium">Deliverables</h4>
            <ul className="text-sm mt-2 space-y-2">
              <li>Connection Summary (PDF)</li>
              <li>Stress Test Report</li>
              <li>Curtailment Contract (draft)</li>
            </ul>
          </section>
        </aside>
      </div>
    </div>
  )
}

function OperatorPortal() {
  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-semibold">Network Operator Portal</h1>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-4">
          <section className="bg-white p-4 rounded shadow-sm">
            <h3 className="font-medium">Utilisation vs TEC</h3>
            <OperatorUtilisationChart />
          </section>

          <section className="bg-white p-4 rounded shadow-sm">
            <h3 className="font-medium">Queue Analytics</h3>
            <QueueAnalytics />
          </section>
        </div>

        <aside className="space-y-4">
          <section className="bg-white p-4 rounded shadow-sm">
            <h4 className="text-sm font-medium">Alerts</h4>
            <div className="text-sm mt-2">No safety alerts</div>
          </section>

          <section className="bg-white p-4 rounded shadow-sm">
            <h4 className="text-sm font-medium">ANM Control</h4>
            <div className="mt-2 text-xs text-slate-500">Pilot ANM active on 2 zones</div>
            <button className="mt-3 w-full py-2 rounded border">Open ANM Console</button>
          </section>
        </aside>
      </div>
    </div>
  )
}

function RegulatorDashboard() {
  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-semibold">Regulator Dashboard — Ofgem View</h1>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-4">
          <section className="bg-white p-4 rounded shadow-sm">
            <h3 className="font-medium">System Metrics</h3>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-3">
              <Metric title="Queue velocity" value="-18%" subtitle="avg time to energisation"/>
              <Metric title="MW accelerated" value="+512 MW" subtitle="via FlexConnect"/>
              <Metric title="Constraint cost change" value="-£2.3m" subtitle="estimated annual"/>
            </div>
          </section>

          <section className="bg-white p-4 rounded shadow-sm">
            <h3 className="font-medium">Comparative DNO Performance</h3>
            <BarRank />
          </section>
        </div>

        <aside className="space-y-4">
          <section className="bg-white p-4 rounded shadow-sm">
            <h4 className="text-sm font-medium">Methodology</h4>
            <div className="text-xs text-slate-500 mt-2">Method version: 1.0 • Last updated: 2026-02-03</div>
            <button className="mt-3 w-full py-2 rounded border">Download Methodology</button>
          </section>
        </aside>
      </div>
    </div>
  )
}

// ------------------------
// Small UI components used above
// ------------------------
function Card({ title, value, subtitle }) {
  return (
    <div className="p-4 border rounded bg-white">
      <div className="text-xs text-slate-500">{title}</div>
      <div className="mt-2 text-2xl font-semibold">{value}</div>
      <div className="text-xs text-slate-400 mt-1">{subtitle}</div>
    </div>
  )
}

function SearchBox() {
  const [q, setQ] = useState('')
  const navigate = useNavigate()
  return (
    <div className="mt-3">
      <div className="flex gap-2">
        <input className="flex-1 p-2 border rounded" placeholder="e.g. Didcot 400kV" value={q} onChange={e=>setQ(e.target.value)} />
        <button className="px-3 py-2 bg-sky-600 text-white rounded" onClick={()=>navigate(`/search?q=${encodeURIComponent(q)}`)}>Search</button>
      </div>
      <div className="text-xs text-slate-400 mt-2">Tip: try postcode or GSP name</div>
    </div>
  )
}

function ConnectionBuilder(){
  const [firm, setFirm] = useState(50)
  const [flex, setFlex] = useState(100)
  const [bess, setBess] = useState(20)
  const est = Math.round((firm + flex*0.5 + bess*0.3))
  return (
    <div className="mt-3 grid grid-cols-1 gap-3">
      <label className="text-sm">Firm capacity (MW)</label>
      <input type="range" min="0" max="300" value={firm} onChange={e=>setFirm(+e.target.value)} />
      <div className="text-sm">{firm} MW</div>

      <label className="text-sm">Flexible capacity (MW)</label>
      <input type="range" min="0" max="300" value={flex} onChange={e=>setFlex(+e.target.value)} />
      <div className="text-sm">{flex} MW</div>

      <label className="text-sm">On-site BESS (MWh)</label>
      <input type="range" min="0" max="200" value={bess} onChange={e=>setBess(+e.target.value)} />
      <div className="text-sm">{bess} MWh</div>

      <div className="mt-2 p-3 border rounded bg-slate-50">Estimated early-available MW: <b>{est} MW</b></div>
      <div className="flex gap-2">
        <button className="py-2 px-3 bg-emerald-600 text-white rounded">Request FlexConnect offer</button>
        <button className="py-2 px-3 border rounded">Export report</button>
      </div>
    </div>
  )
}

function StressChart({ data }){
  const d = data.length ? data : [{label:'P10',val:10},{label:'P50',val:45},{label:'P90',val:78}]
  return (
    <div style={{height:200}}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={d.map((x,i)=>({name:x.label || `s${i}`, value:x.val || x}))}>
          <XAxis dataKey="name" />
          <YAxis />
          <Tooltip />
          <Bar dataKey="value" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

function OperatorUtilisationChart(){
  const data = [{t:'00:00', utilisation:45},{t:'06:00',utilisation:52},{t:'12:00',utilisation:78},{t:'18:00',utilisation:88}]
  return (
    <div style={{height:220}}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data}>
          <XAxis dataKey="t" />
          <YAxis />
          <Tooltip />
          <Area type="monotone" dataKey="utilisation" stroke="#f59e0b" fill="#ffedd5"/>
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}

function QueueAnalytics(){
  return (<div className="p-3 border rounded text-sm">Queue analytics visualisation placeholder — scatter of requested MW vs time-in-queue, attrition model outputs and filter controls.</div>)
}

function Metric({title,value,subtitle}){
  return (
    <div className="p-3 border rounded bg-white">
      <div className="text-xs text-slate-400">{title}</div>
      <div className="text-xl font-semibold mt-1">{value}</div>
      <div className="text-xs text-slate-400 mt-1">{subtitle}</div>
    </div>
  )
}

function BarRank(){
  const data = [{dno:'WPD',v:120},{dno:'UKPN',v:85},{dno:'SSEN',v:60}]
  return (
    <div style={{height:220}}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical">
          <XAxis type="number" />
          <YAxis type="category" dataKey="dno" />
          <Tooltip />
          <Bar dataKey="v" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

// ------------------------
// Router + App shell
// ------------------------

// Wrapper to check current route
function AppContent() {
  const location = useLocation();
  const isSimulator = location.pathname === '/simulator';

  // Simulator gets full viewport - no nav/sidebar
  if (isSimulator) {
    return <GridSimulatorMap />;
  }

  return (
    <div className="min-h-screen bg-slate-100 text-slate-800">
      <TopNav />
      <div className="flex">
        <Sidebar />
        <main className="flex-1">
          <Routes>
            <Route path="/" element={<Home/>} />
            <Route path="/map" element={<GridMapPage/>} />
            <Route path="/developer" element={<DeveloperPortal/>} />
            <Route path="/operator" element={<OperatorPortal/>} />
            <Route path="/regulator" element={<RegulatorDashboard/>} />
            <Route path="*" element={<Home/>} />
          </Routes>
        </main>
      </div>
    </div>
  );
}

export default function GridBridgeDashboard(){
  return (
    <Router>
      <Routes>
        <Route path="/*" element={<AppContent />} />
      </Routes>
    </Router>
  )
}

// ------------------------
// Mock data helpers (for local dev)
// ------------------------
function mockHeadroom(){
  return {
    total_p95: 420,
    hidden_mw: 178,
    top_gsps: [
      {id:'didcot', name:'Didcot 400kV GSP', voltage:'400kV', region:'South', hidden_mw:45, confidence:'HIGH'},
      {id:'burwell', name:'Burwell 132kV', voltage:'132kV', region:'East', hidden_mw:37, confidence:'MEDIUM'},
      {id:'man-bsp', name:'Manchester BSP', voltage:'132kV', region:'North', hidden_mw:28, confidence:'LOW'},
    ]
  }
}

function mockQueue(){
  return [
    {id:'q1',name:'Hypothetical Solar', request_mw:50, developer:'Acme Renew', state:'pre-application', prob:0.35},
    {id:'q2',name:'AI Campus', request_mw:150, developer:'DeepCompute', state:'connection offer', prob:0.75},
    {id:'q3',name:'Storage Park', request_mw:30, developer:'BatteryCo', state:'agreement signed', prob:0.9},
  ]
}

function mockScenarios(){
  return { total:10000, p90:45, distribution:[{label:'P10',val:5},{label:'P50',val:22},{label:'P90',val:45}] }
}

function mockScenarioChart(){
  return Array.from({length:12}).map((_,i)=>({t:`t${i}`, headroom: 30 + Math.sin(i/3)*10}))
}

// ------------------------
// Accessibility & notes
// ------------------------
// - All interactive controls should have keyboard focus states and aria labels in production
// - Replace mock API calls with the platform backend endpoints (examples in the design doc):
//   GET /api/headroom?substation={id}
//   GET /api/scenarios?site={id}
//   GET /api/queue
// - Prefetching & caching: use SWR or React Query in production for low-latency interactivity
// - Authentication: integrate with OIDC (Auth0 / Keycloak) and role-based feature flags for Developer / Operator / Regulator
// - Tests: unit tests for components (React Testing Library) and end-to-end tests (Cypress)

// ------------------------
// Quick run instructions:
// 1) Ensure you have a React app with Tailwind configured (Create React App / Vite + Tailwind)
// 2) Add recharts, react-router-dom, clsx
//    npm i recharts react-router-dom clsx
// 3) Create src/components/GridBridgeDashboard.jsx and paste this file
// 4) Import in App.jsx: import GridBridgeDashboard from './components/GridBridgeDashboard'
//    and render <GridBridgeDashboard />
// 5) Wire backend proxy for /api/* endpoints to the GridBridge backend (or keep mocks)

// End of file
