// Adapt Firefox's promise-based DevTools APIs to the panel's callback interface.
// Storage, messaging and permissions retain native Firefox promise behavior.
globalThis.assistantBrowser = {
  storage: browser.storage,
  runtime: browser.runtime,
  permissions: browser.permissions,
};
if (browser.devtools) {
  assistantBrowser.devtools = {
    network: browser.devtools.network,
    inspectedWindow: {
      eval(expression, callback) {
        browser.devtools.inspectedWindow.eval(expression).then(
          ([result, error]) => callback(result, error),
          error => callback(undefined, { isError: true, value: error.message || String(error) })
        );
      },
    },
    panels: {
      create(title, icon, page, callback) {
        browser.devtools.panels.create(title, icon, page).then(callback, error => console.error('Unable to create Fix Assistant panel:', error));
      },
    },
  };
}
