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

import simplejson as json

from utils.solr_handler import Solr

try:
    import app_secrets
    import local_app_secrets as secrets
except ImportError:
    import app_secrets

days_of_week = ['Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag', 'Sonntag']


def export_solr_dump(core=''):
    """
    Export the wtf_json field of every doc in the index to a new document in the users core and to the user's local file
    system. Uses the current user's ID and a timestamp as the document ID and file name.
    :param core:
    """
    dow = days_of_week[datetime.datetime.today().weekday()]
    if core != 'hb2_users':
        filename = '%s/%s/%s_%s.json' % (secrets.BACKUP_DIR, dow, datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"),
                                         core)
        export_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                           application=secrets.SOLR_APP, export_field='wtf_json', core=core)
        export_docs = export_solr.export()

        fo = open(filename, 'w')
        fo.write(json.dumps(export_docs, indent=4))
        fo.close()

        filename = '%s/%s/%s_%s.not_imported.json' % (secrets.BACKUP_DIR, dow,
                                                      datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"), core)

        export_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                           application=secrets.SOLR_APP, query='-editorial_status:imported', export_field='wtf_json',
                           core=core)
        export_docs = export_solr.export()

        fo = open(filename, 'w')
        fo.write(json.dumps(export_docs, indent=4))
        fo.close()

    else:
        filename = '%s/%s/%s_%s.json' % (secrets.BACKUP_DIR, dow, datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"),
                                         core)
        export_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                           application=secrets.SOLR_APP, core=core)
        export_docs = export_solr.export()

        fo = open(filename, 'w')
        fo.write(json.dumps(export_docs, indent=4))
        fo.close()

export_solr_dump('hb2_users')
export_solr_dump('hb2')
export_solr_dump('group')
export_solr_dump('organisation')
export_solr_dump('person')
export_solr_dump('serial')
