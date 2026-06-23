export function auditGroundedOutline(outline, factTable) {
  const validIds = new Set(
    (factTable || [])
      .map((fact) => fact?.id)
      .filter((id) => Number.isInteger(id))
  );
  const declared = new Set();
  const invalid = new Set();
  const ungroundedContentPages = [];
  const slides = Array.isArray(outline?.slides) ? outline.slides : [];

  for (const [index, slide] of slides.entries()) {
    const ids = Array.isArray(slide?.fact_ids)
      ? slide.fact_ids.filter((id) => Number.isInteger(id))
      : [];
    const validOnPage = ids.filter((id) => validIds.has(id));
    validOnPage.forEach((id) => declared.add(id));
    ids.filter((id) => !validIds.has(id)).forEach((id) => invalid.add(id));
    if (slide?.slide_type === 'content' && validOnPage.length === 0) {
      ungroundedContentPages.push(
        Number.isInteger(slide.page_number) ? slide.page_number : index + 1
      );
    }
  }

  const missingFactIds = [...validIds].filter((id) => !declared.has(id)).sort((a, b) => a - b);
  const factCount = validIds.size;
  const factCoverage = factCount === 0
    ? 0
    : Math.round((declared.size / factCount) * 1000) / 1000;
  const invalidFactIds = [...invalid].sort((a, b) => a - b);
  const pages = [...new Set(ungroundedContentPages)].sort((a, b) => a - b);

  return {
    fact_count: factCount,
    declared_fact_ids: [...declared].sort((a, b) => a - b),
    missing_fact_ids: missingFactIds,
    invalid_fact_ids: invalidFactIds,
    ungrounded_content_pages: pages,
    fact_coverage: factCoverage,
    structurally_valid: invalidFactIds.length === 0 && pages.length === 0,
    complete:
      factCount > 0
      && missingFactIds.length === 0
      && invalidFactIds.length === 0
      && pages.length === 0,
  };
}
