// Build Mermaid from simple, beginner-friendly step text so non-technical users
// don't have to write Mermaid syntax.
//
// Only `flowchart` and `sequenceDiagram` are produced here, because those are the
// ONLY Mermaid types the installed @excalidraw/mermaid-to-excalidraw bridge renders
// as true hand-drawn Excalidraw shapes (verified at runtime — class/ER/state and the
// rest fall back to a flat image). See frontend/diagram-matrix.html.

const esc = (s) => String(s).replace(/"/g, "'").trim();
const splitLines = (text) =>
  (text || '').split('\n').map((line) => line.trim()).filter(Boolean);

function buildFlow(lines, layout, loop) {
  if (lines.length === 0) return '';
  const node = (i) => `n${i}["${esc(lines[i])}"]`;
  if (lines.length === 1) return `flowchart ${layout}\n  ${node(0)}`;
  let body = '';
  for (let i = 0; i < lines.length - 1; i++) {
    body += `  ${node(i)} --> ${node(i + 1)}\n`;
  }
  if (loop) body += `  n${lines.length - 1} --> n0\n`;
  return `flowchart ${layout}\n${body}`.trimEnd();
}

function buildDecision(lines, layout) {
  if (lines.length === 0) return '';
  let body = `  q{"${esc(lines[0])}"}\n`;
  lines.slice(1).forEach((line, i) => {
    // "label: target" (ASCII or Chinese colon); label is optional.
    const match = line.match(/^(.*?)[:：](.*)$/);
    const label = match ? esc(match[1]) : '';
    const target = match ? esc(match[2]) : esc(line);
    body += label
      ? `  q -->|${label}| o${i}["${target}"]\n`
      : `  q --> o${i}["${target}"]\n`;
  });
  return `flowchart ${layout}\n${body}`.trimEnd();
}

function buildSequence(lines) {
  let body = '';
  for (const line of lines) {
    // "Sender -> Receiver: message"
    const match = line.match(/^(.*?)\s*-+>\s*(.*?)\s*[:：]\s*(.*)$/);
    if (match) {
      body += `  ${esc(match[1])}->>${esc(match[2])}: ${esc(match[3])}\n`;
    }
  }
  return body ? `sequenceDiagram\n${body}`.trimEnd() : '';
}

// Metadata that drives the Steps-mode UI (picker labels, placeholders, hints).
export const DIAGRAM_KINDS = [
  {
    id: 'flow',
    label: '流程',
    hasLayout: true,
    placeholder: '每行一个步骤：\n数据输入\n统计模型\n特征提取\n分类结果',
    hint: '按顺序连成流程图。',
  },
  {
    id: 'decision',
    label: '决策',
    hasLayout: true,
    placeholder: '第一行是问题，其后每行一个分支（可写“标签: 结果”）：\n继续学习？\n是: 进入下一课\n否: 复习本课',
    hint: '第一行作为判断框，其余作为分支。',
  },
  {
    id: 'cycle',
    label: '循环',
    hasLayout: true,
    placeholder: '每行一个步骤，最后自动回到第一步：\n计划\n执行\n检查\n改进',
    hint: '步骤首尾相连成环。',
  },
  {
    id: 'sequence',
    label: '时序',
    hasLayout: false,
    placeholder: '每行：发送者 -> 接收者: 消息\n学生 -> 老师: 提问\n老师 -> 学生: 解答',
    hint: '展示角色之间的交互顺序。',
  },
];

/**
 * Build a Mermaid string from step text for the given template kind.
 * @param {string} kind - 'flow' | 'decision' | 'cycle' | 'sequence'
 * @param {string} stepsText - user's raw lines
 * @param {string} layout - 'TD' | 'LR' (ignored for sequence)
 * @returns {string} Mermaid source (empty string if no usable input)
 */
export function buildMermaid(kind, stepsText, layout = 'TD') {
  const lines = splitLines(stepsText);
  switch (kind) {
    case 'decision':
      return buildDecision(lines, layout);
    case 'cycle':
      return buildFlow(lines, layout, true);
    case 'sequence':
      return buildSequence(lines);
    case 'flow':
    default:
      return buildFlow(lines, layout, false);
  }
}
