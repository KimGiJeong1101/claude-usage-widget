"""Windows 트레이 / macOS 메뉴바에 보이는 작은 상태 아이콘을 그리는 파일.

트레이 아이콘은 실제로는 아주 작은 크기(보통 16~22px)로 화면에 표시된다.
그런데 그 크기에서는 얇은 원형 링이나 작은 글씨가 뭉개져서 잘 안 보인다는
걸 실제로 테스트해보고 확인했다. 그래서 스타일을 여러 개 만들어서(설정
화면에서 고를 수 있음) 선택하게 했다 -- "정확한 숫자를 보여줄지" 아니면
"한눈에 대충 얼마나 찼는지 느낌만 보여줄지" 사이에서 사람마다 선호가
다르기 때문이다. 어떤 스타일이든 세션(5시간) 사용량 퍼센트만 보여준다 --
세션 쪽이 주간 사용량보다 훨씬 자주 리셋되니까, 팝업을 열어보지 않고
얼핏 봐도 될 만큼 자주 확인할 가치가 있는 숫자이기 때문이다. 주간
사용량은 클릭 한 번이면 팝업에서 바로 볼 수 있다.

모든 스타일에 테두리(윤곽선, 아래 OUTLINE/OUTLINE_WIDTH 참고)를 둘렀는데,
이건 작업표시줄/메뉴바의 배경색이 어떤 색이든 아이콘 모양이 잘 보이게
하기 위해서다 -- 테두리 없이 색만 채워 넣으면, 배경색이랑 비슷한 색일 때
아이콘이 배경에 묻혀서 안 보이는 경우가 생긴다."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SIZE = 64

GREEN = (52, 168, 83)
YELLOW = (251, 188, 5)
RED = (234, 67, 53)
TRACK = (222, 222, 222)
OUTLINE = (90, 90, 90)
# 여기 적힌 테두리 두께는 원본 크기(64px)를 기준으로 그린 값이다. 실제
# 트레이 아이콘은 16~22px 정도로 축소돼서 보이기 때문에, 이보다 훨씬 얇게
# 그리면 축소되면서 거의 안 보이게 된다 (예: 원본에서 2px 두께였던 선은
# 축소 후 약 0.5px이 되는데, 이건 사실상 안 보이는 것과 같다).
OUTLINE_WIDTH = 7

_FONT_PATH = Path(__file__).parent / "assets" / "fonts" / "Pretendard-Bold.otf"


def color_for_percent(percent: int) -> tuple:
    if percent >= 90:
        return RED
    if percent >= 70:
        return YELLOW
    return GREEN


def _build_donut(session_percent: int, week_percent: int) -> Image.Image:
    """두꺼운 도넛 모양 게이지. 위쪽부터 시계 방향으로 채워진다 -- 얇은
    윤곽선이 아니라 두껍게 색을 채운 부채꼴 모양이라서, 실제 트레이
    크기로 작아져도 "대충 얼마나 찼는지" 정도는 눈에 잘 들어온다."""
    margin, thickness = 3, 28
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    bbox = [margin, margin, SIZE - margin, SIZE - margin]
    draw.ellipse(bbox, fill=TRACK)

    clamped = min(max(session_percent, 0), 100)
    if clamped > 0:
        end_angle = -90 + 360 * clamped / 100
        draw.pieslice(bbox, start=-90, end=end_angle, fill=color_for_percent(session_percent))

    inner = margin + thickness
    inner_bbox = [inner, inner, SIZE - inner, SIZE - inner]
    draw.ellipse(inner_bbox, fill=(0, 0, 0, 0))

    draw.ellipse(bbox, outline=OUTLINE, width=OUTLINE_WIDTH)
    draw.ellipse(inner_bbox, outline=OUTLINE, width=OUTLINE_WIDTH)

    return img


def _build_bar(session_percent: int, week_percent: int) -> Image.Image:
    """세로로 긴 막대 하나. 아래쪽부터 위로 채워진다."""
    bar_width, margin, radius = 30, 4, 6
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    left = (SIZE - bar_width) // 2
    right = left + bar_width
    top, bottom = margin, SIZE - margin
    draw.rounded_rectangle([left, top, right, bottom], radius=radius, fill=TRACK, outline=OUTLINE, width=4)

    height = bottom - top
    clamped = min(max(session_percent, 0), 100)
    fill_height = height * clamped / 100
    if fill_height > 0:
        draw.rounded_rectangle(
            [left, bottom - fill_height, right, bottom], radius=radius, fill=color_for_percent(session_percent)
        )

    return img


def _build_battery(session_percent: int, week_percent: int) -> Image.Image:
    """배터리 모양(둥근 몸통 + 작은 돌기)으로 생긴 게이지. 왼쪽부터
    오른쪽으로 채워진다 -- 실제 배터리 잔량 표시처럼 "얼마나 남았는지"를
    누구나 바로 알 수 있는 익숙한 모양을 그대로 가져왔다."""
    body_w, body_h = 46, 30
    x0, y0 = (SIZE - body_w) // 2, (SIZE - body_h) // 2
    x1, y1 = x0 + body_w, y0 + body_h
    nub_w, nub_h = 6, 14

    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([x0, y0, x1, y1], radius=6, outline=OUTLINE, width=5, fill=TRACK)
    draw.rounded_rectangle(
        [x1 - 2, y0 + (body_h - nub_h) // 2, x1 + nub_w, y0 + (body_h - nub_h) // 2 + nub_h],
        radius=3,
        fill=OUTLINE,
    )

    clamped = min(max(session_percent, 0), 100)
    pad = 6
    fill_width = (body_w - pad * 2) * clamped / 100
    if fill_width > 0:
        draw.rounded_rectangle(
            [x0 + pad, y0 + pad, x0 + pad + fill_width, y1 - pad], radius=3, fill=color_for_percent(session_percent)
        )

    return img


def _build_liquid(session_percent: int, week_percent: int) -> Image.Image:
    """물이 차오르는 것처럼, 원 안이 아래에서부터 위로 채워지는 모양."""
    margin = 3
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    bbox = [margin, margin, SIZE - margin, SIZE - margin]
    draw.ellipse(bbox, fill=TRACK)

    clamped = min(max(session_percent, 0), 100)
    fill_top = SIZE - margin - (SIZE - 2 * margin) * clamped / 100

    mask = Image.new("L", (SIZE, SIZE), 0)
    ImageDraw.Draw(mask).ellipse(bbox, fill=255)
    fill_layer = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    ImageDraw.Draw(fill_layer).rectangle([0, fill_top, SIZE, SIZE], fill=color_for_percent(session_percent))
    img.paste(fill_layer, (0, 0), Image.composite(fill_layer, img, mask).split()[3])

    draw.ellipse(bbox, outline=OUTLINE, width=6)
    return img


def _build_big_number(session_percent: int, week_percent: int) -> Image.Image:
    """상태에 따라 색이 바뀌는 네모 배경 안에, 퍼센트 숫자를 꽉 차게 크게
    그린다 -- 링 옆에 작게 붙은 숫자와 달리, 숫자 자체가 아이콘 크기 대비
    크게 차지하고 있어서 실제 트레이 크기로 작아져도 숫자가 잘 읽힌다."""
    margin = 4
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    color = color_for_percent(session_percent)
    draw.rounded_rectangle([margin, margin, SIZE - margin, SIZE - margin], radius=16, fill=color, outline=OUTLINE, width=3)

    text = str(min(max(session_percent, 0), 99))
    font = ImageFont.truetype(str(_FONT_PATH), 34)
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    text_color = (40, 40, 30) if color == YELLOW else (255, 255, 255)
    draw.text(((SIZE - text_w) / 2, (SIZE - text_h) / 2 - bbox[1]), text, font=font, fill=text_color)

    return img


STYLES = {
    "donut": _build_donut,
    "battery": _build_battery,
    "bar": _build_bar,
    "big_number": _build_big_number,
    "liquid": _build_liquid,
}
STYLE_LABELS = {
    "donut": "도넛 게이지",
    "battery": "배터리",
    "bar": "막대",
    "big_number": "숫자",
    "liquid": "원형 채움",
}
DEFAULT_STYLE = "donut"


LOGGED_OUT_COLOR = (150, 150, 150)


def _build_logged_out(style: str) -> Image.Image:
    """선택된 스타일의 모양은 그대로 두고, 상태를 나타내는 색(초록/노랑/빨강)만
    전부 무채색 회색으로 바꿔서 그린다 -- 로그아웃 상태에서도 색이 그대로
    남아있으면 마치 실제 사용량 수치인 것처럼 보여서 헷갈릴 수 있는데,
    사실 로그아웃 중엔 사용량 추적 자체를 안 하고 있으니 이건 오해를
    부르는 표시가 된다."""
    builder = STYLES.get(style, STYLES[DEFAULT_STYLE])
    img = builder(50, 50).convert("RGBA")
    pixels = img.load()
    for y in range(img.height):
        for x in range(img.width):
            r, g, b, a = pixels[x, y]
            if (r, g, b) in (GREEN, YELLOW, RED):
                pixels[x, y] = (*LOGGED_OUT_COLOR, a)
    return img


def build_icon_image(
    session_percent: int, week_percent: int, style: str = DEFAULT_STYLE, logged_out: bool = False
) -> Image.Image:
    if logged_out:
        return _build_logged_out(style)
    builder = STYLES.get(style, STYLES[DEFAULT_STYLE])
    return builder(session_percent, week_percent)
