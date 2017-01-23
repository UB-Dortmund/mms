#!/usr/bin/env python
# encoding: utf-8

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
import datetime
import logging
import uuid
from os import listdir
from os.path import isfile, join

import simplejson as json
from lxml import etree

try:
    import app_secrets
    import local_app_secrets as secrets
except ImportError:
    import app_secrets

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)-4s %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S',
                    )

MODS_NAMESPACE = 'http://www.loc.gov/mods/v3'
OAI_DC_NAMESPACE = 'http://www.openarchives.org/OAI/2.0/oai_dc/'
DC_NAMESPACE = 'http://purl.org/dc/elements/1.1/'
DCTERMS_NAMESPACE = 'http://purl.org/dc/terms'
XLINK_NAMESPACE = 'http://www.w3.org/1999/xlink'
MODS = '{%s}' % MODS_NAMESPACE
OAI_DC = '{%s}' % OAI_DC_NAMESPACE
DC = '{%s}' % DC_NAMESPACE
DCTERMS = '{%s}' % DCTERMS_NAMESPACE
XLINK = '{%s}' % XLINK_NAMESPACE
# <oai_dc:dc xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.openarchives.org/OAI/2.0/oai_dc/ http://www.openarchives.org/OAI/2.0/oai_dc.xsd"><dc:type>info:eu-repo/semantics/article</dc:type>

NSMAP = {'m': MODS_NAMESPACE,
         'dcterms': DCTERMS_NAMESPACE,
         'xlink': XLINK_NAMESPACE
         }

OAI_MAP = {
    'oai_dc': OAI_DC_NAMESPACE,
    'dc': DC_NAMESPACE
}

FREQUENCY_MAP = {
    'Completely irregular': 'completely_irregular',
    'Annual': 'annual',
    'Quarterly': 'quarterly',
    'Semiannual': 'semiannual',
    'Monthly': 'monthly',
    'Bimonthly': 'bimonthly',
    'Three times a year': 'three_times_a_year',
    'Semimonthly': 'semimonthly',
    'Biannial': 'biennial',
    '15 issues a year': 'fifteen_issues_a_year',
    'Continuously updated': 'continuously_updated',
    'Daily': 'daily',
    'Semiweekly': 'semiweekly',
    'Three times a week': 'three_times_a_week',
    'Weekly': 'weekly',
    'Biweekly': 'biweekly',
    'Three times a month': 'three_times_a_month',
    'Triennial': 'triennial',
}

OLD_PUBTYPES_MAP = {
    'JournalArticle': 'ArticleJournal',
    'JournalArticleAbstract': 'ArticleJournal#abstract',
    'JournalArticleFestschrift': 'ArticleJournal#festschrift',
    'JournalArticleInterview': 'ArticleJournal#interview',
    'JournalArticleLexikonartikel': 'ArticleJournal#lexicon_article',
    'JournalArticleMeetingAbstract': 'ArticleJournal#meeting_abstract',
    'JournalArticlePoster': 'ArticleJournal#poster',
    'JournalArticlePosterAbstract': 'ArticleJournal#poster_abstract',
    'JournalArticlePredigt': 'ArticleJournal#sermon',
    'JournalArticleRezension': 'ArticleJournal#review',
    'JournalArticleVorwort': 'ArticleJournal#introduction',
    'Contribution': 'Chapter',
    'ContributionAbstract': 'Chapter#abstract',
    'ContributionFestschrift': 'Chapter#festschrift',
    'ContributionInterview': 'Chapter#interview',
    'ContributionLexikonartikel': 'Chapter#lexicon_article',
    'ContributionMeetingAbstract': 'Chapter#meeting_abstract',
    'ContributionPoster': 'Chapter#poster',
    'ContributionPosterAbstract': 'Chapter#poster_abstract',
    'ContributionPredigt': 'Chapter#sermon',
    'ContributionRezension': 'Chapter#review',
    'ContributionVorwort': 'Chapter#introduction',
    'ContributionNachwort': 'Chapter#afterword',
    'BookEdited': 'Collection',
    'BookEditedFestschrift': 'Collection#festschrift',
    'BookEditedMusikdruck': 'Collection#musikdruck',
    'Book': 'Monograph',
    'BookDissertation': 'Monograph#dissertation',
    'BookFestschrift': 'Monograph#festschrift',
    'BookHabilitation': 'Monograph#habilitation',
    'BookMusikdruck': 'Monograph#notated_music',
    'BookVorwort': 'Chapter#foreword',
    'BookNachwort': 'Chapter#afterword',
    'UnpublishedWork': 'Other#report',
    'UnpublishedWorkLexikonartikel': 'Other#report#article_article',
    'UnpublishedWorkFestschrift': 'Other#festschrift',
    'UnpublishedWorkPredigt': 'Other#sermon',
    'UnpublishedWorkVorlesungsskript': 'Other#lecture_notes',
    'UnpublishedWorkPoster': 'Other#poster',
    'UnpublishedWorkPosterAbstract': 'Other#poster_abstract',
    'UnpublishedWorkGutachten': 'Other#expert_opinion',
    'Patent': 'Patent',
    'Thesis': 'Thesis',
    'ThesisBachelorarbeit': 'Thesis#bachelor_thesis',
    'ThesisDiplomarbeit': 'Thesis#diploma_thesis',
    'ThesisDissertation': 'Thesis#dissertation',
    'ThesisFestschrift': 'Thesis#festschrift',
    'ThesisHabilitation': 'Thesis#habilitation',
    'ThesisMagisterarbeit': 'Thesis#magisterarbeit',
    'ThesisMasterarbeit': 'Thesis#masters_thesis',
    'ThesisErsteStaatsexamensarbeit': 'Thesis#first_state_examination',
    'ThesisZweiteStaatsexamensarbeit': 'Thesis#second_state_examination',
    'NewspaperArticle': 'ArticleNewspaper',
    'NewspaperArticleRezension': 'ArticleNewspaper#review',
    'AudioBook': 'AudioVideoDocument#audio_book',
    'AudioOrVideoDocument': 'AudioVideoDocument',
    'AudioOrVideoDocumentBilddatenbank': 'AudioVideoDocument#image_database',
    'AudioOrVideoDocumentBühnenwerk': 'AudioVideoDocument#dramatic_work',
    'AudioOrVideoDocumentInterview': 'AudioVideoDocument#interview',
    'ContributionInLegalCommentary': 'ChapterInLegalCommentary',
    'ContributionInLegalCommentaryLexikonartikel': 'ChapterInLegalCommentary#lexicon_article',
    'ConferenceProceedings': 'Conference',
    'ConferenceProceedingsFestschrift': 'Conference#festschrift',
    'CollectedWorks': 'Edition',
    'CollectedWorksFestschrift': 'Edition#festschrift',
    'CollectedWorksMusikdruck': 'Edition#notated_music',
    'InternetDocument': 'InternetDocument',
    'InternetDocumentAbstract': 'InternetDocument#abstract',
    'InternetDocumentHabilitation': 'Thesis#habilitation',
    'InternetDocumentPredigt': 'InternetDocument#sermon',
    'InternetDocumentInterview': 'InternetDocument#interview',
    'InternetDocumentLexikonartikel': 'InternetDocument#lexicon_article',
    'InternetDocumentMeetingAbstract': 'InternetDocument#meeting_abstract',
    'InternetDocumentPoster': 'InternetDocument#poster',
    'InternetDocumentPosterAbstract': 'InternetDocument#poster_abstract',
    'InternetDocumentRezension': 'InternetDocument#review',
    'Journal': 'Journal',
    'periodicalZeitschrift': 'Journal#',
    'Lecture': 'Lecture',
    'LectureAbstract': 'Lecture#abstract',
    'LectureMeetingAbstract': 'Lecture#meeting_abstract',
    'LegalCommentary': 'LegalCommentary',
    'PressRelease': 'PressRelease',
    'Broadcast': 'RadioTVProgram',
    'BroadcastInterview': 'RadioTVProgram#interview',
    'ComputerProgram': 'Software',
    'SpecialIssue': 'SpecialIssue',
    'SpecialIssueFestschrift': 'SpecialIssue#festschrift',
    'Standard': 'Standard',
    # TUDO Spezialitaeten :-(
    'BookPoster': 'Other#poster',
    'persiodicalSchriftenreihe': 'Series#',
    'periodicalSchriftenreihe': 'Series#',
    'periodical': 'Journal',
    'NewspaperArticleInterview': 'ArticleNewspaper#interview',
    'ThesisHabilitationsschrift': 'Thesis#second_state_examination',
    'ThesisStaatsarbeit': 'Thesis#first_state_examination',
    'ThesisZweiteStaatsexamsarbeit': 'Thesis#second_state_examination',
    'LecturePoster': 'Other#poster',
    'BookVorlesungsskript': 'Other#lecture_notes',
    'LectureVorlesungsskript': 'Other#lecture_notes',
    'JournalArticleISBN3-11-011362-7': 'ArticleJournal#',
    'JournalArticleText': 'ArticleJournal#',
    'JournalArticlePosterabstract': 'ArticleJournal#poster_abstract',
    'UnpublishedWorkBühnenwerk': 'Other#dramatic_work',
    'BookBühnenwerk': 'Other#dramatic_work',
    'UnpublishedWorkMusikwerk': 'Other#music',
    'BookMusikwerk': 'Other#music',
    'MusicAlbum': 'AudioVideoDocument',
    'MusicTrack': 'AudioVideoDocument',
    'Manuscript': 'Other',
    'BroadcastPredigt': 'AudioVideoDocument#sermon',
    'AudioOrVideoDocumentDrehbuch': 'Other#',
    'BroadcastDrehbuch': 'Other#',
    'RadioPlay': 'AudioVideoDocument',
    'InternetDocumentText': 'InternetDocument#',
    'BookEditedElektronischeRessource': 'Collection#',
}

SUBJECT_MAPS = {}
with open('mesh_map.json') as mesh_map:
    SUBJECT_MAPS.setdefault('mesh', json.load(mesh_map))

with open('mesh_map.json') as stw_map:
    SUBJECT_MAPS.setdefault('stw', json.load(stw_map))

def oai_elements(name, values):
    if values:
        tmp = []
        for value in values:
            elm = etree.Element('%s%s' % (DC, name), nsmap=OAI_MAP)
            elm.text = value.text
            tmp.append(elm)
        return tmp


def oai_valueURI(name, values):
    if values:
        tmp = []
        for value in values:
            elm = etree.Element('%s%s' % (DC, name), nsmap=OAI_MAP)
            elm.text = value.get('valueURI')
            tmp.append(elm)
        return tmp


def get_names(twig):
    names = []
    for name in twig:
        realname = ''
        family = ''
        first = ''
        nametype = ''
        namerole = ''
        nametype = name.attrib['type']
        pnd = ''

        try:
            pnd = name.attrib.get('valueURI').replace('http://d-nb.info/gnd/', '')
        except AttributeError:
            # logging.debug(twig.attrib.get('valueURI'))
            pass
        for part in name:
            if part.tag == '%snamePart' % MODS:
                if nametype == 'corporate':
                    realname = part.text
                if part.get('type') == 'family':
                    family = part.text
                if part.get('type') == 'given':
                    first = part.text

                if first != '':
                    realname = '%s, %s' % (family, first)
                else:
                    realname = family
                if nametype == 'corporate':
                    realname = part.text
            if part.tag == '%srole' % MODS:
                for role in part:
                    if role.tag == '%sroleTerm' % MODS:
                        namerole = role.text
        # logging.info([family, first, realname, nametype, namerole, pnd])
        names.append({'family': family, 'first': first, 'realname': realname, 'namerole': namerole, 'pnd': pnd,
                      'nametype': nametype})
    return names


def get_wtf_names(elems):
    wtf_pnames = []
    wtf_cnames = []
    for name in get_names(elems):
        if name.get('nametype') == 'personal':
            wtf_pnames.append(
                {'name': name.get('realname'), 'gnd': name.get('pnd'), 'orcid': '', 'role': name.get('namerole'),
                 'corresponding_author': False})
        else:
            wtf_cnames.append(
                {'name': name.get('realname'), 'gnd': name.get('pnd'), 'role': name.get('namerole'), 'isni': ''})

    return {'person': wtf_pnames}, {'corporation': wtf_cnames}


def get_csl_names(elems):
    csl_names = []
    for name in get_names(elems):
        csl_names.append({'given': name.get('first'), 'family': name.get('family')})

    return {'author': csl_names}


def get_solr_persons(elems):
    solr_persons = []
    solr_fpersons = []
    solr_spell = []
    for name in get_names(elems):
        solr_persons.append(name.get('realname'))
        solr_fpersons.append(name.get('realname'))
        solr_spell.append(name.get('realname'))

    return {'person': solr_persons, 'fperson': solr_fpersons, 'spell': solr_spell}


def get_solr_corporates(elems):
    solr_corporates = []
    solr_fcorporates = []
    for name in get_names(elems):
        solr_corporates.append(name.get('realname'))
        solr_fcorporates.append(name.get('realname'))

    return {'institution': solr_corporates, 'fcorporation': solr_fcorporates}


def get_wtf_issued(elems):
    issued = ''
    start = ''
    end = ''
    for date_issued in elems:
        if ' - ' in date_issued.text:
            tmp = date_issued.text.split(' - ')
            start = tmp[0].strip()
            end = tmp[1].strip()
            #logging.info({'startdate_conference': start, 'enddate_conference': end})
        else:
            issued = date_issued.text

    return {'issued': issued, 'startdate_conference': start, 'enddate_conference': end}


def get_wtf_date_application(elems):
    date_application = ''
    for date_other in elems:
        if len(date_other.text.strip()) == 4:
            date_application = '%s-01-01 00:00:00.001' % date_other.text
        elif len(date_other.text.strip()) == 7:
            date_application = '%s-01 00:00:00.001' % date_other.text
        else:
            date_application = '%s 00:00:00.001' % date_other.text

    return {'date_application': date_application}


def get_solr_issued(elems):
    date = '';
    fdate = None;
    date_boost = '';
    for issued in elems:
        date = issued.text.replace('[', '').replace(']', '').strip()
        if len(date.strip()) == 4:
            fdate = int(date)
            date_boost = '%s-01-01T00:00:00.001Z' % date
        elif len(date.strip()) == 7:
            fdate = int(date[0:4])
            date_boost = '%s-01T00:00:00.001Z' % date
        else:
            fdate = int(date[0:4])
            date_boost = '%sT00:00:00.001Z' % date

    return {'date': date, 'fdate': fdate, 'date_boost': date_boost}


def get_wtf_tocs(elems):
    wtf_tocs = []
    for toc in elems:
        tmp = {}
        uri = toc.get('%shref' % XLINK)
        # logging.info(uri)
        toc_text = toc.text
        # logging.info(toc_text)
        if toc_text:
            tmp.setdefault('toc', toc.text)
        if uri:
            tmp.setdefault('uri', uri)
        if tmp.get('toc') or tmp.get('uri'):
            wtf_tocs.append(tmp)
    # logging.info(wtf_tocs)
    return {'table_of_contents': wtf_tocs}


def get_wtf_hosts(elems):
    wtf_hosts = []
    has_title = False
    for host in elems:
        tmp = {}
        for item in host:
            if item.tag == '%stitleInfo' % MODS:
                has_title = True
            if item.tag == '%srecordInfo' % MODS:
                for info in item:
                    if info.tag == '%srecordIdentifier' % MODS:
                        tmp.setdefault('is_part_of', info.text)
                        # logging.info(tmp)
            if item.tag == '%sgenre' % MODS:
                if item.get('authority') == 'local':
                    tmp.setdefault('pubtype', OLD_PUBTYPES_MAP.get(item.text))
                    # logging.info(tmp)
            if item.tag == '%spart' % MODS:
                for part in item:
                    if part.tag == '%sdetail' % MODS:
                        if part.get('type') == 'volume':
                            for number in part:
                                tmp.setdefault('volume', number.text)
                                # logging.info(tmp)
                        if part.get('type') == 'issue':
                            for number in part:
                                tmp.setdefault('issue', number.text)
                                # logging.info(tmp)
                    if part.tag == '%sextent' % MODS:
                        for extent in part:
                            if extent.tag == '%slist' % MODS:
                                tmp.setdefault('page_first', str(extent.text).split("–")[0].replace('[','').replace(']',''))
                                if len(str(extent.text).split("–")) > 1:
                                    tmp.setdefault('page_last', str(extent.text).split("–")[1].replace('[','').replace(']',''))
                                    # logging.info(tmp)
        # logging.info('---')
        # logging.info(tmp)
        if has_title:
            if not tmp.get('pubtype'):
                tmp.setdefault('pubtype', 'Journal')
            if not tmp.get('volume'):
                tmp.setdefault('volume', '')
            if not tmp.get('issue'):
                tmp.setdefault('issue', '')
            if not tmp.get('is_part_of'):
                tmp.setdefault('is_part_of', str(uuid.uuid4()))
            # logging.info('hosts')
            # logging.info(tmp)
            wtf_hosts.append(tmp)

            get_wtf_parents(elems, tmp.get('is_part_of'), 'Journal')

    return {'is_part_of': wtf_hosts}


def get_wtf_parents(elems, id='', default_pubtype=''):
    for host in elems:
        tmp = {}
        tmp.setdefault('id', id)
        tmp.setdefault('ISSN', [])
        tmp.setdefault('ISBN', [])
        # logging.info(tmp)
        pubtype = ''
        subtype = ''
        relateditem = None
        names = []
        stw = []
        mesh = []
        keywords = []
        for item in host:
            if item.tag == '%stitleInfo' % MODS:
                for title in item:
                    if title.tag == '%stitle' % MODS:
                        tmp.setdefault('title', title.text)
                        # logging.info(tmp)
                    if title.tag == '%ssubTitle' % MODS:
                        tmp.setdefault('subtitle', title.text)
                        # logging.info(tmp)
            if item.tag == '%sgenre' % MODS:
                if item.get('authority') == 'local':
                    pubtype = item.text.replace(' ', '')
                    # logging.info(pubtype)
                if not item.get('authority'):
                    subtype = item.text.replace(' ', '')
                    # logging.info(subtype)
            if item.tag == '%sidentifier' % MODS:
                if item.get('type') == 'issn':
                    tmp.get('ISSN').append(item.text)
                    # logging.info(tmp)
                if item.get('type') == 'isbn':
                    tmp.get('ISBN').append(item.text)
                    # logging.info(tmp)
                if item.get('type') == 'doi':
                    tmp.setdefault('DOI', item.text)
                    # logging.info(tmp)
                if item.get('type') == 'pm':
                    tmp.setdefault('PMID', item.text)
                    # logging.info(tmp)
                if item.get('type') == 'urn':
                    tmp.setdefault('urn', item.text)
                    # logging.info(tmp)
                if item.get('type') == 'zdb':
                    tmp.setdefault('ZDBID', item.text)
                    # logging.info(tmp)
                if item.get('type') == 'local' and item.get('displayLabel') == 'HT-ID':
                    tmp.setdefault('hbz_id', item.text)
                    # logging.info(tmp)
            if item.tag == '%srecordInfo' % MODS:
                for info in item:
                    if info.tag == '%srecordCreationDate' % MODS:
                        if len(info.text.strip()) == 10:
                            tmp.setdefault('created', '%s 00:00:00.001' % info.text.strip())
                        else:
                            tmp.setdefault('created', info.text)
                            # logging.info(tmp)
                    if info.tag == '%srecordChangeDate' % MODS:
                        if len(info.text.strip()) == 10:
                            tmp.setdefault('changes', '%s 00:00:00.001' % info.text.strip())
                        else:
                            tmp.setdefault('changes', info.text)
                            # logging.info(tmp)
            if item.tag == '%sname' % MODS:
                names.append(item)
            if item.tag == '%stableOfContents' % MODS:
                tmp.setdefault(get_wtf_tocs(item))
            if item.tag == '%soriginInfo' % MODS:
                for origin in item:
                    if origin.tag == '%sdateIssued' % MODS:
                        tmp.setdefault('issued', origin.text)
                        # logging.info(tmp)
                    if origin.tag == '%spublisher' % MODS:
                        tmp.setdefault('publisher', origin.text)
                        # logging.info(tmp)
                    if origin.tag == '%splace' % MODS:
                        for place in origin:
                            if place.tag == '%splaceTerm' % MODS and place.get('type') == 'text':
                                tmp.setdefault('publisher_place', place.text)
                                # logging.info(tmp)
            if item.tag == '%slanguage' % MODS:
                for lang in item:
                    if lang.tag == '%slanguageTerm' % MODS and lang.get('type') == 'code' and lang.get(
                            'authority') == 'iso639-2b':
                        tmp.setdefault('language', lang.text)
                        # logging.info(tmp)
            if item.tag == '%sphysicalDescription' % MODS:
                for physDesc in item:
                    if physDesc.tag == '%sextent' % MODS:
                        tmp.setdefault('number_of_pages', physDesc.text)
                        # logging.info(tmp)
            if item.tag == '%ssubject' % MODS and item.get('authority') == 'stw':
                stw.append(item)
            if item.tag == '%ssubject' % MODS and item.get('authority') == 'mesh':
                mesh.append(item)
            if item.tag == '%ssubject' % MODS and not item.get('type') and not item.get('authority'):
                for topic in item:
                    keywords.append(topic.text)
            if item.tag == '%srelatedItem' % MODS:
                if item.get('type') == 'series':
                    relateditem = host
        old_pubtype = pubtype + subtype
        # logging.info(old_pubtype)
        if OLD_PUBTYPES_MAP.get(old_pubtype):

            if len(OLD_PUBTYPES_MAP.get(old_pubtype).split('#')) > 1:
                tmp.setdefault('pubtype', OLD_PUBTYPES_MAP.get(old_pubtype).split('#')[0])
                tmp.setdefault('subtype', OLD_PUBTYPES_MAP.get(old_pubtype).split('#')[1])
            else:
                tmp.setdefault('pubtype', OLD_PUBTYPES_MAP.get(old_pubtype))
        else:
            tmp.setdefault('pubtype', default_pubtype)
        # logging.info(names)
        names_wtf = get_wtf_names(names)
        if len(names_wtf[0].get('person')) > 0:
            tmp.setdefault('person', names_wtf[0].get('person'))
        if len(names_wtf[1].get('corporation')) > 0:
            tmp.setdefault('corporation', names_wtf[1].get('corporation'))
        if len(stw) > 0:
            tmp.setdefault(get_wtf_subject(stw))
        if len(mesh) > 0:
            tmp.setdefault(get_wtf_subject(mesh))
        if len(keywords) > 0:
            tmp.setdefault('keyword', keywords)
        if not tmp.get('created'):
            tmp.setdefault('created', str(datetime.datetime.now()))
        if not tmp.get('changed'):
            tmp.setdefault('changed', str(datetime.datetime.now()))
        tmp.setdefault('editorial_status', 'imported')
        tmp.setdefault('owner', ['daten.ub@tu-dortmund.de'])
        tmp.setdefault('catalog', [secrets.CATALOG])

        tmp_parents = []
        if relateditem is not None:
            tmp_series = []
            for series in relateditem:
                if series.tag == '%srelatedItem' % MODS:
                    tmp_s = {}
                    tmp_p = {}
                    for item in series:
                        if item.tag == '%stitleInfo' % MODS:
                            for title in item:
                                if title.tag == '%stitle' % MODS:
                                    tmp_p.setdefault('title', title.text)
                        if item.tag == '%srecordInfo' % MODS:
                            for info in item:
                                if info.tag == '%srecordIdentifier' % MODS:
                                    tmp_s.setdefault('is_part_of', info.text)
                                    tmp_p.setdefault('id', info.text)
                        if item.tag == '%spart' % MODS:
                            for part in item:
                                if part.tag == '%sdetail' % MODS:
                                    if part.get('type') == 'volume':
                                        for number in part:
                                            tmp_s.setdefault('volume', number.text)
                                    if part.get('type') == 'issue':
                                        for number in part:
                                            tmp_s.setdefault('issue', number.text)
                    tmp_s.setdefault('pubtype', 'Series')
                    tmp_p.setdefault('pubtype', 'Series')
                    if not tmp_s.get('is_part_of'):
                        tmp_s.setdefault('is_part_of', str(uuid.uuid4()))
                        tmp_p.setdefault('id', tmp_s.get('is_part_of'))
                    if not tmp_p.get('created'):
                        tmp_p.setdefault('created', str(datetime.datetime.now()))
                    if not tmp_p.get('changed'):
                        tmp_p.setdefault('changed', str(datetime.datetime.now()))
                    tmp_p.setdefault('editorial_status', 'imported')
                    tmp_p.setdefault('owner', ['daten.ub@tu-dortmund.de'])
                    tmp_p.setdefault('catalog', [secrets.CATALOG])
                    tmp_series.append(tmp_s)
                    more_parents.append(tmp_p)
            # logging.info(tmp_series)
            tmp.setdefault('is_part_of', tmp_series)

        # logging.info(tmp)
        parents.append(tmp)


def get_wtf_series(elems):
    wtf_series = []
    for host in elems:
        tmp = {}
        for item in host:
            if item.tag == '%stitleInfo' % MODS:
                for title in item:
                    if title.tag == '%stitle' % MODS:
                        tmp.setdefault('title', title.text)
            if item.tag == '%srecordInfo' % MODS:
                for info in item:
                    if info.tag == '%srecordIdentifier' % MODS:
                        tmp.setdefault('is_part_of', info.text)
            if item.tag == '%spart' % MODS:
                for part in item:
                    if part.tag == '%sdetail' % MODS:
                        if part.get('type') == 'volume':
                            for number in part:
                                tmp.setdefault('volume', number.text)
                        if part.get('type') == 'issue':
                            for number in part:
                                tmp.setdefault('issue', number.text)
                    if part.tag == '%sextent' % MODS:
                        for extent in part:
                            if extent.tag == '%slist' % MODS:
                                tmp.setdefault('page_first', str(extent.text).split("–")[0].replace('[','').replace(']',''))
                                tmp.setdefault('page_last', str(extent.text).split("–")[1].replace('[','').replace(']',''))
        tmp.setdefault('pubtype', 'Series')
        if not tmp.get('is_part_of'):
            tmp.setdefault('is_part_of', str(uuid.uuid4()))
        # logging.info('series')
        # logging.info(tmp)

        wtf_series.append(tmp)

        get_wtf_parents(elems, tmp.get('is_part_of'), 'Series')

    return {'is_part_of': wtf_series}


def get_wtf_subject(elems):
    wtf_subject = []
    authority = elems[0].get('authority')
    for subject in elems:
        tmp = {}
        tmp.setdefault('id', subject[0].text)
        tmp.setdefault('label', SUBJECT_MAPS.get(authority).get(subject[0].text))
        wtf_subject.append(tmp)

    return {'%s_subject' % authority: wtf_subject}


def get_wtf_abstract(elems):
    wtf_abstracts = []
    for abstract in elems:
        tmp = {}
        tmp.setdefault('content', abstract.text)
        if abstract.get('%shref' % XLINK):
            tmp.setdefault('address', abstract.get('%shref' % XLINK))
        tmp.setdefault('label', '')
        if abstract.get('lang'):
            tmp.setdefault('language', abstract.get('lang'))
        if abstract.get('shareable') == 'no':
            tmp.setdefault('shareable', False)
        else:
            tmp.setdefault('shareable', True)
        wtf_abstracts.append(tmp)
    return {'abstract': wtf_abstracts}


def get_new_pubtype(old_pubtype):
    new_pubtype = ''
    if OLD_PUBTYPES_MAP.get(old_pubtype.replace(' ', '')):
        new_pubtype = OLD_PUBTYPES_MAP.get(old_pubtype.replace(' ', ''))
    else:
        logging.info('ERROR old pubtype: ' + old_pubtype.replace(' ', ''))
    return new_pubtype


def get_wtf_affiliation_context(elems):
    contexts = []
    for context in elems:
        if secrets.CATALOG == 'Technische Universität Dortmund':
            contexts.append('Fakultät %s' % context.text)
        else:
            contexts.append(context.text)

    return {'affiliation_context': contexts}


def other_title(elems):
    other_titles = []
    for title in elems:
        other_titles.append({'other_title': title.text, 'language': ''})
    return {'other_title': other_titles}


def get_value(input):
    value = ''
    # logging.info(input)
    value = input
    return value


def doi2index(elems):
    doi = elems[0].text
    solr_doi = {}

    solr_doi.setdefault('doi', doi)

    # TODO: Handle all cases in which the DOI is the source for enrichment

    return solr_doi


def get_wtf_extent(elems):
    extent = elems[0].text
    wtf_extent = {}
    if ' : ' in extent:
        wtf_extent.setdefault('number_of_pages', extent.split(' : ')[0])
        wtf_extent.setdefault('additions', extent.split(' : ')[1])
    else:
        wtf_extent.setdefault('number_of_pages', extent)
    # logging.info('extent %s' % wtf_extent)
    return wtf_extent


try:
    CONVERTER_MAP = {
        "./m:abstract": {
            'wtf': get_wtf_abstract,
            'csl': lambda elems: {'abstract': elems[0].text},
            'solr': lambda elems: {'ro_abstract': get_value(elems[0].text)},
            'oai_dc': (oai_elements, 'abstract')
        },
        # "./m:accessCondition[@type='restriction on access']": lambda elem : {'': elem.text},
        # "./m:accessCondition[@type='use and reproduction']": lambda elem : {'': elem.text},
        "./m:classification[@authority='international patent classification']": {
            'wtf': lambda elems: {'bibliographic_ipc': elems[0].text},
            'solr': lambda elems: {'number': elems[0].text},
        },
        # TUDO Zuordnung zur Affiliation
        "./m:classification[not(@authority)]": {
            'wtf': get_wtf_affiliation_context,
            # 'solr': lambda elems: {'number': elems[0].text},
        },
        # "./m:extension": lambda elem : {'': elem.text},
        "./m:extension/dcterms:bibliographicCitation": {
            'wtf': lambda elem: {'bibliographicCitation': elem[0].text},
        },
        "./m:frequency[@authority='marcfrequency']": {
            'wtf': lambda elems: {'frequency': FREQUENCY_MAP.get(elems[0].text)}},
        # "./m:genre": lambda elem : {'': elem.text},
        "./m:genre[@authority='dct' and @valueURI='http://purl.org/dc/dcmitype/Collection']": {
            'oai_dc': (oai_valueURI, 'type')},
        "./m:genre[@authority='dct' and @valueURI='http://purl.org/dc/dcmitype/Image']": {
            'oai_dc': (oai_valueURI, 'type')},
        "./m:genre[@authority='dct' and @valueURI='http://purl.org/dc/dcmitype/Software']": {
            'oai_dc': (oai_valueURI, 'type')},
        "./m:genre[@authority='dct' and @valueURI='http://purl.org/dc/dcmitype/Sound']": {
            'oai_dc': (oai_valueURI, 'type')},
        "./m:genre[@authority='dct' and @valueURI='http://purl.org/dc/dcmitype/Text']": {
            'oai_dc': (oai_valueURI, 'type')},
        "./m:genre[@authority='local']": {
            'wtf': lambda elem: {'pubtype': get_new_pubtype(elem[0].text)} if not record.xpath(
                "./m:genre[not(@authority) and not(@valueURI)]", namespaces=NSMAP) else
            {'pubtype': get_new_pubtype('%s%s' % (elem[0].text,
                                                  record.xpath("./m:genre[not(@authority) and not(@valueURI)]",
                                                               namespaces=NSMAP)[0].text)).split('#')[0], 'subtype':
                 get_new_pubtype('%s%s' % (elem[0].text, record.xpath("./m:genre[not(@authority) and not(@valueURI)]",
                                                                      namespaces=NSMAP)[0].text)).split('#')[1]},
        },
        # "./m:genre[@authority='marcgt']": lambda elem : {'': elem.text},
        "./m:genre[@valueURI='http://purl.org/info:eu-repo/semantics/article']": {'oai_dc': (oai_valueURI, 'type')},
        "./m:genre[@valueURI='http://purl.org/info:eu-repo/semantics/bachelorThesis']": {
            'oai_dc': (oai_valueURI, 'type')},
        "./m:genre[@valueURI='http://purl.org/info:eu-repo/semantics/book']": {'oai_dc': (oai_valueURI, 'type')},
        "./m:genre[@valueURI='http://purl.org/info:eu-repo/semantics/bookPart']": {'oai_dc': (oai_valueURI, 'type')},
        "./m:genre[@valueURI='http://purl.org/info:eu-repo/semantics/conferencePoster']": {
            'oai_dc': (oai_valueURI, 'type')},
        "./m:genre[@valueURI='http://purl.org/info:eu-repo/semantics/conferenceProceedings']": {
            'oai_dc': (oai_valueURI, 'type')},
        "./m:genre[@valueURI='http://purl.org/info:eu-repo/semantics/doctoralThesis']": {
            'oai_dc': (oai_valueURI, 'type')},
        "./m:genre[@valueURI='http://purl.org/info:eu-repo/semantics/lecture']": {'oai_dc': (oai_valueURI, 'type')},
        "./m:genre[@valueURI='http://purl.org/info:eu-repo/semantics/masterThesis']": {
            'oai_dc': (oai_valueURI, 'type')},
        "./m:genre[@valueURI='http://purl.org/info:eu-repo/semantics/other']": {'oai_dc': (oai_valueURI, 'type')},
        "./m:genre[@valueURI='http://purl.org/info:eu-repo/semantics/patent']": {'oai_dc': (oai_valueURI, 'type')},
        "./m:genre[@valueURI='http://purl.org/info:eu-repo/semantics/report']": {'oai_dc': (oai_valueURI, 'type')},
        "./m:genre[@valueURI='http://purl.org/info:eu-repo/semantics/review']": {'oai_dc': (oai_valueURI, 'type')},
        "./m:genre[@valueURI='http://purl.org/info:eu-repo/semantics/studentThesis']": {
            'oai_dc': (oai_valueURI, 'type')},
        "./m:identifier[@displayLabel='Anmeldenummer']": {
            'wtf': lambda elems: {'application_number': [elem.text for elem in elems]},
            'solr': lambda elems: {'number': [elem.text for elem in elems]},
        },
        "./m:identifier[@displayLabel='Veröffentlichungs-Nr.']": {
            'wtf': lambda elems: {'patent_number': elems[0].text},
            'solr': lambda elems: {'number': elems[0].text},
        },
        "./m:identifier[@type='doi']": {
            'wtf': lambda elems: {'DOI': elems[0].text},
            'csl': lambda elems: {'DOI': elems[0].text},
            'solr': doi2index,
            'oai_dc': (oai_elements, 'identifier')
        },
        "./m:identifier[@type='isi']": {
            'wtf': lambda elems: {'WOSID': elems[0].text},
            'csl': lambda elems: {'WOSID': elems[0].text},
            'oai_dc': (oai_elements, 'identifier')
        },
        "./m:identifier[@type='isbn']": {
            'wtf': lambda elems: {'ISBN': [elem.text for elem in elems]},
            'csl': lambda elems: {'isbn': [elem.text for elem in elems]},
            'solr': lambda elems: {'isbn': [elem.text for elem in elems], 'isxn': [elem.text for elem in elems]},
            'oai_dc': (oai_elements, 'identifier')
        },
        # "./m:identifier[@type='isi']": lambda elem : {'': elem.text},
        "./m:identifier[@type='issn']": {
            'wtf': lambda elems: {'ISSN': [elem.text for elem in elems]},
            'csl': lambda elems: {'issn': [elem.text for elem in elems]},
            'solr': lambda elems: {'issn': [elem.text for elem in elems], 'isxn': [elem.text for elem in elems]},
            'oai_dc': (oai_elements, 'identifier')
        },
        "./m:identifier[@type='ismn']": {
            'wtf': lambda elems: {'ISMN': [elem.text for elem in elems]},
            'csl': lambda elems: {'ismn': [elem.text for elem in elems]},
            'solr': lambda elems: {'ismn': [elem.text for elem in elems], 'isxn': [elem.text for elem in elems]},
            'oai_dc': (oai_elements, 'identifier')
        },
        "./m:identifier[@type='local' and @displayLabel='HT-ID']": {
            'wtf': lambda elems: {'hbz_id': elems[0].text},
            'solr': lambda elems: {'hbz_id': elems[0].text},
        },
        "./m:identifier[@type='pm']": {
            'wtf': lambda elems: {'PMID': elems[0].text},
            'solr': lambda elems: {'pmid': elems[0].text},
        },
        "./m:identifier[@type='standard number']": {
            'wtf': lambda elems: {'number': elems[0].text},
            'solr': lambda elems: {'number': elems[0].text},
        },
        "./m:identifier[@type='urn']": {
            'wtf': lambda elems: {'urn': elems[0].text},
            'solr': lambda elems: {'urn': elems[0].text},
            'oai_dc': (oai_elements, 'identifier')
        },
        "./m:identifier[@type='zdb']": {
            'wtf': lambda elems: {'ZDBID': elems[0].text},
            'solr': lambda elems: {'zdbid': elems[0].text},
        },
        "./m:language/m:languageTerm[@type='code' and @authority='iso639-2b']": {
            'wtf': lambda elems: {'language': [elem.text for elem in elems]},
            'csl': lambda elems: {'language': [elem.text for elem in elems]},
            'solr': lambda elems: {'language': [elem.text for elem in elems]},
            'oai_dc': (oai_elements, 'language')
        },
        # "./m:location": lambda elem : {'': elem.text},
        # "./m:location/physicalLocation": lambda elem : {'': elem.text},
        # "./m:location/shelfLocator": lambda elem : {'': elem.text},
        "./m:location/m:url": {
            'wtf': lambda elems: {'uri': [elem.text for elem in elems]},
            'csl': lambda elems: {'uri': [elem.text for elem in elems]},
            # 'solr': lambda elems: {'publisher': elems[0].text},
            'oai_dc': (oai_elements, 'identifier')
        },
        # "./m:location/url[@displayLabel='Adresse im Internet']": lambda elem : {'': elem.text},
        # "./m:location/url[@displayLabel='Beigabe im Internet' and @dateLastAccessed]/@dateLastAccessed": lambda elem : {'': elem.text},
        # "./m:location/url[@displayLabel='Online-Adresse' and @dateLastAccessed]/@dateLastAccessed": lambda elem : {'': elem.text},
        # "./m:location/url[@displayLabel='URL im E-Periodical' and @dateLastAccessed]/@dateLastAccessed": lambda elem : {'': elem.text},
        "./m:name": {
            'wtf': get_wtf_names,
            'csl': get_csl_names,
        },
        "./m:name[@type='personal']": {
            'solr': get_solr_persons
        },
        "./m:name[@type='corporate']": {
            'solr': get_solr_corporates
        },
        "./m:note[not(@displayLabel)]": {
            'wtf': lambda elem: {'note': elems[0].text}
        },
        "./m:note[@displayLabel='Ansprüche']": {
            'wtf': lambda elem: {'claims': elems[0].text}
        },
        # "./m:note[@displayLabel='Art der Schrift']": lambda elem : {'': elem.text},
        # "./m:note[@displayLabel='Notiz']": lambda elem : {'': elem.text},
        # "./m:note[@displayLabel='Preis']": lambda elem : {'': elem.text},
        "./m:note[@displayLabel='Prioritätsdaten']": {
            'wtf': lambda elem: {'priority_date': elems[0].text}
        },
        "./m:note[@displayLabel='Tagungsort']": {
            'wtf': lambda elem: {'place': elems[0].text}
        },
        "./m:note[@displayLabel='Titelzusätze']": {
            'wtf': lambda elem: {'title_supplement': elems[0].text}
        },
        # "./m:note[@displayLabel='Veranstaltungsdatum']": {
        #    'wtf': lambda elem : {'': elem.text}
        # },
        # "./m:note[@type='publication status']": lambda elem : {'': elem.text},
        "./m:originInfo/m:dateIssued[@encoding='iso8601']": {
            'wtf': get_wtf_issued
        },
        "./m:originInfo/m:dateIssued[@point='start' and @encoding='iso8601']": {
            'wtf': lambda elem: {'issued': elem[0].text},
            'solr': get_solr_issued
        },
        "./m:originInfo/m:dateOther[@encoding='iso8601']": {
            'wtf': get_wtf_date_application,
        },
        "./m:originInfo/m:edition": {
            'wtf': lambda elem: {'edition': elem[0].text}
        },
        "./m:originInfo/m:place/m:placeTerm[@type='text']": {
            'wtf': lambda elems: {'place_of_application': elems[0].text, 'place': elems[0].text} if record.xpath(
                                      "./m:originInfo/m:dateOther[@encoding='iso8601']", namespaces=NSMAP) else
                                  {'publisher_place': elems[0].text, 'place': elems[0].text},
            'csl': lambda elems: {'publisher_place': elems[0].text},
            'solr': lambda elems: {'place': elems[0].text},
            # 'oai_dc': (oai_elements, 'publisher_place')
        },
        "./m:originInfo/m:place/m:placeTerm[@type='code']": {
            'wtf': lambda elems: {'place_of_application': elems[0].text, 'place': elems[0].text} if record.xpath(
                                      "./m:originInfo/m:dateOther[@encoding='iso8601']", namespaces=NSMAP) else
                                  {'publisher_place': elems[0].text, 'place': elems[0].text},
            'csl': lambda elems: {'publisher_place': elems[0].text},
            'solr': lambda elems: {'place': elems[0].text},
            # 'oai_dc': (oai_elements, 'publisher_place')
        },
        "./m:originInfo/m:publisher": {
            'wtf': lambda elems: {'publisher': elems[0].text},
            'csl': lambda elems: {'publisher': elems[0].text},
            'solr': lambda elems: {'publisher': elems[0].text},
            'oai_dc': (oai_elements, 'publisher')
        },

        # "./m:originInfo[@displayLabel='embargoEnd']": lambda elem : {'': elem.text},
        "./m:physicalDescription/m:extent": {
            'wtf': get_wtf_extent,
            'csl': lambda elems: {'number-of-pages': elems[0].text},
        },
        # "./m:physicalDescription/form": lambda elem : {'': elem.text},
        "./m:physicalDescription/m:internetMediaType": {
            'wtf': lambda elems: {'mime_type': elems[0].text},
        },
        "./m:physicalDescription/m:note": {
            'wtf': lambda elems: {'note': elems[0].text},
            'solr': lambda elems: {'note': elems[0].text},
        },
        "./m:recordInfo/m:recordChangeDate[@encoding='iso8601']": {
            # 'wtf': lambda elems: {'changed': elems[0].text},
            'wtf': lambda elems: {'changed': '%s 00:00:00.001' % elems[0].text},
            'solr': lambda elems: {'changed': '%s 00:00:00.001' % elems[0].text},
        },
        "./m:recordInfo/m:recordCreationDate[@encoding='iso8601']": {
            # 'wtf': lambda elems: {'created': elems[0].text},
            'wtf': lambda elems: {'created': '%s 00:00:00.001' % elems[0].text},
            'solr': lambda elems: {'created': '%s 00:00:00.001' % elems[0].text},
        },
        "./m:recordInfo/m:recordIdentifier": {
            'wtf': lambda elems: {'id': elems[0].text},
            'csl': lambda elems: {'id': elems[0].text},
            'solr': lambda elems: {'id': elems[0].text},
            'oai_dc': (oai_elements, 'identifier')
        },
        # "./m:relatedItem": lambda elem : {'': elem.text},
        # "./m:relatedItem/genre[@authority='local']": lambda elem : {'': elem.text},
        # "./m:relatedItem/identifier[@type='isbn']": lambda elem : {'': elem.text},
        # "./m:relatedItem/identifier[@type='issn']": lambda elem : {'': elem.text},
        # "./m:relatedItem/identifier[@type='local' and @displayLabel='HT-ID']": lambda elem : {'': elem.text},
        # "./m:relatedItem/identifier[@type='zdb']": lambda elem : {'': elem.text},
        # "./m:relatedItem/identifier[@valueURI]/@valueURI": lambda elem : {'': elem.text},
        # "./m:relatedItem/name/namePart[@type='family']": lambda elem : {'': elem.text},
        # "./m:relatedItem/name/namePart[@type='given']": lambda elem : {'': elem.text},
        # "./m:relatedItem/name/role": lambda elem : {'': elem.text},
        # "./m:relatedItem/name/role/roleTerm[@type='code' and @authorityURI='http://www.loc.gov/marc/relators/']": lambda elem : {'': elem.text},
        # "./m:relatedItem/name[@type='personal' and starts-with(@valueURI, 'http://d-nb.info/gnd/') and @authority='gnd']/@valueURI": lambda elem : {'': elem.text},
        # "./m:relatedItem/name[@type='personal']": lambda elem : {'': elem.text},
        # u"./m:relatedItem/note[@displayLabel='Nachträge']": lambda elem : {'': elem.text},
        # u"./m:relatedItem/note[@displayLabel='Titelzusätze']": lambda elem : {'': elem.text},
        # "./m:relatedItem/originInfo": lambda elem : {'': elem.text},
        "./m:relatedItem/m:originInfo/m:dateIssued[@encoding='iso8601']": {
            'wtf': get_wtf_issued,
            'solr': get_solr_issued
        },
        # "./m:relatedItem/originInfo/edition": lambda elem : {'': elem.text},
        # "./m:relatedItem/originInfo/place": lambda elem : {'': elem.text},
        # "./m:relatedItem/originInfo/place/placeTerm[@type='text']": lambda elem : {'': elem.text},
        # "./m:relatedItem/originInfo/publisher": lambda elem : {'': elem.text},
        # "./m:relatedItem/part": lambda elem : {'': elem.text},
        "./m:relatedItem/m:part/m:date[@encoding='iso8601']": {
            'wtf': lambda elem: {'issued': elem[0].text},
            'solr': get_solr_issued
        },
        # "./m:relatedItem/part/detail/number": lambda elem : {'': elem.text},
        # "./m:relatedItem/part/detail[@type='delivery complement']": lambda elem : {'': elem.text},
        # "./m:relatedItem/part/detail[@type='issue']": lambda elem : {'': elem.text},
        # "./m:relatedItem/part/detail[@type='number']": lambda elem : {'': elem.text},
        # "./m:relatedItem/part/detail[@type='volume']": lambda elem : {'': elem.text},
        # "./m:relatedItem/part/extent/list": lambda elem : {'': elem.text},
        # "./m:relatedItem/part/extent[@unit='pages']": lambda elem : {'': elem.text},
        # "./m:relatedItem/physicalDescription": lambda elem : {'': elem.text},
        # u"./m:relatedItem/physicalDescription/note[@displayLabel='Anzahl Bände']": lambda elem : {'': elem.text},
        # "./m:relatedItem/relatedItem/identifier[@type='issn']": lambda elem : {'': elem.text},
        # "./m:relatedItem/relatedItem/part": lambda elem : {'': elem.text},
        # "./m:relatedItem/relatedItem/part/detail/number": lambda elem : {'': elem.text},
        # "./m:relatedItem/relatedItem/part/detail[@type='issue']": lambda elem : {'': elem.text},
        # "./m:relatedItem/relatedItem/part/detail[@type='volume']": lambda elem : {'': elem.text},
        # "./m:relatedItem/relatedItem/part/extent/list": lambda elem : {'': elem.text},
        # "./m:relatedItem/relatedItem/part/extent[@unit='pages']": lambda elem : {'': elem.text},
        # "./m:relatedItem/relatedItem/titleInfo": lambda elem : {'': elem.text},
        # "./m:relatedItem/relatedItem/titleInfo/title": lambda elem : {'': elem.text},
        # "./m:relatedItem/relatedItem[@type='host']": lambda elem : {'': elem.text},
        # "./m:relatedItem/relatedItem[@type='series']": lambda elem : {'': elem.text},
        # "./m:relatedItem/titleInfo/subTitle": lambda elem : {'': elem.text},
        # "./m:relatedItem/titleInfo/title": lambda elem : {'': elem.text},
        # "./m:relatedItem/titleInfo[@type='abbreviated']": lambda elem : {'': elem.text},
        # "./m:relatedItem/titleInfo[@type='translated']": lambda elem : {'': elem.text},
        "./m:relatedItem[@type='host']": {
            'wtf': get_wtf_hosts,
            # 'solr': get_solr_hosts,
            # 'solr_parents': get_solr_parents,
        },
        # "./m:relatedItem[@type='isReferencedBy']": lambda elem : {'': elem.text},
        # "./m:relatedItem[@type='otherVersion']": lambda elem : {'': elem.text},
        # "./m:relatedItem[@type='preceding']": lambda elem : {'': elem.text},
        # "./m:relatedItem[@type='references']": lambda elem : {'': elem.text},
        "./m:relatedItem[@type='series']": {
            'wtf': get_wtf_series,
            # 'solr': get_solr_series,
        },
        "./m:subject[not(@authority)]/m:topic": {
            'wtf': lambda elems: {'keyword': [elem.text for elem in elems]},
            'solr': lambda elems: {'subject': [elem.text for elem in elems]},
            'oai_dc': (oai_elements, 'subject')
        },
        "./m:subject[@authority='mesh']": {
            'wtf': get_wtf_subject,
            'solr': lambda elems: {'mesh_terms': [SUBJECT_MAPS.get('mesh').get(elem.text) for elem in elems]},
            'oai_dc': (oai_elements, 'subject')
        },
        "./m:subject[@authority='stw']": {
            'wtf': get_wtf_subject,
            'solr': lambda elems: {'stwterm_de': [SUBJECT_MAPS.get('stw').get(elem.text) for elem in elems]},
            'oai_dc': (oai_elements, 'subject')
        },
        # "./m:subject[@authority='thesoz']": lambda elem : {'': elem.text},
        "./m:tableOfContents": {
            'wtf': get_wtf_tocs,
            'solr': lambda elems: {'toc_text': [elem.text for elem in elems]},
        },
        # "./m:tableOfContents[@xlink:href]/@xlink:href": lambda elem : {'table_of_contents': elem},
        "./m:titleInfo[not(@type)]/m:title": {
            'wtf': lambda elems: {'title': elems[0].text},
            'csl': lambda elems: {'title': elems[0].text} if not record.xpath("./m:titleInfo/m:subTitle",
                                                                              namespaces=NSMAP) else
            {'title': '%s : %s' % (elems[0].text, record.xpath("./m:titleInfo/m:subTitle", namespaces=NSMAP)[0].text)},
            'solr': lambda elems: {'title': elems[0].text, 'exacttitle': elems[0].text, 'sorttitle': elems[0].text,
                                   'spell': elems[0].text},
            'oai_dc': (oai_elements, 'title')  # TODO: Elegant solution for dealing with subtitles...
        },
        "./m:titleInfo/m:subTitle": {
            'wtf': lambda elems: {'subtitle': elems[0].text},
            'solr': lambda elems: {'subtitle': elems[0].text},
        },
        # "./m:titleInfo[@displayLabel='Paragraph(en)']": lambda elem : {'': elem.text},
        "./m:titleInfo[@type='translated']/m:title": {
            'wtf': other_title,
            'solr': lambda elems: {'other_title': elems[0].text},
        },
        # "./m:titleInfo[@type='uniform']": lambda elem : {'': elem.text},
        # "./m:typeOfResource": lambda elem : {'': elem.text},
    }
except IndexError:
    pass

parents = []
more_parents = []
solr_json = []
wtfs = []

modsfiles = []
if len(secrets.MODS_FILES_PATH) > 0:
    modsfiles = [join(secrets.MODS_FILES_PATH, f) for f in listdir(secrets.MODS_FILES_PATH) if isfile(join(
        secrets.MODS_FILES_PATH, f))]
else:
    modsfiles.append(secrets.MODS_TEST_FILE)
logging.info(modsfiles)

for file in modsfiles:
    logging.info('work on ' + file)
    mc = etree.iterparse(file, tag='%smods' % MODS)

    for event, record in mc:
        wtf = {}
        csl = {}
        solr = {}
        old_pubtype = ''
        oai_dc = etree.Element('%smetadata' % OAI_DC, nsmap=OAI_MAP)
        for xpath_expr in CONVERTER_MAP:
            elems = record.xpath(xpath_expr, namespaces=NSMAP)
            try:
                data = CONVERTER_MAP.get(xpath_expr).get('wtf')(elems)
                if list(data.values())[0]:
                    wtf.update(data)
            except TypeError:
                pass
            except IndexError:
                pass
            except AttributeError:
                if type(data) == tuple:
                    for d in data:
                        wtf.update(d)
                else:
                    logging.info(xpath_expr)
                    logging.info(record.xpath("./m:recordInfo/m:recordIdentifier", namespaces=NSMAP)[0].text)
                    for elem in elems:
                        logging.info(etree.tostring(elem))
                    raise
            try:
                data = CONVERTER_MAP.get(xpath_expr).get('csl')(elems)
                if len(list(data.values())) > 0:
                    csl.update(data)
            except TypeError:
                pass
            except IndexError:
                pass
            try:
                data = CONVERTER_MAP.get(xpath_expr).get('solr')(elems)
                if len(list(data.values())) > 0:
                    solr.update(data)
            except TypeError:
                pass
            except IndexError:
                pass

            try:
                oai_dc.extend(CONVERTER_MAP.get(xpath_expr).get('oai_dc')[0](CONVERTER_MAP.get(xpath_expr).get('oai_dc')[1],
                                                                             elems))
            except TypeError:
                pass
            except AttributeError:
                logging.info(xpath_expr)
                logging.info(record.xpath("./m:recordInfo/m:recordIdentifier", namespaces=NSMAP)[0].text)
                raise

        wtf.setdefault('editorial_status', 'imported')
        wtf.setdefault('owner', ['daten.ub@tu-dortmund.de'])
        wtf.setdefault('catalog', [secrets.CATALOG])

        if not wtf.get('pubtype'):
            logging.info('%s: ERROR no pubtype', wtf.get('id'))
        elif len(wtf.get('pubtype').split('#')) > 1:
            tmp = wtf.get('pubtype').split('#')
            wtf['pubtype'] = tmp[0]
            wtf.setdefault('subtype', tmp[1])

        wtfs.append(wtf)
        # solr.setdefault('dc', oai_dc)
        # logging.info('WTF %s' % wtf)
        # pprint.pprint(oai_dc)
        # logging.info('OAI_DC %s' % etree.tostring(oai_dc))
        # logging.info('CSL %s' % csl)
        # logging.info('SOLR %s' % solr)
        # pprint.pprint(solr)

        solr.setdefault('pubtype', wtf.get('pubtype'))
        solr.setdefault('wtf_json', wtf)
        solr_json.append(solr)

fo = open(secrets.RESULTS_DIR + 'more_parents.json', 'w')
fo.write(json.dumps(more_parents, indent=4))
fo.close()

fo = open(secrets.RESULTS_DIR + 'parents.json', 'w')
fo.write(json.dumps(parents, indent=4))
fo.close()

fo = open(secrets.RESULTS_DIR + 'records.json', 'w')
fo.write(json.dumps(wtfs, indent=4))
fo.close()

# print(json.dumps(parents, indent=4))

# pprint.pprint(parents)
# logging.info('####################################################################################################')
