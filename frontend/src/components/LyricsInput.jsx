import { useState } from 'react';

const SAMPLE_LYRICS = `奇异恩典，何等甘甜，
我罪已得赦免！
前我失丧，今被寻回，
瞎眼今得看见。

如此恩典，使我敬畏，
使我心得安慰；
初信之时，即蒙恩惠，
真是何等宝贵！`;

const DEFAULT_LANGUAGES = [
  { code: 'zh', label: '中文', native_label: '中文', script: 'zh' },
  { code: 'en', label: 'English', native_label: 'English', script: 'latin' },
];

const DEFAULT_THEMES = [
  { id: 'classic_dark', name: '经典黑底白字', background: '#000000', text_color: '#FFFFFF', chorus_color: '#FFD700' },
  { id: 'deep_blue', name: '深蓝渐变', background: '#0C1445', text_color: '#FFFFFF', chorus_color: '#81D4FA' },
  { id: 'warm_dark', name: '暖色深底', background: '#1A0A00', text_color: '#FFF8E1', chorus_color: '#FFB74D' },
];

const DEFAULT_LIMITS = {
  single: { min_lines: 2, max_lines: 4, default_lines: 4 },
  single_extended: { min_lines: 2, max_lines: 6, default_lines: 4 },
  bilingual: { min_lines: 2, max_lines: 3, default_lines: 2 },
};

const DEFAULT_CHINESE_SCRIPT_OPTIONS = [
  { id: 'original', name: '原文', name_en: 'Original' },
  { id: 'to_simplified', name: '转为简体', name_en: 'To Simplified' },
  { id: 'to_traditional', name: '转为繁體', name_en: 'To Traditional' },
];

export default function LyricsInput({ onPreview, onGenerate, isLoading, config }) {
  const languages = config?.languages || DEFAULT_LANGUAGES;
  const themes = config?.themes || DEFAULT_THEMES;
  const limits = config?.limits || DEFAULT_LIMITS;
  const chineseScriptOptions = config?.chinese_script_options || DEFAULT_CHINESE_SCRIPT_OPTIONS;

  const [lyrics, setLyrics] = useState('');
  const [title, setTitle] = useState('');
  const [languageMode, setLanguageMode] = useState('single');
  const [primaryLang, setPrimaryLang] = useState('zh');
  const [secondaryLang, setSecondaryLang] = useState('en');
  const [chineseScriptMode, setChineseScriptMode] = useState('original');
  const [extendedSingleLines, setExtendedSingleLines] = useState(false);
  const [linesPerSlide, setLinesPerSlide] = useState(4);
  const [theme, setTheme] = useState('classic_dark');
  const [addTitleSlide, setAddTitleSlide] = useState(true);
  const [addAmenSlide, setAddAmenSlide] = useState(false);
  const [fontFamily, setFontFamily] = useState('');
  const [fontSizeAdj, setFontSizeAdj] = useState(0);
  const [lineSpacing, setLineSpacing] = useState(1.5);

  const currentLimits = languageMode === 'single' && extendedSingleLines
    ? (limits.single_extended || limits.single)
    : limits[languageMode];

  // Keep dependent selections valid when the mode/language changes. Done during
  // render (React's "adjust state when a prop changes" pattern) instead of in
  // effects, which would trigger cascading renders. Each branch is guarded so it
  // only fires when a value is actually out of sync (no render loop).
  if (linesPerSlide > currentLimits.max_lines || linesPerSlide < currentLimits.min_lines) {
    setLinesPerSlide(currentLimits.default_lines);
  }
  if (languageMode === 'bilingual' && secondaryLang === primaryLang) {
    const fallbackSecondary = languages.find((lang) => lang.code !== primaryLang)?.code;
    if (fallbackSecondary) {
      setSecondaryLang(fallbackSecondary);
    }
  }
  if ((languageMode !== 'single' || primaryLang !== 'zh') && chineseScriptMode !== 'original') {
    setChineseScriptMode('original');
  }
  if (languageMode !== 'single' && extendedSingleLines) {
    setExtendedSingleLines(false);
  }

  const buildPayload = () => ({
    lyrics,
    title: title.trim(),
    lines_per_slide: linesPerSlide,
    theme,
    language_mode: languageMode,
    chinese_script_mode: languageMode === 'single' && primaryLang === 'zh' ? chineseScriptMode : 'original',
    extended_single_lines: languageMode === 'single' ? extendedSingleLines : false,
    language_config: {
      primary: primaryLang,
      secondary: languageMode === 'bilingual' ? secondaryLang : undefined,
      primary_label: languages.find((l) => l.code === primaryLang)?.native_label || '',
      secondary_label: languageMode === 'bilingual'
        ? languages.find((l) => l.code === secondaryLang)?.native_label || ''
        : '',
    },
    add_title_slide: addTitleSlide,
    add_amen_slide: addAmenSlide,
    font_family: fontFamily || undefined,
    font_size_adjustment: fontSizeAdj,
    line_spacing: lineSpacing,
  });

  const handlePreview = (e) => {
    e.preventDefault();
    if (!lyrics.trim() || !title.trim()) return;
    onPreview(buildPayload());
  };

  const handleGenerate = (e) => {
    e.preventDefault();
    if (!lyrics.trim() || !title.trim()) return;
    onGenerate(buildPayload());
  };

  const linesOptions = [];
  for (let i = currentLimits.min_lines; i <= currentLimits.max_lines; i++) {
    linesOptions.push(i);
  }

  const linesLabel = languageMode === 'bilingual'
    ? `每页 ${linesPerSlide} 对歌词（共 ${linesPerSlide * 2} 行）`
    : `每页 ${linesPerSlide} 行歌词`;

  return (
    <form className="bashi-card mx-auto max-w-3xl rounded-[28px] p-6 md:p-8">
      <div className="mb-6">
        <div className="inline-flex items-center rounded-full border border-bashi-border px-3 py-1 text-xs uppercase tracking-[0.24em] text-bashi-text-muted">
          Hymn Studio
        </div>
        <h2 className="mt-4 text-2xl font-semibold text-bashi-text md:text-3xl">
          粘贴歌词，一键生成敬拜投影
        </h2>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-bashi-text-secondary md:text-base">
          支持单语和双语对照模式。系统自动识别段落和副歌，生成深色背景大字投影 PPT。
        </p>
      </div>

      <div className="grid gap-5">
        {/* Song title */}
        <div>
          <label className="mb-2 block text-sm font-medium text-bashi-text">
            歌曲标题 Song Title
          </label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="例如：奇异恩典"
            className="bashi-input w-full rounded-2xl px-4 py-3 text-base"
            maxLength={100}
            disabled={isLoading}
            required
          />
        </div>

        {/* Lyrics textarea */}
        <div>
          <label className="mb-2 block text-sm font-medium text-bashi-text">
            歌词 Lyrics
          </label>
          <textarea
            value={lyrics}
            onChange={(e) => setLyrics(e.target.value)}
            placeholder={SAMPLE_LYRICS}
            className="bashi-input min-h-[240px] w-full rounded-2xl px-4 py-3 font-mono text-sm leading-6"
            disabled={isLoading}
            required
          />
          <p className="mt-2 text-xs leading-5 text-bashi-text-muted">
            空行分段。副歌行前加"副歌:"或"chorus:"标记可高亮显示。
          </p>
        </div>

        {/* Language mode */}
        <div>
          <label className="mb-3 block text-sm font-medium text-bashi-text">
            语言模式 Language Mode
          </label>
          <div className="flex flex-wrap gap-3">
            <label
              className={`bashi-pill rounded-full px-4 py-2 ${languageMode === 'single' ? 'active' : ''} ${isLoading ? 'pointer-events-none opacity-60' : ''}`}
            >
              <input
                type="radio"
                name="languageMode"
                value="single"
                checked={languageMode === 'single'}
                onChange={() => setLanguageMode('single')}
                disabled={isLoading}
                className="sr-only"
              />
              单语
            </label>
            <label
              className={`bashi-pill rounded-full px-4 py-2 ${languageMode === 'bilingual' ? 'active' : ''} ${isLoading ? 'pointer-events-none opacity-60' : ''}`}
            >
              <input
                type="radio"
                name="languageMode"
                value="bilingual"
                checked={languageMode === 'bilingual'}
                onChange={() => setLanguageMode('bilingual')}
                disabled={isLoading}
                className="sr-only"
              />
              双语对照
            </label>
          </div>

          {/* Language dropdowns */}
          <div className="mt-3 flex flex-wrap items-center gap-4">
            <div className="flex items-center gap-2">
              <span className="text-sm text-bashi-text-secondary">
                {languageMode === 'bilingual' ? '主语言' : '语言'}:
              </span>
              <select
                value={primaryLang}
                onChange={(e) => setPrimaryLang(e.target.value)}
                disabled={isLoading}
                className="bashi-input rounded-xl px-3 py-2 text-sm"
              >
                {languages.map((lang) => (
                  <option key={lang.code} value={lang.code}>
                    {lang.native_label}
                  </option>
                ))}
              </select>
            </div>
            {languageMode === 'bilingual' && (
              <div className="flex items-center gap-2">
                <span className="text-sm text-bashi-text-secondary">副语言:</span>
                <select
                  value={secondaryLang}
                  onChange={(e) => setSecondaryLang(e.target.value)}
                  disabled={isLoading}
                  className="bashi-input rounded-xl px-3 py-2 text-sm"
                >
                  {languages
                    .filter((lang) => lang.code !== primaryLang)
                    .map((lang) => (
                      <option key={lang.code} value={lang.code}>
                        {lang.native_label}
                      </option>
                    ))}
                </select>
              </div>
            )}
          </div>
        </div>

        {languageMode === 'single' && primaryLang === 'zh' && (
          <div>
            <label className="mb-3 block text-sm font-medium text-bashi-text">
              中文转换 Chinese Script
            </label>
            <div className="flex flex-wrap gap-3">
              {chineseScriptOptions.map((option) => (
                <label
                  key={option.id}
                  className={`bashi-pill rounded-full px-4 py-2 ${chineseScriptMode === option.id ? 'active' : ''} ${isLoading ? 'pointer-events-none opacity-60' : ''}`}
                >
                  <input
                    type="radio"
                    name="chineseScriptMode"
                    value={option.id}
                    checked={chineseScriptMode === option.id}
                    onChange={() => setChineseScriptMode(option.id)}
                    disabled={isLoading}
                    className="sr-only"
                  />
                  {option.name}
                </label>
              ))}
            </div>
            <p className="mt-2 text-xs leading-5 text-bashi-text-muted">
              简繁转换会应用于“预览分页”和“生成歌词 PPT”
            </p>
          </div>
        )}

        {languageMode === 'single' && (
          <div>
            <label className="flex cursor-pointer items-start gap-3 text-sm text-bashi-text-secondary">
              <input
                type="checkbox"
                checked={extendedSingleLines}
                onChange={(e) => setExtendedSingleLines(e.target.checked)}
                disabled={isLoading}
                className="mt-0.5 accent-bashi-copper"
              />
              <span>
                允许更多行数（单语最多 6 行，适合大屏或短句歌词）
              </span>
            </label>
          </div>
        )}

        {/* Lines per slide */}
        <div>
          <label className="mb-3 block text-sm font-medium text-bashi-text">
            每页行数 Lines per Slide
          </label>
          <div className="flex flex-wrap gap-3">
            {linesOptions.map((n) => (
              <label
                key={n}
                className={`bashi-pill rounded-full px-4 py-2 ${linesPerSlide === n ? 'active' : ''} ${isLoading ? 'pointer-events-none opacity-60' : ''}`}
              >
                <input
                  type="radio"
                  name="linesPerSlide"
                  value={n}
                  checked={linesPerSlide === n}
                  onChange={() => setLinesPerSlide(n)}
                  disabled={isLoading}
                  className="sr-only"
                />
                {n}
              </label>
            ))}
          </div>
          <p className="mt-2 text-xs text-bashi-text-muted">{linesLabel}</p>
        </div>

        {/* Typography Controls */}
        <div>
          <label className="mb-3 block text-sm font-medium text-bashi-text">
            排版微调 Typography
          </label>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <div>
              <span className="mb-1 block text-xs text-bashi-text-secondary">字体 Font</span>
              <select
                value={fontFamily}
                onChange={(e) => setFontFamily(e.target.value)}
                disabled={isLoading}
                className="bashi-input w-full rounded-xl px-3 py-2 text-sm"
              >
                <option value="">默认 (Default)</option>
                <option value="Microsoft YaHei">微软雅黑 (Microsoft YaHei)</option>
                <option value="SimHei">黑体 (SimHei)</option>
                <option value="KaiTi">楷体 (KaiTi)</option>
                <option value="Arial">Arial</option>
              </select>
            </div>
            <div>
              <span className="mb-1 block text-xs text-bashi-text-secondary">
                字号微调 Size: {fontSizeAdj > 0 ? `+${fontSizeAdj}` : fontSizeAdj}
              </span>
              <input
                type="range"
                min="-10"
                max="10"
                step="1"
                value={fontSizeAdj}
                onChange={(e) => setFontSizeAdj(parseInt(e.target.value, 10))}
                disabled={isLoading}
                className="w-full accent-bashi-copper"
              />
            </div>
            <div>
              <span className="mb-1 block text-xs text-bashi-text-secondary">
                行距 Spacing: {lineSpacing.toFixed(1)}
              </span>
              <input
                type="range"
                min="1.0"
                max="2.5"
                step="0.1"
                value={lineSpacing}
                onChange={(e) => setLineSpacing(parseFloat(e.target.value))}
                disabled={isLoading}
                className="w-full accent-bashi-copper"
              />
            </div>
          </div>
        </div>

        {/* Theme picker */}
        <div>
          <label className="mb-3 block text-sm font-medium text-bashi-text">
            样式 Theme
          </label>
          <div className="flex flex-wrap gap-3">
            {themes.map((t) => (
              <label
                key={t.id}
                className={`bashi-pill flex items-center gap-3 rounded-2xl px-4 py-3 ${theme === t.id ? 'active' : ''} ${isLoading ? 'pointer-events-none opacity-60' : ''}`}
              >
                <input
                  type="radio"
                  name="theme"
                  value={t.id}
                  checked={theme === t.id}
                  onChange={() => setTheme(t.id)}
                  disabled={isLoading}
                  className="sr-only"
                />
                <span
                  className="inline-block h-6 w-6 rounded-full border border-white/20"
                  style={{ backgroundColor: t.background }}
                />
                <span className="text-sm">{t.name}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Checkboxes */}
        <div className="flex flex-wrap gap-6">
          <label className="flex cursor-pointer items-center gap-2 text-sm text-bashi-text-secondary">
            <input
              type="checkbox"
              checked={addTitleSlide}
              onChange={(e) => setAddTitleSlide(e.target.checked)}
              disabled={isLoading}
              className="accent-bashi-copper"
            />
            添加标题页
          </label>
          <label className="flex cursor-pointer items-center gap-2 text-sm text-bashi-text-secondary">
            <input
              type="checkbox"
              checked={addAmenSlide}
              onChange={(e) => setAddAmenSlide(e.target.checked)}
              disabled={isLoading}
              className="accent-bashi-copper"
            />
            添加结尾页 (阿们)
          </label>
        </div>
      </div>

      {/* Action buttons */}
      <div className="mt-8 flex flex-wrap gap-3">
        <button
          type="button"
          onClick={handlePreview}
          disabled={!lyrics.trim() || !title.trim() || isLoading}
          className="bashi-btn-secondary flex-1 rounded-2xl px-6 py-4 text-base font-semibold"
        >
          {isLoading ? '处理中...' : '预览分页'}
        </button>
        <button
          type="button"
          onClick={handleGenerate}
          disabled={!lyrics.trim() || !title.trim() || isLoading}
          className="bashi-btn-primary flex-1 rounded-2xl px-6 py-4 text-base font-semibold"
        >
          {isLoading ? '正在生成...' : '生成歌词 PPT'}
        </button>
      </div>
    </form>
  );
}
