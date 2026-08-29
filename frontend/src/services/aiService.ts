import { request } from './api'
import type { AIMessage } from '../types'

export interface AICitation {
  type: string
  reference_id: string
  label: string
  target_control?: string
  target_resource?: string
}

export interface DeterministicStateSnapshot {
  project_id: string
  project_name: string
  overall_status: string
  deployment_allowed: boolean
  compliance_score: number
  passed_count: number
  failed_count: number
  unknown_count: number
  evidence_hash: string
}

export interface AIChatResponsePayload {
  reply: string
  deterministic_state: DeterministicStateSnapshot
  citations: AICitation[]
  disclaimer: string
  llm_provider_used: string
  grounding_sources_used: string[]
}

export const aiService = {
  async chatWithCopilot(
    projectId: string,
    message: string,
    history: AIMessage[] = []
  ): Promise<AIChatResponsePayload | null> {
    const formattedHistory = history.map((h) => ({
      role: h.sender === 'user' ? 'user' : 'assistant',
      content: h.text,
    }))

    const res = await request<AIChatResponsePayload>('/ai/chat', {
      method: 'POST',
      body: JSON.stringify({
        project_id: projectId,
        message,
        conversation_history: formattedHistory,
      }),
    })

    if (res.data) {
      return res.data
    }

    // Client fallback if network offline
    return {
      reply: "I am unable to reach the RegulaCloud backend gateway. Please ensure the FastAPI server is running on port 8000.",
      deterministic_state: {
        project_id: projectId,
        project_name: "Project Context Unavailable",
        overall_status: "UNKNOWN",
        deployment_allowed: false,
        compliance_score: 0,
        passed_count: 0,
        failed_count: 0,
        unknown_count: 0,
        evidence_hash: "0000000000000000000000000000000000000000000000000000000000000000",
      },
      citations: [],
      disclaimer: "RegulaCloud provides technical compliance verification and explanation. It does not provide legal advice or legal certification.",
      llm_provider_used: "OFFLINE_CLIENT_FALLBACK",
      grounding_sources_used: [],
    }
  },

  async getRLRemediationRecommendations(activeViolations: string[]) {
    const res = await request<any>('/remediation/optimize', {
      method: 'POST',
      body: JSON.stringify({ active_violations: activeViolations }),
    })
    if (res.data) {
      return res.data
    }
    return null
  },
}
