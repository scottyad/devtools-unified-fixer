# Chrome Web Store Listing — DevTools Full-Spectrum Assistant

> Last Updated: 2026-09-29

## Store Listing

**Extension Name** [REQUIRED]  
DevTools Full-Spectrum Assistant

**Short Description** [REQUIRED]  
Developer tool to inspect, audit, and repair forms, accessibility, and runtime errors in your web apps via DevTools (F12).

*(121 characters — well under the 132-character Chrome Web Store limit)*

**Detailed Description** [REQUIRED]  
```text
DevTools Full-Spectrum Assistant is an integrated diagnostic panel inside Chrome Developer Tools that audits, analyzes, and repairs web application issues in real time.

Designed for web developers, QA engineers, and accessibility specialists, Fix Assistant identifies form control defects, accessibility compliance gaps, security vulnerabilities, and runtime exceptions on any web application you are developing. With one click, generate instant in-browser safe DOM repairs and clean, ready-to-commit Git diffs.

KEY FEATURES
• Comprehensive Web Health Auditing — Evaluates forms, WCAG accessibility, console errors, broken HTTP assets, and target="_blank" link vulnerabilities with an integrated 100-point Health Score.
• Collected Evidence Inspector — Transparently inspect all gathered signals across Page, Forms, Accessibility, and Reliability pillars so you always know what is being analyzed.
• Remediate with Actionable Fix Plans — Generates structured repair plans categorized by risk (Safe, Review, Manual) with full rationale for every recommended fix.
• Instant Safe Fixes — Apply non-destructive accessibility and attribute repairs directly to the live page DOM to preview fixes before writing code.
• Framework Git Diff Exporter — Automatically compiles unified Git diff patches formatted for React, JSX, and HTML components. Copy directly to your editor or terminal.
• Before vs After Verification Scorecard — Compare baseline metrics against post-remediation results with automatic regression detection.
• Works 100% Offline — Built-in deterministic audit and repair engine operates entirely locally within DevTools without requiring external servers or background proxies.
• Bring Your Own Key (BYOK) & Local LLM Support — Connect optional custom inference endpoints (Ollama, local proxies, or cloud models) for deeper contextual code reasoning.

HOW TO USE
1. Open any web application or local development environment in Google Chrome.
2. Press F12 (or Cmd+Option+I on macOS / right-click and choose "Inspect") to open Chrome DevTools.
3. Select the "Fix Assistant" tab in the DevTools panel navigation bar.
4. Click "Rescan Tab" to inspect the current page.
5. Review detected issues in the "Collected Evidence" tab or inspect the generated "Remediation Plan".
6. Click "⚡ Apply Safe Fixes" to preview non-destructive repairs on the live DOM.
7. Click "View Source Diff" or "📄 Copy Git Diff" to export permanent code changes to your repository.

PRIVACY & SECURITY
DevTools Full-Spectrum Assistant runs completely on-device. By default, all auditing, DOM analysis, and fix generation are performed locally by the embedded deterministic engine. No browsing history, page DOM, form values, or personal data are collected, stored, or transmitted to any remote servers.

PERMISSIONS
• "activeTab" — Needed to analyze the DOM layout, form controls, and console logs of the page currently being inspected when you run an audit.
• "<all_urls>" — As a developer tool running inside Chrome DevTools, this allows inspecting your local development environments (http://localhost, http://127.0.0.1), staging domains, and test web applications.

SUPPORT & FEEDBACK
Questions, feature requests, or bug reports?
Email: support@archpanda.xyz
Documentation & Updates: https://archpanda.xyz/devtools-fixer/
```

**Category** [REQUIRED]  
Developer Tools

**Single Purpose** [REQUIRED]  
Audits and remediates form usability, accessibility compliance, and runtime errors in web applications directly within Chrome DevTools.

**Primary Language** [REQUIRED]  
English

---

## Graphics & Assets

| Asset | Dimensions | Status | Filename |
|---|---|---|---|
| Store Icon [REQUIRED] | 128×128 PNG | ✅ Ready | `icons/icon-128.png` |
| Small Icon | 48×48 PNG | ✅ Ready | `icons/icon-48.png` |
| Toolbar Icon | 16×16 PNG | ✅ Ready | `icons/icon-16.png` |
| Screenshot 1 [REQUIRED] | 1280×800 | ✅ Ready | `store-assets/screenshot-audit-overview.png` |
| Screenshot 2 [RECOMMENDED] | 1280×800 | ✅ Ready | `store-assets/screenshot-evidence-inspector.png` |
| Screenshot 3 [RECOMMENDED] | 1280×800 | ✅ Ready | `store-assets/screenshot-git-diff.png` |
| Screenshot 4 [RECOMMENDED] | 1280×800 | ✅ Ready | `store-assets/screenshot-verification-scorecard.png` |
| Small Promo Tile [RECOMMENDED] | 440×280 | ⬜ Optional | `store-assets/promo-small.png` |
| Marquee Promo Tile | 1400×560 | ⬜ Optional | `store-assets/promo-marquee.png` |

---

## Permissions Justification

| Permission | Type | Justification for Reviewers |
|---|---|---|
| `activeTab` | permissions | Required to inspect the DOM hierarchy, form controls, accessibility landmarks, and error logs of the active browser tab being debugged when the developer clicks "Rescan Tab". |
| `<all_urls>` | host_permissions | DevTools developer extensions must be capable of inspecting arbitrary web applications specified by the developer during testing, including local development hosts (`http://localhost:*`, `http://127.0.0.1:*`), intranet staging servers, and live staging URLs. Access is active only when the developer explicitly opens Chrome Developer Tools on that tab. |

### Remote Code Execution & `chrome.devtools.inspectedWindow.eval()` Justification

> **Statement for CWS Review Team:**  
> The extension uses `chrome.devtools.inspectedWindow.eval()` exclusively within the context of the Chrome DevTools panel. This is standard developer tooling behavior required to:  
> 1. Inspect DOM node properties and form values in the developer's inspected tab.  
> 2. Allow the developer to test temporary, non-destructive DOM repairs (such as adding `aria-label` or missing `alt` attributes) on their own site's live preview before committing permanent source code changes via the generated Git diff.  
>  
> The extension **does not execute remotely hosted code**. All scripts and repair generators are bundled locally within the extension package. In offline mode, the deterministic engine synthesizes strictly scoped, sanitized local JavaScript functions that only alter elements on the inspected page when the developer clicks an explicit action button.

---

## Privacy & Data Use

### Data Collection

**Does the extension collect user data?** No

| Data Type | Collected? | Transmitted Off-Device? | Purpose | Shared with Third Parties? |
|---|---|---|---|---|
| Personally identifiable info | No | No | None | No |
| Health info | No | No | None | No |
| Financial info | No | No | None | No |
| Authentication info | No | No | None | No |
| Personal communications | No | No | None | No |
| Location | No | No | None | No |
| Web history | No | No | None | No |
| User activity | No | No | None | No |
| Website content | No | Optional / User-Initiated Only* | In-memory DOM inspection for diagnostic scoring | Never shared |

*\*Note on Website Content:* Website structure is inspected entirely in memory on the client machine. In default (Local Engine) mode, 100% of diagnostic analysis and diff generation occurs on-device with zero network transmission. If a user voluntarily inputs a custom endpoint or BYOK API key in Settings, diagnostic payloads are transmitted exclusively to that user-specified destination.

### Data Use Certification
- [x] Data is NOT sold to third parties
- [x] Data is NOT used for purposes unrelated to the extension's core functionality
- [x] Data is NOT used for creditworthiness or lending purposes

---

## Privacy Policy

**Privacy Policy URL** [REQUIRED]  
`https://archpanda.xyz/privacy-devtools-assistant.html`

### Privacy Policy Content (Published at above URL)
```markdown
# Privacy Policy for DevTools Full-Spectrum Assistant
Last updated: September 29, 2026

DevTools Full-Spectrum Assistant is a browser developer tool built with privacy and security as core principles.

1. Information We Do Not Collect:
   We do not collect, store, sell, or transmit any personally identifiable information, browsing history, form input values, passwords, cookies, or telemetry data.

2. On-Device Processing:
   All page audits, health score computations, accessibility evaluations, and Git diff generations run locally on your device within Chrome Developer Tools.

3. Third-Party Endpoints:
   By default, no third-party network requests are made during page audits. If you configure a custom Bring-Your-Own-Key (BYOK) endpoint or local LLM server (such as Ollama), audit evidence payloads are routed directly to your configured endpoint and nowhere else.

4. Contact:
   For privacy inquiries, contact support@archpanda.xyz.
```

---

## Distribution

- **Visibility**: Public
- **Regions**: All regions

## Developer Info

- **Publisher Name**: ArchPanda DevTools
- **Contact Email**: support@archpanda.xyz
- **Support URL**: https://archpanda.xyz/devtools-fixer/
- **Homepage URL**: https://archpanda.xyz/devtools-fixer/

---

## Step-by-Step Reviewer Testing Instructions

These instructions allow the Chrome Web Store review team to test all features of the extension without needing any backend server, proxy, or external dependencies:

```markdown
### Reviewer Test Steps:

1. Download or unpack the extension directory.
2. In Google Chrome, navigate to `chrome://extensions/`.
3. Enable "Developer mode" in the top right corner.
4. Click "Load unpacked" and select the extension folder containing `manifest.json`.
5. Open any web page (e.g. https://example.com, any public website, or a local HTML file).
6. Press `F12` (or right-click anywhere on the page and select "Inspect") to open Developer Tools.
7. In the DevTools top panel bar, locate and click the "Fix Assistant" tab.
8. Notice the status indicator in the upper-right corner:
   - It will display `⚡ Local Engine Active` (green), indicating the local deterministic engine is active.
   - The license badge defaults to `Free Trial • 10 Audits Left (Local Engine)`.
9. Click the blue "Rescan Tab" button:
   - Notice the progress bar completes smoothly.
   - A green toast confirms: "✓ Local audit complete: generated instant DOM fixes & git diff."
   - The 100-Point Health Score updates with category breakdowns.
10. Explore the "Collected Evidence" tab:
   - Click accordion rows (Page, Forms, Accessibility, JavaScript & Reliability) to inspect the collected diagnostics.
11. Explore the "Remediation Plan" tab:
   - Click "⚡ Apply Safe Fixes" — notice safe non-destructive attributes (e.g. aria-labels or alt text) are applied to the live preview DOM.
   - Click "View Source Diff" — toggle between the original source and the unified Git diff showing the suggested code repairs.
   - Click "📄 Copy Git Diff" — copies the clean Git patch to the clipboard with visual confirmation.
12. Click "🔄 Verify Fixes (Before → After)":
   - The verification scorecard demonstrates the health score improvement and confirms resolved issues.
```

---

## Version History

| Version | Date | Changes | Status |
|---|---|---|---|
| 1.0.0 | 2026-09-29 | Initial Chrome Web Store release: unified DevTools diagnostic panel, zero-backend deterministic engine, collected evidence inspector, safe DOM repairs, and Git diff exporter. | Ready for Review |
