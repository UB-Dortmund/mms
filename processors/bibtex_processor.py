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

import logging

import bibtexparser
import simplejson as json
from bibtexparser.bibdatabase import BibDatabase

from utils.solr_handler import Solr

try:
    import app_secrets
    import local_app_secrets as secrets
except ImportError:
    import app_secrets

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)-4s %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S',
                    )

BIBTEX_PUBTYPES = {
    'Monograph': 'book',
    'AudioBook': 'book',
    'Chapter': 'inbook',
    'ChapterInLegalCommentary': 'inbook',
    'ChapterInMonograph': 'inbook',
    'review': 'misc',
    'Thesis': 'phdthesis',
    'Conference': 'proceedings',
    'Collection': 'book',
    'ArticleJournal': 'article',
    'SpecialIssue': 'misc',
    'InternetDocument': 'misc',
    'ArticleNewspaper': 'article',
    'Report': 'unpublished',
    'ResearchData': 'misc',
    'Patent': 'misc',
    'Lecture': 'misc',
    'Standard': 'misc'
}


def wtf_bibtex(wtf_records=None):

    # logging.info('wtf_records: %s' % wtf_records)
    if wtf_records is None:
        wtf_records = []

    if len(wtf_records) > 0:

        db = BibDatabase()
        db.entries = []

        for record in wtf_records:

            bibtex_entry = {}

            bibtex_type = BIBTEX_PUBTYPES.get(record.get('pubtype'))
            if bibtex_type is None:
                bibtex_type.setdefault('pubtype', 'misc')
            bibtex_entry.setdefault('ENTRYTYPE', bibtex_type)

            bibtex_entry.setdefault('ID', record.get('id'))

            title = record.get('title')
            if record.get('subtitle'):
                title += ': %s' % record.get('subtitle')
            bibtex_entry.setdefault('title', title)

            if record.get('issued'):
                date_parts = []
                for date_part in str(record.get('issued')).replace('[', '').replace(']', '').split('-'):
                    date_parts.append(date_part)
                bibtex_entry.setdefault('year', date_parts[0])
                if len(date_parts) > 1:
                    bibtex_entry.setdefault('month', date_parts[1])
                if len(date_parts) > 2:
                    bibtex_entry.setdefault('day', date_parts[2])

            if record.get('DOI'):
                bibtex_entry.setdefault('crossref', record.get('DOI')[0])

            author_str = ''
            for author in record.get('person'):
                if 'aut' in author.get('role'):
                    if author_str != '':
                        author_str += ' and '
                    author_str += author.get('name')

            bibtex_entry.setdefault('author', author_str)

            # is_part_of
            hosts = []
            if record.get('is_part_of'):
                hosts = record.get('is_part_of')

            for host in hosts:
                if host.get('is_part_of') != '':
                    try:
                        ipo_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                        application=secrets.SOLR_APP, query='id:%s' % host.get('is_part_of'),
                                        facet='false', fields=['wtf_json'])
                        ipo_solr.request()
                        if len(ipo_solr.results) > 0:
                            myjson = json.loads(ipo_solr.results[0].get('wtf_json'))
                            title = myjson.get('title')
                            if myjson.get('subtitle'):
                                title += ': %s' % myjson.get('subtitle')
                            if bibtex_entry.get('ENTRYTYPE') == 'article':
                                bibtex_entry.setdefault('journal', title)
                            elif bibtex_entry.get('ENTRYTYPE') == 'inbook':
                                bibtex_entry.setdefault('booktitle', title)
                            elif bibtex_entry.get('ENTRYTYPE') == 'inproceedings':
                                bibtex_entry.setdefault('booktitle', title)
                            elif bibtex_entry.get('ENTRYTYPE') == 'incollection':
                                bibtex_entry.setdefault('booktitle', title)
                            else:
                                bibtex_entry.setdefault('series', title)
                    except AttributeError as e:
                        logging.error(e)
                if host.get('volume') != '':
                    bibtex_entry.setdefault('volume', host.get('volume'))

            if bibtex_entry:
                db.entries.append(bibtex_entry)

        return bibtexparser.dumps(db)

    else:
        return ''
