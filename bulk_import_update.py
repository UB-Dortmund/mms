# The MIT License
#
#  Copyright 2017 UB Dortmund <api.ub@tu-dortmund.de>.
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
from multiprocessing import Pool
import persistence
import simplejson as json
import redis
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

start_total = timeit.default_timer()
# init queues
r = redis.StrictRedis(host=secrets.REDIS_QUEUE_HOST, port=secrets.REDIS_QUEUE_PORT,
                      db=secrets.REDIS_QUEUE_DB)

queue_id = str(uuid.uuid4())
works_queue_key = 'queue-works-%s' % queue_id
logger.info('init new works queue "%s"' % works_queue_key)
groups_queue_key = 'queue-groups-%s' % queue_id
logger.info('init new groups queue "%s"' % groups_queue_key)
organisations_queue_key = 'queue-orgas-%s' % queue_id
logger.info('init new orgas queue "%s"' % organisations_queue_key)
persons_queue_key = 'queue-persons-%s' % queue_id
logger.info('init new persons queue "%s"' % persons_queue_key)

del_cnt = 0


# >> HELPER <<
def _insert2queue(key='', items=None):
    if items is None:
        items = []

    del_cnt = 0
    queue = r.hkeys(works_queue_key)

    for item in items:
        if item.encode('utf-8') in queue:
            r.hdel(key, item)
            del_cnt += 1
        r.hset(key, item, cnt)

    return del_cnt


def _index_data(record):
    persistence.work2solr(record=record, storage_is_empty=False,
                          update_related_entities=False, manage_queue=False)

# >> PROCESS <<

# read bulk data
if secrets.BULK_DATA_FILE:
    with open(secrets.BULK_DATA_FILE) as data_file:
        records = json.load(data_file)
elif secrets.BULK_DATA_QUERY:
    works_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                      application=secrets.SOLR_APP, core='hb2', handler='query',
                      query=secrets.BULK_DATA_QUERY, facet=False, rows=500000)
    works_solr.request()

    records = []
    if works_solr.response:
        results = works_solr.results
        for result in results:
            records.append(json.loads(result.get('wtf_json')))
else:
    records = []
stop = timeit.default_timer()
read_duration = stop - start_total
logger.info('duration for reading the data: %s' % read_duration)

# process bulk data
summary_time = 0
time_to_manage_queue = 0
cnt = 0

start_primary_data = timeit.default_timer()
for record in records:
    cnt += 1
    start = timeit.default_timer()
    # *2solr()
    if secrets.BULK_DATA_ENTITY_TYPE == 'work':
        id, message, works_queue = persistence.work2solr(record=record, storage_is_empty=False,
                                                         update_related_entities=True, manage_queue=True)

        logger.debug('size tmp_queue = %s' % len(works_queue))
    elif secrets.BULK_DATA_ENTITY_TYPE == 'group':
        works_queue = []
        logger.debug('size tmp_queue = %s' % len(works_queue))
    elif secrets.BULK_DATA_ENTITY_TYPE == 'organisation':
        works_queue = []
        logger.debug('size tmp_queue = %s' % len(works_queue))
    elif secrets.BULK_DATA_ENTITY_TYPE == 'person':
        works_queue = []
        logger.debug('size tmp_queue = %s' % len(works_queue))
    else:
        works_queue = []

    start_manage_queue = timeit.default_timer()
    if works_queue:
        del_cnt += _insert2queue(works_queue_key, works_queue)
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

if r.exists(works_queue_key):
    # get queue
    logger.info('queue - items deleted: %s' % del_cnt)
    queue = r.hkeys(works_queue_key)
    queue_cnt = len(queue)
    logger.info('queue size: %s' % queue_cnt)
    # prepare items for pool
    records = []
    for item in queue:
        records.append(json.loads(persistence.get_work(work_id=item.decode('utf-8')).get('wtf_json')))
    # execute pool
    start = timeit.default_timer()
    pool = Pool(processes=secrets.WORKER)
    pool.map(_index_data, records)
    stop = timeit.default_timer()
    pool_duration = stop - start
    logger.info('duration for pool: %s' % pool_duration)

if r.exists(groups_queue_key):
    logger.info('queue - items deleted: %s' % del_cnt)
    queue = r.hkeys(works_queue_key)
    queue_cnt = len(queue)
    logger.info('queue size: %s' % queue_cnt)
    for item in queue:
        logger.debug('item: %s (%s)' % (item, r.hget(works_queue_key, item)))
        # work2solr with relitems=False
        record = json.loads(persistence.get_group(group_id=item.decode('utf-8')).get('wtf_json'))
        start = timeit.default_timer()
        persistence.group2solr(record=record, storage_is_empty=False,
                               update_related_entities=True, manage_queue=False)
        stop = timeit.default_timer()
        summary_time += stop - start

    r.delete(works_queue_key)

if r.exists(organisations_queue_key):
    logger.info('queue - items deleted: %s' % del_cnt)
    queue = r.hkeys(works_queue_key)
    queue_cnt = len(queue)
    logger.info('queue size: %s' % queue_cnt)
    for item in queue:
        logger.debug('item: %s (%s)' % (item, r.hget(works_queue_key, item)))
        # work2solr with relitems=False
        record = json.loads(persistence.get_orga(orga_id=item.decode('utf-8')).get('wtf_json'))
        start = timeit.default_timer()
        persistence.orga2solr(record=record, storage_is_empty=False,
                              update_related_entities=True, manage_queue=False)
        stop = timeit.default_timer()
        summary_time += stop - start

    r.delete(works_queue_key)

if r.exists(persons_queue_key):
    logger.info('queue - items deleted: %s' % del_cnt)
    queue = r.hkeys(works_queue_key)
    queue_cnt = len(queue)
    logger.info('queue size: %s' % queue_cnt)
    for item in queue:
        logger.debug('item: %s (%s)' % (item, r.hget(works_queue_key, item)))
        # work2solr with relitems=False
        record = json.loads(persistence.get_person(person_id=item.decode('utf-8')).get('wtf_json'))
        start = timeit.default_timer()
        persistence.person2solr(record=record, storage_is_empty=False,
                                update_related_entities=True, manage_queue=False)
        stop = timeit.default_timer()
        summary_time += stop - start

    r.delete(works_queue_key)

# report
logger.info('>>>>>>>>>> REPORT <<<<<<<<<<')
stop_total = timeit.default_timer()
duration = stop_total - start_total
logger.info('duration %s' % duration)

average_time = summary_time / (cnt + queue_cnt)
logger.info('average: %s' % average_time)
logger.info('time to manage queue: %s' % time_to_manage_queue)

