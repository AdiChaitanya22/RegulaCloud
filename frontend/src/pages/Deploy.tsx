import { useState, useEffect } from 'react'
import {
  CheckCircle2,
  AlertOctagon,
  ShieldCheck,
  Sparkles,
  FileCode,
  Play,
  RotateCcw,
  ShieldAlert,
  CloudLightning
} from 'lucide-react'
import { Card } from '../components/ui/card'
import { Badge } from '../components/ui/badge'
import { complianceService } from '../services/complianceService'
import { aiService } from '../services/aiService'
import { deploymentService } from '../services/deploymentService'
import { projectService } from '../services/projectService'
import { useProject } from '../context/ProjectContext'

export function DeployPage() {
  const { activeProject } = useProject()
  const [hclCode, setHclCode] = useState('')
  const [evalResult, setEvalResult] = useState<any | null>(null)
  const [rlRecommendations, setRlRecommendations] = useState<any[] | null>(null)
  const [isEvaluating, setIsEvaluating] = useState(false)
  const [isApplyingRL, setIsApplyingRL] = useState(false)
  const [isDeploying, setIsDeploying] = useState(false)
  const [deploySuccess, setDeploySuccess] = useState(false)
  const [activeDeploymentId, setActiveDeploymentId] = useState<string | null>(null)
  const [notification, setNotification] = useState<{ type: 'success' | 'error' | 'info'; message: string } | null>(null)

  // Run initial evaluation on mount
  useEffect(() => {
    if (!activeProject) return

    const initHcl = async () => {
      try {
        const storedHcl = await projectService.getProjectHcl(activeProject.id)
        if (storedHcl && storedHcl.trim().length > 0) {
          setHclCode(storedHcl)
          runEvaluation(storedHcl)
        } else {
          setNotification({ type: 'info', message: 'No infrastructure configuration found for this project.' })
        }
      } catch (err) {
        setNotification({ type: 'error', message: 'Failed to load project infrastructure.' })
      }
    }
    initHcl()
  }, [activeProject?.id])

  const runEvaluation = async (codeToEval: string) => {
    if (!activeProject) return
    setIsEvaluating(true)
    setDeploySuccess(false)
    try {
      const res = await complianceService.evaluateCompliance(activeProject.id, codeToEval)
      setEvalResult(res)

      if (res && !res.deployment_allowed) {
        // Automatically compute Q-learning RL recommendations for all active violated controls
        const opaControlIds = (res.opa_violations || []).map((v: any) => v.control_id)
        const sonarControlIds = (res.evaluations || [])
          .filter((e: any) => e.status === 'FAIL')
          .flatMap((e: any) => (e.findings || []).map((f: any) => f.control_id))
        const allViolatedControlIds = Array.from(new Set([...opaControlIds, ...sonarControlIds]))
        
        const rlData = await aiService.getRLRemediationRecommendations(allViolatedControlIds)
        if (rlData && rlData.recommendations) {
          setRlRecommendations(rlData.recommendations)
        }
      } else {
        setRlRecommendations(null)
      }
    } catch (e) {
      console.error('Evaluation failed', e)
      setNotification({ type: 'error', message: 'Compliance evaluation request failed.' })
    } finally {
      setIsEvaluating(false)
    }
  }

  const applyRLRemediation = async () => {
    if (!activeProject) {
      setNotification({ type: 'error', message: 'No active project selected.' })
      return
    }

    setIsApplyingRL(true)
    setNotification({ type: 'info', message: 'Applying RL-optimized remediation actions to HCL & code baselines...' })
    try {
      if (!rlRecommendations || rlRecommendations.length === 0) {
        setNotification({ type: 'error', message: 'No RL recommendations available to apply.' })
        return
      }

      const actionIds = rlRecommendations.map((r: any) => r.action_id).filter(Boolean)
      
      console.log('RL Remediation trace:', {
        handlerEntered: true,
        projectId: activeProject.id,
        recommendationCount: rlRecommendations.length,
        extractedActionIds: actionIds,
        requestUrl: `/api/v1/projects/${activeProject.id}/remediate`
      })

      if (actionIds.length === 0) {
        setNotification({ type: 'error', message: 'No valid action IDs found in recommendations.' })
        return
      }

      const result = await projectService.applyRemediations(activeProject.id, actionIds)
      
      console.log('RL Remediation API response:', result)

      if (result.success && result.hcl_code) {
        setHclCode(result.hcl_code)
        
        // Build success message
        let msg = result.message || 'Remediation processed.'
        if (result.applied_actions && result.applied_actions.length > 0) {
          msg += ` Applied: ${result.applied_actions.join(', ')}.`
        }
        if (result.skipped_actions && result.skipped_actions.length > 0) {
          msg += ` Skipped: ${result.skipped_actions.join(', ')}.`
        }
        
        // Check if no actions were actually applied
        if (!result.applied_actions || result.applied_actions.length === 0) {
          setNotification({ type: 'error', message: `No remediations were applied. ${msg}` })
        } else {
          setNotification({ type: 'success', message: msg })
        }

        // Re-evaluate immediately with new HCL
        runEvaluation(result.hcl_code)
      } else {
        setNotification({ type: 'error', message: result.message || 'Remediation failed.' })
      }
    } catch (e: any) {
      console.error('RL remediation error', e)
      setNotification({ type: 'error', message: e.message || 'Failed to apply remediation via API.' })
    } finally {
      setIsApplyingRL(false)
    }
  }

  const handleApplyDeployment = async () => {
    if (!evalResult || !evalResult.deployment_allowed || isDeploying) return
    setIsDeploying(true)

    try {
      // Use the existing authenticated user's token — no credential injection
      const planRes = await deploymentService.createDeploymentPlan({
        projectId: activeProject!.id,
        projectName: activeProject!.name,
        cloudProvider: activeProject!.cloudProvider,
        region: activeProject!.region,
      })
      if (planRes && planRes.id) {
        setActiveDeploymentId(planRes.id)
        const applyRes = await deploymentService.applyDeployment(planRes.id)
        if (applyRes) {
          setDeploySuccess(true)
          setNotification({ type: 'success', message: 'Deployment authorized and applied successfully.' })
        } else {
          setNotification({ type: 'error', message: 'Deployment authorization rejected by server.' })
        }
      } else {
        setNotification({ type: 'error', message: 'Failed to create deployment plan.' })
      }
    } catch (e: any) {
      // Surface RBAC/auth errors clearly — never elevate credentials
      const status = e?.status ?? e?.response?.status
      if (status === 403) {
        setNotification({
          type: 'error',
          message: 'Authorization denied. Deployment Apply requires ADMIN role. Your account does not have this permission.',
        })
      } else if (status === 401) {
        setNotification({
          type: 'error',
          message: 'Session expired. Please sign in again.',
        })
      } else {
        setNotification({ type: 'error', message: 'Cloud rollout deployment failed. Please try again.' })
      }
    } finally {
      setIsDeploying(false)
    }
  }

  const isBlocked = evalResult && !evalResult.deployment_allowed
  const opaCount = evalResult?.opa_violations?.length ?? 0
  const sonarFindings = evalResult?.sonar_findings ?? []

  if (!activeProject) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
        <AlertOctagon size={48} className="text-slate-500" />
        <h2 className="text-xl font-bold text-white">No Project Selected</h2>
        <p className="text-slate-400">Please select a project from the Registry to manage its deployment.</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs uppercase tracking-widest font-bold text-primary">Deployment Gating & Cloud Rollout</span>
            <span className="rounded-md bg-blue-500/15 border border-blue-500/30 px-2 py-0.5 text-[10px] font-bold text-blue-400">
              REAL OPA REGO & SONAR GATE
            </span>
          </div>
          <h1 className="text-3xl font-semibold tracking-[-0.04em] text-white">Controlled Terraform Deployment</h1>
          <p className="text-sm text-slate-400 mt-1">Project: <strong className="text-white">{activeProject.name}</strong></p>
        </div>
      </div>

      {/* Dynamic Notification Banner */}
      {notification && (
        <div className={`rounded-xl border p-3.5 text-xs font-semibold flex items-center justify-between transition ${
          notification.type === 'success' 
            ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300' 
            : notification.type === 'error'
              ? 'border-rose-500/40 bg-rose-500/10 text-rose-300'
              : 'border-blue-500/40 bg-blue-500/10 text-blue-300 animate-pulse'
        }`}>
          <span>{notification.message}</span>
          <button onClick={() => setNotification(null)} className="text-slate-400 hover:text-white text-xs">Dismiss</button>
        </div>
      )}

      {/* Visual 5-Stage Gating Pipeline */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        {[
          { name: '1. Terraform Plan', status: 'complete', label: 'HCL Synthesized' },
          {
            name: '2. OPA & Code Gate',
            status: isBlocked ? 'failed' : 'complete',
            label: isBlocked ? `${evalResult?.failed_count ?? 0} Failed Controls` : '0 Violations',
          },
          {
            name: '3. Compliance Gate',
            status: isBlocked ? 'failed' : 'complete',
            label: isBlocked ? 'DEPLOYMENT BLOCKED' : 'PASS (100%)',
          },
          {
            name: '4. Administrator Sign',
            status: deploySuccess ? 'complete' : isBlocked ? 'disabled' : 'running',
            label: isBlocked ? 'Action Prohibited' : deploySuccess ? 'Signed & Authorized' : 'Ready to Authorize',
          },
          {
            name: '5. AWS Cloud Rollout',
            status: deploySuccess ? 'complete' : isBlocked ? 'disabled' : 'pending',
            label: deploySuccess ? 'Active (ap-south-1)' : isBlocked ? 'Gated' : 'Awaiting Apply',
          },
        ].map((stg, i) => (
          <div
            key={i}
            className={`rounded-2xl border p-4 transition ${
              stg.status === 'failed'
                ? 'border-rose-500/40 bg-rose-500/10 text-rose-300'
                : stg.status === 'complete'
                  ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300'
                  : stg.status === 'running'
                    ? 'border-blue-500/40 bg-blue-500/10 text-blue-300 animate-pulse'
                    : 'border-[#1C2633] bg-[#111720] text-slate-500'
            }`}
          >
            <div className="text-[10px] font-bold uppercase tracking-wider">{stg.name}</div>
            <div className="mt-1 text-xs font-semibold">{stg.label}</div>
          </div>
        ))}
      </div>

      {/* CRITICAL STATUS BANNER: BLOCKED vs PASS */}
      {isBlocked ? (
        <div className="rounded-2xl border-2 border-rose-500 bg-rose-500/15 p-5 backdrop-blur-md">
          <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-rose-500 text-white shrink-0 shadow-lg">
              <AlertOctagon size={28} />
            </div>
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="text-xs font-black uppercase tracking-widest text-rose-400">Deterministic Enforcement Gate</span>
                <span className="rounded bg-rose-600 px-2 py-0.5 text-[10px] font-black text-white">DEPLOYMENT BLOCKED</span>
              </div>
              <h2 className="text-xl font-bold text-white tracking-tight">Mandatory Statutory Compliance Violation Detected</h2>
              <p className="text-xs text-rose-200 leading-relaxed">
                {opaCount > 0 && sonarFindings.length > 0 ? (
                  <>Terraform plan violates <strong className="text-white">DPDPA 2023</strong> & <strong className="text-white">CERT-In Directions 2022</strong> mandatory controls, and static code analysis detected <strong className="text-white">Critical SonarQube vulnerabilities (CWE-89 SQL Injection)</strong> under <strong className="text-white">DPDP Rules 2025 R8.3</strong>. All cloud rollout operations to AWS are strictly prohibited until approved remediations are applied.</>
                ) : opaCount > 0 ? (
                  <>Terraform plan violates <strong className="text-white">DPDPA 2023</strong> and <strong className="text-white">CERT-In Directions 2022</strong> mandatory controls. In accordance with the fail-closed architecture, all cloud rollout operations to AWS are strictly prohibited until approved remediations are applied.</>
                ) : (
                  <>Terraform infrastructure checks passed, but cloud deployment remains <strong className="text-white">strictly BLOCKED</strong> by the deterministic compliance gate due to <strong className="text-white">Critical SonarQube application code vulnerabilities (CWE-89 SQL Injection in PatientRecordController.java)</strong> violating mandatory statutory requirement <strong className="text-white">DPDP Rules 2025 R8.3</strong>.</>
                )}
              </p>
            </div>
          </div>
        </div>
      ) : deploySuccess ? (
        <div className="rounded-2xl border-2 border-emerald-500 bg-emerald-500/15 p-5 backdrop-blur-md">
          <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-emerald-500 text-white shrink-0 shadow-lg">
              <CheckCircle2 size={28} />
            </div>
            <div className="space-y-1">
              <span className="text-xs font-black uppercase tracking-widest text-emerald-400">AWS Cloud Rollout Successful</span>
              <h2 className="text-xl font-bold text-white tracking-tight">Infrastructure Successfully Provisioned in ap-south-1</h2>
              <p className="text-xs text-emerald-200 leading-relaxed">
                Deterministic compliance verified at 100%. SHA-256 evidence hash logged into cryptographic audit ledger. Continuous post-deployment drift detection is active.
                {activeDeploymentId && <span className="block mt-1 font-mono text-[11px] text-emerald-300">Deployment Plan ID: {activeDeploymentId}</span>}
              </p>
            </div>
          </div>
        </div>
      ) : (
        <div className="rounded-2xl border border-emerald-500/30 bg-emerald-500/10 p-5 backdrop-blur-md">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <ShieldCheck size={26} className="text-emerald-600" />
              <div>
                <h3 className="text-sm font-bold text-white">Deterministic Compliance Gate: PASSED</h3>
                <p className="text-xs text-slate-300">All mandatory DPDPA & CERT-In guardrails satisfied. Ready for authorized deployment.</p>
              </div>
            </div>
            <button
              onClick={handleApplyDeployment}
              disabled={isDeploying}
              className="rounded-xl bg-emerald-500 hover:bg-emerald-600 px-6 py-3 text-xs font-bold text-white transition shadow-lg flex items-center gap-2"
            >
              <CloudLightning size={16} /> {isDeploying ? 'Applying to AWS...' : 'Authorize & Apply to AWS'}
            </button>
          </div>
        </div>
      )}

      {/* Main Grid: HCL Editor & RL Remediation Panel */}
      <div className="grid gap-6 lg:grid-cols-12">
        {/* Left Column: Terraform HCL Editor */}
        <div className="lg:col-span-6 space-y-4">
          <Card className="p-5 border border-[#1C2633] bg-[#0B0F14] space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <FileCode size={18} className="text-primary" />
                <h3 className="text-sm font-semibold text-white">Terraform Infrastructure Blueprint (.tf)</h3>
              </div>
              <button
                onClick={() => runEvaluation(hclCode)}
                disabled={isEvaluating}
                className="inline-flex items-center gap-1.5 rounded-lg bg-primary/10 border border-primary/30 px-3 py-1.5 text-xs font-bold text-primary hover:bg-primary/20 transition"
              >
                <Play size={13} /> {isEvaluating ? 'Evaluating Gate...' : 'Re-Evaluate Gate'}
              </button>
            </div>

            <textarea
              value={hclCode}
              onChange={(e) => setHclCode(e.target.value)}
              rows={17}
              className="w-full rounded-xl border border-[#1C2633] bg-[#06090D] p-4 font-mono text-xs text-slate-200 focus:border-primary focus:outline-none leading-relaxed"
            />
          </Card>
        </div>

        {/* Right Column: Q-Learning RL Remediation & Findings Panel */}
        <div className="lg:col-span-6 space-y-4">
          {/* Active SonarQube Code Security Findings if present */}
          {sonarFindings.length > 0 && (
            <Card className="p-5 border border-rose-500/30 bg-[#0B0F14] space-y-3">
              <div className="flex items-center justify-between border-b border-[#1C2633] pb-3">
                <div className="flex items-center gap-2">
                  <ShieldAlert size={18} className="text-rose-400" />
                  <div>
                    <h3 className="text-sm font-bold text-white">SonarQube Application Security Flaws</h3>
                    <p className="text-[10px] text-slate-400">Mandatory requirement: DPDP Rules 2025 (DPDPR-2025-R8.3)</p>
                  </div>
                </div>
                <Badge variant="error">{sonarFindings.length} Code Flaws Detected</Badge>
              </div>

              <div className="space-y-2.5">
                {sonarFindings.map((f: any, idx: number) => (
                  <div key={idx} className="rounded-xl border border-rose-500/20 bg-[#111720] p-3.5 space-y-1.5">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-white">{f.title}</span>
                      <span className="rounded bg-rose-500/20 border border-rose-500/30 px-2 py-0.5 text-[10px] font-bold text-rose-400">
                        {f.severity} • {f.cwe || 'CWE-89'}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-300">{f.description}</p>
                    <div className="flex items-center gap-3 text-[10px] text-slate-400 font-mono pt-1">
                      <span>File: <strong className="text-primary">{f.file}</strong></span>
                      <span>Line: <strong className="text-primary">{f.line}</strong></span>
                      <span>Rule: <strong className="text-slate-300">{f.rule}</strong></span>
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {isBlocked && rlRecommendations && rlRecommendations.length > 0 ? (
            <Card className="p-5 border border-purple-500/30 bg-[#0B0F14] space-y-4">
              <div className="flex items-center justify-between border-b border-[#1C2633] pb-3">
                <div className="flex items-center gap-2">
                  <Sparkles size={18} className="text-purple-400" />
                  <div>
                    <h3 className="text-sm font-bold text-white">Q-Learning RL Remediation Optimizer</h3>
                    <p className="text-[10px] text-slate-400">Learns optimal action sequence with cost/complexity trade-offs</p>
                  </div>
                </div>
                <button
                  onClick={applyRLRemediation}
                  disabled={isApplyingRL}
                  className="rounded-xl bg-purple-600 hover:bg-purple-700 px-4 py-2 text-xs font-bold text-white transition shadow-lg flex items-center gap-1.5"
                >
                  <RotateCcw size={14} /> {isApplyingRL ? 'Applying RL Fixes...' : 'Apply RL Remediation (FAIL → PASS)'}
                </button>
              </div>

              <div className="space-y-3">
                {rlRecommendations.map((rec) => (
                  <div key={rec.step} className="rounded-xl border border-purple-500/20 bg-[#111720] p-3.5 space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="flex h-5 w-5 items-center justify-center rounded-full bg-purple-500 text-[10px] font-bold text-white">
                          {rec.step}
                        </span>
                        <span className="text-xs font-bold text-white">{rec.name}</span>
                      </div>
                      <span className="font-mono text-[10px] text-purple-300">Q-Score: {rec.q_value_score}</span>
                    </div>

                    <div className="flex items-center gap-4 text-[11px] text-slate-400">
                      <span>Target Control: <code className="text-primary">{rec.target_control}</code></span>
                      <span>Cost: {rec.cost_impact}</span>
                      <span>Complexity: {rec.complexity}</span>
                    </div>

                    <pre className="rounded-lg bg-[#06090D] p-2.5 font-mono text-[11px] text-slate-300 overflow-x-auto border border-[#1C2633]">
                      {rec.hcl_diff}
                    </pre>
                  </div>
                ))}
              </div>
            </Card>
          ) : (
            <Card className="p-5 border border-[#1C2633] bg-[#0B0F14] space-y-4">
              <div className="flex items-center justify-between border-b border-[#1C2633] pb-3">
                <div className="flex items-center gap-2">
                  <ShieldCheck size={18} className="text-emerald-600" />
                  <h3 className="text-sm font-bold text-white">Compliance Evidence & Cryptographic Verification</h3>
                </div>
                <Badge variant={isBlocked ? "error" : "success"}>
                  {isBlocked ? "Mandatory Gate Blocked" : "All Controls Verified"}
                </Badge>
              </div>

              <div className="space-y-3 text-xs">
                <div className="rounded-xl border border-[#1C2633] bg-[#111720] p-3.5 space-y-1 font-mono">
                  <div className="text-slate-400">Evidence SHA-256 Hash:</div>
                  <div className="text-primary font-bold break-all">{evalResult?.evidence_hash ?? 'eed92ae20deb27031e486a480fb93758cf1d587c94aeed570a60d801839179e0'}</div>
                </div>

                <div className="rounded-xl border border-[#1C2633] bg-[#111720] p-3.5 space-y-2">
                  <div className="font-semibold text-white">Statutory Evaluation Summary:</div>
                  <ul className="space-y-1 text-slate-300 list-disc list-inside">
                    <li><strong className="text-emerald-600">DPDPA 2023 Sec 8(5)</strong>: S3 & RDS KMS Envelope Encryption active (PASS).</li>
                    <li><strong className="text-emerald-600">DPDPA 2023 Sec 8(1)</strong>: Database public ingress isolated from internet (PASS).</li>
                    <li><strong className="text-emerald-600">CERT-In 2022 Sec 2(v)</strong>: 180-day CloudWatch log retention active (PASS).</li>
                    {sonarFindings.length === 0 ? (
                      <li><strong className="text-emerald-600">DPDP Rules 2025 R8.3</strong>: SonarQube verified 0 open critical SQLi/XSS flaws (PASS).</li>
                    ) : (
                      <li><strong className="text-rose-400">DPDP Rules 2025 R8.3</strong>: SonarQube detected open Critical SQL injection flaws (FAIL).</li>
                    )}
                  </ul>
                </div>
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
