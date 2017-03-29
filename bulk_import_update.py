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
import persistence
import simplejson as json
import redis
import uuid

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
# TODO init queue
r = redis.StrictRedis(host=secrets.REDIS_QUEUE_HOST, port=secrets.REDIS_QUEUE_PORT,
                      db=secrets.REDIS_QUEUE_DB)
key = 'queue-%s' % str(uuid.uuid4())
logger.info('init new queue "%s"' % key)

# read bulk data
with open(secrets.BULK_DATA_FILE) as data_file:
    records = json.load(data_file)

# process bulk data
summary_time = 0
cnt = 0

for record in records:
    start = timeit.default_timer()
    # TODO record2solr()
    stop = timeit.default_timer()
    summary_time += stop - start
    cnt += 1

    if cnt % 100 == 0:
        logger.info('>>>>>>>>>> %s / %s <<<<<<<<<<' % (cnt, len(records)))

logger.info('>>>>>>>>>> %s / %s <<<<<<<<<<' % (cnt, len(records)))

# TODO process queue

# report
logger.info('>>>>>>>>>> REPORT <<<<<<<<<<')
stop_total = timeit.default_timer()
duration = stop_total - start_total
logger.info('duration %s' % duration)

average_time = summary_time / cnt
logger.info('average: %s' % average_time)

