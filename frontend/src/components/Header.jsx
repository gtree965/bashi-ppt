export default function Header() {
  return (
    <header className="pb-2 pt-4 text-center md:pt-8">
      <div className="inline-flex items-center rounded-full border border-bashi-border bg-white/5 px-4 py-1 text-xs uppercase tracking-[0.28em] text-bashi-text-muted">
        Bashi Creation Suite
      </div>

      <div className="mx-auto mt-5 w-full max-w-[560px] px-2">
        <img
          src="/Bashi_PPT_logo.png"
          alt="巴适PPT标志：熔炉式幻灯片工坊"
          className="bashi-brand-logo h-auto w-full rounded-2xl"
          width="1365"
          height="768"
          decoding="async"
          fetchPriority="high"
        />
      </div>

      <h1 className="bashi-gradient-text mt-4 text-5xl font-bold md:text-7xl">
        巴适PPT
      </h1>

      <p className="mt-3 text-lg text-bashi-text-secondary md:text-xl">
        Bashi PPT · 本地 AI 幻灯片生成器
      </p>

      <p className="mx-auto mt-4 max-w-3xl text-sm leading-7 text-bashi-text-muted md:text-base">
        把教学、教会和家长沟通内容更快地整理成可编辑 PPT。
      </p>
    </header>
  );
}
