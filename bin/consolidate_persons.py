# The MIT License
#
#  Copyright 2015 UB Bochum <bibliographie-ub@rub.de>.
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

import redis
import simplejson as json
from fuzzywuzzy import fuzz

from utils.solr_handler import Solr

try:
    import app_secrets
    import local_app_secrets as secrets
except ImportError:
    import app_secrets


# TODO: Deduplizierung nach Nachname, 1. Buchsctabe des Vornamens
# TODO: Vorname und Nachname sind gleich, aber GNDs unterschiedlich => Ist das ueberhaupt ein TODO?
# TODO: Nachname ist gleich und wenn Vorname in den Daten nur ein Buchstabe oder wenn echter Vorname, dann die
# ersten beiden Buchstaben vergleichen
results = []
new_titles = Solr(application=secrets.SOLR_APP, facet='false', rows=2000000,
                  fields=['pnd', 'id', 'title', 'pubtype', 'catalog'])
new_titles.request()

for doc in new_titles.results:
    # logging.info(doc)
    if doc.get('pnd'):
        catalog = 'tmp'
        if doc.get('catalog'):
            if 'Ruhr-Universität Bochum' in doc.get('catalog'):
                catalog = 'rub'
            elif 'Technische Universität Dortmund' in doc.get('catalog'):
                catalog = 'tudo'

        result = {'id': doc.get('id'), 'catalog': catalog, 'title': doc.get('title'), 'pubtype': doc.get('pubtype')}
        creators = []
        # TODO sobald es einen gibt mit len(ids) != 3 muss der Datensatz nicht betrachtet werden!
        is_relevant = True
        for gnd in doc.get('pnd'):
            ids = gnd.split('#')
            if len(ids) != 3:
                is_relevant = False
                break

        if is_relevant:
            for gnd in doc.get('pnd'):
                ids = gnd.split('#')
                if len(ids) == 3:  # Dummy-GND
                    person = ids[2]
                    creator = {}
                    creator.setdefault('name', person)
                    try:
                        lastname, firstname = person.split(', ')
                        firstnames = []
                        terms = []
                        if ' ' in firstname:
                            firstnames = firstname.split(' ')
                        else:
                            firstnames.append(firstname.replace('.', ''))
                        # logging.info('FIRSTNAMES: %s' % firstnames)
                        terms.append('name:%s~' % lastname)
                        for fn in firstnames:
                            terms.append('name:%s~' % fn)
                        # logging.info('1) ' + str(terms))
                        person_check = Solr(application=secrets.SOLR_APP, core='person', query='+AND+'.join(terms),
                                            facet='false')
                        person_check.request()
                        candidate_list = person_check.results
                        if person_check.count() > 0:
                            # logging.info('2) ' + str(candidate_list))
                            for candidates in candidate_list:
                                # for candidate in candidates.get('name'):
                                candidate = candidates.get('name')
                                # logging.info('3) ' + candidate)
                                if person == candidate:
                                    # logging.info('4) %s => %s' % (person, candidate))
                                    creator.setdefault('candidates', []).append(
                                        {'id': candidates.get('id'),
                                         'gnd': candidates.get('gnd'),
                                         'orcid': candidates.get('orcid'),
                                         'tudo': candidates.get('tudo'),
                                         'rubi': candidates.get('rubi'),
                                         'affiliation': candidates.get('affiliation'),
                                         'probability': 100,
                                         'name': candidate})

                                    creators.append(creator)
                        else:
                            recheck_solr = Solr(application=secrets.SOLR_APP, core='person', query='name:%s' % lastname,
                                                facet='false')
                            recheck_solr.request()
                            ln_candidates = recheck_solr.results
                            # logging.info('LASTNAME RESULTS: %s' % len(ln_candidates))
                            if recheck_solr.count() > 0:
                                for ln_candidate in ln_candidates:
                                    # logging.info('ln_candidate: %s' % ln_candidate)
                                    if len(firstnames[0]) > 2:
                                        probability = fuzz.ratio(person, ln_candidate.get('name'))
                                        creator.setdefault('candidates', []).append(
                                            {'id': ln_candidate.get('id'),
                                             'gnd': ln_candidate.get('gnd'),
                                             'orcid': ln_candidate.get('orcid'),
                                             'tudo': candidates.get('tudo'),
                                             'rubi': candidates.get('rubi'),
                                             'affiliation': ln_candidate.get('affiliation'),
                                             'probability': probability,
                                             'name': ln_candidate.get('name')})

                            else:
                                creator.setdefault('candidates', [])

                            creators.append(creator)

                    except TypeError:
                        logging.info('x) ' + str(doc.get('fperson')))
                        raise
                    except IndexError:
                        logging.info('y) %s not found' % person)
                    except ValueError:
                        pass

        if len(creators) > 0:
            result.setdefault('persons', creators)
            results.append(result)
    else:
        # logging.info(doc)
        # try:
        #     for person in doc.get('fperson'):
        #         person_check = Solr(core='person', query='name:%s' % person, facet='false', fuzzy='true')
        #         person_check.request()
        #         if person in person_check.results[0].get('name'):
        #             logging.info('2) %s => %s' % (person, person_check.results[0].get('name')))
        # except TypeError:
        #     logging.info('2) ' + str(doc.get('fperson')))
        # except IndexError:
        #     logging.info('2) %s not found' % person)
        pass
# logging.info(results)

# TODO for debug only
fo = open('../consolidate_persons.json', 'w')
fo.write(json.dumps(results, indent=4))
fo.close()

# TODO push results to redis
try:
    storage_consolidate_persons = redis.StrictRedis(
        host=secrets.REDIS_CONSOLIDATE_PERSONS_HOST,
        port=secrets.REDIS_CONSOLIDATE_PERSONS_PORT,
        db=secrets.REDIS_CONSOLIDATE_PERSONS_DB)

    # TODO Achtung! Nur alle Daten mit key=result.get('catalog') löschen, da hier noch persistente
    # "marked"-Daten kommen
    # TODO diese "marked"-Daten müssen (als JSON) extern gesichert werden!
    logging.info('Tasks still in pipeline: %s' % storage_consolidate_persons.dbsize())
    logging.info('Empty pipeline ...')
    storage_consolidate_persons.flushdb()
    logging.info('ok. Size of pipeline now %s' % storage_consolidate_persons.dbsize())

    logging.info('Push new tasks in pipeline ...')
    for result in results:
        storage_consolidate_persons.hset(result.get('catalog'), result.get('id'), result)

    logging.info('ok. Size of pipline now %s' % storage_consolidate_persons.dbsize())

except Exception as e:
    logging.error('REDIS ERROR: %s' % e)
