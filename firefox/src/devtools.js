assistantBrowser.devtools.panels.create(
  "Fix Assistant",
  "",
  "panel.html",
  (panel) => {
    panel.onShown.addListener((panelWindow) => {
      panelWindow.initializePanel();
    });
  }
);
