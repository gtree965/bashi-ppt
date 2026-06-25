const SCENARIO_LABEL = {
  teaching: '课堂',
  church: '教会',
  parents: '家长',
  general: '通用',
};

const MODE_LABEL = {
  grounded: '严格依据材料',
  creative: '教学创作',
};

function formatRelativeTime(iso) {
  if (!iso) return '';
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return '';
  const diff = Date.now() - then;
  const min = Math.floor(diff / 60000);
  if (min < 1) return '刚刚';
  if (min < 60) return `${min} 分钟前`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr} 小时前`;
  const day = Math.floor(hr / 24);
  if (day < 30) return `${day} 天前`;
  return new Date(iso).toLocaleDateString();
}

export function ProjectRow({ project, onOpen }) {
  const summary = project.summary || {};
  return (
    <button
      type="button"
      onClick={() => onOpen(project.id)}
      className="group flex w-full items-center justify-between gap-3 rounded-xl border border-bashi-border bg-black/20 px-4 py-3 text-left transition hover:border-bashi-copper hover:bg-black/30"
    >
      <div className="min-w-0 flex-1">
        <div className="truncate text-sm font-medium text-bashi-text">
          {project.title || summary.topic || '未命名项目'}
        </div>
        <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-bashi-text-muted">
          {summary.scenario && (
            <span className="rounded-full bg-white/5 px-2 py-0.5">
              {SCENARIO_LABEL[summary.scenario] || summary.scenario}
            </span>
          )}
          {summary.generation_mode && (
            <span className="rounded-full bg-bashi-copper/15 px-2 py-0.5 text-bashi-copper">
              {MODE_LABEL[summary.generation_mode] || summary.generation_mode}
            </span>
          )}
          {summary.slide_count > 0 && <span>{summary.slide_count} 页</span>}
          <span>· {formatRelativeTime(project.updated_at)}</span>
        </div>
      </div>
      <span className="shrink-0 text-xs text-bashi-text-muted transition group-hover:text-bashi-copper">
        继续编辑 →
      </span>
    </button>
  );
}

export default function RecentProjects({ projects = [], onOpen, onBrowseAll }) {
  if (!projects.length) return null;

  return (
    <section className="bashi-card rounded-[28px] p-5 md:p-6">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-bashi-text">最近的项目</h2>
        <button
          type="button"
          onClick={onBrowseAll}
          className="text-xs text-bashi-copper transition hover:underline"
        >
          📂 浏览全部过往项目
        </button>
      </div>
      <div className="flex flex-col gap-2">
        {projects.map((project) => (
          <ProjectRow key={project.id} project={project} onOpen={onOpen} />
        ))}
      </div>
      <p className="mt-3 text-[11px] leading-5 text-bashi-text-muted">
        项目自动保存在本机 <code>projects/</code> 文件夹，绝不上传。
      </p>
    </section>
  );
}
