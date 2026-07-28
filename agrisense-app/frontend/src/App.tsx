import { Route, Routes, useLocation } from 'react-router-dom'
import { AnimatePresence } from 'framer-motion'
import AppShell from './components/layout/AppShell'
import DashboardPage from './pages/DashboardPage'
import FieldDetailPage from './pages/FieldDetailPage'
import SimulatorPage from './pages/SimulatorPage'
import ModelPage from './pages/ModelPage'
import FieldComparisonPage from './pages/FieldComparisonPage'
import NotFoundPage from './pages/NotFoundPage'

export default function App() {
  const location = useLocation()

  return (
    <AppShell>
      <AnimatePresence mode="wait" initial={false}>
        <Routes location={location} key={location.pathname}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/fields/:fieldId" element={<FieldDetailPage />} />
          <Route path="/fields/:fieldId/simulate" element={<SimulatorPage />} />
          <Route path="/simulator" element={<SimulatorPage />} />
          <Route path="/compare" element={<FieldComparisonPage />} />
          <Route path="/model" element={<ModelPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </AnimatePresence>
    </AppShell>
  )
}
