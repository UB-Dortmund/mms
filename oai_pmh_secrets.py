# The MIT License
#
#  Copyright 2016 UB Dortmund <api.ub@tu-dortmund.de>.
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

# ---- APP CONFIG ---- #
DIFFERENT_PROXY_PATH = True

DEBUG = True
DEBUG_KEY = '1cf7e937-c98b-4e80-ac65-ecf0bb2e5e86'

LOGFILE = 'log/oai-pmh.log'

APP_PORT = '5008'

# ---- DOCS ---- #
SWAGGER_SCHEMES = ['http', 'https']
SWAGGER_HOST = 'localhost:5008'
SWAGGER_BASEPATH = '/'
SWAGGER_API_VERSION = ''
SWAGGER_TITLE = ''
SWAGGER_DESCRIPTION = ''

# ---- OAI-PMH CONFIG ---- #
BATCH_SIZE = 500
VALID_METADATA_PREFIXES = ('oai_dc', 'mods')

OAI_PMH_APP_DATA = {
    'tudo': {
        'repositoryName': 'Campus Research Bibliography, TU Dortmund University',
        'baseURL': 'hochschulbibliographie.tu-dortmund.de/oai',
        'protocolVersion': '2.0',
        'adminEmail': ['daten.ub@tu-dortmund.de'],
        'earliestDatestamp': '2010-01-25',
        'deletedRecord': 'persistent',
        'granularity': 'YYYY-MM-DD',
        'repositoryIdentifier': 'hochschulbibliographie.tu-dortmund.de',
        'delimiter': ':',
        'id_prefix': 'oai:hochschulbibliographie.tu-dortmund.de:',
        'sampleIdentifier': '%s9ee01b72-17ee-4eb4-858e-07a10984eedb' % 'oai:hochschulbibliographie.tu-dortmund.de:'
    },
    'rub': {
        'repositoryName': 'Institutional repository test instance, Ruhr-Universität Bochum',
        'baseURL': 'http://bibliographie-test.ub.rub.de/export/xml/oai',
        'protocolVersion': '2.0',
        'adminEmail': ['bibliographie-ub@rub.de'],
        'earliestDatestamp': '2010-01-25',
        'deletedRecord': 'persistent',
        'granularity': 'YYYY-MM-DD',
        'repositoryIdentifier': 'bibliographie.ub.rub.de',
        'delimiter': ':',
        'id_prefix': 'oai:bibliographie-test.ub.rub.de:',
        'sampleIdentifier': '%s9ee01b72-17ee-4eb4-858e-07a10984eedb' % 'oai:bibliographie-test.ub.rub.de:'
    }
}

FORMATS = {
    'oai_dc': {
        'schema': 'http://www.openarchives.org/OAI/2.0/oai_dc.xsd',
        'namespace': 'http://www.openarchives.org/OAI/2.0/oai_dc/'
    },
    'mods': {
        'schema': 'http://www.loc.gov/standards/mods/mods.xsd',
        'namespace': 'http://www.loc.gov/mods/v3'
    }
}

SETS_INFO = {
    'key': 'value',
    'base_url': 'hochschulbibliographie.tu-dortmund.de/oai',
    'ec_fundedresources': 'EC_fundedresources set',
    'ddc:000': 'Generalities, Science',
    'ddc:004': 'Data processing Computer science ',
    'ddc:010': 'Bibliography ',
    'ddc:020': 'Library & information sciences ',
    'ddc:030': 'General encyclopedic works',
    'ddc:050': 'General serials & their indexes',
    'ddc:060': 'General organization & museology ',
    'ddc:070': 'News media, journalism, publishing ',
    'ddc:080': 'General collections ',
    'ddc:090': 'Manuscripts & rare books ',
    'ddc:100': 'Philosophy',
    'ddc:130': 'Paranormal phenomena ',
    'ddc:150': 'Psychology ',
    'ddc:200': 'Religion ',
    'ddc:220': 'Bible ',
    'ddc:230': 'Christian theology ',
    'ddc:290': 'Other & comparative religions ',
    'ddc:300': 'Social sciences ',
    'ddc:310': 'General statistics ',
    'ddc:320': 'Political science ',
    'ddc:330': 'Economics ',
    'ddc:333.7': 'Natural ressources, energy and environment',
    'ddc:340': 'Law ',
    'ddc:350': 'Public administration ',
    'ddc:355': 'Military science ',
    'ddc:360': 'Social services; association ',
    'ddc:370': 'Education ',
    'ddc:380': 'Commerce, communications, transport',
    'ddc:390': 'Customs, etiquette, folklore ',
    'ddc:400': 'Language, Linguistics ',
    'ddc:420': 'English ',
    'ddc:430': 'Germanic ',
    'ddc:439': 'Other Germanic languages ',
    'ddc:440': 'Romance languages French ',
    'ddc:450': 'Italian, Romanian, Rhaeto-Romantic ',
    'ddc:460': 'Spanish & Portugese languages S',
    'ddc:470': 'Italic Latin ',
    'ddc:480': 'Hellenic languages Classical Greek ',
    'ddc:490': 'Other languages ',
    'ddc:500': 'Natural sciences & mathematics ',
    'ddc:510': 'Mathematics ',
    'ddc:520': 'Astronomy & allied sciences ',
    'ddc:530': 'Physics ',
    'ddc:540': 'Chemistry & allied sciences ',
    'ddc:550': 'Earth sciences ',
    'ddc:560': 'Paleontology Paleozoology ',
    'ddc:570': 'Life sciences ',
    'ddc:580': 'Botanical sciences ',
    'ddc:590': 'Zoological sciences ',
    'ddc:600': 'Technology (Applied sciences) ',
    'ddc:610': 'Medical sciences Medicine ',
    'ddc:620': 'Engineering & allied operations ',
    'ddc:630': 'Agriculture ',
    'ddc:640': 'Home economics & family living ',
    'ddc:650': 'Management & auxiliary services ',
    'ddc:660': 'Chemical engineering ',
    'ddc:670': 'Manufacturing ',
    'ddc:690': 'Buildings ',
    'ddc:700': 'The arts ',
    'ddc:710': 'Civic & landscape art ',
    'ddc:720': 'Architecture ',
    'ddc:730': 'Plastic arts Sculpture ',
    'ddc:740': 'Drawing & decorative arts ',
    'ddc:741.5': 'Comics, Cartoons ',
    'ddc:750': 'Painting & paintings ',
    'ddc:760': 'Graphic arts Printmaking & prints ',
    'ddc:770': 'Photography & photographs ',
    'ddc:780': 'Music ',
    'ddc:790': 'Recreational & performing arts ',
    'ddc:791': 'Public performances ',
    'ddc:792': 'Stage presentations ',
    'ddc:793': 'Indoor games & amusements ',
    'ddc:796': 'Athletic & outdoor sports & games ',
    'ddc:800': 'Literature & rhetoric',
    'ddc:810': 'American literature in English ',
    'ddc:820': 'English & Old English literatures ',
    'ddc:830': 'Literatures of Germanic languages ',
    'ddc:839': 'Other Germanic literatures ',
    'ddc:840': 'Literatures of Romance languages ',
    'ddc:850': 'Italian, Romanian, Rhaeto-Romanic literatures',
    'ddc:860': 'Spanish & Portuguese literatures ',
    'ddc:870': 'Italic literatures Latin ',
    'ddc:880': 'Hellenic literatures Classical Greek ',
    'ddc:890': 'Literatures of other languages ',
    'ddc:900': 'Geography & history ',
    'ddc:910': 'Geography & travel ',
    'ddc:914.3': 'Geography & travel Germany ',
    'ddc:920': 'Biography, genealogy, insignia ',
    'ddc:930': 'History of the ancient world ',
    'ddc:940': 'General history of Europe ',
    'ddc:943': 'General history of Europe Central Europe Germany',
    'ddc:950': 'General history of Asia Far East ',
    'ddc:960': 'General history of Africa ',
    'ddc:970': 'General history of North America ',
    'ddc:980': 'General history of South America ',
    'ddc:990': 'General history of other areas ',
    'doc-type:preprint': 'Preprint',
    'doc-type:workingPaper': 'WorkingPaper',
    'doc-type:article': 'Article',
    'doc-type:contributionToPeriodical': 'ContributionToPeriodical',
    'doc-type:PeriodicalPart': 'PeriodicalPart',
    'doc-type:Periodical': 'Periodical',
    'doc-type:book': 'Book',
    'doc-type:bookPart': 'BookPart',
    'doc-type:Manuscript': 'Manuscript',
    'doc-type:StudyThesis': 'StudyThesis',
    'doc-type:bachelorThesis': 'BachelorThesis',
    'doc-type:masterThesis': 'MasterThesis',
    'doc-type:doctoralThesis': 'DoctoralThesis',
    'doc-type:conferenceObject': 'ConferenceObject',
    'doc-type:lecture': 'Lecture',
    'doc-type:review': 'Review',
    'doc-type:annotation': 'Annotation',
    'doc-type:patent': 'Patent',
    'doc-type:report': 'Report',
    'doc-type:MusicalNotation': 'MusicalNotation',
    'doc-type:Sound': 'Sound',
    'doc-type:Image': 'Image',
    'doc-type:MovingImage': 'MovingImage',
    'doc-type:StillImage': 'StillImage',
    'doc-type:CourseMaterial': 'CourseMaterial',
    'doc-type:Website': 'Website',
    'doc-type:Software': 'Software',
    'doc-type:CartographicMaterial': 'CartographicMaterial',
    'doc-type:ResearchData': 'ResearchData',
    'doc-type:Other': 'Other',
    'doc-type:Text': 'Text',
}

# ---- PERSISTENCE ---- #
SOLR_HOST = '129.217.132.18'
SOLR_PORT = '5200'
SOLR_APP = 'solr'


