// Drag-resize for the custom corner grip (see .resize-grip in common.css).
// Frameless popups get no OS resize border, so this reads the drag delta
// in JS and asks Python to grow/shrink the actual window via
// window.pywebview.api.resize_by(dw, dh) -- each popup's js_api wires
// that back to webui.py's resize closure (see _UsageApi etc.).
function initResizeGrip() {
  var grip = document.querySelector(".resize-grip");
  if (!grip) return;

  var startX = 0;
  var startY = 0;

  function onPointerMove(ev) {
    var dw = ev.screenX - startX;
    var dh = ev.screenY - startY;
    startX = ev.screenX;
    startY = ev.screenY;
    window.pywebview.api.resize_by(dw, dh);
  }

  function onPointerUp(ev) {
    grip.releasePointerCapture(ev.pointerId);
    grip.removeEventListener("pointermove", onPointerMove);
    grip.removeEventListener("pointerup", onPointerUp);
  }

  // Pointer Events (not plain mouse events) specifically so
  // setPointerCapture can be used below -- without it, dragging fast
  // enough for the cursor to leave this small frameless window's bounds
  // meant the eventual mouseup landed on a different native surface
  // entirely and never reached these listeners, leaving onMouseMove
  // permanently attached (any later movement over the popup, even
  // without the button held, kept calling resize_by).
  grip.addEventListener("pointerdown", function (ev) {
    // preventDefault (not just stopPropagation) also suppresses the
    // compatibility mousedown event this would otherwise still fire,
    // which is what the window-drag-move listener (easy_drag) listens for.
    ev.preventDefault();
    startX = ev.screenX;
    startY = ev.screenY;
    grip.setPointerCapture(ev.pointerId);
    grip.addEventListener("pointermove", onPointerMove);
    grip.addEventListener("pointerup", onPointerUp);
  });
}
