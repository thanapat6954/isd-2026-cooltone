"""Strict reference matching with independently approved additional source rows."""

REFERENCE_FIELDS = ('regulation_year', 'source_file', 'page_number', 'printed_page_number')


def expected_references(label, reviews):
    baseline = {'regulation_year': label['regulation_year'], 'source_file': label['source_file'],
                'page_number': label['page'], 'printed_page_number': label['book_page']}
    expected = [baseline]
    for review in reviews:
        if (review['program'], review['version']) != (label['program'], label['version']):
            continue
        expected.append({'regulation_year': review['regulation_year'], 'source_file': review['source_file'],
                         'page_number': review['pdf_page'], 'printed_page_number': review['book_page'],
                         'rule_text': review['rule_text'], 'section': review['section'],
                         'review_scope': review['review_scope']})
    return expected


def references_match(rows, expected):
    if len(rows) != len(expected):
        return False
    remaining = list(rows)
    for reference in expected:
        matches = [row for row in remaining if all(row.get(key) == value for key, value in reference.items())]
        if len(matches) != 1:
            return False
        remaining.remove(matches[0])
    return not remaining


def frontend_references_match(sources, expected):
    return all(any(source.get('page') == reference['page_number']
                   and source.get('book_page') == reference['printed_page_number']
                   and source.get('section', '').startswith(reference['source_file'])
                   for source in sources) for reference in expected)
