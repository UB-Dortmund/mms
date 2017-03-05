import logging
from logging.handlers import RotatingFileHandler

import datetime
import requests
import simplejson as json

from utils.solr_handler import Solr

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


# cleanup('hb2_users')

file = '../../../Downloads/2017-02-07_15-05-56_hb2_users.json'

with open(file) as data_file:
    import_json = json.load(data_file)

for record in import_json:

    # TODO preprocessing
    # - add lastlogin timestamp
    record['lastlogin'] = timestamp().strip().replace(' ', 'T') + 'Z'
    # - remove _version
    del record['_version_']

    # print(json.dumps(record, indent=4))

    new_user_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                         application=secrets.SOLR_APP, core='hb2_users', data=[record], facet='false')
    new_user_solr.update()
