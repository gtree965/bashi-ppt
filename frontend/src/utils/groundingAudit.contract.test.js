import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

import { auditGroundedOutline } from './groundingAudit.js';


const fixtureUrl = new URL(
  '../../../tests/fixtures/grounding_audit_contract.json',
  import.meta.url
);
const cases = JSON.parse(readFileSync(fixtureUrl, 'utf8'));

for (const contractCase of cases) {
  test(`grounding audit contract: ${contractCase.name}`, () => {
    const actual = auditGroundedOutline(
      contractCase.outline,
      contractCase.fact_table
    );
    assert.deepEqual(actual, contractCase.expected);
  });
}
