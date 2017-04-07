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

import logging
from logging.handlers import RotatingFileHandler
import simplejson as json
import timeit
import urllib
import redis

from forms.forms import *

from processors import openurl_processor, wtf_csl

from utils import display_vocabularies
from utils.solr_handler import Solr

try:
    import local_p_secrets as secrets
except ImportError:
    import p_secrets as secrets

log_formatter = logging.Formatter("[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s")

logger = logging.getLogger("Rotating Log")
logger.setLevel(logging.INFO)

handler = RotatingFileHandler(secrets.LOGFILE, maxBytes=1000000, backupCount=1)
handler.setFormatter(log_formatter)

logger.addHandler(handler)


def get_work(work_id):
    get_request = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                       application=secrets.SOLR_APP, query='id:"%s"' % work_id)
    get_request.request()

    if len(get_request.results) == 0:
        get_request = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                           application=secrets.SOLR_APP, query='id:"%s/"' % work_id)
        get_request.request()

        if len(get_request.results) == 0:

            get_request = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                               application=secrets.SOLR_APP, query='same_as:%s' % work_id,
                               facet='false')
            get_request.request()

            if len(get_request.results) == 0:
                get_request = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                   application=secrets.SOLR_APP, query='doi:%s' % urllib.parse.unquote_plus(work_id),
                                   facet='false')
                get_request.request()

                if len(get_request.results) == 0:
                    get_request = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                       application=secrets.SOLR_APP, query='pmid:%s' % work_id,
                                       facet='false')
                    get_request.request()

                    if len(get_request.results) == 0:
                        get_request = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                           application=secrets.SOLR_APP, query='isi_id:%s' % work_id,
                                           facet='false')
                        get_request.request()

                        if len(get_request.results) == 0:
                            get_request = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                               application=secrets.SOLR_APP, query='e_id:%s' % work_id,
                                               facet='false')
                            get_request.request()

                            if len(get_request.results) == 0:
                                get_request = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                                   application=secrets.SOLR_APP, query='orcid_put_code:%s' % work_id,
                                                   facet='false')
                                get_request.request()

                                if len(get_request.results) == 0:
                                    return None
                                else:
                                    return get_request.results[0]
                            else:
                                return get_request.results[0]
                        else:
                            return get_request.results[0]
                    else:
                        return get_request.results[0]
                else:
                    return get_request.results[0]
            else:
                return get_request.results[0]
        else:
            return get_request.results[0]
    else:
        return get_request.results[0]


def get_person(person_id):
    get_request = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                       application=secrets.SOLR_APP, query='gnd:%s' % person_id, core='person',
                       facet='false')
    get_request.request()

    if len(get_request.results) == 0:
        get_request = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                           application=secrets.SOLR_APP, query='id:%s' % person_id, core='person',
                           facet='false')
        get_request.request()

        if len(get_request.results) == 0:
            get_request = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                               application=secrets.SOLR_APP, query='dwd:%s' % person_id, core='person',
                               facet='false')
            get_request.request()

            if len(get_request.results) == 0:
                get_request = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                   application=secrets.SOLR_APP, query='orcid:%s' % person_id, core='person',
                                   facet='false')
                get_request.request()

                if len(get_request.results) == 0:
                    get_request = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                       application=secrets.SOLR_APP, query='same_as:%s' % person_id, core='person',
                                       facet='false')
                    get_request.request()

                    if len(get_request.results) == 0:
                        return None
                    else:
                        return get_request.results[0]
                else:
                    return get_request.results[0]
            else:
                return get_request.results[0]
        else:
            return get_request.results[0]
    else:
        return get_request.results[0]


def get_orga(orga_id):
    get_request = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                       application=secrets.SOLR_APP, query='id:"%s"' % orga_id, core='organisation', facet='false')
    get_request.request()

    if len(get_request.results) == 0:
        get_request = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                           application=secrets.SOLR_APP, query='account:%s' % orga_id, core='organisation',
                           facet='false')
        get_request.request()

        if len(get_request.results) == 0:
            get_request = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                               application=secrets.SOLR_APP, query='same_as:%s' % orga_id, core='organisation',
                               facet='false')
            get_request.request()

            if len(get_request.results) == 0:
                return None
            else:
                return get_request.results[0]
        else:
            return get_request.results[0]
    else:
        return get_request.results[0]


def get_group(group_id):
    get_request = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                       application=secrets.SOLR_APP, query='id:%s' % group_id, core='group', facet='false')
    get_request.request()

    if len(get_request.results) == 0:

        get_request = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                           application=secrets.SOLR_APP, query='same_as:%s' % group_id, core='group',
                           facet='false')
        get_request.request()

        if len(get_request.results) == 0:
            return None
        else:
            return get_request.results[0]
    else:
        return get_request.results[0]


# TODO usage of work2solr without 'action' parameter!!!!!!!
# TODO usage of work2solr with parameter 'update_related_entities' instead of 'relitems'
# TODO usage of work2solr with an python object instead of a form!!!!!!!
def work2solr(record=None, storage_is_empty=False, update_related_entities=True, manage_queue=False):

    if record is None:
        record = {}

    message = []

    solr_data = {}
    has_part = []
    is_part_of = []
    other_version = []
    id = ''
    is_rubi = False
    is_tudo = False

    # logger.info('FORM: %s' % form.data)
    if record.get('id'):
        solr_data.setdefault('id', record.get('id').strip())
        id = str(record.get('id').strip())

    # creation and change date
    if not record.get('created'):
        record['created'] = timestamp()
        record['changed'] = record.get('created')
    else:
        if not storage_is_empty:
            record['changed'] = timestamp()

    # execution counter
    r = redis.StrictRedis(host=secrets.REDIS_EXEC_COUNTER_HOST, port=secrets.REDIS_EXEC_COUNTER_PORT,
                          db=secrets.REDIS_EXEC_COUNTER_DB)
    if r.hexists('record2solr', 'total'):
        cnt = int(r.hget('record2solr', 'total'))
        cnt += 1
        r.hset('record2solr', 'total', cnt)
    else:
        r.hset('record2solr', 'total', 1)

    if r.hexists('record2solr', id):
        cnt = int(r.hget('record2solr', id))
        cnt += 1
        r.hset('record2solr', id, cnt)
    else:
        r.hset('record2solr', id, 1)

    # start process
    start_total = timeit.default_timer()
    logger.debug('Profiling: start')

    logger.debug('Profiling: start fields')
    start = timeit.default_timer()

    for field in record.keys():
        # logging.info('%s => %s' % (field, form.data.get(field)))
        # record information
        if field == 'same_as':
            for same_as in record.get(field):
                if len(same_as.strip()) > 0:
                    solr_data.setdefault('same_as', []).append(same_as.strip())
        if field == 'created':
            if len(record.get(field).strip()) == 10:
                solr_data.setdefault('recordCreationDate', '%sT00:00:00.001Z' % record.get(field).strip())
            else:
                solr_data.setdefault('recordCreationDate', record.get(field).strip().replace(' ', 'T') + 'Z')
        if field == 'changed':
            if len(record.get(field).strip()) == 10:
                solr_data.setdefault('recordChangeDate', '%sT00:00:00.001Z' % record.get(field).strip())
            else:
                solr_data.setdefault('recordChangeDate', record.get(field).strip().replace(' ', 'T') + 'Z')
        if field == 'owner':
            for owner in record.get(field):
                solr_data.setdefault('owner', []).append(owner.strip())
        if field == 'catalog':
            for catalog in record.get(field):
                solr_data.setdefault('catalog', []).append(catalog.strip())
        if field == 'deskman' and record.get(field):
            solr_data.setdefault('deskman', record.get(field).strip())
        if field == 'editorial_status':
            solr_data.setdefault('editorial_status', record.get(field).strip())
        if field == 'apparent_dup':
            solr_data.setdefault('apparent_dup', record.get(field))

        if field == 'locked':
            solr_data.setdefault('locked', record.get(field))

        # the work
        if field == 'publication_status':
            solr_data.setdefault('publication_status', record.get(field).strip())
        if field == 'pubtype':
            solr_data.setdefault('pubtype', record.get(field).strip())
        if field == 'subtype':
            solr_data.setdefault('subtype', record.get(field).strip())
        if field == 'title':
            solr_data.setdefault('title', record.get(field).strip())
            solr_data.setdefault('exacttitle', record.get(field).strip())
            solr_data.setdefault('sorttitle', record.get(field).strip())
        if field == 'subtitle':
            solr_data.setdefault('subtitle', record.get(field).strip())
            solr_data.setdefault('other_title', record.get(field).strip())

        if field == 'subseries' and record.get(field).strip():
            # print('subseries: %s' % form.data.get(field).strip())
            solr_data.setdefault('subseries', record.get(field).strip())
        if field == 'subseries_sort' and record.get(field).strip():
            # print('subseries_sort: %s' % form.data.get(field).strip())
            solr_data.setdefault('subseries_sort', record.get(field).strip())
            solr_data.setdefault('fsubseries', '%s / %s' % (record.get('title').strip(), record.get(field).strip()))

        if field == 'title_supplement':
            solr_data.setdefault('other_title', record.get(field).strip())
        if field == 'other_title':
            for other_tit in record.get(field):
                # logging.info(other_tit)
                if other_tit:
                    solr_data.setdefault('parallel_title', other_tit.get('other_title').strip())
                    solr_data.setdefault('other_title', other_tit.get('other_title').strip())
        if field == 'issued' or field == 'application_date' or field == 'priority_date':
            if record.get(field):
                solr_data.setdefault('date', record.get(field).replace('[', '').replace(']', '').strip())
                solr_data.setdefault('fdate', record.get(field).replace('[', '').replace(']', '')[0:4].strip())
                if len(record.get(field).replace('[', '').replace(']', '').strip()) == 4:
                    solr_data.setdefault('date_boost',
                                         '%s-01-01T00:00:00Z' % record.get(field).replace('[', '').replace(']',
                                                                                                              '').strip())
                elif len(record.get(field).replace('[', '').replace(']', '').strip()) == 7:
                    solr_data.setdefault('date_boost',
                                         '%s-01T00:00:00Z' % record.get(field).replace('[', '').replace(']',
                                                                                                           '').strip())
                else:
                    solr_data.setdefault('date_boost',
                                         '%sT00:00:00Z' % record.get(field).replace('[', '').replace(']',
                                                                                                        '').strip())
        if field == 'publisher':
            solr_data.setdefault('publisher', record.get(field).strip())
            solr_data.setdefault('fpublisher', record.get(field).strip())
        if field == 'peer_reviewed':
            solr_data.setdefault('peer_reviewed', record.get(field))
        if field == 'language':
            for lang in record.get(field):
                if lang:
                    solr_data.setdefault('language', []).append(lang)

        # content and subjects
        if field == 'abstract':
            for abstract in record.get(field):
                if abstract.get('sharable'):
                    if abstract.get('content'):
                        solr_data.setdefault('abstract', []).append(abstract.get('content').strip())
                else:
                    if abstract.get('content'):
                        solr_data.setdefault('ro_abstract', []).append(abstract.get('content').strip())
        if field == 'keyword' or field == 'keyword_temporal' or field == 'keyword_geographic':
            for keyword in record.get(field):
                if keyword.strip():
                    solr_data.setdefault('subject', []).append(keyword.strip())

        if field == 'swd_subject':
            for keyword in record.get(field):
                if keyword.get('label') and keyword.get('label').strip():
                    solr_data.setdefault('subject', []).append(keyword.get('label').strip())
        if field == 'ddc_subject':
            for keyword in record.get(field):
                if keyword.get('label') and keyword.get('label').strip():
                    solr_data.setdefault('ddc', []).append(keyword.get('label').strip())
                    # TODO Feld für ddc-id und ggf. fddc mit id#label
                    # für die Befüllung muss einerseits das Mapping Kostenstelle<>DDC und andererseits auch
                    # bei 'parts' die DDC des 'host' berücksichtigt werden
                    # Muss hier auch die DDC-Hierarchie (zumindest in den ersten 100 Klassen)
                    # berücksichtigt werden?
        if field == 'mesh_subject':
            for keyword in record.get(field):
                if keyword.get('label') and keyword.get('label').strip():
                    solr_data.setdefault('mesh_term', []).append(keyword.get('label').strip())
        if field == 'stw_subject':
            for keyword in record.get(field):
                if keyword.get('label') and keyword.get('label').strip():
                    solr_data.setdefault('stwterm_de', []).append(keyword.get('label').strip())
        if field == 'lcsh_subject':
            for keyword in record.get(field):
                if keyword.get('label') and keyword.get('label').strip():
                    solr_data.setdefault('subject', []).append(keyword.get('label').strip())
        if field == 'thesoz_subject':
            for keyword in record.get(field):
                if keyword.get('label') and keyword.get('label').strip():
                    solr_data.setdefault('subject', []).append(keyword.get('label').strip())
        # IDs
        if field == 'DOI':
            try:
                for doi in record.get(field):
                    solr_data.setdefault('doi', []).append(doi.strip())
            except AttributeError as e:
                logging.error(record.get('id'))
                pass
        if field == 'ISSN':
            try:
                for issn in record.get(field):
                    solr_data.setdefault('issn', []).append(issn.strip())
                    solr_data.setdefault('isxn', []).append(issn.strip())
            except AttributeError as e:
                logging.error(record.get('id'))
                pass
        if field == 'ZDBID':
            try:
                for zdbid in record.get(field):
                    solr_data.setdefault('zdbid', []).append(zdbid.strip())
            except AttributeError as e:
                logging.error(record.get('id'))
                pass
        if field == 'ISBN':
            try:
                for isbn in record.get(field):
                    solr_data.setdefault('isbn', []).append(isbn.strip())
                    solr_data.setdefault('isxn', []).append(isbn.strip())
            except AttributeError as e:
                logging.error(record.get('id'))
                pass
        if field == 'ISMN':
            try:
                for ismn in record.get(field):
                    solr_data.setdefault('ismn', []).append(ismn.strip())
                    solr_data.setdefault('isxn', []).append(ismn.strip())
            except AttributeError as e:
                logging.error(record.get('id'))
                pass
        if field == 'PMID':
            solr_data.setdefault('pmid', record.get(field).strip())
        if field == 'WOSID':
            solr_data.setdefault('isi_id', record.get(field).strip())
        if field == 'orcid_sync':
            for link in record.get(field):
                if link.get('orcid_put_code').strip():
                    solr_data.setdefault('orcid_put_code', link.get('orcid_put_code').strip())
        if field == 'scopus_id':
            solr_data.setdefault('e_id', record.get(field).strip())

        # funding
        if field == 'note':
            if 'funded by the Deutsche Forschungsgemeinschaft' in record.get(field):
                record['DFG'] = True
                record['oa_funded'] = True
                solr_data.setdefault('dfg', record.get('DFG'))
                solr_data.setdefault('oa_funds', record.get('oa_funded'))

        if field == 'DFG':
            # print('DFG: %s' % form.data.get(field))
            if record.get(field):
                record['oa_funded'] = True
                solr_data.setdefault('dfg', record.get(field))
                solr_data.setdefault('oa_funds', record.get('oa_funded'))
            else:
                solr_data.setdefault('dfg', record.get(field))

        if field == 'oa_funded':
            # print('oa_funded: %s' % form.data.get(field))
            if record.get(field) or record.get('DFG'):
                solr_data.setdefault('oa_funds', True)
            else:
                solr_data.setdefault('oa_funds', False)

        if field == 'corresponding_affiliation' and record.get(field).strip():
            solr_data.setdefault('corresponding_affiliation', record.get(field).strip())

        if field == 'event':
            for event in record.get(field):
                solr_data.setdefault('other_title', event.get('event_name').strip())

        if field == 'container_title':
            solr_data.setdefault('journal_title', record.get(field).strip())
            solr_data.setdefault('fjtitle', record.get(field).strip())

        # related entities using requests to other entities if database isn't empty
        if not storage_is_empty:
            if field == 'person':
                # für alle personen
                for idx, person in enumerate(record.get(field)):
                    # hat die person einen namen?
                    if person.get('name'):
                        solr_data.setdefault('person', []).append(person.get('name').strip())
                        solr_data.setdefault('fperson', []).append(person.get('name').strip())
                        # hat die person eine gnd-id?
                        if person.get('gnd'):
                            # logging.info('drin: gnd: %s' % person.get('gnd'))
                            solr_data.setdefault('pnd', []).append(
                                '%s#%s' % (person.get('gnd').strip(), person.get('name').strip()))
                            solr_data.setdefault('pndid', []).append(
                                '%s' % person.get('gnd').strip())
                            # prüfe, ob eine 'person' mit GND im System ist.
                            result = get_person(person.get('gnd'))

                            if result:
                                myjson = json.loads(result.get('wtf_json'))
                                # TODO get ORCID iD
                                # TODO exists aka? then add more pnd-fields
                                # TODO get rubi/true boolean instead
                                for catalog in myjson.get('catalog'):
                                    if 'Bochum' in catalog:
                                        # logging.info("%s, %s: yo! rubi!" % (person.get('name'), person.get('gnd')))
                                        record['person'][idx]['rubi'] = True
                                        solr_data.setdefault('frubi_pers', []).append(
                                            '%s#%s' % (person.get('gnd').strip(), person.get('name').strip()))
                                        is_rubi = True
                                    if 'Dortmund' in catalog:
                                        record['person'][idx]['tudo'] = True
                                        solr_data.setdefault('ftudo_pers', []).append(
                                            '%s#%s' % (person.get('gnd').strip(), person.get('name').strip()))
                                        is_tudo = True
                            else:
                                message.append('ID from relation "person" could not be found! Ref: %s' % person.get('gnd'))

                        else:
                            # dummy gnd für die Identifizierung in "consolidate persons"
                            solr_data.setdefault('pnd', []).append(
                                '%s#person-%s#%s' % (record.get('id'), idx, person.get('name').strip()))

            if field == 'corporation':
                for idx, corporation in enumerate(record.get(field)):
                    if corporation.get('name'):
                        solr_data.setdefault('institution', []).append(corporation.get('name').strip())
                        solr_data.setdefault('fcorporation', []).append(corporation.get('name').strip())
                        if corporation.get('gnd'):
                            # logging.info('drin: gnd: %s' % corporation.get('gnd'))
                            solr_data.setdefault('gkd', []).append(
                                '%s#%s' % (corporation.get('gnd').strip(), corporation.get('name').strip()))
                            solr_data.setdefault('gkdid', []).append(
                                '%s' % corporation.get('gnd').strip())

                            # prüfe, ob eine 'person' mit GND im System ist.
                            result = get_orga(corporation.get('gnd'))
                            if result:
                                myjson = json.loads(result.get('wtf_json'))
                                # TODO allgemeiner?
                                for catalog in myjson.get('catalog'):
                                    if 'Bochum' in catalog:
                                        # logging.info("%s, %s: yo! rubi!" % (corporation.get('name'), corporation.get('gnd')))
                                        record['corporation'][idx]['rubi'] = True
                                        solr_data.setdefault('frubi_orga', []).append(
                                            '%s#%s' % (corporation.get('gnd').strip(), corporation.get('name').strip()))
                                        is_rubi = True
                                    if 'Dortmund' in catalog:
                                        record['corporation'][idx]['tudo'] = True
                                        solr_data.setdefault('ftudo_orga', []).append(
                                            '%s#%s' % (corporation.get('gnd').strip(), corporation.get('name').strip()))
                                        is_tudo = True
                            else:
                                message.append(
                                    'ID from relation "corporation" could not be found! Ref: %s' % corporation.get('gnd'))

                        else:
                            solr_data.setdefault('gkd', []).append(
                                '%s#corporation-%s#%s' % (record.get('id'), idx, corporation.get('name').strip()))
                    if corporation.get('role'):
                        if 'RadioTVProgram' in record.get('pubtype') and corporation.get('role')[0] == 'edt':
                            record['corporation'][idx]['role'] = 'brd'
                        if 'Thesis' in record.get('pubtype') and corporation.get('role')[0] == 'ctb':
                            record['corporation'][idx]['role'] = 'dgg'

            if field == 'affiliation_context':
                for context in record.get(field):
                    # logging.info(context)
                    if context:

                        result = get_orga(context)

                        if result:
                            myjson = json.loads(result.get('wtf_json'))
                            solr_data.setdefault('fakultaet', []).append(
                                '%s#%s' % (myjson.get('id'), myjson.get('pref_label')))
                            solr_data.setdefault('affiliation_id', []).append(myjson.get('id'))
                            # TODO allgemeiner?
                            for catalog in myjson.get('catalog'):
                                if 'Bochum' in catalog:
                                    # logging.info("%s, %s: yo! rubi!" % (corporation.get('name'), corporation.get('gnd')))
                                    solr_data.setdefault('frubi_orga', []).append(
                                        '%s#%s' % (myjson.get('id'), myjson.get('pref_label')))
                                    is_rubi = True
                                if 'Dortmund' in catalog:
                                    solr_data.setdefault('ftudo_orga', []).append(
                                        '%s#%s' % (myjson.get('id'), myjson.get('pref_label')))
                                    is_tudo = True
                        else:
                            solr_data.setdefault('fakultaet', []).append(context)
                            message.append('ID from relation "affiliation" could not be found! Ref: %s' % context)

            if field == 'group_context':
                for context in record.get(field):
                    # logging.info(context)
                    if context:

                        result = get_group(context)

                        if result:
                            myjson = json.loads(result.get('wtf_json'))
                            solr_data.setdefault('group_id', []).append(myjson.get('id'))
                            solr_data.setdefault('group', []).append(
                                '%s#%s' % (myjson.get('id'), myjson.get('pref_label')))
                            # TODO allgemeiner?
                            for catalog in myjson.get('catalog'):
                                if 'Bochum' in catalog:
                                    # logging.info("%s, %s: yo! rubi!" % (corporation.get('name'), corporation.get('gnd')))
                                    solr_data.setdefault('frubi_orga', []).append(
                                        '%s#%s' % (myjson.get('id'), myjson.get('pref_label')))
                                    is_rubi = True
                                if 'Dortmund' in catalog:
                                    solr_data.setdefault('ftudo_orga', []).append(
                                        '%s#%s' % (myjson.get('id'), myjson.get('pref_label')))
                                    is_tudo = True
                        else:
                            solr_data.setdefault('group', []).append(context)
                            message.append('ID from relation "group" could not be found! Ref: %s' % context)

            if field == 'is_part_of' and len(record.get(field)) > 0:
                ipo_ids = []
                ipo_index = {}
                try:
                    for idx, ipo in enumerate(record.get(field)):
                        if ipo:
                            # logging.info(ipo)
                            if 'is_part_of' in ipo:
                                # logging.info('POOP')
                                if ipo.get('is_part_of') != '':
                                    ipo_ids.append(ipo.get('is_part_of').strip())
                                    ipo_index.setdefault(ipo.get('is_part_of').strip(), idx)
                            else:
                                # logging.info('PEEP')
                                ipo_ids.append(ipo)
                                ipo_index.setdefault(ipo, idx)
                    query = ''
                    if len(ipo_ids) > 1:
                        query = '{!terms f=id}%s' % ','.join(ipo_ids)
                    if len(ipo_ids) == 1:
                        query = 'id:%s' % ipo_ids[0]
                    if len(ipo_ids) > 0:
                        ipo_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                        application=secrets.SOLR_APP, query=query, rows=len(ipo_ids), facet='false',
                                        fields=['wtf_json'])
                        ipo_solr.request()
                        if len(ipo_solr.results) == 0:
                            message.append('Not all IDs from relation "is part of" could be found! Ref: %s' % record.get('id'))
                        for doc in ipo_solr.results:
                            myjson = json.loads(doc.get('wtf_json'))
                            is_part_of.append(myjson.get('id'))
                            idx = ipo_index.get(myjson.get('id'))
                            title = myjson.get('title')
                            if myjson.get('subseries'):
                                title = '%s / %s' % (title, myjson.get('subseries'))
                            solr_data.setdefault('is_part_of_id', []).append(myjson.get('id'))
                            solr_data.setdefault('is_part_of', []).append(json.dumps({'pubtype': myjson.get('pubtype'),
                                                                                      'id': myjson.get('id'),
                                                                                      'title': title,
                                                                                      'issn': myjson.get('issn'),
                                                                                      'isbn': myjson.get('isbn'),
                                                                                      'page_first': record.get(field)[
                                                                                          idx].get('page_first', ''),
                                                                                      'page_last': record.get(field)[
                                                                                          idx].get('page_last', ''),
                                                                                      'volume': record.get(field)[
                                                                                          idx].get('volume', ''),
                                                                                      'issue': record.get(field)[
                                                                                          idx].get('issue', '')}))
                except AttributeError as e:
                    logging.error(e)

            if field == 'has_part' and len(record.get(field)) > 0:
                hp_ids = []
                try:
                    for idx, hp in enumerate(record.get(field)):
                        if hp:
                            if 'has_part' in hp:
                                if hp.get('has_part') != '':
                                    hp_ids.append(hp.get('has_part').strip())
                            else:
                                # logging.info('PEEP')
                                hp_ids.append(hp)
                    queries = []
                    if len(hp_ids) == 1:
                        queries.append('id:%s' % hp_ids[0])
                    if len(hp_ids) > 1:
                        query = '{!terms f=id}'
                        tmp = []
                        for hp_id in hp_ids:
                            if len(tmp) < 2:
                                tmp.append(hp_id)
                            elif len(query + ','.join(tmp) + ',' + hp_id) < 7168:
                                tmp.append(hp_id)
                            else:
                                queries.append('{!terms f=id}%s' % ','.join(tmp))
                                tmp = [hp_id]
                        if len(tmp) > 0:
                            queries.append('{!terms f=id}%s' % ','.join(tmp))
                    if len(queries) > 0:
                        for query in queries:
                            hp_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                           application=secrets.SOLR_APP, query=query, rows=len(hp_ids), facet='false',
                                           fields=['wtf_json'])
                            hp_solr.request()
                            if len(hp_solr.results) == 0:
                                message.append('Not all IDs from relation "has part" could be found! Ref: %s' % record.get(
                                                'id'))
                            for doc in hp_solr.results:
                                myjson = json.loads(doc.get('wtf_json'))
                                has_part.append(myjson.get('id'))
                                # logging.debug('PARTS: myjson.get(\'is_part_of\') = %s' % myjson.get('is_part_of'))
                                if len(myjson.get('is_part_of')) > 0:
                                    for host in myjson.get('is_part_of'):
                                        # logging.debug('PARTS: host = %s' % host)
                                        # logging.debug('PARTS: %s vs. %s' % (host.get('is_part_of'), id))
                                        if host.get('is_part_of') == id:
                                            solr_data.setdefault('has_part_id', []).append(myjson.get('id'))
                                            solr_data.setdefault('has_part', []).append(json.dumps({'pubtype': myjson.get('pubtype'),
                                                                                                    'id': myjson.get('id'),
                                                                                                    'title': myjson.get('title'),
                                                                                                    'page_first': host.get('page_first', ''),
                                                                                                    'page_last': host.get('page_last', ''),
                                                                                                    'volume': host.get('volume', ''),
                                                                                                    'issue': host.get('issue', '')}))
                                # logging.info(solr_data.get('has_part'))
                except AttributeError as e:
                    logging.error('has_part: %s' % e)

            if field == 'other_version' and len(record.get(field)) > 0:
                # for myov in form.data.get(field):
                # logging.info('OV ' + myov)
                ov_ids = []
                try:
                    for version in record.get(field):
                        if version.get('other_version') != '':
                            ov_ids.append(version.get('other_version'))
                    query = ''
                    if len(ov_ids) > 0:
                        query = '{!terms f=id}%s' % ','.join(ov_ids)
                    if len(ov_ids) == 1:
                        query = 'id:%s' % ov_ids[0]
                    if len(ov_ids) > 0:
                        ov_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                       application=secrets.SOLR_APP, query=query, facet='false', fields=['wtf_json'])
                        ov_solr.request()
                        if len(ov_solr.results) == 0:
                            message.append('Not all IDs from relation "other version" could be found! Ref: %s' % record.get(
                                            'id'))
                        for doc in ov_solr.results:
                            # logging.info(json.loads(doc.get('wtf_json')))
                            myjson = json.loads(doc.get('wtf_json'))
                            other_version.append(myjson.get('id'))
                            solr_data.setdefault('other_version_id', []).append(myjson.get('id'))
                            solr_data.setdefault('other_version', []).append(json.dumps({'pubtype': myjson.get('pubtype'),
                                                                                         'id': myjson.get('id'),
                                                                                         'title': myjson.get('title')}))
                except AttributeError as e:
                    logging.error(e)

    stop = timeit.default_timer()
    fields = stop - start
    logger.debug('Profiling: fields - %s' % fields)

    logger.debug('Profiling: start wtf_json')
    start = timeit.default_timer()
    solr_data.setdefault('rubi', is_rubi)
    solr_data.setdefault('tudo', is_tudo)

    wtf_json = json.dumps(record).replace(' "', '"')
    solr_data.setdefault('wtf_json', wtf_json)
    stop = timeit.default_timer()
    wtf = stop - start
    logger.debug('Profiling: wtf - %s' % wtf)

    # build CSL-JSON
    logger.debug('Profiling: start csl')
    start = timeit.default_timer()
    csl_json = json.dumps(wtf_csl.wtf_csl(wtf_records=[json.loads(wtf_json)]))
    solr_data.setdefault('csl_json', csl_json)
    stop = timeit.default_timer()
    csl = stop - start
    logger.debug('Profiling: csl - %s' % csl)

    # build openurl
    logger.debug('Profiling: start openurl')
    start = timeit.default_timer()
    open_url = openurl_processor.wtf_openurl(json.loads(wtf_json))
    solr_data.setdefault('bibliographicCitation', open_url)
    stop = timeit.default_timer()
    z3988 = stop - start
    logger.debug('Profiling: openurl - %s' % z3988)

    # store record
    record_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                       application=secrets.SOLR_APP, core='hb2', data=[solr_data])
    record_solr.update()

    stop = timeit.default_timer()
    stored = stop - start_total
    logger.debug('Profiling: self stored - %s' % stored)

    # reload all records listed in has_part, is_part_of, other_version
    # logger.debug('relitems = %s' % relitems)
    # logger.info('has_part: %s' % len(has_part))
    # logger.info('is_part_of: %s' % len(is_part_of))
    # logger.info('other_version: %s' % len(other_version))
    queue = None
    if update_related_entities:
        if manage_queue:
            queue = has_part + is_part_of + other_version
        else:
            logger.debug('Profiling: start relitems')
            start_relitems = timeit.default_timer()

            for record_id in has_part:
                logger.debug('Profiling: start get part - %s' % record_id)
                start_part = timeit.default_timer()

                # search record
                result = get_work(record_id)

                stop = timeit.default_timer()
                duration = stop - start
                logger.debug('Profiling: end get part - %s' % duration)

                if result:
                    # load record in form and modify changeDate
                    logger.debug('Profiling: start modify part')
                    start = timeit.default_timer()
                    thedata = json.loads(result.get('wtf_json'))
                    form = display_vocabularies.PUBTYPE2FORM.get(thedata.get('pubtype')).from_json(thedata)

                    # add is_part_of to form if not exists
                    exists = False
                    if form.data.get('is_part_of'):
                        for ipo in form.data.get('is_part_of'):
                            if ipo.get('is_part_of') == id:
                                exists = True
                                break
                    if not exists:
                        is_part_of_form = IsPartOfForm()
                        is_part_of_form.is_part_of.data = id
                        form.is_part_of.append_entry(is_part_of_form.data)

                    # save record
                    try:
                        form.changed.data = timestamp()
                        work2solr(record=form.data, update_related_entities=False)
                    except AttributeError as e:
                        logger.error('linking from %s: %s' % (record_id, str(e)))
                    stop = timeit.default_timer()
                    duration = stop - start
                    logger.debug('Profiling: end modify part - %s' % duration)
                else:
                    message.append('ID from relation "has_part" could not be found! Ref: %s' % record_id)

                stop_part = timeit.default_timer()
                duration = stop_part - start_part
                logger.debug('Profiling: end part - %s' % duration)

            for record_id in is_part_of:

                logger.debug('Profiling: start get host')
                start = timeit.default_timer()
                result = get_work(record_id)
                stop = timeit.default_timer()
                duration = stop - start
                logger.debug('Profiling: end get host - %s' % duration)

                if result:
                    # load record in form and modify changeDate
                    logger.debug('Profiling: start modify host')
                    start = timeit.default_timer()
                    thedata = json.loads(result.get('wtf_json'))
                    form = display_vocabularies.PUBTYPE2FORM.get(thedata.get('pubtype')).from_json(thedata)

                    # add has_part to form
                    exists = False
                    if form.data.get('has_part'):
                        for hpo in form.data.get('has_part'):
                            if hpo.get('has_part') == id:
                                exists = True
                                break
                    if not exists:
                        has_part_form = HasPartForm()
                        has_part_form.has_part.data = id
                        form.has_part.append_entry(has_part_form.data)

                    # save record
                    try:
                        form.changed.data = timestamp()
                        work2solr(record=form.data, update_related_entities=False)
                    except AttributeError as e:
                        logger.error('linking from %s: %s' % (record_id, str(e)))
                    stop = timeit.default_timer()
                    duration = stop - start
                    logger.debug('Profiling: end modify host - %s' % duration)
                else:
                    message.append('ID from relation "is_part_of" could not be found! Ref: %s' % record_id)

            for record_id in other_version:

                result = get_work(record_id)

                if result:
                    # load record in form and modify changeDate
                    thedata = json.loads(result.get('wtf_json'))
                    form = display_vocabularies.PUBTYPE2FORM.get(thedata.get('pubtype')).from_json(thedata)

                    # add is_part_of to form
                    exists = False
                    if form.data.get('other_version'):
                        for ovo in form.data.get('other_version'):
                            if ovo.get('other_version') == id:
                                exists = True
                                break
                    if not exists:
                        other_version_form = OtherVersionForm()
                        other_version_form.other_version.data = id
                        form.other_version.append_entry(other_version_form.data)

                    # save record
                    try:
                        form.changed.data = timestamp()
                        work2solr(record=form.data, update_related_entities=False)
                    except AttributeError as e:
                        logger.error('linking from %s: %s' % (record_id, str(e)))
                else:
                    message.append('ID from relation "other_version" could not be found! Ref: %s' % record_id)

            # TODO link all records as 'has_part' which has a 'same_as'-ID in 'is_part_of'

            # TODO link all records as 'is_part_of' which has a 'same_as'-ID in 'has_part'

            # TODO link all records as 'other_version' which has a 'same_as'-ID in 'other_version'

            stop_relitems = timeit.default_timer()
            duration = stop_relitems - start_relitems
            logger.debug('Profiling: end relitems - %s' % duration)

        stop_total = timeit.default_timer()
        duration = stop_total - start_total
        logger.debug('Profiling: end - %s' % duration)

    return id, message, queue


# TODO usage of person2solr without 'action' parameter!!!!!!!
# TODO usage of person2solr without return value 'doit'
# TODO usage of person2solr with parameter 'update_related_entities' instead of 'relitems'
# TODO usage of work2solr with an python object instead of a form!!!!!!!
def person2solr(record=None, storage_is_empty=False, update_related_entities=True, manage_queue=False):

    if record is None:
        record = {}

    message = []
    tmp = {}

    new_id = record.get('id')
    if record.get('dwid') and record.get('dwid').strip():
        tmp.setdefault('dwid', record.get('dwid'))
        new_id = tmp.get('dwid')
    if record.get('gnd') and record.get('gnd').strip():
        tmp.setdefault('gnd', record.get('gnd'))
        new_id = tmp.get('gnd')

    # creation and change date
    if not record.get('created'):
        record['created'] = timestamp()
        record['changed'] = record.get('created')
    else:
        if not storage_is_empty:
            record['changed'] = timestamp()

    for field in record.keys():
        if field == 'name':
            tmp.setdefault('name', record.get(field).strip())
        elif field == 'also_known_as':
            for also_known_as in record.get(field):
                if also_known_as.strip():
                    tmp.setdefault('also_known_as', []).append(str(also_known_as).strip())
        elif field == 'same_as':
            for same_as in record.get(field):
                if same_as.strip():
                    tmp.setdefault('same_as', []).append(same_as.strip())
        elif field == 'orcid':
            if record.get(field).strip():
                tmp.setdefault('orcid', record.get(field).strip())
        elif field == 'email':
            tmp.setdefault('email', record.get(field))
        elif field == 'rubi':
            tmp.setdefault('rubi', record.get(field))
        elif field == 'tudo':
            tmp.setdefault('tudo', record.get(field))
        elif field == 'created':
            tmp.setdefault('created', record.get(field).strip().replace(' ', 'T') + 'Z')
        elif field == 'changed':
            tmp.setdefault('changed', record.get(field).strip().replace(' ', 'T') + 'Z')
        elif field == 'catalog':
            for catalog in record.get(field):
                tmp.setdefault('catalog', catalog.strip())
        elif field == 'status':
            for status in record.get(field):
                tmp.setdefault('personal_status', []).append(status.strip())
        elif field == 'editorial_status':
            tmp.setdefault('editorial_status', record.get(field))
        elif field == 'deskman' and record.get(field):
            tmp.setdefault('deskman', record.get(field).strip())
        elif field == 'owner':
            for owner in record.get(field):
                tmp.setdefault('owner', owner.strip())
        elif field == 'url':
            for url in record.get(field):
                if url.get('label') and url.get('label').strip():
                    tmp.setdefault('url', []).append(url.get('label').strip())
        elif field == 'data_supplied':
            if record.get(field).strip() != "":
                tmp.setdefault('data_supplied', '%sT00:00:00.001Z' % record.get(field).strip())

        if not storage_is_empty:
            if field == 'affiliation':
                for idx, affiliation in enumerate(record.get(field)):
                    if affiliation.get('organisation_id'):

                        result = get_orga(affiliation.get('organisation_id'))

                        if result:
                            myjson = json.loads(result.get('wtf_json'))

                            record['affiliation'][idx]['organisation_id'] = myjson.get('id').strip()
                            tmp.setdefault('affiliation_id', []).append(myjson.get('id').strip())

                            label = myjson.get('pref_label').strip()
                            record['affiliation'][idx]['pref_label'] = label
                            tmp.setdefault('affiliation', []).append(label)
                            tmp.setdefault('faffiliation', []).append(label)
                        else:
                            message.append(
                                'ID from relation "organisation_id" could not be found! Ref: %s' % affiliation.get(
                                    'organisation_id'))

                    elif affiliation.get('pref_label'):
                        tmp.setdefault('affiliation', []).append(affiliation.get('pref_label').strip())
                        tmp.setdefault('faffiliation', []).append(affiliation.get('pref_label').strip())

            elif field == 'group':
                for idx, group in enumerate(record.get(field)):
                    if group.get('group_id'):

                        result = get_group(group.get('group_id'))

                        if result:
                            myjson = json.loads(result.get('wtf_json'))

                            record['group'][idx]['group_id'] = myjson.get('id').strip()
                            tmp.setdefault('affiliation_id', []).append(group.get('group_id'))

                            label = myjson.get('pref_label').strip()
                            record['group'][idx]['pref_label'] = label
                            tmp.setdefault('group', []).append(label)
                            tmp.setdefault('fgroup', []).append(label)

                        else:
                            message.append('ID from relation "group_id" could not be found! Ref: %s' % group.get(
                                'group_id'))

                    elif group.get('pref_label'):
                        tmp.setdefault('group', []).append(group.get('pref_label').strip())
                        tmp.setdefault('fgroup', []).append(group.get('pref_label').strip())

    # set primary id
    gnd_to_change = ''
    if new_id != record.get('id'):
        get_request = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                           application=secrets.SOLR_APP, query='gnd:"%s"' % record.get('id'),
                           core='person', facet='false')
        get_request.request()
        if get_request.results and new_id == record.get('gnd'):
            # Änderung der GND-ID!
            gnd_to_change = record.get('id')
        else:
            record['same_as'].append_entry(record.get('id'))
            tmp.setdefault('same_as', []).append(record.get('id'))

        # delete record with current id
        try:
            delete_person_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                      application=secrets.SOLR_APP, core='person', del_id=record.get('id'))
            delete_person_solr.delete()
        except Exception as e:
            logging.error(e)
        record['id'] = new_id
    else:
        if not record.get('gnd'):
            get_request = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                               application=secrets.SOLR_APP, query='gnd:"%s"' % record.get('id'),
                               core='person', facet='false')
            get_request.request()
            if get_request.results:
                # GND-ID gelöscht
                if record.get('dwid'):
                    record['id'] = record.get('dwid')
                elif record.get('same_as'):
                    for same_as in record.get('same_as'):
                        if same_as.strip():
                            record['id'] = same_as.strip()
                            break
                else:
                    record['id'] = str(uuid.uuid4())

                # delete record with current id
                try:
                    delete_person_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                              application=secrets.SOLR_APP, core='person', del_id=new_id)
                    delete_person_solr.delete()
                except Exception as e:
                    logging.error(e)

    tmp.setdefault('id', record['id'])
    wtf_json = json.dumps(record)
    tmp.setdefault('wtf_json', wtf_json)
    person_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                       application=secrets.SOLR_APP, core='person', data=[tmp])
    person_solr.update()

    # TODO if GND-ID changed: for all works using the old GND-ID, change the GND-ID
    if gnd_to_change:
        logger.debug('build bulk update file and store in "bulk_update_watch_folder"')

    queue = None
    if update_related_entities and record.get('gnd'):

        # update all works linked with the current GND-ID
        works_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                          application=secrets.SOLR_APP, core='hb2',
                          query='pndid:%s' % record.get('gnd'), facet=False, rows=2000000)
        works_solr.request()

        if works_solr.results:

            if manage_queue:
                logger.debug('build works queue')
                queue = []
                for work in works_solr.results:
                    queue.append(work.get('id'))
            else:
                logger.debug('update works')
                for work in works_solr.results:
                    # edit
                    try:
                        thedata = json.loads(work.get('wtf_json'))
                        form = display_vocabularies.PUBTYPE2FORM.get(thedata.get('pubtype')).from_json(thedata)
                        form.changed.data = timestamp()
                        work2solr(record=form.data, update_related_entities=False)
                    except Exception as e:
                        logging.error(e)
                        logging.error('thedata: %s' % work.get('wtf_json'))

    return new_id, message, queue


# TODO usage of orga2solr without 'action' parameter!!!!!!!
# TODO usage of orga2solr with parameter 'update_related_entities' instead of 'relitems'
# TODO usage of orga2solr with an python object instead of a form!!!!!!!
def orga2solr(record=None, storage_is_empty=False, update_related_entities=True, manage_queue=False):

    if record is None:
        record = {}

    message = []
    tmp = {}

    record_id = record.get('id')
    new_id = record.get('id')
    if record.get('dwid'):
        for account in record.get('dwid'):
            if account.strip():
                tmp.setdefault('account', []).append(account.strip())
        if tmp.get('account'):
            new_id = tmp.get('account')[0]
    if record.get('gnd') and record.get('gnd').strip():
        tmp.setdefault('gnd', record.get('gnd'))
        new_id = tmp.get('gnd')

    # creation and change date
    if not record.get('created'):
        record['created'] = timestamp()
        record['changed'] = record.get('created')
    else:
        if not storage_is_empty:
            record['changed'] = timestamp()

    parents = []
    children = []
    projects = []

    for field in record.keys():
        if field == 'same_as':
            for same_as in record.get(field):
                if same_as.strip():
                    tmp.setdefault('same_as', []).append(same_as.strip())
        elif field == 'pref_label':
            tmp.setdefault('pref_label', record.get(field).strip())
        elif field == 'also_known_as':
            for also_known_as in record.get(field):
                if also_known_as.strip():
                    tmp.setdefault('also_known_as', []).append(str(also_known_as).strip())
        elif field == 'created':
            tmp.setdefault('created', record.get(field).strip().replace(' ', 'T') + 'Z')
        elif field == 'changed':
            tmp.setdefault('changed', record.get(field).strip().replace(' ', 'T') + 'Z')
        elif field == 'deskman':
            if record.get(field).strip():
                tmp.setdefault('deskman', record.get(field).strip())
        elif field == 'owner':
            for owner in record.get(field):
                if owner.strip():
                    tmp.setdefault('owner', owner.strip())
        elif field == 'editorial_status':
            tmp.setdefault('editorial_status', record.get(field))
        elif field == 'catalog':
            for catalog in record.get(field):
                tmp.setdefault('catalog', catalog.strip())
        elif field == 'destatis':
            for destatis in record.get(field):
                if destatis.get('destatis_label'):
                    tmp.setdefault('destatis_label', []).append(destatis.get('destatis_label').strip())
                if destatis.get('destatis_id'):
                    tmp.setdefault('destatis_id', []).append(destatis.get('destatis_id').strip())

        if not storage_is_empty:
            if field == 'parent':
                # its a list with only one element (reason form object)
                parent = record.get(field)[0]
                # logger.info('parent: %s' % parent)
                if parent.get('parent_id'):
                    # remember ID for work on related entity
                    parents.append(parent.get('parent_id'))
                    # prepare index data and enrich form data
                    tmp.setdefault('parent_id', parent.get('parent_id'))

                    result = get_orga(parent.get('parent_id'))

                    # print('Treffer für %s: %s' % (parent.get('id'), result))
                    if result:
                        try:
                            myjson = json.loads(result.get('wtf_json'))
                            label = myjson.get('pref_label').strip()
                            tmp['parent_label'] = label
                            tmp['fparent'] = '%s#%s' % (myjson.get('id').strip(), label)
                            record['parent'][0]['parent_label'] = label
                        except TypeError:
                            logger.error(result)
                    else:
                        message.append('ID from relation "parent" could not be found! Ref: %s' % parent.get('parent_id'))
                elif parent.get('parent_label') and len(parent.get('parent_label')) > 0:
                    tmp.setdefault('fparent', parent.get('parent_label'))
                    tmp.setdefault('parent_label', parent.get('parent_label'))

            elif field == 'children':
                # logging.info('children in form of %s : %s' % (id, form.data.get(field)))
                for idx, child in enumerate(record.get(field)):
                    if child:
                        if 'child_id' in child and 'child_label' in child:
                            if child.get('child_id'):
                                # remember ID for work on related entity
                                children.append(child.get('child_id'))
                                # prepare index data and enrich form data
                                result = get_orga(child.get('child_id'))

                                if result:
                                    try:
                                        myjson = json.loads(result.get('wtf_json'))
                                        label = myjson.get('pref_label').strip()
                                        record['children'][idx]['child_label'] = label
                                        tmp.setdefault('children', []).append(
                                            json.dumps({'id': myjson.get('id').strip(),
                                                        'label': label,
                                                        'type': 'organisation'}))
                                        tmp.setdefault('fchildren', []).append(
                                            '%s#%s' % (myjson.get('id').strip(), label))
                                    except TypeError:
                                        logger.info(result)
                                else:
                                    result = get_group(child.get('child_id'))

                                    if result:
                                        try:
                                            myjson = json.loads(result.get('wtf_json'))
                                            label = myjson.get('pref_label').strip()
                                            record['children'][idx]['child_label'] = label
                                            tmp.setdefault('children', []).append(json.dumps({'id': myjson.get('id').strip(),
                                                                                              'label': label,
                                                                                              'type': 'group'}))
                                            tmp.setdefault('fchildren', []).append(
                                                '%s#%s' % (myjson.get('id').strip(), label))
                                        except TypeError:
                                            logger.info(result)
                                    else:
                                        message.append('ID from relation "child" could not be found! Ref: %s' % child.get(
                                                    'child_id'))
                            elif child.get('child_label'):
                                tmp.setdefault('children', []).append(json.dumps({'id': '',
                                                                                  'label': child.get('child_label').strip(),
                                                                                  'type': ''}))
                                tmp.setdefault('fchildren', []).append(child.get('child_label').strip())

            elif field == 'projects':
                # logging.info('projects in form of %s : %s' % (id, form.data.get(field)))
                for idx, project in enumerate(record.get(field)):
                    if project:
                        if 'project_id' in project and 'project_label' in project:
                            if project.get('project_id'):
                                # remember ID for work on related entity
                                projects.append(project.get('project_id'))
                                # prepare index data and enrich form data
                                result = get_group(project.get('project_id'))

                                if result:
                                    try:
                                        myjson = json.loads(result.get('wtf_json'))
                                        label = myjson.get('pref_label').strip()
                                        record['projects'][idx]['project_label'] = label
                                        tmp.setdefault('projects', []).append(json.dumps({'id': myjson.get('id').strip(),
                                                                                          'label': label}))
                                        tmp.setdefault('fprojects', []).append('%s#%s' % (myjson.get('id').strip(), label))
                                    except TypeError:
                                        logger.info(result)
                                else:
                                    message.append('IDs from relation "projects" could not be found! Ref: %s' % project.get('project_id'))
                            elif project.get('project_label'):
                                tmp.setdefault('fprojects', []).append(project.get('project_label').strip())

    # search existing children from index and possibly add them
    if not storage_is_empty:
        search_orga_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                application=secrets.SOLR_APP, core='organisation', rows=500000,
                                query='parent_id:%s' % record_id)
        search_orga_solr.request()
        if len(search_orga_solr.results) > 0:
            for result in search_orga_solr.results:
                exists = False
                for child in record.get('children'):
                    # logging.info('%s vs. %s' % (child.get('child_id'), result.get('id')))
                    if child.get('child_id').strip() == result.get('id'):
                        exists = True
                        break
                if not exists:
                    record['children'].append({'child_id': result.get('id'), 'child_label': result.get('pref_label')})

        if record.get('dwid'):
            for dwid in record.get('dwid'):
                if dwid:
                    search_orga_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                            application=secrets.SOLR_APP, core='organisation', rows=500000,
                                            query='parent_id:%s' % dwid)
                    search_orga_solr.request()
                    if len(search_orga_solr.results) > 0:
                        for result in search_orga_solr.results:
                            exists = False
                            for child in record.get('children'):
                                # logging.info('%s vs. %s' % (child.get('child_id'), result.get('id')))
                                if child.get('child_id') == result.get('id'):
                                    exists = True
                                    break
                            if not exists:
                                record['children'].append(
                                    {'child_id': result.get('id'), 'child_label': result.get('pref_label')})

        if record.get('same_as'):
            for same_as in record.get('same_as'):
                if same_as:
                    search_orga_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                            application=secrets.SOLR_APP, core='organisation', rows=500000,
                                            query='parent_id:%s' % same_as)
                    search_orga_solr.request()
                    if len(search_orga_solr.results) > 0:
                        for result in search_orga_solr.results:
                            exists = False
                            for child in record.get('children'):
                                # logging.info('%s vs. %s' % (child.get('child_id'), result.get('id')))
                                if child.get('child_id') == result.get('id'):
                                    exists = True
                                    break
                            if not exists:
                                record['children'].append({'child_id': result.get('id'), 'child_label': result.get('pref_label')})

    # set primary id
    gnd_to_change = ''
    if new_id != record.get('id'):
        get_request = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                           application=secrets.SOLR_APP, query='gnd:"%s"' % record.get('id'),
                           core='organisation', facet='false')
        get_request.request()
        if get_request.results and new_id == record.get('gnd'):
            # Änderung der GND-ID!
            gnd_to_change = record.get('id')
        else:
            record['same_as'].append_entry(record.get('id'))
            tmp.setdefault('same_as', []).append(record.get('id'))

        # delete record with current id
        try:
            delete_person_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                      application=secrets.SOLR_APP, core='organisation', del_id=record.get('id'))
            delete_person_solr.delete()
        except Exception as e:
            logging.error(e)
        record['id'] = new_id
    else:
        if not storage_is_empty and not record.get('gnd'):
            get_request = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                               application=secrets.SOLR_APP, query='gnd:"%s"' % record.get('id'),
                               core='organisation', facet='false')
            get_request.request()
            if get_request.results:
                # GND-ID gelöscht
                gnd_to_change = record.get('id')
                if record.get('dwid'):
                    for dwid in record.get('same_as'):
                        if dwid.strip():
                            record['id'] = dwid.strip()
                            break
                elif record.get('same_as'):
                    for same_as in record.get('same_as'):
                        if same_as.strip():
                            record['id'] = same_as.strip()
                            del record['same_as'][same_as.strip()]
                            break
                else:
                    record['id'] = str(uuid.uuid4())

                # delete record with current id
                try:
                    delete_person_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                              application=secrets.SOLR_APP, core='organisation', del_id=new_id)
                    delete_person_solr.delete()
                except Exception as e:
                    logging.error(e)

    # save record to index
    tmp.setdefault('id', record['id'])
    wtf_json = json.dumps(record)
    tmp.setdefault('wtf_json', wtf_json)
    # logging.info(tmp)
    orga_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                     application=secrets.SOLR_APP, core='organisation', data=[tmp])
    orga_solr.update()

    # TODO if GND-ID changed: for all works using the old GND-ID, change the GND-ID
    if gnd_to_change:
        logger.debug('build bulk update file and store in "bulk_update_watch_folder"')

    orgas_queue = None
    groups_queue = None
    persons_queue = None
    works_queue = None
    # add links to related entities
    if update_related_entities:

        if manage_queue:
            orgas_queue = parents

            groups_queue = projects

            if children:
                for child_id in children:
                    result = get_orga(child_id)
                    if result:
                        orgas_queue.append(child_id)
                    else:
                        result = get_group(child_id)
                        if result:
                            groups_queue.append(child_id)

            persons_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                application=secrets.SOLR_APP, core='person',
                                query='affiliation_id:%s' % record_id, facet=False, rows=500000)
            persons_solr.request()
            if persons_solr.results:
                persons_queue = []
                for person in persons_solr.results:
                    persons_queue.append(person.get('id'))

            works_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                              application=secrets.SOLR_APP, core='hb2',
                              query='affiliation_id:%s' % record_id, facet=False, rows=2000000)
            works_solr.request()

            if works_solr.results:
                works_queue = []
                for work in works_solr.results:
                    works_queue.append(work.get('id'))

        else:
            # logging.info('parents: %s' % parents)
            for parent_id in parents:
                # search record
                result = get_orga(parent_id)

                # load orga in form and modify changeDate
                if result:
                    # edit
                    try:
                        thedata = json.loads(result.get('wtf_json'))
                        form = OrgaAdminForm.from_json(thedata)
                        # add child to form if not exists
                        exists = False
                        for child in form.data.get('children'):
                            # logging.info('%s == %s ?' % (project.get('child_id'), id))
                            if child.get('child_id'):
                                if child.get('child_id') == id:
                                    exists = True
                                    break
                                elif child.get('child_id') in dwid:
                                    exists = True
                                    break
                                elif child.get('child_id') in same_as:
                                    exists = True
                                    break
                        if not exists:
                            childform = ChildForm()
                            childform.child_id.data = id
                            form.children.append_entry(childform.data)

                        # save record
                        try:
                            form.changed.data = timestamp()
                            orga2solr(form, action='update', relitems=False)
                        except AttributeError as e:
                            logging.error('linking from %s: %s' % (parent_id, str(e)))

                    except TypeError as e:
                        logging.error(e)
                        logging.error('thedata: %s' % result.get('wtf_json'))
                else:
                    logging.info('Currently there is no record for parent_id %s!' % parent_id)

            # logging.info('children: %s' % children)
            for child_id in children:
                # search record
                result = get_orga(child_id)

                # load orga in form and modify changeDate
                if result:
                    # edit
                    try:
                        thedata = json.loads(result.get('wtf_json'))
                        form = OrgaAdminForm.from_json(thedata)
                        # add parent to form if not exists
                        if not form.data.get('parent'):
                            parentform = ParentForm()
                            parentform.parent_id = id
                            form.parent.append_entry(parentform.data)
                        else:
                            form.parent[0].parent_id = id

                        # save record
                        try:
                            form.changed.data = timestamp()
                            orga2solr(form, update_related_entities=False)
                        except AttributeError as e:
                            logging.error('linking from %s: %s' % (child_id, str(e)))

                    except TypeError as e:
                        logging.error(e)
                        logging.error('thedata: %s' % result.get('wtf_json'))
                else:
                    result = get_group(child_id)

                    # load orga in form and modify changeDate
                    if result:
                        # edit
                        try:
                            thedata = json.loads(result.get('wtf_json'))
                            form = GroupAdminForm.from_json(thedata)
                            # add parent to form if not exists
                            if not form.data.get('parent'):
                                parentform = ParentForm()
                                parentform.parent_id = id
                                form.parent.append_entry(parentform.data)
                            else:
                                form.parent[0].parent_id = id

                            # save record
                            try:
                                form.changed.data = timestamp()
                                group2solr(form, action='update', relitems=False)
                            except AttributeError as e:
                                logging.error('linking from %s: %s' % (child_id, str(e)))

                        except TypeError as e:
                            logging.error(e)
                            logging.error('thedata: %s' % result.get('wtf_json'))
                    else:
                        logging.info('Currently there is no record for child_id %s!' % child_id)

            # logging.debug('partners: %s' % partners)
            for project_id in projects:
                # search record
                result = get_group(project_id)

                # load orga in form and modify changeDate
                if result:
                    # edit
                    try:
                        thedata = json.loads(result.get('wtf_json'))
                        form = GroupAdminForm.from_json(thedata)
                        # add project to form if not exists
                        exists = False
                        for partner in form.data.get('partners'):
                            # logging.info('%s == %s ?' % (project.get('project_id'), id))
                            if partner.get('partner_id'):
                                if partner.get('partner_id') == id:
                                    exists = True
                                    break
                                elif partner.get('partner_id') in same_as:
                                    exists = True
                                    break
                        # logging.debug('exists? %s' % exists)
                        if not exists:
                            partnerform = PartnerForm()
                            partnerform.partner_id.data = id
                            form.partners.append_entry(partnerform.data)

                        # save record
                        try:
                            form.changed.data = timestamp()
                            group2solr(form, action='update', relitems=False)
                        except AttributeError as e:
                            logging.error('ERROR linking from %s: %s' % (project_id, str(e)))

                    except TypeError as e:
                        logging.error(e)
                        logging.error('thedata: %s' % result.get('wtf_json'))
                else:
                    logging.info('Currently there is no record for project_id %s!' % project_id)

            # store work records again
            works_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                              application=secrets.SOLR_APP, core='hb2',
                              query='affiliation_id:%s' % id, facet=False, rows=500000)
            works_solr.request()

            for work in works_solr.results:
                # edit
                try:
                    thedata = json.loads(work.get('wtf_json'))
                    form = display_vocabularies.PUBTYPE2FORM.get(thedata.get('pubtype')).from_json(thedata)
                    form.changed.data = timestamp()
                    work2solr(record=form.data, update_related_entities=False)
                except TypeError as e:
                    logging.error(e)
                    logging.error('thedata: %s' % work.get('wtf_json'))

            # store person records again
            results = []
            persons_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                application=secrets.SOLR_APP, core='person',
                                query='affiliation_id:%s' % id, facet=False, rows=500000)
            persons_solr.request()
            if len(persons_solr.results) > 0:
                results.append(persons_solr.results)
            for entry in dwid:
                persons_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                    application=secrets.SOLR_APP, core='person',
                                    query='affiliation_id:%s' % entry, facet=False, rows=500000)
                persons_solr.request()
                if len(persons_solr.results) > 0:
                    results += persons_solr.results
            for entry in same_as:
                persons_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                    application=secrets.SOLR_APP, core='person',
                                    query='affiliation_id:%s' % entry, facet=False, rows=500000)
                persons_solr.request()
                if len(persons_solr.results) > 0:
                    results += persons_solr.results

            for person in results:
                # edit
                try:
                    thedata = json.loads(person.get('wtf_json'))
                    form = PersonAdminForm.from_json(thedata)
                    form.changed.data = timestamp()
                    person2solr(form, action='update')
                except TypeError as e:
                    logging.error(e)
                    logging.error('thedata: %s' % person.get('wtf_json'))
                except AttributeError as e:
                    logging.error(e)

    return record['id'], message, orgas_queue, groups_queue, persons_queue, works_queue


def group2solr(record=None, storage_is_empty=False, update_related_entities=True, manage_queue=False):

    if record is None:
        record = {}

    message = []
    tmp = {}

    record_id = record.get('id')
    new_id = record.get('id')
    if record.get('dwid') and record.get('dwid').strip():
        tmp.setdefault('dwid', record.get('dwid'))
        new_id = tmp.get('dwid')
    if record.get('gnd') and record.get('gnd').strip():
        tmp.setdefault('gnd', record.get('gnd'))
        new_id = tmp.get('gnd')

    # creation and change date
    if not record.get('created'):
        record['created'] = timestamp()
        record['changed'] = record.get('created')
    else:
        record['changed'] = timestamp()

    parents = []
    children = []
    partners = []

    for field in record.keys():
        if field == 'same_as':
            for same_as in record.get(field):
                if same_as.strip():
                    tmp.setdefault('same_as', []).append(same_as.strip())
        elif field == 'funds':
            for funder in record.get(field):
                if funder.get('organisation') and funder.get('organisation').strip():
                    tmp.setdefault('funder_id', []).append(funder.get('organisation_id').strip())
                    tmp.setdefault('funder', []).append(funder.get('organisation').strip())
                    tmp.setdefault('ffunder', []).append(funder.get('organisation').strip())
        elif field == 'pref_label':
            tmp.setdefault('pref_label', record.get(field).strip())
        elif field == 'also_known_as':
            for also_known_as in record.get(field):
                if also_known_as.strip():
                    tmp.setdefault('also_known_as', []).append(str(also_known_as).strip())
        elif field == 'created':
            tmp.setdefault('created', record.get(field).strip().replace(' ', 'T') + 'Z')
        elif field == 'changed':
            tmp.setdefault('changed', record.get(field).strip().replace(' ', 'T') + 'Z')
        elif field == 'deskman' and record.get(field):
            tmp.setdefault('deskman', record.get(field).strip())
        elif field == 'owner':
            for owner in record.get(field):
                if owner.strip():
                    tmp.setdefault('owner', owner.strip())
        elif field == 'editorial_status':
            tmp.setdefault('editorial_status', record.get(field))
        elif field == 'catalog':
            for catalog in record.get(field):
                tmp.setdefault('catalog', catalog.strip())
        elif field == 'destatis':
            for destatis in record.get(field):
                if destatis.get('destatis_label'):
                    tmp.setdefault('destatis_label', []).append(destatis.get('destatis_label').strip())
                if destatis.get('destatis_id'):
                    tmp.setdefault('destatis_id', []).append(destatis.get('destatis_id').strip())

        if not storage_is_empty:
            if field == 'parent':
                parent = record.get(field)[0]
                # logging.info('parent: %s' % parent)
                if parent.get('parent_id'):
                    # remember ID for work on related entity
                    parents.append(parent.get('parent_id'))
                    # prepare index data and enrich form data
                    tmp.setdefault('parent_id', parent.get('parent_id'))

                    result = get_group(parent.get('parent_id'))

                    if result:
                        myjson = json.loads(result.get('wtf_json'))
                        tmp.setdefault('parent_type', 'group')
                        tmp.setdefault('parent_label', myjson.get('pref_label'))
                        tmp.setdefault('fparent', '%s#%s' % (myjson.get('id'), myjson.get('pref_label')))
                        record['parent'][0]['parent_label'] = myjson.get('pref_label')
                    else:
                        result = get_orga(parent.get('parent_id'))

                        if result:
                            myjson = json.loads(result.get('wtf_json'))
                            tmp.setdefault('parent_type', 'organisation')
                            tmp.setdefault('parent_label', myjson.get('pref_label'))
                            tmp.setdefault('fparent', '%s#%s' % (myjson.get('id'), myjson.get('pref_label')))
                            record['parent'][0]['parent_label'] = myjson.get('pref_label')
                        else:
                            message.append(
                                'IDs from relation "parent" could not be found! Ref: %s' % parent.get('parent_id'))

                elif parent.get('parent_label'):
                    tmp.setdefault('fparent', parent.get('parent_label'))
                    tmp.setdefault('parent_label', parent.get('parent_label'))

            elif field == 'children':
                # logging.info('children in form of %s : %s' % (id, form.data.get(field)))
                for idx, child in enumerate(record.get(field)):
                    if child:
                        if 'child_id' in child and 'child_label' in child:
                            if child.get('child_id'):
                                # remember ID for work on related entity
                                children.append(child.get('child_id'))
                                # prepare index data and enrich form data

                                result = get_group(child.get('child_id'))

                                if result:
                                    myjson = json.loads(result.get('wtf_json'))
                                    label = myjson.get('pref_label').strip()
                                    record['children'][idx]['child_label'] = label
                                    tmp.setdefault('children', []).append(json.dumps({'id': myjson.get('id'),
                                                                                      'label': label}))
                                    tmp.setdefault('fchildren', []).append('%s#%s' % (myjson.get('id'), label))
                                else:
                                    message.append('IDs from relation "child" could not be found! Ref: %s' % child.get(
                                        'child_id'))

                            elif child.get('child_label'):
                                tmp.setdefault('children', []).append(child.get('child_label'))
                                tmp.setdefault('fchildren', []).append(child.get('child_label'))

            elif field == 'partners':
                # logging.info('partners in form of %s : %s' % (id, form.data.get(field)))
                for idx, partner in enumerate(record.get(field)):
                    if partner:
                        if 'partner_id' in partner and 'partner_label' in partner:
                            if partner.get('partner_id'):
                                # remember ID for work on related entity
                                partners.append(partner.get('partner_id'))
                                # prepare index data and enrich form data

                                result = get_orga(partner.get('partner_id'))

                                if result:
                                    myjson = json.loads(result.get('wtf_json'))
                                    label = myjson.get('pref_label').strip()
                                    record['partners'][idx]['partner_label'] = label
                                    tmp.setdefault('partners', []).append(json.dumps({'id': myjson.get('id'),
                                                                                      'label': label}))
                                    tmp.setdefault('fpartners', []).append('%s#%s' % (myjson.get('id'), label))
                                else:
                                    message.append('IDs from relation "partners" could not be found! Ref: %s' % partner.get(
                                        'partner_id'))

                            elif partner.get('partner_label'):
                                tmp.setdefault('partners', []).append(partner.get('partner_label'))
                                tmp.setdefault('fpartners', []).append(partner.get('partner_label'))

    # set primary id
    gnd_to_change = ''
    if new_id != record.get('id'):
        get_request = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                           application=secrets.SOLR_APP, query='gnd:"%s"' % record.get('id'),
                           core='group', facet='false')
        get_request.request()
        if get_request.results and new_id == record.get('gnd'):
            # Änderung der GND-ID!
            gnd_to_change = record.get('id')
        else:
            record['same_as'].append_entry(record.get('id'))
            tmp.setdefault('same_as', []).append(record.get('id'))

        # delete record with current id
        try:
            delete_person_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                      application=secrets.SOLR_APP, core='group', del_id=record.get('id'))
            delete_person_solr.delete()
        except Exception as e:
            logging.error(e)
        record['id'] = new_id
    else:
        if not storage_is_empty and not record.get('gnd'):
            get_request = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                               application=secrets.SOLR_APP, query='gnd:"%s"' % record.get('id'),
                               core='group', facet='false')
            get_request.request()
            if get_request.results:
                # GND-ID gelöscht
                gnd_to_change = record.get('id')
                if record.get('dwid'):
                    for dwid in record.get('same_as'):
                        if dwid.strip():
                            record['id'] = dwid.strip()
                            break
                elif record.get('same_as'):
                    for same_as in record.get('same_as'):
                        if same_as.strip():
                            record['id'] = same_as.strip()
                            del record['same_as'][same_as.strip()]
                            break
                else:
                    record['id'] = str(uuid.uuid4())

                # delete record with current id
                try:
                    delete_person_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                              application=secrets.SOLR_APP, core='group', del_id=new_id)
                    delete_person_solr.delete()
                except Exception as e:
                    logging.error(e)

    # save record to index
    tmp.setdefault('id', record['id'])
    wtf_json = json.dumps(record)
    tmp.setdefault('wtf_json', wtf_json)
    # logging.info(tmp)
    groups_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                       application=secrets.SOLR_APP, core='group', data=[tmp])
    groups_solr.update()

    # TODO if GND-ID changed: for all works using the old GND-ID, change the GND-ID
    if gnd_to_change:
        logger.debug('build bulk update file and store in "bulk_update_watch_folder"')

    # add links to related entities
    groups_queue = None
    orgas_queue = None
    persons_queue = None
    works_queue = None
    if update_related_entities:

        if manage_queue:
            orgas_queue = partners

            groups_queue = children

            if parents and parents[0]:
                result = get_group(parents[0])
                if result:
                    orgas_queue.append(parents[0])
                else:
                    result = get_group(parents[0])
                    if result:
                        groups_queue.append(parents[0])

            persons_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                application=secrets.SOLR_APP, core='person',
                                query='group_id:%s' % record_id, facet=False, rows=500000)
            persons_solr.request()
            if persons_solr.results:
                persons_queue = []
                for person in persons_solr.results:
                    persons_queue.append(person.get('id'))

            # TODO solr export with query!
            works_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                              application=secrets.SOLR_APP, core='hb2',
                              query='group_id:%s' % record_id, facet=False, rows=2000000)
            works_solr.request()

            if works_solr.results:
                works_queue = []
                for work in works_solr.results:
                    works_queue.append(work.get('id'))

        else:
            # logging.debug('parents: %s' % parents)
            for parent_id in parents:
                # search record
                result = get_orga(parent_id)

                # load orga in form and modify changeDate
                if result:
                    # logging.info('IS ORGA')
                    try:
                        thedata = json.loads(result.get('wtf_json'))
                        form = OrgaAdminForm.from_json(thedata)
                        # add child to form if not exists
                        exists = False
                        for child in form.data.get('children'):
                            if child.get('child_id'):
                                # logging.info('%s == %s ?' % (child.get('child_id'), id))
                                if child.get('child_id') == id:
                                    exists = True
                                    break
                                elif child.get('child_id') in same_as:
                                    exists = True
                                    break
                        if not exists:
                            childform = ChildForm()
                            childform.child_id.data = id
                            form.children.append_entry(childform.data)

                        # save record
                        try:
                            form.changed.data = timestamp()
                            orga2solr(form, action='update', relitems=False)
                        except AttributeError as e:
                            logging.error('linking from %s: %s' % (parent_id, str(e)))

                    except TypeError as e:
                        logging.error(e)
                        logging.error('thedata: %s' % result.get('wtf_json'))
                else:
                    result = get_group(parent_id)

                    # load group in form and modify changeDate
                    if result:
                        # logging.info('IS GROUP')
                        try:
                            thedata = json.loads(result.get('wtf_json'))
                            form = GroupAdminForm.from_json(thedata)
                            # add child to form if not exists
                            exists = False
                            for child in form.data.get('children'):
                                if child.get('child_id'):
                                    # logging.info('%s == %s ?' % (child.get('child_id'), id))
                                    if child.get('child_id') == id:
                                        exists = True
                                        break
                                    elif child.get('child_id') in same_as:
                                        exists = True
                                        break
                            if not exists:
                                childform = ChildForm()
                                childform.child_id.data = id
                                form.children.append_entry(childform.data)

                            # save record
                            # logging.info('children in form of %s : %s' % (parent_id, form.data.get('children')))
                            try:
                                form.changed.data = timestamp()
                                group2solr(form, action='update', relitems=False)
                            except AttributeError as e:
                                logging.error('linking from %s: %s' % (parent_id, str(e)))

                        except TypeError as e:
                            logging.error(e)
                            logging.error('thedata: %s' % result.get('wtf_json'))
                    else:
                        logging.info('Currently there is no record for parent_id %s!' % parent_id)

            # logging.debug('children: %s' % children)
            for child_id in children:
                # search record
                result = get_group(child_id)

                # load orga in form and modify changeDate
                if result:
                    try:
                        thedata = json.loads(result.get('wtf_json'))
                        form = GroupAdminForm.from_json(thedata)
                        # add parent to form if not exists
                        if not form.data.get('parent'):
                            parentform = ParentForm()
                            parentform.parent_id = id
                            form.parent.append_entry(parentform.data)
                        else:
                            form.parent[0].parent_id = id

                        # save record
                        try:
                            form.changed.data = timestamp()
                            group2solr(form, action='update', relitems=False)
                        except AttributeError as e:
                            logging.error('linking from %s: %s' % (parent_id, str(e)))
                    except TypeError as e:
                        logging.error(e)
                        logging.error('thedata: %s' % result.get('wtf_json'))
                else:
                    logging.info('Currently there is no record for child_id %s!' % child_id)

            # logging.debug('partners: %s' % partners)
            for partner_id in partners:
                # search record
                result = get_orga(partner_id)

                # load orga in form and modify changeDate
                if result:
                    try:
                        thedata = json.loads(result.get('wtf_json'))
                        form = OrgaAdminForm.from_json(thedata)
                        # add project to form if not exists
                        exists = False
                        for project in form.data.get('projects'):
                            # logging.info('%s == %s ?' % (project.get('project_id'), id))
                            if project.get('project_id'):
                                if project.get('project_id') == id:
                                    exists = True
                                    break
                                elif project.get('project_id') in same_as:
                                    exists = True
                                    break
                        # logging.debug('exists? %s' % exists)
                        if not exists:
                            projectmemberform = ProjectMemberForm()
                            projectmemberform.project_id.data = id
                            form.projects.append_entry(projectmemberform.data)
                        else:
                            form.changed.data = timestamp()

                        # save record
                        try:
                            form.changed.data = timestamp()
                            orga2solr(form, action='update', relitems=False)
                        except AttributeError as e:
                            logging.error('ERROR linking from %s: %s' % (partner_id, str(e)))

                    except TypeError as e:
                        logging.error(e)
                        logging.error('thedata: %s' % result.get('wtf_json'))
                else:
                    logging.info('Currently there is no record for partner_id %s!' % partner_id)

            # store work records again
            works_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                              application=secrets.SOLR_APP, core='hb2',
                              query='group_id:%s' % id, facet=False, rows=500000)
            works_solr.request()

            for work in works_solr.results:
                try:
                    thedata = json.loads(work.get('wtf_json'))
                    form = display_vocabularies.PUBTYPE2FORM.get(thedata.get('pubtype')).from_json(thedata)
                    form.changed.data = timestamp()
                    work2solr(record=form.data, update_related_entities=False)
                except TypeError as e:
                    logging.error(e)
                    logging.error('thedata: %s' % work.get('wtf_json'))

            # store person records again
            results = []
            persons_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                application=secrets.SOLR_APP, core='person',
                                query='group_id:%s' % id, facet=False, rows=500000)
            persons_solr.request()
            if len(persons_solr.results) > 0:
                results += persons_solr.results

            for entry in same_as:
                persons_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                    application=secrets.SOLR_APP, core='person',
                                    query='group_id:%s' % entry, facet=False, rows=500000)
                persons_solr.request()
                if len(persons_solr.results) > 0:
                    results += persons_solr.results

            for person in results:
                try:
                    thedata = json.loads(person.get('wtf_json'))
                    form = PersonAdminForm.from_json(thedata)
                    form.changed.data = timestamp()
                    person2solr(form, action='update')
                except TypeError as e:
                    logging.error(e)
                    logging.error('thedata: %s' % person.get('wtf_json'))
                except AttributeError as e:
                    logging.error(e)

    return record['id'], message, groups_queue, orgas_queue, persons_queue, works_queue
