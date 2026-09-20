"""Pedestal metadata parser and public processing API. Standard library only."""
import re
from html.parser import HTMLParser
from inventory import process, Limits


class PlainHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in {'br', 'p', 'div', 'li'}:
            self.parts.append('\n')

    def handle_endtag(self, tag):
        if tag in {'p', 'div', 'li'}:
            self.parts.append('\n')

    def handle_data(self, data):
        self.parts.append(data)


def parse_metadata(raw):
    row = {'raw_metadata_text': raw, 'digitizer': '', 'digitisation_date': ''}
    raw = raw.lstrip('\ufeff')
    for label in ('Title', 'License', 'Author', 'Source'):
        match = re.search(r'^' + label + r':[ \t]*(.*)$', raw, re.M)
        row[label.lower()] = match.group(1).strip() if match else ''
    match = re.search(r'^Model downloaded from Pedestal 3D instance:\s*(\S+) at ([^\r\n]+)', raw)
    row['download_origin'] = match.group(1) if match else ''
    row['download_timestamp'] = match.group(2) if match else ''
    match = re.search(r'\bABP-HBM-\d+(?:\.\d+)*\b', row['title'])
    row['catalogue_id'] = match.group() if match else ''
    row['catalogue_id_basis'] = 'inferred from title label' if match else ''
    before, sep, description = raw.partition('Description:')
    row['description_html'] = description.strip() if sep else ''
    row['attribution_instruction'] = '\n'.join(l.strip() for l in before.splitlines() if l.strip() and not re.match(r'^(Model downloaded|Title:|License:|Author:|Source:)', l))
    parser = PlainHTML()
    parser.feed(row['description_html'])
    text = ''.join(parser.parts).strip()
    matches = list(re.finditer(r'(?:^|\n)\s*(Keywords|Date|Location):\s*', text))
    row['description_text'] = text[:matches[0].start()].strip() if matches else text
    for key in ('keywords', 'historical_date_text', 'location'):
        row[key] = ''
    for i, match in enumerate(matches):
        key = {'Keywords': 'keywords', 'Date': 'historical_date_text', 'Location': 'location'}[match.group(1)]
        row[key] = text[match.end():matches[i+1].start() if i+1 < len(matches) else len(text)].strip()
    return row
