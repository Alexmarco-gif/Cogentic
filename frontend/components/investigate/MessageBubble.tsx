'use client'

import { cn } from '@/lib/utils'
import { StreamingText } from '@/components/ui'
import type { Message } from '@/lib/hooks/useInvestigate'

interface MessageBubbleProps {
  message: Message
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user'

  return (
    <div className={cn('flex w-full', isUser ? 'justify-end' : 'justify-start')}>
      <div
        className={cn(
          'max-w-[85%] rounded-2xl px-4 py-3',
          isUser
            ? 'bg-primary text-white rounded-tr-sm'
            : 'bg-surface border border-border text-body rounded-tl-sm shadow-sm',
        )}
      >
        {isUser ? (
          <p className="text-[13px] leading-relaxed whitespace-pre-wrap">{message.content}</p>
        ) : (
          <AiMessageContent message={message} />
        )}
        <p
          className={cn(
            'text-[10px] mt-1.5 leading-none',
            isUser ? 'text-white/50 text-right' : 'text-subtle',
          )}
        >
          {message.timestamp.toLocaleTimeString('en-GB', {
            hour: '2-digit',
            minute: '2-digit',
          })}
        </p>
      </div>
    </div>
  )
}

// ── AI message content ────────────────────────────────────────────────────────
// Renders simple markdown: **bold**, [n] citation refs, bullet points

function AiMessageContent({ message }: { message: Message }) {
  if (message.isStreaming) {
    return (
      <div className="text-[13px] leading-relaxed text-body">
        {/* speed=12 chars/tick at 20ms → ~3,000 chars in ~5s for long briefs */}
        <StreamingText text={message.content} speed={12} interval={20} />
      </div>
    )
  }
  return <MarkdownContent content={message.content} />
}

// Lightweight markdown renderer — supports:
//   ### Section Header
//   > callout / status block
//   ---  horizontal divider
//   **bold** (standalone line = section label)
//   - bullets
//   1. numbered list
//   inline **bold** and [n] citation refs
function MarkdownContent({ content }: { content: string }) {
  const lines = content.split('\n')

  return (
    <div className="text-[13px] leading-relaxed text-body space-y-1">
      {lines.map((line, i) => {
        // ── Empty line → small gap ──────────────────
        if (!line.trim()) return <div key={i} className="h-2" />

        // ── Horizontal rule ─────────────────────────
        if (line.trim() === '---') {
          return <hr key={i} className="border-border my-2" />
        }

        // ── ### Section header ───────────────────────
        if (line.startsWith('### ')) {
          return (
            <div key={i} className="flex items-center gap-2 pt-3 pb-1">
              <span className="text-[10px] font-bold tracking-widest uppercase text-subtle">
                {line.slice(4)}
              </span>
              <div className="flex-1 h-px bg-border" />
            </div>
          )
        }

        // ── > callout block ──────────────────────────
        if (line.startsWith('> ')) {
          return (
            <div key={i} className="bg-primary/5 border-l-2 border-primary/40 rounded-r-lg px-3 py-2 my-1">
              <span className="text-[12px] text-body">{renderInline(line.slice(2))}</span>
            </div>
          )
        }

        // ── Standalone **heading** line ──────────────
        if (line.startsWith('**') && line.endsWith('**') && !line.slice(2, -2).includes('**')) {
          return (
            <p key={i} className="font-medium text-heading text-[13px] pt-1.5 pb-0.5 leading-snug">
              {line.slice(2, -2)}
            </p>
          )
        }

        // ── Bullet point ─────────────────────────────
        if (line.startsWith('- ')) {
          return (
            <div key={i} className="flex gap-2 items-start pl-1">
              <span className="text-primary/60 mt-[5px] shrink-0 text-[8px]">◆</span>
              <span className="text-[13px] leading-relaxed">{renderInline(line.slice(2))}</span>
            </div>
          )
        }

        // ── Numbered list ─────────────────────────────
        if (/^\d+\. /.test(line)) {
          const num  = line.match(/^(\d+)\./)?.[1] ?? ''
          const rest = line.replace(/^\d+\. /, '')
          return (
            <div key={i} className="flex gap-2.5 items-start pl-1">
              <span className="w-4 h-4 rounded-full bg-primary/10 text-primary text-[9px] font-bold flex items-center justify-center shrink-0 mt-0.5">
                {num}
              </span>
              <span className="text-[13px] leading-relaxed flex-1">{renderInline(rest)}</span>
            </div>
          )
        }

        return <p key={i} className="leading-relaxed">{renderInline(line)}</p>
      })}
    </div>
  )
}

// Render inline **bold** and [n] citations
function renderInline(text: string): React.ReactNode {
  // Split on **bold** and [n] patterns
  const parts = text.split(/(\*\*[^*]+\*\*|\[\d+\])/g)
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={i} className="font-medium text-heading">{part.slice(2, -2)}</strong>
    }
    if (/^\[\d+\]$/.test(part)) {
      return (
        <sup key={i}>
          <span className="text-[9px] font-semibold text-primary bg-primary/10 rounded px-0.5 mx-0.5 cursor-default">
            {part}
          </span>
        </sup>
      )
    }
    return <span key={i}>{part}</span>
  })
}
