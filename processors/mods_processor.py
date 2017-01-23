# The MIT License
#
#  Copyright 2015 UB Bochum <bibliographie-ub@rub.de>.
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

from lxml import etree

try:
    import app_secrets
    import local_app_secrets as secrets
except ImportError:
    import app_secrets

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)-4s %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S',
                    )


def mods2csl(record):

    csl_json = []

    MODS = 'http://www.loc.gov/mods/v3'
    NSDICT = {'m': MODS}

    for mods in record.xpath('//m:mods', namespaces=NSDICT):

        csl = {}

        try:
            theid = str(uuid.uuid4())
            if mods.xpath('./m:recordInfo/m:recordIdentifier', namespaces=NSDICT):
                theid = mods.xpath('./m:recordInfo/m:recordIdentifier', namespaces=NSDICT)[0].text

            csl.setdefault('type', 'book')
            csl_title = ''

            csl.setdefault('id', theid)

            # logging.info(etree.tostring(record))

            if mods.xpath('./m:titleInfo/m:nonSort', namespaces=NSDICT):
                csl_title = mods.xpath('./m:titleInfo/m:nonSort', namespaces=NSDICT)[0].text + ' '
            csl_title += '%s' % mods.xpath('./m:titleInfo/m:title', namespaces=NSDICT)[0].text
            if mods.xpath('./m:titleInfo/m:subTitle', namespaces=NSDICT):
                csl_title += ' : %s' % mods.xpath('./m:titleInfo/m:subTitle', namespaces=NSDICT)[0].text
            csl.setdefault('title', csl_title)

            if mods.xpath('./m:name[@type="personal"]', namespaces=NSDICT):
                for name in mods.xpath('./m:name[@type="personal"]', namespaces=NSDICT):
                    csl_tmp = {}
                    if name.xpath('./m:namePart[@type="family"]', namespaces=NSDICT):
                        csl_tmp.setdefault('family', name.xpath('./m:namePart[@type="family"]', namespaces=NSDICT)[0].text)
                    if name.xpath('./m:namePart[@type="given"]', namespaces=NSDICT):
                        csl_tmp.setdefault('given', name.xpath('./m:namePart[@type="given"]', namespaces=NSDICT)[0].text)

                    role = ''
                    if name.xpath('./m:role/m.roleTerm[@authority="marcrelator"]', namespaces=NSDICT):
                        role = name.xpath('./m:role/m.roleTerm[@authority="marcrelator"]', namespaces=NSDICT)[0].text

                    if csl_tmp.get('family'):
                        if role == 'edt':
                            csl.setdefault('editor', []).append(csl_tmp)
                        else:
                            csl.setdefault('author', []).append(csl_tmp)

            if mods.xpath('./m:originInfo/m:place/m:placeTerm[@type="text"]', namespaces=NSDICT):
                csl.setdefault('publisher-place', mods.xpath('./m:originInfo/m:place/m:placeTerm[@type="text"]', namespaces=NSDICT)[0].text)
            if mods.xpath('./m:originInfo/m:publisher', namespaces=NSDICT):
                csl.setdefault('publisher', mods.xpath('./m:originInfo/m:publisher', namespaces=NSDICT)[0].text)
            if mods.xpath('./m:originInfo/m:dateIssued', namespaces=NSDICT):
                year = mods.xpath('./m:originInfo/m:dateIssued', namespaces=NSDICT)[0].text.replace('[', '').replace(']', '').replace('c', '')
                if type(year) == int:
                    csl.setdefault('issued', {}).setdefault('date-parts', [[year]])

            if mods.xpath('./m:language/m:languageTerm', namespaces=NSDICT):
                csl.setdefault('language', mods.xpath('./m:language/m:languageTerm', namespaces=NSDICT)[0].text)

            # if mods.xpath('./m:physicalDescription/m:extent', namespaces=NSDICT):
                # csl.setdefault('page', mods.xpath('./m:physicalDescription/m:extent', namespaces=NSDICT)[0].text)

            if mods.xpath('./m:abstract', namespaces=NSDICT):
                csl.setdefault('abstract', mods.xpath('./m:abstract', namespaces=NSDICT)[0].text)

            csl_json.append(csl)
        except Exception:
            continue

    return {'items': csl_json}


def mods2wtfjson(ppn=''):

    wtf = {}

    record = etree.parse(
        'http://sru.gbv.de/gvk?version=1.1&operation=searchRetrieve&query=%s=%s&maximumRecords=10&recordSchema=mods'
        % ('pica.ppn', ppn))
    # logging.info(etree.tostring(record))

    MODS = 'http://www.loc.gov/mods/v3'
    NSDICT = {'m': MODS}

    mods = record.xpath('//m:mods', namespaces=NSDICT)[0]

    wtf.setdefault('id', str(uuid.uuid4()))
    timestamp = str(datetime.datetime.now())
    wtf.setdefault('created', timestamp)
    wtf.setdefault('changed', timestamp)
    wtf.setdefault('editorial_status', 'new')

    wtf.setdefault('pubtype', 'Monograph')

    wtf.setdefault('title', mods.xpath('./m:titleInfo/m:title', namespaces=NSDICT)[0].text)
    if mods.xpath('./m:titleInfo/m:subTitle', namespaces=NSDICT):
        wtf.setdefault('subtitle', mods.xpath('./m:titleInfo/m:subTitle', namespaces=NSDICT)[0].text)

    persons = []
    if mods.xpath('./m:name[@type="personal"]', namespaces=NSDICT):
        for name in mods.xpath('./m:name[@type="personal"]', namespaces=NSDICT):
            tmp = {}
            if name.get('authority') and name.get('authority') == 'gnd' and name.get('valueURI'):
                tmp.setdefault('gnd', name.get('valueURI').split('gnd/')[1])
            tmp.setdefault('name', '%s, %s' % (name.xpath('./m:namePart[@type="family"]', namespaces=NSDICT)[0].text, name.xpath('./m:namePart[@type="given"]', namespaces=NSDICT)[0].text))
            persons.append(tmp)
    wtf.setdefault('person', persons)

    if mods.xpath('./m:originInfo/m:place/m:placeTerm[@type="text"]', namespaces=NSDICT):
        wtf.setdefault('place', mods.xpath('./m:originInfo/m:place/m:placeTerm[@type="text"]', namespaces=NSDICT)[0].text)
    if mods.xpath('./m:originInfo/m:publisher', namespaces=NSDICT):
        wtf.setdefault('publisher', mods.xpath('./m:originInfo/m:publisher', namespaces=NSDICT)[0].text)
    if mods.xpath('./m:originInfo/m:dateIssued', namespaces=NSDICT):
        year = mods.xpath('./m:originInfo/m:dateIssued', namespaces=NSDICT)[0].text.replace('[', '').replace(']', '').replace('c', '')
        if type(year) == int:
            wtf.setdefault('issued', year)

    if mods.xpath('./m:language/m:languageTerm', namespaces=NSDICT):
        wtf.setdefault('language', mods.xpath('./m:language/m:languageTerm', namespaces=NSDICT)[0].text)

    if mods.xpath('./m:physicalDescription/m:extent', namespaces=NSDICT):
        wtf.setdefault('pages', mods.xpath('./m:physicalDescription/m:extent', namespaces=NSDICT)[0].text)

    if mods.xpath('./m:abstract', namespaces=NSDICT):
        abstract = {}
        abstract.setdefault('content', mods.xpath('./m:abstract', namespaces=NSDICT)[0].text)
        abstract.setdefault('shareable', True)
        wtf.setdefault('abstract', []).append(abstract)

    if mods.xpath('./m:note', namespaces=NSDICT):
        notes = mods.xpath('./m:note', namespaces=NSDICT)
        for note in notes:
            wtf.setdefault('note', []).append(note.text)

    if mods.xpath('./m:subject', namespaces=NSDICT):
        keywords = []
        subjects = mods.xpath('./m:subject', namespaces=NSDICT)
        for subject in subjects:
            for topic in subject:
                keywords.append(topic.text)
        wtf.setdefault('keyword', keywords)

    if mods.xpath('./m:classification', namespaces=NSDICT):
        classifications = mods.xpath('./m:classification', namespaces=NSDICT)
        for classification in classifications:
            tmp = {}
            if classification.get('authority') and classification.get('authority') == 'ddc':
                tmp.setdefault('id', classification.text)
                tmp.setdefault('label', '')
                wtf.setdefault('ddc_subject', []).append(tmp)

    if mods.xpath('./m:identifier[@type]', namespaces=NSDICT):
        ids = mods.xpath('./m:identifier[@type]', namespaces=NSDICT)
        for myid in ids:
            wtf.setdefault(str(myid.get('type')).upper(), []).append(myid.text)

    if mods.xpath('./m:relatedItem', namespaces=NSDICT):
        items = mods.xpath('./m:relatedItem', namespaces=NSDICT)
        for item in items:
            if item.get('type') and (item.get('type') == 'series' or item.get('type') == 'host'):
                tmp = {}
                for subitem in item:
                    if subitem.tag == '{http://www.loc.gov/mods/v3}titleInfo':
                        tmp.setdefault('is_part_of', subitem[0].text)
                        tmp.setdefault('volume', '')
                wtf.setdefault('is_part_of', []).append(tmp)

    # logging.debug('wtf_json: %s' % wtf)

    return wtf

