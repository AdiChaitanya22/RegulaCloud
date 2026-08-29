import { useState, useRef, useEffect } from 'react'
import {
  Send,
  Sparkles,
  User,
  ShieldAlert,
  ShieldCheck,
  Info,
  ChevronDown,
  ChevronUp,
  FileCheck,
  Cpu,
  Layers,
  RotateCcw,
  ExternalLink,
  BookOpen
} from 'lucide-react'
import { Card } from '../components/ui/card'
import { Badge } from '../components/ui/badge'
import { aiService } from '../services/aiService'
import type { AIChatResponsePayload, AICitation } from '../services/aiService'

interface ChatMessage {
  sender: 'user' | 'ai'
  text: string
  deterministicState?: any
  citations?: AICitation[]
  provider?: string
  disclaimer?: string
}

const regulatorPrompts = [
  { text: 'Why is this deployment blocked?', prompt: 'Why is this application\'s deployment blocked?' },
  { text: 'Which regulations apply?', prompt: 'Which regulations apply to this project?' },
  { text: 'Which technical controls failed?', prompt: 'Which technical controls failed?' },
  { text: 'What evidence caused the failure?', prompt: 'What evidence caused the failure?' },
  { text: 'What remediation is recommended?', prompt: 'What remediation is recommended?' },
  { text: 'Can you approve this deployment?', prompt: 'Can you approve this deployment?' },
]

export function AIAssistantPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      sender: 'ai',
      text: 'Welcome to the RegulaCloud Regulatory AI Copilot.\n\nI provide explainable, grounded analysis of your statutory cloud compliance status under DPDPA 2023 and CERT-In 2022. I can explain why deployments are blocked, inspect empirical OPA/Sonar evidence, and provide Q-learning remediation roadmaps.',
      provider: 'REGULATORY_KNOWLEDGE_BASE (Grounded Mode)',
      disclaimer: 'RegulaCloud provides technical compliance verification and explanation. It does not provide legal advice or legal certification.'
    }
  ])
  const [inputText, setInputText] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const [expandedSections, setExpandedSections] = useState<Record<number, boolean>>({})
  const chatEndRef = useRef<HTMLDivElement | null>(null)

  const activeProjectId = 'proj-healthcare-india'

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isTyping])

  const toggleSection = (idx: number) => {
    setExpandedSections((prev) => ({ ...prev, [idx]: !prev[idx] }))
  }

  const handleSend = async (text: string) => {
    if (!text.trim() || isTyping) return

    // 1. Append User Message
    const userMsg: ChatMessage = { sender: 'user', text }
    setMessages((prev) => [...prev, userMsg])
    setInputText('')
    setIsTyping(true)

    try {
      // 2. Call FastAPI RAG Endpoint
      const historyForApi = messages.map((m) => ({
        sender: m.sender,
        text: m.text,
      }))
      const res = await aiService.chatWithCopilot(activeProjectId, text, historyForApi as any)

      if (res) {
        const aiMsg: ChatMessage = {
          sender: 'ai',
          text: res.reply,
          deterministicState: res.deterministic_state,
          citations: res.citations,
          provider: res.llm_provider_used,
          disclaimer: res.disclaimer,
        }
        setMessages((prev) => [...prev, aiMsg])
      }
    } catch (e) {
      console.error('Chat error', e)
    } finally {
      setIsTyping(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Legal Disclaimer Top Banner */}
      <div className="rounded-2xl border border-amber-500/25 bg-amber-500/10 p-4 backdrop-blur-md">
        <div className="flex items-start gap-3">
          <Info className="text-amber-400 shrink-0 mt-0.5" size={18} />
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-amber-400">
              Authoritative Gating & Legal Disclaimer
            </h4>
            <p className="mt-1 text-xs text-slate-300 leading-relaxed">
              The AI Copilot is strictly an explanatory tool grounded in real OPA/Sonar evidence. It has <strong className="text-white">NO</strong> authority to approve deployments or alter compliance outcomes. The deterministic compliance engine remains the sole authority.
            </p>
          </div>
        </div>
      </div>

      {/* Header */}
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs uppercase tracking-widest font-bold text-primary">Regulator & Architect Copilot</span>
            <span className="rounded-md bg-emerald-500/15 border border-emerald-500/30 px-2 py-0.5 text-[10px] font-bold text-emerald-600">
              GROUNDED RAG ACTIVE
            </span>
          </div>
          <h1 className="text-3xl font-semibold tracking-[-0.04em] text-white">Grounded Regulatory Assistant</h1>
        </div>

        {/* Project Target Badge */}
        <div className="rounded-xl border border-[#1C2633] bg-[#111720] px-4 py-2 text-xs">
          <span className="text-slate-400">Active Grounding Target: </span>
          <strong className="text-white font-mono">Ayushman Digital Health Registry</strong>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.6fr_0.8fr]">
        {/* Chat Window */}
        <Card className="flex flex-col h-[650px] overflow-hidden border border-[#1C2633] bg-[#0B0F14] rounded-3xl">
          <div className="border-b border-[#1C2633]/60 bg-[#111720]/40 px-5 py-4 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="flex h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
              <span className="text-xs uppercase tracking-[0.18em] text-slate-400 font-bold">Evidence-Grounded Copilot</span>
            </div>
            <span className="text-[10px] text-slate-500 font-mono">Zero AI Authority Over Deployment Gates</span>
          </div>

          <div className="flex-1 overflow-y-auto p-5 space-y-5">
            {messages.map((msg, idx) => (
              <div
                key={idx}
                className={`flex gap-3 max-w-[90%] ${
                  msg.sender === 'user' ? 'ml-auto flex-row-reverse' : 'mr-auto'
                }`}
              >
                <div
                  className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-semibold ${
                    msg.sender === 'user'
                      ? 'bg-primary text-white'
                      : 'bg-primary/20 text-primary border border-primary/30'
                  }`}
                >
                  {msg.sender === 'user' ? <User size={14} /> : <Sparkles size={14} />}
                </div>

                <div className="space-y-3 w-full">
                  <div
                    className={`rounded-2xl p-4 text-sm leading-relaxed whitespace-pre-line ${
                      msg.sender === 'user'
                        ? 'bg-primary text-white ml-auto'
                        : 'bg-[#111720] border border-[#1C2633] text-slate-200'
                    }`}
                  >
                    {msg.text}
                  </div>

                  {/* AI Message Detailed Breakdown & Expandable Citations */}
                  {msg.sender === 'ai' && (msg.citations?.length || msg.deterministicState) && (
                    <div className="rounded-xl border border-[#1C2633] bg-[#06090D] p-3 text-xs space-y-2">
                      {/* State Pills */}
                      {msg.deterministicState && (
                        <div className="flex flex-wrap items-center gap-2 border-b border-[#1C2633] pb-2">
                          <span className="text-[10px] uppercase font-bold text-slate-500">Deterministic State:</span>
                          <span
                            className={`rounded px-2 py-0.5 text-[9px] font-bold ${
                              msg.deterministicState.overall_status === 'PASS'
                                ? 'bg-emerald-500/15 text-emerald-600 border border-emerald-500/30'
                                : 'bg-rose-500/15 text-rose-400 border border-rose-500/30'
                            }`}
                          >
                            {msg.deterministicState.overall_status} ({msg.deterministicState.compliance_score}%)
                          </span>
                          <span
                            className={`rounded px-2 py-0.5 text-[9px] font-bold ${
                              msg.deterministicState.deployment_allowed
                                ? 'bg-emerald-500/15 text-emerald-600'
                                : 'bg-rose-500/20 text-rose-300'
                            }`}
                          >
                            {msg.deterministicState.deployment_allowed ? 'DEPLOYMENT UNBLOCKED' : 'DEPLOYMENT BLOCKED'}
                          </span>
                        </div>
                      )}

                      {/* Expandable Citations Drawer */}
                      {msg.citations && msg.citations.length > 0 && (
                        <div>
                          <button
                            onClick={() => toggleSection(idx)}
                            className="flex items-center justify-between w-full text-slate-400 hover:text-white py-1 transition text-[11px] font-semibold"
                          >
                            <span className="flex items-center gap-1.5 text-primary">
                              <BookOpen size={13} />
                              Regulatory & Evidence Citations ({msg.citations.length})
                            </span>
                            {expandedSections[idx] ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                          </button>

                          {expandedSections[idx] && (
                            <div className="mt-2 space-y-1.5 pt-2 border-t border-[#1C2633]">
                              {msg.citations.map((c, cIdx) => (
                                <div
                                  key={cIdx}
                                  className="flex items-center justify-between p-2 rounded-lg bg-[#111720] border border-[#1C2633] text-[10px]"
                                >
                                  <div className="flex items-center gap-2">
                                    <span className="rounded bg-primary/20 text-primary px-1.5 py-0.2 font-mono font-bold">
                                      {c.type}
                                    </span>
                                    <span className="text-slate-300 font-medium">{c.label}</span>
                                  </div>
                                  <a
                                    href="/compliance"
                                    className="text-primary hover:underline flex items-center gap-1 shrink-0 font-bold"
                                  >
                                    View Traceability <ExternalLink size={10} />
                                  </a>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      )}

                      {/* Disclaimer footer */}
                      <div className="text-[9px] text-slate-500 italic pt-1">
                        {msg.disclaimer || 'RegulaCloud technical compliance verification.'}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}

            {isTyping && (
              <div className="flex gap-3 mr-auto max-w-[80%]">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/20 text-primary border border-primary/30">
                  <Sparkles size={14} />
                </div>
                <div className="rounded-2xl bg-[#111720] border border-[#1C2633] p-4 text-sm text-slate-400 flex items-center gap-1.5">
                  <span className="text-xs text-primary font-mono mr-2">Retrieving Knowledge Base & OPA Evidence...</span>
                  <div className="h-2 w-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <div className="h-2 w-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <div className="h-2 w-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          {/* Input form */}
          <form
            onSubmit={(e) => {
              e.preventDefault()
              handleSend(inputText)
            }}
            className="border-t border-[#1C2633]/60 bg-[#111720]/20 p-4 flex gap-3"
          >
            <input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="Ask why deployment is blocked, which laws apply, or what remediation is needed..."
              className="flex-1 rounded-xl border border-[#1C2633] bg-[#111720] px-4 py-3 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-primary"
            />
            <button
              type="submit"
              disabled={isTyping || !inputText.trim()}
              className="inline-flex h-11 w-11 items-center justify-center rounded-xl bg-primary text-white hover:bg-blue-600 transition disabled:opacity-40"
            >
              <Send size={16} />
            </button>
          </form>
        </Card>

        {/* Quick Regulator Actions sidebar */}
        <div className="space-y-4">
          <Card className="p-5 border border-[#1C2633] bg-[#0B0F14]">
            <h3 className="mb-3 text-xs uppercase tracking-[0.18em] text-slate-400 font-bold">
              Regulator Audit Prompts
            </h3>
            <div className="space-y-2">
              {regulatorPrompts.map((item) => (
                <button
                  key={item.text}
                  onClick={() => handleSend(item.prompt)}
                  disabled={isTyping}
                  className="block w-full rounded-xl border border-[#1C2633] bg-[#111720] px-3.5 py-2.5 text-left text-xs text-slate-300 hover:bg-[#1C2633] hover:text-white transition disabled:opacity-50"
                >
                  {item.text}
                </button>
              ))}
            </div>
          </Card>

          <Card className="p-5 border border-[#1C2633] bg-[#0B0F14] text-xs space-y-3">
            <div className="flex items-center gap-2 text-primary font-bold">
              <Layers size={16} />
              <span>Grounding Sources Active</span>
            </div>
            <ul className="space-y-1.5 text-slate-400 list-disc list-inside">
              <li><strong className="text-slate-300">India DPDPA 2023</strong> (Gazette Act 22)</li>
              <li><strong className="text-slate-300">DPDP Rules 2025</strong> (Data Governance)</li>
              <li><strong className="text-slate-300">CERT-In 2022 Directions</strong> (Sec 70B)</li>
              <li><strong className="text-slate-300">Live OPA Rego Evaluation</strong> (Plan JSON)</li>
              <li><strong className="text-slate-300">Q-Learning Remediation Agent</strong></li>
            </ul>
          </Card>
        </div>
      </div>
    </div>
  )
}
