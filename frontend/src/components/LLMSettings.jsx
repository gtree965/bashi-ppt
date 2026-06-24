import { useState, useEffect } from "react";
import { getLLMSettings, saveLLMSettings, getRecommendedModels, testLLMSettings, getOpenRouterFreeModels } from "../api/client";

const CLOUD_PROVIDERS = new Set(["openrouter", "siliconflow", "dashscope", "custom"]);

const PROVIDERS = [
  {
    id: "dashscope",
    icon: "☁️",
    title: "阿里云百炼",
    subtitle: "中国大陆访问稳定，适合 Qwen 系列模型",
    badge: "国内推荐",
    badgeColor: "bg-emerald-500/20 text-emerald-300",
    keyLabel: "百炼 API Key",
    keyPlaceholder: "sk-...",
    help: {
      label: "bailian.console.aliyun.com",
      url: "https://bailian.console.aliyun.com/",
    },
    modelPlaceholder: "qwen3.7-plus",
  },
  {
    id: "siliconflow",
    icon: "⚡",
    title: "硅基流动",
    subtitle: "OpenAI 兼容接口，中文模型选择多，价格透明",
    badge: "高性价比",
    badgeColor: "bg-amber-500/20 text-amber-300",
    keyLabel: "硅基流动 API Key",
    keyPlaceholder: "sk-...",
    help: {
      label: "cloud.siliconflow.cn",
      url: "https://cloud.siliconflow.cn/",
    },
    modelPlaceholder: "Qwen/Qwen3.6-35B-A3B",
  },
  {
    id: "openrouter",
    icon: "🌐",
    title: "OpenRouter",
    subtitle: "海外聚合服务，免费模型多，但质量和访问可能波动",
    badge: "免费可试",
    badgeColor: "bg-cyan-500/20 text-cyan-300",
    keyLabel: "OpenRouter API Key",
    keyPlaceholder: "sk-or-v1-...",
    help: {
      label: "openrouter.ai",
      url: "https://openrouter.ai",
    },
    modelPlaceholder: "openrouter/free",
  },
  {
    id: "lmstudio",
    icon: "🔧",
    title: "本地 LM Studio",
    subtitle: "本机运行，适合已会加载本地模型的用户",
    badge: "本地",
    badgeColor: "bg-purple-500/20 text-purple-300",
    modelPlaceholder: "local-model",
  },
  {
    id: "ollama",
    icon: "🖥️",
    title: "本地 Ollama",
    subtitle: "隐私保护、离线优先，适合技术用户",
    badge: "离线优先",
    badgeColor: "bg-blue-500/20 text-blue-300",
    modelPlaceholder: "qwen3:8b",
  },
  {
    id: "custom",
    icon: "🧩",
    title: "自定义兼容接口",
    subtitle: "用于 DeepSeek、Groq 或其他 OpenAI-compatible 服务",
    badge: "高级",
    badgeColor: "bg-slate-500/20 text-slate-300",
    keyLabel: "API Key",
    keyPlaceholder: "your-api-key",
    modelPlaceholder: "provider-model-id",
  },
];

const PROVIDER_DEFAULTS = {
  lmstudio: "http://localhost:1234/v1",
  ollama: "http://localhost:11434/v1",
  openrouter: "https://openrouter.ai/api/v1",
  siliconflow: "https://api.siliconflow.cn/v1",
  dashscope: "https://dashscope.aliyuncs.com/compatible-mode/v1",
  custom: "",
};

function getProviderMeta(provider) {
  return PROVIDERS.find((item) => item.id === provider) || PROVIDERS[0];
}

function isRecommendedModel(model, models) {
  return Boolean(model) && models.some((item) => item.id === model);
}

export default function LLMSettings() {
  const [provider, setProvider] = useState("lmstudio");
  const [model, setModel] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [showAdvancedUrl, setShowAdvancedUrl] = useState(false);
  const [recommendedModels, setRecommendedModels] = useState({});
  const [isTesting, setIsTesting] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [saveResult, setSaveResult] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [pixabayApiKey, setPixabayApiKey] = useState("");
  const [isFetchingModels, setIsFetchingModels] = useState(false);

  useEffect(() => {
    Promise.all([getLLMSettings(), getRecommendedModels()])
      .then(([settings, models]) => {
        const prov = settings.provider || "lmstudio";
        setProvider(prov);
        setModel(settings.model || "");

        if (settings.api_key_set) {
          setApiKey(settings.api_key_masked || "");
        }
        if (settings.base_url) {
          setBaseUrl(settings.base_url);
          const defaultUrl = PROVIDER_DEFAULTS[prov] || "";
          const cleanBase = settings.base_url.replace(/\/$/, "");
          const cleanDefault = defaultUrl.replace(/\/$/, "");
          setShowAdvancedUrl(prov === "custom" || cleanBase !== cleanDefault);
        }
        if (settings.pixabay_api_key_set) {
          setPixabayApiKey(settings.pixabay_api_key_masked || "");
        }

        setRecommendedModels(models || {});
      })
      .catch(() => {})
      .finally(() => setIsLoading(false));
  }, []);

  const selectedProvider = getProviderMeta(provider);
  const requiresApiKey = CLOUD_PROVIDERS.has(provider);
  const currentRecommended = recommendedModels[provider] || [];
  const hasCustomRecommendedValue = model && !isRecommendedModel(model, currentRecommended);

  const buildPayload = () => {
    const payload = { provider, model };
    if (requiresApiKey) payload.api_key = apiKey;
    if (provider === "custom" || showAdvancedUrl) payload.base_url = baseUrl;
    return payload;
  };

  const handleTest = async () => {
    setIsTesting(true);
    setTestResult(null);
    try {
      const result = await testLLMSettings(buildPayload());
      if (result.connected) {
        setTestResult({ ok: true, message: result.message });
      } else {
        setTestResult({ ok: false, message: result.message });
      }
    } catch (e) {
      setTestResult({ ok: false, message: `❌ 连接异常：${e.message}` });
    } finally {
      setIsTesting(false);
    }
  };

  const handleSave = async () => {
    setIsSaving(true);
    setSaveResult(null);
    try {
      const payload = buildPayload();
      payload.pixabay_api_key = pixabayApiKey;
      await saveLLMSettings(payload);
      setSaveResult({ ok: true, message: "✅ 设置已保存，立即生效" });
    } catch (e) {
      setSaveResult({ ok: false, message: `❌ 保存失败：${e.message}` });
    } finally {
      setIsSaving(false);
    }
  };

  const handleFetchFreeModels = async () => {
    setIsFetchingModels(true);
    try {
      const result = await getOpenRouterFreeModels();
      if (result.success && result.models) {
        setRecommendedModels(prev => ({
          ...prev,
          openrouter: result.models
        }));
        setTestResult({ ok: true, message: `✅ 已更新 ${result.models.length} 个最新免费模型` });
      } else {
        setTestResult({ ok: false, message: `❌ 获取失败：${result.error || "未知错误"}` });
      }
    } catch (e) {
      setTestResult({ ok: false, message: `❌ 获取异常：${e.message}` });
    } finally {
      setIsFetchingModels(false);
    }
  };

  const handleProviderChange = (newProvider) => {
    setProvider(newProvider);
    setApiKey("");
    setBaseUrl(PROVIDER_DEFAULTS[newProvider] || "");
    setShowAdvancedUrl(newProvider === "custom");

    const defaultModel =
      recommendedModels[newProvider]?.[0]?.id ||
      getProviderMeta(newProvider).modelPlaceholder ||
      "";
    setModel(defaultModel);

    setTestResult(null);
    setSaveResult(null);
  };

  if (isLoading) {
    return (
      <div className="flex h-40 items-center justify-center text-bashi-text-muted text-sm">
        加载设置中...
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-5">
      <div>
        <h2 className="text-xl font-semibold text-bashi-text">AI 模型设置</h2>
        <p className="mt-1 text-sm text-bashi-text-secondary">选择 AI 来源，巴适PPT 会记住你的选择。</p>
      </div>

      <div className="rounded-2xl border border-amber-500/20 bg-amber-500/10 p-3 text-xs leading-relaxed text-amber-100">
        云端模型会接收你输入的主题、参考材料、大纲和讲稿请求，并可能产生费用。请根据学校/机构规则和材料敏感程度自行选择服务商。
      </div>

      <div className="grid gap-3">
        {PROVIDERS.map((p) => (
          <label
            key={p.id}
            className={`bashi-card flex cursor-pointer items-start gap-4 rounded-2xl p-4 transition-all ${
              provider === p.id ? "ring-2 ring-bashi-copper" : "opacity-70 hover:opacity-100"
            }`}
          >
            <input
              type="radio"
              name="provider"
              value={p.id}
              checked={provider === p.id}
              onChange={() => handleProviderChange(p.id)}
              className="sr-only"
            />
            <span className="mt-0.5 text-2xl">{p.icon}</span>
            <div className="flex-1 min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-medium text-bashi-text">{p.title}</span>
                <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${p.badgeColor}`}>{p.badge}</span>
              </div>
              <p className="mt-0.5 text-xs text-bashi-text-muted">{p.subtitle}</p>
            </div>
            <div className={`mt-1 h-4 w-4 flex-shrink-0 rounded-full border-2 ${
              provider === p.id ? "border-bashi-copper bg-bashi-copper" : "border-bashi-border"
            }`} />
          </label>
        ))}
      </div>

      <div className="grid gap-4">
        {requiresApiKey && (
          <div>
            <label className="mb-1.5 block text-sm font-medium text-bashi-text">{selectedProvider.keyLabel || "API Key"}</label>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder={selectedProvider.keyPlaceholder || "your-api-key"}
              className="bashi-input w-full rounded-xl px-4 py-2.5 font-mono text-sm"
              autoComplete="new-password"
            />
            <p className="mt-1.5 text-xs text-bashi-text-muted">
              {selectedProvider.help ? (
                <>
                  到 <a href={selectedProvider.help.url} target="_blank" rel="noreferrer" className="text-bashi-copper underline">{selectedProvider.help.label}</a> 创建/复制 API Key。
                </>
              ) : (
                "请从对应服务商控制台复制 API Key。"
              )}
              {" "}密钥只保存在本机应用目录的 .env 文件中。
            </p>
          </div>
        )}

        {provider === "ollama" && (
          <div className="rounded-xl border border-blue-500/20 bg-blue-500/10 p-3 text-xs text-blue-300">
            <p className="font-medium">尚未安装 Ollama？</p>
            <p className="mt-1">访问 <a href="https://ollama.com" target="_blank" rel="noreferrer" className="underline">ollama.com</a> 下载安装包（约 300MB），安装后点击“测试连接”。</p>
          </div>
        )}

        {currentRecommended.length > 0 && (
          <div>
            <div className="mb-1.5 flex items-center justify-between">
              <label className="text-sm font-medium text-bashi-text">推荐模型</label>
              {provider === "openrouter" && (
                <button
                  type="button"
                  onClick={handleFetchFreeModels}
                  disabled={isFetchingModels}
                  className="text-xs text-bashi-copper hover:underline disabled:opacity-50 flex items-center gap-1"
                >
                  {isFetchingModels ? "🔄 正在更新..." : "🔄 获取最新免费模型"}
                </button>
              )}
            </div>
            <select
              value={hasCustomRecommendedValue ? "__custom__" : model}
              onChange={(e) => {
                if (e.target.value !== "__custom__") setModel(e.target.value);
              }}
              className="bashi-input w-full rounded-xl px-4 py-2.5 text-sm"
            >
              <option value="">-- 选择推荐模型 --</option>
              {hasCustomRecommendedValue && <option value="__custom__">当前手动模型：{model}</option>}
              {currentRecommended.map((m) => (
                <option key={m.id} value={m.id}>{m.label}</option>
              ))}
            </select>
          </div>
        )}

        <div>
          <label className="mb-1.5 block text-sm font-medium text-bashi-text">模型 ID</label>
          <input
            type="text"
            value={model}
            onChange={(e) => setModel(e.target.value)}
            placeholder={selectedProvider.modelPlaceholder || "provider-model-id"}
            className="bashi-input w-full rounded-xl px-4 py-2.5 font-mono text-sm"
          />
          <p className="mt-1 text-[11px] text-bashi-text-muted leading-relaxed">
            可直接填写服务商模型页面上的 Model ID；本地 LM Studio 通常可保持为 local-model。
          </p>
        </div>

        <div>
          <button type="button" onClick={() => setShowAdvancedUrl(!showAdvancedUrl)} className="text-xs text-bashi-text-muted underline">
            {showAdvancedUrl ? "▲ 收起服务地址" : "▼ 服务地址 / 高级设置"}
          </button>
          {(showAdvancedUrl || provider === "custom") && (
            <div className="mt-2">
              <label className="mb-1 block text-xs font-medium text-bashi-text-secondary">服务地址 Base URL</label>
              <input
                type="text"
                value={baseUrl}
                onChange={(e) => setBaseUrl(e.target.value)}
                placeholder={PROVIDER_DEFAULTS[provider] || "https://your-provider.example/v1"}
                className="bashi-input w-full rounded-xl px-4 py-2.5 font-mono text-sm"
              />
              <p className="mt-1 text-[11px] text-bashi-text-muted leading-relaxed">
                仅在服务商要求自定义接入点时修改。LM Studio / Ollama 会自动补齐 /v1。
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Pixabay settings */}
      <div className="rounded-2xl border border-bashi-border bg-black/10 p-4">
        <h3 className="text-sm font-semibold text-bashi-text flex items-center gap-1.5">🖼️ 图片搜索设置</h3>
        <p className="mt-1 text-xs text-bashi-text-secondary">配置 Pixabay 免费图片搜索，用于在幻灯片中插入高清配图。</p>
        <div className="mt-3">
          <label className="mb-1 block text-xs font-medium text-bashi-text-secondary">Pixabay API Key</label>
          <input
            type="password"
            value={pixabayApiKey}
            onChange={(e) => setPixabayApiKey(e.target.value)}
            placeholder="例如：43210987-abcdef..."
            className="bashi-input w-full rounded-xl px-3 py-2 font-mono text-sm"
            autoComplete="new-password"
          />
          <p className="mt-1.5 text-[11px] text-bashi-text-muted leading-relaxed">
            免费注册并获取 API Key：<a href="https://pixabay.com/api/docs/" target="_blank" rel="noreferrer" className="text-bashi-copper underline">pixabay.com/api/docs</a> （在页面 "Parameters" 示例中直接复制你的 key 即可）。
          </p>
        </div>
      </div>

      {testResult && (
        <div className={`rounded-xl px-4 py-2.5 text-sm ${testResult.ok ? "bg-emerald-500/10 text-emerald-300" : "bg-red-500/10 text-red-300"}`}>
          {testResult.message}
        </div>
      )}
      {saveResult && (
        <div className={`rounded-xl px-4 py-2.5 text-sm ${saveResult.ok ? "bg-emerald-500/10 text-emerald-300" : "bg-red-500/10 text-red-300"}`}>
          {saveResult.message}
        </div>
      )}

      <div className="flex gap-3">
        <button type="button" onClick={handleTest} disabled={isTesting} className="bashi-btn-secondary flex-1 rounded-xl px-4 py-2.5 text-sm font-medium">
          {isTesting ? "测试中..." : "🔌 测试连接"}
        </button>
        <button type="button" onClick={handleSave} disabled={isSaving} className="bashi-btn-primary flex-1 rounded-xl px-4 py-2.5 text-sm font-medium">
          {isSaving ? "保存中..." : "💾 保存设置"}
        </button>
      </div>
    </div>
  );
}
