import { useEffect, useState } from 'react';
import ImageSearchModal from './ImageSearchModal';
import { mermaidToPngDataUrl } from '../utils/diagramRenderer';

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

// Build a top-down Mermaid flowchart from a plain list of steps (one per line),
// so users can type "数据输入 / 统计模型 / 特征提取" instead of Mermaid syntax.
function stepsToMermaid(stepsText) {
  const lines = (stepsText || '')
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean);
  if (lines.length === 0) return '';
  // Double quotes would break the quoted label; swap for safe single quotes.
  const node = (i) => `n${i}["${lines[i].replace(/"/g, "'")}"]`;
  if (lines.length === 1) return `flowchart TD\n  ${node(0)}`;
  let body = '';
  for (let i = 0; i < lines.length - 1; i++) {
    body += `  ${node(i)} --> ${node(i + 1)}\n`;
  }
  return `flowchart TD\n${body}`.trimEnd();
}

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

export default function OutlineEditor({ outline, onOutlineChange }) {
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [activeSlideIndex, setActiveSlideIndex] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
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
    const constraints = SLIDE_CONSTRAINTS[slide.slide_type];
    if (slide.content_points.length >= constraints.maxPoints) return;
    slide.content_points = [...slide.content_points, '新要点'];
    updated.slides[slideIndex] = slide;
    onOutlineChange(updated);
  };

  const removePoint = (slideIndex, pointIndex) => {
    const updated = { ...outline };
    updated.slides = [...updated.slides];
    const slide = { ...updated.slides[slideIndex] };
    const constraints = SLIDE_CONSTRAINTS[slide.slide_type];
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

  const updateSlideDiagram = (slideIndex, diagram) => {
    const updated = { ...outline };
    updated.slides = [...updated.slides];
    // Editing raw Mermaid makes any stored steps stale, so drop them — otherwise a
    // remount would default back to simple mode and show/overwrite outdated steps.
    updated.slides[slideIndex] = {
      ...updated.slides[slideIndex],
      diagram: diagram || undefined,
      diagram_steps: undefined,
    };
    onOutlineChange(updated);
  };

  // Simple mode: store the user's raw step lines and (re)derive the Mermaid from them.
  const updateSlideDiagramSteps = (slideIndex, stepsText) => {
    const updated = { ...outline };
    updated.slides = [...updated.slides];
    updated.slides[slideIndex] = {
      ...updated.slides[slideIndex],
      diagram_steps: stepsText || undefined,
      diagram: stepsToMermaid(stepsText) || undefined,
    };
    onOutlineChange(updated);
  };

  const clearSlideDiagram = (slideIndex, pageNumber) => {
    const updated = { ...outline };
    updated.slides = [...updated.slides];
    updated.slides[slideIndex] = {
      ...updated.slides[slideIndex],
      diagram: undefined,
      diagram_steps: undefined,
    };
    onOutlineChange(updated);
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
    };
    updated.slides = [
      ...updated.slides.slice(0, insertIndex),
      newSlide,
      ...updated.slides.slice(insertIndex),
    ];
    updated.slides = updated.slides.map((slide, index) => ({ ...slide, page_number: index + 1 }));
    onOutlineChange(updated);
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

      <div className="space-y-4">
        {outline.slides.map((slide, slideIndex) => {
          const constraints = SLIDE_CONSTRAINTS[slide.slide_type];

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
                      标题最多 {constraints.maxTitleLength} 字，要点 {constraints.minPoints}-{constraints.maxPoints} 条
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
                onChange={(event) => updateSlideTitle(slideIndex, event.target.value)}
                maxLength={constraints.maxTitleLength}
                className="bashi-input mt-4 w-full rounded-2xl px-4 py-3 text-lg font-medium"
              />

              <div className="mt-4 space-y-2">
                {slide.content_points.map((point, pointIndex) => (
                  <div key={pointIndex} className="flex items-center gap-3">
                    <span className="text-lg text-bashi-copper">&bull;</span>
                    <input
                      type="text"
                      value={point}
                      onChange={(event) => updatePoint(slideIndex, pointIndex, event.target.value)}
                      maxLength={constraints.maxPointLength}
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
                        <textarea
                          value={slide.diagram_steps || ''}
                          onChange={(event) => updateSlideDiagramSteps(slideIndex, event.target.value)}
                          placeholder={'每行一个步骤，自动生成流程图：\n数据输入\n统计模型\n特征提取\n分类结果'}
                          rows={4}
                          className="bashi-input mt-2 w-full rounded-2xl px-4 py-2.5 text-sm"
                        />
                        <p className="mt-1 text-xs text-bashi-text-muted">
                          每行一个步骤，按顺序自动连成自上而下的流程图。
                        </p>
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
