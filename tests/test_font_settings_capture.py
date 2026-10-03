import simple_extract as app


def test_original_font_settings_are_captured_once(monkeypatch):
    app._original_font_settings.clear()
    app._font_settings_captured = False
    calls = []

    def fake_read():
        calls.append(True)
        return {
            "font_smoothing": 0,
            "font_smoothing_type": 1,
            "reg_FontSmoothing": "0",
            "reg_FontSmoothingType": 1,
        }

    monkeypatch.setattr(app, "_read_original_font_settings", fake_read)

    app._capture_original_font_settings_once()
    first = dict(app._original_font_settings)
    app._capture_original_font_settings_once()

    assert len(calls) == 1
    assert app._original_font_settings == first
