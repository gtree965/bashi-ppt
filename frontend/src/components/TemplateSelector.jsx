const TEMPLATE_INFO = {
  teaching: {
    name: '课堂教学',
    nameEn: 'Classroom',
    description: '适用于编程教学及通用课堂展示。',
  },
  church: {
    name: '教会讲座',
    nameEn: 'Church',
    description: '适用于查经班、主日学、教会讲章。',
  },
  professional: {
    name: '商务会议',
    nameEn: 'Professional',
    description: '适用于说明会、工作总结及商务汇报。',
  },
  default: {
    name: '默认简约',
    nameEn: 'Default',
    description: '适用于常规及其他通用演示文稿。',
  },
};

const SCENARIO_LABELS = {
  teaching: '课堂教学',
  church: '教会讲座',
  parents: '家长说明',
  general: '通用',
};

const THEME_OPTIONS = {
  clean_blue: {
    name: '简约蓝',
    nameEn: 'Clean Blue',
    color: '#1A5276',
    accent: '#2E86C1',
    bg: '#FFFFFF',
    description: '经典蓝白色调，学术、自然、课堂讲义的简约精美呈现。',
  },
  church_grace: {
    name: '恩典之光',
    nameEn: 'Grace',
    color: '#1B4F72',
    accent: '#2980B9',
    bg: '#F8F9F9',
    description: '沉稳灰蓝底色与圣洁白交融，适合查经班、主日学、讲座。',
  },
  warm_earth: {
    name: '暖色大地',
    nameEn: 'Warm Earth',
    color: '#6E2C00',
    accent: '#E67E22',
    bg: '#FEF9E7',
    description: '复古大地的暖意橙棕色，展现温馨、舒适、深刻的人文氛围。',
  },
  dark_arcade: {
    name: '暗色游戏',
    nameEn: 'Dark Arcade',
    color: '#FF6B00',
    accent: '#4ECDC4',
    bg: '#1A1C29',
    description: '酷炫黑金与科幻蓝绿的对撞，专为夜晚、科技感或创意演示打造。',
  },
  emerald_growth: {
    name: '翡翠生机',
    nameEn: 'Emerald',
    color: '#0E6251',
    accent: '#1E8449',
    bg: '#E8F8F5',
    description: '淡绿薄荷底色配以深邃翡翠绿，传达学术严谨、生机盎然与成长活力。',
  },
  royal_purple: {
    name: '皇家紫韵',
    nameEn: 'Royal Purple',
    color: '#5B2C6F',
    accent: '#884EA0',
    bg: '#F4ECF7',
    description: '淡雅薰衣草底色与深紫交相辉映，尽显典雅、神秘与创意火花。',
  },
  sleek_dark: {
    name: '极简暗黑',
    nameEn: 'Sleek Dark',
    color: '#D4AC0D',
    accent: '#17A589',
    bg: '#121212',
    description: '极致纯粹的暗夜深灰，衬以金黄和青绿高亮，充满科技感与高阶质感。',
  },
  cherry_blossom: {
    name: '樱花粉黛',
    nameEn: 'Cherry Blossom',
    color: '#78281F',
    accent: '#CB4335',
    bg: '#FDEDEC',
    description: '温柔轻盈的粉粉色底调，搭配深樱桃红，带来春天般的温馨与细腻情调。',
  },
};

export default function TemplateSelector({
  scenario,
  selected,
  bulletStyle,
  onBulletStyleChange,
  selectedTheme = 'clean_blue',
  onThemeChange,
}) {
  const theme = THEME_OPTIONS[selectedTheme] || THEME_OPTIONS.clean_blue;
  const template = TEMPLATE_INFO[selected] || TEMPLATE_INFO.teaching;

  const BULLET_OPTIONS = [
    { value: 'dot', label: '圆点 (•)' },
    { value: 'square', label: '方块 (▪)' },
    { value: 'arrow', label: '箭头 (➢)' },
    { value: 'dash', label: '短划线 (-)' },
    { value: 'none', label: '无项目符号' },
  ];

  return (
    <section className="bashi-card rounded-[28px] p-5 md:p-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <div className="text-xs uppercase tracking-[0.24em] text-bashi-text-muted">
            Theme Preview
          </div>
          <h2 className="mt-2 text-xl font-semibold text-bashi-text">
            系统将为您应用 {template.name} 模板
          </h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-bashi-text-secondary">
            基于您选择的场景（{SCENARIO_LABELS[scenario] || '课堂教学'}），巴适PPT 会自动套用匹配的版式，并支持在下方自定义配色方案与符号样式。
          </p>
        </div>

        <div className="rounded-2xl border border-bashi-border bg-black/20 p-4 md:min-w-[280px]">
          <div className="flex items-center gap-3">
            <div className="flex gap-2">
              <div className="h-10 w-4 rounded-full" style={{ backgroundColor: theme.color }} />
              <div className="h-10 w-4 rounded-full" style={{ backgroundColor: theme.accent }} />
              <div className="h-10 w-4 rounded-full border border-white/10" style={{ backgroundColor: theme.bg }} />
            </div>
            <div>
              <div className="font-medium text-bashi-text">{theme.name} 配色</div>
              <div className="text-sm text-bashi-text-secondary">{theme.nameEn} Theme</div>
            </div>
          </div>
          <div className="mt-3 text-sm leading-6 text-bashi-text-muted">
            {theme.description}
          </div>
        </div>
      </div>

      <hr className="my-5 border-white/10" />

      <div className="mb-5">
        <label className="mb-3 block text-sm font-medium text-bashi-text">
          主题配色 Theme Colors
        </label>
        <div className="flex flex-wrap gap-3">
          {Object.entries(THEME_OPTIONS).map(([key, item]) => (
            <label
              key={key}
              className={`bashi-pill flex items-center gap-2 rounded-full px-4 py-2 text-sm cursor-pointer ${
                selectedTheme === key ? 'active' : ''
              }`}
            >
              <input
                type="radio"
                name="selectedTheme"
                value={key}
                checked={selectedTheme === key}
                onChange={(e) => onThemeChange(e.target.value)}
                className="sr-only"
              />
              <span className="flex gap-0.5">
                <span className="inline-block h-3.5 w-3.5 rounded-full border border-white/10" style={{ backgroundColor: item.bg }} />
                <span className="inline-block h-3.5 w-3.5 rounded-full" style={{ backgroundColor: item.color }} />
              </span>
              {item.name}
            </label>
          ))}
        </div>
      </div>

      <div>
        <label className="mb-3 block text-sm font-medium text-bashi-text">
          内容项符号 Bullet Style
        </label>
        <div className="flex flex-wrap gap-3">
          {BULLET_OPTIONS.map((item) => (
            <label
              key={item.value}
              className={`bashi-pill rounded-full px-4 py-2 text-sm cursor-pointer ${
                bulletStyle === item.value ? 'active' : ''
              }`}
            >
              <input
                type="radio"
                name="bulletStyle"
                value={item.value}
                checked={bulletStyle === item.value}
                onChange={(e) => onBulletStyleChange(e.target.value)}
                className="sr-only"
              />
              {item.label}
            </label>
          ))}
        </div>
      </div>
    </section>
  );
}
