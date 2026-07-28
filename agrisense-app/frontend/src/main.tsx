import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import ParticlesBackground from './components/ParticlesBackground'
import './index.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Dashboard aggregation runs live inference; refetching on every window
      // focus would re-run it constantly during a demo.
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 60_000,
    },
  },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <ParticlesBackground />
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
)
