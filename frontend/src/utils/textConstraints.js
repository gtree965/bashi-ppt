const TOKEN_PATTERN =
  /[\u3400-\u9fff]|[A-Za-zÀ-ÖØ-öø-ÿĀ-ž0-9]+(?:[-'’][A-Za-zÀ-ÖØ-öø-ÿĀ-ž0-9]+)*|\s+|./gu;
const CJK_PATTERN = /^[\u3400-\u9fff]$/u;
const WORD_PATTERN =
  /^[A-Za-zÀ-ÖØ-öø-ÿĀ-ž0-9]+(?:[-'’][A-Za-zÀ-ÖØ-öø-ÿĀ-ž0-9]+)*$/u;

function tokenHalfUnits(token) {
  if (/^\s+$/u.test(token)) return 0;
  if (CJK_PATTERN.test(token)) return 2;
  if (WORD_PATTERN.test(token)) return 4;
  return 1;
}

export function textDisplayUnits(text) {
  const tokens = String(text || '').match(TOKEN_PATTERN) || [];
  return tokens.reduce((total, token) => total + tokenHalfUnits(token), 0) / 2;
}

export function truncateSlideText(text, limit) {
  const clean = String(text || '').trimStart();
  if (textDisplayUnits(clean) <= limit) return clean;

  const tokens = clean.match(TOKEN_PATTERN) || [];
  const budget = limit * 2;
  let used = 0;
  const kept = [];
  for (const token of tokens) {
    const cost = tokenHalfUnits(token);
    if (used + cost > budget) break;
    kept.push(token);
    used += cost;
  }
  return kept.join('').replace(/[ \t\r\n,，;；:：\-—]+$/u, '');
}

export function lengthHint(limit, outputLanguage) {
  const words = Math.max(1, Math.floor(limit / 2));
  if (outputLanguage === 'en') return `约 ${words} 个英文单词`;
  if (outputLanguage === 'bilingual') {
    return `约 ${limit} 个中文显示单位 / ${words} 个英文单词（中英合计）`;
  }
  return `约 ${limit} 个中文字；英文约 ${words} 词`;
}
