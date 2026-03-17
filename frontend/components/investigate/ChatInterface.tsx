'use client'

import { useEffect, useRef } from 'react'
import { Sparkles, Trash2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { LiveIndicator, ScrollArea } from '@/components/ui'
import { MessageBubble } from './MessageBubble'
import { ChatInput }     from './ChatInput'
import type { Message }  from '@/lib/hooks/useInvestigate'

interface ChatInterfaceProps {
  messages: Message[]
  isProcessing: boolean
  onSend: (text: string) => void
  onClear: () => void
  onSuggestionClick: (text: string) => void
}

const STARTER_SUGGESTIONS = [
  "What's driving price pressure on the top entity?",
  "Analyze the latest regulatory policy changes",
]

export function ChatInterface({
  messages,
  isProcessing,
  onSend,
  onClear,
  onSuggestionClick,
}: ChatInterfaceProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <div className="flex flex-col h-full bg-surface border-r border-border">
      {/* ── Header ────────────────────────────────────── */}
      <div className="flex items-center justify-between px-5 py-3.5 border-b border-border shrink-0">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-primary/10 flex items-center justify-center">
            <Sparkles size={13} className="text-primary" />
          </div>
          <div>
            <p className="text-[13px] font-medium text-heading">War Room</p>
            <p className="text-[10px] text-subtle">Deep-dive intelligence analysis</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <LiveIndicator label="Live data" />
          {messages.length > 0 && (
            <button
              onClick={onClear}
              className="p-1.5 rounded-lg text-subtle hover:text-body hover:bg-muted transition-colors"
              title="Clear conversation"
            >
              <Trash2 size={13} />
            </button>
          )}
        </div>
      </div>

      {/* ── Messages ──────────────────────────────────── */}
      <ScrollArea className="flex-1 overflow-y-auto">
        <div className="px-4 py-4 space-y-3">
          {messages.length === 0 ? (
            <EmptyState onSuggestionClick={onSuggestionClick} />
          ) : (
            <>
              {messages.map(msg => (
                <MessageBubble key={msg.id} message={msg} />
              ))}
              {/* Processing indicator */}
              {isProcessing && (
                <div className="flex justify-start">
                  <div className="bg-surface border border-border rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm">
                    <div className="flex items-center gap-1.5">
                      {[0, 1, 2].map(i => (
                        <span
                          key={i}
                          className="w-1.5 h-1.5 rounded-full bg-border animate-bounce"
                          style={{ animationDelay: `${i * 150}ms` }}
                        />
                      ))}
                    </div>
                  </div>
                </div>
              )}
              <div ref={bottomRef} />
            </>
          )}
        </div>
      </ScrollArea>

      {/* ── Input ─────────────────────────────────────── */}
      <ChatInput
        onSend={onSend}
        onClear={onClear}
        isDisabled={isProcessing}
        hasMessages={messages.length > 0}
      />
    </div>
  )
}

// ── Empty state ───────────────────────────────────────────────────────────────
function EmptyState({ onSuggestionClick }: { onSuggestionClick: (t: string) => void }) {
  return (
    <div className="flex flex-col items-center justify-center py-10 gap-4">
      <div className="w-12 h-12 rounded-2xl bg-primary/5 border border-primary/10 flex items-center justify-center">
        <Sparkles size={20} className="text-primary" />
      </div>
      <div className="text-center">
        <p className="text-[14px] font-medium text-heading mb-1">Cogent Intelligence</p>
        <p className="text-[12px] text-subtle leading-relaxed max-w-[220px]">
          Ask anything about your strategic domains — entities, risks, market signals.
        </p>
      </div>
      <div className="w-full space-y-1.5 mt-1">
        {STARTER_SUGGESTIONS.map(s => (
          <button
            key={s}
            onClick={() => onSuggestionClick(s)}
            className={cn(
              'w-full text-left px-3 py-2.5 rounded-lg border border-border bg-muted/50',
              'hover:bg-muted hover:border-primary/20 transition-colors text-[12px] text-body',
            )}
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  )
}
