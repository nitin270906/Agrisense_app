import { useMemo } from 'react'

export default function ParticlesBackground() {
  const particles = useMemo(() => {
    return Array.from({ length: 24 }).map((_, i) => ({
      id: i,
      size: Math.random() * 4 + 2,
      x: Math.random() * 100,
      y: Math.random() * 100,
      duration: Math.random() * 18 + 12,
      delay: Math.random() * 5,
      opacity: Math.random() * 0.4 + 0.1,
    }))
  }, [])

  return (
    <div className="pointer-events-none fixed inset-0 z-0 overflow-hidden opacity-70">
      {particles.map((p) => (
        <div
          key={p.id}
          className="absolute rounded-full bg-[var(--accent)]"
          style={{
            width: `${p.size}px`,
            height: `${p.size}px`,
            left: `${p.x}%`,
            top: `${p.y}%`,
            opacity: p.opacity,
            animation: `floatParticle ${p.duration}s infinite ease-in-out ${p.delay}s`,
          }}
        />
      ))}
    </div>
  )
}
