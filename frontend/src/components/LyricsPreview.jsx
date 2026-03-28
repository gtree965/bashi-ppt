const THEME_STYLES = {
  classic_dark: { bg: '#000000', text: '#FFFFFF', chorus: '#FFD700', secondary: '#B0BEC5' },
  deep_blue: { bg: '#0C1445', text: '#FFFFFF', chorus: '#81D4FA', secondary: '#90CAF9' },
  warm_dark: { bg: '#1A0A00', text: '#FFF8E1', chorus: '#FFB74D', secondary: '#D7CCC8' },
};

function SlideContent({ slide, colors }) {
  if (slide.type === 'title' || slide.type === 'amen') {
    return (
      <div
        className="truncate text-center leading-snug"
        style={{
          color: colors.text,
          fontSize: slide.type === 'title' ? '14px' : '16px',
          fontWeight: 700,
          maxWidth: '220px',
        }}
      >
        {slide.lines[0]}
      </div>
    );
  }

  // Bilingual slide with pairs
  if (slide.pairs) {
    return slide.pairs.map((pair, i) => (
      <div key={i} className="mb-0.5">
        <div
          className="truncate text-center leading-snug"
          style={{
            color: slide.is_chorus ? colors.chorus : colors.text,
            fontSize: '11px',
            fontWeight: 600,
            maxWidth: '220px',
          }}
        >
          {pair.primary}
        </div>
        {pair.secondary && (
          <div
            className="truncate text-center leading-snug"
            style={{
              color: colors.secondary,
              fontSize: '9px',
              fontWeight: 400,
              maxWidth: '220px',
            }}
          >
            {pair.secondary}
          </div>
        )}
      </div>
    ));
  }

  // Single-language slide
  return slide.lines.map((line, i) => (
    <div
      key={i}
      className="truncate text-center leading-snug"
      style={{
        color: slide.is_chorus ? colors.chorus : colors.text,
        fontSize: '11px',
        fontWeight: 600,
        maxWidth: '220px',
      }}
    >
      {line}
    </div>
  ));
}

export default function LyricsPreview({ slides, theme, totalPages }) {
  if (!slides || slides.length === 0) return null;

  const colors = THEME_STYLES[theme] || THEME_STYLES.classic_dark;

  return (
    <div className="bashi-card mx-auto max-w-3xl rounded-[28px] p-6 md:p-8">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-lg font-semibold text-bashi-text">
          分页预览
        </h3>
        <span className="text-sm text-bashi-text-muted">
          共 {totalPages} 页
        </span>
      </div>

      <div className="flex gap-4 overflow-x-auto pb-4">
        {slides.map((slide) => (
          <div
            key={slide.page}
            className="flex-none"
          >
            <div
              className="flex h-[135px] w-[240px] flex-col items-center justify-center rounded-xl border border-white/10 px-4 py-3"
              style={{ backgroundColor: colors.bg }}
            >
              <SlideContent slide={slide} colors={colors} />
            </div>
            <div className="mt-2 text-center text-xs text-bashi-text-muted">
              {slide.type === 'title' ? '标题' : slide.type === 'amen' ? '阿们' : `第 ${slide.page} 页`}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
