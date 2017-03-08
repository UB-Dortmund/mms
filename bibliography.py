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


from __future__ import (absolute_import, division, print_function, unicode_literals)

import logging
import re
from logging.handlers import RotatingFileHandler
from bs4 import BeautifulSoup

import requests
import simplejson as json
from collections import OrderedDict
from citeproc import Citation, CitationItem
from citeproc import CitationStylesStyle, CitationStylesBibliography
from citeproc import formatter
from citeproc.py2compat import *
from citeproc.source.json import CiteProcJSON
from flask import Flask, request, jsonify, url_for
from flask import make_response
from flask_babel import Babel, lazy_gettext
from flask_login import LoginManager
from flask_cors import CORS
from flask_humanize import Humanize
from flask_redis import Redis
from flask_swagger import swagger
from flask_wtf.csrf import CSRFProtect

from forms.forms import *
from processors import openurl_processor
from processors import wtf_csl
from utils import display_vocabularies
from utils import urlmarker
from utils.solr_handler import Solr

try:
    import local_bibliography_secrets as secrets
except ImportError:
    import bibliography_secrets as secrets


class ReverseProxied(object):
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        script_name = environ.get('HTTP_X_SCRIPT_NAME', '')
        if script_name:
            environ['SCRIPT_NAME'] = script_name
            path_info = environ['PATH_INFO']
            if path_info.startswith(script_name):
                environ['PATH_INFO'] = path_info[len(script_name):]

        scheme = environ.get('HTTP_X_SCHEME', '')
        if scheme:
            environ['wsgi.url_scheme'] = scheme
        return self.app(environ, start_response)


app = Flask(__name__)
CORS(app)

if secrets.DIFFERENT_PROXY_PATH:
    app.wsgi_app = ReverseProxied(app.wsgi_app)

app.debug = secrets.DEBUG
app.secret_key = secrets.DEBUG_KEY

app.config['DEBUG_TB_INTERCEPT_REDIRECTS '] = False

app.config['REDIS_PUBLIST_CACHE_URL'] = secrets.REDIS_PUBLIST_CACHE_URL
Redis(app, 'REDIS_PUBLIST_CACHE')

csrf = CSRFProtect(app)

log_formatter = logging.Formatter("[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s")
handler = RotatingFileHandler(secrets.LOGFILE, maxBytes=10000, backupCount=1)
handler.setLevel(logging.INFO)
handler.setFormatter(log_formatter)
app.logger.addHandler(handler)

log = logging.getLogger('werkzeug')
log.setLevel(logging.DEBUG)
log.addHandler(handler)

PUBTYPE_KEYS = {
    'articlejournal': 'ArticleJournal',
    'articlenewspaper': 'ArticleNewspaper',
    'audiobook': 'AudioBook',
    'audiovideodocument': 'AudioVideoDocument',
    'chapter': 'Chapter',
    'chapterinlegalcommentary': 'ChapterInLegalCommentary',
    'chapterinmonograph': 'ChapterInMonograph',
    'collection': 'Collection',
    'conference': 'Conference',
    'edition': 'Edition',
    'internetdocument': 'InternetDocument',
    'journal': 'Journal',
    'lecture': 'Lecture',
    'legalcommentary': 'LegalCommentary',
    'monograph': 'Monograph',
    'multivolumework': 'MultivolumeWork',
    'newspaper': 'Newspaper',
    'other': 'Other',
    'patent': 'Patent',
    'pressrelease': 'PressRelease',
    'radiotvprogram': 'RadioTVProgram',
    'report': 'Report',
    'researchdata': 'ResearchData',
    'series': 'Series',
    'software': 'Software',
    'specialissue': 'SpecialIssue',
    'standard': 'Standard',
    'thesis': 'Thesis',
}


# ---------- PUB LISTS ----------

@app.route('/<agent>/<agent_id>/bibliography/<style>', methods=['GET'])
@csrf.exempt
def bibliography(agent='', agent_id='', style='harvard1'):
    """
        Getting a bibliography

        swagger_from_file: bibliography_doc/bibliography.yml
    """
    format = request.args.get('format', 'html')

    filter_by_year = request.args.get('filter_by_year', '')
    filter_by_type = request.args.get('filter_by_type', '')
    exclude_by_type = request.args.get('exclude_by_type', '')
    filter_by_pr = request.args.get('filter_by_pr', False)
    filter_by_ger = request.args.get('filter_by_ger', False)
    filter_by_eng = request.args.get('filter_by_eng', False)
    filter_by_current_members = request.args.get('filter_by_current_members', False)
    filter_by_former_members = request.args.get('filter_by_former_members', False)
    group_by_year = request.args.get('group_by_year', False)
    # logging.info('group_by_year = %s' % group_by_year)
    group_by_type = request.args.get('group_by_type', False)
    group_by_type_year = request.args.get('group_by_type_year', False)
    pubsort = request.args.get('pubsort', '')
    toc = request.args.get('toc', False)
    locale = request.args.get('locale', '')
    # TODO start-creationdate, end-creationdate >> Szenario Raumplanung
    start_creationdate = request.args.get('start_creationdate', '')
    end_creationdate = request.args.get('end_creationdate', '')

    reasoning = request.args.get('reasoning', False)
    refresh = request.args.get('refresh', False)

    formats = ['html', 'txt']
    agent_types = {
        'person': 'person',
        'research_group': 'organisation',
        'chair': 'organisation',
        'organisation': 'organisation',
        'working_group': 'group',
        'project': 'group',
    }
    pubsorts = ['stm', 'anh']
    STM_SORT = ['ArticleJournal', 'Chapter', 'Monograph', 'Journal', 'Series', 'Conference', 'Collection',
                'MultivolumeWork', 'SpecialIssue', 'Patent', 'Standard', 'Thesis', 'InternetDocument', 'Report', 'Lecture', 'Sonstiges',
                'ArticleNewspaper', 'PressRelease', 'RadioTVProgram', 'AudioVideoDocument',
                'ResearchData', 'Other']
    STM_LIST = {
        'ArticleJournal': '',
        'Chapter': '',
        'Monograph': '',
        'Journal': '',
        'Series': '',
        'Conference': '',
        'Collection': '',
        'MultivolumeWork': '',
        'SpecialIssue': '',
        'Patent': '',
        'Standard': '',
        'Thesis': '',
        'InternetDocument': '',
        'Report': '',
        'Lecture': '',
        'ArticleNewspaper': '',
        'PressRelease': '',
        'RadioTVProgram': '',
        'AudioVideoDocument': '',
        'ResearchData': '',
        'Other': '',
    }
    ANH_SORT = ['Monograph', 'ArticleJournal', 'ChapterInLegalCommentary', 'Chapter', 'LegalCommentary', 'Collection',
                 'MultivolumeWork', 'Conference', 'Edition', 'SpecialIssue', 'Journal', 'Series', 'Newspaper', 'Thesis',
                'ArticleNewspaper',
                'Lecture', 'Report', 'InternetDocument', 'RadioTVProgram', 'AudioVideoDocument',
                'PressRelease', 'ResearchData', 'Other']
    ANH_LIST = {
        'Monograph': '',
        'ArticleJournal': '',
        'ChapterInLegalCommentary': '',
        'Chapter': '',
        'LegalCommentary': '',
        'Collection': '',
        'MultivolumeWork': '',
        'Conference': '',
        'Edition': '',
        'SpecialIssue': '',
        'Journal': '',
        'Series': '',
        'Newspaper': '',
        'Thesis': '',
        'ArticleNewspaper': '',
        'Lecture': '',
        'Report': '',
        'InternetDocument': '',
        'RadioTVProgram': '',
        'AudioVideoDocument': '',
        'PressRelease': '',
        'ResearchData': '',
        'Other': '',
    }

    if format not in formats:
        return make_response('Bad request: format!', 400)
    elif agent not in agent_types.keys():
        return make_response('Bad request: agent!', 400)
    elif pubsort and pubsort not in pubsorts:
        return make_response('Bad request: pubsort!', 400)

    key = request.full_path.replace('&refresh=true', '').replace('?refresh=true', '?')
    # logging.debug('KEY: %s' % key)
    response = ''
    if not refresh:
        # request in cache?
        try:

            storage_publists_cache = app.extensions['redis']['REDIS_PUBLIST_CACHE']

            if storage_publists_cache.exists(key):
                response = storage_publists_cache.get(key)

        except Exception as e:
            logging.info('REDIS ERROR: %s' % e)

    if response == '':

        group = False
        group_field = ''
        group_limit = 100000
        if str2bool(group_by_year):
            group = True
            group_field = 'fdate'
        elif str2bool(group_by_type):
            group = True
            group_field = 'pubtype'

        filterquery = []
        if str2bool(filter_by_eng):
            filterquery.append('language:eng')
        elif str2bool(filter_by_ger):
            filterquery.append('language:ger')
        elif str2bool(filter_by_pr):
            filterquery.append('peer_reviewed:true')

        if filter_by_type != '':
            entries = filter_by_type.split('|')
            filter_string = ''
            for entry in entries:
                filter_string += 'pubtype:%s' % PUBTYPE_KEYS.get(entry.lower()) + '+OR+'
            filterquery.append(filter_string[:-4])

        if filter_by_year != '':
            entries = filter_by_year.split('|')
            filter_string = ''
            for entry in entries:
                filter_string += 'fdate:%s' % entry + '+OR+'
            filterquery.append(filter_string[:-4])

        if exclude_by_type:
            entries = exclude_by_type.split('|')
            for entry in entries:
                filterquery.append('-pubtype:"%s"' % PUBTYPE_KEYS.get(entry.lower()))

        fquery = ''
        if start_creationdate and not end_creationdate:
            fquery = 'recordCreationDate:[%s TO *]' % (start_creationdate + 'T00:00:00Z')
        elif not start_creationdate and end_creationdate:
            fquery = 'recordCreationDate:[*+TO+%s]' % (end_creationdate + 'T00:00:00Z')
        elif start_creationdate and end_creationdate:
            fquery = 'recordCreationDate:[%s+TO+%s]' % (start_creationdate + 'T00:00:00Z', end_creationdate + 'T00:00:00Z')

        if fquery:
            filterquery.append(fquery)

        query = ''
        results = []
        if agent_types.get(agent) == 'person':

            # get facet value
            actor_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                              application=secrets.SOLR_APP, query='gnd:%s' % agent_id, export_field='wtf_json',
                              core=agent_types.get(agent))
            actor_solr.request()

            if len(actor_solr.results) == 0:
                return make_response('Not Found: Unknown Agent!', 404)
            else:
                name = actor_solr.results[0].get('name')

                query = 'pndid:%s' % agent_id
                # query = 'pnd:"%s%s%s"' % (agent_id, '%23', name)
                # logging.info('query=%s' % query)

        else:
            # get orga/group doc
            actor_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                              application=secrets.SOLR_APP, query='id:%s' % agent_id,
                              export_field='wtf_json',
                              core=agent_types.get(agent))
            actor_solr.request()

            if actor_solr.results:

                name = actor_solr.results[0].get('pref_label')
                # logging.debug('name = %s' % name)

                if reasoning:
                    # logging.debug('reasoning: %s' % reasoning)
                    orgas = {}
                    orgas.setdefault(agent_id, name)
                    # get all children
                    if actor_solr.results[0].get('children'):
                        children = actor_solr.results[0].get('children')
                        for child_json in children:
                            child = json.loads(child_json)
                            orgas.setdefault(child.get('id'), child.get('label'))
                    query = ''
                    idx_o = 0
                    id_type = agent_types.get(agent)
                    if id_type == 'organisation':
                        id_type = 'affiliation'

                    for orga_id in orgas.keys():

                        fquery = ['gnd:[\'\' TO *]']

                        if not agent_types.get(agent) == 'person':
                            if filter_by_former_members:
                                fquery.append('personal_status:emeritus+OR+personal_status:alumnus')
                            elif filter_by_current_members:
                                fquery.append('-personal_status:emeritus')
                                fquery.append('-personal_status:alumnus')

                        member_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                           application=secrets.SOLR_APP, query='%s_id:"%s"' % (id_type, orga_id),
                                           fquery=fquery, fields=['gnd', 'name'], rows=100000,
                                           core='person')
                        member_solr.request()

                        query_part = ''

                        if member_solr.results and len(member_solr.results) > 0:
                            idx_p = 0
                            for member in member_solr.results:
                                query_part += 'pnd:"%s%s%s"' % (member.get('gnd'), '%23', member.get('name'))
                                idx_p += 1
                                if idx_p < len(member_solr.results) and query_part != '':
                                    query_part += ' OR '

                            if query_part != '':
                                query += query_part

                        idx_o += 1
                        if idx_o < len(orgas) and query != '':
                            query += ' OR '

                    while query.endswith(' OR '):
                        query = query[:-4]

                    # logging.info('query=%s' % query)

                else:
                    logging.debug('reasoning: %s' % reasoning)
                    id_type = agent_types.get(agent)
                    if id_type == 'organisation':
                        id_type = 'affiliation'
                    query = '%s_id:%s' % (id_type, agent_id)
            else:
                return make_response('Not Found: Unknown Agent!', 404)

        biblist_id = str(uuid.uuid4())
        biblist = ''
        biblist_toc = ''
        biblist_coins = ''

        STM_TOC = {
            'ArticleJournal': '',
            'Chapter': '',
            'Monograph': '',
            'Journal': '',
            'Series': '',
            'Conference': '',
            'Collection': '',
            'MultivolumeWork': '',
            'SpecialIssue': '',
            'Patent': '',
            'Standard': '',
            'Thesis': '',
            'InternetDocument': '',
            'Report': '',
            'Lecture': '',
            'ArticleNewspaper': '',
            'PressRelease': '',
            'RadioTVProgram': '',
            'AudioVideoDocument': '',
            'ResearchData': '',
        }
        ANH_TOC = {
            'Monograph': '',
            'ArticleJournal': '',
            'ChapterInLegalCommentary': '',
            'Chapter': '',
            'LegalCommentary': '',
            'Collection': '',
            'MultivolumeWork': '',
            'Conference': '',
            'Edition': '',
            'SpecialIssue': '',
            'Journal': '',
            'Series': '',
            'Newspaper': '',
            'Thesis': '',
            'ArticleNewspaper': '',
            'Lecture': '',
            'Report': '',
            'InternetDocument': '',
            'RadioTVProgram': '',
            'AudioVideoDocument': '',
            'PressRelease': '',
            'ResearchData': '',
        }

        STM_COINS = {
            'ArticleJournal': '',
            'Chapter': '',
            'Monograph': '',
            'Journal': '',
            'Series': '',
            'Conference': '',
            'Collection': '',
            'MultivolumeWork': '',
            'SpecialIssue': '',
            'Patent': '',
            'Standard': '',
            'Thesis': '',
            'InternetDocument': '',
            'Report': '',
            'Lecture': '',
            'ArticleNewspaper': '',
            'PressRelease': '',
            'RadioTVProgram': '',
            'AudioVideoDocument': '',
            'ResearchData': '',
        }
        ANH_COINS = {
            'Monograph': '',
            'ArticleJournal': '',
            'ChapterInLegalCommentary': '',
            'Chapter': '',
            'LegalCommentary': '',
            'Collection': '',
            'MultivolumeWork': '',
            'Conference': '',
            'Edition': '',
            'SpecialIssue': '',
            'Journal': '',
            'Series': '',
            'Newspaper': '',
            'Thesis': '',
            'ArticleNewspaper': '',
            'Lecture': '',
            'Report': '',
            'InternetDocument': '',
            'RadioTVProgram': '',
            'AudioVideoDocument': '',
            'PressRelease': '',
            'ResearchData': '',
        }

        if group_by_type_year:

            facet_tree = ('pubtype', 'fdate')

            publist_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                application=secrets.SOLR_APP, handler='query',
                                query=query, fquery=filterquery,
                                fields=['wtf_json'], rows=0,
                                facet='true', facet_tree=facet_tree, facet_sort=False, facet_limit=-1,
                                sort='fdate asc', core='hb2')
            publist_solr.request()
            # logging.info('publist_solr.tree: %s' % json.dumps(publist_solr.tree, indent=4))

            list_cnt = 0
            for pubtype in publist_solr.tree.get('pubtype,fdate'):
                # logging.debug('pubtype = %s' % pubtype.get('value'))
                # logging.debug('pubtype = %s' % pubtype)
                year_list = ''
                year_coins = ''
                if pubtype.get('pivot'):
                    for year in pubtype.get('pivot')[::-1]:
                        # logging.debug('\t%s: %s' % (year.get('value'), year.get('count')))
                        filterquery = []
                        filterquery.append('fdate:%s' % year.get('value'))
                        filterquery.append('pubtype:%s' % pubtype.get('value'))
                        pivot_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                          application=secrets.SOLR_APP, handler='query',
                                          query=query, fields=['wtf_json'], rows=100000,
                                          fquery=filterquery, core='hb2')
                        pivot_solr.request()
                        results = pivot_solr.results
                        # logging.debug('PIVOT_PUB_LIST: %s' % results)

                        publist_docs = []
                        for result in results:
                            publist_docs.append(json.loads(result.get('wtf_json')))
                            if format == 'html':
                                year_coins += '<div class="coins"><span class="Z3988" title="%s"></span></div>' % openurl_processor.wtf_openurl(json.loads(result.get('wtf_json'))).replace('&', '&amp;')

                        if not group_by_type:
                            if format == 'html':
                                year_list += '<h5>%s</h5>' % year.get('value')
                            else:
                                year_list += '%s\n' % year.get('value')

                        year_list += citeproc_node(wtf_csl.wtf_csl(publist_docs), format, locale, style)
                else:
                    filterquery = []
                    filterquery.append('pubtype:%s' % pubtype.get('value'))
                    pivot_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                      application=secrets.SOLR_APP, handler='query',
                                      query=query, fields=['wtf_json'], rows=100000,
                                      fquery=filterquery, core='hb2')
                    pivot_solr.request()
                    results = pivot_solr.results
                    # logging.debug('PIVOT_PUB_LIST: %s' % results)

                    publist_docs = []
                    for result in results:
                        publist_docs.append(json.loads(result.get('wtf_json')))
                        if format == 'html':
                            year_coins += '<div class="coins"><span class="Z3988" title="%s"></span></div>' % openurl_processor.wtf_openurl(
                                json.loads(result.get('wtf_json'))).replace('&', '&amp;')

                    year_list += citeproc_node(wtf_csl.wtf_csl(publist_docs), format, locale, style)

                if locale.startswith('de'):
                    group_value = display_vocabularies.PUBTYPE_GER.get(pubtype.get('value'))
                else:
                    group_value = display_vocabularies.PUBTYPE_ENG.get(pubtype.get('value'))

                list_cnt += 1
                if format == 'html':
                    header = '<h4 id="%s_%s">%s</h4>' % (biblist_id, list_cnt, group_value)
                elif format == 'txt':
                    header = '%s\n' % group_value
                else:
                    header = ''
                footer = ''
                if toc and format == 'html':
                    back_string = 'Back to table of contents'
                    if locale.startswith('de'):
                        back_string = 'Zurück zum Inhaltsverzeichnis'
                    footer = '<div class="toc_return"><a href="#%s_citetoc">%s</a></div>' % (biblist_id, back_string)

                if pubsort == 'stm':
                    STM_LIST[pubtype.get('value')] = header + year_list + footer
                    if format == 'html':
                        STM_TOC[pubtype.get('value')] = '<li><a href="#%s_%s">%s</a></li>' % (biblist_id, list_cnt, group_value)
                        STM_COINS[pubtype.get('value')] = year_coins
                elif pubsort == 'anh':
                    ANH_LIST[pubtype.get('value')] = header + year_list + footer
                    if format == 'html':
                        ANH_TOC[pubtype.get('value')] = '<li><a href="#%s_%s">%s</a></li>' % (biblist_id, list_cnt, group_value)
                        ANH_COINS[pubtype.get('value')] = year_coins
                else:
                    biblist += header + year_list
                    if format == 'html':
                        biblist_toc += '<li><a href="#%s_%s">%s</a></li>' % (biblist_id, list_cnt, group_value)
                        biblist_coins += year_coins

            if pubsort == 'anh':
                # logging.debug(ANH_LIST)
                biblist = ''
                biblist_toc = ''
                for pubtype in ANH_SORT:
                    if ANH_LIST.get(pubtype):
                        biblist += ANH_LIST.get(pubtype)
                        if format == 'html':
                            biblist_toc += ANH_TOC.get(pubtype)
                            biblist_coins += ANH_COINS.get(pubtype)
            elif pubsort == 'stm':
                # logging.debug(STM_LIST)
                biblist = ''
                biblist_toc = ''
                for pubtype in STM_SORT:
                    if STM_LIST.get(pubtype):
                        biblist += STM_LIST.get(pubtype)
                        if format == 'html':
                            biblist_toc += STM_TOC.get(pubtype)
                            biblist_coins += STM_COINS.get(pubtype)

        else:

            publist_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                application=secrets.SOLR_APP, handler='query',
                                query=query, fields=['wtf_json'],
                                rows=100000, fquery=filterquery,
                                group=group, group_field=group_field, group_limit=group_limit,
                                sort='fdate desc',
                                core='hb2')
            publist_solr.request()
            results.extend(publist_solr.results)
            # print('publist_solr.results: %s' % results)

            publist_docs = []
            if group:
                biblist = ''
                list_cnt = 0
                for result in results:
                    # logging.debug('groupValue: %s' % result.get('groupValue'))
                    # logging.debug('numFound: %s' % result.get('doclist').get('numFound'))
                    # logging.debug('docs: %s' % result.get('doclist').get('docs'))

                    coins = ''
                    for doc in result.get('doclist').get('docs'):
                        publist_docs.append(json.loads(doc.get('wtf_json')))
                        if format == 'html':
                            coins += '<div class="coins"><span class="Z3988" title="%s"></span></div>' % openurl_processor.wtf_openurl(json.loads(doc.get('wtf_json'))).replace('&', '&amp;')

                    group_value = result.get('groupValue')
                    if str2bool(group_by_type):
                        if locale.startswith('de'):
                            group_value = display_vocabularies.PUBTYPE_GER.get(result.get('groupValue'))
                        else:
                            group_value = display_vocabularies.PUBTYPE_ENG.get(result.get('groupValue'))

                    list_cnt += 1
                    if format == 'html':
                        header = '<h4 id="%s_%s">%s</h4>' % (biblist_id, list_cnt, group_value)
                    elif format == 'txt':
                        header = '%s' % group_value
                    else:
                        header = ''
                    footer = ''
                    if toc and format == 'html':
                        back_string = 'Back to table of contents'
                        if locale.startswith('de'):
                            back_string = 'Zurück zum Inhaltsverzeichnis'
                        footer = '<div class="toc_return"><a href="#%s_citetoc">%s</a></div>' % (biblist_id, back_string)

                    if str2bool(group_by_type):
                        if pubsort == 'stm':
                            STM_LIST[result.get('groupValue')] = header + citeproc_node(wtf_csl.wtf_csl(publist_docs), format, locale, style) + footer
                            if format == 'html':
                                STM_TOC[result.get('groupValue')] = '<li><a href="#%s_%s">%s</a></li>' % (biblist_id, list_cnt, group_value)
                                STM_COINS[result.get('groupValue')] = coins
                        elif pubsort == 'anh':
                            ANH_LIST[result.get('groupValue')] = header + citeproc_node(wtf_csl.wtf_csl(publist_docs), format, locale, style) + footer
                            if format == 'html':
                                ANH_TOC[result.get('groupValue')] = '<li><a href="#%s_%s">%s</a></li>' % (biblist_id, list_cnt, group_value)
                                ANH_COINS[result.get('groupValue')] = coins
                        else:
                            biblist += header + citeproc_node(wtf_csl.wtf_csl(publist_docs), format, locale, style) + footer
                            if format == 'html':
                                biblist_toc += '<li><a href="#%s_%s">%s</a></li>' % (biblist_id, list_cnt, group_value)
                                biblist_coins += coins
                    elif str2bool(group_by_year):
                        biblist += header + citeproc_node(wtf_csl.wtf_csl(publist_docs), format, locale, style) + footer
                        if format == 'html':
                            biblist_toc += '<li><a href="#%s_%s">%s</a></li>' % (biblist_id, list_cnt, group_value)
                            biblist_coins += coins
                    else:
                        biblist += header + citeproc_node(wtf_csl.wtf_csl(publist_docs), format, locale, style) + footer

                    if str2bool(group_by_type) and pubsort == 'anh':
                        # logging.debug(ANH_LIST)
                        biblist = ''
                        biblist_toc = ''
                        for pubtype in ANH_SORT:
                            if ANH_LIST.get(pubtype):
                                biblist += ANH_LIST.get(pubtype)
                                if format == 'html':
                                    biblist_toc += ANH_TOC.get(pubtype)
                                    biblist_coins += ANH_COINS.get(pubtype)
                    elif str2bool(group_by_type) and pubsort == 'stm':
                        # logging.debug(STM_LIST)
                        biblist = ''
                        biblist_toc = ''
                        for pubtype in STM_SORT:
                            if STM_LIST.get(pubtype):
                                biblist += STM_LIST.get(pubtype)
                                if format == 'html':
                                    biblist_toc += STM_TOC.get(pubtype)
                                    biblist_coins += STM_COINS.get(pubtype)

                    publist_docs = []

            else:
                for result in results:
                    publist_docs.append(json.loads(result.get('wtf_json')))

                biblist = citeproc_node(wtf_csl.wtf_csl(publist_docs), format, locale, style)

        response = ''

        if toc and format == 'html':
            response += '<ul id="%s_citetoc">' % biblist_id + biblist_toc + '</ul>'

        response += biblist + biblist_coins

    if response:
        try:

            storage_publists_cache = app.extensions['redis']['REDIS_PUBLIST_CACHE']

            storage_publists_cache.set(key, response)
            storage_publists_cache.hset(agent_id, key, timestamp())

        except Exception as e:
            logging.error('REDIS: %s' % e)

    resp = make_response(response)
    if format == 'txt':
        resp.headers["Content-Type"] = "text/plain; charset=utf-8"
    else:
        resp.headers["Content-Type"] = "text/html; charset=utf-8"

    return resp


def citeproc_node(docs=None, format='html', locale='', style=''):

    locales_url = secrets.CITEPROC_LOCALES_FILE

    with open(locales_url) as data_file:
        locales = json.load(data_file)

    # load a CSL style (from the current directory)
    # logging.debug('LOCALE: %s' % locale)
    if locale not in locales.get('language-names').keys():
        locale = locales.get('primary-dialects').get(locale)
    # logging.debug('LOCALE: %s' % locale)

    citeproc_url = secrets.CITEPROC_SERVICE_URL % ('html', style, locale)

    items = OrderedDict()
    for item in docs:
        items.setdefault(item.get('id'), item)

    response = requests.post(citeproc_url, data=json.dumps({'items': items}),
                             headers={'Content-type': 'application/json'})

    bib = response.content.decode()
    if format == 'html':
        urls = re.findall(urlmarker.URL_REGEX, bib)
        logging.info(urls)

        for url in list(set(urls)):
            bib = bib.replace(url, '<a href="%s">%s</a>' % (url.replace('http://dx.doi.org/', 'https://doi.org/'), url.replace('http://dx.doi.org/', 'https://doi.org/')))

        dois = re.findall(urlmarker.DOI_REGEX, bib)
        # logging.info('DOIs: %s' % dois)

        for doi in list(set(dois)):
            if doi.endswith('.'):
                doi = doi[:-1]
            elif doi.endswith('.</div>'):
                doi = doi[:-7]
            bib = bib.replace(doi, '<a href="https://doi.org/%s">%s</a>' % (doi.replace('doi:', ''), doi))

        dois = re.findall(urlmarker.DOI_REGEX_1, bib)
        # logging.info('DOIs: %s' % dois)

        for doi in list(set(dois)):
            if doi.endswith('.'):
                doi = doi[:-1]
            elif doi.endswith('.</div>'):
                doi = doi[:-7]
            bib = bib.replace(doi, '<a href="https://doi.org/%s">%s</a>' % (doi.replace('DOI: ', ''), doi))

    if format != 'html':
        bib = BeautifulSoup(bib, "lxml").text
        bib = "\n".join([line for line in bib.split('\n') if line.strip().lstrip() != ''])

    return bib


def render_bibliography(docs=None, format='html', locale='', style='', commit_link=False, commit_system=''):

    if docs is None:
        docs = []

    publist = ''
    # logging.debug('csl-docs: %s' % docs)
    if len(docs) > 0:

        locales_url = secrets.CITEPROC_LOCALES_FILE

        with open(locales_url) as data_file:
            locales = json.load(data_file)

        bib_source = CiteProcJSON(docs)
        # load a CSL style (from the current directory)
        locale = '%s/csl-locales/locales-%s' % (secrets.CSL_DATA_DIR, locales.get('primary-dialects').get(locale))
        # logging.info('locale: %s' % locale)
        bib_style = CitationStylesStyle('%s/csl/%s' % (secrets.CSL_DATA_DIR, style),
                                        locale=locale,
                                        validate=False)
        # Create the citeproc-py bibliography, passing it the:
        # * CitationStylesStyle,
        # * BibliographySource (CiteProcJSON in this case), and
        # * a formatter (plain, html, or you can write a custom formatter)
        bibliography = CitationStylesBibliography(bib_style, bib_source, formatter.html)
        # get a list of the item ids and register them to the bibliography object

        def warn(citation_item):
            logging.warning(
                "WARNING: Reference with key '{}' not found in the bibliography.".format(citation_item.key)
            )

        for item in docs:
            citation = Citation([CitationItem(item.get('id'))])
            bibliography.register(citation)
            bibliography.cite(citation, warn)

        # And finally, the bibliography can be rendered.
        if format == 'html':
            publist += '<div class="csl-bib-body">'

        idx = 0
        for item in bibliography.bibliography():
            # TODO Formatierung
            # logging.info('CSL item: %s' % item)
            # logging.info('CSL item ID: %s' % docs[idx].get('id'))
            if format == 'html':
                publist += '<div class="csl-entry">'
                if commit_link:
                    publist += '<span class="glyphicon glyphicon-minus" aria-hidden="true"></span> '

            if format == 'html':
                urls = re.findall(urlmarker.URL_REGEX, str(item))
                # logging.info(urls)

                for url in urls:
                    item = item.replace(url, '<a href="%s">%s</a>' % (url, url))

            publist += str(item)

            if commit_link and commit_system:
                if commit_system == 'crossref':
                    publist += ' <span class="glyphicon glyphicon-transfer" aria-hidden="true"></span> <a href="%s?doi=%s">%s</a>' % (url_for("new_by_identifiers"), docs[idx].get('id'), lazy_gettext('Use this Record'))
                else:
                    publist += ' <span class="glyphicon glyphicon-transfer" aria-hidden="true"></span> <a href="%s?source=%s&id=%s">%s</a>' % (url_for("new_by_identifiers"), commit_system, docs[idx].get('id'), lazy_gettext('Use this Record'))

            if format == 'html':
                publist += '</div>'

            idx += 1

        if format == 'html':
            publist += '</div>'

    return publist


# ---------- REST ----------

@app.route("/spec")
def spec():
    swag = swagger(app, from_file_keyword='swagger_from_file')
    swag['info']['version'] = secrets.SWAGGER_API_VERSION
    swag['info']['title'] = secrets.SWAGGER_TITLE
    swag['info']['description'] = secrets.SWAGGER_DESCRIPTION
    swag['schemes'] = secrets.SWAGGER_SCHEMES
    swag['host'] = secrets.SWAGGER_HOST
    swag['basePath'] = secrets.SWAGGER_BASEPATH
    swag['tags'] = [
        {
            'name': 'monitoring',
            'description': 'Methods for monitoring the service'
        },
        {
            'name': 'groups',
            'description': 'Working groups/Projects operations'
        },
        {
            'name': 'organisations',
            'description': 'Organisation operations'
        },
        {
            'name': 'persons',
            'description': 'Persons operations'
        },
        {
            'name': 'works',
            'description': 'Works operations'
        },
    ]
    return jsonify(swag)


@app.route('/_ping')
@csrf.exempt
def _ping():
    """
        Ping the service

        swagger_from_file: bibliography_doc/_ping.yml
    """
    try:
        if 'failed' in json.dumps(dependencies_health(), indent=4):
            return make_response('One or more dependencies unavailable!', 500)
        else:
            return make_response('pong', 200)
    except Exception:
        return make_response('One or more dependencies unavailable!', 500)


@app.route('/_health')
@csrf.exempt
def _health():
    """
        Showing the health of the service an its dependencies

        swagger_from_file: bibliography_doc/_health.yml
    """
    health_json = {
        "name": "hb2_flask",
        "timestamp": timestamp(),
        "dependencies": dependencies_health()
    }

    json_string = json.dumps(health_json, indent=4)
    status = 200

    if 'failed' in json_string:
        status = 500

    response = make_response(json_string, status)
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Content-type'] = 'application/json'

    return response


def dependencies_health():

    dependencies = []

    # health of Solr cores
    try:
        status = requests.get(
            'http://%s:%s/%s/hb2/admin/ping?wt=json' % (secrets.SOLR_HOST, secrets.SOLR_PORT, secrets.SOLR_APP),
            headers={'Accept': 'application/json'}).json().get('status').lower()
    except requests.exceptions.ConnectionError:
        status = 'failed'

    dependencies.append({
        'service': 'Solr Core "hb2"',
        'status': status,
        'description': 'Storage for bibliographic data',
        'external': False
    })

    try:
        status = requests.get(
            'http://%s:%s/%s/hb2_users/admin/ping?wt=json' % (secrets.SOLR_HOST, secrets.SOLR_PORT, secrets.SOLR_APP),
            headers={'Accept': 'application/json'}).json().get('status').lower()
    except requests.exceptions.ConnectionError:
        status = 'failed'

    dependencies.append({
        'service': 'Solr Core "hb2_users"',
        'status': status,
        'description': 'Storage for registered users',
        'external': False
    })

    try:
        status = requests.get(
            'http://%s:%s/%s/group/admin/ping?wt=json' % (secrets.SOLR_HOST, secrets.SOLR_PORT, secrets.SOLR_APP),
            headers={'Accept': 'application/json'}).json().get('status').lower()
    except requests.exceptions.ConnectionError:
        status = 'failed'

    dependencies.append({
        'service': 'Solr Core "group',
        'status': status,
        'description': 'Storage for working groups or projects data',
        'external': False
    })

    try:
        status = requests.get(
            'http://%s:%s/%s/organisation/admin/ping?wt=json' % (secrets.SOLR_HOST, secrets.SOLR_PORT, secrets.SOLR_APP),
            headers={'Accept': 'application/json'}).json().get('status').lower()
    except requests.exceptions.ConnectionError:
        status = 'failed'

    dependencies.append({
        'service': 'Solr Core "organisation',
        'status': status,
        'description': 'Storage for organisations data',
        'external': False
    })

    try:
        status = requests.get(
            'http://%s:%s/%s/person/admin/ping?wt=json' % (secrets.SOLR_HOST, secrets.SOLR_PORT, secrets.SOLR_APP),
            headers={'Accept': 'application/json'}).json().get('status').lower()
    except requests.exceptions.ConnectionError:
        status = 'failed'

    dependencies.append({
        'service': 'Solr Core "person',
        'status': status,
        'description': 'Storage for persons data',
        'external': False
    })

    # health of Redis
    try:
        storage = app.extensions['redis']['REDIS_PUBLIST_CACHE']
        status = storage.dbsize()
    except:
        status = 0

    if status:
        dependencies.append({
            'service': 'Redis "PUBLIST_CACHE"',
            'status': 'ok',
            'description': 'Cache for user defined citation lists',
            'external': False
        })
    else:
        dependencies.append({
            'service': 'Redis "PUBLIST_CACHE"',
            'status': 'failed',
            'description': 'Cache for user defined citation lists',
            'external': False
        })

    return dependencies


# ---------- MAIN ----------

def str2bool(v):
    if str(v).lower() in ("yes", "true",  "True", "t", "1"):
        return True
    else:
        return False


def theme(ip):
    # logging.info('IPs: %s' % len(ip))
    # logging.info('IPs: %s' % ip)
    site = 'dortmund'
    try:
        idx = len(ip)-2
    except Exception:
        idx = ip[0]

    if ip[idx].startswith('134.147'):
        site = 'bochum'
    elif ip[idx].startswith('129.217'):
        site = 'dortmund'

    return site


def cleanhtml(raw_html):
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, '', raw_html)
    return cleantext


if __name__ == '__main__':
    app.run(port=secrets.APP_PORT)
