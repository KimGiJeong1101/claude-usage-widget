"""사용자가 설정 화면에서 바꿀 수 있는 값들(자동갱신 주기, 트레이 아이콘
스타일 등)을 담당하는 파일. 이 값들은 config.json이라는 파일에 저장된다."""

import json
import os
from dataclasses import asdict, dataclass, fields

from usage_widget.i18n import DEFAULT_LANGUAGE
from usage_widget.paths import config_path
from usage_widget.tray_icon import DEFAULT_STYLE as DEFAULT_TRAY_ICON_STYLE

DEFAULT_REFRESH_SECONDS = 60
DEFAULT_USAGE_POPUP_OPACITY = 100


@dataclass
class Config:
    refresh_seconds: int = DEFAULT_REFRESH_SECONDS
    tray_icon_style: str = DEFAULT_TRAY_ICON_STYLE
    # 투명도 값 (40~100%) -- 사용량 팝업의 카드 배경만 이 값에 따라 흐려짐.
    # 설정/계정 팝업은 자주 들여다보는 화면이 아니라서 굳이 이 기능을 안
    # 넣었음 (자세한 배경은 private notes 저장소 기획 메모의 13.12 참고).
    usage_popup_opacity: int = DEFAULT_USAGE_POPUP_OPACITY
    language: str = DEFAULT_LANGUAGE

    @classmethod
    def load(cls) -> "Config":
        path = config_path()
        if not path.exists():
            return cls()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            # config.json은 "마지막으로 저장했던 버전이 무엇이든" 공유해서
            # 쓰는 파일이다. 그런데 예전 버전(예: language 필드가 아직
            # 없던 버전)이 최신 버전이 저장한 파일을 읽으면, 파이썬의
            # dataclass는 "내가 모르는 필드가 있다"며 그냥 에러를 내고
            # 죽어버린다. 그래서 여기서 미리 "이 클래스가 실제로 알고
            # 있는 필드"만 걸러내고 나머지는 버린다 -- 모르는 필드는
            # 그냥 저장이 안 된 셈 치고 원래 기본값을 쓰는 것과 똑같은
            # 결과가 된다.
            known_fields = {f.name for f in fields(cls)}
            data = {key: value for key, value in data.items() if key in known_fields}
            return cls(**data)
        except Exception:
            # 이 코드가 도저히 이해할 수 없는 내용(JSON 형식 자체가 깨짐,
            # 저장하다가 중간에 끊겨서 파일이 반쯤만 써짐, 값의 타입이
            # 이상함 등)을 만나면, 원래는 프로그램이 시작하자마자 그대로
            # 죽어버렸을 것이다. 그러면 프로그램 코드를 볼 줄 모르는
            # 동료가 이걸 겪었을 때 스스로 해결할 방법이 없다. 그래서
            # 이런 경우엔 그냥 조용히 기본 설정값으로 다시 시작하도록
            # 했다 -- 여기서 다루는 건 그냥 사용자가 바꿀 수 있는
            # 취향/설정값일 뿐이고, 진짜 중요한 로그인 정보는 이 파일이
            # 아니라 완전히 별개인 다른 파일(session_state.json)에 있으니,
            # 설정값 몇 개가 기본값으로 리셋되는 정도는 괜찮은 손해다.
            return cls()

    def save(self) -> None:
        # 바로 config.json에 write_text로 덮어쓰지 않고, 임시 파일에 먼저 쓴
        # 다음 os.replace로 바꿔치기하는 이유: 설정 팝업 저장과 사용량 팝업의
        # 투명도 저장처럼 서로 다른 스레드가 이 파일에 거의 동시에 쓰는
        # 경우가 실제로 있는데, write_text는 파일 내용을 원자적으로(한
        # 번에 통째로) 바꿔주는 게 아니라서 두 스레드의 쓰기가 겹치면
        # JSON이 반쯤 섞여서 깨진 파일이 될 위험이 있다. os.replace는 OS
        # 수준에서 원자적인 교체를 보장해서, 항상 "이전 내용 전체" 아니면
        # "새 내용 전체" 둘 중 하나만 보이게 된다 -- 둘이 섞인 중간 상태가
        # 보일 일이 없다.
        path = config_path()
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        tmp_path.write_text(
            json.dumps(asdict(self), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        os.replace(tmp_path, path)
