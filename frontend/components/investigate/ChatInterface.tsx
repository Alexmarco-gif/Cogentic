'use client'

import { useEffect, useRef } from 'react'
import { Sparkles, Square, Trash2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { LiveIndicator, ScrollArea } from '@/components/ui'
import { MessageBubble } from './MessageBubble'
import { ChatInput } from './ChatInput'
import type { Message } from '@/lib/hooks/useInvestigate'

interface ChatInterfaceProps {
  messages: Message[]
  isProcessing: boolean
  sessionTitle?: string | null
  onSend: (text: string) => void
  onStop: () => void
  onClear: () => void
  onSuggestionClick: (text: string) => void
}

const STARTER_SUGGESTIONS = [
  "What's driving price pressure on the top entity?",
  'Analyze the latest regulatory policy changes',
]

export function ChatInterface({
  messages,
  isProcessing,
  sessionTitle,
  onSend,
  onStop,
  onClear,
  onSuggestionClick,
}: ChatInterfaceProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <div className="flex h-full flex-col bg-surface">
      <div className="flex items-start justify-between gap-3 px-5 py-3.5 shrink-0">
        <div className="flex min-w-0 items-start gap-2.5">
          <div className="mt-0.5 flex h-7 w-7 items-center justify-center rounded-lg bg-primary/10">
            <Sparkles size={13} className="text-primary" />
          </div>
          <div className="min-w-0">
            <p className="text-[13px] font-medium text-heading">War Room</p>
            <p className="truncate text-[10px] text-subtle">
              {sessionTitle || 'Deep-dive intelligence analysis'}
            </p>
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          <LiveIndicator label={isProcessing ? 'Streaming' : 'Ready'} />
          {isProcessing && (
            <button
              onClick={onStop}
              className="inline-flex items-center gap-1 rounded-lg border border-border px-2 py-1 text-[10px] font-medium text-body transition-colors hover:border-primary/20 hover:bg-muted"
              title="Stop current investigation"
            >
              <Square size={10} />
              Stop
            </button>
          )}
          {messages.length > 0 && (
            <button
              onClick={onClear}
              className="rounded-lg p-1.5 text-subtle transition-colors hover:bg-muted hover:text-body"
              title="Clear conversation"
            >
              <Trash2 size={13} />
            </button>
          )}
        </div>
      </div>

      <ScrollArea className="flex-1 overflow-y-auto border-t border-border">
        <div className="space-y-3 px-4 py-4">
          {messages.length === 0 ? (
            <EmptyState onSuggestionClick={onSuggestionClick} />
          ) : (
            <>
              {messages.map((message) => (
                <MessageBubble key={message.id} message={message} />
              ))}
              {isProcessing && (
                <div className="flex justify-start">
                  <div className="rounded-2xl rounded-tl-sm border border-border bg-surface px-4 py-3 shadow-sm">
                    <div className="flex items-center gap-1.5">
                      {[0, 1, 2].map((index) => (
                        <span
                          key={index}
                          className="h-1.5 w-1.5 animate-bounce rounded-full bg-border"
                          style={{ animationDelay: `${index * 150}ms` }}
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

      <ChatInput
        onSend={onSend}
        onClear={onClear}
        isDisabled={isProcessing}
        hasMessages={messages.length > 0}
      />
    </div>
  )
}

function EmptyState({ onSuggestionClick }: { onSuggestionClick: (text: string) => void }) {
  return (
    <div className="flex flex-col items-center justify-center gap-4 py-10">
      <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-primary/10 bg-primary/5">
        <Sparkles size={20} className="text-primary" />
      </div>
      <div className="text-center">
        <p className="mb-1 text-[14px] font-medium text-heading">Cogent Intelligence</p>
        <p className="max-w-[220px] text-[12px] leading-relaxed text-subtle">
          Ask anything about your monitored entities, risks, markets, or policy events.
        </p>
      </div>
      <div className="mt-1 w-full space-y-1.5">
        {STARTER_SUGGESTIONS.map((suggestion) => (
          <button
            key={suggestion}
            onClick={() => onSuggestionClick(suggestion)}
            className={cn(
              'w-full rounded-lg border border-border bg-muted/50 px-3 py-2.5 text-left text-[12px] text-body transition-colors',
              'hover:border-primary/20 hover:bg-muted',
            )}
          >
            {suggestion}
          </button>
        ))}
      </div>
    </div>
  )
}
