"""Tests for font loading and text rendering."""

from pathlib import Path

import pytest

from sids_3dx_utils import ops
from sids_3dx_utils.text import Font, FontError, list_fonts, render_text
from sids_3dx_utils.world import count_objects, iter_objects

REPO_ROOT = Path(__file__).resolve().parent.parent
FONTS_DIR = REPO_ROOT / "fonts"

pytestmark = pytest.mark.skipif(
    not (FONTS_DIR / "arial" / "arial.world").is_file(),
    reason="arial font assets not present",
)


@pytest.fixture(scope="module")
def arial() -> Font:
    return Font.load(FONTS_DIR / "arial")


def test_font_load_covers_all_glyphs(arial):
    # arial.json declares 65 glyphs; every one should get geometry
    assert len(arial.glyphs) == 65
    for needed in "AZaz09.:":
        assert arial.has(needed)


def test_glyph_objects_are_disjoint(arial):
    seen = set()
    for glyph in arial.glyphs.values():
        for obj in glyph.objects:
            key = id(obj)
            assert key not in seen, "object assigned to two glyphs"
            seen.add(key)


def test_render_simple_text(arial):
    world = render_text(arial, "AB")
    total = count_objects(world)
    expected = len(arial.glyphs["A"].objects) + len(arial.glyphs["B"].objects)
    assert total == expected
    # B must be to the right of A
    xs_by_type = sorted(o["p"][0] for o in iter_objects(world))
    assert xs_by_type[0] < xs_by_type[-1]


def test_render_applies_scale_color_position(arial):
    plain = render_text(arial, "A")
    scaled = render_text(
        arial, "A", scale=2.0, color=(1.0, 0.0, 0.0),
        position=(100.0, 50.0, -5.0),
    )
    assert count_objects(scaled) == count_objects(plain)
    obj = next(iter_objects(scaled))
    assert obj["c"] == [1.0, 0.0, 0.0]
    stats = ops.world_stats(scaled)
    assert stats["bounds"]["min"][0] >= 100.0 - 1e-6
    # scaled sizes are doubled relative to plain
    plain_s = sorted(o["s"][0] for o in iter_objects(plain))
    scaled_s = sorted(o["s"][0] for o in iter_objects(scaled))
    assert scaled_s[0] == pytest.approx(plain_s[0] * 2.0)


def test_render_space_advances_cursor(arial):
    tight = render_text(arial, "AA")
    spaced = render_text(arial, "A A")
    tight_w = ops.world_stats(tight)["bounds"]
    spaced_w = ops.world_stats(spaced)["bounds"]
    assert (spaced_w["max"][0] - spaced_w["min"][0]) > (
        tight_w["max"][0] - tight_w["min"][0]
    )


def test_render_multiline_and_align(arial):
    world = render_text(arial, "AAAA\nAA", align="center")
    ys = sorted({round(o["p"][1], 1) for o in iter_objects(world)})
    # two distinct line bands
    assert ys[0] < -arial.line_spacing / 2
    world_left = render_text(arial, "AAAA\nAA", align="left")

    # centered second line starts further right than left-aligned one
    def second_line_min_x(w):
        objs = [o for o in iter_objects(w) if o["p"][1] < -4]
        return min(o["p"][0] for o in objs)

    assert second_line_min_x(world) > second_line_min_x(world_left)


def test_render_case_fallback_and_missing(arial):
    # ABC Enlarged has no lowercase; arial has both, so use a char that
    # only exists in one case: ':' exists, ';' does not.
    world = render_text(arial, ":;")
    assert count_objects(world) == len(arial.glyphs[":"].objects)


def test_render_rejects_bad_args(arial):
    with pytest.raises(ValueError):
        render_text(arial, "A", align="justified")
    with pytest.raises(ValueError):
        render_text(arial, "A", scale=0)


def test_list_fonts_reports_usable_and_broken():
    info = list_fonts(FONTS_DIR)
    assert info["arial"]["usable"] is True
    assert info["arial"]["glyphs"] == 65
    assert info["balloon"]["usable"] is False
    assert "error" in info["balloon"]


def test_font_load_missing_dir():
    with pytest.raises(FontError):
        Font.load(FONTS_DIR / "balloon")
