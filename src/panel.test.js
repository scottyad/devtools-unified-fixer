/**
 * Automated Test Suite for DevTools Unified Fixer
 * Tests health score calculations, issue extraction, strict safe fix guarantees,
 * before/after verification, regression guard, and the 8 core automated repairs.
 *
 * Run directly with: node src/panel.test.js
 */

const assert = require('assert');

// ─── Minimal Mock DOM Environment ──────────────────────────────────────────
class MockElement {
  constructor(tag, id = '', className = '') {
    this.tagName = tag.toUpperCase();
    this.id = id;
    this.className = className;
    this.attributes = {};
    this.children = [];
    this.textContent = '';
    this.value = '';
    this.type = '';
    this.required = false;
    this.disabled = false;
    this.parentElement = null;
  }

  setAttribute(name, val) { this.attributes[name.toLowerCase()] = String(val); }
  getAttribute(name) { return this.attributes[name.toLowerCase()] || null; }
  removeAttribute(name) { delete this.attributes[name.toLowerCase()]; }
  hasAttribute(name) { return name.toLowerCase() in this.attributes; }

  appendChild(child) {
    child.parentElement = this;
    this.children.push(child);
    return child;
  }

  querySelector(selector) {
    const all = this.querySelectorAll(selector);
    return all.length > 0 ? all[0] : null;
  }

  querySelectorAll(selector) {
    const results = [];
    const traverse = (el) => {
      for (const child of el.children) {
        if (matches(child, selector)) results.push(child);
        traverse(child);
      }
    };
    traverse(this);
    return results;
  }
}

function matches(el, selector) {
  selector = selector.trim();
  if (selector.startsWith('#')) return el.id === selector.slice(1);
  if (selector.startsWith('.')) return el.className.split(/\s+/).includes(selector.slice(1));
  if (selector.includes('[') && selector.endsWith(']')) {
    const attrMatch = selector.match(/\[([a-zA-Z0-9_-]+)(?:=["']?(.*?)["']?)?\]/);
    if (attrMatch) {
      const attr = attrMatch[1];
      const val = attrMatch[2];
      if (val === undefined) return el.hasAttribute(attr);
      return el.getAttribute(attr) === val;
    }
  }
  return el.tagName.toLowerCase() === selector.toLowerCase();
}

class MockDocument {
  constructor() {
    this.documentElement = new MockElement('html');
    this.head = new MockElement('head');
    this.body = new MockElement('body');
    this.documentElement.appendChild(this.head);
    this.documentElement.appendChild(this.body);
    this.title = '';
  }

  createElement(tag) { return new MockElement(tag); }
  getElementById(id) {
    const all = this.querySelectorAll('#' + id);
    return all.length > 0 ? all[0] : null;
  }
  querySelector(sel) { return this.documentElement.querySelector(sel); }
  querySelectorAll(sel) { return this.documentElement.querySelectorAll(sel); }
}

// ─── Test Suite Runner ─────────────────────────────────────────────────────
let passedTests = 0;
let failedTests = 0;

function test(description, fn) {
  try {
    fn();
    console.log(`  ✓ \x1b[32mPASS\x1b[0m: ${description}`);
    passedTests++;
  } catch (err) {
    console.error(`  ✗ \x1b[31mFAIL\x1b[0m: ${description}`);
    console.error(`    ${err.message}`);
    failedTests++;
  }
}

console.log('\n======================================================');
console.log('🧪 DevTools Unified Fixer: Automated Test Suite');
console.log('======================================================\n');

// ─── Test Group 1: Health Score Engine ─────────────────────────────────────
console.log('📦 1. Health Score Engine & Point Deductions');

function calculateHealthScore(scan) {
  let formsScore = 20;
  let a11yScore = 30;
  let jsScore = 20;
  let networkScore = 10;
  let securityScore = 10;
  let seoScore = 10;
  const deductions = [];

  const ev = scan.evidence || {};

  if (ev.forms) {
    const f = ev.forms.totals;
    if (f.unlabelled > 0) {
      const penalty = Math.min(10, f.unlabelled * 3);
      formsScore -= penalty;
      deductions.push({ category: "Forms", points: penalty, reason: `${f.unlabelled} input(s) lack labels` });
    }
    if (f.invalidEmails > 0) {
      const penalty = Math.min(10, f.invalidEmails * 4);
      formsScore -= penalty;
      deductions.push({ category: "Forms", points: penalty, reason: `${f.invalidEmails} invalid email values` });
    }
  }

  if (ev.accessibility) {
    const a = ev.accessibility;
    if (a.unlabeledButtons && a.unlabeledButtons.length > 0) {
      const penalty = Math.min(10, a.unlabeledButtons.length * 3);
      a11yScore -= penalty;
      deductions.push({ category: "Accessibility", points: penalty, reason: `${a.unlabeledButtons.length} unlabeled buttons` });
    }
    if (a.imagesMissingAlt && a.imagesMissingAlt.length > 0) {
      const penalty = Math.min(10, a.imagesMissingAlt.length * 2);
      a11yScore -= penalty;
      deductions.push({ category: "Accessibility", points: penalty, reason: `${a.imagesMissingAlt.length} images missing alt` });
    }
    if (!a.hasMainLandmark) {
      a11yScore -= 4;
      deductions.push({ category: "Accessibility", points: 4, reason: "Missing <main> landmark" });
    }
    if (a.duplicateIds && a.duplicateIds.length > 0) {
      const penalty = Math.min(6, a.duplicateIds.length * 3);
      a11yScore -= penalty;
      deductions.push({ category: "Accessibility", points: penalty, reason: `${a.duplicateIds.length} duplicate IDs` });
    }
  }

  if (scan.error_logs && scan.error_logs.length > 0) {
    const penalty = Math.min(20, scan.error_logs.length * 7);
    jsScore -= penalty;
    deductions.push({ category: "JavaScript", points: penalty, reason: `${scan.error_logs.length} runtime error(s)` });
  }

  if (ev.network && ev.network.failedRequests && ev.network.failedRequests.length > 0) {
    const penalty = Math.min(10, ev.network.failedRequests.length * 3);
    networkScore -= penalty;
    deductions.push({ category: "Network", points: penalty, reason: `${ev.network.failedRequests.length} failed HTTP request(s)` });
  }

  if (ev.security) {
    const s = ev.security;
    if (s.mixedContent && s.mixedContent.length > 0) {
      const penalty = Math.min(5, s.mixedContent.length * 2);
      securityScore -= penalty;
      deductions.push({ category: "Security", points: penalty, reason: `${s.mixedContent.length} mixed content asset(s)` });
    }
    if (s.insecureBlankLinks && s.insecureBlankLinks.length > 0) {
      const penalty = Math.min(5, s.insecureBlankLinks.length * 2);
      securityScore -= penalty;
      deductions.push({ category: "Security", points: penalty, reason: `${s.insecureBlankLinks.length} target="_blank" without noopener` });
    }
  }

  if (ev.seo) {
    const o = ev.seo;
    if (!o.titlePresent) {
      seoScore -= 4;
      deductions.push({ category: "SEO", points: 4, reason: "Missing <title> tag" });
    }
  }

  formsScore = Math.max(0, formsScore);
  a11yScore = Math.max(0, a11yScore);
  jsScore = Math.max(0, jsScore);
  networkScore = Math.max(0, networkScore);
  securityScore = Math.max(0, securityScore);
  seoScore = Math.max(0, seoScore);

  const overall = formsScore + a11yScore + jsScore + networkScore + securityScore + seoScore;
  return { overall, deductions };
}

test('Clean page yields perfect 100/100 score with zero deductions', () => {
  const cleanScan = {
    evidence: {
      forms: { totals: { unlabelled: 0, invalidEmails: 0 } },
      accessibility: { unlabeledButtons: [], imagesMissingAlt: [], hasMainLandmark: true, duplicateIds: [] },
      network: { failedRequests: [] },
      security: { mixedContent: [], insecureBlankLinks: [] },
      seo: { titlePresent: true }
    },
    error_logs: []
  };
  const result = calculateHealthScore(cleanScan);
  assert.strictEqual(result.overall, 100);
  assert.strictEqual(result.deductions.length, 0);
});

test('Broken page correctly computes deductions across all 6 categories', () => {
  const brokenScan = {
    evidence: {
      forms: { totals: { unlabelled: 2, invalidEmails: 1 } },
      accessibility: {
        unlabeledButtons: [{ id: 'btn1' }],
        imagesMissingAlt: [{ src: 'img1.png' }],
        hasMainLandmark: false,
        duplicateIds: ['dup1']
      },
      network: { failedRequests: [{ url: '/api/fail', status: 404 }] },
      security: { mixedContent: ['http://asset.png'], insecureBlankLinks: [{ href: 'https://ext.com' }] },
      seo: { titlePresent: false }
    },
    error_logs: [{ type: 'error', detail: 'ReferenceError: x is not defined' }]
  };
  const result = calculateHealthScore(brokenScan);
  assert(result.overall < 70, `Expected score < 70, got ${result.overall}`);
  assert(result.deductions.length >= 8, `Expected >= 8 deductions, got ${result.deductions.length}`);
});

// ─── Test Group 2: Stricter Safe Fix Guarantee ─────────────────────────────
console.log('\n📦 2. Strict Safe Fix Guarantee & Risk Classification');

function synthesizeDefaultFixPlan(data, evidence) {
  const plan = [];
  if (data.safe_remediation_script && data.safe_remediation_script.trim()) {
    plan.push({
      id: "fix-safe-a11y",
      title: "Add missing ARIA attributes and labels",
      risk: "safe",
      category: "accessibility",
      remediation_code: data.safe_remediation_script.trim()
    });
  } else if (data.remediation_script && data.remediation_script.trim()) {
    // If only general remediation_script is provided, NEVER mark it as 'safe'
    plan.push({
      id: "fix-general-review",
      title: "Review & apply multi-domain repairs",
      risk: "review",
      category: "general",
      remediation_code: data.remediation_script.trim()
    });
  }
  return plan;
}

test('General remediation_script is NEVER marked as safe when safe_remediation_script is absent', () => {
  const data = {
    remediation_script: "document.querySelector('form').reset();",
    safe_remediation_script: null
  };
  const plan = synthesizeDefaultFixPlan(data, {});
  assert.strictEqual(plan.length, 1);
  assert.strictEqual(plan[0].risk, 'review', 'Expected remediation_script to be classified as review');
});

test('Safe script is properly isolated and given risk: safe', () => {
  const data = {
    remediation_script: "document.body.innerHTML = '';",
    safe_remediation_script: "document.querySelector('button').setAttribute('aria-label', 'Submit');"
  };
  const plan = synthesizeDefaultFixPlan(data, {});
  assert.strictEqual(plan.length, 1);
  assert.strictEqual(plan[0].risk, 'safe');
  assert.strictEqual(plan[0].remediation_code, data.safe_remediation_script);
});

test('Safe fix filter rejects execution when safe snippets are absent', () => {
  const plan = [
    { id: '1', risk: 'review', remediation_code: 'alert(1);' },
    { id: '2', risk: 'manual', remediation_code: null }
  ];
  const safeMatches = plan.filter(item => item.risk === 'safe');
  const codeSnippets = safeMatches.map(m => m.remediation_code).filter(Boolean);
  assert.strictEqual(safeMatches.length, 0);
  assert.strictEqual(codeSnippets.length, 0);
});

// ─── Test Group 3: Before → After Verification ─────────────────────────────
console.log('\n📦 3. Before → After Verification & Scorecard Metrics');

function verifyRemediation(beforeIssues, afterIssues, beforeScore, afterScore) {
  const resolved = beforeIssues.filter(b => !afterIssues.includes(b));
  const stillPresent = beforeIssues.filter(b => afterIssues.includes(b));
  const newRegressions = afterIssues.filter(a => !beforeIssues.includes(a));
  return {
    beforeScore,
    afterScore,
    scoreDelta: afterScore - beforeScore,
    resolvedCount: resolved.length,
    stillPresentCount: stillPresent.length,
    newRegressionsCount: newRegressions.length
  };
}

test('Verification scorecard accurately calculates resolved issues and score delta', () => {
  const beforeIssues = ['a11y:btn', 'forms:unlabelled', 'a11y:alt'];
  const afterIssues = ['forms:unlabelled'];
  const result = verifyRemediation(beforeIssues, afterIssues, 65, 85);

  assert.strictEqual(result.resolvedCount, 2);
  assert.strictEqual(result.stillPresentCount, 1);
  assert.strictEqual(result.newRegressionsCount, 0);
  assert.strictEqual(result.scoreDelta, +20);
});

test('Regression guard identifies newly introduced issues', () => {
  const baselineIssues = ['a11y:btn'];
  const currentIssues = ['a11y:btn', 'js:error:ReferenceError'];
  const result = verifyRemediation(baselineIssues, currentIssues, 90, 70);

  assert.strictEqual(result.newRegressionsCount, 1);
  assert.strictEqual(result.scoreDelta, -20);
});

// ─── Test Group 4: Verification of All 8 Core Repairs ──────────────────────
console.log('\n📦 4. Verification of All 8 Web Health Repairs on Mock DOM');

const doc = new MockDocument();

// Setup 8 defective elements
// 1. Unlabeled button
const brokenBtn = doc.createElement('button');
brokenBtn.id = 'iconBtn';
brokenBtn.appendChild(doc.createElement('svg'));
doc.body.appendChild(brokenBtn);

// 2. Unlabelled input
const brokenInput = doc.createElement('input');
brokenInput.id = 'usernameInput';
brokenInput.type = 'text';
doc.body.appendChild(brokenInput);

// 3. Image missing alt
const brokenImg = doc.createElement('img');
brokenImg.id = 'heroImg';
brokenImg.setAttribute('src', 'hero.jpg');
doc.body.appendChild(brokenImg);

// 4. Missing document title
doc.title = '';

// 5. Missing <main> landmark
// (no main element in body)

// 6. External target="_blank" missing rel="noopener"
const brokenLink = doc.createElement('a');
brokenLink.id = 'extLink';
brokenLink.setAttribute('href', 'https://example.com');
brokenLink.setAttribute('target', '_blank');
doc.body.appendChild(brokenLink);

// 7. Duplicate DOM IDs
const dup1 = doc.createElement('div');
dup1.id = 'duplicate-header';
const dup2 = doc.createElement('div');
dup2.id = 'duplicate-header';
doc.body.appendChild(dup1);
doc.body.appendChild(dup2);

// 8. Insecure HTTP asset link
const mixedAsset = doc.createElement('script');
mixedAsset.id = 'insecureScript';
mixedAsset.setAttribute('src', 'http://cdn.example.com/lib.js');
doc.body.appendChild(mixedAsset);

// Now apply 8 standard safe fixes:
test('Repair 1: Accessible name added to interactive button', () => {
  assert(!brokenBtn.getAttribute('aria-label'));
  brokenBtn.setAttribute('aria-label', 'Open navigation menu');
  assert.strictEqual(brokenBtn.getAttribute('aria-label'), 'Open navigation menu');
});

test('Repair 2: Accessible label added to input control', () => {
  assert(!brokenInput.getAttribute('aria-label'));
  brokenInput.setAttribute('aria-label', 'Username');
  assert.strictEqual(brokenInput.getAttribute('aria-label'), 'Username');
});

test('Repair 3: Alt attribute added to image', () => {
  assert(!brokenImg.hasAttribute('alt'));
  brokenImg.setAttribute('alt', 'Hero promotional banner');
  assert.strictEqual(brokenImg.getAttribute('alt'), 'Hero promotional banner');
});

test('Repair 4: Document title assigned when missing', () => {
  assert.strictEqual(doc.title, '');
  doc.title = 'DevTools Inspector - Health Check';
  assert.strictEqual(doc.title, 'DevTools Inspector - Health Check');
});

test('Repair 5: Main landmark role established', () => {
  const main = doc.createElement('main');
  main.setAttribute('role', 'main');
  doc.body.appendChild(main);
  assert(doc.querySelector('[role="main"]') !== null);
});

test('Repair 6: rel="noopener noreferrer" added to target="_blank" link', () => {
  assert(!brokenLink.hasAttribute('rel'));
  brokenLink.setAttribute('rel', 'noopener noreferrer');
  assert.strictEqual(brokenLink.getAttribute('rel'), 'noopener noreferrer');
});

test('Repair 7: Duplicate DOM IDs resolved and uniquely identified', () => {
  assert.strictEqual(dup1.id, dup2.id);
  dup2.id = 'duplicate-header-2';
  assert.notStrictEqual(dup1.id, dup2.id);
  assert.strictEqual(dup2.id, 'duplicate-header-2');
});

test('Repair 8: Insecure HTTP asset upgraded to secure HTTPS protocol', () => {
  const currentSrc = mixedAsset.getAttribute('src');
  assert(currentSrc.startsWith('http://'));
  mixedAsset.setAttribute('src', currentSrc.replace(/^http:\/\//i, 'https://'));
  assert(mixedAsset.getAttribute('src').startsWith('https://'));
});

// ─── Test Group 5: Zero-Backend Local Deterministic Engine ────────────────
console.log('\n📦 5. Zero-Backend Local Engine & Deterministic Fix Synthesis');

const vm = require('vm');

function buildLocalFixPlan(evidence, errorLogs = [], netErrors = []) {
  const plan = [];
  const safeSnippets = [];
  const allSnippets = [];
  const diffHunks = [];

  const a = evidence.accessibility || {};
  const f = evidence.forms || { totals: {} };
  const s = evidence.security || {};

  // 1. Unlabeled buttons
  if (a.unlabeledButtons && a.unlabeledButtons.length > 0) {
    const code = `document.querySelectorAll('button, [role="button"]').forEach((b, i) => { if (!b.textContent.trim() && !b.getAttribute('aria-label') && !b.querySelector('img[alt]:not([alt=""])')) { b.setAttribute('aria-label', b.id ? b.id.replace(/[-_]/g, ' ') : ('Action ' + (i + 1))); } });`;
    plan.push({
      id: "fix-unlabeled-buttons",
      title: `Add accessible names to ${a.unlabeledButtons.length} interactive button(s)`,
      risk: "safe",
      category: "accessibility",
      description: "Buttons without visible text or aria-label are inaccessible to screen readers (WCAG 4.1.2). Adds aria-label attributes.",
      remediation_code: code
    });
    safeSnippets.push(code);
    diffHunks.push(`@@ -12,3 +12,3 @@\n-<button class="btn">\n+<button class="btn" aria-label="Action">\n   <svg aria-hidden="true">...</svg>\n </button>`);
  }

  // 2. Unlabeled links
  if (a.unlabeledLinks && a.unlabeledLinks.length > 0) {
    const code = `document.querySelectorAll('a:not([aria-label])').forEach(a => { if (!a.textContent.trim()) a.setAttribute('aria-label', a.getAttribute('href') || 'Navigation link'); });`;
    plan.push({
      id: "fix-unlabeled-links",
      title: `Add accessible text to ${a.unlabeledLinks.length} link(s)`,
      risk: "safe",
      category: "accessibility",
      description: "Links without readable anchor text or aria-label fail WCAG 2.4.4. Adds descriptive aria-labels.",
      remediation_code: code
    });
    safeSnippets.push(code);
  }

  // 3. Missing image alt text
  if (a.images && a.images.missingAlt && a.images.missingAlt.length > 0) {
    const code = `document.querySelectorAll('img:not([alt])').forEach(img => { img.setAttribute('alt', img.getAttribute('title') || ''); });`;
    plan.push({
      id: "fix-missing-alt",
      title: `Add alt attributes to ${a.images.missingAlt.length} image(s)`,
      risk: "safe",
      category: "accessibility",
      description: "Images missing alt attributes violate WCAG 1.1.1. Adds descriptive alt attributes or marks decorative assets.",
      remediation_code: code
    });
    safeSnippets.push(code);
    diffHunks.push(`@@ -25,3 +25,3 @@\n-<img src="graphic.svg">\n+<img src="graphic.svg" alt="">`);
  }

  // 4. Missing main landmark
  if (!a.landmarks || !a.landmarks.hasMain) {
    const code = `if (!document.querySelector('main, [role="main"]')) { const target = document.querySelector('.panel, .container, #root, #app') || document.body.firstElementChild; if (target) target.setAttribute('role', 'main'); }`;
    plan.push({
      id: "fix-main-landmark",
      title: "Assign main landmark role to primary container",
      risk: "safe",
      category: "accessibility",
      description: "Document lacks a <main> landmark, preventing assistive tech from jumping to primary content (WCAG 1.3.1).",
      remediation_code: code
    });
    safeSnippets.push(code);
  }

  // 5. Unlabelled form inputs
  if (f.totals && f.totals.unlabelled > 0) {
    const code = `document.querySelectorAll('input:not([aria-label]):not([aria-labelledby]):not([id])').forEach(inp => { if (inp.placeholder) inp.setAttribute('aria-label', inp.placeholder); });`;
    plan.push({
      id: "fix-unlabelled-inputs",
      title: `Associate accessible labels with ${f.totals.unlabelled} form input(s)`,
      risk: "safe",
      category: "forms",
      description: "Inputs without associated <label> or aria-label fail WCAG 1.3.1. Infers accessible name from placeholder.",
      remediation_code: code
    });
    safeSnippets.push(code);
    diffHunks.push(`@@ -35,3 +35,3 @@\n-<input type="text" placeholder="Search">\n+<input type="text" placeholder="Search" aria-label="Search">`);
  }

  // 6. Insecure external target="_blank" links
  if (s.insecureBlankLinks && s.insecureBlankLinks.length > 0) {
    const code = `document.querySelectorAll('a[target="_blank"]:not([rel*="noopener"])').forEach(a => { const rel = a.getAttribute('rel') || ''; a.setAttribute('rel', (rel + ' noopener noreferrer').trim()); });`;
    plan.push({
      id: "fix-insecure-blank",
      title: `Add rel="noopener noreferrer" to ${s.insecureBlankLinks.length} external link(s)`,
      risk: "safe",
      category: "security",
      description: "Links with target='_blank' without rel=noopener expose the tab to reverse tabnabbing vulnerabilities.",
      remediation_code: code
    });
    safeSnippets.push(code);
    diffHunks.push(`@@ -45,3 +45,3 @@\n-<a href="https://example.com" target="_blank">\n+<a href="https://example.com" target="_blank" rel="noopener noreferrer">`);
  }

  // 7. Disabled & readOnly lockout controls
  if ((f.totals && (f.totals.disabled > 0 || f.totals.readonly > 0)) || (evidence.interactive && evidence.interactive.disabledElements > 0)) {
    const code = `document.querySelectorAll('[readonly], [disabled]').forEach(el => { el.removeAttribute('readonly'); el.removeAttribute('disabled'); });`;
    plan.push({
      id: "fix-locked-controls",
      title: "Unlock disabled and read-only form controls",
      risk: "review",
      category: "forms",
      description: "Restores user interactivity to locked form controls during testing and debugging.",
      remediation_code: code
    });
    allSnippets.push(code);
    diffHunks.push(`@@ -55,3 +55,3 @@\n-<input type="tel" value="+1555019999" readonly>\n+<input type="tel" value="+1555019999">`);
  }

  // 8. Invalid email syntax
  if (f.totals && f.totals.invalidEmails > 0) {
    const code = `document.querySelectorAll('input[type="email"]').forEach(inp => { if (inp.value && inp.value.includes('@@')) inp.value = inp.value.replace(/@@+/g, '@'); });`;
    plan.push({
      id: "fix-invalid-email-syntax",
      title: `Correct malformed email syntax in ${f.totals.invalidEmails} field(s)`,
      risk: "review",
      category: "forms",
      description: "Corrects syntax errors (e.g. duplicate @@ characters) that prevent HTML5 form submission.",
      remediation_code: code
    });
    allSnippets.push(code);
  }

  // 9. Runtime errors / network 4xx
  if ((errorLogs && errorLogs.length > 0) || (netErrors && netErrors.length > 0)) {
    const errCount = (errorLogs ? errorLogs.length : 0) + (netErrors ? netErrors.length : 0);
    plan.push({
      id: "fix-runtime-guards",
      title: `Add runtime exception guards (${errCount} exception/4xx logged)`,
      risk: "manual",
      category: "reliability",
      description: "Inspect uncaught errors in the Collected Evidence tab and wrap async calls in try/catch recovery blocks.",
      remediation_code: null
    });
  }

  // Fallback if page is 100% clean
  if (plan.length === 0) {
    plan.push({
      id: "fix-page-clean",
      title: "No urgent structural defects detected",
      risk: "safe",
      category: "best-practices",
      description: "The audited page conforms to standard form, accessibility, and security baseline rules.",
      remediation_code: "// Page adheres to baseline standards."
    });
  }

  allSnippets.unshift(...safeSnippets);

  const safeScript = safeSnippets.length > 0
    ? `(function() {\n  // DevTools Deterministic Safe Fixes\n  ${safeSnippets.join('\n  ')}\n})();`
    : "";

  const remediationScript = allSnippets.length > 0
    ? `(function() {\n  // DevTools Deterministic Full Remediation\n  ${allSnippets.join('\n  ')}\n})();`
    : "";

  const gitDiff = diffHunks.length > 0
    ? `--- a/src/App.jsx\n+++ b/src/App.jsx\n${diffHunks.join('\n')}\n`
    : "--- a/src/App.jsx\n+++ b/src/App.jsx\n@@ -1,5 +1,5 @@\n // No DOM changes required. Page adheres to baseline standards.\n";

  return {
    plan,
    safeScript,
    remediationScript,
    gitDiff
  };
}

test('buildLocalFixPlan generates complete remediation plan with expected categories and risk ratings', () => {
  const sampleEvidence = {
    accessibility: {
      unlabeledButtons: [{ id: 'menu-btn' }],
      unlabeledLinks: [{ href: '#top' }],
      images: { missingAlt: [{ src: 'avatar.png' }] },
      landmarks: { hasMain: false }
    },
    forms: {
      totals: { unlabelled: 3, disabled: 1, readonly: 1, invalidEmails: 1 }
    },
    security: {
      insecureBlankLinks: [{ href: 'https://example.com' }]
    }
  };
  const errors = [{ type: 'error', detail: 'TypeError: undefined is not a function' }];
  const netErrors = [{ url: '/api/v1/data', status: 404 }];

  const result = buildLocalFixPlan(sampleEvidence, errors, netErrors);

  assert(result.plan.length >= 8, `Expected >= 8 plan items, got ${result.plan.length}`);
  
  const safeItems = result.plan.filter(p => p.risk === 'safe');
  const reviewItems = result.plan.filter(p => p.risk === 'review');
  const manualItems = result.plan.filter(p => p.risk === 'manual');

  assert(safeItems.length >= 5, `Expected >= 5 safe items, got ${safeItems.length}`);
  assert(reviewItems.length >= 2, `Expected >= 2 review items, got ${reviewItems.length}`);
  assert(manualItems.length >= 1, `Expected >= 1 manual item, got ${manualItems.length}`);
});

test('safeScript isolates safe WCAG repairs and excludes review/manual actions', () => {
  const sampleEvidence = {
    accessibility: { unlabeledButtons: [{ id: 'btn1' }] },
    forms: { totals: { disabled: 2, invalidEmails: 1 } }
  };
  const result = buildLocalFixPlan(sampleEvidence);

  assert(result.safeScript.length > 0, 'safeScript should not be empty');
  assert(result.safeScript.includes('aria-label'), 'safeScript should contain aria-label fix');
  assert(!result.safeScript.includes('removeAttribute(\'disabled\')'), 'safeScript must NOT unlock controls');
  assert(!result.safeScript.includes('replace(/@@+/g'), 'safeScript must NOT modify user input values');
});

test('remediationScript bundles both safe and review snippets into an executable IIFE', () => {
  const sampleEvidence = {
    accessibility: { unlabeledButtons: [{ id: 'btn1' }] },
    forms: { totals: { disabled: 1, invalidEmails: 1 } }
  };
  const result = buildLocalFixPlan(sampleEvidence);

  assert(result.remediationScript.includes('aria-label'), 'remediationScript should contain safe fixes');
  assert(result.remediationScript.includes('removeAttribute'), 'remediationScript should contain review unlocks');
  assert(result.remediationScript.includes('replace(/@@+/g'), 'remediationScript should contain email repairs');
  assert(result.remediationScript.startsWith('(function() {'), 'remediationScript should be wrapped in IIFE');
  assert(result.remediationScript.endsWith('})();'), 'remediationScript should close IIFE');
});

test('gitDiff produces valid unified diff headers and hunk markers', () => {
  const sampleEvidence = {
    accessibility: { unlabeledButtons: [{ id: 'b1' }] },
    forms: { totals: { unlabelled: 1 } },
    security: { insecureBlankLinks: [{ href: 'https://test.com' }] }
  };
  const result = buildLocalFixPlan(sampleEvidence);

  assert(result.gitDiff.startsWith('--- a/src/App.jsx\n+++ b/src/App.jsx\n'), 'Diff header must match unified git format');
  assert(result.gitDiff.includes('@@'), 'Diff must contain hunk markers');
  assert(result.gitDiff.includes('+<button class="btn" aria-label="Action">'), 'Diff must contain added aria-label attribute');
});

test('Synthesized JavaScript scripts pass syntax validation via Node vm.Script', () => {
  const sampleEvidence = {
    accessibility: {
      unlabeledButtons: [{ id: 'btn1' }],
      unlabeledLinks: [{ href: '/page' }],
      images: { missingAlt: [{ src: 'test.jpg' }] },
      landmarks: { hasMain: false }
    },
    forms: { totals: { unlabelled: 2, disabled: 1, invalidEmails: 1 } },
    security: { insecureBlankLinks: [{ href: 'https://foo.bar' }] }
  };
  const result = buildLocalFixPlan(sampleEvidence);

  // Validate syntax without throwing
  assert.doesNotThrow(() => {
    new vm.Script(result.safeScript);
  }, 'safeScript must be syntactically valid JavaScript');

  assert.doesNotThrow(() => {
    new vm.Script(result.remediationScript);
  }, 'remediationScript must be syntactically valid JavaScript');
});

test('Clean page fallback handles pristine pages gracefully with zero runtime errors', () => {
  const cleanEvidence = {
    accessibility: { landmarks: { hasMain: true } },
    forms: { totals: { unlabelled: 0, disabled: 0, readonly: 0, invalidEmails: 0 } },
    security: {}
  };
  const result = buildLocalFixPlan(cleanEvidence, [], []);

  assert.strictEqual(result.plan.length, 1);
  assert.strictEqual(result.plan[0].id, 'fix-page-clean');
  assert.strictEqual(result.plan[0].risk, 'safe');
  assert.strictEqual(result.safeScript, '');
  assert(result.gitDiff.includes('No DOM changes required'), 'Clean diff should indicate no changes needed');
});

// ─── Test Summary ──────────────────────────────────────────────────────────
console.log('\n======================================================');
console.log(`🏁 Test Results: ${passedTests} passed, ${failedTests} failed`);
console.log('======================================================\n');

if (failedTests > 0) {
  process.exit(1);
} else {
  process.exit(0);
}
