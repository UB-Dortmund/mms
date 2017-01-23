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

# https://api.datacite.org/

# TODO see https://schema.datacite.org/meta/kernel-3.1/doc/DataCite-MetadataKernel_v3.1.pdf
DATACITE_TYPES = {
    'book': 'Monograph',
    'editedbook': 'Collection',
    'bookchapter': 'Chapter',
    'bookseries': 'Series',
    'journalarticle': 'ArticleJournal',
    'article': 'ArticleJournal',
    'journalissue': 'Collection',
    'conferencepaper': 'Chapter',
    'dictionaryentry': 'Chapter',
    'encyclopediaentry': 'Chapter',
    'workingpaper': 'Report',
    'bookprospectus': 'Other',
    'bookreview': 'Other',
    'conferenceabstract': 'Other',
    'conferenceposter': 'Other',
    'conferenceprogram': 'Other',
    'isclosure': 'Other',
    'dissertation': 'Thesis',
    'fundingsubmission': 'Other',
    'license': 'Other',
    'magazinearticle': 'ArticleNewspaper',
    'manual': 'Other',
    'newsletterarticle': 'InternetDocument',
    'newspaperarticle': 'ArticleNewspaper',
    'onlineresource': 'InternetDocument',
    'patent': 'Patent',
    'registeredcopyright': 'Other',
    'researchtool': 'ResearchData',
    'supervisedstudentpublication': 'Thesis',
    'test': 'ResearchData',
    'trademark': 'Other',
    'translation': 'Other',
    'universityacademicunit': 'Thesis',
    'website': 'InternetDocument',
    'audiovisual': 'AudioVideoDocument',
    'collection': 'ResearchData',
    'dataset': 'ResearchData',
    'event': 'ResearchData',
    'image': 'ResearchData',
    'interactiveresource': 'ResearchData',
    'model': 'ResearchData',
    'physicalobject': 'ResearchData',
    'service': 'ResearchData',
    'software': 'ResearchData',
    'sound': 'ResearchData',
    'workflow': 'ResearchData',
    'other': 'Other',
    'report': 'Report',
}


def datacite2csl(doi='', query=''):

    rows = 10

    csl_json = []

    record = {}
    try:
        if doi != '':
            record = requests.get('https://api.datacite.org/works/%s' % doi).json()
        elif query != '':
            record = requests.get('https://api.datacite.org/works?rows=%s&query=%s' % (rows, query)).json()
        else:
            record.setdefault('data', [])
    except JSONDecodeError:
        pass

    if doi != '':
        if record.get('data'):
            datacite_items = record.get('data')
        else:
            datacite_items = []
    elif query != '':
        datacite_items = record.get('data')
    else:
        datacite_items = []

    for item in datacite_items:

        if item.get('type') == 'works':
            csl_record = {}

            doi_from_data = item.get('attributes').get('doi')
            csl_record.setdefault('doi', doi_from_data)
            csl_record.setdefault('id', doi_from_data)

            if item.get('attributes').get('type'):
                csl_type = item.get('attributes').get('type')
            elif item.get('attributes').get('resource-type'):
                csl_type = item.get('attributes').get('resource-type')
            else:
                csl_type = item.get('attributes').get('resource-type-general')
            csl_record.setdefault('type', csl_type)

            title = item.get('attributes').get('title')
            csl_record.setdefault('title', title)

            issued = item.get('attributes').get('published')
            csl_issued = {'raw': issued}
            csl_record.setdefault('issued', csl_issued)

            authors = []
            if item.get('attributes').get('author'):
                for author in item.get('attributes').get('author'):
                    if author.get('literal'):
                        tmp = author.get('literal').split(' ')
                        authors.append({'family': tmp[len(tmp)-1], 'given': author.get('literal').replace(' %s' % tmp[len(tmp)-1], '')})
                        # authors.append({'literal': author.get('literal')})
                    elif author.get('family') or author.get('given'):
                        authors.append({'family': author.get('family'), 'given': author.get('given')})

            if len(authors) > 0:
                csl_record.setdefault('author', authors)

            publisher_id = item.get('attributes').get('publisher-id')

            for item1 in datacite_items:

                if item1.get('type') == 'publishers' and item1.get('id') == publisher_id:
                    csl_record.setdefault('publisher', item1.get('attributes').get('title'))

            csl_json.append(csl_record)

    return {'items': csl_json}


def datacite2wtfjson(doi=''):

    wtf = {}

    record = requests.get('https://api.datacite.org/works/%s' % doi).json()

    if record.get('data'):
        datacite_items = record.get('data')
    else:
        datacite_items = []

    for item in datacite_items:

        if item.get('type') == 'works':
            wtf.setdefault('id', str(uuid.uuid4()))
            timestamp = str(datetime.datetime.now())
            wtf.setdefault('created', timestamp)
            wtf.setdefault('changed', timestamp)
            wtf.setdefault('editorial_status', 'new')

            if str(item.get('attributes').get('resource-type-general')).lower() == 'text':
                logging.debug(str(item.get('attributes').get('resource-type')))
                pubtype = DATACITE_TYPES.get(str(item.get('attributes').get('resource-type')).lower())
            else:
                pubtype = item.get('attributes').get('resource-type-general')

            wtf.setdefault('pubtype', pubtype)

            title = item.get('attributes').get('title')
            wtf.setdefault('title', title)

            issued = item.get('attributes').get('published')
            wtf.setdefault('issued', issued)

            persons = []
            if item.get('attributes').get('author'):
                for author in item.get('attributes').get('author'):
                    person = {}
                    if author.get('literal'):
                        tmp = author.get('literal').split(' ')
                        person.setdefault('name', '%s, %s' % (tmp[len(tmp) - 1], author.get('literal').replace(' %s' % tmp[len(tmp) - 1], '')))
                    else:
                        person.setdefault('name', '%s, %s' % (author.get('family'), author.get('given')))
                    person.setdefault('role', []).append('aut')
                    persons.append(person)

            if len(persons) > 0:
                wtf.setdefault('person', persons)

            publisher_id = item.get('attributes').get('publisher-id')

            for item1 in datacite_items:

                if item1.get('type') == 'publishers' and item1.get('id') == publisher_id:
                    wtf.setdefault('publisher', item1.get('attributes').get('title'))

            wtf.setdefault('DOI', []).append(doi)

            if item.get('attributes').get('description'):
                abstract = {}
                abstract.setdefault('content', item.get('attributes').get('description'))
                abstract.setdefault('shareable', True)
                wtf.setdefault('abstract', []).append(abstract)

            break

    return wtf

# logging.debug(json.dumps(datacite2csl('10.4230/DAGREP.1.10.37'), indent=4))
# logging.debug(json.dumps(datacite2wtfjson('10.4230/DAGREP.1.10.37'), indent=4))
# logging.debug(json.dumps(datacite2wtfjson('10.5162/sensor11/c1.3'), indent=4))
# logging.debug(json.dumps(datacite2wtfjson('10.17877/DE290R-7365'), indent=4))

