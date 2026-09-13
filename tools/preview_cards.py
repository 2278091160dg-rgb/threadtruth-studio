"""Deterministic local card composition. Geometry is not a visual attestation."""
from pathlib import Path
from math import ceil

from PIL import Image, ImageDraw, ImageFont, ImageOps


CONTRACT = {
    'board': [1200, 1200],
    'cells': [[44, 140, 360, 480], [420, 140, 360, 480], [796, 140, 360, 480],
              [44, 636, 360, 480], [420, 636, 360, 480], [796, 636, 360, 480]],
    'title': [44, 16, 1112, 72], 'subtitle': [44, 92, 1112, 36],
    'footer': [44, 1128, 1112, 60],
    'fit': 'contain-no-upscale', 'padding': 'white',
    'jpeg_quality': 90, 'thumbnail': [600, 600],
    'footer_text': 'AI生成 · 排版衍生预览 · 非成片\nPREVIEW ONLY — NOT FINAL',
}


def rectangles(layout, original_sha256, dimensions):
    if not isinstance(layout, dict) or set(layout) != {'original_sha256', 'cells'}:
        raise ValueError('observed layout fields invalid')
    if layout['original_sha256'] != original_sha256:
        raise ValueError('observed layout source hash mismatch')
    cells = layout['cells']
    if not isinstance(cells, list) or len(cells) != 6:
        raise ValueError('six observed rectangles required')
    for cell in cells:
        if not isinstance(cell, list) or len(cell) != 4 or any(type(n) is not int for n in cell):
            raise ValueError('observed geometry invalid')
        x, y, w, h = cell
        if min(x, y) < 0 or min(w, h) <= 0 or x+w > dimensions[0] or y+h > dimensions[1]:
            raise ValueError('observed geometry invalid')
    for i, a in enumerate(cells):
        for b in cells[i+1:]:
            if a[0] < b[0]+b[2] and b[0] < a[0]+a[2] and a[1] < b[1]+b[3] and b[1] < a[1]+a[3]:
                raise ValueError('observed rectangles overlap')
    for row in (cells[:3], cells[3:]):
        if any(row[i][0]+row[i][2] > row[i+1][0] for i in (0, 1)):
            raise ValueError('observed column order invalid')
        if max(c[1] for c in row) >= min(c[1]+c[3] for c in row):
            raise ValueError('observed row order invalid')
    if max(c[1]+c[3] for c in cells[:3]) > min(c[1] for c in cells[3:]):
        raise ValueError('observed row order invalid')
    return cells


def transforms(cells):
    result = []
    for source, card in zip(cells, CONTRACT['cells']):
        w, h = source[2:]
        scale = min(1, 360/w, 480/h)
        fitted = [max(1, int(w*scale)), max(1, int(h*scale))]
        result.append({'source': source, 'card': card, 'scale': scale, 'fitted': fitted,
                       'paste': [card[0]+(360-fitted[0])//2, card[1]+(480-fitted[1])//2]})
    return result


def _text(draw, text, band, font_path, maximum):
    # All input characters remain present. Font size and wrapping may vary only
    # inside the dedicated band; never truncate or draw over an image card.
    for size in range(maximum, 17, -1):
        font = ImageFont.truetype(str(font_path), size)
        missing = bytes(font.getmask('\u0378'))
        if any(bytes(font.getmask(c)) == missing for c in set(text) if not c.isspace()):
            raise ValueError('supplied font lacks required label glyphs')
        lines = []
        for paragraph in text.split('\n'):
            line = ''
            for char in paragraph:
                if line and draw.textlength(line+char, font=font) > band[2]:
                    lines.append(line)
                    line = ''
                line += char
            lines.append(line)
        rendered = '\n'.join(lines)
        box = draw.multiline_textbbox((0, 0), rendered, font=font, spacing=4, align='center')
        w, h = ceil(box[2]-box[0]), ceil(box[3]-box[1])
        if w <= band[2] and h <= band[3]:
            x, y = band[0]+(band[2]-w)//2, band[1]+(band[3]-h)//2
            draw.multiline_text((x-box[0], y-box[1]), rendered, font=font,
                                fill=(25, 25, 25), spacing=4, align='center')
            return {'text': text, 'rendered': rendered, 'font_size': size, 'bounds': [x, y, w, h]}
    raise ValueError('complete label cannot fit reserved text band')


def render(native, cells, labels, font_path, directory, style):
    font = ImageFont.truetype(str(font_path), 24)
    board = Image.new('RGB', tuple(CONTRACT['board']), 'white')
    fitted = transforms(cells)
    with Image.open(native) as opened:
        source = ImageOps.exif_transpose(opened).convert('RGB')
        for transform in fitted:
            x, y, w, h = transform['source']
            panel = source.crop((x, y, x+w, y+h))
            if list(panel.size) != transform['fitted']:
                panel = panel.resize(tuple(transform['fitted']), Image.Resampling.LANCZOS)
            board.paste(panel, tuple(transform['paste']))
    draw = ImageDraw.Draw(board)
    text = {name: _text(draw, labels[name], CONTRACT[name], font_path, size)
            for name, size in [('title', 34), ('subtitle', 26), ('footer', 22)]}
    display = Path(directory) / f'{style}-display.jpg'
    thumb = Path(directory) / f'{style}-thumb.jpg'
    board.save(display, 'JPEG', quality=90, optimize=True, progressive=True)
    board.resize((600, 600), Image.Resampling.LANCZOS).save(thumb, 'JPEG', quality=90, optimize=True, progressive=True)
    return {'font_name': ' '.join(font.getname()), 'transforms': fitted, 'text': text}
