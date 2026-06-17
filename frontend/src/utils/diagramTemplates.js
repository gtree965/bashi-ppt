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

// A line ending in ? / ？ is treated as a decision.
const isQuestion = (s) => /[?？]\s*$/.test(s);

// Emit a flowchart node with the given shape. Re-stating the same id+shape on each
// edge is fine for Mermaid as long as it's consistent (shapeFor is deterministic).
function node(id, text, shape) {
  const t = esc(text);
  switch (shape) {
    case 'circle':
      return `${id}(("${t}"))`;
    case 'rounded':
      return `${id}("${t}")`;
    case 'diamond':
      return `${id}{"${t}"}`;
    case 'rect':
    default:
      return `${id}["${t}"]`;
  }
}

// Flow with smart auto-shapes: first/last steps are circles (start/end), a line
// ending in ? becomes a decision diamond (inline, single path), the rest rectangles.
function buildFlow(lines, layout) {
  if (lines.length === 0) return '';
  const shapeFor = (i) => {
    if (isQuestion(lines[i])) return 'diamond';
    if (i === 0 || i === lines.length - 1) return 'circle';
    return 'rect';
  };
  if (lines.length === 1) {
    return `flowchart ${layout}\n  ${node('n0', lines[0], shapeFor(0))}`;
  }
  let body = '';
  for (let i = 0; i < lines.length - 1; i++) {
    body += `  ${node(`n${i}`, lines[i], shapeFor(i))} --> ${node(`n${i + 1}`, lines[i + 1], shapeFor(i + 1))}\n`;
  }
  return `flowchart ${layout}\n${body}`.trimEnd();
}

// Cycle: rounder (circle) nodes connected in a loop back to the first step.
function buildCycle(lines, layout) {
  if (lines.length === 0) return '';
  const n = (i) => node(`n${i}`, lines[i], 'circle');
  if (lines.length === 1) return `flowchart ${layout}\n  ${n(0)}`;
  let body = '';
  for (let i = 0; i < lines.length - 1; i++) {
    body += `  ${n(i)} --> ${n(i + 1)}\n`;
  }
  body += `  n${lines.length - 1} --> n0\n`;
  return `flowchart ${layout}\n${body}`.trimEnd();
}

// Decision: first line is the question (diamond), each following line a branch
// (optionally "label: result" for a labeled yes/no edge).
function buildDecision(lines, layout) {
  if (lines.length === 0) return '';
  let body = `  ${node('q', lines[0], 'diamond')}\n`;
  lines.slice(1).forEach((line, i) => {
    const match = line.match(/^(.*?)[:：](.*)$/);
    const label = match ? esc(match[1]) : '';
    const target = match ? match[2] : line;
    body += label
      ? `  q -->|${label}| ${node(`o${i}`, target, 'rect')}\n`
      : `  q --> ${node(`o${i}`, target, 'rect')}\n`;
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
    placeholder: '每行一个步骤（以 ? 结尾的行会变成判断框）：\n开始\n读取输入\n数据有效?\n处理\n结束',
    hint: '首尾自动为圆形（开始/结束），以 ? 结尾的行变为判断框，其余为方框。',
  },
  {
    id: 'decision',
    label: '决策',
    hasLayout: true,
    placeholder: '第一行是问题，其后每行一个分支（可写“标签: 结果”）：\n继续学习？\n是: 进入下一课\n否: 复习本课',
    hint: '第一行作为判断框，其余作为带标签的分支。',
  },
  {
    id: 'cycle',
    label: '循环',
    hasLayout: true,
    placeholder: '每行一个步骤，最后自动回到第一步：\n计划\n执行\n检查\n改进',
    hint: '圆形节点首尾相连成环。',
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
      return buildCycle(lines, layout);
    case 'sequence':
      return buildSequence(lines);
    case 'flow':
    default:
      return buildFlow(lines, layout);
  }
}
