"""Write the Hearth, Studio and Instrument token blocks into src/styles/tokens.css (0.17 UX1, PP-D38).

Each theme is a small palette (THEMES below) plus its type, corner and size tokens. The script reads the roles the
Normal blocks set, gives every one of them a value in the theme's light and dark blocks (its own primitives for
surfaces, text, borders and the accent; Normal's for status, data context and type hues), and replaces the region
between the two UX1 markers. Run it after changing a palette, then run `npx vitest run src/styles/tokens.test.ts`:
the contrast minimums decide whether a palette is allowed.

    python3 frontend/tools/gen_themes.py
"""
import re, sys, pathlib
P = pathlib.Path(__file__).resolve().parents[1] / 'src' / 'styles' / 'tokens.css'
css = P.read_text()
START, END = '/* --- UX1 themes: generated region start --- */', '/* --- UX1 themes: generated region end --- */'
if START in css:
    css = css[:css.index(START)] + css[css.index(END) + len(END):].lstrip('\n')

def block(sel, start=0):
    i = css.index(sel + ' {', start); j = css.index('{', i); d = 0
    for k in range(j, len(css)):
        if css[k] == '{': d += 1
        if css[k] == '}':
            d -= 1
            if d == 0: return css[j + 1:k]
def decls(b):
    return dict((m.group(1), m.group(2).strip()) for m in re.finditer(r'--([a-z0-9-]+):\s*([^;]+);', re.sub(r'/\*[\s\S]*?\*/', '', b)))
normal_light = decls(block(':root'))
normal_dark = decls(block(':root[data-theme="dark"]'))
ROLES = list(normal_dark.keys())

KEYS = dict(app='surface-app', top='surface-top', nav='surface-nav', raised='surface-raised', sunken='surface-sunken',
            hover='surface-hover', fill='surface-fill', t1='text-primary', t2='text-secondary', t3='text-tertiary',
            tph='text-placeholder', on='text-on-action', bf='border-faint', bs='border-subtle', bst='border-strong',
            bc='border-control', bch='border-control-hover', ac='action-primary', ach='action-primary-hover',
            link='link', focus='focus-color', sel='state-selected', selt='state-selected-text',
            sell='state-selected-line', sth='state-hover')
def pal(s):
    return dict(pair.split('=') for pair in s.split())
THEMES = {
 'hearth': dict(
   light=pal('app=#f6f2ec top=#fffdf9 nav=#f3eee7 raised=#fffdf9 sunken=#f1ece4 hover=#ebe5db fill=#ebe5db t1=#24201a t2=#564f45 t3=#645d52 tph=#6e675b on=#ffffff bf=#ece6dc bs=#e5ded2 bst=#cfc6b7 bc=#8a8174 bch=#645d52 ac=#4853d4 ach=#3b46c0 link=#404bcb focus=#4853d4 sel=#e9ebfc selt=#2a3391 sell=#c5caf5 sth=#f3eee7'),
   dark=pal('app=#181613 top=#1d1b18 nav=#1b1916 raised=#211f1b sunken=#141310 hover=#2a2722 fill=#2a2722 t1=#f1ede5 t2=#c0b9aa t3=#a8a192 tph=#989182 on=#14163a bf=#2a2722 bs=#36322b bst=#4d483f bc=#7d7669 bch=#a8a192 ac=#9aa3ff ach=#b3baff link=#a3abff focus=#9aa3ff sel=#272a4d selt=#d5d9ff sell=#3d427a sth=#1d1b18'),
   shadow_l='60, 45, 20', shadow_d='0, 0, 0',
   # Titles in Fraunces at 500: a serif with the weight to stand beside the sans section headings.
   extra={'font-display': '"Fraunces Variable", "Fraunces", "Iowan Old Style", Georgia, serif', 'display-weight': '500', 'display-tracking': '-0.015em',
          'radius-control': '8px', 'radius-button': '8px', 'card-radius': '12px', 'radius-overlay': '18px', 'radius-xs': '5px', 'radius-panel': '10px', 'radius-large': '14px', 'control-height': '36px', 'shadow-card': 'var(--shadow-sm)', 'text-2xl': '32px'}),
 'studio': dict(
   light=pal('app=#efeaf6 top=#ffffff nav=#efeaf6 raised=#ffffff sunken=#f5f3fa hover=#e9e5f2 fill=#e9e5f2 t1=#1d1a26 t2=#4f4960 t3=#5d576d tph=#676178 on=#ffffff bf=#efecf5 bs=#e7e3ef bst=#cfc9dd bc=#837d97 bch=#5d576d ac=#4a53e0 ach=#3d46cc link=#444dd8 focus=#4a53e0 sel=#eaebff selt=#2b3299 sell=#c6c9fb sth=#f5f3fa'),
   dark=pal('app=#100f16 top=#1a1922 nav=#100f16 raised=#1a1922 sunken=#14131a hover=#22212c fill=#22212c t1=#f0eef7 t2=#bdb8cf t3=#a39eb8 tph=#948fa9 on=#12133a bf=#24232e bs=#2e2c3a bst=#45425a bc=#7a7591 bch=#a39eb8 ac=#99a0ff ach=#b4b9ff link=#a4aaff focus=#99a0ff sel=#272850 selt=#d6d8ff sell=#3e407d sth=#1a1922'),
   shadow_l='60, 50, 140', shadow_d='0, 0, 0',
   extra={'font-display': '"Bricolage Grotesque Variable", "Bricolage Grotesque", var(--font-sans)', 'display-weight': '650', 'display-tracking': '-0.03em',
          'radius-control': '10px', 'radius-button': '999px', 'card-radius': '16px', 'radius-overlay': '26px', 'radius-xs': '6px', 'radius-panel': '14px', 'radius-large': '20px', 'control-height': '38px', 'shadow-card': 'none', 'card-surface': 'var(--surface-sunken)', 'card-border': 'transparent', 'fs-12-5': '13px', 'fs-13': '13.5px', 'fs-13-5': '14px', 'fs-14': '14.5px', 'text-sm': '13.5px', 'text-md': '14.5px', 'text-lg': '16px', 'text-xl': '21px', 'text-2xl': '34px'}),
 'instrument': dict(
   light=pal('app=#fbfaf8 top=#fbfaf8 nav=#f3f1ed raised=#ffffff sunken=#f3f1ed hover=#eceae5 fill=#eceae5 t1=#1c1b19 t2=#55514a t3=#625e57 tph=#6c6860 on=#ffffff bf=#efece7 bs=#e9e6e0 bst=#d3cfc6 bc=#88837a bch=#625e57 ac=#3f49c9 ach=#323bb0 link=#3a44c2 focus=#3f49c9 sel=#eceefb selt=#26339a sell=#c9cff5 sth=#f6f5f2'),
   dark=pal('app=#111113 top=#111113 nav=#18181b raised=#151517 sunken=#18181b hover=#1f1f23 fill=#1f1f23 t1=#ececee t2=#b4b3ba t3=#9a99a1 tph=#8d8c95 on=#10153d bf=#1f1f23 bs=#26262b bst=#3a3a42 bc=#74737c bch=#9a99a1 ac=#9aa4ff ach=#b5bcff link=#a7b1ff focus=#9aa4ff sel=#23264a selt=#d3d8ff sell=#3a4280 sth=#18181b'),
   shadow_l='20, 20, 30', shadow_d='0, 0, 0',
   # Type: Inter for text (open shapes and a tall x-height, so the theme stays dense and still reads at 12 to 13.5px);
   # titles keep Instrument Sans. No text below 11px, running text and table cells at 13px or more.
   extra={'font-sans': '"Inter Variable", "Inter", ui-sans-serif, system-ui, sans-serif',
          'font-display': '"Instrument Sans Variable", "Instrument Sans", ui-sans-serif, system-ui, sans-serif', 'display-weight': '620', 'display-tracking': '-0.015em',
          'radius-control': '6px', 'radius-button': '6px', 'card-radius': '6px', 'radius-overlay': '10px', 'radius-xs': '4px', 'radius-panel': '6px', 'radius-large': '8px', 'control-height': '30px', 'shadow-card': 'none', 'fs-10': '11px', 'fs-13-5': '13px', 'fs-14': '13.5px', 'fs-15': '14.5px', 'text-md': '13.5px', 'text-lg': '14.5px', 'text-xl': '17px', 'text-2xl': '22px', 'topbar-height': '48px'}),
}
DARK_BAR = {'selection-bar-surface': 'fill', 'selection-bar-border': 'bst', 'selection-bar-text': 't1', 'selection-bar-action': 'ac', 'selection-bar-hover': 'hover', 'selection-bar-muted': 't2'}
def shadows(rgb, dark):
    a = (0.42, 0.4, 0.5, 0.6, 0.55) if dark else (0.3, 0.06, 0.14, 0.24, 0.2)
    return {'backdrop': f'rgba({rgb}, {a[0]})', 'shadow-sm': f'0 1px 2px rgba({rgb}, {a[1]})', 'shadow-md': f'0 8px 24px rgba({rgb}, {a[2]})',
            'shadow-overlay': f'0 24px 64px rgba({rgb}, {a[3]})', 'shadow-sheet': f'0 -12px 40px rgba({rgb}, {a[4]})'}
def roles(name, mode):
    t = THEMES[name]; p = t[mode]; base = normal_light if mode == 'light' else normal_dark
    out = {}
    own = {role: f'var(--{name}-{mode}-{key})' for key, role in KEYS.items()}
    sh = shadows(t['shadow_l'] if mode == 'light' else t['shadow_d'], mode == 'dark')
    for r in ROLES:
        if r in own: out[r] = own[r]
        elif r in sh: out[r] = sh[r]
        elif r == 'selection-bar-danger': out[r] = 'var(--status-error-action)'
        elif mode == 'dark' and r in DARK_BAR: out[r] = f'var(--{name}-dark-{DARK_BAR[r]})'
        else: out[r] = base[r]
    return out
def emit(sel, d, indent='  ', head=()):
    lines = [f'{sel} {{'] + [indent + h for h in head] + [f'{indent}--{k}: {v};' for k, v in d.items()] + ['}']
    return '\n'.join(lines)
out = [START, '''/* Hearth, Studio and Instrument (0.17 UX1, PP-D38): themes chosen on Settings › Appearance (`data-scheme`), beside
   Normal (no attribute, the reference) and Website purple. Each sets every role the Normal blocks set, in light
   and in dark; its own colours are primitives named after it, held in its light block, and the status, context
   and type-hue roles keep Normal's. A theme also sets its display typeface, corners and control height here; its
   frame is `data-frame` (app/ShellFrame). Written by `frontend/tools/gen_themes.py`: change a palette there and run
   it, not by hand. */''']
for name, t in THEMES.items():
    prim = {f'{name}-{mode}-{key}': val for mode in ('light', 'dark') for key, val in t[mode].items()}
    light = {**prim, **roles(name, 'light'), **t['extra']}
    dark = roles(name, 'dark')
    out.append(emit(f':root[data-scheme="{name}"]', light, head=['color-scheme: light;']))
    out.append(emit(f':root[data-scheme="{name}"][data-theme="dark"]', dark, head=['color-scheme: dark;']))
    inner = emit(f'  :root[data-scheme="{name}"]:not([data-theme="light"])', dark, indent='    ', head=['color-scheme: dark;']).replace('\n}', '\n  }')
    out.append('@media (prefers-color-scheme: dark) {\n' + inner + '\n}')
out.append(END)
anchor = '/* Type palette A (U-D13, Settings › Appearance)'
assert anchor in css
css = css.replace(anchor, '\n\n'.join(out) + '\n\n' + anchor, 1)
# Normal gains the tokens a theme may change (once).
if '--font-display:' not in css.split(START)[0]:
    a = '  --text-xs: 12px;'
    css = css.replace(a, '  /* The typeface of page and record titles; a theme may name another (0.17 UX1). */\n  --font-display: var(--font-sans);\n  --display-weight: 600;\n  --display-tracking: -0.015em;\n' + a, 1)
    a = '  --card-radius: 8px;'
    css = css.replace(a, a + '\n  /* Sheets, dialogs and menus (0.17 UX1). */\n  --radius-overlay: 12px;\n  /* A resting card\'s shadow; none in Normal, whose cards are bordered. */\n  --shadow-card: none;\n  /* Motion (0.17 UX1): hover and press, menus and toasts, sheets and page entrance. */\n  --motion-fast: 120ms;\n  --motion: 200ms;\n  --motion-slow: 320ms;\n  --ease-out: cubic-bezier(0.2, 0.8, 0.2, 1);\n  --ease-in: cubic-bezier(0.4, 0, 1, 1);', 1)
P.write_text(css)
print('ok', len(css.splitlines()))
