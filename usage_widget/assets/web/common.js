// 커스텀 모서리 리사이즈 손잡이(그립) 드래그 처리 (common.css의 .resize-grip 참고).
// 테두리가 없는 프레임리스(frameless) 팝업 창은 OS가 기본으로 제공하는 크기 조절
// 테두리가 없다. 그래서 여기 JS에서 드래그한 만큼의 이동량(delta)을 직접 계산해서
// Python 쪽에 window.pywebview.api.resize_by(dw, dh)로 알려주고, 실제 창 크기를
// 늘리거나 줄이는 건 Python이 담당한다 -- 각 팝업의 js_api가 이 호출을
// webui.py에 있는 resize 클로저(closure, 함수가 자기 주변 변수를 계속 기억하는 것.
// 여기서는 "어느 창을 얼마나 조절할지"를 기억하는 함수를 뜻함)로 연결해준다
// (_UsageApi 등 참고).
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

  // 일반 마우스 이벤트(mousedown/mousemove/mouseup)가 아니라 굳이 포인터
  // 이벤트(Pointer Events)를 쓰는 이유는, 바로 아래에 나오는
  // setPointerCapture(포인터 캡처, 마우스 버튼을 누른 요소가 커서 위치와
  // 상관없이 계속 이후 이벤트를 받도록 "붙잡아두는" 기능)를 쓰기 위해서다.
  // 이게 없으면, 이 작은 프레임리스 창은 크기가 작다 보니 사용자가 빠르게
  // 드래그할 때 커서가 창 경계를 순식간에 벗어나버릴 수 있는데, 그러면
  // 정작 mouseup 이벤트는 전혀 다른 네이티브(OS) 창/화면 위에서 발생해버려서
  // 이 리스너들한테는 영영 도착하지 않는다. 결과적으로 onPointerMove(당시엔
  // onMouseMove)가 떨어지지 않고 계속 붙어있게 되어서, 나중에 마우스 버튼을
  // 누르지 않은 채로 팝업 위를 지나가기만 해도 계속 resize_by가 호출되는
  // 버그가 있었다.
  grip.addEventListener("pointerdown", function (ev) {
    // stopPropagation만으로는 부족하고 preventDefault를 써야 하는 이유:
    // preventDefault를 호출하면 이 pointerdown 때문에 원래 같이 발생했을
    // "호환용(compatibility)" mousedown 이벤트까지 같이 막아준다. 이
    // mousedown을 창 전체 드래그-이동 리스너(easy_drag)가 감시하고 있어서,
    // 막아두지 않으면 그립을 잡고 크기를 조절하려던 동작이 창을 통째로
    // 옮기는 동작으로 잘못 인식돼버린다.
    ev.preventDefault();
    startX = ev.screenX;
    startY = ev.screenY;
    grip.setPointerCapture(ev.pointerId);
    grip.addEventListener("pointermove", onPointerMove);
    grip.addEventListener("pointerup", onPointerUp);
  });
}
