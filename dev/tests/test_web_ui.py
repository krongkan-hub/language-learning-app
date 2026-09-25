"""Accessibility and small-screen correctness pins for app/static/index.html.

This is the whole web front end in one hand-written file, used by a learner
typing on a phone, sometimes with a screen reader. These checks pin the
specific defects that pass had to fix: no aria-live anywhere, several
controls with no accessible name, a "drill" dialog with no focus management,
a fixed side panel that eats the conversation column below ~700px, no
prefers-reduced-motion handling, and (checked computationally, not by eye)
whether the theme's own custom properties clear WCAG AA for text.

Parsed with html.parser and regex only — no new dependency.
"""
import pathlib
import re
from html.parser import HTMLParser

PAGE_PATH = pathlib.Path(__file__).parent.parent.parent / 'app' / 'static' / 'index.html'
PAGE = PAGE_PATH.read_text()


# ---- a minimal tag collector: every element, its attrs, and its own text ----
class _Elements(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.tags = []  # (tag, attrs dict, text accumulated inside)

    def handle_starttag(self, tag, attrs):
        rec = {'tag': tag, 'attrs': dict(attrs), 'text': ''}
        self.tags.append(rec)
        self.stack.append(rec)

    def handle_startendtag(self, tag, attrs):
        self.tags.append({'tag': tag, 'attrs': dict(attrs), 'text': ''})

    def handle_endtag(self, tag):
        # pop the nearest matching open tag; tolerant of the odd unclosed
        # <input>/<br> in this file, which never call handle_endtag
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i]['tag'] == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        for rec in self.stack:
            rec['text'] += data


def _parse():
    p = _Elements()
    p.feed(PAGE)
    return p.tags


ELEMENTS = _parse()
LABEL_FORS = {e['attrs'].get('for') for e in ELEMENTS if e['tag'] == 'label'}


def _accessible_name(el):
    """Best-effort accessible name: aria-label, a <label for>, visible text,
    or (for an input) a placeholder — matching the priority real UAs use."""
    attrs = el['attrs']
    if attrs.get('aria-label', '').strip():
        return attrs['aria-label'].strip()
    if attrs.get('aria-labelledby', '').strip():
        return attrs['aria-labelledby'].strip()  # presence is enough here
    if attrs.get('id') in LABEL_FORS:
        return '(labelled)'
    if el['text'].strip():
        return el['text'].strip()
    if attrs.get('placeholder', '').strip():
        return attrs['placeholder'].strip()
    return ''


# ---------------------------------------------------------------------------
# 1. Keyboard and screen reader
# ---------------------------------------------------------------------------

def test_every_button_has_an_accessible_name():
    buttons = [e for e in ELEMENTS if e['tag'] == 'button']
    assert len(buttons) >= 10, 'fewer buttons than expected; this file changed shape'
    for b in buttons:
        assert _accessible_name(b), f"button with no accessible name: {b['attrs']}"


def test_every_text_input_has_an_accessible_name():
    inputs = [e for e in ELEMENTS if e['tag'] == 'input'
              and e['attrs'].get('type') == 'text']
    assert len(inputs) >= 3, 'fewer text inputs than expected; this file changed shape'
    for i in inputs:
        assert _accessible_name(i), f"input with no accessible name: {i['attrs']}"


def test_npc_turns_get_a_polite_live_region_not_the_visible_log():
    # #log grows by streaming text into an existing node (partial-sentence
    # appends), which is exactly the case where marking it aria-live spams
    # or silences a screen reader depending on aria-relevant. The fix is a
    # separate hidden region, updated once per completed turn.
    log = next(e for e in ELEMENTS if e['attrs'].get('id') == 'log')
    assert 'aria-live' not in log['attrs'], (
        '#log itself should not be aria-live; see srAnnounce')
    ann = next(e for e in ELEMENTS if e['attrs'].get('id') == 'srAnnounce')
    assert ann['attrs'].get('aria-live') == 'polite'
    assert 'sr-only' in ann['attrs'].get('class', '')
    # it has to actually be written to when a turn completes
    npc_branch = PAGE.split("ev.type==='npc'")[1].split("else if(ev.type")[0]
    assert "$('srAnnounce').textContent" in npc_branch


def test_the_scenario_cards_are_keyboard_operable_with_a_readable_name():
    # <div class="scen" onclick=...> has no tab stop and no Enter/Space
    # activation at all — a mouse-only control in a keyboard-first list.
    body = PAGE.split('async function pickLang')[1].split('\nfunction filterScenarios')[0]
    assert "card.setAttribute('role', 'button')" in body
    assert 'card.tabIndex = 0' in body
    assert "e.key === 'Enter'" in body and "e.key === ' '" in body
    assert "card.setAttribute('aria-label'" in body


def test_the_drill_is_a_labelled_modal_dialog():
    drill = next(e for e in ELEMENTS if e['attrs'].get('id') == 'drill')
    assert drill['attrs'].get('role') == 'dialog'
    assert drill['attrs'].get('aria-modal') == 'true'
    assert drill['attrs'].get('aria-labelledby')


def test_the_drill_traps_tab_and_handles_escape():
    handler = PAGE.split("$('drill').addEventListener('keydown'")[1].split('\n});')[0]
    assert "e.key === 'Tab'" in handler
    assert 'preventDefault' in handler
    assert "e.key === 'Escape'" in handler
    # Escape must not be a silent no-op, and must not fabricate a skip the
    # server refuses (409) mid-drill — it hands focus to the one control
    # that already works unconditionally in every state.
    assert "$('endBtn').focus()" in handler


def test_focus_is_visible_everywhere():
    assert re.search(r':focus-visible\s*\{[^}]*outline\s*:\s*(?!none)', PAGE)
    assert 'outline:none' not in PAGE.replace(' ', '')
    assert 'outline: none' not in PAGE


# ---------------------------------------------------------------------------
# 2. Small screens
# ---------------------------------------------------------------------------

def test_no_element_forces_width_past_a_375px_screen():
    for m in re.finditer(r'min-width\s*:\s*(\d+)px', PAGE):
        assert int(m.group(1)) <= 375, f'min-width:{m.group(1)}px cannot fit a 375px screen'


def test_the_side_panel_stacks_below_the_conversation_on_a_phone():
    # At 375px, a fixed 340px side panel leaves ~35px for the transcript.
    # Below 700px #main switches to a column and the panel gets a height
    # cap instead of a fixed width.
    small = PAGE.split('@media (max-width: 700px)')[1].split('\n  }\n')[0]
    assert '#main' in small and 'flex-direction:column' in small
    assert '#side' in small
    assert 'width:100%' in small
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


def _root_vars():
    root = PAGE.split(':root {')[1].split('}')[0]
    return dict(re.findall(r'--([a-z]+)\s*:\s*(#[0-9a-fA-F]{6})', root))


def test_root_palette_has_not_drifted():
    # The AA check below is only meaningful if these are still the values it
    # was computed against.
    v = _root_vars()
    assert v == {
        'bg': '#12141a', 'panel': '#1a1d26', 'line': '#2a2f3d', 'ink': '#e6e8ee',
        'dim': '#8b93a7', 'accent': '#7aa2f7', 'good': '#9ece6a', 'bad': '#f7768e',
    }, 'a custom property changed — recompute the contrast ratios before touching this'


def test_body_text_colours_meet_aa_against_their_backgrounds():
    # Every (text, background) custom-property pair actually used for body
    # text in this file, checked against WCAG AA's 4.5:1 floor for normal
    # text. Ratios as measured (bg/panel are the two backgrounds text sits
    # on): ink/bg 15.03, ink/panel 13.74, dim/bg 5.99, dim/panel 5.47,
    # accent/bg 7.31, accent/panel 6.68, good/bg 10.07, good/panel 9.21,
    # bad/bg 6.96, bad/panel 6.36 — all comfortably clear 4.5:1, so no
    # property changed; this test exists to catch a future edit that
    # weakens one without anyone re-checking the number.
    v = _root_vars()
    pairs = [
        ('ink', 'bg'), ('ink', 'panel'),
        ('dim', 'bg'), ('dim', 'panel'),
        ('accent', 'bg'), ('accent', 'panel'),
        ('good', 'bg'), ('good', 'panel'),
        ('bad', 'bg'), ('bad', 'panel'),
    ]
    for fg, bg in pairs:
        ratio = _contrast(v[fg], v[bg])
        assert ratio >= 4.5, f'--{fg} on --{bg} is only {ratio:.2f}:1'


def test_the_accent_focus_ring_clears_the_non_text_contrast_floor():
    # WCAG 2.4.11 / 1.4.11 want 3:1 for a focus indicator against the
    # background it sits on, a lower bar than body text.
    v = _root_vars()
    for bg in ('bg', 'panel'):
        ratio = _contrast(v['accent'], v[bg])
        assert ratio >= 3.0, f'focus outline (--accent) on --{bg} is only {ratio:.2f}:1'
