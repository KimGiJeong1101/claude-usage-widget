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

  function onMouseMove(ev) {
    var dw = ev.screenX - startX;
    var dh = ev.screenY - startY;
    startX = ev.screenX;
    startY = ev.screenY;
    window.pywebview.api.resize_by(dw, dh);
  }

  function onMouseUp() {
    window.removeEventListener("mousemove", onMouseMove);
    window.removeEventListener("mouseup", onMouseUp);
  }

  grip.addEventListener("mousedown", function (ev) {
    ev.stopPropagation(); // don't also trigger the window-drag-move listener
    startX = ev.screenX;
    startY = ev.screenY;
    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp);
  });
}
