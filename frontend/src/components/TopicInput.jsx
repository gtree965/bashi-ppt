import { useEffect, useState } from 'react';
import { recommendSlides } from '../api/client';

const SCENARIOS = [
  { value: 'teaching', label: '课堂教学', note: '自动套用课堂模板' },
  { value: 'church', label: '教会讲座', note: '自动套用教会模板' },
  { value: 'parents', label: '家长说明', note: '自动套用课堂模板' },
  { value: 'general', label: '通用', note: '自动套用课堂模板' },
];

const LANGUAGES = [
  { value: 'zh', label: '简体中文' },
  { value: 'en', label: 'English' },
  { value: 'bilingual', label: '中英双语' },
];

const MAX_REFERENCE_TEXT = 6000;

function formatElapsed(seconds) {
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${String(minutes).padStart(2, '0')}:${String(remainingSeconds).padStart(2, '0')}`;
}

export default function TopicInput({
  onSubmit,
  isLoading,
  initialValues = null,
  loadingStage = 'outline',
}) {
  const [topic, setTopic] = useState(initialValues?.topic || '');
  const [referenceText, setReferenceText] = useState(initialValues?.referenceText || '');
  const [numSlides, setNumSlides] = useState(initialValues?.numSlides || 8);
  const [slideCountMode, setSlideCountMode] = useState(initialValues?.slideCountMode || 'auto');
  const [slideRecommendation, setSlideRecommendation] = useState({
    recommended_slides: initialValues?.numSlides || 8,
    basis: 'topic_scope',
    reason: '输入主题或参考材料后，系统会自动建议页数。',
  });
  const [recommendationBusy, setRecommendationBusy] = useState(false);
  const [scenario, setScenario] = useState(initialValues?.scenario || 'teaching');
  const [outputLanguage, setOutputLanguage] = useState(
    initialValues?.outputLanguage || 'zh'
  );
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [draftFirst, setDraftFirst] = useState(initialValues?.draftFirst || false);
  const [strictMaterial, setStrictMaterial] = useState(
    initialValues ? initialValues.generationMode === 'grounded' : true
  );
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

  useEffect(() => {
    const cleanTopic = topic.trim();
    const cleanReference = referenceText.trim();
    if (!cleanTopic && !cleanReference) {
      setRecommendationBusy(false);
      setSlideRecommendation({
        recommended_slides: 8,
        basis: 'topic_scope',
        reason: '输入主题或参考材料后，系统会自动建议页数。',
      });
      if (slideCountMode === 'auto') setNumSlides(8);
      return undefined;
    }

    const controller = new AbortController();
    const timer = window.setTimeout(async () => {
      setRecommendationBusy(true);
      try {
        const data = await recommendSlides({
          topic: cleanTopic,
          referenceText: cleanReference,
          scenario,
          outputLanguage,
          signal: controller.signal,
        });
        setSlideRecommendation(data);
        if (slideCountMode === 'auto') {
          setNumSlides(data.recommended_slides);
        }
      } catch (error) {
        if (error.name !== 'AbortError') {
          // Keep the previous recommendation; generation remains available.
        }
      } finally {
        if (!controller.signal.aborted) setRecommendationBusy(false);
      }
    }, 450);

    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [topic, referenceText, scenario, outputLanguage, slideCountMode]);

  // The draft-article step only makes sense for topic-only input (AI invents an
  // article to review). If any reference text is present the user already has source
  // material, so the toggle is hidden and draft-first is never triggered.
  const showDraftToggle = topic.trim() !== '' && referenceText.trim() === '';

  const handleSubmit = (event) => {
    event.preventDefault();
    if (!topic.trim() && !referenceText.trim()) return;

    onSubmit({
      topic: topic.trim(),
      referenceText: referenceText.trim(),
      numSlides,
      scenario,
      outputLanguage,
      draftFirst: showDraftToggle ? draftFirst : false,
      generationMode: referenceText.trim() && strictMaterial ? 'grounded' : 'creative',
      slideCountMode,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="bashi-card mx-auto max-w-3xl rounded-[28px] p-6 md:p-8">
      <div className="mb-6">
        <div className="inline-flex items-center rounded-full border border-bashi-border px-3 py-1 text-xs uppercase tracking-[0.24em] text-bashi-text-muted">
          Outline Studio
        </div>
        <h2 className="mt-4 text-2xl font-semibold text-bashi-text md:text-3xl">
          输入主题，或粘贴参考材料给 AI 提炼
        </h2>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-bashi-text-secondary md:text-base">
          可直接生成可编辑大纲，也可先生成备课文章确认内容方向，再渲染成 PPTX。
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

        {showDraftToggle && (
          <label className="flex cursor-pointer items-start gap-3 rounded-2xl border border-bashi-border bg-black/20 px-4 py-3 text-sm text-bashi-text-secondary">
            <input
              type="checkbox"
              checked={draftFirst}
              onChange={(event) => setDraftFirst(event.target.checked)}
              disabled={isLoading}
              className="mt-0.5 accent-bashi-copper"
            />
            <span>
              先生成备课文章，再生成大纲
              <span className="mt-0.5 block text-xs leading-5 text-bashi-text-muted">
                适合只有主题时：先确认和修改内容方向，再生成 PPT 大纲。
              </span>
            </span>
          </label>
        )}

        <div>
          <div className="mb-2 flex items-center justify-between gap-3">
            <label className="block text-sm font-medium text-bashi-text">
              已有参考材料（可选） Source Material
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
            这不是必填项。材料会发送给“AI 模型设置”中当前连接的服务；
            请先删除学生、会友或其他人员的敏感信息。
          </p>
          {referenceText.trim() && (
            <div className="mt-3 rounded-2xl border border-bashi-border bg-black/20 p-4">
              <div className="text-sm font-medium text-bashi-text">材料使用方式</div>
              <label className="mt-3 flex cursor-pointer items-start gap-3 text-sm text-bashi-text-secondary">
                <input
                  type="radio"
                  name="materialMode"
                  checked={strictMaterial}
                  onChange={() => setStrictMaterial(true)}
                  disabled={isLoading}
                  className="mt-0.5 accent-bashi-copper"
                />
                <span>
                  严格依据材料
                  <span className="mt-0.5 block text-xs leading-5 text-bashi-text-muted">
                    只整理、压缩和重组材料中的事实，不主动补充背景、例子或结论。
                  </span>
                </span>
              </label>
              <label className="mt-3 flex cursor-pointer items-start gap-3 text-sm text-bashi-text-secondary">
                <input
                  type="radio"
                  name="materialMode"
                  checked={!strictMaterial}
                  onChange={() => setStrictMaterial(false)}
                  disabled={isLoading}
                  className="mt-0.5 accent-bashi-copper"
                />
                <span>
                  允许教学扩展
                  <span className="mt-0.5 block text-xs leading-5 text-bashi-text-muted">
                    将材料作为参考，允许 AI 补充教学性背景、例子和过渡内容。
                  </span>
                </span>
              </label>
            </div>
          )}
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
              <span>
                {slideCountMode === 'auto' ? '系统建议，可手动覆盖' : '已手动覆盖系统建议'}
              </span>
              <span className="text-lg font-semibold text-bashi-copper">{numSlides} 页</span>
            </div>
            <input
              type="range"
              min={4}
              max={15}
              value={numSlides}
              onChange={(event) => {
                setNumSlides(Number(event.target.value));
                setSlideCountMode('manual');
              }}
              disabled={isLoading}
              className="w-full"
            />
            <div className="mt-2 flex justify-between text-xs text-bashi-text-muted">
              <span>4</span>
              <span>15</span>
            </div>
            <div className="mt-3 flex flex-col gap-2 border-t border-white/5 pt-3 text-xs leading-5 text-bashi-text-muted sm:flex-row sm:items-start sm:justify-between">
              <span className="max-w-xl">
                {recommendationBusy
                  ? '正在重新计算建议页数…'
                  : slideRecommendation.reason}
              </span>
              {slideCountMode === 'manual' && (
                <button
                  type="button"
                  onClick={() => {
                    setSlideCountMode('auto');
                    setNumSlides(slideRecommendation.recommended_slides);
                  }}
                  disabled={isLoading}
                  className="shrink-0 text-left font-medium text-bashi-copper hover:text-bashi-text disabled:opacity-40"
                >
                  恢复推荐 {slideRecommendation.recommended_slides} 页
                </button>
              )}
            </div>
          </div>
        </div>

        <div>
          <label className="mb-3 block text-sm font-medium text-bashi-text">
            PPT 输出语言 Output Language
          </label>
          <p className="mb-3 text-xs leading-5 text-bashi-text-muted">
            输入材料可以是中文、英文或中英混合；这里决定生成的 PPT 使用哪种语言。
            其他输入语言目前属于实验性支持。
          </p>
          <div className="flex flex-wrap gap-3">
            {LANGUAGES.map((item) => (
              <label
                key={item.value}
                className={`bashi-pill rounded-full px-4 py-2 ${
                  outputLanguage === item.value ? 'active' : ''
                } ${isLoading ? 'pointer-events-none opacity-60' : ''}`}
              >
                <input
                  type="radio"
                  name="outputLanguage"
                  value={item.value}
                  checked={outputLanguage === item.value}
                  onChange={(event) => setOutputLanguage(event.target.value)}
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
        <button
          type="submit"
          disabled={(!topic.trim() && !referenceText.trim()) || isLoading}
          className="bashi-btn-primary w-full rounded-2xl px-6 py-4 text-lg font-semibold"
        >
          {isLoading
            ? (loadingStage === 'facts'
                ? '正在提取必须保留的事实...'
                : (draftFirst && showDraftToggle
                  ? '正在生成备课文章...'
                  : (referenceText.trim() && strictMaterial
                      ? '正在提取事实并生成大纲...'
                      : '正在生成大纲...')))
            : (draftFirst && showDraftToggle ? '生成备课文章 Prep Article' : '生成大纲 Generate Outline')}
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
              {loadingStage === 'facts'
                ? '正在从材料中提取事实。下一步会由你逐条确认，确认前不会生成大纲。'
                : (referenceText.trim() && strictMaterial
                  ? '正在先提取必须保留的材料事实，再生成 outline。'
                  : '正在生成 outline。')}
              {' '}
              云端模型通常在十几秒内完成，本地模型可能需要几分钟。进度条仅表示“仍在工作中”。
            </div>
          </div>
        )}
      </div>
    </form>
  );
}
