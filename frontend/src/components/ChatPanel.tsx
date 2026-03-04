import { useState, useCallback } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import type { HouseholdProfile, EvaluationResponse, EvaluationRequest } from '@/types/api'

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

interface ChatPanelProps {
  household: HouseholdProfile
  result: EvaluationResponse
  evalRequest: EvaluationRequest
}

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

const SUGGESTIONS = [
  'Why is savings rate my biggest driver?',
  'What if I retire at 65 instead?',
  'How does my savings compare to peers?',
]

export function ChatPanel({ household, result, evalRequest }: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [streamingText, setStreamingText] = useState('')
  const [statusText, setStatusText] = useState<string | null>(null)
  const sendMessage = useCallback(async (question: string) => {
    question = question.trim()
    if (!question || isStreaming) return

    const userMessage: ChatMessage = { role: 'user', content: question }
    const updatedMessages = [...messages, userMessage]
    setMessages(updatedMessages)
    setInput('')
    setIsStreaming(true)
    setStreamingText('')
    setStatusText(null)

    const payload = {
      household,
      messages: updatedMessages,
      context: {
        // Evaluation result
        success_probability: result.success_probability,
        success_label: result.success_label,
        top_drivers: result.top_drivers,
        // Retirement plan inputs — give the agent the full picture
        planned_retirement_age: evalRequest.planned_retirement_age,
        life_expectancy: evalRequest.life_expectancy,
        annual_spending_retirement: evalRequest.annual_spending_retirement,
        social_security_annual: evalRequest.social_security_annual,
        savings_rate: evalRequest.savings_rate,
        equity_fraction: evalRequest.equity_fraction,
      },
    }

    try {
      const response = await fetch(`${API_BASE}/api/v1/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })

      if (!response.ok || !response.body) {
        throw new Error(`Server error ${response.status}`)
      }

      // Read the SSE stream with fetch + ReadableStream.
      //
      // Why not native EventSource?  EventSource only supports GET requests and
      // can't send a JSON body.  The raw fetch approach requires manual SSE parsing
      // but works with POST and needs zero additional dependencies — and is a common
      // interview topic worth being able to explain.
      //
      // C# equivalent: await foreach (var chunk in response.Content.ReadFromJsonAsAsyncEnumerable<T>())
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let accumulated = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        // Decode the byte chunk into a string and append to the SSE buffer.
        // { stream: true } tells TextDecoder to handle multi-byte characters
        // that may be split across chunk boundaries.
        buffer += decoder.decode(value, { stream: true })

        // SSE events are delimited by double newlines: "data: {...}\n\n"
        // Split on the delimiter, keeping any incomplete trailing event in the buffer.
        const parts = buffer.split('\n\n')
        buffer = parts.pop() ?? ''

        for (const part of parts) {
          if (!part.startsWith('data: ')) continue
          const raw = part.slice(6).trim()
          if (!raw) continue

          let event: { type: string; text?: string }
          try { event = JSON.parse(raw) } catch { continue }

          if (event.type === 'status' && event.text) {
            setStatusText(event.text)
          } else if (event.type === 'token' && event.text) {
            accumulated += event.text
            setStreamingText(accumulated)
            setStatusText(null)   // Clear status once tokens start flowing
          } else if (event.type === 'done') {
            if (accumulated) {
              setMessages(prev => [...prev, { role: 'assistant', content: accumulated }])
            }
            setStreamingText('')
            setStatusText(null)
            setIsStreaming(false)
          }
        }
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Unknown error'
      setMessages(prev => [...prev, { role: 'assistant', content: `[Error: ${msg}]` }])
      setStreamingText('')
      setStatusText(null)
      setIsStreaming(false)
    }
  }, [isStreaming, messages, household, result])

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage(input)
    }
  }

  return (
    <Card className="flex flex-col h-full">
      <CardHeader className="pb-3">
        <CardTitle className="text-base font-semibold">Ask About Your Results</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col flex-1 min-h-0 gap-3 pb-4">

        {/* Message history — grows to fill available space; scrolls internally */}
        {(messages.length > 0 || isStreaming) && (
          <div className="space-y-3 flex-1 min-h-0 overflow-y-auto pr-1">
            {messages.map((msg, i) => (
              <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div
                  className={`max-w-[85%] rounded-lg px-3 py-2 text-sm whitespace-pre-wrap ${
                    msg.role === 'user'
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-muted text-foreground'
                  }`}
                >
                  {msg.content}
                </div>
              </div>
            ))}

            {/* In-progress assistant bubble */}
            {isStreaming && (
              <div className="flex justify-start">
                <div className="max-w-[85%] rounded-lg px-3 py-2 text-sm bg-muted text-foreground whitespace-pre-wrap">
                  {statusText && !streamingText && (
                    <span className="text-muted-foreground italic flex items-center gap-2">
                      {statusText}
                      <span className="inline-flex gap-1">
                        <span className="animate-bounce">·</span>
                        <span className="animate-bounce [animation-delay:0.15s]">·</span>
                        <span className="animate-bounce [animation-delay:0.3s]">·</span>
                      </span>
                    </span>
                  )}
                  {streamingText}
                  {!streamingText && !statusText && (
                    <span className="inline-flex gap-1 text-muted-foreground">
                      <span className="animate-bounce">·</span>
                      <span className="animate-bounce [animation-delay:0.15s]">·</span>
                      <span className="animate-bounce [animation-delay:0.3s]">·</span>
                    </span>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Suggested prompts — shown only before first message */}
        {messages.length === 0 && !isStreaming && (
          <div className="flex flex-wrap gap-2">
            {SUGGESTIONS.map(s => (
              <button
                key={s}
                type="button"
                onClick={() => sendMessage(s)}
                className="text-xs px-3 py-1.5 rounded-full border border-border bg-background hover:bg-muted transition-colors text-muted-foreground"
              >
                {s}
              </button>
            ))}
          </div>
        )}

        {/* Input row */}
        <div className="flex gap-2">
          <Input
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about your results..."
            disabled={isStreaming}
            className="flex-1"
          />
          <Button
            type="button"
            onClick={() => sendMessage(input)}
            disabled={isStreaming || !input.trim()}
            size="sm"
          >
            {isStreaming ? '···' : 'Send'}
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
