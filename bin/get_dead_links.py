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


def export_solr_dump():
    dow = days_of_week[datetime.datetime.today().weekday()]
    filename = '%s/%s/%s_%s.dead_ends.json' % (secrets.BACKUP_DIR, dow,
                                                  datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"), 'hb2')

    export_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                       application=secrets.SOLR_APP, query='is_part_of:[\'\' TO *]',
                       export_field='wtf_json', core='hb2')
    export_docs = export_solr.export()

    # TODO get id of the host and check if it exists
    dead_ends = []
    for doc in export_docs:
        for part in doc.get('is_part_of'):
            try:
                query = 'id:%s' % part.get('is_part_of')
                get_record_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                       application=secrets.SOLR_APP, core='hb2', query=query, facet='false',
                                       fields=['wtf_json'])
                get_record_solr.request()
                if len(get_record_solr.results) == 0:
                    print('%s is a dead end' % part.get('is_part_of'))
                    if part.get('is_part_of') not in dead_ends:
                        dead_ends.append(part.get('is_part_of'))
            except AttributeError as e:
                print(e)

    fo = open(filename, 'w')
    fo.write(json.dumps(dead_ends, indent=4))
    fo.close()

export_solr_dump()
