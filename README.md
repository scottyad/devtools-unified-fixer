# DevTools Full-Spectrum Assistant

Developer extension for inspecting, auditing, and repairing forms, accessibility issues, and runtime errors through the Fix Assistant DevTools panel.

## Firefox

The Firefox edition is version 1.0.4 and requires desktop Firefox 142 or newer.

- [Firefox extension ZIP](devtools-unified-fixer-firefox-1.0.4.zip)
- [Firefox source ZIP for Mozilla reviewers](devtools-unified-fixer-firefox-source-1.0.4.zip)
- [Readable source, build instructions, and validation notes](firefox/README.md)

For local testing, open `about:debugging` in Firefox, select **This Firefox → Load Temporary Add-on**, and choose `firefox/manifest.json` or the extension ZIP. Open a webpage, press F12, and select **Fix Assistant**. Temporary installation ends when Firefox restarts; permanent installation requires Mozilla signing.

Build and test from the repository root:

```sh
python3 firefox/package.py
node firefox/tests/compat.test.cjs
```

The Firefox source is unminified and needs no compiler. The compatibility adapter supports Firefox's promise-based DevTools APIs. Local validation reported zero errors and 12 existing dynamic HTML rendering warnings; see the Firefox README for testing details and limits.

## License

This project is licensed under the [MIT License](LICENSE).

Copyright (c) 2026 scottyad. Third-party dependencies and assets retain their respective licenses.

### Anthropic prompt caching

The cloud backend marks stable diagnosis instructions and enables five-minute automatic prompt caching for hosted and Anthropic BYOK diagnoses. It logs cache read/write token counts without document contents or keys. Savings require repeated prefixes meeting the model’s minimum length; cache writes cost extra, and prompts are not padded. The setting runs on the backend and applies to Chrome and Firefox clients.
