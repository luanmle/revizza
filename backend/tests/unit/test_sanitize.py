from apps.notes.sanitize import sanitize_field_values, sanitize_html


def test_strips_script_and_event_handlers():
    dirty = '<b>ok</b><script>alert(1)</script><img src="x.png" onerror="alert(1)">'
    clean = sanitize_html(dirty)
    assert "<script" not in clean
    assert "onerror" not in clean
    assert "<b>ok</b>" in clean
    assert '<img src="x.png">' in clean


def test_blocks_javascript_urls():
    assert "javascript:" not in sanitize_html('<a href="javascript:alert(1)">x</a>')


def test_keeps_anki_compatible_formatting():
    html = (
        '<span style="font-size:18px">A</span>'
        '<div style="text-align:center">B</div><ul><li>i</li></ul><u>u</u>'
    )
    assert sanitize_html(html) == html


def test_only_keeps_required_style_properties():
    clean = sanitize_html(
        '<div style="position:fixed;background:url(javascript:x);text-align:right">x</div>'
    )
    assert clean == '<div style="text-align:right">x</div>'


def test_sanitize_field_values_covers_all_fields():
    result = sanitize_field_values(
        {"Frente": "<script>x</script>oi", "Verso": "<i>ok</i>"}
    )
    assert result == {"Frente": "oi", "Verso": "<i>ok</i>"}
