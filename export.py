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
    import local_p_secrets as secrets
except ImportError:
    import p_secrets as secrets

days_of_week = ['Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag', 'Sonntag']


def export_solr_query(core='', query='*:*', filename=''):
    if core != 'hb2_users':
        if filename != '':
            dow = days_of_week[datetime.datetime.today().weekday()]
            filename = '%s/%s/%s_%s.%s' % (secrets.BACKUP_DIR, dow,
                                           datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"), core, filename)

            export_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                               application=secrets.SOLR_APP, query=query, export_field='wtf_json',
                               core=core)
            export_docs = export_solr.export()

            fo = open(filename, 'w')
            fo.write(json.dumps(export_docs, indent=4))
            fo.close()

# export_solr_query('hb2', 'pubtype:Patent', 'pubtype_Patent.json')
export_solr_query('hb2', '-date:["" TO *]', 'not_issued.json')

