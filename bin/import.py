# The MIT License
#
#  Copyright 2015-2017 University Library Bochum <bibliogaphie-ub@rub.de> and UB Dortmund <api.ub@tu-dortmund.de>.
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

from __future__ import (absolute_import, division, print_function, unicode_literals)

import logging
from logging.handlers import RotatingFileHandler

import datetime
import requests
from requests import RequestException
import simplejson as json


try:
    import local_import_secrets as secrets
except ImportError:
    import import_secrets as secrets

log_formatter = logging.Formatter("[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s")

logger = logging.getLogger("Rotating Log")
logger.setLevel(logging.INFO)

handler = RotatingFileHandler(secrets.LOGFILE, maxBytes=10000, backupCount=1)
handler.setFormatter(log_formatter)

logger.addHandler(handler)


def timestamp():
    date_string = str(datetime.datetime.now())[:-3]
    if date_string.endswith('0'):
        date_string = '%s1' % date_string[:-1]

    return date_string


def cleanup(core=''):

    try:
        status = requests.get(
            'http://%s:%s/%s/%s/update?stream.body=<delete><query>*:*</query></delete>&commit=true' %
            (secrets.SOLR_HOST, secrets.SOLR_PORT, secrets.SOLR_APP, core))
    except requests.exceptions.ConnectionError:
        status = 'failed'


def preprocess_orga(data=None):

    if data:
        if data.get('parent_id') or data.get('parent_label'):
            parents = []
            parent = {}
            parent.setdefault('parent_id', data.get('parent_id'))
            parent.setdefault('parent_label', data.get('parent_label'))
            parents.append(parent)
            del data['parent_id']
            del data['parent_label']
            data.setdefault('parent', parents)
        # TODO id, gnd, dwid, parent_id, child_id, project_id: replace /, spatium
        if data.get('id'):
            data['id'] = data.get('id').strip().replace('/', '')
            if data.get('id').startswith('TUDO') or data.get('id').startswith('RUB'):
                if not data.get('dwid') or data.get('id') not in data.get('dwid'):
                    data['dwid'].append(data.get('id'))
        if data.get('gnd'):
            data['gnd'] = data.get('gnd').strip().replace('/', '')
        if data.get('parent'):
            for idx, parent in enumerate(data.get('parent')):
                data['parent'][idx]['parent_id'] = parent.get('parent_id').strip().replace('/', '')
        if data.get('children'):
            for idx, child in enumerate(data.get('children')):
                data['children'][idx]['child_id'] = child.get('child_id').strip().replace('/', '')
        if data.get('project'):
            for idx, project in enumerate(data.get('project')):
                data['project'][idx]['project_id'] = project.get('project_id').strip().replace('/', '')

    return data


def preprocess_group(data=None):

    if data:
        if data.get('parent_id') or data.get('parent_label'):
            parents = []
            parent = {}
            parent.setdefault('parent_id', data.get('parent_id'))
            parent.setdefault('parent_label', data.get('parent_label'))
            parents.append(parent)
            del data['parent_id']
            del data['parent_label']
            data.setdefault('parent', parents)
        # TODO id, gnd, dwid, parent_id, child_id, partner_id: replace /, spatium
        if data.get('id'):
            data['id'] = data.get('id').strip().replace('/', '')
        if data.get('gnd'):
            data['gnd'] = data.get('gnd').strip().replace('/', '')
        if data.get('parent'):
            for idx, parent in enumerate(data.get('parent')):
                data['parent'][idx]['parent_id'] = parent.get('parent_id').strip().replace('/', '')
        if data.get('children'):
            for idx, child in enumerate(data.get('children')):
                data['children'][idx]['child_id'] = child.get('child_id').strip().replace('/', '')
        if data.get('partners'):
            for idx, partner in enumerate(data.get('partners')):
                data['partners'][idx]['partner_id'] = partner.get('partner_id').strip().replace('/', '')

    return data


def preprocess_person(data=None):

    # TODO id, gnd, affiliation_id, group_id: replace /, spatium
    if data.get('id'):
        data['id'] = data.get('id').strip().replace('/', '')
    if data.get('gnd'):
        data['gnd'] = data.get('gnd').strip().replace('/', '')
    if data.get('group'):
        for idx, group in enumerate(data.get('group')):
            data['group'][idx]['group_id'] = group.get('group_id').strip().replace('/', '')
    if data.get('affiliation'):
        for idx, affiliation in enumerate(data.get('affiliation')):
            data['affiliation'][idx]['organisation_id'] = affiliation.get('organisation_id').strip().replace('/', '')

    return data


def preprocess_work(data=None):

    # TODO id, affiliation_id, group_id, has_part, is_part_of, other_version: replace /, spatium
    if data.get('id'):
        data['id'] = data.get('id').strip().replace('/', '')
    if data.get('has_part'):
        for idx, part in enumerate(data.get('has_part')):
            data['has_part'][idx]['has_part'] = part.get('has_part').strip().replace('/', '')
    if data.get('is_part_of'):
        for idx, host in enumerate(data.get('is_part_of')):
            data['is_part_of'][idx]['is_part_of'] = host.get('is_part_of').strip().replace('/', '')
    if data.get('other_version'):
        for idx, other_version in enumerate(data.get('other_version')):
            data['other_version'][idx]['other_version'] = other_version.get('other_version').strip().replace('/', '')
    if data.get('same_as'):
        for idx, same_as in enumerate(data.get('same_as')):
            data['same_as'][idx] = same_as.strip().replace('/', '')
    if data.get('affiliation_context'):
        for idx, affiliation_context in enumerate(data.get('affiliation_context')):
            data['affiliation_context'][idx] = affiliation_context.strip().replace('/', '')
    if data.get('group_context'):
        for idx, group_context in enumerate(data.get('group_context')):
            data['group_context'][idx] = group_context.strip().replace('/', '')

    return data


def import_data(entity_type='', file='', force='false', rewrite='false', rel='true'):

    if entity_type and file:

        not_imported = []

        with open(file) as data_file:
            import_json = json.load(data_file)

        # for each record in import_json do REST API POST
        cnt = 0
        for record in import_json:
            try:
                # preprocess data
                if entity_type == 'organisation':
                    json_to_post = json.dumps(preprocess_orga(record))
                elif entity_type == 'group':
                    json_to_post = json.dumps(preprocess_group(record))
                elif entity_type == 'person':
                    json_to_post = json.dumps(preprocess_person(record))
                elif entity_type == 'work':
                    json_to_post = json.dumps(preprocess_work(record))
                else:
                    json_to_post = json.dumps(record)

                # post data
                response = requests.post('%s/%s?force=%s&rewrite=%s&rel=%s' % (secrets.API, entity_type, force, rewrite, rel),
                                         headers={'Content-Type': 'application/json', 'Authorization': 'Bearer %s' % secrets.TOKEN},
                                         data=json_to_post
                                         )
                status = response.status_code
                logging.info('STATUS: %s' % status)
                if status == 201:
                    response_json = json.loads(response.content.decode("utf-8"))
                    if response_json.get('message'):
                        logging.info(response_json.get('message'))
                    cnt += 1
                else:
                    logger.error('%s: %s' % (status, response.content.decode("utf-8")))
                    not_imported.append(record)

            except requests.exceptions.ConnectionError as e:
                logging.error(e)

        print("Report: %s / %s records loaded!" % (cnt, len(import_json)))
        if not_imported:
            fo = open('../log/records.import_failed.json', 'w')
            fo.write(json.dumps(not_imported, indent=4))
            fo.close()

    else:
        print('Bad request!')


def import_orgas():
    print('START organisations: %s' % timestamp())
    cleanup('organisation')
    print('CLEANUP finnished: %s' % timestamp())
    print('LOAD DATA 1')
    import_data(
        entity_type='organisation',
        file='/home/hb2/2017-01-27_21-11-44_organisation.json',
        force='true',
        rewrite='false',
        rel='false'
    )
    print('END: %s' % timestamp())
    print('LOAD DATA 2')
    import_data(
        entity_type='organisation',
        file='/home/hb2/2017-01-27_21-11-44_organisation.json',
        force='false',
        rewrite='true',
        rel='true'
    )
    print('END organisations: %s' % timestamp())


def import_groups():
    print('START groups: %s' % timestamp())
    cleanup('group')
    print('CLEANUP finnished: %s' % timestamp())
    print('LOAD DATA 1')
    import_data(
        entity_type='group',
        file='/home/hb2/2017-01-27_21-11-44_group.json',
        force='true',
        rewrite='false',
        rel='false'
    )
    print('END: %s' % timestamp())
    print('LOAD DATA 2')
    import_data(
        entity_type='group',
        file='/home/hb2/2017-01-27_21-11-44_group.json',
        force='false',
        rewrite='true',
        rel='true'
    )
    print('END groups: %s' % timestamp())


def import_persons():
    print('START persons: %s' % timestamp())
    cleanup('person')
    # print('CLEANUP finnished: %s' % timestamp())
    print('LOAD DATA 1')
    import_data(
        entity_type='person',
        file='/home/hb2/2017-01-27_21-11-45_person.json',
        force='true',
        rewrite='false',
        rel='false'
    )
    print('END persons: %s' % timestamp())


def import_works():
    print('START works: %s' % timestamp())
    cleanup('hb2')
    print('CLEANUP finnished: %s' % timestamp())
    print('LOAD DATA 1')
    import_data(
        entity_type='work',
        file='/home/hb2/2017-01-27_21-05-02_hb2.json',
        force='true',
        rewrite='false',
        rel='false'
    )
    print('END: %s' % timestamp())
    print('LOAD DATA 2')
    import_data(
        entity_type='work',
        file='/home/hb2/2017-01-27_21-05-02_hb2.json',
        force='false',
        rewrite='true',
        rel='true'
    )
    print('END works: %s' % timestamp())

# import_orgas()
# import_groups()
import_persons()
# import_works()
