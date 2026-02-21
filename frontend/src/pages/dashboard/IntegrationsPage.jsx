import { useState, useEffect } from "react";
import { useI18n } from "../../lib/i18n";
import { formatDate } from "../../lib/formatDate";
import integrationsAPI from "../../api/integrations";

export default function IntegrationsPage() {
  const { t, locale } = useI18n();
  const [integrations, setIntegrations] = useState([]);
  const [providers, setProviders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showSetup, setShowSetup] = useState(null);
  const [testResult, setTestResult] = useState(null);
  const [form, setForm] = useState({ api_key: "", webhook_url: "", sync_direction: "export" });

  useEffect(() => { fetchIntegrations(); }, []);

  const fetchIntegrations = async () => {
    try {
      const res = await integrationsAPI.list();
      setIntegrations(res.data.integrations || []);
      setProviders(res.data.available_providers || []);
    } catch {} finally { setLoading(false); }
  };

  const handleConnect = async (providerId) => {
    try {
      await integrationsAPI.create({ provider: providerId, api_key: form.api_key, webhook_url: form.webhook_url, sync_direction: form.sync_direction });
      setShowSetup(null);
      setForm({ api_key: "", webhook_url: "", sync_direction: "export" });
      fetchIntegrations();
    } catch {}
  };

  const handleTest = async (id) => {
    try {
      const res = await integrationsAPI.test(id);
      setTestResult(res.data);
      setTimeout(() => setTestResult(null), 3000);
    } catch {}
  };

  const handleSync = async (id) => {
    try {
      await integrationsAPI.sync(id);
      fetchIntegrations();
    } catch {}
  };

  const handleToggle = async (id, isActive) => {
    try {
      await integrationsAPI.update(id, { is_active: !isActive });
      fetchIntegrations();
    } catch {}
  };

  const handleDisconnect = async (id) => {
    if (!confirm(t("integrations.disconnectConfirm"))) return;
    try {
      await integrationsAPI.delete(id);
      fetchIntegrations();
    } catch {}
  };

  const connectedProviders = new Set(integrations.map(i => i.provider));

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-navy-900">{t("integrations.title")}</h1>
        <p className="text-navy-500 mt-1">{t("integrations.subtitle")}</p>
      </div>

      {loading ? (
        <div className="text-center py-12 text-navy-400">{t("common.loading")}</div>
      ) : (
        <>
          {/* Connected integrations */}
          {integrations.length > 0 && (
            <div className="space-y-4">
              <h2 className="text-lg font-semibold text-navy-900">{t("integrations.connected")}</h2>
              {integrations.map((intg) => (
                <div key={intg.id} className="bg-white rounded-xl border border-navy-200 p-6">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className={`w-12 h-12 rounded-xl flex items-center justify-center text-white font-bold text-lg ${
                        intg.provider === "greenhouse" ? "bg-green-600" : "bg-blue-600"
                      }`}>
                        {intg.provider === "greenhouse" ? "G" : "L"}
                      </div>
                      <div>
                        <h3 className="font-semibold text-navy-900 capitalize">{intg.provider}</h3>
                        <div className="flex items-center gap-2 mt-0.5">
                          <span className={`inline-flex items-center gap-1 text-xs font-medium ${intg.is_active ? 'text-green-600' : 'text-navy-400'}`}>
                            <span className={`w-1.5 h-1.5 rounded-full ${intg.is_active ? 'bg-green-500' : 'bg-navy-300'}`} />
                            {intg.is_active ? t("integrations.active") : t("integrations.inactive")}
                          </span>
                          <span className="text-xs text-navy-400">· {intg.sync_direction}</span>
                          {intg.last_synced_at && (
                            <span className="text-xs text-navy-400">
                              · {t("integrations.lastSync")}: {formatDate(intg.last_synced_at, locale)}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <button onClick={() => handleTest(intg.id)} className="px-3 py-1.5 text-xs font-medium text-navy-600 border border-navy-200 rounded-lg hover:bg-navy-50">
                        {t("integrations.test")}
                      </button>
                      <button onClick={() => handleSync(intg.id)} className="px-3 py-1.5 text-xs font-medium text-primary-600 border border-primary-200 rounded-lg hover:bg-primary-50">
                        {t("integrations.sync")}
                      </button>
                      <button onClick={() => handleToggle(intg.id, intg.is_active)} className="px-3 py-1.5 text-xs font-medium text-navy-500 border border-navy-200 rounded-lg hover:bg-navy-50">
                        {intg.is_active ? t("integrations.disable") : t("integrations.enable")}
                      </button>
                      <button onClick={() => handleDisconnect(intg.id)} className="px-3 py-1.5 text-xs font-medium text-red-500 border border-red-200 rounded-lg hover:bg-red-50">
                        {t("integrations.disconnect")}
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Available providers */}
          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-navy-900">{t("integrations.available")}</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {providers.map((p) => (
                <div key={p.id} className="bg-white rounded-xl border border-navy-200 p-6">
                  <div className="flex items-center gap-3 mb-4">
                    <div className={`w-10 h-10 rounded-lg flex items-center justify-center text-white font-bold ${
                      p.id === "greenhouse" ? "bg-green-600" : "bg-blue-600"
                    }`}>
                      {p.id === "greenhouse" ? "G" : "L"}
                    </div>
                    <div>
                      <h3 className="font-semibold text-navy-900">{p.name}</h3>
                      <p className="text-xs text-navy-500">{p.description}</p>
                    </div>
                  </div>
                  <ul className="space-y-1 mb-4">
                    {p.features.map((f) => (
                      <li key={f} className="flex items-center gap-2 text-sm text-navy-600">
                        <svg className="w-4 h-4 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                        {f}
                      </li>
                    ))}
                  </ul>
                  {connectedProviders.has(p.id) ? (
                    <span className="text-sm text-green-600 font-medium">{t("integrations.alreadyConnected")}</span>
                  ) : (
                    <button
                      onClick={() => setShowSetup(p.id)}
                      className="bg-primary-600 hover:bg-primary-700 text-white px-4 py-2 rounded-lg text-sm font-medium w-full transition-colors"
                    >
                      {t("integrations.connect")}
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      {/* Test result toast */}
      {testResult && (
        <div className={`fixed bottom-4 end-4 px-4 py-3 rounded-lg shadow-lg text-sm font-medium ${
          testResult.success ? 'bg-green-600 text-white' : 'bg-red-600 text-white'
        }`}>
          {testResult.message}
        </div>
      )}

      {/* Setup modal */}
      {showSetup && (
        <div className="fixed inset-0 bg-navy-900/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md">
            <div className="p-6 border-b border-navy-100">
              <h2 className="text-lg font-semibold text-navy-900">
                {t("integrations.setup")} {showSetup.charAt(0).toUpperCase() + showSetup.slice(1)}
              </h2>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-navy-700 mb-1">{t("integrations.apiKey")}</label>
                <input
                  type="password" value={form.api_key}
                  onChange={(e) => setForm({ ...form, api_key: e.target.value })}
                  className="w-full px-3 py-2 border border-navy-300 rounded-lg text-sm"
                  placeholder="Enter your API key"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-navy-700 mb-1">{t("integrations.webhookUrl")}</label>
                <input
                  type="url" value={form.webhook_url}
                  onChange={(e) => setForm({ ...form, webhook_url: e.target.value })}
                  className="w-full px-3 py-2 border border-navy-300 rounded-lg text-sm"
                  placeholder="https://..."
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-navy-700 mb-1">{t("integrations.syncDirection")}</label>
                <select
                  value={form.sync_direction}
                  onChange={(e) => setForm({ ...form, sync_direction: e.target.value })}
                  className="w-full px-3 py-2 border border-navy-300 rounded-lg text-sm"
                >
                  <option value="export">Export (CoreMatch → ATS)</option>
                  <option value="import">Import (ATS → CoreMatch)</option>
                  <option value="bidirectional">Bidirectional</option>
                </select>
              </div>
            </div>
            <div className="p-6 border-t border-navy-100 flex gap-3 justify-end">
              <button onClick={() => setShowSetup(null)} className="px-4 py-2 text-sm text-navy-600 hover:text-navy-800">
                {t("common.cancel")}
              </button>
              <button
                onClick={() => handleConnect(showSetup)}
                disabled={!form.api_key}
                className="bg-primary-600 hover:bg-primary-700 disabled:opacity-50 text-white px-4 py-2 rounded-lg text-sm font-medium"
              >
                {t("integrations.connect")}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
