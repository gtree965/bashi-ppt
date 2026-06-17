import { useState } from 'react';

// Review screen shown when the user chose "draft article first": shows the AI article
// (editable) and a preview of the outline derived from it, with a correction prompt to
// regenerate and a confirm button to proceed to outline editing.
export default function DraftReview({ article, onArticleChange, outline, onRefine, onConfirm, isBusy }) {
  const [correction, setCorrection] = useState('');

  const submitRefine = () => {
    const text = correction.trim();
    if (!text || isBusy) return;
    onRefine(text);
    setCorrection('');
  };

  return (
    <section className="bashi-card rounded-[28px] p-5 md:p-6">
      <div className="mb-4">
        <div className="text-xs uppercase tracking-[0.24em] text-bashi-text-muted">Draft Article</div>
        <h2 className="mt-2 text-2xl font-semibold text-bashi-text">AI 生成的参考文章</h2>
        <p className="mt-2 text-sm leading-6 text-bashi-text-secondary">
          先确认方向：可直接修改下面的文章，或在“修改方向”里告诉 AI 怎么调整，然后重新生成。满意后再进入大纲编辑。
        </p>
      </div>

      <textarea
        value={article}
        onChange={(event) => onArticleChange(event.target.value)}
        disabled={isBusy}
        rows={12}
        className="bashi-input w-full rounded-2xl px-4 py-3 text-sm leading-7"
      />

      {/* Correction prompt */}
      <div className="mt-4">
        <label className="mb-2 block text-sm font-medium text-bashi-text">修改方向 Correction（可选）</label>
        <div className="flex flex-col gap-2 sm:flex-row">
          <input
            type="text"
            value={correction}
            onChange={(event) => setCorrection(event.target.value)}
            onKeyDown={(event) => { if (event.key === 'Enter') { event.preventDefault(); submitRefine(); } }}
            placeholder="例如：不是这个方向，请改成面向小学生的入门课"
            disabled={isBusy}
            className="bashi-input flex-1 rounded-2xl px-4 py-3 text-sm"
          />
          <button
            type="button"
            onClick={submitRefine}
            disabled={isBusy || !correction.trim()}
            className="bashi-btn-secondary rounded-2xl px-5 py-3 text-sm font-semibold disabled:opacity-40"
          >
            {isBusy ? '生成中...' : '重新生成'}
          </button>
        </div>
      </div>

      {/* Outline preview (read-only; full editing happens in the next step) */}
      <div className="mt-6 rounded-2xl border border-white/10 bg-black/20 p-4">
        <h3 className="text-sm font-medium text-bashi-text">PPT 大纲预览 / Outline（{outline?.slides?.length || 0} 页）</h3>
        <ol className="mt-3 space-y-3">
          {outline?.slides?.map((slide) => (
            <li key={slide.page_number} className="text-sm">
              <span className="text-bashi-text-muted">{slide.page_number}.</span>{' '}
              <span className="font-medium text-bashi-text">{slide.title}</span>
              <ul className="mt-1 list-disc pl-8 text-bashi-text-secondary">
                {slide.content_points?.map((point, index) => (
                  <li key={index}>{point}</li>
                ))}
              </ul>
            </li>
          ))}
        </ol>
      </div>

      <button
        type="button"
        onClick={onConfirm}
        disabled={isBusy}
        className="bashi-btn-primary mt-6 w-full rounded-2xl px-6 py-4 text-lg font-semibold disabled:opacity-40"
      >
        确认并继续编辑大纲 →
      </button>
    </section>
  );
}
