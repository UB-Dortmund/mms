# The MIT License
#
#  Copyright 2017 UB Dortmund <data.ub@tu-dortmund.de>.
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

import argparse
from jsonschema import validate
import logging
from logging.handlers import RotatingFileHandler
from multiprocessing import Pool
import persistence
import simplejson as json
import redis
import textwrap
import uuid

from utils.solr_handler import Solr

import timeit

try:
    import local_import_secrets as secrets
except ImportError:
    import import_secrets as secrets

# init logger
log_formatter = logging.Formatter("[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s")

logger = logging.getLogger("Rotating Import Log")
logger.setLevel(logging.INFO)

handler = RotatingFileHandler(secrets.LOGFILE, maxBytes=1000000, backupCount=1)
handler.setFormatter(log_formatter)

logger.addHandler(handler)


def _validate_data(thedata=None, entity_type='work'):

    if thedata is None:
        thedata = []

    if thedata:
        with open('init/json_schema/%s.schema.json' % entity_type) as data_file:
            schema = json.load(data_file)

        try:
            validate(thedata, schema)
            return True
        except:
            return False


def _read_data_from_file(file=''):
    with open(file) as data_file:
        return json.load(data_file)


def _read_data_from_index(core='', query='*:*'):
    if query != '*:*':
        works_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                          application=secrets.SOLR_APP, core=core, handler='query',
                          query=query, facet=False, rows=500000)
        works_solr.request()
        if works_solr.response:
            results = works_solr.results
        else:
            results = []

        records = []
        for result in results:
            try:
                records.append(json.loads(result.get('wtf_json')))
            except Exception:
                logger.error('read error %s' % result.get('id'))
    else:
        export_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                           application=secrets.SOLR_APP, export_field='wtf_json', core=core)
        results = export_solr.export()

        records = []
        for result in results:
            try:
                records.append(result)
            except Exception as e:
                logger.error(e)
                logger.error('read error %s' % result.get('id'))
                logger.error(result)

    return records


# TODO if you want to pre-process the data, you have to implement this function!
def _preprocess_data(records=None):

    if records is None:
        records = []

    return records


def _insert2queue(key='', items=None, cnt=0):
    if items is None:
        items = []

    del_cnt = 0
    # init queues
    r = redis.StrictRedis(host=secrets.REDIS_QUEUE_HOST, port=secrets.REDIS_QUEUE_PORT,
                          db=secrets.REDIS_QUEUE_DB)

    queue = r.hkeys(key)

    for item in items:
        if item.encode('utf-8') in queue:
            r.hdel(key, item)
            del_cnt += 1
        r.hset(key, item, cnt)

    return del_cnt


def _index_orga_data(record):
    persistence.orga2solr(record=record, storage_is_empty=False,
                          update_related_entities=False, manage_queue=False)


def _index_group_data(record):
    persistence.group2solr(record=record, storage_is_empty=False,
                           update_related_entities=False, manage_queue=False)


def _index_person_data(record):
    persistence.person2solr(record=record, storage_is_empty=False,
                            update_related_entities=False, manage_queue=False)


def _index_work_data(record):
    persistence.work2solr(record=record, storage_is_empty=False,
                          update_related_entities=False, manage_queue=False)


def _manage_bulk_upload(entity_type='work', records=None, storage_is_empty=False, update_related_entities=False, manage_queue=False):

    if records is None:
        records = []

    summary_time = 0
    time_to_manage_queue = 0
    cnt = 0

    del_works_cnt = 0
    del_orgas_cnt = 0
    del_groups_cnt = 0
    del_persons_cnt = 0

    queue_id = str(uuid.uuid4())
    works_queue_key = 'queue-works-%s' % queue_id
    logger.info('init new works queue "%s"' % works_queue_key)
    groups_queue_key = 'queue-groups-%s' % queue_id
    logger.info('init new groups queue "%s"' % groups_queue_key)
    organisations_queue_key = 'queue-orgas-%s' % queue_id
    logger.info('init new orgas queue "%s"' % organisations_queue_key)
    persons_queue_key = 'queue-persons-%s' % queue_id
    logger.info('init new persons queue "%s"' % persons_queue_key)

    start_total = timeit.default_timer()

    start_primary_data = timeit.default_timer()
    for record in records:
        cnt += 1
        start = timeit.default_timer()
        # *2solr()
        works_queue = []
        groups_queue = []
        orgas_queue = []
        persons_queue = []
        if entity_type == 'work':
            record_id, message, works_queue = persistence.work2solr(record=record, storage_is_empty=storage_is_empty,
                                                                    update_related_entities=update_related_entities,
                                                                    manage_queue=manage_queue)
            size = 0
            if works_queue:
                size = len(works_queue)
            logger.debug('size works_queue = %s' % size)
        elif entity_type == 'group':
            record_id, message, groups_queue, orgas_queue, persons_queue, works_queue = persistence.group2solr(
                record=record, storage_is_empty=storage_is_empty, update_related_entities=update_related_entities,
                manage_queue=manage_queue)
            size = 0
            if groups_queue:
                size = len(groups_queue)
            logger.debug('size groups_queue = %s' % size)
        elif entity_type == 'organisation':
            record_id, message, orgas_queue, groups_queue, persons_queue, works_queue = persistence.orga2solr(
                record=record, storage_is_empty=storage_is_empty, update_related_entities=update_related_entities,
                manage_queue=manage_queue)
            size = 0
            if orgas_queue:
                size = len(orgas_queue)
            logger.debug('size orgas_queue = %s' % size)
            size = 0
            if groups_queue:
                size = len(groups_queue)
            logger.debug('size groups_queue = %s' % size)
            size = 0
            if persons_queue:
                size = len(persons_queue)
            logger.debug('size persons_queue = %s' % size)
            size = 0
            if works_queue:
                size = len(works_queue)
            logger.debug('size works_queue = %s' % size)
        elif entity_type == 'person':
            record_id, message, works_queue = persistence.person2solr(record=record, storage_is_empty=storage_is_empty,
                                                                      update_related_entities=update_related_entities,
                                                                      manage_queue=manage_queue)
            size = 0
            if works_queue:
                size = len(works_queue)
            logger.debug('size works_queue = %s' % size)

        start_manage_queue = timeit.default_timer()
        if works_queue:
            del_works_cnt += _insert2queue(key=works_queue_key, items=works_queue, cnt=cnt)
        if groups_queue:
            del_groups_cnt += _insert2queue(key=groups_queue_key, items=groups_queue, cnt=cnt)
        if orgas_queue:
            del_orgas_cnt += _insert2queue(key=organisations_queue_key, items=orgas_queue, cnt=cnt)
        if persons_queue:
            del_persons_cnt += _insert2queue(key=persons_queue_key, items=persons_queue, cnt=cnt)
        stop_manage_queue = timeit.default_timer()
        manage_queue_duration = stop_manage_queue - start_manage_queue
        time_to_manage_queue += manage_queue_duration
        logger.debug('duration for manage queue: %s' % manage_queue_duration)

        stop = timeit.default_timer()
        summary_time += stop - start

        if cnt % 100 == 0:
            logger.info('>>>>>>>>>> %s / %s <<<<<<<<<<' % (cnt, len(records)))

    stop_primary_data = timeit.default_timer()
    primary_data_duration = stop_primary_data - start_primary_data

    logger.info('>>>>>>>>>> %s / %s <<<<<<<<<<' % (cnt, len(records)))
    logger.info('duration for storing primary data: %s' % primary_data_duration)
    average_time = summary_time / cnt
    logger.info('average: %s' % average_time)

    # process queue
    queue_cnt = 0
    r = redis.StrictRedis(host=secrets.REDIS_QUEUE_HOST, port=secrets.REDIS_QUEUE_PORT,
                          db=secrets.REDIS_QUEUE_DB)

    if r.exists(groups_queue_key):
        logger.info('groups queue - items de-duplicated: %s' % del_groups_cnt)
        queue = r.hkeys(groups_queue_key)
        queue_cnt = len(queue)
        logger.info('groups queue size: %s' % queue_cnt)
        # prepare items for pool
        records = []
        for item in queue:
            try:
                records.append(json.loads(persistence.get_group(group_id=item.decode('utf-8')).get('wtf_json')))
            except Exception:
                logger.error('group item not found: %s' % item)
        # execute pool
        start = timeit.default_timer()
        pool = Pool(processes=secrets.WORKER)
        pool.map(_index_group_data, records)
        stop = timeit.default_timer()
        pool_duration = stop - start
        logger.info('duration for groups pool: %s' % pool_duration)

        r.delete(groups_queue_key)

    if r.exists(organisations_queue_key):
        logger.info('orgas queue - items de-duplicated: %s' % del_orgas_cnt)
        queue = r.hkeys(organisations_queue_key)
        queue_cnt = len(queue)
        logger.info('orgas queue size: %s' % queue_cnt)
        # prepare items for pool
        records = []
        for item in queue:
            try:
                records.append(json.loads(persistence.get_orga(orga_id=item.decode('utf-8')).get('wtf_json')))
            except Exception:
                logger.error('orga item not found: %s' % item)
        # execute pool
        start = timeit.default_timer()
        pool = Pool(processes=secrets.WORKER)
        pool.map(_index_orga_data, records)
        stop = timeit.default_timer()
        pool_duration = stop - start
        logger.info('duration for orgas pool: %s' % pool_duration)

        r.delete(organisations_queue_key)

    if r.exists(persons_queue_key):
        logger.info('persons queue - items de-duplicated: %s' % del_persons_cnt)
        queue = r.hkeys(persons_queue_key)
        queue_cnt = len(queue)
        logger.info('persons queue size: %s' % queue_cnt)
        # prepare items for pool
        records = []
        for item in queue:
            try:
                records.append(json.loads(persistence.get_person(person_id=item.decode('utf-8')).get('wtf_json')))
            except Exception:
                logger.error('person item not found: %s' % item)
        # execute pool
        start = timeit.default_timer()
        pool = Pool(processes=secrets.WORKER)
        pool.map(_index_person_data, records)
        stop = timeit.default_timer()
        pool_duration = stop - start
        logger.info('duration for persons pool: %s' % pool_duration)

        r.delete(persons_queue_key)

    if r.exists(works_queue_key):
        # get queue
        logger.info('works queue - items de-duplicated: %s' % del_works_cnt)
        queue = r.hkeys(works_queue_key)
        queue_cnt = len(queue)
        logger.info('works queue size: %s' % queue_cnt)
        # prepare items for pool
        records = []
        for item in queue:
            try:
                records.append(json.loads(persistence.get_work(work_id=item.decode('utf-8')).get('wtf_json')))
            except Exception:
                logger.error('work item not found: %s' % item)
        # execute pool
        start = timeit.default_timer()
        pool = Pool(processes=secrets.WORKER)
        pool.map(_index_work_data, records)
        stop = timeit.default_timer()
        pool_duration = stop - start
        logger.info('duration for works pool: %s' % pool_duration)

        r.delete(works_queue_key)

    # report
    logger.info('>>>>>>>>>> REPORT <<<<<<<<<<')
    stop_total = timeit.default_timer()
    duration = stop_total - start_total
    logger.info('duration %s' % duration)

    average_time = summary_time / (cnt + queue_cnt)
    logger.info('average: %s' % average_time)
    logger.info('time to manage queue: %s' % time_to_manage_queue)


def restore_backup(entity_type='work', file=''):

    start = timeit.default_timer()
    records = _read_data_from_file(file=file)
    stop = timeit.default_timer()
    read_duration = stop - start
    logger.info('duration for reading the data: %s' % read_duration)

    if _validate_data(thedata=records, entity_type=entity_type):

        # first run
        _manage_bulk_upload(entity_type=entity_type, records=records, storage_is_empty=True, update_related_entities=False,
                            manage_queue=False)

        # second run
        _manage_bulk_upload(entity_type=entity_type, records=records, storage_is_empty=False, update_related_entities=False,
                            manage_queue=False)
    else:
        print('ERROR: The given data is invalid!')


def reindex_data_from_file(entity_type='work', file='', preprocessing=False, bears_related_entities=False):

    start = timeit.default_timer()
    records = _read_data_from_file(file=file)
    stop = timeit.default_timer()
    read_duration = stop - start
    logger.info('duration for reading the data: %s' % read_duration)

    if _validate_data(thedata=records, entity_type=entity_type):

        if preprocessing:
            # TODO if you want to pre-process the input data, you have to implement the _preprocess_data function for your case
            records = _preprocess_data(records=records)

            _manage_bulk_upload(entity_type=entity_type, records=records, storage_is_empty=False,
                                update_related_entities=bears_related_entities, manage_queue=bears_related_entities)
        else:
            _manage_bulk_upload(entity_type=entity_type, records=records, storage_is_empty=False,
                                update_related_entities=False, manage_queue=False)
    else:
        print('ERROR: The given data is invalid!')


def reindex_data_from_index(entity_type='work', query='*:*', preprocessing=False, bears_related_entities=False):

    # TODO this is necessary until the solr core 'hb2' is renamed to 'work'
    if entity_type == 'work':
        core = 'hb2'
    else:
        core = entity_type

    start = timeit.default_timer()
    records = _read_data_from_index(core=core, query=query)
    stop = timeit.default_timer()
    read_duration = stop - start
    logger.info('duration for reading the data: %s' % read_duration)

    if _validate_data(thedata=records, entity_type=entity_type):

        if preprocessing:
            # TODO if you want to pre-process the input data, you have to implement the _preprocess_data function for your case
            records = _preprocess_data(records=records)

            _manage_bulk_upload(entity_type=entity_type, records=records, storage_is_empty=False,
                                update_related_entities=bears_related_entities, manage_queue=bears_related_entities)
        else:
            _manage_bulk_upload(entity_type=entity_type, records=records, storage_is_empty=False,
                                update_related_entities=False, manage_queue=False)
    else:
        print('ERROR: The given data is invalid!')


# __main__
parser = argparse.ArgumentParser(description='This tool restores a backup or reindex a data set in the MMS.',
                                 formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=textwrap.dedent('''\
                                        Examples:
                                        - restore backup for works:
                                            bulk_import_update.py --entity_type work --restore True --backup_file works.json
                                        - reindex data for works from file:
                                            bulk_import_update.py --entity_type work --reindex True --data_file works.json
                                        - reindex preprocessed data for organisations from existing solr instance and the update bears the related entities:
                                            bulk_import_update.py --entity_type work --reindex True --data_query Knappschaftskrankenhaus --preprocess_data True --bears_related_entities True
                                        '''))
parser.add_argument('--entity_type', help='entity_type in backup file (one of work, person, organisation, group)',
                    type=str)
parser.add_argument('--restore', help='restore backup', default=False, type=bool)
parser.add_argument('--backup_file', help='backup file to restore', type=str)
parser.add_argument('--reindex', help='reindex data', default=False, type=bool)
parser.add_argument('--data_file', help='data file to reindex', type=str)
parser.add_argument('--data_query', help='query for data to reindex', type=str)
parser.add_argument('--preprocess_data',
                    help='pre-process data; you have to implement the _preprocess_data function in this code!',
                    type=bool)
parser.add_argument('--bears_related_entities',
                    help='if pre-processing bears the data of related entities, set to True!', type=bool)
args = parser.parse_args()
params = vars(args)

# restore
if params.get('restore') and (not params.get('backup_file') or not params.get('entity_type')):
    print('If you want to restore data to the system, you have to add the --backup_file and the --entity_type argument!')
elif params.get('restore') and params.get('backup_file') and params.get('entity_type'):
    restore_backup(entity_type=params.get('entity_type'), file=params.get('backup_file'))
# reindex
elif params.get('reindex') and (not params.get('data_file') or not params.get('data_query') or not params.get('entity_type')):
    print('If you want to reindex data to the system, you have to add the --data_file and the --entity_type argument!')
elif params.get('reindex') and params.get('entity_type') and (params.get('data_file') or params.get('data_query')):
    # from file
    if params.get('data_file'):
        reindex_data_from_file(entity_type=params.get('entity_type'), file=params.get('data_file'),
                               preprocessing=params.get('preprocess_data'),
                               bears_related_entities=params.get('bears_related_entities'))
    # from solr query
    elif params.get('data_query'):
        reindex_data_from_index(entity_type=params.get('entity_type'), query=params.get('data_query'),
                                preprocessing=params.get('preprocess_data'),
                                bears_related_entities=params.get('bears_related_entities'))
# print usage
else:
    print(params)
    parser.print_help()



