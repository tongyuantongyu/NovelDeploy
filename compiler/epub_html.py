import re
import random
from typing import Match, Tuple

fnorder = ['①', '②', '③', '④', '⑤', '⑥', '⑦', '⑧', '⑨', '⑩', '⑪', '⑫', '⑬', '⑭', '⑮', '⑯',
           '⑰', '⑱', '⑲', '⑳', '㉑', '㉒', '㉓', '㉔', '㉕', '㉖', '㉗', '㉘', '㉙', '㉚', '㉛', '㉜',
           '㉝', '㉞', '㉟', '㊱', '㊲', '㊳', '㊴', '㊵', '㊶', '㊷', '㊸', '㊹', '㊺', '㊻', '㊼', '㊽',
           '㊾', '㊿']
oforder = ['❶', '❷', '❸', '❹', '❺', '❻', '❼', '❽', '❾', '❿', '⓫', '⓬', '⓭', '⓮', '⓯', '⓰',
           '⓱', '⓲', '⓳', '⓴']

note = '<a epub:type="noteref" href="#{1}" class="notetag">{0}</a>'
fnside = '<aside epub:type="footnote" id="{0}"><h4>译者注释：</h4>{1}</aside>'
ofside = '<aside epub:type="footnote" id="{0}"><h4>作者注释：</h4>{1}</aside>'
trside = '<aside epub:type="footnote" id="{0}"><p>{1}</p></aside>'

htmlbase = '<?xml version="1.0" encoding="utf-8"?><!DOCTYPE html>' \
           '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">' \
           '<head><title>{ptitle}</title></head>' \
           '<body><div>{title}{content}</div></body></html>'


class Counter:
    def __init__(self, series):
        self.series = series
        self.count = -1

    def get(self):
        self.count += 1
        return self.series[self.count], 'note_' + hex(random.randint(0, 1 << 32 - 1))[2:]


class EmptyTexError(RuntimeError):
    def __init__(self, *args):
        super().__init__(self, *args)


def gen_ruby_html(match: Match) -> str:
    """Convert matched ruby tex code into plain text for bbs usage
    \ruby{A}{B} -> <ruby><rb>A</rb><rp>（</rp><rt>B</rt><rp>）</rp></ruby>

    Also support | split ruby
    \ruby{椎名|真昼}{しいな|まひる} ->
    <ruby><rb>椎名</rb><rp>（</rp><rt>しいな</rt><rp>）</rp><rb>真昼</rb><rp>（</rp><rt>まひる</rt><rp>）</rp></ruby>
    """
    return ''.join('<ruby><rb>{}</rb><rp>（</rp><rt>{}</rt><rp>）</rp></ruby>'.format(*pair) for pair in
                   zip(match['word'].split('|'), match['ruby'].split('|')))


def gen_note_html(note):
    return ''.join(f'<p>{line}</p>' for line in note.split('\\\\'))


def format_line(source_line: str, fts: Counter, ofs: Counter) -> str:
    if '\\psline' in source_line:
        return '<hr>'
    if '\\vspace{2\\baselineskip}' in source_line:
        return '<p><br/></p>'
    if '\\begin{itemize}' in source_line:
        return '<ul>'
    if '\\end{itemize}' in source_line:
        return '</ul>'
    if '\\item' in source_line:
        _line = source_line.replace('\\item', '').replace(' ', '')
        return f"<li>{_line}</li>"
    processed_line = source_line
    # {\jpfont にほんご} -> にほんご
    processed_line = processed_line.replace("\\sqsplit", "◇◇◇◇◇◇◇◇")
    processed_line = processed_line.replace("\\cardline", "  --------")
    processed_line = re.sub(r'\\textbf{(?P<word>.+?)}', '<b>\\g<word></b>', processed_line)
    processed_line = re.sub(r'\\gray{(?P<word>.+?)}', '<span style="color:gray">\\g<word></color>', processed_line)
    processed_line = re.sub(r' {\\jpfont (?P<word>.+?)}', '<span lang="ja">\\g<word></span>', processed_line)
    processed_line = re.sub(r'(?<=}){\\jpfont (?P<word>.+?)}(?!\|)', '{<span lang="ja">\\g<word></span>}',
                            processed_line)
    processed_line = re.sub(r'(?<=[{|]){\\jpfont (?P<word>.+?)}', '<span lang="ja">\\g<word></span>', processed_line)
    # format ruby using ruby_func
    additional = ''
    processed_line = re.sub(r'\\ruby{(?P<word>.+?)}{(?P<ruby>.+?)}', gen_ruby_html, processed_line)
    for match in re.finditer(r'\\trans{(?P<word>.+?)}{(?P<trans>.+?)}', processed_line):
        _id = 'trans_' + hex(random.randint(0, 1 << 32 - 1))[2:]
        processed_line = processed_line.replace(match[0], match['word'] + note.format('译', _id))
        additional += trside.format(_id, match['trans'])
    additional_note = ''
    for match in re.finditer(r'\\footnote{(?P<note>.+?)}', processed_line):
        count, _id = fts.get()
        processed_line = processed_line.replace(match[0], note.format(count, _id))
        additional_note += fnside.format(_id, gen_note_html(match['note']))
    additional_onote = ''
    for match in re.finditer(r'\\ofnote{(?P<note>.+?)}', processed_line):
        count, _id = ofs.get()
        processed_line = processed_line.replace(match[0], note.format(count, _id))
        additional_onote += ofside.format(_id, gen_note_html(match['note']))
    additional = additional + additional_onote + additional_note
    if processed_line.endswith("\\\\"):
        additional += '<p><br/></p>'
        processed_line = processed_line[:-2]
    return f'<p>{processed_line}</p>' + additional


def format_title(source_title: str, fts: Counter, ofs: Counter) -> Tuple[str, str]:
    data = re.search('(?<=\\\\subsection)(\\[(?P<plain_title>.+)\\])?({(?P<title>.+)\\})', source_title)
    t = re.sub(r' {\\jpfont (?P<word>.+?)}', '<span lang="ja">\\g<word></span>', data.group('title'))
    t = re.sub(r'(?<=}){\\jpfont (?P<word>.+?)}(?!\|)', '{<span lang="ja">\\g<word></span>}', t)
    t = re.sub(r'(?<=[{|]){\\jpfont (?P<word>.+?)}', '<span lang="ja">\\g<word></span>', t)
    t = re.sub(r'\\ruby{(?P<word>.+?)}{(?P<ruby>.+?)}', gen_ruby_html, t)
    additional = ''
    for match in re.finditer(r'\\footnote{(?P<note>.+?)}', t):
        count, _id = fts.get()
        t = t.replace(match[0], note.format(count, _id))
        additional += fnside.format(count, _id, match['note'])
    for match in re.finditer(r'\\ofnote{(?P<note>.+?)}', t):
        count, _id = ofs.get()
        t = t.replace(match[0], note.format(count, _id))
        additional += fnside.format(count, _id, match['note'])
    if data.group('plain_title'):
        return f'<h1>{t}</h1>{additional}', data.group('plain_title')
    clean = re.sub(r' {\\jpfont (?P<word>.+?)}', '\\g<word>', data.group('title'))
    clean = re.sub(r' {\\jpfont (?P<word>.+?)}', '{\\g<word>}', clean)
    clean = re.sub(r'(?<=[{|]){\\jpfont (?P<word>.+?)}', '\\g<word>', clean)
    clean = re.sub(r'\\ruby{(?P<word>.+?)}{(?P<ruby>.+?)}', '\\g<word>', clean)
    clean = re.sub(r'\\footnote{(?P<note>.+?)}', '', clean)
    clean = re.sub(r'\\ofnote{(?P<note>.+?)}', '', clean)
    return f'<h1>{t}</h1>{additional}', clean


def compile(tex):
    fts = Counter(fnorder)
    ofs = Counter(oforder)
    try:
        tex = tex.decode()
    except AttributeError:
        pass
    sl = [i for i in tex.split('\n') if i if not i.startswith('%')]
    ol = []
    if not sl or not sl[0].startswith('\\'):
        raise EmptyTexError()
    title, clean_title = format_title(sl[0], fts, ofs)
    for line in (s for s in sl[1:] if s):
        if '\\' not in line:
            ol.append(f'<p>{line}</p>')
        else:
            ol.append(format_line(line, fts, ofs))
    if not ol:
        raise EmptyTexError()
    content = ''.join(ol)
    return clean_title, htmlbase.format(ptitle=clean_title, title=title, content=content).encode()
