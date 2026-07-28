import { useState } from 'react'
import { Download, FileSpreadsheet, FileJson } from 'lucide-react'

interface DataExportProps<T extends Record<string, unknown>> {
  data: T[]
  filename?: string
  label?: string
}

export default function DataExport<T extends Record<string, unknown>>({
  data,
  filename = 'agrisense-export',
  label = 'Export data',
}: DataExportProps<T>) {
  const [isOpen, setIsOpen] = useState(false)

  const downloadFile = (content: string, type: 'csv' | 'json', ext: string) => {
    const timestamp = new Date().toISOString().split('T')[0]
    const fullFilename = `${filename}-${timestamp}.${ext}`
    const mimeType = type === 'csv' ? 'text/csv;charset=utf-8;' : 'application/json'

    const blob = new Blob([content], { type: mimeType })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.setAttribute('href', url)
    link.setAttribute('download', fullFilename)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
    setIsOpen(false)
  }

  const exportCSV = () => {
    if (!data.length) return
    const keys = Object.keys(data[0])
    const header = keys.join(',')
    const rows = data.map((row) =>
      keys
        .map((k) => {
          const val = row[k]
          if (val === null || val === undefined) return '""'
          if (typeof val === 'object') return `"${JSON.stringify(val).replace(/"/g, '""')}"`
          return `"${String(val).replace(/"/g, '""')}"`
        })
        .join(','),
    )

    const csvContent = [header, ...rows].join('\n')
    downloadFile(csvContent, 'csv', 'csv')
  }

  const exportJSON = () => {
    if (!data.length) return
    const jsonContent = JSON.stringify(data, null, 2)
    downloadFile(jsonContent, 'json', 'json')
  }

  return (
    <div className="relative inline-block text-left">
      <button
        onClick={() => setIsOpen((prev) => !prev)}
        className="flex items-center gap-2 rounded-xl px-3 py-1.5 text-xs font-semibold text-ink-soft transition hover:bg-surface-2 hover:text-ink"
        style={{ border: '1px solid var(--border-strong)' }}
      >
        <Download size={13} aria-hidden />
        {label}
      </button>

      {isOpen && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setIsOpen(false)} />
          <div className="absolute right-0 z-20 mt-1.5 w-40 rounded-xl border border-edge bg-surface-1 p-1 shadow-lg ring-1 ring-black/5 backdrop-blur">
            <button
              onClick={exportCSV}
              className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-xs font-medium text-ink-soft transition hover:bg-surface-2 hover:text-ink"
            >
              <FileSpreadsheet size={14} className="text-good" />
              Export CSV
            </button>
            <button
              onClick={exportJSON}
              className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-xs font-medium text-ink-soft transition hover:bg-surface-2 hover:text-ink"
            >
              <FileJson size={14} className="text-[#2969C4]" />
              Export JSON
            </button>
          </div>
        </>
      )}
    </div>
  )
}
