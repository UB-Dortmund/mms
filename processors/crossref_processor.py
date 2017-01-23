__author__ = 'hagbeck'

# The MIT License
#
#  Copyright 2016 UB Dortmund <daten.ub@tu-dortmund.de>.
#
#  Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in
#  all copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#  THE SOFTWARE.

import datetime
import logging
import uuid

import requests
from simplejson import JSONDecodeError

try:
    import app_secrets
    import local_app_secrets as secrets
except ImportError:
    import app_secrets

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)-4s %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S',
                    )

# https://github.com/CrossRef/rest-api-doc/blob/master/rest_api.md

CROSSREF_PUBTYPES = {
    'book': 'Monograph',
    'book-chapter': 'Chapter',
    'book-edited': 'Collection',
    'book-section': 'Chapter',
    'book-series': 'Series',
    'book-set': 'Monograph',
    'book-track': 'Chapter',
    'component': 'Report',
    'data-set': 'ResearchData',
    'dissertation': 'Thesis',
    'journal-article': 'ArticleJournal',
    'journal': 'Journal',
    'journal-issue': 'Collection',
    'journal-volume': 'Collection',
    'monograph': 'Monograph',
    'other': 'Report',
    'preprint': 'Report',
    'proceedings': 'Conference',
    'proceedings-article': 'Chapter',
    'reference': 'Collection',
    'reference-entry': 'Chapter',
    'report': 'Report',
    'report-series': 'Series',
    'standard': 'Standard',
    'standard-series': 'Series',
}


def crossref2csl(doi='', query=''):

    rows = 10

    csl_json = []

    record = {}
    try:
        if doi != '':
            record = requests.get('http://api.crossref.org/works/%s' % doi).json()
        elif query != '':
            record = requests.get('http://api.crossref.org/works?rows=%s&query=%s' % (rows, query)).json()
        else:
            record.setdefault('message', [])
    except JSONDecodeError:
        pass

    if doi != '':
        if record.get('message'):
            crossref_items = [record.get('message')]
        else:
            crossref_items = []
    elif query != '':
        crossref_items = record.get('message').get('items')
    else:
        crossref_items = []

    for item in crossref_items:

        if item.get('title'):
            # logging.debug(json.dumps(item, indent=4))

            csl_record = {}

            doi_from_data = item.get('DOI')
            csl_record.setdefault('doi', doi_from_data)
            csl_record.setdefault('id', doi_from_data)

            csl_type = item.get('type')
            csl_record.setdefault('type', csl_type)

            title = item.get('title')[0]
            csl_record.setdefault('title', title)

            issued = item.get('created').get('date-parts')[0][0]
            if item.get('created').get('date-parts')[0][1]:
                issued = '%s-%s' % (issued, item.get('created').get('date-parts')[0][1])
            if item.get('created').get('date-parts')[0][2]:
                issued = '%s-%s' % (issued, item.get('created').get('date-parts')[0][2])

            csl_issued = {'raw': issued}
            csl_record.setdefault('issued', csl_issued)

            journal_title = None
            for jtitle in item.get('container-title'):
                if jtitle != '':
                    journal_title = jtitle
                    break

            if journal_title is not None:
                csl_record.setdefault('parent_title', journal_title)

            authors = []
            if item.get('author'):
                for author in item.get('author'):
                    authors.append({'family': author.get('family'), 'given': author.get('given')})

            if item.get('editor'):
                for editor in item.get('editor'):
                    authors.append({'family': editor.get('family'), 'given': editor.get('given')})

            if len(authors) > 0:
                csl_record.setdefault('author', authors)

            publisher = item.get('publisher')
            csl_record.setdefault('publisher', publisher)

            if item.get('ISBN'):
                isbns = []
                for isbn in item.get('ISBN'):
                    isbns.append(isbn.strip().split('isbn/')[1])

            csl_json.append(csl_record)

    return {'items': csl_json}


def crossref2wtfjson(doi=''):

    wtf = {}

    record = {}
    try:
        record = requests.get('http://api.crossref.org/works/%s' % doi).json()
    except JSONDecodeError:
        pass

    if record.get('message'):
        wtf.setdefault('id', str(uuid.uuid4()))
        timestamp = str(datetime.datetime.now())
        wtf.setdefault('created', timestamp)
        wtf.setdefault('changed', timestamp)
        wtf.setdefault('editorial_status', 'new')

        pubtype = CROSSREF_PUBTYPES.get(record.get('message').get('type'))
        wtf.setdefault('pubtype', pubtype)

        title = record.get('message').get('title')[0]
        wtf.setdefault('title', title)

        issued = record.get('message').get('created').get('date-parts')[0][0]
        if record.get('message').get('created').get('date-parts')[0][1]:
            issued = '%s-%s' % (issued, record.get('message').get('created').get('date-parts')[0][1])
        if record.get('message').get('created').get('date-parts')[0][2]:
            issued = '%s-%s' % (issued, record.get('message').get('created').get('date-parts')[0][2])

        wtf.setdefault('issued', issued)

        is_part_of = []
        if record.get('message').get('container-title'):
            for jtitle in record.get('message').get('container-title'):
                if jtitle != '':
                    part = {}
                    part.setdefault('is_part_of', jtitle)
                    if record.get('message').get('volume'):
                        part.setdefault('volume', record.get('message').get('volume'))
                    if record.get('message').get('issue'):
                        part.setdefault('issue', record.get('message').get('issue'))
                    if record.get('message').get('page_first'):
                        part.setdefault('page_first', record.get('message').get('page_first'))
                    if record.get('message').get('page_last'):
                        part.setdefault('page_last', record.get('message').get('page_last'))
                    if record.get('message').get('page'):
                        page = str(record.get('message').get('page')).split('-')
                        part.setdefault('page_first', page[0])
                        if len(page) > 1:
                            part.setdefault('page_last',  page[1])
                    is_part_of.append(part)
                    break

        if record.get('message').get('parent-title'):
            for jtitle in record.get('message').get('parent-title'):
                if jtitle != '':
                    part = {}
                    part.setdefault('is_part_of', jtitle)
                    if record.get('message').get('volume'):
                        part.setdefault('volume', record.get('message').get('volume'))
                    if record.get('message').get('issue'):
                        part.setdefault('issue', record.get('message').get('issue'))
                    if record.get('message').get('page_first'):
                        part.setdefault('page_first', record.get('message').get('page_first'))
                    if record.get('message').get('page_last'):
                        part.setdefault('page_last', record.get('message').get('page_last'))
                    if record.get('message').get('page'):
                        page = str(record.get('message').get('page')).split('-')
                        part.setdefault('page_first', page[0])
                        if len(page) > 1:
                            part.setdefault('page_last',  page[1])
                    is_part_of.append(part)
                    break

        if len(is_part_of) > 0:
            wtf.setdefault('is_part_of', is_part_of)

        persons = []
        if record.get('message').get('author'):
            for author in record.get('message').get('author'):
                person = {}
                person.setdefault('name', '%s, %s' % (author.get('family'), author.get('given')))
                person.setdefault('role', []).append('aut')
                persons.append(person)

        if record.get('message').get('editor'):
            for editor in record.get('message').get('editor'):
                person = {}
                person.setdefault('name', '%s, %s' % (editor.get('family'), editor.get('given')))
                person.setdefault('role', []).append('edt')
                persons.append(person)

        if len(persons) > 0:
            wtf.setdefault('person', persons)

        publisher = record.get('message').get('publisher')
        wtf.setdefault('publisher', publisher)

        wtf.setdefault('DOI', []).append(doi)

        if record.get('message').get('ISBN'):
            isbns = []
            for isbn in record.get('message').get('ISBN'):
                isbns.append(isbn.strip().split('isbn/')[1])
            wtf.setdefault('isbn', isbns)

    return wtf

