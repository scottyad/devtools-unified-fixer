# DevTools Full-Spectrum Assistant for Firefox 1.0.4

Requires desktop Firefox 142 or newer. Load manifest.json through about:debugging → This Firefox → Load Temporary Add-on. Open a normal web page, press F12, and select Fix Assistant. Temporary installs end on browser restart. Permanent installation requires Mozilla signing.

## Build and source submission

The JavaScript, HTML and CSS in this directory are the original readable extension source. No minification, transpilation or external dependencies are required. From this directory run:

```sh
python3 package.py
node tests/compat.test.cjs
```

The packaging script writes devtools-unified-fixer-firefox-1.0.4.zip one directory above this directory. Contents are copied verbatim; manifest.json is at the ZIP root. Backend code and secrets are not part of this extension.

Firefox uses an event background script rather than a Chrome service worker. src/firefox-compat.js adapts promise-based DevTools evaluation and panel creation to the existing callback workflow; storage, permissions and messaging use Firefox's native browser APIs. clipboardWrite supports report and patch export. The manifest declares website content, browsing activity, and authentication information for diagnostic requests, URLs, trial identity and license keys.

## Validation

Mozilla web-ext lint reported zero errors and 12 UNSAFE_VAR_ASSIGNMENT warnings about existing dynamic HTML templates in src/panel.js. These warnings require reviewer attention; this package does not claim store approval. The templates use the existing escaping code. The panel runs bundled repair operations; cloud responses are treated as data, not executable code.

The extension loaded successfully using web-ext with Firefox 153.3.0esr. Adapter tests cover evaluation results, exceptions, rejection, panel creation and shared trial identity. Panel workflow checks passed using Chromium with Firefox-style promise APIs and mocked inspected-page and backend fixtures. A complete manual Firefox DevTools workflow still needs testing.

## Privacy and reviewer testing

Opening the panel initiates an audit and can send a compact DOM excerpt, page/form metadata, URLs, runtime errors and failed requests to https://cite.archpanda.xyz/devtools/. The backend uses Anthropic Claude. Entered form values are stripped, but other page data can still contain sensitive information. Trial identity and license keys are sent for entitlement and quota handling. Custom backend URLs require explicit host access. Review privacy-devtools-assistant.html (included in the source package) for the detailed policy.

Test with a disposable web page containing an unlabeled button and form inputs. Open Fix Assistant, review the findings, apply supported repairs, and verify the before/after results. Test Explain and report/source-patch export. Live cloud tests consume the free allowance; no paid account is necessary for the free tier.

## License

MIT; see LICENSE. Third-party dependencies and assets retain their respective licenses.
