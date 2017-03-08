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
import uuid

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

CSL_PUBTYPES = {
    'ArticleJournal': 'article-journal',
    'ArticleNewspaper': 'article-newspaper',
    'AudioBook': 'book',
    'AudioVideoDocument': 'broadcast',
    # 'Chapter': 'book-chapter',
    'Chapter': 'chapter',
    'ChapterInLegalCommentary': 'legal_case',
    'Collection': 'book',
    'Conference': 'book',
    'Edition': 'book',
    'InternetDocument': 'webpage',
    'Journal': 'book',
    'Lecture': 'speech',
    'LegalCommentary': 'legal_case',
    'Monograph': 'book',
    'MultivolumeWork': 'book',
    'Newspaper': 'book',
    'Other': 'report',
    'Patent': 'patent',
    'PressRelease': 'article',
    'RadioTVProgram': 'broadcast',
    'Report': 'report',
    'ResearchData': 'dataset',
    'Series': 'book',
    'Software': 'webpage',
    'SpecialIssue': 'book',
    'Standard': 'report',
    'Thesis': 'thesis',
}


WTF_PUBTYPES = {
    'article-journal': 'ArticleJournal',
    'article-newspaper': 'ArticleNewspaper',
    'book': 'Monograph',
    'broadcast': 'AudioVideoDocument',
    'book-chapter': 'Chapter',
    'legal_case': 'ChapterInLegalCommentary',
    'webpage': 'InternetDocument',
    'speech': 'Lecture',
    'report': 'Report',
    'patent': 'Patent',
    'article': 'PressRelease',
    'dataset': 'ResearchData',
    'thesis': 'Thesis',
    'standard': 'Standard',
}


def wtf_csl(wtf_records=None):
    csl_records = []

    # logging.info('wtf_records: %s' % wtf_records)
    if wtf_records is None:
        wtf_records = []

    if len(wtf_records) > 0:
        for record in wtf_records:
            # logging.info('record: %s' % record)
            hosts = []
            if record.get('is_part_of'):
                hosts = record.get('is_part_of')
            else:
                hosts.append({'is_part_of': ''})

            for host in hosts:
                csl_record = {}
                # id
                csl_record.setdefault('id', record.get('id'))
                # type
                csl_type = CSL_PUBTYPES.get(record.get('pubtype'))
                if csl_type is None:
                    csl_record.setdefault('pubtype', record.get('pubtype'))
                csl_record.setdefault('type', csl_type)
                # title
                title = record.get('title')
                if record.get('subtitle'):
                    title += ': %s' % record.get('subtitle')
                # TODO title supplements
                csl_record.setdefault('title', title)

                # doi
                if record.get('DOI') and record.get('DOI')[0] != '':
                    csl_record.setdefault('DOI', record.get('DOI')[0].strip())
                    csl_record.setdefault('URL', 'http://dx.doi.org/%s' % record.get('DOI')[0].strip())
                    csl_record.setdefault('uri', 'http://dx.doi.org/%s' % record.get('DOI')[0].strip())

                # uri
                if record.get('uri') and record.get('uri')[0] != '':
                    for uri in record.get('uri'):
                        csl_record.setdefault('URL', uri.strip())
                        csl_record.setdefault('uri', uri.strip())

                # contributors
                if record.get('person'):
                    author = []
                    editor = []
                    contributor = []
                    for person in record.get('person'):
                        # logging.info(person.get('name'))
                        family = person.get('name').split(', ')[0]
                        given = ''
                        if len(person.get('name').split(', ')) > 1:
                            given = person.get('name').split(', ')[1]
                        # logging.info('%s, %s' % (family, given))
                        if person.get('role'):
                            if 'aut' in person.get('role'):
                                author.append({'family': family, 'given': given})
                            elif 'edt' in person.get('role'):
                                editor.append({'family': family, 'given': given})
                            else:
                                contributor.append({'family': family, 'given': given})

                    if len(author) > 0:
                        csl_record.setdefault('author', author)
                    if len(editor) > 0:
                        csl_record.setdefault('editor', editor)
                    if len(contributor) > 0 and record.get('pubtype') == 'Lecture':
                        csl_record.setdefault('author', contributor)

                # container
                if host.get('is_part_of') != '':
                    try:
                        ipo_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                        application=secrets.SOLR_APP, query='id:%s' % host.get('is_part_of'),
                                        facet='false', fields=['wtf_json'])
                        ipo_solr.request()
                        if len(ipo_solr.results) > 0:
                            myjson = json.loads(ipo_solr.results[0].get('wtf_json'))
                            if myjson.get('pubtype') != 'Series':
                                title = myjson.get('title')
                                if myjson.get('subtitle'):
                                    title += ': %s' % myjson.get('subtitle')
                                csl_record.setdefault('container-title', title)
                                author = []
                                editor = []
                                for person in myjson.get('person'):
                                    # logging.info(person.get('name'))
                                    family = person.get('name').split(', ')[0]
                                    given = ''
                                    if len(person.get('name').split(', ')) > 1:
                                        given = person.get('name').split(', ')[1]
                                    # logging.info('%s, %s' % (family, given))
                                    if person.get('role'):
                                        if 'aut' in person.get('role'):
                                            author.append({'family': family, 'given': given})
                                        elif 'edt' in person.get('role'):
                                            editor.append({'family': family, 'given': given})

                                if len(author) > 0:
                                    csl_record.setdefault('author', author)
                                if len(editor) > 0:
                                    csl_record.setdefault('editor', editor)
                            else:
                                if myjson.get('fsubseries'):
                                    title = myjson.get('fsubseries')
                                else:
                                    title = myjson.get('title')
                                csl_record.setdefault('edition', title)
                        else:
                            csl_record.setdefault('container-title', host.get('is_part_of'))

                    except AttributeError as e:
                        logging.error(e)

                # volume
                if host.get('volume') and host.get('volume') != '':
                    csl_record.setdefault('volume', host.get('volume'))
                # issue
                if host.get('issue') and host.get('issue') != '':
                    csl_record.setdefault('issue', host.get('issue'))
                # page_first
                if host.get('page_first') and host.get('page_first') != '':
                    csl_record.setdefault('page_first', host.get('page_first').replace('-', '_'))
                # page_last
                if host.get('page_last') and host.get('page_last') != '':
                    csl_record.setdefault('page_last', host.get('page_last').replace('-', '_'))
                # page
                if host.get('page_first') and host.get('page_first') != '' and host.get('page_last') and host.get('page_last') != '':
                    csl_record.setdefault('page', '%s-%s' % (host.get('page_first').replace('-', '_'), host.get('page_last').replace('-', '_')))
                else:
                    if host.get('page_first') and host.get('page_first') != '':
                        csl_record.setdefault('page', host.get('page_first').replace('-', '_'))
                    # page_last
                    if host.get('page_last') and host.get('page_last') != '':
                        csl_record.setdefault('page', host.get('page_last').replace('-', '_'))

                # collection-number
                # collection-author
                # collection-editor
                # number_of_volumes
                if host.get('number_of_volumes') and host.get('number_of_volumes') != '':
                    csl_record.setdefault('number_of_volumes', host.get('number_of_volumes'))

                # language
                if record.get('language') and record.get('language')[0] != '' and record.get('language')[0] != 'None':
                    csl_record.setdefault('language', record.get('language')[0])
                # issued
                if record.get('issued'):
                    issued = {}
                    date_parts = []
                    for date_part in str(record.get('issued')).replace('[', '').replace(']', '').split('-'):
                        date_parts.append(date_part)
                    issued.setdefault('date-parts', []).append(date_parts)
                    csl_record.setdefault('issued', issued)
                # edition
                if record.get('edition'):
                    csl_record.setdefault('edition', record.get('edition'))

                # isbn
                if record.get('isbn'):
                    csl_record.setdefault('isbn', record.get('ISBN')[0])
                # issn
                if record.get('issn'):
                    csl_record.setdefault('issn', record.get('ISSN')[0])
                # ismn
                if record.get('ismn'):
                    csl_record.setdefault('ismn', record.get('ISMN')[0])

                # publisher
                if record.get('publisher'):
                    csl_record.setdefault('publisher', record.get('publisher'))
                    csl_record.setdefault('original-publisher', record.get('publisher'))
                # publisher_place
                if record.get('publisher_place'):
                    csl_record.setdefault('publisher-place', record.get('publisher_place'))
                    csl_record.setdefault('original-publisher-place', record.get('publisher_place'))
                # number_of_pages
                if record.get('number_of_pages'):
                    csl_record.setdefault('number_of_pages', record.get('number_of_pages'))
                # uri

                # WOSID
                if record.get('WOSID'):
                    csl_record.setdefault('WOSID', record.get('WOSID'))
                # PMID
                if record.get('PMID'):
                    csl_record.setdefault('PMID', record.get('PMID'))
                # abstract
                if record.get('abstract')[0] and record.get('abstract')[0].get('content') != '':
                    csl_record.setdefault('abstract', record.get('abstract')[0].get('content'))

                csl_records.append(csl_record)

    return csl_records


def csl_wtf(csl_records=None):
    wtf = []

    if csl_records is None:
        csl_records = []

    if len(csl_records) > 0:
        for record in csl_records:
            # logging.info('record: %s' % record)
            wtf_record = {}
            wtf_record.setdefault('id', str(uuid.uuid4()))
            wtf_record.setdefault('pubtype', WTF_PUBTYPES.get(record.get('type')))

            wtf_record.setdefault('doi', []).append(record.get('id'))
            wtf_record.setdefault('title', record.get('title'))
            if record.get('publisher'):
                wtf_record.setdefault('publisher', record.get('publisher'))
            if record.get('issued'):
                wtf_record.setdefault('issued', record.get('issued').get('raw'))

            is_part_of = []
            if record.get('parent_title'):
                part = {}
                part.setdefault('is_part_of', record.get('parent_title'))
                if record.get('volume'):
                    part.setdefault('volume', record.get('volume'))
                if record.get('issue'):
                    part.setdefault('issue', record.get('issue'))
                if record.get('page_first'):
                    part.setdefault('page_first', record.get('page_first'))
                if record.get('page_last'):
                    part.setdefault('page_last', record.get('page_last'))
                is_part_of.append(part)

            if record.get('container_title'):
                part = {}
                part.setdefault('is_part_of', record.get('container_title'))
                if record.get('volume'):
                    part.setdefault('volume', record.get('volume'))
                if record.get('issue'):
                    part.setdefault('issue', record.get('issue'))
                if record.get('page_first'):
                    part.setdefault('page_first', record.get('page_first'))
                if record.get('page_last'):
                    part.setdefault('page_last', record.get('page_last'))
                is_part_of.append(part)

            if len(is_part_of) > 0:
                wtf_record.setdefault('is_part_of', is_part_of)

            persons = []
            if record.get('author'):
                for author in record.get('author'):
                    person = {}
                    person.setdefault('name', '%s, %s' % (author.get('family'), author.get('given')))
                    person.setdefault('role', []).append('aut')
                    persons.append(person)

            if record.get('editor'):
                for editor in record.get('editor'):
                    person = {}
                    person.setdefault('name', '%s, %s' % (editor.get('family'), editor.get('given')))
                    person.setdefault('role', []).append('edt')
                    persons.append(person)

            if record.get('contributor'):
                for contributor in record.get('contributor'):
                    person = {}
                    person.setdefault('name', '%s, %s' % (contributor.get('family'), contributor.get('given')))
                    person.setdefault('role', []).append('ctb')
                    persons.append(person)

            if len(persons) > 0:
                wtf_record.setdefault('person', persons)

            # logging.info('wtf: %s' % wtf_record)
            wtf.append(wtf_record)

    # logging.info('wtf: %s' % wtf)
    return wtf
