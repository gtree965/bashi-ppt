const TEMPLATE_INFO = {
  teaching: {
    name: '课堂教学',
    nameEn: 'Classroom',
    color: '#d4a373',
    accent: '#f4a261',
    bg: '#12151a',
    description: '课堂教学、家长说明和通用主题会自动使用这个模板。',
  },
  church: {
    name: '教会讲座',
    nameEn: 'Church',
    color: '#d4a373',
    accent: '#e76f51',
    bg: '#12151a',
    description: '教会场景会自动使用更适合讲章与主日学内容的模板。',
  },
};

const SCENARIO_LABELS = {
  teaching: '课堂教学',
  church: '教会讲座',
  parents: '家长说明',
  general: '通用',
};

export default function TemplateSelector({ scenario, selected }) {
  const template = TEMPLATE_INFO[selected] || TEMPLATE_INFO.teaching;

  return (
    <section className="bashi-card rounded-[28px] p-5 md:p-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <div className="text-xs uppercase tracking-[0.24em] text-bashi-text-muted">
            Auto Theme Mapping
          </div>
          <h2 className="mt-2 text-xl font-semibold text-bashi-text">
            已自动匹配模板，不再手动二选一
          </h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-bashi-text-secondary">
            当前场景是 {SCENARIO_LABELS[scenario] || '课堂教学'}，所以系统自动使用
            {' '}
            {template.name}
            {' '}
            模板。这样可以减少一个容易让人困惑的步骤。
          </p>
        </div>

        <div className="rounded-2xl border border-bashi-border bg-black/20 p-4 md:min-w-[280px]">
          <div className="flex items-center gap-3">
            <div className="flex gap-2">
              <div className="h-10 w-4 rounded-full" style={{ backgroundColor: template.color }} />
              <div className="h-10 w-4 rounded-full" style={{ backgroundColor: template.accent }} />
              <div className="h-10 w-4 rounded-full border border-white/10" style={{ backgroundColor: template.bg }} />
            </div>
            <div>
              <div className="font-medium text-bashi-text">{template.name}</div>
              <div className="text-sm text-bashi-text-secondary">{template.nameEn}</div>
            </div>
          </div>
          <div className="mt-3 text-sm leading-6 text-bashi-text-muted">
            {template.description}
          </div>
        </div>
      </div>
    </section>
  );
}
