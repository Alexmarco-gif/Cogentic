'use client'

import { useRef, useState, useEffect, useCallback } from 'react'
import { ArrowUp, RotateCcw } from 'lucide-react'
import { cn } from '@/lib/utils'

interface ChatInputProps {
  onSend: (text: string) => void
  onClear?: () => void
  isDisabled?: boolean
  placeholder?: string
  hasMessages?: boolean
}

export function ChatInput({
  onSend,
  onClear,
  isDisabled = false,
  placeholder = 'Ask about market trends, entities, policy events…',
  hasMessages = false,
}: ChatInputProps) {
  const [value, setValue] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`
  }, [value])

  const handleSend = useCallback(() => {
    const trimmed = value.trim()
    if (!trimmed || isDisabled) return
    onSend(trimmed)
    setValue('')
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }, [value, isDisabled, onSend])

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const charCount = value.length
  const isOverLimit = charCount > 800

  return (
    <div className="border-t border-border bg-surface px-4 py-3 shrink-0">
      {/* Textarea wrapper */}
      <div
        className={cn(
          'flex items-end gap-2 rounded-xl border bg-muted/50 px-3 py-2.5 transition-colors',
          isOverLimit ? 'border-critical/50' : 'border-border focus-within:border-primary/40 focus-within:bg-surface',
        )}
      >
        <textarea
          ref={textareaRef}
          value={value}
          onChange={e => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isDisabled}
          placeholder={placeholder}
          rows={1}
          className={cn(
            'flex-1 resize-none bg-transparent text-[13px] text-body placeholder:text-subtle',
            'outline-none leading-relaxed min-h-[22px]',
            'disabled:opacity-50 disabled:cursor-not-allowed',
          )}
          aria-label="Chat message"
        />

        {/* Send button */}
        <button
          onClick={handleSend}
          disabled={isDisabled || !value.trim() || isOverLimit}
          className={cn(
            'w-7 h-7 rounded-lg flex items-center justify-center shrink-0 transition-all',
            value.trim() && !isDisabled && !isOverLimit
              ? 'bg-primary text-white hover:bg-primary/90 shadow-sm'
              : 'bg-muted text-subtle cursor-not-allowed',
          )}
          title="Send (Enter)"
        >
          {isDisabled
            ? <span className="w-3 h-3 rounded-full border-2 border-white/40 border-t-white animate-spin" />
            : <ArrowUp size={13} strokeWidth={2.5} />
          }
        </button>
      </div>

      {/* Footer row */}
      <div className="flex items-center justify-between mt-1.5 px-0.5">
        <div className="flex items-center gap-3">
          <span className="text-[10px] text-subtle">Stem Cogent can make mistake. Verify Info</span>
          {hasMessages && onClear && (
            <button
              onClick={onClear}
              className="text-[10px] text-subtle hover:text-body flex items-center gap-1 transition-colors"
            >
              <RotateCcw size={9} />
              Clear
            </button>
          )}
        </div>
        <span className={cn('text-[10px] tabular-nums', isOverLimit ? 'text-critical' : 'text-subtle')}>
          {charCount > 600 ? `${charCount}/800` : ''}
        </span>
      </div>
    </div>
  )
}
