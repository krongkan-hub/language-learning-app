"""Small-screen, motion and contrast pins for the practice screen's CSS.

The page is used by a learner typing on a phone, sometimes with a screen
reader. These checks pin defects an accessibility pass had to fix: a fixed
side panel that ate the conversation column below ~700px, no
prefers-reduced-motion handling, and (checked computationally, not by eye)
whether the theme's own custom properties clear WCAG AA for text.

The markup half of that pass — accessible names, the live region, the drill's
focus trap, keyboard-operable scenario cards — is tested on the rendered page
in frontend/src/practice/a11y.test.tsx (`npm test`).
"""
import pathlib
import re

PAGE_PATH = (pathlib.Path(__file__).parent.parent.parent
             / 'frontend' / 'src' / 'practice' / 'practice.css')
PAGE = PAGE_PATH.read_text()


def test_focus_is_visible_everywhere():
    assert re.search(r':focus-visible\s*\{[^}]*outline\s*:\s*(?!none)', PAGE)
    # outline:none, outline:0 and outline-style:none all remove the ring
    assert not re.search(r'outline(-style)?\s*:\s*(none|0)\b', PAGE)


# ---------------------------------------------------------------------------
# 2. Small screens
# ---------------------------------------------------------------------------

def test_no_element_forces_width_past_a_375px_screen():
    # min-width, a fixed width and a flex basis can each force the page wider
    # (max-width only caps, so it is left out)
    for m in re.finditer(r'(?<![-\w])(min-width|width|flex-basis)\s*:\s*(\d+)px', PAGE):
        assert int(m.group(2)) <= 375, f'{m.group(1)}:{m.group(2)}px cannot fit a 375px screen'
    for m in re.finditer(r'flex\s*:\s*\d+\s+\d+\s+(\d+)px', PAGE):
        assert int(m.group(1)) <= 375, f'flex basis {m.group(1)}px cannot fit a 375px screen'


def test_the_side_panel_stacks_below_the_conversation_on_a_phone():
    # At 375px, a fixed 340px side panel leaves ~35px for the transcript.
    # Below 700px #main switches to a column and the panel gets a height
    # cap instead of a fixed width.
    small = PAGE.split('@media (max-width: 700px)')[1].split('\n  }\n')[0]
    assert '#main' in small and 'flex-direction:column' in small
    assert '#side' in small
    assert re.search(r'#side\s*\{[^}]*(?<![-\w])width:100%', small), '#side itself must go full width'
    assert 'overflow-y:auto' in small, 'a capped panel with no overflow can push past the viewport'


def test_the_kpi_grid_drops_to_two_columns_under_480px():
    small = PAGE.split('@media (max-width: 480px)')[1].split('\n  }\n')[0]
    assert '.kpis' in small
    assert 'repeat(2,1fr)' in small


def test_text_inputs_can_shrink_in_a_flex_row():
    # The UA default min-width:auto on a text input is sized off its `size`
    # attribute (20 characters) regardless of available space, which is what
    # actually forces the horizontal scrollbar in a narrow footer row.
    rule = PAGE.split('input[type=text] {')[1].split('}')[0]
    assert 'min-width:0' in rule


# ---------------------------------------------------------------------------
# 3. prefers-reduced-motion
# ---------------------------------------------------------------------------

def test_prefers_reduced_motion_is_respected():
    assert '@media (prefers-reduced-motion: reduce)' in PAGE
    block = PAGE.split('@media (prefers-reduced-motion: reduce)')[1].split('\n  }\n')[0]
    assert 'animation-duration' in block
    assert 'transition-duration' in block
    assert '!important' in block, 'a weaker rule can be overridden by the very rules it targets'


# ---------------------------------------------------------------------------
# 4. Colour contrast (computed, not eyeballed)
# ---------------------------------------------------------------------------

def _srgb_to_linear(c):
    c = c / 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def _luminance(hex_color):
    h = hex_color.lstrip('#')
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return 0.2126 * _srgb_to_linear(r) + 0.7152 * _srgb_to_linear(g) + 0.0722 * _srgb_to_linear(b)


def _contrast(hex_a, hex_b):
    la, lb = _luminance(hex_a), _luminance(hex_b)
    la, lb = max(la, lb), min(la, lb)
    return (la + 0.05) / (lb + 0.05)


TOKENS = (PAGE_PATH.parent.parent / 'tokens.css').read_text()
PAIRS = [(fg, bg) for fg in ('ink', 'dim', 'accent', 'good', 'bad') for bg in ('bg', 'panel')]


def _vars(block):
    return dict(re.findall(r'--([a-z-]+)\s*:\s*(#[0-9a-fA-F]{6})', block))


def _palettes():
    """Both palettes of the game theme (#62): light (the first :root) and
    night (the :root inside prefers-color-scheme: dark)."""
    light = TOKENS.split(':root {')[1].split('}')[0]
    dark = TOKENS.split('prefers-color-scheme: dark')[1].split('{', 2)[2].split('}')[0]
    forced = TOKENS.split(":root[data-theme='dark'] {")[1].split('}')[0]
    assert _vars(dark) == _vars(forced), 'the system-dark and chosen-dark palettes drifted apart'
    return {'light': _vars(light), 'dark': _vars(dark)}


def test_both_pages_draw_from_the_one_token_file():
    # Two :root palettes (practice.css and theme.css) once drifted apart.
    assert "@import '../tokens.css'" in PAGE
    assert "@import './tokens.css'" in (PAGE_PATH.parent.parent / 'theme.css').read_text()
    assert not re.search(r':root\s*\{[^}]*--bg', PAGE)


def test_root_palette_has_not_drifted():
    # The AA check below is only meaningful if these are still the values it
    # was computed against (game theme, 2026-10-15).
    p = _palettes()
    text = ('bg', 'panel', 'ink', 'dim', 'accent', 'good', 'bad')
    assert {k: p['light'][k] for k in text} == {
        'bg': '#f1f4ff', 'panel': '#ffffff', 'ink': '#1e1a3c', 'dim': '#545a7c',
        'accent': '#5636d3', 'good': '#1b7543', 'bad': '#c4283a',
    }, 'a light custom property changed — recompute the contrast ratios before touching this'
    assert {k: p['dark'][k] for k in text} == {
        'bg': '#15122c', 'panel': '#211d42', 'ink': '#ece9ff', 'dim': '#aaa7cf',
        'accent': '#a995ff', 'good': '#6fdc9b', 'bad': '#ff8d8d',
    }, 'a dark custom property changed — recompute the contrast ratios before touching this'


def test_body_text_colours_meet_aa_against_their_backgrounds():
    # Every (text, background) pair in both palettes against WCAG AA's 4.5:1.
    # Measured 2026-10-15 — light: ink 15.1/16.6, dim 6.1/6.7, accent
    # 6.7/7.3, good 5.2/5.7, bad 5.2/5.7; dark: ink 15.3/13.4, dim 7.9/6.9,
    # accent 7.3/6.4, good 10.7/9.4, bad 8.2/7.2 (on bg / panel).
    for mode, v in _palettes().items():
        for fg, bg in PAIRS:
            ratio = _contrast(v[fg], v[bg])
            assert ratio >= 4.5, f'{mode}: --{fg} on --{bg} is only {ratio:.2f}:1'


def test_the_game_tokens_used_for_text_meet_aa():
    # The corrected line and the red mark on a panel, text and gold on the
    # HUD, and ink on gold — in both palettes (review #54, #62).
    for mode, v in _palettes().items():
        for fg, bg in (('fixed', 'bg'), ('fixed', 'panel'), ('pen', 'bg'), ('pen', 'panel'),
                       ('on-cover', 'cover'), ('gold', 'cover'), ('ink', 'highlight')):
            ratio = _contrast(v[fg], v[bg])
            assert ratio >= 4.5, f'{mode}: --{fg} on --{bg} is only {ratio:.2f}:1'


def test_text_on_an_accent_button_meets_aa():
    for mode, v in _palettes().items():
        ratio = _contrast(v['on-accent'], v['accent'])
        assert ratio >= 4.5, f'{mode}: --on-accent on --accent is only {ratio:.2f}:1'




def test_the_stage_gives_way_to_the_conversation_on_a_small_screen():
    # A fixed 200px stage left the transcript ~50px on a 375x667 phone, below
    # zero with the drill open (review #55). Small or short screens hide it.
    rule = re.search(r'@media \(max-width: 700px\), \(max-height: 620px\) \{\s*#stage \{ display:none; \}', PAGE)
    assert rule, 'the stage must be hidden below 700px wide or 620px tall'
    # and the grin's lift is a translate, which cannot override a scale
    assert "[data-expression='grin'] { translate:" in PAGE
