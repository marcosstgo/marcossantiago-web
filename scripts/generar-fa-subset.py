import re, subprocess, pathlib
SRC = pathlib.Path('/home/corillo-adm/marcossantiago-web/src')
css  = pathlib.Path(__file__).parent / 'fa-all.css'.read_text()

# 1) Iconos realmente usados en el sitio (astro + mdx)
used = set()
for f in list(SRC.rglob('*.astro')) + list(SRC.rglob('*.mdx')):
    for m in re.findall(r'\bfa-[a-z0-9-]+', f.read_text(encoding='utf-8', errors='ignore')):
        used.add(m)
for junk in ('fa-solid','fa-brands','fa-regular','fa-subset'):
    used.discard(junk)

# 2) Mapa nombre -> codepoint desde all.min.css
mapping = {}
for sels, content in re.findall(r'([^{}]*?)\{--fa:\s*"?\\?([0-9a-f]{2,5})"?', css):
    for sel in re.findall(r'\.(fa-[a-z0-9-]+):{1,2}before', sels):
        mapping.setdefault(sel, content)
for sels, content in re.findall(r'([^{}]*?)\{content:\s*"\\([0-9a-f]{2,5})"', css):
    for sel in re.findall(r'\.(fa-[a-z0-9-]+):{1,2}before', sels):
        mapping.setdefault(sel, content)

# 3) Cuales son de marcas (brands)
brands_block = css[css.find('.fab,'):] if '.fab,' in css else ''
BRANDS = {'fa-behance','fa-github','fa-instagram','fa-telegram','fa-vimeo-v','fa-whatsapp',
          'fa-x-twitter','fa-youtube'}

found   = {i: mapping[i] for i in sorted(used) if i in mapping}
missing = sorted(i for i in used if i not in mapping)

out = ['/* Font Awesome 6.5 Free — subset: solo los iconos usados en el sitio.',
       '   Generado con scratchpad/mksubset.py a partir de all.min.css.',
       '   Al usar un icono nuevo en src/, hay que regenerar este archivo. */',
       '@font-face {',
       '  font-family: "Font Awesome 6 Free";',
       '  font-style: normal; font-weight: 900; font-display: block;',
       '  src: url("https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/webfonts/fa-solid-900.woff2") format("woff2");',
       '}',
       '@font-face {',
       '  font-family: "Font Awesome 6 Free";',
       '  font-style: normal; font-weight: 400; font-display: block;',
       '  src: url("https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/webfonts/fa-regular-400.woff2") format("woff2");',
       '}',
       '@font-face {',
       '  font-family: "Font Awesome 6 Brands";',
       '  font-style: normal; font-weight: 400; font-display: block;',
       '  src: url("https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/webfonts/fa-brands-400.woff2") format("woff2");',
       '}',
       '.fa-solid, .fas, .fa-regular, .far, .fab, .fa-brands {',
       '  font-style: normal; font-variant: normal; text-rendering: auto;',
       '  line-height: 1; display: inline-block;',
       '  -webkit-font-smoothing: antialiased;',
       '}',
       '.fa-solid, .fas { font-family: "Font Awesome 6 Free"; font-weight: 900 }',
       '.fa-regular, .far { font-family: "Font Awesome 6 Free"; font-weight: 400 }',
       '.fab, .fa-brands { font-family: "Font Awesome 6 Brands"; font-weight: 400 }',
       '']
w = max(len(i) for i in found)
out.append('/* Marcas */')
for i, c in found.items():
    if i in BRANDS: out.append(f'.{i}::before'.ljust(w+11) + f' {{ content: "\\{c}" }}')
out.append('/* Solid / Regular */')
for i, c in found.items():
    if i not in BRANDS: out.append(f'.{i}::before'.ljust(w+11) + f' {{ content: "\\{c}" }}')
out.append('')
pathlib.Path('/home/corillo-adm/marcossantiago-web/public/fa-subset.css').write_text('\n'.join(out))
print('iconos usados:', len(used), '| resueltos:', len(found), '| SIN resolver:', missing)
