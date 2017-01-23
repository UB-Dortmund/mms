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

import orcid
import simplejson as json
from requests import RequestException

from processors import orcid_processor
from utils.solr_handler import Solr

try:
    import app_secrets
    import local_app_secrets as secrets
except ImportError:
    import app_secrets

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)-4s %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S')

# see also: https://github.com/ORCID/ORCID-Source/tree/master/orcid-model/src/main/resources/record_2.0_rc2


def orcid_user_info(affiliation='', orcid_id='', access_token=''):

    if affiliation:
        info = {}
        info.setdefault('orcid', orcid_id)

        sandbox = secrets.orcid_app_data.get(affiliation).get('sandbox')
        client_id = secrets.orcid_app_data.get(affiliation).get('sandbox_client_id')
        client_secret = secrets.orcid_app_data.get(affiliation).get('sandbox_client_secret')
        redirect_uri = secrets.orcid_app_data.get(affiliation).get('redirect_uri')
        if not sandbox:
            client_id = secrets.orcid_app_data.get(affiliation).get('client_id')
            client_secret = secrets.orcid_app_data.get(affiliation).get('client_secret')

        api = orcid.MemberAPI(client_id, client_secret, sandbox=sandbox)

        try:
            # get public_info from orcid
            public_info = api.read_record_public(orcid_id=orcid_id, request_type='person', token=access_token)
            print(json.dumps(public_info, indent=4))
            info.setdefault('name', '%s, %s' % (public_info.get('name').get('family-name').get('value'),
                                                public_info.get('name').get('given-names').get('value')))

            # get member_info from orcid
            member_info = api.read_record_member(orcid_id=orcid_id, request_type='activities', token=access_token)
            # print(json.dumps(member_info.get('employments'), indent=4))

            affil_here = {
                'organization': {
                    'name': 'Technische Universität Dortmund',
                    'address': {
                        'city': 'Dortmund',
                        'region': 'Nordrhein-Westfalen',
                        'country': 'DE'
                    }
                }
            }
            # print(json.dumps(affil_here, indent=4))

            doit = True
            if member_info.get('employments'):
                for orga in member_info.get('employments').get('employment-summary'):
                    affilliation = {
                        'organization': {
                            'address': orga.get('organization').get('address'),
                            'name': orga.get('organization').get('name')
                        }
                    }
                    if json.dumps(affil_here) == json.dumps(affilliation):
                        doit = False
                        # print('%s' % doit)



                        # info.setdefault('affiliation', member_info.get('employments'))
                        # info.setdefault('works', member_info.get('works'))
                        # print(json.dumps(info, indent=4))

        except RequestException as e:
            logging.error('ORCID-ERROR: %s' % e.response.text)

    else:
        logging.error('Bad request: affiliation has no value!')


def orcid_add_records(affiliation='', orcid_id='', access_token='', works=None):
    if works is None:
        works = {}

    if len(works) > 0:

        if affiliation:
            sandbox = secrets.orcid_app_data.get(affiliation).get('sandbox')
            client_id = secrets.orcid_app_data.get(affiliation).get('sandbox_client_id')
            client_secret = secrets.orcid_app_data.get(affiliation).get('sandbox_client_secret')
            if not sandbox:
                client_id = secrets.orcid_app_data.get(affiliation).get('client_id')
                client_secret = secrets.orcid_app_data.get(affiliation).get('client_secret')

            api = orcid.MemberAPI(client_id, client_secret, sandbox=sandbox)

            for record_id in works.keys():
                # logging.info('work: %s' % work)
                work = works.get(record_id)
                print(work)

                try:
                    put_code = api.add_record(orcid_id=orcid_id, token=access_token, request_type='work', data=work)

                    if put_code:
                        # lock record
                        lock_record_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                                application=secrets.SOLR_APP, core='hb2',
                                                data=[{'id': record_id, 'locked': {'set': 'true'}}])
                        lock_record_solr.update()
                        # search record
                        edit_record_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                                application=secrets.SOLR_APP, core='hb2', query='id:%s' % record_id)
                        edit_record_solr.request()
                        # load record in form and modify changeDate
                        thedata = json.loads(edit_record_solr.results[0].get('wtf_json'))
                        # add putcode to hb2
                        thedata.setdefault('orcid_put_code', put_code)
                        try:
                            # TODO load thedata to form
                            # save record # TODO problem: a restful PUT-service is needed!
                            _record2solr(form, action='update', relitems=False)
                        except AttributeError as e:
                            flash(gettext('ERROR linking from %s: %s' % (record_id, str(e))), 'error')
                        # unlock record
                        unlock_record_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                                  application=secrets.SOLR_APP, core='hb2',
                                                  data=[{'id': record_id, 'locked': {'set': 'false'}}])
                        unlock_record_solr.update()

                    # get info from orcid again
                    info = api.read_record_member(orcid_id=orcid_id, request_type='work', token=access_token,
                                                  put_code=put_code)
                    logging.info('info: %s' % info)

                except RequestException as e:
                    logging.error('ORCID-ERROR: %s' % e.response.text)

        else:
            logging.error('Bad request: affiliation has no value!')


def orcid_add_external_id(affiliation='', orcid_id='', access_token='', external_id=None):

    put_code = ''

    if affiliation:
        sandbox = secrets.orcid_app_data.get(affiliation).get('sandbox')
        client_id = secrets.orcid_app_data.get(affiliation).get('sandbox_client_id')
        client_secret = secrets.orcid_app_data.get(affiliation).get('sandbox_client_secret')
        if not sandbox:
            client_id = secrets.orcid_app_data.get(affiliation).get('client_id')
            client_secret = secrets.orcid_app_data.get(affiliation).get('client_secret')

        api = orcid.MemberAPI(client_id, client_secret, sandbox=sandbox)

        try:

            logging.info('external_id: %s' % external_id)

            put_code = api.add_record(orcid_id=orcid_id, token=access_token, request_type='external-identifiers',
                                      data=external_id)

            # get info from orcid again
            info = api.read_record_member(orcid_id=orcid_id, request_type='external-identifiers', token=access_token)
            logging.info('info: %s' % info)

        except RequestException as e:
            logging.error('ORCID-ERROR: %s' % e.response.text)
    else:
        logging.error('Bad request: affiliation has no value!')

    return put_code


def orcid_read_works(affiliation='', orcid_id='', access_token=''):

    works = []

    if affiliation:
        sandbox = secrets.orcid_app_data.get(affiliation).get('sandbox')
        client_id = secrets.orcid_app_data.get(affiliation).get('sandbox_client_id')
        client_secret = secrets.orcid_app_data.get(affiliation).get('sandbox_client_secret')
        if not sandbox:
            client_id = secrets.orcid_app_data.get(affiliation).get('client_id')
            client_secret = secrets.orcid_app_data.get(affiliation).get('client_secret')

        api = orcid.MemberAPI(client_id, client_secret, sandbox=sandbox)

        try:

            info = api.read_record_member(orcid_id=orcid_id, request_type='activities', token=access_token)
            # logging.info('info: %s' % info)
            works = info.get('works').get('group')

        except RequestException as e:
            logging.error('ORCID-ERROR: %s' % e.response.text)

    else:
        logging.error('Bad request: affiliation has no value!')

    return works


# ---------------------------------------


def dict_compare(d1, d2):
    d1_keys = set(d1.keys())
    d2_keys = set(d2.keys())
    intersect_keys = d1_keys.intersection(d2_keys)
    added = d1_keys - d2_keys
    removed = d2_keys - d1_keys
    modified = {o: (d1[o], d2[o]) for o in intersect_keys if d1[o] != d2[o]}
    same = set(o for o in intersect_keys if d1[o] == d2[o])
    return added, removed, modified, same

# ---------------------------------------


def get_records(affiliation='', query='*:*'):

    get_record_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                           application=secrets.SOLR_APP, query=query, rows=100000)
    get_record_solr.request()

    orcid_records = {}

    if len(get_record_solr.results) == 0:
        logging.error('No records found for query: %s' % query)
    else:
        # orcid_records.append(orcid_processor.wtf_orcid(affiliation=affiliation, wtf_records=[json.loads(get_record_solr.results[0].get('wtf_json'))])[0])
        for record in get_record_solr.results:
            wtf = json.loads(record.get('wtf_json'))
            orcid_records.setdefault(record.get('id'), orcid_processor.wtf_orcid(affiliation=affiliation, wtf_records=[wtf]))

    return orcid_records


def sync_orcid_to_hb():
    works = orcid_read_works(affiliation=affiliation, orcid_id=orcid_id, access_token=orcid_token)
    print('results: %s' % len(works))
    cnt = 0
    if works:
        for work in works:
            do_break = False
            for work_sum in work.get('work-summary'):
                # - putcode is not in hb2
                print('put_code: %s' % work_sum.get('put-code'))
                records = get_records(affiliation=affiliation, query='orcid_put_code:%s' % work_sum.get('put-code'))
                if len(records) > 0:
                    do_break = True
                    break
                logging.debug('external_ids: %s' % work_sum.get('external-ids').get('external-id'))
                for ext_id in work_sum.get('external-ids').get('external-id'):
                    # - doi is not in hb2
                    if ext_id.get('external-id-type') == 'doi':
                        print('doi: %s' % ext_id.get('external-id-value'))
                        records = get_records(affiliation=affiliation, query='doi:%s' % ext_id.get('external-id-value'))
                        if len(records) > 0:
                            do_break = True
                            break
                    # - isbn of book is not in hb2
                    if work_sum.get('type') == 'BOOK' and ext_id.get('external-id-type') == 'isbn':
                        print('isbn: %s' % ext_id.get('external-id-value'))
                        records = get_records(affiliation=affiliation,
                                              query='isbn:%s' % ext_id.get('external-id-value'))
                        if len(records) > 0:
                            do_break = True
                            break
                if do_break:
                    break
            if do_break:
                print('>> record already exists')
            else:
                print('>> record to add')
                cnt += 1
    print('results to add: %s' % cnt)


def sync_hb_to_orcid():
    records = get_records(affiliation=affiliation, query='pnd:"1049808495%23Becker, Hans-Georg"')
    orcid_add_records(affiliation=affiliation, orcid_id=orcid_id, access_token=orcid_token, works=records)



affiliation = 'tudo'
orcid_id = '0000-0003-0432-294X'
orcid_token = '8bde38f6-66a4-4346-b517-3af7134d740a'

# orcid_user_info(affiliation=affiliation, orcid_id=orcid_id, access_token=orcid_token)

external_ids = {
        'external-id-type': 'TU Dortmund ID',
        'external-id-value': '1234567890',
        'external-id-url': 'http://data.ub.tu-dortmund.de/resource/1234567890'}

# orcid_add_external_id(affiliation=affiliation, orcid_id=orcid_id, access_token=orcid_token, external_id=external_ids)

records = get_records(affiliation=affiliation, query='pnd:"1049808495%23Becker, Hans-Georg"')
print(json.dumps(records, indent=4))
# sync_orcid_to_hb()
