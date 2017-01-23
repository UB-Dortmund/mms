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

handler = RotatingFileHandler(secrets.LOGFILE, maxBytes=10000, backupCount=1)
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

            # TODO request 'same_as'
            return None
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


def record2solr(form, action, relitems=True):

    message = []

    solr_data = {}
    has_part = []
    is_part_of = []
    other_version = []
    id = ''
    is_rubi = False
    is_tudo = False

    # logging.info('FORM: %s' % form.data)

    if form.data.get('id'):
        solr_data.setdefault('id', form.data.get('id').strip())
        id = form.data.get('id').strip()

    for field in form.data:
        # logging.info('%s => %s' % (field, form.data.get(field)))
        # record information
        if field == 'same_as':
            for same_as in form.data.get(field):
                if len(same_as.strip()) > 0:
                    solr_data.setdefault('same_as', []).append(same_as.strip())
        if field == 'created':
            if len(form.data.get(field).strip()) == 10:
                solr_data.setdefault('recordCreationDate', '%sT00:00:00.001Z' % form.data.get(field).strip())
            else:
                solr_data.setdefault('recordCreationDate', form.data.get(field).strip().replace(' ', 'T') + 'Z')
        if field == 'changed':
            if len(form.data.get(field).strip()) == 10:
                solr_data.setdefault('recordChangeDate', '%sT00:00:00.001Z' % form.data.get(field).strip())
            else:
                solr_data.setdefault('recordChangeDate', form.data.get(field).strip().replace(' ', 'T') + 'Z')
        if field == 'owner':
            for owner in form.data.get(field):
                solr_data.setdefault('owner', []).append(owner.strip())
        if field == 'catalog':
            for catalog in form.data.get(field):
                solr_data.setdefault('catalog', []).append(catalog.strip())
        if field == 'deskman' and form.data.get(field):
            solr_data.setdefault('deskman', form.data.get(field).strip())
        if field == 'editorial_status':
            solr_data.setdefault('editorial_status', form.data.get(field).strip())
        if field == 'apparent_dup':
            solr_data.setdefault('apparent_dup', form.data.get(field))

        if field == 'affiliation_context':
            for context in form.data.get(field):
                # logging.info(context)
                if len(context) > 0:
                    try:
                        query = 'id:%s' % context

                        parent_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                           application=secrets.SOLR_APP, core='organisation', query=query,
                                           facet='false', fields=['wtf_json'])
                        parent_solr.request()

                        if len(parent_solr.results) == 0:

                            query = 'account:%s' % context

                            parent_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                               application=secrets.SOLR_APP, core='organisation', query=query,
                                               facet='false', fields=['wtf_json'])
                            parent_solr.request()

                            if len(parent_solr.results) == 0:

                                query = 'same_as:%s' % context

                                parent_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                                   application=secrets.SOLR_APP, core='organisation', query=query,
                                                   facet='false', fields=['wtf_json'])
                                parent_solr.request()

                                if len(parent_solr.results) == 0:
                                    solr_data.setdefault('fakultaet', []).append(context)
                                    message.append('IDs from relation "affiliation" could not be found! Ref: %s' % context)
                                else:
                                    for doc in parent_solr.results:
                                        myjson = json.loads(doc.get('wtf_json'))
                                        solr_data.setdefault('fakultaet', []).append(
                                            '%s#%s' % (myjson.get('id'), myjson.get('pref_label')))
                                        solr_data.setdefault('affiliation_id', []).append(myjson.get('id'))
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
                                for doc in parent_solr.results:
                                    myjson = json.loads(doc.get('wtf_json'))
                                    solr_data.setdefault('fakultaet', []).append(
                                        '%s#%s' % (myjson.get('id'), myjson.get('pref_label')))
                                    solr_data.setdefault('affiliation_id', []).append(myjson.get('id'))
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
                            for doc in parent_solr.results:
                                myjson = json.loads(doc.get('wtf_json'))
                                solr_data.setdefault('fakultaet', []).append('%s#%s' % (myjson.get('id'), myjson.get('pref_label')))
                                solr_data.setdefault('affiliation_id', []).append(myjson.get('id'))
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

                    except AttributeError as e:
                        logging.error(e)

        if field == 'group_context':
            for context in form.data.get(field):
                # logging.info(context)
                if len(context) > 0:
                    try:
                        query = 'id:%s' % context
                        parent_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                           application=secrets.SOLR_APP, core='group', query=query, facet='false',
                                           fields=['wtf_json'])
                        parent_solr.request()

                        if len(parent_solr.results) == 0:
                            query = 'same_as:%s' % context
                            parent_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                               application=secrets.SOLR_APP, core='group', query=query, facet='false',
                                               fields=['wtf_json'])
                            parent_solr.request()

                            if len(parent_solr.results) == 0:
                                solr_data.setdefault('group', []).append(context)
                                message.append('IDs from relation "group" could not be found! Ref: %s' % context)
                            else:
                                for doc in parent_solr.results:
                                    myjson = json.loads(doc.get('wtf_json'))
                                    solr_data.setdefault('group_id', []).append(myjson.get('id'))
                                    solr_data.setdefault('group', []).append(
                                        '%s#%s' % (myjson.get('id'), myjson.get('pref_label')))
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
                            for doc in parent_solr.results:
                                myjson = json.loads(doc.get('wtf_json'))
                                solr_data.setdefault('group_id', []).append(myjson.get('id'))
                                solr_data.setdefault('group', []).append('%s#%s' % (myjson.get('id'), myjson.get('pref_label')))
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
                    except AttributeError as e:
                        logging.error(e)

        if field == 'locked':
            solr_data.setdefault('locked', form.data.get(field))

        # the work
        if field == 'publication_status':
            solr_data.setdefault('publication_status', form.data.get(field).strip())
        if field == 'pubtype':
            solr_data.setdefault('pubtype', form.data.get(field).strip())
        if field == 'subtype':
            solr_data.setdefault('subtype', form.data.get(field).strip())
        if field == 'title':
            solr_data.setdefault('title', form.data.get(field).strip())
            solr_data.setdefault('exacttitle', form.data.get(field).strip())
            solr_data.setdefault('sorttitle', form.data.get(field).strip())
        if field == 'subtitle':
            solr_data.setdefault('subtitle', form.data.get(field).strip())
            solr_data.setdefault('other_title', form.data.get(field).strip())
        if field == 'title_supplement':
            solr_data.setdefault('other_title', form.data.get(field).strip())
        if field == 'other_title':
            for other_tit in form.data.get(field):
                # logging.info(other_tit)
                if other_tit.get('other_title'):
                    solr_data.setdefault('parallel_title', other_tit.get('other_title').strip())
                    solr_data.setdefault('other_title', other_tit.get('other_title').strip())
        if field == 'issued':
            if form.data.get(field):
                solr_data.setdefault('date', form.data.get(field).replace('[', '').replace(']', '').strip())
                solr_data.setdefault('fdate', form.data.get(field).replace('[', '').replace(']', '')[0:4].strip())
                if len(form.data.get(field).replace('[', '').replace(']', '').strip()) == 4:
                    solr_data.setdefault('date_boost',
                                         '%s-01-01T00:00:00Z' % form.data.get(field).replace('[', '').replace(']',
                                                                                                              '').strip())
                elif len(form.data.get(field).replace('[', '').replace(']', '').strip()) == 7:
                    solr_data.setdefault('date_boost',
                                         '%s-01T00:00:00Z' % form.data.get(field).replace('[', '').replace(']',
                                                                                                           '').strip())
                else:
                    solr_data.setdefault('date_boost',
                                         '%sT00:00:00Z' % form.data.get(field).replace('[', '').replace(']',
                                                                                                        '').strip())
        if field == 'application_date':
            if form.data.get(field):
                solr_data.setdefault('date', form.data.get(field).replace('[', '').replace(']', '').strip())
                solr_data.setdefault('fdate', form.data.get(field).replace('[', '').replace(']', '')[0:4].strip())
                if len(form.data.get(field).replace('[', '').replace(']', '').strip()) == 4:
                    solr_data.setdefault('date_boost',
                                         '%s-01-01T00:00:00Z' % form.data.get(field).replace('[', '').replace(']',
                                                                                                              '').strip())
                elif len(form.data.get(field).replace('[', '').replace(']', '').strip()) == 7:
                    solr_data.setdefault('date_boost',
                                         '%s-01T00:00:00Z' % form.data.get(field).replace('[', '').replace(']',
                                                                                                           '').strip())
                else:
                    solr_data.setdefault('date_boost',
                                         '%sT00:00:00Z' % form.data.get(field).replace('[', '').replace(']',
                                                                                                        '').strip())
        if field == 'priority_date':
            if form.data.get(field):
                solr_data.setdefault('date', form.data.get(field).replace('[', '').replace(']', '').strip())
                solr_data.setdefault('fdate', form.data.get(field).replace('[', '').replace(']', '')[0:4].strip())
                if len(form.data.get(field).replace('[', '').replace(']', '').strip()) == 4:
                    solr_data.setdefault('date_boost',
                                         '%s-01-01T00:00:00Z' % form.data.get(field).replace('[', '').replace(']',
                                                                                                              '').strip())
                elif len(form.data.get(field).replace('[', '').replace(']', '').strip()) == 7:
                    solr_data.setdefault('date_boost',
                                         '%s-01T00:00:00Z' % form.data.get(field).replace('[', '').replace(']',
                                                                                                           '').strip())
                else:
                    solr_data.setdefault('date_boost',
                                         '%sT00:00:00Z' % form.data.get(field).replace('[', '').replace(']',
                                                                                                        '').strip())
        if field == 'publisher':
            solr_data.setdefault('publisher', form.data.get(field).strip())
            solr_data.setdefault('fpublisher', form.data.get(field).strip())
        if field == 'peer_reviewed':
            solr_data.setdefault('peer_reviewed', form.data.get(field))
        if field == 'language':
            for lang in form.data.get(field):
                solr_data.setdefault('language', []).append(lang)
        if field == 'person':
            # für alle personen
            for idx, person in enumerate(form.data.get(field)):
                # hat die person einen namen?
                if person.get('name'):
                    solr_data.setdefault('person', []).append(person.get('name').strip())
                    solr_data.setdefault('fperson', []).append(person.get('name').strip())
                    # hat die person eine gnd-id?
                    if person.get('gnd'):
                        # logging.info('drin: gnd: %s' % person.get('gnd'))
                        solr_data.setdefault('pnd', []).append(
                            '%s#%s' % (person.get('gnd').strip(), person.get('name').strip()))
                        # prüfe, ob eine 'person' mit GND im System ist. Wenn ja, setze affiliation_context, wenn nicht
                        # schon belegt.
                        try:
                            query = 'id:%s' % person.get('gnd')
                            gnd_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                            application=secrets.SOLR_APP, core='person', query=query, facet='false',
                                            fields=['wtf_json'])
                            gnd_solr.request()
                            if len(gnd_solr.results) == 0:
                                # logging.info('keine Treffer zu gnd: %s' % person.get('gnd'))
                                message.append('IDs from relation "person" could not be found! Ref: %s' % person.get('gnd'))
                            else:
                                # setze den parameter für die boolesche zugehörigkeit
                                myjson = json.loads(gnd_solr.results[0].get('wtf_json'))
                                for catalog in myjson.get('catalog'):
                                    if 'Bochum' in catalog:
                                        # logging.info("%s, %s: yo! rubi!" % (person.get('name'), person.get('gnd')))
                                        form.person[idx].rubi.data = True
                                        solr_data.setdefault('frubi_pers', []).append('%s#%s' % (person.get('gnd').strip(), person.get('name').strip()))
                                        is_rubi = True
                                    if 'Dortmund' in catalog:
                                        form.person[idx].tudo.data = True
                                        solr_data.setdefault('ftudo_pers', []).append('%s#%s' % (person.get('gnd').strip(), person.get('name').strip()))
                                        is_tudo = True
                                # details zur zugeörigkeit ermitteln
                                for idx1, doc in enumerate(gnd_solr.results):
                                    myjson = json.loads(doc.get('wtf_json'))
                                    # logging.info(myjson)
                                    if myjson.get('affiliation') and len(myjson.get('affiliation')) > 0:
                                        for affiliation in myjson.get('affiliation'):
                                            affiliation_id = affiliation.get('organisation_id')
                                            # logging.info(affiliation_id)
                                            # füge affiliation_context dem wtf_json hinzu
                                            # TODO wollen wir das?
                                            # if affiliation_id not in form.data.get('affiliation_context'):
                                                # form.affiliation_context.append_entry(affiliation_id)
                        except AttributeError as e:
                            logging.error(e)
                    else:
                        # TODO versuche Daten aus dem'person'-Index zu holen (vgl. is_part_of oder has_part)
                        # die gndid muss dann aber auch dem 'wtf' hinzugefügt werden
                        solr_data.setdefault('pnd', []).append(
                            '%s#person-%s#%s' % (form.data.get('id'), idx, person.get('name').strip()))
        if field == 'corporation':
            for idx, corporation in enumerate(form.data.get(field)):
                if corporation.get('name'):
                    solr_data.setdefault('institution', []).append(corporation.get('name').strip())
                    solr_data.setdefault('fcorporation', []).append(corporation.get('name').strip())
                    # TODO reicht gnd hier aus? eher nein, oder?
                    if corporation.get('gnd'):
                        solr_data.setdefault('gkd', []).append(
                            '%s#%s' % (corporation.get('gnd').strip(), corporation.get('name').strip()))
                        # prüfe, ob eine 'person' mit GND im System ist. Wenn ja, setze affiliation_context, wenn nicht
                        # schon belegt.
                        try:
                            query = 'id:%s' % corporation.get('gnd')
                            gnd_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                            application=secrets.SOLR_APP, core='organisation', query=query, facet='false',
                                            fields=['wtf_json'])
                            gnd_solr.request()
                            if len(gnd_solr.results) == 0:
                                # logging.info('keine Treffer zu gnd: %s' % person.get('gnd'))
                                message.append('IDs from relation "corporation" could not be found! Ref: %s' % corporation.get('gnd'))
                            else:
                                # setze den parameter für die boolesche zugehörigkeit
                                myjson = json.loads(gnd_solr.results[0].get('wtf_json'))
                                for catalog in myjson.get('catalog'):
                                    if 'Bochum' in catalog:
                                        # logging.info("%s, %s: yo! rubi!" % (corporation.get('name'), corporation.get('gnd')))
                                        form.corporation[idx].rubi.data = True
                                        solr_data.setdefault('frubi_orga', []).append('%s#%s' % (corporation.get('gnd').strip(), corporation.get('name').strip()))
                                        is_rubi = True
                                    if 'Dortmund' in catalog:
                                        form.corporation[idx].tudo.data = True
                                        solr_data.setdefault('ftudo_orga', []).append('%s#%s' % (corporation.get('gnd').strip(), corporation.get('name').strip()))
                                        is_tudo = True
                                # details zur zugeörigkeit ermitteln
                                for idx1, doc in enumerate(gnd_solr.results):
                                    myjson = json.loads(doc.get('wtf_json'))
                                    # logging.info(myjson)
                                    if myjson.get('affiliation') and len(myjson.get('affiliation')) > 0:
                                        for affiliation in myjson.get('affiliation'):
                                            affiliation_id = affiliation.get('organisation_id')
                                            # logging.info(affiliation_id)
                                            # füge affiliation_context dem wtf_json hinzu
                                            if affiliation_id not in form.data.get('affiliation_context'):
                                                form.affiliation_context.append_entry(affiliation_id)
                        except AttributeError as e:
                            logging.error(e)
                    else:
                        solr_data.setdefault('gkd', []).append(
                            '%s#corporation-%s#%s' % (form.data.get('id'), idx, corporation.get('name').strip()))
                if corporation.get('role'):
                    if 'RadioTVProgram' in form.data.get('pubtype') and corporation.get('role')[0] == 'edt':
                        form.corporation[idx].role.data = 'brd'
                    if 'Thesis' in form.data.get('pubtype') and corporation.get('role')[0] == 'ctb':
                        form.corporation[idx].role.data = 'dgg'

        # content and subjects
        if field == 'abstract':
            for abstract in form.data.get(field):
                if abstract.get('sharable'):
                    solr_data.setdefault('abstract', []).append(abstract.get('content').strip())
                else:
                    solr_data.setdefault('ro_abstract', []).append(abstract.get('content').strip())
        if field == 'keyword':
            for keyword in form.data.get(field):
                if keyword.strip():
                    solr_data.setdefault('subject', []).append(keyword.strip())
        if field == 'keyword_temporal':
            for keyword in form.data.get(field):
                if keyword.strip():
                    solr_data.setdefault('subject', []).append(keyword.strip())
        if field == 'keyword_geographic':
            for keyword in form.data.get(field):
                if keyword.strip():
                    solr_data.setdefault('subject', []).append(keyword.strip())
        if field == 'swd_subject':
            for keyword in form.data.get(field):
                if keyword.get('label') and keyword.get('label').strip():
                    solr_data.setdefault('subject', []).append(keyword.get('label').strip())
        if field == 'ddc_subject':
            for keyword in form.data.get(field):
                if keyword.get('label') and keyword.get('label').strip():
                    solr_data.setdefault('ddc', []).append(keyword.get('label').strip())
        if field == 'mesh_subject':
            for keyword in form.data.get(field):
                if keyword.get('label') and keyword.get('label').strip():
                    solr_data.setdefault('mesh_term', []).append(keyword.get('label').strip())
        if field == 'stw_subject':
            for keyword in form.data.get(field):
                if keyword.get('label') and keyword.get('label').strip():
                    solr_data.setdefault('stwterm_de', []).append(keyword.get('label').strip())
        if field == 'lcsh_subject':
            for keyword in form.data.get(field):
                if keyword.get('label') and keyword.get('label').strip():
                    solr_data.setdefault('subject', []).append(keyword.get('label').strip())
        if field == 'thesoz_subject':
            for keyword in form.data.get(field):
                if keyword.get('label') and keyword.get('label').strip():
                    solr_data.setdefault('subject', []).append(keyword.get('label').strip())
        # IDs
        if field == 'DOI':
            try:
                for doi in form.data.get(field):
                    solr_data.setdefault('doi', []).append(doi.strip())
            except AttributeError as e:
                logging.error(form.data.get('id'))
                pass
        if field == 'ISSN':
            try:
                for issn in form.data.get(field):
                    solr_data.setdefault('issn', []).append(issn.strip())
                    solr_data.setdefault('isxn', []).append(issn.strip())
            except AttributeError as e:
                logging.error(form.data.get('id'))
                pass
        if field == 'ZDBID':
            try:
                for zdbid in form.data.get(field):
                    solr_data.setdefault('zdbid', []).append(zdbid.strip())
            except AttributeError as e:
                logging.error(form.data.get('id'))
                pass
        if field == 'ISBN':
            try:
                for isbn in form.data.get(field):
                    solr_data.setdefault('isbn', []).append(isbn.strip())
                    solr_data.setdefault('isxn', []).append(isbn.strip())
            except AttributeError as e:
                logging.error(form.data.get('id'))
                pass
        if field == 'ISMN':
            try:
                for ismn in form.data.get(field):
                    solr_data.setdefault('ismn', []).append(ismn.strip())
                    solr_data.setdefault('isxn', []).append(ismn.strip())
            except AttributeError as e:
                logging.error(form.data.get('id'))
                pass
        if field == 'PMID':
            solr_data.setdefault('pmid', form.data.get(field).strip())
        if field == 'WOSID':
            solr_data.setdefault('isi_id', form.data.get(field).strip())
        if field == 'orcid_put_code':
            solr_data.setdefault('orcid_put_code', form.data.get(field).strip())

        # funding
        if field == 'note':
            if 'funded by the Deutsche Forschungsgemeinschaft' in form.data.get(field):
                form.DFG.data = True
                solr_data.setdefault('dfg', form.data.get('DFG'))

        if field == 'DFG':
            solr_data.setdefault('dfg', form.data.get('DFG'))

        # related entities
        if field == 'event':
            for event in form.data.get(field):
                solr_data.setdefault('other_title', event.get('event_name').strip())
        if field == 'container_title':
            solr_data.setdefault('journal_title', form.data.get(field).strip())
            solr_data.setdefault('fjtitle', form.data.get(field).strip())

        if field == 'is_part_of' and len(form.data.get(field)) > 0:
            ipo_ids = []
            ipo_index = {}
            try:
                for idx, ipo in enumerate(form.data.get(field)):
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
                        message.append('Not all IDs from relation "is part of" could be found! Ref: %s' % form.data.get('id'))
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
                                                                                  'page_first': form.data.get(field)[
                                                                                      idx].get('page_first', ''),
                                                                                  'page_last': form.data.get(field)[
                                                                                      idx].get('page_last', ''),
                                                                                  'volume': form.data.get(field)[
                                                                                      idx].get('volume', ''),
                                                                                  'issue': form.data.get(field)[
                                                                                      idx].get('issue', '')}))
            except AttributeError as e:
                logging.error(e)

        if field == 'has_part' and len(form.data.get(field)) > 0:

            hp_ids = []
            try:
                for idx, hp in enumerate(form.data.get(field)):
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
                            message.append('Not all IDs from relation "has part" could be found! Ref: %s' % form.data.get(
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

        if field == 'other_version' and len(form.data.get(field)) > 0:
            # for myov in form.data.get(field):
            # logging.info('OV ' + myov)
            ov_ids = []
            try:
                for version in form.data.get(field):
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
                        message.append('Not all IDs from relation "other version" could be found! Ref: %s' % form.data.get(
                                        'id'))
                    for doc in ov_solr.results:
                        # logging.info(json.loads(doc.get('wtf_json')))
                        myjson = json.loads(doc.get('wtf_json'))
                        other_version.append(myjson.get('id'))
                        solr_data.setdefault('other_version_id', []).append(myjson.get('id'))
                        solr_data.setdefault('other_version', []).append(json.dumps({'pubtype': myjson.get('pubtype'),
                                                                                     'id': myjson.get('id'),
                                                                                     'title': myjson.get('title'),}))
            except AttributeError as e:
                logging.error(e)

    solr_data.setdefault('rubi', is_rubi)
    solr_data.setdefault('tudo', is_tudo)

    wtf_json = json.dumps(form.data).replace(' "', '"')
    solr_data.setdefault('wtf_json', wtf_json)

    csl_json = json.dumps(wtf_csl.wtf_csl(wtf_records=[json.loads(wtf_json)]))
    solr_data.setdefault('csl_json', csl_json)

    # TODO build openurl
    open_url = openurl_processor.wtf_openurl(json.loads(wtf_json))
    solr_data.setdefault('bibliographicCitation', open_url)

    record_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                       application=secrets.SOLR_APP, core='hb2', data=[solr_data])
    record_solr.update()
    # reload all records listed in has_part, is_part_of, other_version
    # logging.debug('relitems = %s' % relitems)
    # logging.info('has_part: %s' % has_part)
    # logging.info('is_part_of: %s' % is_part_of)
    # logging.info('other_version: %s' % other_version)
    if relitems:
        for record_id in has_part:
            # lock record
            lock_record_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                    application=secrets.SOLR_APP, core='hb2',
                                    data=[{'id': record_id, 'locked': {'set': 'true'}}])
            lock_record_solr.update()
            # search record
            edit_record_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                    application=secrets.SOLR_APP, core='hb2', query='id:%s' % record_id)
            edit_record_solr.request()
            # load record in form and modify changeDate
            thedata = json.loads(edit_record_solr.results[0].get('wtf_json'))
            form = display_vocabularies.PUBTYPE2FORM.get(thedata.get('pubtype')).from_json(thedata)
            # add is_part_of to form if not exists
            exists = False
            if form.data.get('is_part_of'):
                for ipo in form.data.get('is_part_of'):
                    if ipo.get('is_part_of') == id:
                        exists = True
                        break
            if not exists:
                try:
                    is_part_of_form = IsPartOfForm()
                    is_part_of_form.is_part_of.data = id
                    form.is_part_of.append_entry(is_part_of_form.data)
                    form.changed.data = timestamp()
                    # save record
                    record2solr(form, action='update', relitems=False)
                except AttributeError as e:
                    logger.error('linking from %s: %s' % (record_id, str(e)))
            else:
                # save record
                record2solr(form, action='update', relitems=False)
            # unlock record
            unlock_record_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                      application=secrets.SOLR_APP, core='hb2',
                                      data=[{'id': record_id, 'locked': {'set': 'false'}}])
            unlock_record_solr.update()
        for record_id in is_part_of:
            # lock record
            lock_record_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                    application=secrets.SOLR_APP, core='hb2',
                                    data=[{'id': record_id, 'locked': {'set': 'true'}}])
            lock_record_solr.update()
            # search record
            edit_record_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                    application=secrets.SOLR_APP, core='hb2', query='id:%s' % record_id)
            edit_record_solr.request()
            # load record in form and modify changeDate
            thedata = json.loads(edit_record_solr.results[0].get('wtf_json'))
            # logging.info('is_part_of-Item: %s' % thedata)
            form = display_vocabularies.PUBTYPE2FORM.get(thedata.get('pubtype')).from_json(thedata)
            # add has_part to form
            exists = False
            if form.data.get('has_part'):
                for hpo in form.data.get('has_part'):
                    if hpo.get('has_part') == id:
                        exists = True
                        break
            if not exists:
                try:
                    has_part_form = HasPartForm()
                    has_part_form.has_part.data = id
                    form.has_part.append_entry(has_part_form.data)
                    form.changed.data = timestamp()
                    # save record
                    record2solr(form, action='update', relitems=False)
                except AttributeError as e:
                    logger.error('linking from %s: %s' % (record_id, str(e)))
            else:
                # save record
                record2solr(form, action='update', relitems=False)

            # unlock record
            unlock_record_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                      application=secrets.SOLR_APP, core='hb2',
                                      data=[{'id': record_id, 'locked': {'set': 'false'}}])
            unlock_record_solr.update()
        for record_id in other_version:
            # lock record
            lock_record_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                    application=secrets.SOLR_APP, core='hb2',
                                    data=[{'id': record_id, 'locked': {'set': 'true'}}])
            lock_record_solr.update()
            # search record
            edit_record_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                    application=secrets.SOLR_APP, core='hb2', query='id:%s' % record_id)
            edit_record_solr.request()
            # load record in form and modify changeDate
            thedata = json.loads(edit_record_solr.results[0].get('wtf_json'))
            form = display_vocabularies.PUBTYPE2FORM.get(thedata.get('pubtype')).from_json(thedata)
            # add is_part_of to form
            exists = False
            if form.data.get('other_version'):
                for ovo in form.data.get('other_version'):
                    if ovo.get('other_version') == id:
                        exists = True
                        break
            if not exists:
                try:
                    other_version_form = OtherVersionForm()
                    other_version_form.other_version.data = id
                    form.other_version.append_entry(other_version_form.data)
                    form.changed.data = timestamp()
                    # save record
                    record2solr(form, action='update', relitems=False)
                except AttributeError as e:
                    logger.error('linking from %s: %s' % (record_id, str(e)))
            else:
                # save record
                record2solr(form, action='update', relitems=False)
            # unlock record
            unlock_record_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                      application=secrets.SOLR_APP, core='hb2',
                                      data=[{'id': record_id, 'locked': {'set': 'false'}}])
            unlock_record_solr.update()

    return message


def person2solr(form, action):

    message = []
    tmp = {}

    if not form.data.get('editorial_status'):
        form.editorial_status.data = 'new'

    if not form.data.get('owner'):
        tmp.setdefault('owner', ['daten.ub@tu-dortmund.de'])
    else:
        tmp.setdefault('owner', form.data.get('owner'))

    new_id = form.data.get('id')
    for field in form.data:
        if field == 'name':
            form.name.data = form.data.get(field).strip()
            tmp.setdefault('name', form.data.get(field).strip())
        elif field == 'also_known_as':
            for also_known_as in form.data.get(field):
                if len(also_known_as.strip()) > 0:
                    tmp.setdefault('also_known_as', []).append(str(also_known_as).strip())
        elif field == 'same_as':
            for same_as in form.data.get(field):
                if len(same_as.strip()) > 0:
                    tmp.setdefault('same_as', []).append(same_as.strip())
        elif field == 'gnd':
            if len(form.data.get(field).strip()) > 0:
                tmp.setdefault('gnd', form.data.get(field).strip())
                new_id = form.data.get(field).strip()
        elif field == 'dwid':
            tmp.setdefault('dwid', form.data.get(field))
            logging.info('%s vs. %s' % (form.data.get(field).strip(), form.data.get('gnd')))
            if len(form.data.get('gnd')) == 0 and len(form.data.get(field).strip()) > 0:
                new_id = form.data.get(field).strip().strip()
        elif field == 'email':
            tmp.setdefault('email', form.data.get(field))
        elif field == 'rubi':
            tmp.setdefault('rubi', form.data.get(field))
        elif field == 'tudo':
            tmp.setdefault('tudo', form.data.get(field))
        elif field == 'created':
            tmp.setdefault('created', form.data.get(field).strip().replace(' ', 'T') + 'Z')
        elif field == 'changed':
            tmp.setdefault('changed', form.data.get(field).strip().replace(' ', 'T') + 'Z')
        elif field == 'catalog':
            for catalog in form.data.get(field):
                tmp.setdefault('catalog', catalog.strip())
        elif field == 'status':
            for status in form.data.get(field):
                tmp.setdefault('personal_status', []).append(status.strip())
        elif field == 'editorial_status':
            tmp.setdefault('editorial_status', form.data.get(field))
        elif field == 'deskman' and form.data.get(field):
            tmp.setdefault('deskman', form.data.get(field).strip())
        elif field == 'catalog':
            for catalog in form.data.get(field):
                tmp.setdefault('catalog', catalog.strip())
        elif field == 'research_interest':
            for research_interest in form.data.get(field):
                tmp.setdefault('research_interest', []).append(research_interest.strip())
        elif field == 'url':
            for url in form.data.get(field):
                tmp.setdefault('url', []).append(url.get('label').strip())
        elif field == 'membership':
            for membership in form.data.get(field):
                if membership.get('label'):
                    tmp.setdefault('membership', []).append(membership.get('label').strip())
        elif field == 'award':
            for award in form.data.get(field):
                if award.get('label'):
                    tmp.setdefault('award', []).append(award.get('label').strip())
        elif field == 'project':
            for project in form.data.get(field):
                if project.get('label'):
                    tmp.setdefault('project', []).append(project.get('label').strip())
                if project.get('project_id') and project.get('label'):
                    tmp.setdefault('project_id', []).append(
                        '%s#%s' % (project.get('project_id').strip(), project.get('label').strip()))
                if project.get('project_type'):
                    tmp.setdefault('project_type', []).append(project.get('project_type'))
        elif field == 'thesis':
            for thesis in form.data.get(field):
                if thesis.get('label'):
                    tmp.setdefault('thesis', []).append(thesis.get('label').strip())
        elif field == 'cv':
            for cv in form.data.get(field):
                if cv.get('label'):
                    tmp.setdefault('cv', []).append(cv.get('label').strip())
        elif field == 'editor':
            for editor in form.data.get(field):
                if editor.get('label'):
                    tmp.setdefault('editor', []).append(editor.get('label').strip())
                if editor.get('issn'):
                    tmp.setdefault('editor_issn', []).append(editor.get('issn'))
                if editor.get('zdbid'):
                    tmp.setdefault('editor_zdbid', []).append(editor.get('zdbid'))
        elif field == 'reviewer':
            for reviewer in form.data.get(field):
                if reviewer.get('label'):
                    tmp.setdefault('reviewer', []).append(reviewer.get('label').strip())
                if reviewer.get('issn'):
                    tmp.setdefault('reviewer_issn', []).append(reviewer.get('issn'))
                if reviewer.get('zdbid'):
                    tmp.setdefault('reviewer_zdbid', []).append(reviewer.get('zdbid'))
        elif field == 'data_supplied':
            if form.data.get(field).strip() != "":
                tmp.setdefault('data_supplied', '%sT00:00:00.001Z' % form.data.get(field).strip())

        elif field == 'affiliation':
            for idx, affiliation in enumerate(form.data.get(field)):
                if affiliation.get('organisation_id'):
                    tmp.setdefault('affiliation_id', affiliation.get('organisation_id'))
                    try:
                        query = 'id:%s' % affiliation.get('organisation_id')
                        parent_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                           application=secrets.SOLR_APP, core='organisation', query=query,
                                           facet='false', fields=['wtf_json'])
                        parent_solr.request()
                        if len(parent_solr.results) == 0:
                            query = 'account:%s' % affiliation.get('organisation_id')
                            parent_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                               application=secrets.SOLR_APP, core='organisation', query=query,
                                               facet='false', fields=['wtf_json'])
                            parent_solr.request()
                            if len(parent_solr.results) == 0:
                                query = 'same_as:%s' % affiliation.get('organisation_id')
                                parent_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                                   application=secrets.SOLR_APP, core='organisation', query=query,
                                                   facet='false', fields=['wtf_json'])
                                parent_solr.request()
                                if len(parent_solr.results) == 0:
                                    message.append('IDs from relation "organisation_id" could not be found! Ref: %s' % affiliation.get(
                                                'organisation_id'))
                                else:
                                    for doc in parent_solr.results:
                                        myjson = json.loads(doc.get('wtf_json'))
                                        # logging.info(myjson.get('pref_label'))
                                        label = myjson.get('pref_label').strip()
                                        form.affiliation[idx].pref_label.data = label
                                        tmp.setdefault('affiliation', []).append(label)
                                        tmp.setdefault('faffiliation', []).append(label)
                            else:
                                for doc in parent_solr.results:
                                    myjson = json.loads(doc.get('wtf_json'))
                                    # logging.info(myjson.get('pref_label'))
                                    label = myjson.get('pref_label').strip()
                                    form.affiliation[idx].pref_label.data = label
                                    tmp.setdefault('affiliation', []).append(label)
                                    tmp.setdefault('faffiliation', []).append(label)
                        else:
                            for doc in parent_solr.results:
                                myjson = json.loads(doc.get('wtf_json'))
                                # logging.info(myjson.get('pref_label'))
                                label = myjson.get('pref_label').strip()
                                form.affiliation[idx].pref_label.data = label
                                tmp.setdefault('affiliation', []).append(label)
                                tmp.setdefault('faffiliation', []).append(label)
                    except AttributeError as e:
                        logging.error(e)
                elif affiliation.get('pref_label'):
                    tmp.setdefault('affiliation', []).append(affiliation.get('pref_label').strip())
                    tmp.setdefault('faffiliation', []).append(affiliation.get('pref_label').strip())

        elif field == 'group':
            for idx, group in enumerate(form.data.get(field)):
                if group.get('group_id'):
                    tmp.setdefault('group_id', group.get('group_id'))
                    try:
                        query = 'id:%s' % group.get('group_id')
                        group_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                          application=secrets.SOLR_APP, core='group', query=query, facet='false',
                                          fields=['wtf_json'])
                        group_solr.request()
                        if len(group_solr.results) == 0:
                            query = 'same_as:%s' % group.get('group_id')
                            group_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                              application=secrets.SOLR_APP, core='group', query=query,
                                              facet='false', fields=['wtf_json'])
                            group_solr.request()
                            if len(group_solr.results) == 0:
                                message.append('IDs from relation "group_id" could not be found! Ref: %s' % group.get(
                                            'group_id'))
                            else:
                                for doc in group_solr.results:
                                    myjson = json.loads(doc.get('wtf_json'))
                                    # logging.info(myjson.get('pref_label'))
                                    label = myjson.get('pref_label').strip()
                                    form.affiliation[idx].pref_label.data = label
                                    tmp.setdefault('group', []).append(label)
                                    tmp.setdefault('fgroup', []).append(label)
                        else:
                            for doc in group_solr.results:
                                myjson = json.loads(doc.get('wtf_json'))
                                # logging.info(myjson.get('pref_label'))
                                label = myjson.get('pref_label').strip()
                                form.group[idx].pref_label.data = label
                                tmp.setdefault('group', []).append(label)
                                tmp.setdefault('fgroup', []).append(label)
                    except AttributeError as e:
                        logging.error(e)
                elif group.get('pref_label'):
                    tmp.setdefault('group', []).append(group.get('pref_label').strip())
                    tmp.setdefault('fgroup', []).append(group.get('pref_label').strip())

    doit = False
    if action == 'create':
        person_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                           application=secrets.SOLR_APP, core='person', query='id:%s' % new_id,
                           facet='false', fields=['wtf_json'])
        person_solr.request()
        if len(person_solr.results) == 0:
            doit = True
    else:
        doit = True

    # logging.info('new_id: %s for %s' % (new_id, form.data.get('id')))
    # logging.info('doit: %s for %s' % (doit, form.data.get('id')))

    if doit:
        if new_id != form.data.get('id'):
            form.same_as.append_entry(form.data.get('id'))
            tmp.setdefault('same_as', []).append(form.data.get('id'))
            # delete record with current id
            try:
                delete_person_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                          application=secrets.SOLR_APP, core='person', del_id=form.data.get('id'))
                delete_person_solr.delete()
            except AttributeError as e:
                logging.error(e)
            form.id.data = new_id
        tmp.setdefault('id', new_id)
        wtf_json = json.dumps(form.data)
        tmp.setdefault('wtf_json', wtf_json)
        person_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                           application=secrets.SOLR_APP, core='person', data=[tmp])
        person_solr.update()

    return doit, new_id, message


def orga2solr(form, action, relitems=True):

    message = []

    tmp = {}
    parents = []
    children = []
    projects = []

    id = form.data.get('id').strip()
    logging.info('ID: %s' % id)
    dwid = form.data.get('dwid')
    logging.info('DWID: %s' % dwid)

    if not form.data.get('editorial_status'):
        form.editorial_status.data = 'new'

    if not form.data.get('owner'):
        tmp.setdefault('owner', ['daten.ub@tu-dortmund.de'])
    else:
        tmp.setdefault('owner', form.data.get('owner'))

    for field in form.data:
        if field == 'orga_id':
            tmp.setdefault('orga_id', form.data.get(field))
        elif field == 'same_as':
            for same_as in form.data.get(field):
                if len(same_as.strip()) > 0:
                    tmp.setdefault('same_as', []).append(same_as.strip())
        elif field == 'pref_label':
            tmp.setdefault('pref_label', form.data.get(field).strip())
        elif field == 'alt_label':
            for alt_label in form.data.get(field):
                tmp.setdefault('alt_label', []).append(alt_label.strip())
        elif field == 'dwid':
            for account in form.data.get(field):
                tmp.setdefault('account', []).append(account.strip())
            if len(form.data.get('gnd')) == 0 and len(form.data.get(field)[0].strip()) > 0:
                form.id.data = form.data.get(field)[0].strip()
        elif field == 'gnd':
            if len(form.data.get(field)) > 0:
                tmp.setdefault('gnd', form.data.get(field).strip())
                form.id.data = form.data.get(field).strip()
        elif field == 'created':
            tmp.setdefault('created', form.data.get(field).strip().replace(' ', 'T') + 'Z')
        elif field == 'changed':
            tmp.setdefault('changed', form.data.get(field).strip().replace(' ', 'T') + 'Z')
        elif field == 'deskman' and form.data.get(field):
            tmp.setdefault('deskman', form.data.get(field).strip())
        elif field == 'editorial_status':
            tmp.setdefault('editorial_status', form.data.get(field))
        elif field == 'catalog':
            for catalog in form.data.get(field):
                tmp.setdefault('catalog', catalog.strip())
        elif field == 'destatis':
            for destatis in form.data.get(field):
                if destatis.get('destatis_label'):
                    tmp.setdefault('destatis_label', []).append(destatis.get('destatis_label').strip())
                if destatis.get('destatis_id'):
                    tmp.setdefault('destatis_id', []).append(destatis.get('destatis_id').strip())

        elif field == 'parent':
            parent = form.data.get(field)[0]
            # logging.info('parent: %s' % parent)
            if parent.get('parent_id'):
                # remember ID for work on related entity
                parents.append(parent.get('parent_id'))
                # prepare index data and enrich form data
                tmp.setdefault('parent_id', parent.get('parent_id'))
                try:
                    query = 'id:%s' % parent.get('parent_id')
                    parent_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                       application=secrets.SOLR_APP, core='organisation', query=query,
                                       facet='false',
                                       fields=['wtf_json'])
                    parent_solr.request()
                    # logging.info('Treffer für %s: %s' % (parent.get('id'), len(parent_solr.results)))
                    if len(parent_solr.results) == 0:
                        message.append('IDs from relation "parent" could not be found! Ref: %s' % parent.get('parent_id'))
                    else:
                        for doc in parent_solr.results:
                            myjson = json.loads(doc.get('wtf_json'))
                            label = myjson.get('pref_label').strinp()
                            tmp.setdefault('parent_label', label)
                            tmp.setdefault('fparent', '%s#%s' % (myjson.get('id').strip(), label))
                            form.parent[0].parent_label.data = label
                except AttributeError as e:
                    logging.error('ORGA: parent_id=%s: %s' % (parent.get('parent_id'), e))
            elif parent.get('parent_label') and len(parent.get('parent_label')) > 0:
                tmp.setdefault('fparent', parent.get('parent_label'))
                tmp.setdefault('parent_label', parent.get('parent_label'))

        elif field == 'children':
            # logging.info('children in form of %s : %s' % (id, form.data.get(field)))
            for idx, child in enumerate(form.data.get(field)):
                if child:
                    if 'child_id' in child and 'child_label' in child:
                        if child.get('child_id'):
                            # remember ID for work on related entity
                            children.append(child.get('child_id'))
                            # prepare index data and enrich form data
                            try:
                                query = 'id:%s' % child.get('child_id')
                                child_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                                  application=secrets.SOLR_APP, core='organisation',
                                                  query=query,
                                                  facet='false', fields=['wtf_json'])
                                child_solr.request()
                                if len(child_solr.results) > 0:
                                    for doc in child_solr.results:
                                        myjson = json.loads(doc.get('wtf_json'))
                                        label = myjson.get('pref_label').strip()
                                        form.children[idx].child_label.data = label
                                        tmp.setdefault('children', []).append(
                                            json.dumps({'id': myjson.get('id').strip(),
                                                        'label': label,
                                                        'type': 'organisation'}))
                                        tmp.setdefault('fchildren', []).append(
                                            '%s#%s' % (myjson.get('id').strip(), label))
                                else:
                                    child_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                                      application=secrets.SOLR_APP, core='group',
                                                      query=query,
                                                      facet='false', fields=['wtf_json'])
                                    child_solr.request()
                                    if len(child_solr.results) > 0:
                                        for doc in child_solr.results:
                                            myjson = json.loads(doc.get('wtf_json'))
                                            label = myjson.get('pref_label').strip()
                                            form.children[idx].child_label.data = label
                                            tmp.setdefault('children', []).append(json.dumps({'id': myjson.get('id').strip(),
                                                                                              'label': label,
                                                                                              'type': 'group'}))
                                            tmp.setdefault('fchildren', []).append(
                                                '%s#%s' % (myjson.get('id').strip(), label))

                                    else:
                                        message.append('IDs from relation "child" could not be found! Ref: %s' % child.get(
                                                    'child_id'))
                            except AttributeError as e:
                                logging.error('ORGA: child_id=%s: %s' % (child.get('child_id'), e))
                        elif child.get('child_label'):
                            tmp.setdefault('children', []).append(json.dumps({'id': '',
                                                                              'label': child.get('child_label').strip(),
                                                                              'type': ''}))
                            tmp.setdefault('fchildren', []).append(child.get('child_label').strip())

        elif field == 'projects':
            # logging.info('projects in form of %s : %s' % (id, form.data.get(field)))
            for idx, project in enumerate(form.data.get(field)):
                if project:
                    if 'project_id' in project and 'project_label' in project:
                        if project.get('project_id'):
                            # remember ID for work on related entity
                            projects.append(project.get('project_id'))
                            # prepare index data and enrich form data
                            try:
                                query = 'id:%s' % project.get('project_id')
                                project_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                                    application=secrets.SOLR_APP, core='group', query=query,
                                                    facet='false', fields=['wtf_json'])
                                project_solr.request()
                                if len(project_solr.results) == 0:
                                    message.append('IDs from relation "projects" could not be found! Ref: %s' % project.get('project_id'))
                                for doc in project_solr.results:
                                    myjson = json.loads(doc.get('wtf_json'))
                                    label = myjson.get('pref_label').strip()
                                    form.projects[idx].project_label.data = label
                                    tmp.setdefault('projects', []).append(json.dumps({'id': myjson.get('id').strip(),
                                                                                      'label': label}))
                                    tmp.setdefault('fprojects', []).append('%s#%s' % (myjson.get('id').strip(), label))

                            except AttributeError as e:
                                logging.error('GROUP: project_id=%s: %s' % (project.get('project_id'), e))
                        elif project.get('project_label'):
                            tmp.setdefault('fprojects', []).append(project.get('project_label').strip())

    # search record
    search_orga_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                            application=secrets.SOLR_APP, core='organisation', rows=1000, query='parent_id:%s' % id)
    search_orga_solr.request()
    if len(search_orga_solr.results) > 0:
        children = form.data.get('children')
        for result in search_orga_solr.results:
            exists = False
            for project in children:
                logging.info('%s vs. %s' % (project.get('child_id'), result.get('id')))
                if project.get('child_id') == result.get('id'):
                    exists = True
                    break
            if not exists:
                childform = ChildForm()
                childform.child_id.data = result.get('id')
                childform.child_label.data = result.get('pref_label')
                form.children.append_entry(childform.data)

    # save record to index
    try:
        # logging.info('%s vs. %s' % (id, form.data.get('id')))
        if id != form.data.get('id'):
            delete_orga_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                    application=secrets.SOLR_APP, core='organisation', del_id=id)
            delete_orga_solr.delete()
            form.same_as.append_entry(id)
            tmp.setdefault('id', form.data.get('id'))
            tmp.setdefault('same_as', []).append(id)

            id = form.data.get('id')
        else:
            tmp.setdefault('id', id)
        # build json
        wtf_json = json.dumps(form.data)
        tmp.setdefault('wtf_json', wtf_json)
        # logging.info(tmp)
        orga_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                         application=secrets.SOLR_APP, core='organisation', data=[tmp])
        orga_solr.update()
    except AttributeError as e:
        logging.error(e)

    same_as = form.data.get('same_as')
    # logging.info('same_as: %s' % same_as)

    # add link to parent
    if relitems:
        # logging.info('parents: %s' % parents)
        for parent_id in parents:
            # search record
            edit_orga_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                  application=secrets.SOLR_APP, core='organisation', query='id:%s' % parent_id)
            edit_orga_solr.request()
            # load orga in form and modify changeDate
            if len(edit_orga_solr.results) > 0:
                # lock record
                lock_orga_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                      application=secrets.SOLR_APP, core='organisation',
                                      data=[{'id': parent_id, 'locked': {'set': 'true'}}])
                lock_orga_solr.update()
                # edit
                try:
                    thedata = json.loads(edit_orga_solr.results[0].get('wtf_json'))
                    form = OrgaAdminForm.from_json(thedata)
                    # add child to form if not exists
                    exists = False
                    for project in form.data.get('children'):
                        # logging.info('%s == %s ?' % (project.get('child_id'), id))
                        if project.get('child_id'):
                            if project.get('child_id') == id:
                                exists = True
                                break
                            elif project.get('child_id') in dwid:
                                exists = True
                                break
                            elif project.get('child_id') in same_as:
                                exists = True
                                break
                    if not exists:
                        try:
                            childform = ChildForm()
                            childform.child_id.data = id
                            form.children.append_entry(childform.data)
                            form.changed.data = timestamp()
                            # save record
                            orga2solr(form, action='update', relitems=False)
                        except AttributeError as e:
                            logging.error('linking from %s: %s' % (parent_id, str(e)))
                    else:
                        # possibly rewrite label
                        form.changed.data = timestamp()
                        orga2solr(form, action='update', relitems=False)
                except TypeError as e:
                    logging.error(e)
                    logging.error('thedate: %s' % edit_orga_solr.results[0].get('wtf_json'))
                # unlock record
                unlock_orga_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                        application=secrets.SOLR_APP, core='organisation',
                                        data=[{'id': parent_id, 'locked': {'set': 'false'}}])
                unlock_orga_solr.update()
            else:
                logging.info('Currently there is no record for parent_id %s!' % parent_id)

        # logging.info('children: %s' % children)
        for child_id in children:
            # search record
            edit_orga_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                  application=secrets.SOLR_APP, core='organisation', query='id:%s' % child_id)
            edit_orga_solr.request()
            # load orga in form and modify changeDate
            if len(edit_orga_solr.results) > 0:
                # lock record
                lock_orga_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                      application=secrets.SOLR_APP, core='organisation',
                                      data=[{'id': child_id, 'locked': {'set': 'true'}}])
                lock_orga_solr.update()
                # edit
                try:
                    thedata = json.loads(edit_orga_solr.results[0].get('wtf_json'))
                    form = OrgaAdminForm.from_json(thedata)
                    # add parent to form if not exists
                    if not form.data.get('parent'):
                        try:
                            parentform = ParentForm()
                            parentform.parent_id = id
                            form.parent.append_entry(parentform.data)
                            form.changed.data = timestamp()
                            # save record
                            orga2solr(form, action='update', relitems=False)
                        except AttributeError as e:
                            logging.error('linking from %s: %s' % (child_id, str(e)))
                    else:
                        try:
                            form.parent[0].parent_id = id
                            form.changed.data = timestamp()
                            # save record
                            orga2solr(form, action='update', relitems=False)
                        except AttributeError as e:
                            logging.error('linking from %s: %s' % (child_id, str(e)))
                except TypeError as e:
                    logging.error(e)
                    logging.error('thedate: %s' % edit_orga_solr.results[0].get('wtf_json'))
                # unlock record
                unlock_orga_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                        application=secrets.SOLR_APP, core='organisation',
                                        data=[{'id': child_id, 'locked': {'set': 'false'}}])
                unlock_orga_solr.update()
            else:
                edit_group_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                       application=secrets.SOLR_APP, core='group', query='id:%s' % child_id)
                edit_group_solr.request()
                # load orga in form and modify changeDate
                if len(edit_group_solr.results) > 0:
                    # lock record
                    lock_group_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                           application=secrets.SOLR_APP, core='group',
                                           data=[{'id': child_id, 'locked': {'set': 'true'}}])
                    lock_group_solr.update()
                    # edit
                    try:
                        thedata = json.loads(edit_group_solr.results[0].get('wtf_json'))
                        form = GroupAdminForm.from_json(thedata)
                        # add parent to form if not exists
                        if not form.data.get('parent'):
                            try:
                                parentform = ParentForm()
                                parentform.parent_id = id
                                form.parent.append_entry(parentform.data)
                                form.changed.data = timestamp()
                                # save record
                                group2solr(form, action='update', relitems=False)
                            except AttributeError as e:
                                logging.error('linking from %s: %s' % (child_id, str(e)))
                        else:
                            try:
                                form.parent[0].parent_id = id
                                form.changed.data = timestamp()
                                # save record
                                group2solr(form, action='update', relitems=False)
                            except AttributeError as e:
                                logging.error('linking from %s: %s' % (child_id, str(e)))
                    except TypeError as e:
                        logging.error(e)
                        logging.error('thedate: %s' % edit_group_solr.results[0].get('wtf_json'))
                    # unlock record
                    unlock_group_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                             application=secrets.SOLR_APP, core='group',
                                             data=[{'id': child_id, 'locked': {'set': 'false'}}])
                    unlock_group_solr.update()

                else:
                    logging.info('Currently there is no record for child_id %s!' % child_id)

        # logging.debug('partners: %s' % partners)
        for project_id in projects:
            # search record
            query = 'id:%s' % project_id
            edit_orga_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                  application=secrets.SOLR_APP, core='group', query=query)
            edit_orga_solr.request()
            # load orga in form and modify changeDate
            if len(edit_orga_solr.results) > 0:
                # lock record
                lock_orga_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                      application=secrets.SOLR_APP, core='group',
                                      data=[{'id': project_id, 'locked': {'set': 'true'}}])
                lock_orga_solr.update()
                # edit
                try:
                    thedata = json.loads(edit_orga_solr.results[0].get('wtf_json'))
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
                        try:
                            partnerform = PartnerForm()
                            partnerform.partner_id.data = id
                            form.partners.append_entry(partnerform.data)
                            form.changed.data = timestamp()
                            # save record
                            group2solr(form, action='update', relitems=False)
                        except AttributeError as e:
                            logging.error('ERROR linking from %s: %s' % (project_id, str(e)))
                    else:
                        # possibly rewrite label
                        form.changed.data = timestamp()
                        group2solr(form, action='update', relitems=False)
                except TypeError as e:
                    logging.error(e)
                    logging.error('thedata: %s' % edit_orga_solr.results[0].get('wtf_json'))
                # unlock record
                unlock_orga_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                        application=secrets.SOLR_APP, core='group',
                                        data=[{'id': project_id, 'locked': {'set': 'false'}}])
                unlock_orga_solr.update()
            else:
                logging.info('Currently there is no record for project_id %s!' % project_id)

        # store work records again
        works_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                          application=secrets.SOLR_APP, core='hb2',
                          query='affiliation_id:%s' % id, facet=False, rows=500000)
        works_solr.request()

        for work in works_solr.results:
            # lock record
            lock_work_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                  application=secrets.SOLR_APP, core='hb2',
                                  data=[{'id': work.get('id'), 'locked': {'set': 'true'}}])
            lock_work_solr.update()

            # edit
            try:
                thedata = json.loads(work.get('wtf_json'))
                form = display_vocabularies.PUBTYPE2FORM.get(thedata.get('pubtype')).from_json(thedata)
                form.changed.data = timestamp()
                record2solr(form, action='update')
            except TypeError as e:
                logging.error(e)
                logging.error('thedata: %s' % work.get('wtf_json'))

            # unlock record
            unlock_work_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                    application=secrets.SOLR_APP, core='hb2',
                                    data=[{'id': work.get('id'), 'locked': {'set': 'false'}}])
            unlock_work_solr.update()

        # store person records again
        persons_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                            application=secrets.SOLR_APP, core='person',
                            query='affiliation_id:%s' % id, facet=False, rows=500000)
        persons_solr.request()

        for person in persons_solr.results:
            # lock record
            lock_person_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                    application=secrets.SOLR_APP, core='person',
                                    data=[{'id': person.get('id'), 'locked': {'set': 'true'}}])
            lock_person_solr.update()

            # edit
            try:
                thedata = json.loads(person.get('wtf_json'))
                form = PersonAdminForm.from_json(thedata)
                form.changed.data = timestamp()
                person2solr(form, action='update')
            except TypeError as e:
                logging.error(e)
                logging.error('thedata: %s' % person.get('wtf_json'))

            # unlock record
            unlock_person_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                      application=secrets.SOLR_APP, core='person',
                                      data=[{'id': person.get('id'), 'locked': {'set': 'false'}}])
            unlock_person_solr.update()

    return id, message


def group2solr(form, action, relitems=True):

    message = []

    tmp = {}
    parents = []
    children = []
    partners = []

    id = form.data.get('id').strip()
    logging.info('ID: %s' % id)

    if not form.data.get('editorial_status'):
        form.editorial_status.data = 'new'

    if action == 'update':
        if form.data.get('editorial_status') == 'new':
            form.editorial_status.data = 'in_process'

    if not form.data.get('owner'):
        tmp.setdefault('owner', ['daten.ub@tu-dortmund.de'])
    else:
        tmp.setdefault('owner', form.data.get('owner'))

    for field in form.data:
        if field == 'id':
            tmp.setdefault('id', form.data.get(field))
        elif field == 'same_as':
            for same_as in form.data.get(field):
                if len(same_as.strip()) > 0:
                    tmp.setdefault('same_as', []).append(same_as.strip())
        elif field == 'funds':
            for funder in form.data.get(field):
                if len(funder.get('organisation').strip()) > 0:
                    tmp.setdefault('funder_id', []).append(funder.get('organisation_id').strip())
                    tmp.setdefault('funder', []).append(funder.get('organisation').strip())
                    tmp.setdefault('ffunder', []).append(funder.get('organisation').strip())
        elif field == 'pref_label':
            tmp.setdefault('pref_label', form.data.get(field).strip())
        elif field == 'alt_label':
            for alt_label in form.data.get(field):
                tmp.setdefault('alt_label', []).append(alt_label.data.strip())
        elif field == 'dwid':
            tmp.setdefault('account', form.data.get(field))
        elif field == 'gnd':
            if len(form.data.get(field)) > 0:
                tmp.setdefault('gnd', form.data.get(field).strip())
                form.id.data = form.data.get(field).strip()
        elif field == 'created':
            tmp.setdefault('created', form.data.get(field).strip().replace(' ', 'T') + 'Z')
        elif field == 'changed':
            tmp.setdefault('changed', form.data.get(field).strip().replace(' ', 'T') + 'Z')
        elif field == 'deskman' and form.data.get(field):
            tmp.setdefault('deskman', form.data.get(field).strip())
        elif field == 'editorial_status':
            tmp.setdefault('editorial_status', form.data.get(field))
        elif field == 'catalog':
            for catalog in form.data.get(field):
                tmp.setdefault('catalog', catalog.strip())
        elif field == 'destatis':
            for destatis in form.data.get(field):
                if destatis.get('destatis_label'):
                    tmp.setdefault('destatis_label', []).append(destatis.get('destatis_label').strip())
                if destatis.get('destatis_id'):
                    tmp.setdefault('destatis_id', []).append(destatis.get('destatis_id').strip())

        elif field == 'parent':
            parent = form.data.get(field)[0]
            # logging.info('parent: %s' % parent)
            if parent.get('parent_id'):
                # remember ID for work on related entity
                parents.append(parent.get('parent_id'))
                # prepare index data and enrich form data
                tmp.setdefault('parent_id', parent.get('parent_id'))
                try:
                    query = 'id:%s' % parent.get('parent_id')
                    parent_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                       application=secrets.SOLR_APP, core='group', query=query,
                                       facet='false',
                                       fields=['wtf_json'])
                    parent_solr.request()
                    # logging.info('Treffer für %s: %s' % (parent.get('id'), len(parent_solr.results)))
                    results = []
                    type = ''
                    if len(parent_solr.results) == 0:

                        parent_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                           application=secrets.SOLR_APP, core='organisation', query=query,
                                           facet='false',
                                           fields=['wtf_json'])
                        parent_solr.request()

                        if len(parent_solr.results) == 0:
                            message.append('IDs from relation "parent" could not be found! Ref: %s' % parent.get('parent_id'))
                        else:
                            results = parent_solr.results
                            type = 'organisation'
                    else:
                        results = parent_solr.results
                        type = 'group'

                    if results:
                        for doc in parent_solr.results:
                            myjson = json.loads(doc.get('wtf_json'))
                            tmp.setdefault('parent_type', type)
                            tmp.setdefault('parent_label', myjson.get('pref_label'))
                            tmp.setdefault('fparent', '%s#%s' % (myjson.get('id'), myjson.get('pref_label')))
                            form.parent[0].parent_label.data = myjson.get('pref_label')

                except AttributeError as e:
                    logging.error('GROUP: parent_id=%s: %s' % (parent.get('parent_id'), e))
            elif parent.get('parent_label'):
                tmp.setdefault('fparent', parent.get('parent_label'))
                tmp.setdefault('parent_label', parent.get('parent_label'))

        elif field == 'children':
            # logging.info('children in form of %s : %s' % (id, form.data.get(field)))
            for idx, child in enumerate(form.data.get(field)):
                if child:
                    if 'child_id' in child and 'child_label' in child:
                        if child.get('child_id'):
                            # remember ID for work on related entity
                            children.append(child.get('child_id'))
                            # prepare index data and enrich form data
                            try:
                                query = 'id:%s' % child.get('child_id')
                                child_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                                  application=secrets.SOLR_APP, core='group',
                                                  query=query,
                                                  facet='false', fields=['wtf_json'])
                                child_solr.request()
                                if len(child_solr.results) == 0:
                                    message.append('IDs from relation "child" could not be found! Ref: %s' % child.get(
                                                'child_id'))
                                for doc in child_solr.results:
                                    myjson = json.loads(doc.get('wtf_json'))
                                    label = myjson.get('pref_label').strip()
                                    form.children[idx].child_label.data = label
                                    tmp.setdefault('children', []).append(json.dumps({'id': myjson.get('id'),
                                                                                      'label': label}))
                                    tmp.setdefault('fchildren', []).append('%s#%s' % (myjson.get('id'), label))
                            except AttributeError as e:
                                logging.error('GROUP: child_id=%s: %s' % (child.get('child_id'), e))
                        elif child.get('child_label'):
                            tmp.setdefault('children', []).append(child.get('child_label'))
                            tmp.setdefault('fchildren', []).append(child.get('child_label'))

        elif field == 'partners':
            # logging.info('partners in form of %s : %s' % (id, form.data.get(field)))
            for idx, partner in enumerate(form.data.get(field)):
                if partner:
                    if 'partner_id' in partner and 'partner_label' in partner:
                        if partner.get('partner_id'):
                            # remember ID for work on related entity
                            partners.append(partner.get('partner_id'))
                            # prepare index data and enrich form data
                            try:
                                query = 'id:%s' % partner.get('partner_id')
                                partner_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                                    application=secrets.SOLR_APP, core='organisation', query=query,
                                                    facet='false', fields=['wtf_json'])
                                partner_solr.request()
                                # TODO same_as
                                if len(partner_solr.results) == 0:
                                    message.append('IDs from relation "partners" could not be found! Ref: %s' % partner.get('partner_id'))
                                for doc in partner_solr.results:
                                    myjson = json.loads(doc.get('wtf_json'))
                                    label = myjson.get('pref_label').strip()
                                    form.partners[idx].partner_label.data = label
                                    tmp.setdefault('partners', []).append(json.dumps({'id': myjson.get('id'),
                                                                                      'label': label}))
                                    tmp.setdefault('fpartners', []).append('%s#%s' % (myjson.get('id'), label))
                            except AttributeError as e:
                                logging.error('ORGA: partner_id=%s: %s' % (partner.get('partner_id'), e))
                        elif partner.get('partner_label'):
                            tmp.setdefault('partners', []).append(partner.get('partner_label'))
                            tmp.setdefault('fpartners', []).append(partner.get('partner_label'))

    # save record to index
    try:
        logging.info('%s vs. %s' % (id, form.data.get('id')))
        if id != form.data.get('id'):
            delete_group_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                     application=secrets.SOLR_APP, core='group', del_id=id)
            delete_group_solr.delete()
            form.same_as.append_entry(id)
            tmp.setdefault('id', form.data.get('id'))
            tmp.setdefault('same_as', []).append(id)

            id = form.data.get('id')
        else:
            tmp.setdefault('id', id)
        # build json
        wtf_json = json.dumps(form.data)
        tmp.setdefault('wtf_json', wtf_json)
        # logging.info(tmp)
        groups_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                           application=secrets.SOLR_APP, core='group', data=[tmp])
        groups_solr.update()
    except AttributeError as e:
        logging.error(e)

    same_as = form.data.get('same_as')
    # logging.info('same_as: %s' % same_as)

    # add links to related entities
    if relitems:
        # logging.debug('parents: %s' % parents)
        for parent_id in parents:
            # search record
            query = 'id:%s' % parent_id
            edit_orga_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                  application=secrets.SOLR_APP, core='organisation', query=query)
            edit_orga_solr.request()
            # load orga in form and modify changeDate
            if len(edit_orga_solr.results) > 0:
                # lock record
                lock_orga_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                      application=secrets.SOLR_APP, core='organisation',
                                      data=[{'id': parent_id, 'locked': {'set': 'true'}}])
                lock_orga_solr.update()
                # edit
                try:
                    thedata = json.loads(edit_orga_solr.results[0].get('wtf_json'))
                    form = OrgaAdminForm.from_json(thedata)
                    # add child to form if not exists
                    exists = False
                    for child in form.data.get('children'):
                        # logging.info('%s == %s ?' % (child.get('child_id'), id))
                        if child.get('child_id') == id:
                            exists = True
                            break
                        elif child.get('child_id') in same_as:
                            exists = True
                            break
                    if not exists:
                        try:
                            childform = ChildForm()
                            childform.child_id.data = id
                            form.children.append_entry(childform.data)
                            form.changed.data = timestamp()
                            # save record
                            orga2solr(form, action='update', relitems=False)
                        except AttributeError as e:
                            logging.error('linking from %s: %s' % (parent_id, str(e)))
                    else:
                        # possibly rewrite label
                        form.changed.data = timestamp()
                        orga2solr(form, action='update', relitems=False)
                except TypeError as e:
                    logging.error(e)
                    logging.error('thedata: %s' % edit_orga_solr.results[0].get('wtf_json'))
                # unlock record
                unlock_orga_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                        application=secrets.SOLR_APP, core='organisation',
                                        data=[{'id': parent_id, 'locked': {'set': 'false'}}])
                unlock_orga_solr.update()
            else:
                edit_group_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                       application=secrets.SOLR_APP, core='group', query=query)
                edit_group_solr.request()
                # load group in form and modify changeDate
                if len(edit_group_solr.results) > 0:
                    # lock record
                    lock_group_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                           application=secrets.SOLR_APP, core='group',
                                           data=[{'id': parent_id, 'locked': {'set': 'true'}}])
                    lock_group_solr.update()
                    # edit
                    try:
                        thedata = json.loads(edit_group_solr.results[0].get('wtf_json'))
                        form = GroupAdminForm.from_json(thedata)
                        # add child to form if not exists
                        exists = False
                        for child in form.data.get('children'):
                            # logging.info('%s == %s ?' % (child.get('child_id'), id))
                            if child.get('child_id') == id:
                                exists = True
                                break
                            elif child.get('child_id') in same_as:
                                exists = True
                                break
                        if not exists:
                            try:
                                childform = ChildForm()
                                childform.child_id.data = id
                                form.children.append_entry(childform.data)
                                form.changed.data = timestamp()
                                # save record
                                group2solr(form, action='update', relitems=False)
                            except AttributeError as e:
                                logging.error('linking from %s: %s' % (parent_id, str(e)))
                        else:
                            # possibly rewrite label
                            form.changed.data = timestamp()
                            group2solr(form, action='update', relitems=False)
                    except TypeError as e:
                        logging.error(e)
                        logging.error('thedata: %s' % edit_group_solr.results[0].get('wtf_json'))
                    # unlock record
                    unlock_group_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                             application=secrets.SOLR_APP, core='group',
                                             data=[{'id': parent_id, 'locked': {'set': 'false'}}])
                    unlock_group_solr.update()
                else:
                    logging.info('Currently there is no record for parent_id %s!' % parent_id)

        # logging.debug('children: %s' % children)
        for child_id in children:
            # search record
            edit_group_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                   application=secrets.SOLR_APP, core='group', query='id:%s' % child_id)
            edit_group_solr.request()
            # load orga in form and modify changeDate
            if len(edit_group_solr.results) > 0:
                # lock record
                lock_group_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                       application=secrets.SOLR_APP, core='group',
                                       data=[{'id': child_id, 'locked': {'set': 'true'}}])
                lock_group_solr.update()
                # edit
                try:
                    thedata = json.loads(edit_group_solr.results[0].get('wtf_json'))
                    form = GroupAdminForm.from_json(thedata)
                    # add parent to form if not exists
                    if not form.data.get('parent'):
                        try:
                            parentform = ParentForm()
                            parentform.parent_id = id
                            form.parent.append_entry(parentform.data)
                            form.changed.data = timestamp()
                            # save record
                            group2solr(form, action='update', relitems=False)
                        except AttributeError as e:
                            logging.error('linking from %s: %s' % (parent_id, str(e)))
                    else:
                        try:
                            form.parent[0].parent_id = id
                            form.changed.data = timestamp()
                            # save record
                            group2solr(form, action='update', relitems=False)
                        except AttributeError as e:
                            logging.error('ERROR linking from %s: %s' % (parent_id, str(e)))
                except TypeError as e:
                    logging.error(e)
                    logging.error('thedata: %s' % edit_group_solr.results[0].get('wtf_json'))
                # unlock record
                unlock_group_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                         application=secrets.SOLR_APP, core='group',
                                         data=[{'id': child_id, 'locked': {'set': 'false'}}])
                unlock_group_solr.update()
            else:
                logging.info('Currently there is no record for parent_id %s!' % parent_id)

        # logging.debug('partners: %s' % partners)
        for partner_id in partners:
            # search record
            query = 'id:%s' % partner_id
            edit_orga_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                  application=secrets.SOLR_APP, core='organisation', query=query)
            edit_orga_solr.request()
            # load orga in form and modify changeDate
            if len(edit_orga_solr.results) > 0:
                # lock record
                lock_orga_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                      application=secrets.SOLR_APP, core='organisation',
                                      data=[{'id': partner_id, 'locked': {'set': 'true'}}])
                lock_orga_solr.update()
                # edit
                try:
                    thedata = json.loads(edit_orga_solr.results[0].get('wtf_json'))
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
                        try:
                            projectmemberform = ProjectMemberForm()
                            projectmemberform.project_id.data = id
                            form.projects.append_entry(projectmemberform.data)
                            form.changed.data = timestamp()
                            # save record
                            orga2solr(form, action='update', relitems=False)
                        except AttributeError as e:
                            logging.error('ERROR linking from %s: %s' % (partner_id, str(e)))
                    else:
                        # possibly rewrite label
                        form.changed.data = timestamp()
                        orga2solr(form, action='update', relitems=False)
                except TypeError as e:
                    logging.error(e)
                    logging.error('thedata: %s' % edit_orga_solr.results[0].get('wtf_json'))
                # unlock record
                unlock_orga_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                        application=secrets.SOLR_APP, core='organisation',
                                        data=[{'id': partner_id, 'locked': {'set': 'false'}}])
                unlock_orga_solr.update()
            else:
                logging.info('Currently there is no record for partner_id %s!' % partner_id)

        # store work records again
        works_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                          application=secrets.SOLR_APP, core='hb2',
                          query='group_id:%s' % id, facet=False, rows=500000)
        works_solr.request()

        for work in works_solr.results:
            # lock record
            lock_work_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                  application=secrets.SOLR_APP, core='hb2',
                                  data=[{'id': work.get('id'), 'locked': {'set': 'true'}}])
            lock_work_solr.update()

            # edit
            try:
                thedata = json.loads(work.get('wtf_json'))
                form = display_vocabularies.PUBTYPE2FORM.get(thedata.get('pubtype')).from_json(thedata)
                form.changed.data = timestamp()
                record2solr(form, action='update')
            except TypeError as e:
                logging.error(e)
                logging.error('thedata: %s' % work.get('wtf_json'))

            # unlock record
            unlock_work_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                    application=secrets.SOLR_APP, core='hb2',
                                    data=[{'id': work.get('id'), 'locked': {'set': 'false'}}])
            unlock_work_solr.update()

        # store person records again
        persons_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                            application=secrets.SOLR_APP, core='person',
                            query='group_id:%s' % id, facet=False, rows=500000)
        persons_solr.request()

        for person in persons_solr.results:
            # lock record
            lock_person_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                    application=secrets.SOLR_APP, core='person',
                                    data=[{'id': person.get('id'), 'locked': {'set': 'true'}}])
            lock_person_solr.update()

            # edit
            try:
                thedata = json.loads(person.get('wtf_json'))
                form = PersonAdminForm.from_json(thedata)
                form.changed.data = timestamp()
                person2solr(form, action='update')
            except TypeError as e:
                logging.error(e)
                logging.error('thedata: %s' % person.get('wtf_json'))

            # unlock record
            unlock_person_solr = Solr(host=secrets.SOLR_HOST, port=secrets.SOLR_PORT,
                                      application=secrets.SOLR_APP, core='person',
                                      data=[{'id': person.get('id'), 'locked': {'set': 'false'}}])
            unlock_person_solr.update()

    return id, message

