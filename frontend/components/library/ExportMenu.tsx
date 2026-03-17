'use client'

import { useState, useRef, useEffect } from 'react'
import { FileDown, Presentation, ChevronDown, FileText, Check, Loader2 } from 'lucide-react'
import type { LibraryBrief } from '@/lib/hooks/useLibrary'
import { exportBrief } from '@/lib/api/exports'

interface ExportMenuProps {
  brief: LibraryBrief
  className?: string
}

type ExportFormat = 'pdf' | 'pptx' | 'markdown' | 'docx'

const FORMATS: { id: ExportFormat; label: string; desc: string; icon: React.ReactNode }[] = [
  {
    id: 'pdf',
    label: 'Export PDF',
    desc: 'Print-optimised, ready for sharing',
    icon: <FileDown className="h-4 w-4" />,
  },
  {
    id: 'pptx',
    label: 'Export PPTX',
    desc: 'PowerPoint / Google Slides',
    icon: <Presentation className="h-4 w-4" />,
  },
  {
    id: 'docx',
    label: 'Export Word',
    desc: 'Editable .docx document',
    icon: <FileText className="h-4 w-4" />,
  },
  {
    id: 'markdown',
    label: 'Copy Markdown',
    desc: 'Plain text, Markdown formatted',
    icon: <FileText className="h-4 w-4" />,
  },
]

export function ExportMenu({ brief, className = '' }: ExportMenuProps) {
  const [open,      setOpen]      = useState(false)
  const [exported,  setExported]  = useState<ExportFormat | null>(null)
  const [exporting, setExporting] = useState<ExportFormat | null>(null)
  const menuRef = useRef<HTMLDivElement>(null)

  // Close on click outside
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    if (open) document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  const handleExport = async (format: ExportFormat) => {
    if (exporting) return

    if (format === 'markdown') {
      const md = [
        `# ${brief.title}`,
        brief.subtitle ? `\n_${brief.subtitle}_\n` : '',
        `**Domain:** ${brief.domain}  `,
        `**Date:** ${brief.relativeDate}  `,
        `**Confidence:** ${brief.confidence}%  `,
        `**Author:** ${brief.author}\n`,
        `---\n`,
        `## Summary\n${brief.summary}\n`,
        ...brief.sections.map(s => `## ${s.heading}\n\n${s.content}\n`),
      ].join('\n')
      navigator.clipboard.writeText(md).catch(() => {})
      setExported('markdown')
      setTimeout(() => { setExported(null); setOpen(false) }, 1400)
      return
    }

    // Map UI format names to API format values
    const apiFormat = format === 'pdf' ? 'pdf-html' : format

    setExporting(format)
    try {
      await exportBrief({
        title:      brief.title,
        subtitle:   brief.subtitle,
        domain:     brief.domain,
        author:     brief.author,
        confidence: brief.confidence,
        sections:   brief.sections,
        format:     apiFormat as 'pdf-html' | 'pptx' | 'docx',
      })
      setExported(format)
      setTimeout(() => { setExported(null); setOpen(false) }, 1400)
    } catch (err) {
      console.error('Export failed:', err)
    } finally {
      setExporting(null)
    }
  }

  return (
    <div ref={menuRef} className={`relative ${className}`}>
      <button
        onClick={() => setOpen(v => !v)}
        className="flex items-center gap-1.5 rounded-lg border border-border bg-surface px-3 py-1.5 text-xs font-medium text-body shadow-sm transition-colors hover:bg-muted"
        aria-haspopup="true"
        aria-expanded={open}
      >
        <FileDown className="h-3.5 w-3.5" />
        Export
        <ChevronDown className={`h-3 w-3 text-subtle transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <div
          className="absolute right-0 top-full z-50 mt-1.5 w-52 overflow-hidden rounded-xl border border-border bg-surface shadow-modal"
          role="menu"
        >
          <div className="p-1">
            {FORMATS.map(fmt => {
              const done = exported === fmt.id
              return (
                <button
                  key={fmt.id}
                  role="menuitem"
                  onClick={() => handleExport(fmt.id)}
                  disabled={!!exporting}
                  className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left transition-colors hover:bg-muted disabled:opacity-50"
                >
                  <span className={`flex-shrink-0 ${done ? 'text-success' : 'text-subtle'}`}>
                    {exporting === fmt.id
                      ? <Loader2 className="h-4 w-4 animate-spin" />
                      : done
                      ? <Check className="h-4 w-4" />
                      : fmt.icon
                    }
                  </span>
                  <div>
                    <p className={`text-xs font-medium ${done ? 'text-success' : 'text-heading'}`}>
                      {exporting === fmt.id
                        ? 'Generating…'
                        : done
                        ? (fmt.id === 'markdown' ? 'Copied!' : 'Exported!')
                        : fmt.label
                      }
                    </p>
                    {!done && !exporting && <p className="text-[10px] text-subtle">{fmt.desc}</p>}
                  </div>
                </button>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
