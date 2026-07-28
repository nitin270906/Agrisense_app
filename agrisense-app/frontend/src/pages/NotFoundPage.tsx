import { motion } from 'framer-motion'
import { Home, ArrowLeft } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Card } from '../components/ui/primitives'

export default function NotFoundPage() {
  return (
    <motion.div
      className="flex min-h-[60vh] items-center justify-center"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      <Card className="max-w-md p-8 text-center">
        <div className="mb-4 text-6xl font-bold" style={{ color: 'var(--accent)' }}>
          404
        </div>
        <h1 className="mb-2 text-xl font-semibold text-ink">Page not found</h1>
        <p className="mb-6 text-sm text-ink-muted">
          The page you're looking for doesn't exist or has been moved.
        </p>
        <div className="flex justify-center gap-3">
          <Link
            to="/"
            className="flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition hover:bg-surface-2"
            style={{ color: 'var(--accent)' }}
          >
            <Home size={16} aria-hidden />
            Go to Dashboard
          </Link>
          <button
            onClick={() => window.history.back()}
            className="flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium text-ink-soft transition hover:bg-surface-2"
          >
            <ArrowLeft size={16} aria-hidden />
            Go Back
          </button>
        </div>
      </Card>
    </motion.div>
  )
}
