import { useEffect, useState } from 'react';

const SCENARIOS = [
  { value: 'teaching', label: '课堂教学', note: '自动套用课堂模板' },
  { value: 'church', label: '教会讲座', note: '自动套用教会模板' },
  { value: 'parents', label: '家长说明', note: '自动套用课堂模板' },
  { value: 'general', label: '通用', note: '自动套用课堂模板' },
];

const LANGUAGES = [
  { value: 'zh', label: '中文' },
  { value: 'en', label: 'English' },
  { value: 'bilingual', label: '双语' },
];

const MAX_REFERENCE_TEXT = 6000;

function formatElapsed(seconds) {
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${String(minutes).padStart(2, '0')}:${String(remainingSeconds).padStart(2, '0')}`;
}

export default function TopicInput({ onSubmit, isLoading }) {
  const [topic, setTopic] = useState('');
  const [referenceText, setReferenceText] = useState('');
  const [numSlides, setNumSlides] = useState(8);
  const [scenario, setScenario] = useState('teaching');
  const [language, setLanguage] = useState('zh');
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [draftFirst, setDraftFirst] = useState(false);
  const [wasLoading, setWasLoading] = useState(isLoading);

  // Reset the timer whenever loading starts/stops. Done during render (React's
  // "adjust state when a prop changes" pattern) instead of a synchronous setState
  // in the effect body, which causes cascading renders.
  if (wasLoading !== isLoading) {
    setWasLoading(isLoading);
    setElapsedSeconds(0);
  }

  useEffect(() => {
    if (!isLoading) return undefined;

    const startedAt = Date.now();
    const intervalId = window.setInterval(() => {
      setElapsedSeconds(Math.floor((Date.now() - startedAt) / 1000));
    }, 1000);

    return () => window.clearInterval(intervalId);
  }, [isLoading]);

  const handleSubmit = (event) => {
    event.preventDefault();
    if (!topic.trim() && !referenceText.trim()) return;

    onSubmit({
      topic: topic.trim(),
      referenceText: referenceText.trim(),
      numSlides,
      scenario,
      language,
      draftFirst,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="bashi-card mx-auto max-w-3xl rounded-[28px] p-6 md:p-8">
      <div className="mb-6">
        <div className="inline-flex items-center rounded-full border border-bashi-border px-3 py-1 text-xs uppercase tracking-[0.24em] text-bashi-text-muted">
          Outline Studio
        </div>
        <h2 className="mt-4 text-2xl font-semibold text-bashi-text md:text-3xl">
          输入主题，或贴一篇参考文章给 AI 提炼
        </h2>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-bashi-text-secondary md:text-base">
          巴适PPT会先生成可编辑大纲，再渲染成 PPTX。教会场景自动使用教会模板，其它场景自动使用课堂模板，避免再让你做多一步选择。
        </p>
      </div>

      <div className="grid gap-5">
        <div>
          <label className="mb-2 block text-sm font-medium text-bashi-text">
            主题 Topic
          </label>
          <input
            type="text"
            value={topic}
            onChange={(event) => setTopic(event.target.value)}
            placeholder="例如：MakeCode Arcade游戏编程入门"
            className="bashi-input w-full rounded-2xl px-4 py-3 text-base"
            maxLength={200}
            disabled={isLoading}
          />
        </div>

        <div>
          <div className="mb-2 flex items-center justify-between gap-3">
            <label className="block text-sm font-medium text-bashi-text">
              参考文章 Reference Article
            </label>
            <span className="text-xs text-bashi-text-muted">
              {referenceText.length} / {MAX_REFERENCE_TEXT}
            </span>
          </div>
          <textarea
            value={referenceText}
            onChange={(event) => setReferenceText(event.target.value.slice(0, MAX_REFERENCE_TEXT))}
            placeholder="可选：粘贴一篇文章、讲义或课程说明，AI 会优先提炼其中的结构和重点。"
            className="bashi-input min-h-[160px] w-full rounded-2xl px-4 py-3 text-sm leading-6"
            disabled={isLoading}
          />
          <p className="mt-2 text-xs leading-5 text-bashi-text-muted">
            这不是必填项。建议粘贴关键段落或讲义内容，不必贴整本书。
          </p>
        </div>

        <div>
          <label className="mb-3 block text-sm font-medium text-bashi-text">
            场景 Scenario
          </label>
          <div className="grid gap-3 md:grid-cols-2">
            {SCENARIOS.map((item) => (
              <label
                key={item.value}
                className={`bashi-pill rounded-2xl px-4 py-4 ${
                  scenario === item.value ? 'active' : ''
                } ${isLoading ? 'pointer-events-none opacity-60' : ''}`}
              >
                <input
                  type="radio"
                  name="scenario"
                  value={item.value}
                  checked={scenario === item.value}
                  onChange={(event) => setScenario(event.target.value)}
                  disabled={isLoading}
                  className="sr-only"
                />
                <div className="font-medium">{item.label}</div>
                <div className="mt-1 text-xs text-bashi-text-muted">{item.note}</div>
              </label>
            ))}
          </div>
        </div>

        <div>
          <label className="mb-2 block text-sm font-medium text-bashi-text">
            页数 Slides
          </label>
          <div className="rounded-2xl border border-bashi-border bg-black/20 px-4 py-4">
            <div className="mb-3 flex items-center justify-between text-sm text-bashi-text-secondary">
              <span>根据内容长度自动生成更合适的结构</span>
              <span className="text-lg font-semibold text-bashi-copper">{numSlides} 页</span>
            </div>
            <input
              type="range"
              min={4}
              max={15}
              value={numSlides}
              onChange={(event) => setNumSlides(Number(event.target.value))}
              disabled={isLoading}
              className="w-full"
            />
            <div className="mt-2 flex justify-between text-xs text-bashi-text-muted">
              <span>4</span>
              <span>15</span>
            </div>
          </div>
        </div>

        <div>
          <label className="mb-3 block text-sm font-medium text-bashi-text">
            语言 Language
          </label>
          <div className="flex flex-wrap gap-3">
            {LANGUAGES.map((item) => (
              <label
                key={item.value}
                className={`bashi-pill rounded-full px-4 py-2 ${
                  language === item.value ? 'active' : ''
                } ${isLoading ? 'pointer-events-none opacity-60' : ''}`}
              >
                <input
                  type="radio"
                  name="language"
                  value={item.value}
                  checked={language === item.value}
                  onChange={(event) => setLanguage(event.target.value)}
                  disabled={isLoading}
                  className="sr-only"
                />
                {item.label}
              </label>
            ))}
          </div>
        </div>
      </div>

      <div className="mt-8 space-y-4">
        <label className="flex cursor-pointer items-start gap-3 rounded-2xl border border-bashi-border bg-black/20 px-4 py-3 text-sm text-bashi-text-secondary">
          <input
            type="checkbox"
            checked={draftFirst}
            onChange={(event) => setDraftFirst(event.target.checked)}
            disabled={isLoading}
            className="mt-0.5 accent-bashi-copper"
          />
          <span>
            先生成参考文章，确认后再生成大纲
            <span className="mt-0.5 block text-xs text-bashi-text-muted">
              Draft an article first, then the outline — lets you review/correct the direction before the PPT.
            </span>
          </span>
        </label>

        <button
          type="submit"
          disabled={(!topic.trim() && !referenceText.trim()) || isLoading}
          className="bashi-btn-primary w-full rounded-2xl px-6 py-4 text-lg font-semibold"
        >
          {isLoading
            ? (draftFirst ? '正在生成文章...' : '正在生成大纲...')
            : (draftFirst ? '生成参考文章 Draft Article' : '生成大纲 Generate Outline')}
        </button>

        {isLoading && (
          <div className="rounded-2xl border border-bashi-border bg-black/25 px-4 py-4">
            <div className="mb-3 flex items-center justify-between gap-4 text-sm text-bashi-text-secondary">
              <span className="font-medium text-bashi-text">AI 模型正在思考中</span>
              <span className="text-bashi-copper">已等待 {formatElapsed(elapsedSeconds)}</span>
            </div>
            <div className="bashi-progress-track">
              <div className="bashi-progress-indeterminate" />
            </div>
            <div className="mt-3 text-sm leading-6 text-bashi-text-secondary">
              正在生成 outline。云端模型通常在十几秒内完成，本地模型可能需要几分钟。进度条仅表示“仍在工作中”。
            </div>
          </div>
        )}
      </div>
    </form>
  );
}
