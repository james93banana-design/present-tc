// Inline before the report's presentation controller; see html-features.md.
(() => {
  window.createPresentationReturn = ({isPresenting, fitReading = () => {
    window.dispatchEvent(new Event('tc-fit'));
  }}) => {
    let revision = 0;
    let frame = 0;
    function begin() {
      revision++;
      cancelAnimationFrame(frame);
    }
    function restore(page, fullscreenExit = Promise.resolve()) {
      const ticket = ++revision;
      cancelAnimationFrame(frame);
      const valid = () => ticket === revision && !isPresenting() && page?.isConnected;
      const position = () => {
        if (!valid()) return;
        fitReading();
        page.scrollIntoView({block: 'start', inline: 'nearest', behavior: 'instant'});
      };
      const afterLayout = () => {
        if (!valid()) return;
        cancelAnimationFrame(frame);
        frame = requestAnimationFrame(() => {
          frame = requestAnimationFrame(position);
        });
      };
      // Restore immediately for rapid reentry, then after layout/fullscreen settles.
      position();
      afterLayout();
      Promise.resolve(fullscreenExit).catch(() => {}).then(afterLayout);
    }
    return {begin, restore};
  };
})();
