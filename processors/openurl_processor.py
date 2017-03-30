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

# see also: http://ocoins.info/
# see also: http://epub.mimas.ac.uk/openurl/KEV_Guidelines-200706.html

import logging
from urllib import parse

import simplejson as json

from utils.solr_handler import Solr

try:
    import local_p_secrets as secrets
except ImportError:
    import p_secrets as secrets

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)-4s %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S',
                    )

OPENURL_KEV_MTX = {
    'ArticleJournal': 'journal',
    'ArticleNewspaper': 'journal',
    'AudioBook': 'book',
    'AudioVideoDocument': 'book',
    'Chapter': 'book',
    'ChapterInLegalCommentary': 'book',
    'Collection': 'book',
    'Conference': 'book',
    'InternetDocument': 'book',
    'Journal': 'journal',
    'Lecture': 'book',
    'LegalCommentary': 'book',
    'Monograph': 'book',
    'MultivolumeWork': 'book',
    'Other': 'book',
    'Patent': 'patent',
    'PressRelease': 'book',
    'RadioTVProgram': 'book',
    'Report': 'book',
    'ResearchData': 'book',
    'Series': 'journal',
    'Software': 'book',
    'SpecialIssue': 'journal',
    'Standard': 'patent',
    'Thesis': 'dissertation',
}

OPENURL_GENRE = {
    'ArticleJournal': 'article',
    'ArticleNewspaper': 'article',
    'AudioBook': 'unknown',
    'AudioVideoDocument': 'unknown',
    'Chapter': 'bookitem',
    'ChapterInLegalCommentary': 'bookitem',
    'Collection': 'book',
    'Conference': 'conference',
    'InternetDocument': 'document',
    'Journal': 'journal',
    'Lecture': 'document',
    'LegalCommentary': 'document',
    'Monograph': 'book',
    'MultivolumeWork': 'book',
    'Other': 'report',
    'PressRelease': 'document',
    'RadioTVProgram': 'unknown',
    'Report': 'report',
    'ResearchData': 'unknown',
    'Series': 'journal',
    'Software': 'unknown',
    'SpecialIssue': 'issue',
}


def wtf_openurl(record=None):

    open_url = 'ctx_ver=Z39.88-2004'

    if record:

        # pubtype
        if record.get('pubtype') and OPENURL_KEV_MTX.get(record.get('pubtype')):
            open_url += '&rft_val_fmt=info:ofi/fmt:kev:mtx:%s' % OPENURL_KEV_MTX.get(record.get('pubtype'))
        else:
            open_url += '&rft_val_fmt=info:ofi/fmt:kev:mtx:%s' % 'book'
        if OPENURL_GENRE.get(record.get('pubtype')):
            open_url += '&rft.genre=%s' % OPENURL_GENRE.get(record.get('pubtype'))
        else:
            open_url += '&rft.genre=%s' % 'unknown'

        # sid
        # open_url += '&info:ofi/nam:info:sid:%s' % str(parse.quote(record.get('id'), 'utf-8'))

        # doi
        if record.get('DOI') and record.get('DOI')[0]:
            open_url += '&info:ofi/nam:info:doi:%s' % parse.quote(record.get('DOI')[0], 'utf-8')

        # authors
        if record.get('person'):
            for person in record.get('person'):
                open_url += '&rft.au=%s' % parse.quote(person.get('name'), 'utf8')

        if record.get('is_part_of') and record.get('is_part_of')[0] and record.get('is_part_of')[0].get('is_part_of'):
            for host in record.get('is_part_of'):
                if host.get('is_part_of'):
                    try:
                        ipo_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                        application=secrets.SOLR_APP, query='id:%s' % host.get('is_part_of'),
                                        facet='false', fields=['wtf_json'])
                        ipo_solr.request()
                        if len(ipo_solr.results) > 0:
                            myjson = json.loads(ipo_solr.results[0].get('wtf_json'))
                            if myjson.get('pubtype') == 'journal':
                                open_url += '&rft.jtitle=%s' % parse.quote(myjson.get('title'), 'utf-8')
                                open_url += '&rft.issn=%s' % parse.quote(myjson.get('ISSN')[0], 'utf-8')
                                open_url += '&rft.volume=%s' % parse.quote(host.get('volume'), 'utf-8')
                                open_url += '&rft.issue=%s' % parse.quote(host.get('issue'), 'utf-8')
                                open_url += '&rft.pages=%s' % host.get('page_first')
                                if host.get('page_last'):
                                    open_url += '-%s' % host.get('page_last')
                                # article title
                                open_url += '&rft.atitle=%s' % parse.quote(record.get('title'), 'utf-8')
                            elif myjson.get('pubtype') == 'Monograph' or \
                                            myjson.get('pubtype') == 'Collection' or \
                                            myjson.get('pubtype') == 'Conference' or \
                                            myjson.get('pubtype') == 'LegalCommentary':
                                # btitle
                                open_url += '&rft.btitle=%s' % parse.quote(myjson.get('title'), 'utf-8')
                                open_url += '&rft.isbn=%s' % parse.quote(myjson.get('ISBN')[0], 'utf-8')
                                open_url += '&rft.pages=%s' % host.get('page_first')
                                if host.get('page_last'):
                                    open_url += '-%s' % host.get('page_last')
                    except AttributeError as e:
                        logging.error(e)
                    break

        if 'rft.atitle' not in open_url:
            open_url += '&rft.title=%s' % parse.quote(record.get('title'), 'utf-8')

        if record.get('ISSN'):
            open_url += '&rft.issn=%s' % parse.quote(record.get('ISSN')[0], 'utf-8')
        if record.get('ISBN'):
            open_url += '&rft.isbn=%s' % parse.quote(record.get('ISBN')[0], 'utf-8')

        # origin info
        if record.get('issued'):
            open_url += '&rft.date=%s' % record.get('issued')
        if record.get('publisher_place'):
            open_url += '&rft.place=%s' % parse.quote(record.get('publisher_place'), 'utf-8')
        if record.get('publisher') and record.get('publisher')[0]:
            open_url += '&rft.publisher=%s' % parse.quote(record.get('publisher')[0], 'utf-8')

        # other
        if record.get('corporation'):
            for corporation in record.get('corporation'):
                open_url += '&rft.inst=%s' % parse.quote(corporation.get('name'), 'utf-8')

    return open_url
