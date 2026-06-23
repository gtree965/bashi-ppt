import { useEffect, useMemo, useRef, useState } from 'react';
import ImageSearchModal from './ImageSearchModal';
import { mermaidToPngDataUrl } from '../utils/diagramRenderer';
import { buildMermaid, DIAGRAM_KINDS } from '../utils/diagramTemplates';
import { lengthHint, truncateSlideText } from '../utils/textConstraints';
import { auditGroundedOutline } from '../utils/groundingAudit';
import { generateSpeakerNotes } from '../api/client';

const NOTE_DURATIONS = [5, 10, 20, 30, 45, 60];
const NOTE_STYLES = [
  { id: 'classroom', label: '课堂讲解' },
  { id: 'sundayschool', label: '主日学' },
  { id: 'parents', label: '家长沟通' },
  { id: 'formal', label: '正式演讲' },
];
const STYLE_BY_SCENARIO = {
  teaching: 'classroom',
  church: 'sundayschool',
  parents: 'parents',
  general: 'formal',
};

const SLIDE_TYPE_STYLES = {
  title: 'border-[#d4a373] bg-[rgba(212,163,115,0.08)]',
  content: 'border-white/15 bg-white/5',
  conclusion: 'border-[#f4a261] bg-[rgba(244,162,97,0.08)]',
};

const SLIDE_TYPE_LABELS = {
  title: '标题页',
  content: '内容页',
  conclusion: '总结页',
};

const SLIDE_CONSTRAINTS = {
  title: {
    minPoints: 2,
    maxPoints: 4,
    maxPointLength: 20,
    maxTitleLength: 25,
  },
  content: {
    minPoints: 3,
    maxPoints: 5,
    maxPointLength: 25,
    maxTitleLength: 20,
  },
  conclusion: {
    minPoints: 2,
    maxPoints: 4,
    maxPointLength: 20,
    maxTitleLength: 15,
  },
};

export default function OutlineEditor({
  outline,
  onOutlineChange,
  scenario = 'general',
  outputLanguage = 'zh',
  article = '',
  generationMode = 'creative',
  factTable = [],
  generationAudit = null,
}) {
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [activeSlideIndex, setActiveSlideIndex] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  // Speaker-notes (讲稿) controls
  const [notesDuration, setNotesDuration] = useState(10);
  const [notesStyle, setNotesStyle] = useState(STYLE_BY_SCENARIO[scenario] || 'formal');
  const [notesBusy, setNotesBusy] = useState(false);
  const [notesError, setNotesError] = useState(null);
  const [notesNotice, setNotesNotice] = useState(null);
  const [openNotes, setOpenNotes] = useState(() => new Set());
  const [openFactMappings, setOpenFactMappings] = useState(() => new Set());
  // Track the latest outline so the async notes result can detect structural changes
  // (add/remove slide) that happened while the LLM was running, and discard if so.
  const outlineRef = useRef(outline);
  useEffect(() => {
    outlineRef.current = outline;
  }, [outline]);
  // Per-slide diagram preview, keyed by page_number: { status, url, source }.
  // `source` records the Mermaid string the preview was rendered from, so a preview
  // is treated as stale (and re-rendered) whenever the slide's diagram differs — this
  // guards against page_number reuse after add/remove renumbers slides.
  const [diagramPreviews, setDiagramPreviews] = useState({});
  // Diagram editors are collapsed by default; expanded once a slide has a diagram
  // or the user explicitly opens one. Keyed by page_number.
  const [openDiagrams, setOpenDiagrams] = useState(() => new Set());
  // Per-slide input mode: 'simple' (steps, one per line) or 'advanced' (raw Mermaid).
  const [diagramModes, setDiagramModes] = useState({});
  const currentAudit = useMemo(
    () =>
      generationMode === 'grounded'
        ? auditGroundedOutline(outline, factTable)
        : null,
    [outline, factTable, generationMode]
  );

  const renderDiagramPreview = async (pageNumber, mermaid) => {
    const source = (mermaid || '').trim();
    if (!source) {
      setDiagramPreviews((prev) => ({ ...prev, [pageNumber]: undefined }));
      return;
    }
    setDiagramPreviews((prev) => ({ ...prev, [pageNumber]: { status: 'loading', source } }));
    const url = await mermaidToPngDataUrl(source);
    setDiagramPreviews((prev) => {
      // Ignore a result whose source was superseded while rendering.
      const current = prev[pageNumber];
      if (current && current.source !== source) return prev;
      return {
        ...prev,
        [pageNumber]: url ? { status: 'ok', url, source } : { status: 'error', source },
      };
    });
  };

  // Auto-render a preview for content slides whose diagram has no up-to-date preview
  // (newly arrived from the LLM, edited by the user, or stale after a structural edit
  // renumbered slides). Debounced so editing the Mermaid textarea — which updates
  // `outline` on every keystroke — only triggers the expensive Excalidraw render once
  // the user pauses, instead of on every character.
  useEffect(() => {
    if (!outline) return undefined;
    const timer = setTimeout(() => {
      for (const slide of outline.slides) {
        if (slide.slide_type !== 'content') continue;
        const mermaid = (slide.diagram || '').trim();
        if (!mermaid) continue;
        const preview = diagramPreviews[slide.page_number];
        if (!preview || preview.source !== mermaid) {
          renderDiagramPreview(slide.page_number, mermaid);
        }
      }
    }, 600);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [outline]);

  if (!outline) {
    return (
      <div className="bashi-card rounded-[28px] p-8 text-center text-bashi-text-muted">
        大纲将在此显示 / Outline will appear here
      </div>
    );
  }

  const updateSlideTitle = (slideIndex, newTitle) => {
    const updated = { ...outline };
    updated.slides = [...updated.slides];
    updated.slides[slideIndex] = { ...updated.slides[slideIndex], title: newTitle };
    onOutlineChange(updated);
  };

  const updatePoint = (slideIndex, pointIndex, newText) => {
    const updated = { ...outline };
    updated.slides = [...updated.slides];
    const slide = { ...updated.slides[slideIndex] };
    slide.content_points = [...slide.content_points];
    slide.content_points[pointIndex] = newText;
    updated.slides[slideIndex] = slide;
    onOutlineChange(updated);
  };

  const addPoint = (slideIndex) => {
    const updated = { ...outline };
    updated.slides = [...updated.slides];
    const slide = { ...updated.slides[slideIndex] };
    const constraints = constraintsFor(slide.slide_type);
    if (slide.content_points.length >= constraints.maxPoints) return;
    slide.content_points = [...slide.content_points, '新要点'];
    updated.slides[slideIndex] = slide;
    onOutlineChange(updated);
  };

  const removePoint = (slideIndex, pointIndex) => {
    const updated = { ...outline };
    updated.slides = [...updated.slides];
    const slide = { ...updated.slides[slideIndex] };
    const constraints = constraintsFor(slide.slide_type);
    if (slide.content_points.length <= constraints.minPoints) return;
    slide.content_points = slide.content_points.filter((_, index) => index !== pointIndex);
    updated.slides[slideIndex] = slide;
    onOutlineChange(updated);
  };

  const removeSlide = (slideIndex) => {
    if (outline.slides.length <= 4) return;
    const updated = { ...outline };
    updated.slides = outline.slides.filter((_, index) => index !== slideIndex);
    updated.slides = updated.slides.map((slide, index) => ({ ...slide, page_number: index + 1 }));
    onOutlineChange(updated);
  };

  const updateSlideImage = (slideIndex, imageUrl) => {
    const updated = { ...outline };
    updated.slides = [...updated.slides];
    updated.slides[slideIndex] = { ...updated.slides[slideIndex], image_url: imageUrl || undefined };
    onOutlineChange(updated);
  };

  const patchSlide = (slideIndex, patch) => {
    const updated = { ...outline };
    updated.slides = [...updated.slides];
    updated.slides[slideIndex] = { ...updated.slides[slideIndex], ...patch };
    onOutlineChange(updated);
  };

  const updateSlideDiagram = (slideIndex, diagram) => {
    // Editing raw Mermaid makes any stored steps/template stale, so drop them —
    // otherwise a remount would default back to simple mode and overwrite the Mermaid.
    patchSlide(slideIndex, {
      diagram: diagram || undefined,
      diagram_steps: undefined,
      diagram_kind: undefined,
      diagram_layout: undefined,
    });
  };

  // Simple mode: store the user's raw step lines and (re)derive Mermaid from them,
  // honoring the slide's chosen template kind and layout.
  const updateSlideDiagramSteps = (slideIndex, stepsText) => {
    const slide = outline.slides[slideIndex];
    const kind = slide.diagram_kind || 'flow';
    const layout = slide.diagram_layout || 'TD';
    patchSlide(slideIndex, {
      diagram_steps: stepsText || undefined,
      diagram: buildMermaid(kind, stepsText, layout) || undefined,
    });
  };

  const setDiagramKind = (slideIndex, kind) => {
    const slide = outline.slides[slideIndex];
    const layout = slide.diagram_layout || 'TD';
    patchSlide(slideIndex, {
      diagram_kind: kind,
      diagram: buildMermaid(kind, slide.diagram_steps || '', layout) || undefined,
    });
  };

  const setDiagramLayout = (slideIndex, layout) => {
    const slide = outline.slides[slideIndex];
    const kind = slide.diagram_kind || 'flow';
    patchSlide(slideIndex, {
      diagram_layout: layout,
      diagram: buildMermaid(kind, slide.diagram_steps || '', layout) || undefined,
    });
  };

  const clearSlideDiagram = (slideIndex, pageNumber) => {
    patchSlide(slideIndex, {
      diagram: undefined,
      diagram_steps: undefined,
      diagram_kind: undefined,
      diagram_layout: undefined,
    });
    setOpenDiagrams((prev) => {
      const next = new Set(prev);
      next.delete(pageNumber);
      return next;
    });
  };

  const openDiagram = (pageNumber, mode = 'simple') => {
    setOpenDiagrams((prev) => new Set(prev).add(pageNumber));
    setDiagramModes((prev) => ({ ...prev, [pageNumber]: mode }));
  };

  const setDiagramMode = (pageNumber, mode) => {
    setDiagramModes((prev) => ({ ...prev, [pageNumber]: mode }));
  };

  const updateSlideNotes = (slideIndex, notes) => {
    patchSlide(slideIndex, { notes: notes || undefined });
  };

  const toggleNotesOpen = (pageNumber) => {
    setOpenNotes((prev) => {
      const next = new Set(prev);
      if (next.has(pageNumber)) next.delete(pageNumber);
      else next.add(pageNumber);
      return next;
    });
  };

  const toggleFactMappingOpen = (pageNumber) => {
    setOpenFactMappings((prev) => {
      const next = new Set(prev);
      if (next.has(pageNumber)) next.delete(pageNumber);
      else next.add(pageNumber);
      return next;
    });
  };

  const toggleSlideFact = (slideIndex, factId) => {
    const slide = outline.slides[slideIndex];
    const current = Array.isArray(slide.fact_ids) ? slide.fact_ids : [];
    const next = current.includes(factId)
      ? current.filter((id) => id !== factId)
      : [...current, factId].sort((a, b) => a - b);
    patchSlide(slideIndex, { fact_ids: next });
  };

  // Signature over exactly the fields the notes prompt consumes.
  // If any of these change during the async call — add/remove, delete-then-add, or a
  // title/point/fact-mapping edit — the returned notes no longer match and are discarded.
  const structureSignature = (o) =>
    JSON.stringify(
      o.slides.map((s) => [
        s.slide_type,
        s.title,
        s.content_points,
        s.fact_ids || [],
      ])
    );

  const handleGenerateNotes = async () => {
    if (notesBusy) return;
    if (generationMode === 'grounded' && !currentAudit?.complete) {
      setNotesError('请先完成事实对应：所有确认事实至少覆盖一次，且每个内容页都要有有效事实依据。');
      return;
    }
    setNotesBusy(true);
    setNotesError(null);
    setNotesNotice(null);
    const snapshot = structureSignature(outline);
    try {
      const data = await generateSpeakerNotes({
        outline,
        article,
        outputLanguage,
        duration: notesDuration,
        style: notesStyle,
        generationMode,
        factTable,
      });
      if (!data.success) {
        setNotesError(data.error || '讲稿生成失败');
        return;
      }
      const current = outlineRef.current;
      if (structureSignature(current) !== snapshot) {
        setNotesError('大纲在生成期间发生了变化，未写入讲稿，请重新生成。');
        return;
      }
      const notes = data.notes || [];
      onOutlineChange({
        ...current,
        slides: current.slides.map((slide, index) => ({ ...slide, notes: notes[index] || undefined })),
      });
      setOpenNotes(new Set(current.slides.map((slide) => slide.page_number)));
      if (data.warnings && data.warnings.length) {
        setNotesNotice(data.warnings.join(' '));
      }
    } catch (err) {
      setNotesError(err.message || '讲稿生成请求出错');
    } finally {
      setNotesBusy(false);
    }
  };

  const openSearch = (slideIndex, currentTitle) => {
    setActiveSlideIndex(slideIndex);
    setSearchQuery(currentTitle || '');
    setIsSearchOpen(true);
  };

  const addSlide = () => {
    if (outline.slides.length >= 15) return;
    const updated = { ...outline };
    const insertIndex = updated.slides.length - 1;
    const newSlide = {
      page_number: insertIndex + 1,
      title: '新页面',
      content_points: ['要点一', '要点二', '要点三'],
      slide_type: 'content',
      fact_ids: generationMode === 'grounded' ? [] : undefined,
    };
    updated.slides = [
      ...updated.slides.slice(0, insertIndex),
      newSlide,
      ...updated.slides.slice(insertIndex),
    ];
    updated.slides = updated.slides.map((slide, index) => ({ ...slide, page_number: index + 1 }));
    onOutlineChange(updated);
  };

  const constraintsFor = (slideType) => {
    const constraints = SLIDE_CONSTRAINTS[slideType];
    if (generationMode === 'grounded' && slideType === 'content') {
      return { ...constraints, minPoints: 1 };
    }
    return constraints;
  };

  return (
    <section className="bashi-card rounded-[28px] p-5 md:p-6">
      <div className="mb-5 flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
        <div>
          <div className="text-xs uppercase tracking-[0.24em] text-bashi-text-muted">
            Editable Outline
          </div>
          <h2 className="mt-2 text-2xl font-semibold text-bashi-text">
            大纲编辑
          </h2>
          <p className="mt-2 text-sm leading-6 text-bashi-text-secondary">
            这里可以直接修改标题、要点、页数结构。编辑完成后生成的 PPT 会按这里的内容输出。
          </p>
        </div>
        <div className="text-sm text-bashi-text-muted">
          共 {outline.slides.length} 页
        </div>
      </div>

      {/* Speaker-notes (讲稿) controls */}
      {generationMode === 'grounded' && (
        <div
          className={`mb-5 rounded-2xl border px-4 py-3 text-sm ${
            !currentAudit?.complete
              ? 'border-amber-300/30 bg-amber-400/10 text-amber-50'
              : 'border-emerald-300/25 bg-emerald-400/10 text-emerald-50'
          }`}
        >
          <div className="font-medium">严格依据材料模式</div>
          <div className="mt-1 text-xs leading-5 opacity-80">
            大纲和后续讲稿依据已确认的 {factTable.length} 条材料事实生成。
            修改大纲后，下面的事实标注覆盖会立即更新。
          </div>
          <div className="mt-2 border-t border-current/10 pt-2 text-xs leading-5 opacity-90">
            <div>
              当前事实标注覆盖：
              {currentAudit?.declared_fact_ids.length || 0} / {currentAudit?.fact_count || factTable.length}
              （{Math.round((currentAudit?.fact_coverage || 0) * 100)}%）
              {generationAudit?.retry_attempted
                ? `；生成时页数已自动修复 ${generationAudit.initial_slides} → ${generationAudit.retry_slides}`
                : ''}
            </div>
            {currentAudit?.missing_fact_ids.length > 0 && (
              <div>尚未分配到页面的事实：{currentAudit.missing_fact_ids.join('、')}</div>
            )}
            {currentAudit?.invalid_fact_ids.length > 0 && (
              <div>已失效的事实编号：{currentAudit.invalid_fact_ids.join('、')}</div>
            )}
            {currentAudit?.ungrounded_content_pages.length > 0 && (
              <div>
                未选择事实依据的内容页：
                {currentAudit.ungrounded_content_pages.join('、')}
              </div>
            )}
            <div className="mt-1 opacity-70">
              这是事实编号的结构检查，不代表系统已经判断正文语义完全正确。
            </div>
          </div>
        </div>
      )}

      {/* Speaker-notes (讲稿) controls */}
      <div className="mb-5 rounded-2xl border border-white/10 bg-black/20 p-4">
        <div className="flex flex-wrap items-center gap-x-6 gap-y-3">
          <span className="text-sm font-medium text-bashi-text">讲稿 Speaker Notes</span>
          <div className="flex items-center gap-2">
            <span className="text-xs text-bashi-text-secondary">时长</span>
            <div className="inline-flex rounded-full border border-white/10 p-0.5 text-xs">
              {NOTE_DURATIONS.map((d) => (
                <button
                  key={d}
                  type="button"
                  onClick={() => setNotesDuration(d)}
                  disabled={notesBusy}
                  className={`rounded-full px-2.5 py-1 transition disabled:opacity-40 ${notesDuration === d ? 'bg-bashi-copper/20 text-bashi-copper' : 'text-bashi-text-muted hover:text-bashi-text-secondary'}`}
                >
                  {d}分钟
                </button>
              ))}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-bashi-text-secondary">风格</span>
            <div className="inline-flex flex-wrap rounded-full border border-white/10 p-0.5 text-xs">
              {NOTE_STYLES.map((s) => (
                <button
                  key={s.id}
                  type="button"
                  onClick={() => setNotesStyle(s.id)}
                  disabled={notesBusy}
                  className={`rounded-full px-2.5 py-1 transition disabled:opacity-40 ${notesStyle === s.id ? 'bg-bashi-copper/20 text-bashi-copper' : 'text-bashi-text-muted hover:text-bashi-text-secondary'}`}
                >
                  {s.label}
                </button>
              ))}
            </div>
          </div>
          <button
            type="button"
            onClick={handleGenerateNotes}
            disabled={
              notesBusy
              || (generationMode === 'grounded' && !currentAudit?.complete)
            }
            className="bashi-btn-secondary rounded-full px-4 py-2 text-xs font-semibold disabled:opacity-40"
          >
            {notesBusy
              ? '生成讲稿中...'
              : (generationMode === 'grounded' && !currentAudit?.complete
                  ? '请先完成事实对应'
                  : '生成讲稿')}
          </button>
        </div>
        {notesError && <p className="mt-2 text-xs text-red-200">{notesError}</p>}
        {notesNotice && <p className="mt-2 text-xs text-amber-200/80">{notesNotice}</p>}
        <p className="mt-2 text-xs text-bashi-text-muted">
          为每页生成可照着讲的讲稿（要点稿，时长越长内容越充实，由讲者临场展开），导出时写入 PowerPoint 备注区；可逐页编辑。
        </p>
      </div>

      <div className="space-y-4">
        {outline.slides.map((slide, slideIndex) => {
          const constraints = constraintsFor(slide.slide_type);

          return (
            <div
              key={slideIndex}
              className={`rounded-3xl border p-4 md:p-5 ${SLIDE_TYPE_STYLES[slide.slide_type]}`}
            >
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <span className="flex h-8 w-8 items-center justify-center rounded-full bg-black/30 text-sm font-semibold text-bashi-text">
                    {slide.page_number}
                  </span>
                  <div>
                    <div className="text-sm font-medium text-bashi-text">{SLIDE_TYPE_LABELS[slide.slide_type]}</div>
                    <div className="text-xs text-bashi-text-muted">
                      标题{lengthHint(constraints.maxTitleLength, outputLanguage)}，
                      要点 {constraints.minPoints}-{constraints.maxPoints} 条
                    </div>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => removeSlide(slideIndex)}
                  className="rounded-full border border-white/10 px-3 py-1 text-xs text-bashi-text-muted transition hover:border-red-300/40 hover:text-red-200 disabled:opacity-40"
                  disabled={outline.slides.length <= 4}
                >
                  删除本页
                </button>
              </div>

              <input
                type="text"
                value={slide.title}
                onChange={(event) =>
                  updateSlideTitle(
                    slideIndex,
                    truncateSlideText(event.target.value, constraints.maxTitleLength)
                  )
                }
                className="bashi-input mt-4 w-full rounded-2xl px-4 py-3 text-lg font-medium"
              />

              <div className="mt-4 space-y-2">
                {slide.content_points.map((point, pointIndex) => (
                  <div key={pointIndex} className="flex items-center gap-3">
                    <span className="text-lg text-bashi-copper">&bull;</span>
                    <input
                      type="text"
                      value={point}
                      onChange={(event) =>
                        updatePoint(
                          slideIndex,
                          pointIndex,
                          truncateSlideText(event.target.value, constraints.maxPointLength)
                        )
                      }
                      className="bashi-input flex-1 rounded-2xl px-4 py-2.5 text-sm"
                    />
                    <button
                      type="button"
                      onClick={() => removePoint(slideIndex, pointIndex)}
                      disabled={slide.content_points.length <= constraints.minPoints}
                      className="rounded-full border border-white/10 px-3 py-2 text-xs text-bashi-text-muted transition hover:border-red-300/40 hover:text-red-200 disabled:opacity-40"
                    >
                      删除
                    </button>
                  </div>
                ))}
              </div>

              <button
                type="button"
                onClick={() => addPoint(slideIndex)}
                disabled={slide.content_points.length >= constraints.maxPoints}
                className="mt-4 rounded-full border border-bashi-border px-4 py-2 text-sm text-bashi-text-secondary transition hover:border-bashi-border-focus hover:text-bashi-text disabled:opacity-40"
              >
                + 添加要点
              </button>

              {generationMode === 'grounded' && (() => {
                const selectedIds = Array.isArray(slide.fact_ids) ? slide.fact_ids : [];
                const validSelected = selectedIds.filter((id) =>
                  factTable.some((fact) => fact.id === id)
                );
                const invalidSelected = selectedIds.filter((id) =>
                  !factTable.some((fact) => fact.id === id)
                );
                const mappingOpen = openFactMappings.has(slide.page_number);
                const requiresFact = slide.slide_type === 'content';
                return (
                  <div
                    className={`mt-4 rounded-2xl border px-4 py-3 ${
                      requiresFact && validSelected.length === 0
                        ? 'border-amber-300/30 bg-amber-400/10'
                        : 'border-white/10 bg-black/15'
                    }`}
                  >
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <div className="text-xs font-medium text-bashi-text-secondary">
                          本页事实依据
                        </div>
                        <div className="mt-1 flex flex-wrap gap-1.5">
                          {selectedIds.length > 0 ? (
                            <>
                              {validSelected.map((id) => (
                                <span
                                  key={id}
                                  className="rounded-full border border-emerald-300/25 bg-emerald-400/10 px-2 py-0.5 text-xs text-emerald-100"
                                >
                                  #{id}
                                </span>
                              ))}
                              {invalidSelected.map((id) => (
                                <span
                                  key={`invalid-${id}`}
                                  className="rounded-full border border-red-300/30 bg-red-400/10 px-2 py-0.5 text-xs text-red-100"
                                >
                                  无效 #{id}
                                </span>
                              ))}
                            </>
                          ) : (
                            <span className="text-xs text-amber-100/80">
                              {requiresFact ? '内容页必须至少选择一条事实' : '尚未选择事实'}
                            </span>
                          )}
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() => toggleFactMappingOpen(slide.page_number)}
                        className="rounded-full border border-bashi-border px-3 py-1.5 text-xs text-bashi-text-secondary transition hover:border-bashi-copper hover:text-bashi-copper"
                      >
                        {mappingOpen ? '收起事实列表' : '调整事实对应'}
                      </button>
                    </div>

                    {invalidSelected.length > 0 && (
                      <button
                        type="button"
                        onClick={() => patchSlide(slideIndex, { fact_ids: validSelected })}
                        className="mt-2 text-xs font-medium text-red-200 transition hover:text-white"
                      >
                        清理本页无效编号
                      </button>
                    )}

                    {mappingOpen && (
                      <div className="mt-3 max-h-64 space-y-2 overflow-y-auto border-t border-white/10 pt-3">
                        {factTable.map((fact) => {
                          const checked = selectedIds.includes(fact.id);
                          return (
                            <label
                              key={fact.id}
                              className={`flex cursor-pointer items-start gap-3 rounded-xl border px-3 py-2 text-xs leading-5 transition ${
                                checked
                                  ? 'border-emerald-300/25 bg-emerald-400/10 text-emerald-50'
                                  : 'border-white/10 bg-black/15 text-bashi-text-secondary'
                              }`}
                            >
                              <input
                                type="checkbox"
                                checked={checked}
                                onChange={() => toggleSlideFact(slideIndex, fact.id)}
                                className="mt-1 accent-bashi-copper"
                              />
                              <span>
                                <span className="mr-1 font-semibold">#{fact.id}</span>
                                {fact.text}
                              </span>
                            </label>
                          );
                        })}
                      </div>
                    )}
                    <p className="mt-2 text-xs leading-5 text-bashi-text-muted">
                      请人工确认本页文字确实表达了所选事实；系统这里只检查编号覆盖关系。
                    </p>
                  </div>
                );
              })()}

              {/* Optional Image for content slide */}
              {slide.slide_type === 'content' && (
                <div className="mt-4 border-t border-white/5 pt-4">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-bashi-text-secondary">配图 Image</span>
                  </div>
                  <div className="mt-2 flex items-center gap-4">
                    {slide.image_url ? (
                      <>
                        <div className="relative h-16 w-28 overflow-hidden rounded-xl border border-white/10 bg-black/40">
                          <img
                            src={slide.image_url}
                            alt="Selected slide graphic"
                            className="h-full w-full object-cover"
                          />
                        </div>
                        <div className="flex gap-2">
                          <button
                            type="button"
                            onClick={() => openSearch(slideIndex, slide.title)}
                            className="rounded-full border border-white/10 px-3.5 py-1.5 text-xs text-bashi-text-secondary transition hover:border-bashi-border-focus hover:text-bashi-text"
                          >
                            更换配图
                          </button>
                          <button
                            type="button"
                            onClick={() => updateSlideImage(slideIndex, null)}
                            className="rounded-full border border-white/10 px-3.5 py-1.5 text-xs text-bashi-text-muted transition hover:border-red-300/40 hover:text-red-200"
                          >
                            删除配图
                          </button>
                        </div>
                      </>
                    ) : (
                      <button
                        type="button"
                        onClick={() => openSearch(slideIndex, slide.title)}
                        className="flex items-center gap-1.5 rounded-full border border-dashed border-bashi-border px-4 py-2 text-xs text-bashi-text-secondary transition hover:border-bashi-border-focus hover:text-bashi-text"
                      >
                        🖼️ + 添加配图
                      </button>
                    )}
                  </div>
                </div>
              )}

              {/* Optional hand-drawn diagram for content slide (collapsed until added) */}
              {slide.slide_type === 'content' && (() => {
                const pageNumber = slide.page_number;
                const hasDiagram = !!(slide.diagram || '').trim() || !!(slide.diagram_steps || '').trim();
                const isOpen = hasDiagram || openDiagrams.has(pageNumber);

                if (!isOpen) {
                  return (
                    <div className="mt-4 border-t border-white/5 pt-4">
                      <button
                        type="button"
                        onClick={() => openDiagram(pageNumber, 'simple')}
                        className="flex items-center gap-1.5 rounded-full border border-dashed border-bashi-border px-4 py-2 text-xs text-bashi-text-secondary transition hover:border-bashi-border-focus hover:text-bashi-text"
                      >
                        📈 + 添加图示
                      </button>
                    </div>
                  );
                }

                // LLM-supplied diagrams arrive as Mermaid (no steps) → default to advanced.
                const mode = diagramModes[pageNumber] ?? (slide.diagram && !slide.diagram_steps ? 'advanced' : 'simple');
                const preview = diagramPreviews[pageNumber];
                const kind = slide.diagram_kind || 'flow';
                const layout = slide.diagram_layout || 'TD';
                const kindMeta = DIAGRAM_KINDS.find((k) => k.id === kind) || DIAGRAM_KINDS[0];

                return (
                  <div className="mt-4 border-t border-white/5 pt-4">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="text-xs text-bashi-text-secondary">手绘图示 Diagram</span>
                      <div className="flex items-center gap-2">
                        <div className="inline-flex rounded-full border border-white/10 p-0.5 text-xs">
                          <button
                            type="button"
                            onClick={() => setDiagramMode(pageNumber, 'simple')}
                            className={`rounded-full px-2.5 py-1 transition ${mode === 'simple' ? 'bg-bashi-copper/20 text-bashi-copper' : 'text-bashi-text-muted hover:text-bashi-text-secondary'}`}
                          >
                            步骤
                          </button>
                          <button
                            type="button"
                            onClick={() => setDiagramMode(pageNumber, 'advanced')}
                            className={`rounded-full px-2.5 py-1 transition ${mode === 'advanced' ? 'bg-bashi-copper/20 text-bashi-copper' : 'text-bashi-text-muted hover:text-bashi-text-secondary'}`}
                          >
                            Mermaid
                          </button>
                        </div>
                        <button
                          type="button"
                          onClick={() => clearSlideDiagram(slideIndex, pageNumber)}
                          className="rounded-full border border-white/10 px-3 py-1 text-xs text-bashi-text-muted transition hover:border-red-300/40 hover:text-red-200"
                        >
                          删除
                        </button>
                      </div>
                    </div>

                    {mode === 'simple' ? (
                      <>
                        <div className="mt-2 flex flex-wrap items-center gap-2">
                          <div className="inline-flex flex-wrap rounded-full border border-white/10 p-0.5 text-xs">
                            {DIAGRAM_KINDS.map((k) => (
                              <button
                                key={k.id}
                                type="button"
                                onClick={() => setDiagramKind(slideIndex, k.id)}
                                className={`rounded-full px-2.5 py-1 transition ${kind === k.id ? 'bg-bashi-copper/20 text-bashi-copper' : 'text-bashi-text-muted hover:text-bashi-text-secondary'}`}
                              >
                                {k.label}
                              </button>
                            ))}
                          </div>
                          {kindMeta.hasLayout && (
                            <div className="inline-flex rounded-full border border-white/10 p-0.5 text-xs">
                              {['TD', 'LR'].map((lay) => (
                                <button
                                  key={lay}
                                  type="button"
                                  onClick={() => setDiagramLayout(slideIndex, lay)}
                                  className={`rounded-full px-2.5 py-1 transition ${layout === lay ? 'bg-bashi-copper/20 text-bashi-copper' : 'text-bashi-text-muted hover:text-bashi-text-secondary'}`}
                                >
                                  {lay === 'TD' ? '竖向' : '横向'}
                                </button>
                              ))}
                            </div>
                          )}
                        </div>
                        <textarea
                          value={slide.diagram_steps || ''}
                          onChange={(event) => updateSlideDiagramSteps(slideIndex, event.target.value)}
                          placeholder={kindMeta.placeholder}
                          rows={4}
                          className="bashi-input mt-2 w-full rounded-2xl px-4 py-2.5 text-sm"
                        />
                        <p className="mt-1 text-xs text-bashi-text-muted">{kindMeta.hint}</p>
                        {slide.diagram && !slide.diagram_steps && (
                          <p className="mt-1 text-xs text-amber-200/80">
                            当前图示为 Mermaid 代码；在此输入步骤会将其替换。
                          </p>
                        )}
                      </>
                    ) : (
                      <textarea
                        value={slide.diagram || ''}
                        onChange={(event) => updateSlideDiagram(slideIndex, event.target.value)}
                        placeholder="flowchart TD; A[输入] --> B[处理] --> C[输出]"
                        rows={4}
                        className="bashi-input mt-2 w-full rounded-2xl px-4 py-2.5 font-mono text-xs"
                      />
                    )}

                    {slide.image_url && (slide.diagram || '').trim() && (
                      <p className="mt-2 text-xs text-amber-200/80">
                        该页已有配图，导出时将优先使用配图，图示不会显示。
                      </p>
                    )}

                    {(() => {
                      // Only trust a preview rendered from the slide's current Mermaid;
                      // a mismatch means it's stale and the effect will re-render it.
                      if (!preview || preview.source !== (slide.diagram || '').trim()) return null;
                      if (preview.status === 'loading') {
                        return <p className="mt-2 text-xs text-bashi-text-muted">渲染中…</p>;
                      }
                      if (preview.status === 'error') {
                        return <p className="mt-2 text-xs text-red-200">图示语法有误，无法渲染。</p>;
                      }
                      return (
                        <div className="mt-2 overflow-hidden rounded-xl border border-white/10 bg-white p-2">
                          <img src={preview.url} alt="Diagram preview" className="mx-auto max-h-48 object-contain" />
                        </div>
                      );
                    })()}
                  </div>
                );
              })()}

              {/* Speaker notes for this slide (all slide types) */}
              {(() => {
                const pageNumber = slide.page_number;
                const hasNotes = !!(slide.notes || '').trim();
                const isOpen = hasNotes || openNotes.has(pageNumber);
                if (!isOpen) {
                  return (
                    <div className="mt-4 border-t border-white/5 pt-4">
                      <button
                        type="button"
                        onClick={() => toggleNotesOpen(pageNumber)}
                        className="flex items-center gap-1.5 rounded-full border border-dashed border-bashi-border px-4 py-2 text-xs text-bashi-text-secondary transition hover:border-bashi-border-focus hover:text-bashi-text"
                      >
                        📝 + 讲稿
                      </button>
                    </div>
                  );
                }
                return (
                  <div className="mt-4 border-t border-white/5 pt-4">
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-bashi-text-secondary">讲稿 Notes</span>
                      <button
                        type="button"
                        onClick={() => {
                          updateSlideNotes(slideIndex, '');
                          setOpenNotes((prev) => {
                            const next = new Set(prev);
                            next.delete(pageNumber);
                            return next;
                          });
                        }}
                        className="rounded-full border border-white/10 px-3 py-1 text-xs text-bashi-text-muted transition hover:border-red-300/40 hover:text-red-200"
                      >
                        清除
                      </button>
                    </div>
                    <textarea
                      value={slide.notes || ''}
                      onChange={(event) => updateSlideNotes(slideIndex, event.target.value)}
                      rows={3}
                      placeholder="这一页要讲的话…"
                      className="bashi-input mt-2 w-full rounded-2xl px-4 py-2.5 text-sm leading-6"
                    />
                  </div>
                );
              })()}
            </div>
          );
        })}
      </div>

      <button
        type="button"
        onClick={addSlide}
        disabled={outline.slides.length >= 15}
        className="mt-5 w-full rounded-3xl border border-dashed border-bashi-border px-6 py-4 text-bashi-text-secondary transition hover:border-bashi-border-focus hover:text-bashi-text disabled:opacity-40"
      >
        + 添加幻灯片
      </button>
      <ImageSearchModal
        isOpen={isSearchOpen}
        onClose={() => setIsSearchOpen(false)}
        onSelectImage={(imageUrl) => updateSlideImage(activeSlideIndex, imageUrl)}
        initialQuery={searchQuery}
      />
    </section>
  );
}
