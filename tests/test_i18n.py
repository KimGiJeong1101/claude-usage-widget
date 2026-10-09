"""i18n.py의 번역 테이블이 4개 언어 모두 똑같은 키 집합을 갖고 있는지
확인한다 -- 번역 키를 하나 추가하면서 언어 하나를 깜빡 빠뜨리면, 그
언어를 쓰는 사용자에게는 한국어 문구가 섞여 나오거나(i18n.t()의 폴백
동작 자체는 안전하지만) 트레이 아이콘 스타일 이름이 깨지는 식으로 조용히
드러난다 -- 이 테스트는 그걸 즉시 잡아준다."""

from usage_widget import i18n


def test_all_languages_have_the_same_translation_keys():
    tables = i18n._TRANSLATIONS
    languages = list(tables.keys())
    assert set(languages) == set(i18n.LANGUAGE_NAMES.keys())

    reference_keys = set(tables[i18n.DEFAULT_LANGUAGE].keys())
    for lang in languages:
        missing = reference_keys - set(tables[lang].keys())
        extra = set(tables[lang].keys()) - reference_keys
        assert not missing, f"'{lang}' 언어에 누락된 키: {missing}"
        assert not extra, f"'{lang}' 언어에만 있는 키(오타 가능성): {extra}"


def test_all_languages_have_the_same_tray_style_labels():
    tables = i18n._STYLE_LABELS
    reference_keys = set(tables[i18n.DEFAULT_LANGUAGE].keys())
    for lang, table in tables.items():
        assert set(table.keys()) == reference_keys, f"'{lang}' 트레이 스타일 라벨 키가 다르다"


def test_t_falls_back_to_default_language_for_unknown_language():
    assert i18n.t("tray.open", "xx-unknown") == i18n.t("tray.open", i18n.DEFAULT_LANGUAGE)


def test_t_formats_placeholders():
    text = i18n.t("update.new_version", "en", version="1.2.3", label="Update now")
    assert "1.2.3" in text
    assert "Update now" in text
