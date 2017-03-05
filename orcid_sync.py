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
from logging.handlers import RotatingFileHandler
import orcid
import simplejson as json
import requests
from requests import RequestException
import urllib

from processors import crossref_processor
from processors import datacite_processor
from processors import orcid_processor
from utils.solr_handler import Solr

try:
    import local_orcid_secrets as orcid_secrets
except ImportError:
    import orcid_secrets as orcid_secrets

try:
    import local_p_secrets as p_secrets
except ImportError:
    import p_secrets as p_secrets

log_formatter = logging.Formatter("[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s")

logger = logging.getLogger("ORCID")
logger.setLevel(logging.DEBUG)

handler = RotatingFileHandler(orcid_secrets.LOGFILE, maxBytes=1000000, backupCount=1)
handler.setFormatter(log_formatter)

logger.addHandler(handler)

# ---- ORCID functions ---- #
# see also: https://github.com/ORCID/ORCID-Source/tree/master/orcid-model/src/main/resources/record_2.0_rc2


def orcid_user_info(affiliation='', orcid_id='', access_token=''):

    if affiliation:
        info = {}
        info.setdefault('orcid', orcid_id)

        sandbox = orcid_secrets.orcid_app_data.get(affiliation).get('sandbox')
        client_id = orcid_secrets.orcid_app_data.get(affiliation).get('sandbox_client_id')
        client_secret = orcid_secrets.orcid_app_data.get(affiliation).get('sandbox_client_secret')
        redirect_uri = orcid_secrets.orcid_app_data.get(affiliation).get('redirect_uri')
        if not sandbox:
            client_id = orcid_secrets.orcid_app_data.get(affiliation).get('client_id')
            client_secret = orcid_secrets.orcid_app_data.get(affiliation).get('client_secret')

        api = orcid.MemberAPI(client_id, client_secret, sandbox=sandbox)

        try:
            # get public_info from orcid
            public_info = api.read_record_public(orcid_id=orcid_id, request_type='person', token=access_token)
            return public_info

        except RequestException as e:
            logging.error('ORCID-ERROR: %s' % e.response.text)

    else:
        logging.error('Bad request: affiliation has no value!')


def orcid_add_records(affiliation='', orcid_id='', access_token='', works=None):
    if works is None:
        works = {}

    if works:

        if affiliation:
            sandbox = orcid_secrets.orcid_app_data.get(affiliation).get('sandbox')
            client_id = orcid_secrets.orcid_app_data.get(affiliation).get('sandbox_client_id')
            client_secret = orcid_secrets.orcid_app_data.get(affiliation).get('sandbox_client_secret')
            if not sandbox:
                client_id = orcid_secrets.orcid_app_data.get(affiliation).get('client_id')
                client_secret = orcid_secrets.orcid_app_data.get(affiliation).get('client_secret')

            api = orcid.MemberAPI(client_id, client_secret, sandbox=sandbox)

            for record_id in works.keys():
                # logging.info('work: %s' % work)

                work = works.get(record_id)[0]
                print(work)

                try:
                    put_code = api.add_record(orcid_id=orcid_id, token=access_token, request_type='work', data=work)

                    if put_code:
                        update_json = {}
                        orcid_sync = {'orcid_id': orcid_id, 'orcid_put_code': str(put_code)}
                        update_json['orcid_sync'] = [orcid_sync]

                        logger.info('PUT /work/%s' % record_id)
                        # TODO PUT request
                        logger.info(json.dumps(update_json, indent=4))
                        try:
                            # put data
                            response = requests.put(
                                '%s/%s/%s' % (orcid_secrets.API, 'work', record_id),
                                headers={'Content-Type': 'application/json', 'Authorization': 'Bearer %s' % orcid_secrets.TOKEN},
                                data=json.dumps(update_json)
                                )
                            status = response.status_code
                            logger.info('STATUS: %s' % status)
                            if status == 200:
                                response_json = json.loads(response.content.decode("utf-8"))
                                logger.info(response_json.get('work'))
                                if response_json.get('message'):
                                    logger.info(response_json.get('message'))
                            else:
                                logger.error('ERROR: %s: %s' % (status, response.content.decode("utf-8")))

                        except requests.exceptions.ConnectionError as e:
                            logging.error(e)
                except RequestException as e:
                    logging.error('ORCID-ERROR: %s' % e.response.text)

                break
        else:
            logging.error('Bad request: affiliation has no value!')


def orcid_update_records(affiliation='', orcid_id='', access_token='', works=None):
    if works is None:
        works = {}

    if works:

        if affiliation:
            sandbox = orcid_secrets.orcid_app_data.get(affiliation).get('sandbox')
            client_id = orcid_secrets.orcid_app_data.get(affiliation).get('sandbox_client_id')
            client_secret = orcid_secrets.orcid_app_data.get(affiliation).get('sandbox_client_secret')
            if not sandbox:
                client_id = orcid_secrets.orcid_app_data.get(affiliation).get('client_id')
                client_secret = orcid_secrets.orcid_app_data.get(affiliation).get('client_secret')

            api = orcid.MemberAPI(client_id, client_secret, sandbox=sandbox)

            for record_id in works.keys():
                # logging.info('work: %s' % work)

                work = works.get(record_id)[0]
                print(json.dumps(work, indent=4))

                try:
                    put_code = int(record_id)
                    api.update_record(orcid_id=orcid_id, token=access_token,
                                      request_type='work', put_code=put_code, data=work)

                except RequestException as e:
                    logging.error('ORCID-ERROR: %s' % e.response.text)

                break
        else:
            logging.error('Bad request: affiliation has no value!')


def orcid_add_external_id(affiliation='', orcid_id='', access_token='', external_id=None):

    put_code = ''

    if affiliation:
        sandbox = orcid_secrets.orcid_app_data.get(affiliation).get('sandbox')
        client_id = orcid_secrets.orcid_app_data.get(affiliation).get('sandbox_client_id')
        client_secret = orcid_secrets.orcid_app_data.get(affiliation).get('sandbox_client_secret')
        if not sandbox:
            client_id = orcid_secrets.orcid_app_data.get(affiliation).get('client_id')
            client_secret = orcid_secrets.orcid_app_data.get(affiliation).get('client_secret')

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
        sandbox = orcid_secrets.orcid_app_data.get(affiliation).get('sandbox')
        client_id = orcid_secrets.orcid_app_data.get(affiliation).get('sandbox_client_id')
        client_secret = orcid_secrets.orcid_app_data.get(affiliation).get('sandbox_client_secret')
        if not sandbox:
            client_id = orcid_secrets.orcid_app_data.get(affiliation).get('client_id')
            client_secret = orcid_secrets.orcid_app_data.get(affiliation).get('client_secret')

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


# ---- HB 2 funktions ---- #

def get_new_records(affiliation='', query='*:*'):

    get_record_solr = Solr(host=p_secrets.SOLR_HOST, port=p_secrets.SOLR_PORT,
                           application=p_secrets.SOLR_APP,
                           query='%s AND -orcid_put_code:[\'\' TO *]' % query, rows=100000)
    get_record_solr.request()

    orcid_records = {}

    if len(get_record_solr.results) == 0:
        logging.error('No records found for query: %s' % query)
    else:
        print(len(get_record_solr.results))
        # orcid_records.append(orcid_processor.wtf_orcid(affiliation=affiliation, wtf_records=[json.loads(get_record_solr.results[0].get('wtf_json'))])[0])
        for record in get_record_solr.results:
            wtf = json.loads(record.get('wtf_json'))
            orcid_records.setdefault(record.get('id'), orcid_processor.wtf_orcid(affiliation=affiliation, wtf_records=[wtf]))

    return orcid_records


def get_updated_records(affiliation='', query='*:*'):

    get_record_solr = Solr(host=p_secrets.SOLR_HOST, port=p_secrets.SOLR_PORT,
                           application=p_secrets.SOLR_APP,
                           query='%s AND orcid_put_code:[\'\' TO *]' % query, rows=100000)
    get_record_solr.request()

    orcid_records = {}

    if len(get_record_solr.results) == 0:
        logging.error('No records found for query: %s' % query)
    else:
        print(len(get_record_solr.results))
        # orcid_records.append(orcid_processor.wtf_orcid(affiliation=affiliation, wtf_records=[json.loads(get_record_solr.results[0].get('wtf_json'))])[0])
        for record in get_record_solr.results:
            wtf = json.loads(record.get('wtf_json'))
            orcid_records.setdefault(record.get('orcid_put_code')[0], orcid_processor.wtf_orcid(affiliation=affiliation, wtf_records=[wtf]))

    return orcid_records


# ---- utils ---- #


def dict_compare(d1, d2):
    d1_keys = set(d1.keys())
    d2_keys = set(d2.keys())
    intersect_keys = d1_keys.intersection(d2_keys)
    added = d1_keys - d2_keys
    removed = d2_keys - d1_keys
    modified = {o: (d1[o], d2[o]) for o in intersect_keys if d1[o] != d2[o]}
    same = set(o for o in intersect_keys if d1[o] == d2[o])
    return added, removed, modified, same


# ---- ORCID plattform to HB 2 ---- #
# TODO get work records of ORCID member from ORCID plattform
# TODO for each ORCID record:
# - if 'put_code' already exists in HB 2: DO NOTHING
# - if 'doi' already exists in HB 2: add 'put_code' to record in HB 2
# - if 'wos_id' already exists in HB 2: add 'put_code' and 'doi' nd 'scopus_id' and 'pmid' to record in HB 2
# - if 'scopus_id' already exists in HB 2: add 'put_code' and 'doi' and 'wos_id' and 'pmid' to record in HB 2
# - if 'pmid' already exists in HB 2: add 'put_code' and 'doi' and 'wos_id' and 'scopus_id' to record in HB 2
# - else: transform record to HB 2 record and store it in HB 2
def sync_orcid_to_hb():
    get_user = Solr(host=p_secrets.SOLR_HOST, port=p_secrets.SOLR_PORT,
                    application=p_secrets.SOLR_APP, core='hb2_users',
                    query='orcidid:%s' % orcid_id)
    get_user.request()

    if get_user.results:
        if '/read-limited' in get_user.results[0].get('orcidscopes'):
            works = orcid_read_works(affiliation=affiliation, orcid_id=orcid_id, access_token=orcid_token)
            logger.info('results from ORCID: %s\n' % len(works))
            if works:
                for work in works:
                    do_break = False
                    hb2_record_id = None
                    orcid_record = None
                    for work_sum in work.get('work-summary'):
                        # - putcode is not in hb2
                        try:
                            response = requests.get('http://localhost:5007/work/%s' % work_sum.get('put-code'),
                                                    headers={'Accept': 'application/json'},
                                                    )
                            status = response.status_code
                            if status == 200:
                                hb2_record_id = json.loads(response.content.decode('utf8')).get('id')
                                do_break = True
                                break
                            else:
                                # print('\t\tNo record found for "%s"' % work_sum.get('put-code'))

                                # logging.debug('external_ids: %s' % work_sum.get('external-ids').get('external-id'))
                                for ext_id in work_sum.get('external-ids').get('external-id'):
                                    # - doi is not in hb2
                                    # print('type: %s - %s' % (ext_id.get('external-id-type'), ext_id.get('external-id-value')))

                                    # if exists record with doi
                                    if ext_id.get('external-id-type') == 'doi':
                                        doi = ext_id.get('external-id-value').replace('http://dx.doi.org/', '').replace('doi:', '')
                                        # print('\tdoi?: %s' % doi)

                                        try:
                                            # TODO not cool but currently the only way
                                            work_id = urllib.parse.quote_plus(urllib.parse.quote_plus(doi))
                                            response = requests.get(
                                                'http://localhost:5007/work/%s' % work_id,
                                                headers={'Accept': 'application/json'},
                                                )
                                            status = response.status_code
                                            if status == 200:
                                                hb2_record_id = json.loads(response.content).get('id')
                                                orcid_record = work_sum
                                                do_break = True
                                                break
                                            else:
                                                logger.info('\t\tNo record found for "%s"' % work_id)

                                        except requests.exceptions.ConnectionError:
                                            logger.error('REQUEST ERROR: %s' % ext_id.get('external-id-value'))

                                    # if exists record with pmid
                                    if ext_id.get('external-id-type') == 'pmid':
                                        pmid = ext_id.get('external-id-value')
                                        # print('\tpmid?: %s' % pmid)

                                        try:
                                            response = requests.get(
                                                'http://localhost:5007/work/%s' % pmid,
                                                headers={'Accept': 'application/json'},
                                                )
                                            status = response.status_code
                                            if status == 200:
                                                hb2_record_id = json.loads(response.content.decode('utf8')).get('id')
                                                orcid_record = work_sum
                                                do_break = True
                                                break
                                            else:
                                                logger.info('\t\tNo record found for "%s"' % pmid)

                                        except requests.exceptions.ConnectionError:
                                            logger.error('REQUEST ERROR: %s' % ext_id.get('external-id-value'))

                                    # if exists record with wos_id / isi_id
                                    if ext_id.get('external-id-type') == 'wosuid':
                                        wosuid = ext_id.get('external-id-value')
                                        # print('\twosuid?: %s' % wosuid)

                                        try:
                                            response = requests.get(
                                                'http://localhost:5007/work/%s' % wosuid,
                                                headers={'Accept': 'application/json'},
                                                )
                                            status = response.status_code
                                            if status == 200:
                                                hb2_record_id = json.loads(response.content.decode('utf8')).get('id')
                                                orcid_record = work_sum
                                                do_break = True
                                                break
                                            else:
                                                logger.info('\t\tNo record found for "%s"' % wosuid)

                                        except requests.exceptions.ConnectionError:
                                            logger.error('REQUEST ERROR: %s' % ext_id.get('external-id-value'))

                                    # if exists record with scopus_id / e_id
                                    if ext_id.get('external-id-type') == 'eid':
                                        eid = ext_id.get('external-id-value')
                                        # print('\teid?: %s' % eid)

                                        try:
                                            response = requests.get(
                                                'http://localhost:5007/work/%s' % eid,
                                                headers={'Accept': 'application/json'},
                                                )
                                            status = response.status_code
                                            if status == 200:
                                                hb2_record_id = json.loads(response.content.decode('utf8')).get('id')
                                                orcid_record = work_sum
                                                do_break = True
                                                break
                                            else:
                                                logger.info('\t\tNo record found for "%s"' % eid)

                                        except requests.exceptions.ConnectionError:
                                            logger.error('REQUEST ERROR: %s' % ext_id.get('external-id-value'))

                                    # - isbn of book is not in hb2
                                    if work_sum.get('type') == 'BOOK' and ext_id.get('external-id-type') == 'isbn':
                                        print('isbn: %s' % ext_id.get('external-id-value'))
                                        records = get_new_records(affiliation=affiliation,
                                                                  query='isbn:%s' % ext_id.get('external-id-value'))
                                        if len(records) > 0:
                                            do_break = True
                                            break

                        except requests.exceptions.ConnectionError:
                            logger.error('REQUEST ERROR: %s' % work_sum.get('put-code'))

                        if do_break:
                            break
                        else:
                            orcid_record = work_sum

                    if do_break:
                        # print('\t\t>> record already exists: %s <<' % hb2_record_id)
                        if orcid_record:
                            # TODO add orcid_put_code, wos_id, scopus_id and pmid to hb 2 record
                            update_json = {}
                            # print('\tadd orcid_put_code "%s"' % work_sum.get('put-code'))
                            orcid_sync = {'orcid_id': orcid_id, 'orcid_put_code': str(work_sum.get('put-code'))}
                            update_json['orcid_sync'] = [orcid_sync]
                            for extid in work_sum.get('external-ids').get('external-id'):
                                if extid.get('external-id-type') == 'eid':
                                    # print('\tadd scopus_id "%s"' % extid.get('external-id-value'))
                                    update_json['scopus_id'] = extid.get('external-id-value')
                                if extid.get('external-id-type') == 'wosuid':
                                    # print('\tadd wosuid "%s"' % extid.get('external-id-value'))
                                    update_json['WOSID'] = extid.get('external-id-value')
                                if extid.get('external-id-type') == 'pmid':
                                    # print('\tadd pmid "%s"' % extid.get('external-id-value'))
                                    update_json['PMID'] = extid.get('external-id-value')
                            logger.info('PUT /work/%s' % hb2_record_id)
                            # PUT request
                            # logger.info(json.dumps(update_json, indent=4))
                            try:
                                # put data
                                response = requests.put(
                                    '%s/%s/%s' % (orcid_secrets.API, 'work', hb2_record_id),
                                    headers={'Content-Type': 'application/json', 'Authorization': 'Bearer %s' % orcid_secrets.TOKEN},
                                    data=json.dumps(update_json)
                                    )
                                status = response.status_code
                                logger.info('STATUS: %s' % status)
                                if status == 200:
                                    response_json = json.loads(response.content.decode("utf-8"))
                                    logger.info(response_json.get('work'))
                                    if response_json.get('message'):
                                        logger.info(response_json.get('message'))
                                else:
                                    logger.error('ERROR: %s: %s' % (status, response.content.decode("utf-8")))
                            except requests.exceptions.ConnectionError as e:
                                logging.error(e)
                            logger.info('')
                    else:
                        logger.info('>> ADD RECORD <<')
                        thedata = None
                        doi = None
                        if orcid_record:
                            # if exists doi: get record from crossref or datacite
                            for extid in orcid_record.get('external-ids').get('external-id'):
                                if extid.get('external-id-type') == 'doi':
                                    doi = extid.get('external-id-value')
                                    break

                            print(doi)
                            print(doi.split('dx.doi.org/')[1])
                            if doi:

                                thedata = crossref_processor.crossref2wtfjson(doi=doi.split('dx.doi.org/')[1])
                                # if thedata == []: datacite request
                                if not thedata:
                                    thedata = datacite_processor.datacite2wtfjson(doi=doi.split('dx.doi.org/')[1])
                                print(json.dumps(thedata, indent=4))

                                # edit author information about the orcid member using all "aka"s
                                public_info = orcid_user_info(affiliation=affiliation, orcid_id=orcid_id, access_token=orcid_token)
                                # print(json.dumps(public_info, indent=4))
                                idx_to_change = -1
                                for other_name in public_info.get('other-names').get('other-name'):
                                    break_it = False
                                    for idx, person in enumerate(thedata.get('person')):
                                        name = '%s %s' % (person.get('name').split(', ')[1], person.get('name').split(', ')[0])
                                        print('%s vs. %s' % (name, other_name.get('content')))
                                        if name == other_name.get('content'):
                                            idx_to_change = idx
                                            break_it = True
                                            break
                                    if break_it:
                                        break
                                # print(idx_to_change)

                                person = {
                                    'name': thedata['person'][idx_to_change].get('name'),
                                    'orcid': orcid_id,
                                    'role': ['aut']
                                }

                                get_user = Solr(host=p_secrets.SOLR_HOST, port=p_secrets.SOLR_PORT,
                                                application=p_secrets.SOLR_APP, core='person',
                                                query='orcid:%s' % orcid_id)
                                get_user.request()

                                if get_user.results:
                                    if get_user.results[0].get('gnd'):
                                        person['gnd'] = get_user.results[0].get('gnd')

                                if affiliation == 'tudo':
                                    person['tudo'] = True
                                    person['rubi'] = False
                                    thedata['catalog'] = ['Technische Universität Dortmund']
                                elif affiliation == 'rub':
                                    person['tudo'] = False
                                    person['rubi'] = True
                                    thedata['catalog'] = ['Ruhr-Universität Bochum']
                                else:
                                    person['tudo'] = False
                                    person['rubi'] = False
                                    thedata['catalog'] = ['Temporäre Daten']

                                thedata['person'][idx_to_change] = person

                                for extid in orcid_record.get('external-ids').get('external-id'):
                                    if extid.get('external-id-type') == 'eid':
                                        # print('\tadd scopus_id "%s"' % extid.get('external-id-value'))
                                        thedata['scopus_id'] = extid.get('external-id-value')
                                    if extid.get('external-id-type') == 'wosuid':
                                        # print('\tadd wosuid "%s"' % extid.get('external-id-value'))
                                        thedata['WOSID'] = extid.get('external-id-value')
                                    if extid.get('external-id-type') == 'pmid':
                                        # print('\tadd pmid "%s"' % extid.get('external-id-value'))
                                        thedata['PMID'] = extid.get('external-id-value')

                                thedata['note'] = 'added by ORCID synchronization'
                                thedata['owner'] = ['daten.ub@tu-dortmund.de']
                                # print(json.dumps(thedata, indent=4))
                            else:
                                # logger.info(json.dumps(orcid_record, indent=4))
                                thedata = orcid_processor.orcid_wtf(orcid_id, orcid_record)
                                print(thedata)
                                # add author via orcid_user_info
                                public_info = orcid_user_info(affiliation=affiliation, orcid_id=orcid_id, access_token=orcid_token)
                                person = {
                                    'name': '%s, %s' % (public_info.get('name').get('family-name').get('value'), public_info.get('name').get('given-names').get('value')),
                                    'orcid': orcid_id,
                                    'role': ['aut']
                                }
                                if affiliation == 'tudo':
                                    person['tudo'] = True
                                    person['rubi'] = False
                                    thedata['catalog'] = ['Technische Universität Dortmund']
                                elif affiliation == 'rub':
                                    person['tudo'] = False
                                    person['rubi'] = True
                                    thedata['catalog'] = ['Ruhr-Universität Bochum']
                                else:
                                    person['tudo'] = False
                                    person['rubi'] = False
                                    thedata['catalog'] = ['Temporäre Daten']

                                thedata['person'] = [person]

                        if thedata:
                            logger.info('POST /work')
                            # POST request
                            logger.info(json.dumps(thedata, indent=4))
                            try:
                                # post data
                                response = requests.post(
                                    '%s/%s' % (orcid_secrets.API, 'work'),
                                    headers={'Content-Type': 'application/json', 'Authorization': 'Bearer %s' % orcid_secrets.TOKEN},
                                    data=json.dumps(thedata)
                                )
                                status = response.status_code
                                logger.info('STATUS: %s' % status)
                                if status == 201:
                                    response_json = json.loads(response.content.decode("utf-8"))
                                    logger.info(response_json.get('work'))
                                    if response_json.get('message'):
                                        logger.info(response_json.get('message'))
                                else:
                                    logger.error('ERROR: %s: %s' % (status, response.content.decode("utf-8")))

                            except requests.exceptions.ConnectionError as e:
                                logging.error(e)
                            logger.info('')


# ---- HB 2 to ORCID plattform ---- #
# TODO get ORCID members from HB 2
# TODO for each ORCID member: get work records from HB 2 (later: in requested range of time)
# TODO for each work record:
# - transform the data to an ORCID record and include the local record ID as external_id
# - POST data and add 'put_code' response in HB 2 record if not already contained
# - ADDITIONALLY sync 'doi', 'pmid', 'wos_id' and 'scopus_id' to HB 2 record if exists
def sync_hb_to_orcid():
    get_user = Solr(host=p_secrets.SOLR_HOST, port=p_secrets.SOLR_PORT,
                    application=p_secrets.SOLR_APP, core='hb2_users',
                    query='orcidid:%s' % orcid_id)
    get_user.request()

    if get_user.results:
        if '/activities/update' in get_user.results[0].get('orcidscopes'):
            # records = get_new_records(affiliation=affiliation, query='pnd:"1049808495%23Becker, Hans-Georg"')
            records = get_updated_records(affiliation=affiliation, query='pnd:"1019952040%23Höhner, Kathrin"')
            orcid_update_records(affiliation=affiliation, orcid_id=orcid_id, access_token=orcid_token, works=records)

###################################################

affiliation = 'tudo'
# TODO hagbeck
# orcid_id = '0000-0003-0432-294X'
# orcid_token = '8bde38f6-66a4-4346-b517-3af7134d740a'
# TODO Kathrin
orcid_id = '0000-0002-3988-7839'
orcid_token = '149e252e-1f2e-4137-bfb6-2003d0aceafb'

# TODO get user info
# orcid_user_info(affiliation=affiliation, orcid_id=orcid_id, access_token=orcid_token)

# TODO add external IDs to ORCID member
external_ids = {
        'external-id-type': 'TU Dortmund ID',
        'external-id-value': '1234567890',
        'external-id-url': 'http://data.ub.tu-dortmund.de/resource/1234567890'}

# orcid_add_external_id(affiliation=affiliation, orcid_id=orcid_id, access_token=orcid_token, external_id=external_ids)

# TODO show orcid works
# print(json.dumps(orcid_read_works(affiliation=affiliation, orcid_id=orcid_id, access_token=orcid_token), indent=4))

# TODO sync ORCID works to HB2
# sync_orcid_to_hb()

# TODO show works from HB2
# records = get_new_records(affiliation=affiliation, query='pnd:"1049808495%23Becker, Hans-Georg"')
# records = get_new_records(affiliation=affiliation, query='pnd:"1019952040%23Höhner, Kathrin"')
# print(json.dumps(records, indent=4))

# records = get_updated_records(affiliation=affiliation, query='pnd:"1049808495%23Becker, Hans-Georg"')
# print(json.dumps(records, indent=4))

# records = get_updated_records(affiliation=affiliation, query='recordChangeDate:[2017-02-06T16:08:00.000Z TO *]')
# print(json.dumps(records, indent=4))

# TODO sync HB2 works to ORCID
# sync_hb_to_orcid()
