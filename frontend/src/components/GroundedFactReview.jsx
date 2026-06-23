import { useState } from 'react';

const MAX_FACTS = 80;

export default function GroundedFactReview({
  topic,
  facts,
  onConfirm,
  onBack,
  isBusy,
}) {
  const [items, setItems] = useState(() =>
    facts.map((fact) => ({
      key: fact.id,
      checked: true,
      text: fact.text,
    }))
  );

  const selectedItems = items.filter((item) => item.checked && item.text.trim());
  const canConfirm = selectedItems.length > 0 && !isBusy;

  const updateItem = (key, patch) => {
    setItems((current) =>
      current.map((item) => (item.key === key ? { ...item, ...patch } : item))
    );
  };

  const handleAddFact = () => {
    if (items.length >= MAX_FACTS) return;
    const nextKey = items.reduce((highest, item) => Math.max(highest, item.key), 0) + 1;
    setItems((current) => [
      ...current,
      { key: nextKey, checked: true, text: '' },
    ]);
  };

  const handleConfirm = () => {
    if (!canConfirm) return;
    onConfirm(
      selectedItems.map((item, index) => ({
        id: index + 1,
        text: item.text.trim(),
      }))
    );
  };

  const allSelected = items.length > 0 && items.every((item) => item.checked);

  return (
    <section className="bashi-card mx-auto max-w-4xl rounded-[28px] p-6 md:p-8">
      <div className="flex flex-col gap-4 border-b border-white/10 pb-6 md:flex-row md:items-start md:justify-between">
        <div>
          <div className="inline-flex items-center rounded-full border border-bashi-copper/40 bg-bashi-copper/10 px-3 py-1 text-xs font-medium text-bashi-copper">
            严格材料模式 · 事实确认
          </div>
          <h2 className="mt-4 text-2xl font-semibold text-bashi-text">
            请确认 PPT 必须保留的事实
          </h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-bashi-text-secondary">
            这些事实将成为大纲和讲稿的内容边界。可取消不重要的项目，也可直接修改或补充；
            你确认后的文字会被视为可靠事实。
          </p>
          {topic && (
            <p className="mt-2 text-xs text-bashi-text-muted">
              当前主题：{topic}
            </p>
          )}
        </div>
        <div className="shrink-0 rounded-2xl border border-bashi-border bg-black/20 px-4 py-3 text-sm">
          <div className="text-bashi-text-muted">已选择</div>
          <div className="mt-1 text-xl font-semibold text-bashi-copper">
            {selectedItems.length} / {items.length}
          </div>
        </div>
      </div>

      <div className="mt-5 rounded-2xl border border-amber-300/25 bg-amber-400/10 px-4 py-3 text-xs leading-5 text-amber-50/90">
        请特别核对数字、日期、地点、责任主体以及“不得 / 必须 / 仅限”等限制性表述。
        取消勾选代表不要求 AI 在 PPT 中覆盖该事实，并不会修改原始材料。
      </div>

      <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
        <button
          type="button"
          onClick={() =>
            setItems((current) =>
              current.map((item) => ({ ...item, checked: !allSelected }))
            )
          }
          disabled={isBusy || items.length === 0}
          className="text-sm font-medium text-bashi-copper transition hover:text-bashi-text disabled:opacity-40"
        >
          {allSelected ? '全部取消' : '全部选择'}
        </button>
        <button
          type="button"
          onClick={handleAddFact}
          disabled={isBusy || items.length >= MAX_FACTS}
          className="rounded-full border border-bashi-border px-4 py-2 text-sm text-bashi-text-secondary transition hover:border-bashi-copper hover:text-bashi-copper disabled:opacity-40"
        >
          + 补充事实
        </button>
      </div>

      <div className="mt-4 space-y-3">
        {items.map((item, index) => (
          <div
            key={item.key}
            className={`rounded-2xl border p-4 transition ${
              item.checked
                ? 'border-bashi-copper/35 bg-bashi-copper/5'
                : 'border-bashi-border bg-black/15 opacity-65'
            }`}
          >
            <div className="flex items-start gap-3">
              <input
                type="checkbox"
                checked={item.checked}
                onChange={(event) =>
                  updateItem(item.key, { checked: event.target.checked })
                }
                disabled={isBusy}
                aria-label={`选择事实 ${index + 1}`}
                className="mt-3 accent-bashi-copper"
              />
              <div className="min-w-0 flex-1">
                <label className="mb-2 block text-xs font-medium text-bashi-text-muted">
                  事实 {index + 1}
                </label>
                <textarea
                  value={item.text}
                  onChange={(event) =>
                    updateItem(item.key, { text: event.target.value.slice(0, 1000) })
                  }
                  disabled={isBusy}
                  rows={Math.min(5, Math.max(2, Math.ceil(item.text.length / 48)))}
                  placeholder="输入必须保留的事实"
                  className="bashi-input w-full resize-y rounded-xl px-3 py-2 text-sm leading-6"
                />
              </div>
            </div>
          </div>
        ))}
      </div>

      {selectedItems.length === 0 && (
        <p className="mt-4 text-sm text-red-200">
          请至少选择并填写一条事实，或返回改用“允许教学扩展”。
        </p>
      )}

      <div className="mt-7 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
        <button
          type="button"
          onClick={onBack}
          disabled={isBusy}
          className="rounded-2xl border border-bashi-border px-5 py-3 text-sm font-medium text-bashi-text-secondary transition hover:border-bashi-copper hover:text-bashi-text disabled:opacity-40"
        >
          返回修改材料
        </button>
        <button
          type="button"
          onClick={handleConfirm}
          disabled={!canConfirm}
          className="bashi-btn-primary rounded-2xl px-6 py-3 text-sm font-semibold"
        >
          {isBusy ? '正在按确认事实生成大纲…' : `确认 ${selectedItems.length} 条事实并生成大纲`}
        </button>
      </div>

      {isBusy && (
        <div className="mt-5 rounded-2xl border border-bashi-border bg-black/25 px-4 py-4">
          <div className="bashi-progress-track">
            <div className="bashi-progress-indeterminate" />
          </div>
          <p className="mt-3 text-sm leading-6 text-bashi-text-secondary">
            AI 只会围绕你确认的事实组织内容。请保留此页面，生成完成后将进入可编辑大纲。
          </p>
        </div>
      )}
    </section>
  );
}
