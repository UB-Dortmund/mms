import datetime
import logging
import uuid

import rdflib
import simplejson as json

try:
    import app_secrets
    import local_app_secrets as secrets
except ImportError:
    import app_secrets

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)-4s %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S',
                    )

# TODO read redsys-export, split into entity types
filename = ''
if secrets.CATALOG == 'Ruhr-Universität Bochum':
    filename = '2016-06-14.dump.rub.pretty.json'
elif secrets.CATALOG == 'Technische Universität Dortmund':
    filename = '2016-06-14.dump.tudo.pretty.json'

fr = open(secrets.SOURCE_DIR + filename, 'r', encoding="utf8")
thedata = json.loads(fr.read())
fr.close()

orga_data = []
person_data = []

for record in thedata:
    # logging.info(record)
    if record.get('model') == 'personen.orga':
        orga_data.append(record)
    if record.get('model') == 'personen.person':
        person_data.append(record)

# save memory
thedata = None

# TODO processing
more_parents = {}
parents = {}
orgas = {}
persons = []

prefix = ''
pk2gnd = {}

if secrets.CATALOG == 'Ruhr-Universität Bochum':

    prefix = 'RUB'
    # TODO orgas
    # hierarchische Struktur:
    # * Fakultät (ist ÜO zu) Fachgebiet (ist ÜO zu) Institution
    # * es gibt immer fakultät, immer institut, nicht immer fachgebiet
    # gnd und pk(=kostenstelle) gehören zu Institution
    # "alle" Institutionen haben eine GND (ggf. haben mehrere Institutionen dieselbe GND, aber unterschiedliche
    #   Kostenstellen >> mehrere Datensätze mit gleicher ID >> Herausforderung bei GND als Primärschlüssel in HB2)
    # Es gibt keine Datensätze in der HB1 zu den ÜO.
    #
    # TODO Verfahren des Import in die HB2:
    # * Erzeuge für jeden Datensatz eine Entität in der HB2.
    # * Ermittle dabei deduplizierte Listen zu den beiden ÜO-Ebenen
    # * Erzeuge zu den Einträgen in diesen Listen jeweils eigene HB2-Orga-Entitäten
    # * Verknüpfe diese zu einer "echten" Hierarchie

    for orga in orga_data:
        if orga.get('fields').get('fakultaet') and len(orga.get('fields').get('fakultaet')) > 0:
            hb2_more_parent = {}
            hb2_more_parent.setdefault('editorial_status', 'imported')
            hb2_more_parent.setdefault('created', str(datetime.datetime.now()))
            hb2_more_parent.setdefault('changed', str(datetime.datetime.now()))
            hb2_more_parent.setdefault('catalog', []).append(secrets.CATALOG)
            hb2_more_parent.setdefault('owner', []).append(secrets.contact_mail)
            hb2_more_parent.setdefault('id', str(uuid.uuid4()))
            hb2_more_parent.setdefault('pref_label', orga.get('fields').get('fakultaet'))
            orgas.setdefault(orga.get('fields').get('fakultaet'), hb2_more_parent)

    logging.info('orgas: %s' % len(orgas))

    for orga in orga_data:
        if orga.get('fields').get('fachgebiet') and len(orga.get('fields').get('fachgebiet')) > 0:
            hb2_parent = {}
            hb2_parent.setdefault('editorial_status', 'imported')
            hb2_parent.setdefault('created', str(datetime.datetime.now()))
            hb2_parent.setdefault('changed', str(datetime.datetime.now()))
            hb2_parent.setdefault('catalog', []).append(secrets.CATALOG)
            hb2_parent.setdefault('owner', []).append(secrets.contact_mail)
            hb2_parent.setdefault('id', str(uuid.uuid4()))
            hb2_parent.setdefault('pref_label', orga.get('fields').get('fachgebiet'))
            # TODO Link to parent
            if orga.get('fields').get('fakultaet') and len(orga.get('fields').get('fakultaet')) > 0:
                hb2_parent.setdefault('parent_id', orgas.get(orga.get('fields').get('fakultaet')).get('id'))
                hb2_parent.setdefault('parent_label', orgas.get(orga.get('fields').get('fakultaet')).get('pref_label'))
            orgas.setdefault(orga.get('fields').get('fachgebiet'), hb2_parent)

    logging.info('orgas: %s' % len(orgas))

    for orga in orga_data:
        hb2_orga = {}
        hb2_orga.setdefault('editorial_status', 'imported')
        hb2_orga.setdefault('created', str(datetime.datetime.now()))
        hb2_orga.setdefault('changed', str(datetime.datetime.now()))
        hb2_orga.setdefault('catalog', []).append(secrets.CATALOG)
        hb2_orga.setdefault('owner', []).append(secrets.contact_mail)

        if orga.get('fields').get('gnd') and len(orga.get('fields').get('gnd')) > 0:

            pk2gnd.setdefault('%s%s' % (prefix, orga.get('pk')), orga.get('fields').get('gnd'))

            if orga.get('fields').get('gnd') in orgas.keys():
                hb2_orga.setdefault('id', '%s%s' % (prefix, orga.get('pk')))
                hb2_orga.setdefault('dwid', []).append('%s%s' % (prefix, orga.get('pk')))
                hb2_orga.setdefault('gnd', orga.get('fields').get('gnd'))
                # TODO add pk to record with gnd as id
                orgas.get(orga.get('fields').get('gnd')).get('dwid').append('%s%s' % (prefix, orga.get('pk')))
            else:
                hb2_orga.setdefault('id', orga.get('fields').get('gnd'))
                hb2_orga.setdefault('gnd', orga.get('fields').get('gnd'))
                if orga.get('pk'):
                    hb2_orga.setdefault('dwid', []).append('%s%s' % (prefix, orga.get('pk')))
        elif orga.get('pk'):
            hb2_orga.setdefault('id', '%s%s' % (prefix, orga.get('pk')))
            hb2_orga.setdefault('dwid', []).append('%s%s' % (prefix, orga.get('pk')))
        else:
            hb2_orga.setdefault('id', str(uuid.uuid4()))

        if orga.get('fields').get('institut') and len(orga.get('fields').get('institut')) > 0:
            hb2_orga.setdefault('pref_label', orga.get('fields').get('institut'))
            # TODO Link to parent
            if orga.get('fields').get('fachgebiet') and len(orga.get('fields').get('fachgebiet')) > 0:
                hb2_orga.setdefault('parent_id', orgas.get(orga.get('fields').get('fachgebiet')).get('id'))
                hb2_orga.setdefault('parent_label', orgas.get(orga.get('fields').get('fachgebiet')).get('pref_label'))
            elif orga.get('fields').get('fakultaet') and len(orga.get('fields').get('fakultaet')) > 0:
                hb2_orga.setdefault('parent_id', orgas.get(orga.get('fields').get('fakultaet')).get('id'))
                hb2_orga.setdefault('parent_label', orgas.get(orga.get('fields').get('fakultaet')).get('pref_label'))

        orgas.setdefault(hb2_orga.get('id'), hb2_orga)

    logging.info('orgas: %s' % len(orgas))

    orga_data = None

elif secrets.CATALOG == 'Technische Universität Dortmund':

    prefix = 'TUDO'

    # TODO read labels from orga_data
    edited_labels = {}
    for orga in orga_data:
        if orga.get('fields').get('institut') and len(orga.get('fields').get('institut')) > 0:
            edited_labels.setdefault('%s%s' % (prefix, orga.get('pk')), orga.get('fields').get('institut'))

    # TODO read parents rdf
    graph = rdflib.Graph()
    graph.load(secrets.SOURCE_DIR + '2016-07-11_based_on_2013-03-21_orga.ttl', format='turtle')

    logging.info('Triples in graph before add: %s' % len(graph))

    parent_links = {}
    for statement in graph:
        if 'hasUnit' in statement[1]:
            # logging.info('subject: %s' % statement[0])
            # logging.info('object: %s' % statement[2])
            id = ''
            if str(statement[0]).split('/orga/')[1].startswith('9'):
                id = '%s%s' % (prefix, str(statement[0]).split('/orga/')[1])
            else:
                id = '%s' % str(statement[0]).split('/orga/')[1]
            parent_links.setdefault('%s%s' % (prefix, str(statement[2]).split('/orga/')[1]), id)

    cnt = 0

    for subject in graph.subjects():

        if '/orga/' in subject:

            hb2_parent = {}
            hb2_parent.setdefault('editorial_status', 'imported')
            hb2_parent.setdefault('created', str(datetime.datetime.now()))
            hb2_parent.setdefault('changed', str(datetime.datetime.now()))
            hb2_parent.setdefault('catalog', []).append(secrets.CATALOG)
            hb2_parent.setdefault('owner', []).append(secrets.contact_mail)

            if str(subject).split('/orga/')[1].startswith('9'):
                hb2_parent.setdefault('id', '%s%s' % (prefix, str(subject).split('/orga/')[1]))
                hb2_parent.setdefault('dwid', '%s%s' % (prefix, str(subject).split('/orga/')[1]))
            else:
                hb2_parent.setdefault('id', '%s' % str(subject).split('/orga/')[1])

            if hb2_parent.get('id') in edited_labels.keys():
                hb2_parent.setdefault('pref_label', edited_labels.get(hb2_parent.get('id')))
            else:
                for po in graph.predicate_objects(subject=subject):
                    if 'prefLabel' in po[0] and not str(po[1]).startswith('9'):
                        hb2_parent.setdefault('pref_label', '%s' % str(po[1]))

            if hb2_parent.get('id') in parent_links.keys():
                hb2_parent.setdefault('parent_id', parent_links.get(hb2_parent.get('id')))

            if hb2_parent.get('pref_label'):
                if hb2_parent.get('id') not in orgas.keys():
                    orgas.setdefault(hb2_parent.get('id'), hb2_parent)

            if hb2_parent.get('pref_label') and hb2_parent.get('id') not in orgas.keys():
                orgas.setdefault(hb2_parent.get('id'), hb2_parent)

    logging.info('subjects: %s' % cnt)
    logging.info('orgas after subjects: %s' % len(orgas))

    graph.close()

    for orga in orga_data:
        hb2_orga = {}
        hb2_orga.setdefault('editorial_status', 'imported')
        hb2_orga.setdefault('created', str(datetime.datetime.now()))
        hb2_orga.setdefault('changed', str(datetime.datetime.now()))
        hb2_orga.setdefault('catalog', []).append(secrets.CATALOG)
        hb2_orga.setdefault('owner', []).append(secrets.contact_mail)

        if orga.get('pk'):
            hb2_orga.setdefault('id', '%s%s' % (prefix, orga.get('pk')))
            hb2_orga.setdefault('dwid', []).append('%s%s' % (prefix, orga.get('pk')))
        else:
            hb2_orga.setdefault('id', str(uuid.uuid4()))

        if orga.get('fields').get('institut') and len(orga.get('fields').get('institut')) > 0:
            hb2_orga.setdefault('pref_label', orga.get('fields').get('institut'))
            # TODO Link to parent
            if orga.get('fields').get('fakultaet') and len(orga.get('fields').get('fakultaet')) > 0:
                hb2_orga.setdefault('parent_label', orga.get('fields').get('fakultaet'))

        if hb2_orga.get('id') != '78912345' and hb2_orga.get('id') != 'TUDO99999':
            if hb2_orga.get('id') not in orgas.keys():
                orgas.setdefault(hb2_orga.get('id'), hb2_orga)
                logging.info('id not in ttl-orgas: %s' % hb2_orga.get('id'))

    logging.info('orgas: %s' % len(orgas))

else:
    logging.info('ERROR')

# TODO persons
for person in person_data:
    hb2_person = {}
    hb2_person.setdefault('editorial_status', 'imported')
    hb2_person.setdefault('created', str(datetime.datetime.now()))
    hb2_person.setdefault('changed', str(datetime.datetime.now()))
    hb2_person.setdefault('catalog', []).append(secrets.CATALOG)
    hb2_person.setdefault('owner', []).append(secrets.contact_mail)

    if prefix == 'RUB':
        hb2_person.setdefault('rubi', True)
        hb2_person.setdefault('tudo', False)
    elif prefix == 'TUDO':
        hb2_person.setdefault('tudo', True)
        hb2_person.setdefault('rubi', False)

    if person.get('fields').get('pndid') and len(person.get('fields').get('pndid')) > 0:
        hb2_person.setdefault('id', person.get('fields').get('pndid'))
        hb2_person.setdefault('gnd', person.get('fields').get('pndid'))
    elif person.get('fields').get('uvid') and len(person.get('fields').get('uvid')) > 0:
        hb2_person.setdefault('id', '%s%s' % (prefix, person.get('fields').get('uvid')))
    else:
        hb2_person.setdefault('id', str(uuid.uuid4()))

    if person.get('fields').get('uvid') and len(person.get('fields').get('uvid')) > 0:
        hb2_person.setdefault('dwid', '%s%s' % (prefix, person.get('fields').get('uvid')))

    if person.get('fields').get('orcid') and len(person.get('fields').get('orcid')) > 0:
        hb2_person.setdefault('orcid', person.get('fields').get('orcid'))

    if person.get('fields').get('zugehoerigkeit') and len(person.get('fields').get('zugehoerigkeit')) > 0:
        for affiliation in person.get('fields').get('zugehoerigkeit'):
            if affiliation == '99999':
                continue
            elif affiliation == '16039348-6':
                orga = {}
                orga.setdefault('organisation_id', affiliation)
                orga.setdefault('label', 'Technische Universität Dortmund')
                hb2_person.setdefault('affiliation', []).append(orga)
            else:
                orga = {}
                if '%s%s' % (prefix, affiliation) in pk2gnd.keys():
                    orga.setdefault('organisation_id', pk2gnd.get('%s%s' % (prefix, affiliation)))
                    orga.setdefault('label', orgas.get(pk2gnd.get('%s%s' % (prefix, affiliation))).get('pref_label'))
                else:
                    orga.setdefault('organisation_id', '%s%s' % (prefix, affiliation))
                    try:
                        orga.setdefault('label', orgas.get('%s%s' % (prefix, affiliation)).get('pref_label'))
                    except AttributeError as e:
                        logging.error(e)
                        logging.error('%s%s' % (prefix, affiliation))
                hb2_person.setdefault('affiliation', []).append(orga)

    if person.get('fields').get('email') and len(person.get('fields').get('email')) > 0:
        hb2_person.setdefault('email', person.get('fields').get('email'))

    if person.get('fields').get('nachnamen') and person.get('fields').get('vornamen') and len(person.get('fields').get('nachnamen')) > 0 and len(person.get('fields').get('vornamen')) > 0:
        hb2_person.setdefault('name', '%s, %s' % (person.get('fields').get('nachnamen'), person.get('fields').get('vornamen')))

    if person.get('fields').get('anrede') and len(person.get('fields').get('anrede')) > 0:
        if person.get('fields').get('salutation') == 'f':
            hb2_person.setdefault('email', 'f')
        elif person.get('fields').get('salutation') == 'h':
            hb2_person.setdefault('email', 'h')

    if person.get('fields').get('alumnus'):
        hb2_person.setdefault('status', []).append('alumnus')

    if person.get('fields').get('wissenschaftler'):
        hb2_person.setdefault('status', []).append('official')

    if person.get('fields').get('prof'):
        hb2_person.setdefault('status', []).append('professor')

    if person.get('fields').get('pi'):
        hb2_person.setdefault('status', []).append('principal_investigator')

    if person.get('fields').get('extern'):
        hb2_person.setdefault('status', []).append('external')

    if person.get('fields').get('nwbeamter'):
        hb2_person.setdefault('status', []).append('official_ns')

    if person.get('fields').get('tuv'):
        hb2_person.setdefault('status', []).append('tech_admin')

    if person.get('fields').get('lehrauftrag'):
        hb2_person.setdefault('status', []).append('assistant_lecturer')

    if person.get('fields').get('emeritus'):
        hb2_person.setdefault('status', []).append('emeritus')

    if person.get('fields').get('selbstangelegt'):
        hb2_person.setdefault('status', []).append('manually_added')

    if person.get('fields').get('doktorand'):
        hb2_person.setdefault('status', []).append('official')

    if person.get('fields').get('exini'):
        hb2_person.setdefault('status', []).append('ranking')

    if person.get('fields').get('daten') and len(person.get('fields').get('daten')) > 0:
        for issue in person.get('fields').get('daten'):
            if issue == 1927:
                hb2_person.setdefault('status', []).append('callcenter')

    if person.get('fields').get('notizen') and len(person.get('fields').get('notizen')) > 0:
        hb2_person.setdefault('note', person.get('fields').get('notizen').replace('\r', '').replace('\n', ''))

    if person.get('fields').get('lieferung') and len(person.get('fields').get('lieferung')) > 0:
        hb2_person.setdefault('data_supplied', person.get('fields').get('lieferung'))

    persons.append(hb2_person)


# output
# fo = open(secrets.RESULTS_DIR + 'orga.more_parents.json', 'w')
# fo.write(json.dumps(list(more_parents.values()), indent=4))
# fo.close()

# fo = open(secrets.RESULTS_DIR + 'orga.parents.json', 'w')
# fo.write(json.dumps(list(parents.values()), indent=4))
# fo.close()

fo = open(secrets.RESULTS_DIR + prefix + '/orga.json', 'w')
fo.write(json.dumps(list(orgas.values()), indent=4))
fo.close()

fo = open(secrets.RESULTS_DIR + prefix + '/person.json', 'w')
fo.write(json.dumps(persons, indent=4))
fo.close()

