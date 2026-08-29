import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Bell,
  Cloud,
  Shield,
  Sliders,
  Eye,
  EyeOff,
  CheckCircle,
  AlertCircle,
} from 'lucide-react'
import { Card } from '../components/ui/card'
import { Switch } from '../components/ui/switch'

export function SettingsPage() {
  // Input states
  const [awsArn, setAwsArn] = useState('arn:aws:iam::123456789012:role/ReguCloudCrossAccount')
  const [azureTenant, setAzureTenant] = useState('4fa38c92-38ef-4122-8321-75bf22e391aa')
  const [slackWebhook, setSlackWebhook] = useState('https://example.com/slack-webhook')

  // Rule toggles
  const [rulesPci, setRulesPci] = useState(true)
  const [rulesSoc, setRulesSoc] = useState(true)
  const [rulesHipaa, setRulesHipaa] = useState(false)

  // Visibility toggles
  const [showAzure, setShowAzure] = useState(false)
  const [showWebhook, setShowWebhook] = useState(false)

  // Validation / Save feedback states
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'success' | 'error'>('idle')
  const [errors, setErrors] = useState<Record<string, string>>({})

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault()
    setErrors({})
    setSaveStatus('saving')

    const newErrors: Record<string, string> = {}

    // 1. AWS ARN Validation
    const arnRegex = /^arn:aws:iam::[0-9]{12}:role\/[a-zA-Z0-9+=,.@\-_/]+$/
    if (!arnRegex.test(awsArn)) {
      newErrors.awsArn = 'Invalid ARN pattern. Expected: arn:aws:iam::12digits:role/Name'
    }

    // 2. Azure Tenant ID validation (UUID)
    const uuidRegex = /^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$/
    if (!uuidRegex.test(azureTenant)) {
      newErrors.azureTenant = 'Invalid tenant ID. Must match standard UUID format.'
    }

    if (slackWebhook && !slackWebhook.startsWith('https://')) {
      newErrors.slackWebhook = 'Webhook URL must be a valid HTTPS endpoint.'
    }

    setTimeout(() => {
      if (Object.keys(newErrors).length > 0) {
        setErrors(newErrors)
        setSaveStatus('error')
      } else {
        setSaveStatus('success')
        // Automatically return to idle after 3 seconds
        setTimeout(() => setSaveStatus('idle'), 3000)
      }
    }, 800)
  }

  const handleDiscard = () => {
    setAwsArn('arn:aws:iam::123456789012:role/ReguCloudCrossAccount')
    setAzureTenant('4fa38c92-38ef-4122-8321-75bf22e391aa')
    setSlackWebhook('https://example.com/slack-webhook')
    setRulesPci(true)
    setRulesSoc(true)
    setRulesHipaa(false)
    setErrors({})
    setSaveStatus('idle')
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <p className="text-sm text-slate-400">Control Panel</p>
          <h1 className="text-3xl font-semibold tracking-[-0.04em] text-white">Settings</h1>
        </div>

        {/* Save Status Indicators */}
        <AnimatePresence mode="wait">
          {saveStatus === 'success' && (
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              className="flex items-center gap-2 rounded-xl bg-emerald-500/10 border border-emerald-500/20 px-4 py-2 text-xs font-bold text-emerald-600"
            >
              <CheckCircle size={14} /> Settings saved successfully
            </motion.div>
          )}
          {saveStatus === 'error' && (
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              className="flex items-center gap-2 rounded-xl bg-rose-500/10 border border-rose-500/20 px-4 py-2 text-xs font-bold text-rose-500"
            >
              <AlertCircle size={14} /> Validation failed
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <form onSubmit={handleSave} className="space-y-6">
        <div className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
          <div className="space-y-6">
            {/* Cloud Credentials */}
            <Card className="p-6 border border-[#1C2633] bg-[#0B0F14] rounded-3xl">
              <div className="mb-5 flex items-center gap-3 text-primary border-b border-[#1C2633]/60 pb-3">
                <Cloud size={18} />
                <h2 className="text-lg font-semibold text-white">Cloud Provider Credentials</h2>
              </div>

              <div className="space-y-4">
                {/* AWS ARN */}
                <div>
                  <label className="block text-xs uppercase tracking-wider text-slate-500 mb-2 font-semibold">
                    AWS IAM Cross-Account Role ARN
                  </label>
                  <input
                    type="text"
                    value={awsArn}
                    onChange={(e) => setAwsArn(e.target.value)}
                    className={`w-full rounded-xl border bg-[#111720] px-4 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-primary transition ${
                      errors.awsArn ? 'border-rose-500/60 focus:border-rose-500' : 'border-[#1C2633]'
                    }`}
                  />
                  {errors.awsArn && <span className="text-[10px] text-rose-500 mt-1 block">{errors.awsArn}</span>}
                </div>

                {/* Azure Directory tenant ID */}
                <div>
                  <label className="block text-xs uppercase tracking-wider text-slate-500 mb-2 font-semibold">
                    Azure Tenant ID (Directory UUID)
                  </label>
                  <div className="relative">
                    <input
                      type={showAzure ? 'text' : 'password'}
                      value={azureTenant}
                      onChange={(e) => setAzureTenant(e.target.value)}
                      className={`w-full rounded-xl border bg-[#111720] pl-4 pr-12 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-primary transition ${
                        errors.azureTenant ? 'border-rose-500/60 focus:border-rose-500' : 'border-[#1C2633]'
                      }`}
                    />
                    <button
                      type="button"
                      onClick={() => setShowAzure(!showAzure)}
                      className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-white"
                    >
                      {showAzure ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                  {errors.azureTenant && <span className="text-[10px] text-rose-500 mt-1 block">{errors.azureTenant}</span>}
                </div>
              </div>
            </Card>

            {/* Compliance frameworks */}
            <Card className="p-6 border border-[#1C2633] bg-[#0B0F14] rounded-3xl">
              <div className="mb-5 flex items-center gap-3 text-primary border-b border-[#1C2633]/60 pb-3">
                <Shield size={18} />
                <h2 className="text-lg font-semibold text-white">Compliance frameworks</h2>
              </div>

              <div className="space-y-3">
                <div className="flex items-center justify-between p-3 border border-[#1C2633] bg-[#111720]/40 rounded-2xl">
                  <div>
                    <div className="text-sm font-semibold text-white">PCI DSS v4.0</div>
                    <div className="text-xs text-slate-500 mt-0.5">Enforce payment card security checks</div>
                  </div>
                  <Switch checked={rulesPci} onChange={setRulesPci} />
                </div>

                <div className="flex items-center justify-between p-3 border border-[#1C2633] bg-[#111720]/40 rounded-2xl">
                  <div>
                    <div className="text-sm font-semibold text-white">SOC 2 Type II</div>
                    <div className="text-xs text-slate-500 mt-0.5">Enforce security and availability isolation controls</div>
                  </div>
                  <Switch checked={rulesSoc} onChange={setRulesSoc} />
                </div>

                <div className="flex items-center justify-between p-3 border border-[#1C2633] bg-[#111720]/40 rounded-2xl">
                  <div>
                    <div className="text-sm font-semibold text-white">HIPAA Safeguards</div>
                    <div className="text-xs text-slate-500 mt-0.5">Audit patient health data protection policies</div>
                  </div>
                  <Switch checked={rulesHipaa} onChange={setRulesHipaa} />
                </div>
              </div>
            </Card>
          </div>

          <div className="space-y-6">
            {/* Notification alert hooks */}
            <Card className="p-5 border border-[#1C2633] bg-[#0B0F14] rounded-3xl">
              <div className="mb-4 flex items-center gap-3 text-primary border-b border-[#1C2633]/60 pb-2">
                <Bell size={18} />
                <h2 className="text-sm font-semibold text-white">Slack Webhooks</h2>
              </div>
              <div className="space-y-3">
                <div>
                  <label className="block text-[10px] uppercase tracking-wider text-slate-500 mb-2 font-semibold">
                    Slack Webhook Endpoint
                  </label>
                  <div className="relative">
                    <input
                      type={showWebhook ? 'text' : 'password'}
                      value={slackWebhook}
                      onChange={(e) => setSlackWebhook(e.target.value)}
                      className={`w-full rounded-xl border bg-[#111720] pl-3 pr-10 py-2.5 text-xs text-slate-200 focus:outline-none focus:border-primary transition ${
                        errors.slackWebhook ? 'border-rose-500/60 focus:border-rose-500' : 'border-[#1C2633]'
                      }`}
                    />
                    <button
                      type="button"
                      onClick={() => setShowWebhook(!showWebhook)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-white"
                    >
                      {showWebhook ? <EyeOff size={14} /> : <Eye size={14} />}
                    </button>
                  </div>
                  {errors.slackWebhook && <span className="text-[10px] text-rose-500 mt-1 block">{errors.slackWebhook}</span>}
                </div>
                <div className="flex items-center justify-between text-xs text-slate-350 pt-2">
                  <span>Alert on Critical Failures</span>
                  <span className="text-primary font-bold">Enabled</span>
                </div>
              </div>
            </Card>

            {/* OPA Parameters */}
            <Card className="p-5 border border-[#1C2633] bg-[#0B0F14] rounded-3xl">
              <div className="mb-4 flex items-center gap-3 text-primary border-b border-[#1C2633]/60 pb-2">
                <Sliders size={18} />
                <h2 className="text-sm font-semibold text-white">OPA Engine Telemetry</h2>
              </div>
              <div className="space-y-2 text-xs text-slate-400">
                <div className="flex justify-between py-1 border-b border-[#1C2633]/60">
                  <span>Audit scan interval</span>
                  <span className="font-semibold text-white">1 Hour</span>
                </div>
                <div className="flex justify-between py-1 border-b border-[#1C2633]/60">
                  <span>Evaluation engine mode</span>
                  <span className="font-semibold text-white">Continuous</span>
                </div>
                <div className="flex justify-between py-1">
                  <span>Remediation action policy</span>
                  <span className="font-semibold text-primary">Auto-Remediate</span>
                </div>
              </div>
            </Card>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="flex justify-end gap-3 border-t border-[#1C2633]/60 pt-6">
          <button
            type="button"
            onClick={handleDiscard}
            className="rounded-xl border border-[#1C2633] bg-[#111720] px-5 py-3 text-sm font-semibold text-slate-200 hover:bg-[#1C2633] transition"
          >
            Discard changes
          </button>
          <button
            type="submit"
            disabled={saveStatus === 'saving'}
            className="rounded-xl bg-primary px-5 py-3 text-sm font-semibold text-white transition hover:bg-blue-600 disabled:opacity-40"
          >
            {saveStatus === 'saving' ? 'Saving...' : 'Save settings'}
          </button>
        </div>
      </form>
    </div>
  )
}