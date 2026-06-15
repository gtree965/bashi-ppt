import { useState } from 'react';
import ImageSearchModal from './ImageSearchModal';

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

export default function OutlineEditor({ outline, onOutlineChange }) {
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [activeSlideIndex, setActiveSlideIndex] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');

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
