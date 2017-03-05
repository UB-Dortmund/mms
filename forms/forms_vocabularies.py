from flask_babel import lazy_gettext

LICENSE_MAP = (
    ('', lazy_gettext('Select a License')),
    ('cc_zero', lazy_gettext('Creative Commons Zero - Public Domain')),
    ('cc_by', lazy_gettext('Creative Commons Attribution')),
    ('cc_by_sa', lazy_gettext('Creative Commons Attribution Share Alike')),
    ('cc_by_nd', lazy_gettext('Creative Commons Attribution No Derivatives'))
)

# see: http://www.loc.gov/marc/languages/
LANGUAGES = [
    ('', lazy_gettext('Select a Language')),
    ('eng', lazy_gettext('English')),
    ('ger', lazy_gettext('German')),
    ('fre', lazy_gettext('French')),
    ('rus', lazy_gettext('Russian')),
    ('spa', lazy_gettext('Spanish')),
    ('ita', lazy_gettext('Italian')),
    ('jpn', lazy_gettext('Japanese')),
    ('lat', lazy_gettext('Latin')),
    ('zhn', lazy_gettext('Chinese')),
    ('dut', lazy_gettext('Dutch')),
    ('tur', lazy_gettext('Turkish')),
    ('por', lazy_gettext('Portuguese')),
    ('pol', lazy_gettext('Polish')),
    ('gre', lazy_gettext('Greek')),
    ('srp', lazy_gettext('Serbian')),
    ('cat', lazy_gettext('Catalan')),
    ('dan', lazy_gettext('Danish')),
    ('cze', lazy_gettext('Czech')),
    ('kor', lazy_gettext('Korean')),
    ('ara', lazy_gettext('Arabic')),
    ('hun', lazy_gettext('Hungarian')),
    ('swe', lazy_gettext('Swedish')),
    ('ukr', lazy_gettext('Ukranian')),
    ('heb', lazy_gettext('Hebrew')),
    ('hrv', lazy_gettext('Croatian')),
    ('slo', lazy_gettext('Slovak')),
    ('nor', lazy_gettext('Norwegian')),
    ('rum', lazy_gettext('Romanian')),
    ('fin', lazy_gettext('Finnish')),
    ('geo', lazy_gettext('Georgian')),
    ('bul', lazy_gettext('Bulgarian')),
    ('grc', lazy_gettext('Ancient Greek')),
    ('ind', lazy_gettext('Indonesian Language')),
    ('gmh', lazy_gettext('Middle High German')),
    ('mon', lazy_gettext('Mongolian Language')),
    ('peo', lazy_gettext('Persian')),
    ('alb', lazy_gettext('Albanian')),
    ('bos', lazy_gettext('Bosnian')),
    ('lit', lazy_gettext('Lithuanian')),
    ('slv', lazy_gettext('Slovenian')),
    ('baq', lazy_gettext('Basque')),
    ('gag', lazy_gettext('Galician')),
    ('tib', lazy_gettext('Tibetan')),
]

USER_ROLES = [
    ('', lazy_gettext('Select a Role')),
    ('aut', lazy_gettext('Author')),
    ('edt', lazy_gettext('Editor')),
    ('ctb', lazy_gettext('Contributor')),
    ('ths', lazy_gettext('Thesis Adviser')),
]

CORP_ROLES_USER = [
    ('', lazy_gettext('Select a Role')),
    ('edt', lazy_gettext('Editor')),
    ('ctb', lazy_gettext('Contributor')),
    ('dgg', lazy_gettext('Degree granting institution')),
]

CORP_ROLES = CORP_ROLES_USER[:]

CORP_ROLES.extend([
    ('his', lazy_gettext('Host institution')),
    ('orm', lazy_gettext('Organizer')),
    ('brd', lazy_gettext('Broadcaster')),
])

PATENT_PERS_ROLES = [
    ('', lazy_gettext('Select a Role')),
    ('inv', lazy_gettext('Inventor')),
    ('pta', lazy_gettext('Patent applicant')),
]

PATENT_CORP_ROLES = [
    ('pta', lazy_gettext('Patent applicant')),
]

ADMIN_ROLES = USER_ROLES[:]

ADMIN_ROLES.extend([
    ('abr', lazy_gettext('Abridger')),
    ('arr', lazy_gettext('Arranger')),
    ('aui', lazy_gettext('Author of Foreword')),
    ('aft', lazy_gettext('Author of Afterword')),
    ('org', lazy_gettext('Originator')),
    ('std', lazy_gettext('Set designer')),
    ('chr', lazy_gettext('Choreographer')),
    ('stl', lazy_gettext('Storyteller')),
    ('fmk', lazy_gettext('Filmmaker')),
    ('pht', lazy_gettext('Photographer')),
    ('hnr', lazy_gettext('Honoree')),
    ('ill', lazy_gettext('Illustrator')),
    ('itr', lazy_gettext('Instrumentalist')),
    ('ivr', lazy_gettext('Interviewer')),
    ('ive', lazy_gettext('Interviewee')),
    ('cwt', lazy_gettext('Commentator for written text')),
    ('cmp', lazy_gettext('Composer')),
    ('cst', lazy_gettext('Costume Designer')),
    ('elg', lazy_gettext('Electrician')),
    ('mod', lazy_gettext('Moderator')),
    ('mus', lazy_gettext('Musician')),
    ('pmn', lazy_gettext('Production Manager')),
    ('pro', lazy_gettext('Producer')),
    ('prg', lazy_gettext('Programmer')),
    ('pdr', lazy_gettext('Project Director')),
    ('red', lazy_gettext('Redaktor')),
    ('spk', lazy_gettext('Speaker')),
    ('drt', lazy_gettext('Director')),
    ('sng', lazy_gettext('Singer')),
    ('act', lazy_gettext('Actor')),
    ('tcd', lazy_gettext('Technical Director')),
    ('trl', lazy_gettext('Translator')),
])

USER_PUBTYPES = [
    ('', lazy_gettext('Select a Publication Type')),
    ('ArticleJournal', lazy_gettext('Article in Journal')),
    ('Chapter', lazy_gettext('Chapter in...')),
    ('Collection', lazy_gettext('Collection')),
    ('Monograph', lazy_gettext('Monograph')),
    ('Report', lazy_gettext('Report / Other')),
    ('ResearchData', lazy_gettext('Research Data including Software')),
]

ADMIN_PUBTYPES = [
    ('', lazy_gettext('Select a Publication Type')),
    ('ArticleJournal', lazy_gettext('Article in Journal')),
    ('Chapter', lazy_gettext('Chapter in...')),
    ('Collection', lazy_gettext('Collection')),
    ('Monograph', lazy_gettext('Monograph')),
    ('MultivolumeWork', lazy_gettext('MultivolumeWork')),
    ('Report', lazy_gettext('Report')),
    ('ResearchData', lazy_gettext('Research Data including Software')),
    ('ArticleNewspaper', lazy_gettext('Article in Newspaper')),
    ('AudioVideoDocument', lazy_gettext('Audio or Video Document')),
    ('ChapterInLegalCommentary', lazy_gettext('Chapter in a Legal Commentary')),
    ('Conference', lazy_gettext('Conference')),
    ('Edition', lazy_gettext('Edition')),
    ('InternetDocument', lazy_gettext('Internet Document')),
    ('Journal', lazy_gettext('Journal')),
    ('Lecture', lazy_gettext('Lecture')),
    ('LegalCommentary', lazy_gettext('Legal Commentary')),
    ('Newspaper', lazy_gettext('Newspaper')),
    ('Patent', lazy_gettext('Patent')),
    ('PressRelease', lazy_gettext('Press Release')),
    ('RadioTVProgram', lazy_gettext('Radio or TV program')),
    ('Series', lazy_gettext('Series')),
    ('SpecialIssue', lazy_gettext('Special Issue')),
    ('Standard', lazy_gettext('Standard')),
    ('Thesis', lazy_gettext('Thesis')),
    ('Other', lazy_gettext('Other')),
]

EDITORIAL_STATUS = [
    ('', lazy_gettext('Select an Editorial Status')),
    ('new', lazy_gettext('New')),
    ('in_process', lazy_gettext('Editing')),
    ('processed', lazy_gettext('Edited')),
    ('final_editing', lazy_gettext('Final Editing')),
    ('finalized', lazy_gettext('Finalized')),
    ('imported', lazy_gettext('Imported')),
    ('deleted', lazy_gettext('Deleted')),
]

PERS_STATUS_MAP = [
    ('', lazy_gettext('Select a Status')),
    ('alumnus', lazy_gettext('Alumnus')),
    ('assistant_lecturer', lazy_gettext('Assistant Lecturer')),
    ('callcenter', lazy_gettext('Callcenter')),
    ('ranking', lazy_gettext('Relevant for Ranking')),
    ('external', lazy_gettext('External Staff')),
    ('manually_added', lazy_gettext('Manually added')),
    ('official', lazy_gettext('Official')),
    ('official_ns', lazy_gettext('Official, Non-Scientific')),
    ('research_school', lazy_gettext('Doctoral Candidate')),
    ('principal_investigator', lazy_gettext('Principal Investigator')),
    ('professor', lazy_gettext('Professor')),
    ('emeritus', lazy_gettext('Emeritus')),
    ('teaching_assistant', lazy_gettext('Teaching Assistant')),
    ('tech_admin', lazy_gettext('Technical and Administrative Staff')),
]

PROJECT_TYPES = [
    ('', lazy_gettext('Select a Project Type')),
    ('fp7', lazy_gettext('FP7')),
    ('h2020', lazy_gettext('Horizon 2020')),
    ('dfg', lazy_gettext('DFG')),
    ('mercur', lazy_gettext('Mercator Research Center Ruhr (MERCUR)')),
    ('other', lazy_gettext('Other')),
]

CARRIER = [
    ('', lazy_gettext('Select a Carrier')),
    ('AudioDisc', lazy_gettext('Audio disc')),
    ('Audiocassette', lazy_gettext('Audiocassette')),
    ('AudiotapeReel', lazy_gettext('Audiotape reel')),
    ('ComputerDisc', lazy_gettext('Computer disc')),
    ('OnlineRessource', lazy_gettext('Online-ressource')),
    ('Microfiche', lazy_gettext('Microfiche')),
    ('MicrofilmCassette', lazy_gettext('Microfilm cassette')),
    ('MicrofilmReel', lazy_gettext('Microfilm reel')),
    ('MicrofilmRoll', lazy_gettext('Microfilm roll')),
    ('MicroscopeSlide', lazy_gettext('Microscope slide')),
    ('FilmCassette', lazy_gettext('Film cassette')),
    ('FilmReel', lazy_gettext('Film reel')),
    ('FilmRoll', lazy_gettext('Film roll')),
    ('FilmStrip', lazy_gettext('Film strip')),
    ('Object', lazy_gettext('Object')),
    ('card', lazy_gettext('card')),
    ('Videocassette', lazy_gettext('Videocassette')),
    ('Videodisc', lazy_gettext('Videodisc')),
    ('Unspecified', lazy_gettext('Unspecified')),
]

RESOURCE_TYPES = [
    ('', lazy_gettext('Select a Resource Type')),
    ('Audiovisual', lazy_gettext('Audiovisual')),
    ('Collection', lazy_gettext('Collection')),
    ('Dataset', lazy_gettext('Dataset')),
    ('Event', lazy_gettext('Event')),
    ('Image', lazy_gettext('Image')),
    ('InteractiveResource', lazy_gettext('InteractiveResource')),
    ('Model', lazy_gettext('Model')),
    ('PhysicalObject', lazy_gettext('PhysicalObject')),
    ('Service', lazy_gettext('Service')),
    ('Software', lazy_gettext('Software')),
    ('Sound', lazy_gettext('Sound')),
    ('Text', lazy_gettext('Text')),
    ('Workflow', lazy_gettext('Workflow')),
    ('Other', lazy_gettext('Other')),
]

FREQUENCY = [
    ('', lazy_gettext('Select a Frequency')),
    ('completely_irregular', lazy_gettext('Completely Irregular')),
    ('annual', lazy_gettext('Annual')),
    ('quarterly', lazy_gettext('Quarterly')),
    ('semiannual', lazy_gettext('Semiannual')),
    ('monthly', lazy_gettext('Monthly')),
    ('bimonthly', lazy_gettext('Bimonthly')),
    ('three_times_a_year', lazy_gettext('Three Times a Year')),
    ('semimonthly', lazy_gettext('Semimonthly')),
    ('biennial', lazy_gettext('Biannial')),
    ('fifteen_issues_a_year', lazy_gettext('Fifteen Issues a Year')),
    ('continuously_updated', lazy_gettext('Continuously Updated')),
    ('daily', lazy_gettext('Daily')),
    ('semiweekly', lazy_gettext('Semiweekly')),
    ('three_times_a_week', lazy_gettext('Three Times a Week')),
    ('weekly', lazy_gettext('Weekly')),
    ('biweekly', lazy_gettext('Biweekly')),
    ('three_times_a_month', lazy_gettext('Three Times a Month')),
    ('triennial', lazy_gettext('Triennial')),
]

PUB_STATUS = [
    ('', lazy_gettext('Select a Publication Status')),
    ('published', lazy_gettext('Published')),
    ('unpublished', lazy_gettext('Unpublished')),
    ('forthcoming', lazy_gettext('Forthcoming')),
    ('submitted', lazy_gettext('Submitted')),
    ('accepted', lazy_gettext('Accepted')),
]

PATENT_PUB_STATUS = PUB_STATUS

PATENT_PUB_STATUS.extend([
    ('granted', lazy_gettext('Granted'))
])

PATENT_COUNTRY_CODES = [
    ('', lazy_gettext('Select a country code')),
    ('DE', lazy_gettext('DE')),
    ('FR', lazy_gettext('FR')),
    ('GB', lazy_gettext('GB')),
    ('AT', lazy_gettext('AT')),
    ('US', lazy_gettext('US')),
]

CATALOGS = [
    ('Ruhr-Universität Bochum', lazy_gettext('Ruhr-Universität Bochum')),
    ('Technische Universität Dortmund', lazy_gettext('Technische Universität Dortmund')),
    ('Temporäre Daten', lazy_gettext('Temporäre Daten')),
]

OA_FUNDS = [
    ('', lazy_gettext('Select a Open Access Fund')),
    ('Ruhr-Universität Bochum', lazy_gettext('Ruhr-Universität Bochum')),
    ('Technische Universität Dortmund', lazy_gettext('Technische Universität Dortmund')),
]



RELATION_TYPES = [
    ('', lazy_gettext('Select a Relation Type')),
    ('cited', lazy_gettext('cited by this upload')),
    ('is_cited_by', lazy_gettext('is cited by this upload')),
    ('is_supplement_by', lazy_gettext('is supplement by this upload')),
    ('is_supplement_to', lazy_gettext('is a supplement to this upload')),
    ('is_referenced_by', lazy_gettext('is referenced by this upload')),
    ('references', lazy_gettext('references this upload')),
    ('is_previous_version_of', lazy_gettext('is previous version of this upload')),
    ('is_new_version_of', lazy_gettext('is new version of this upload')),
    ('has_part', lazy_gettext('has this upload as part')),
    ('is_part_of', lazy_gettext('is part of this upload')),
    ('is_created_by', lazy_gettext('is compiled/created by this upload')),
    ('is_created_by', lazy_gettext('compiled/created this upload')),
    ('identical', lazy_gettext('is identical to this upload')),
]
