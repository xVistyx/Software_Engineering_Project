"""Generate editable diagrams.net pages and matching SVGs from an explicit code-reviewed model.

Run: python Documents/generate_backend_uml.py
This documents the inspected implementation; it does not infer architecture from source.
"""
from pathlib import Path
import textwrap
from xml.etree import ElementTree as E

OUT = Path(__file__).resolve().parent
NS = 'http://www.w3.org/2000/svg'
E.register_namespace('', NS)
BOOK = E.Element('mxfile', host='app.diagrams.net', version='24.7.17')
PAGES = []
INK, MUTED, LINE = '#292630', '#746f7d', '#bcb6c8'
PURPLE, GREEN, AMBER = '#f1edf8', '#edf6f0', '#fff5e3'


def element(parent, tag, **attributes):
    return E.SubElement(parent, '{' + NS + '}' + tag, {k.replace('_', '-'): str(v) for k, v in attributes.items()})


class Page:
    def __init__(self, slug, title, subtitle):
        self.slug, self.title, self.count = slug, title, 1
        self.width, self.height = 1600, 1000
        page = E.SubElement(BOOK, 'diagram', id=slug, name=title)
        model = E.SubElement(page, 'mxGraphModel', page='1', pageWidth='1600', pageHeight='1000', grid='1', gridSize='10')
        self.root = E.SubElement(model, 'root')
        E.SubElement(self.root, 'mxCell', id='0')
        E.SubElement(self.root, 'mxCell', id='1', parent='0')
        self.svg = E.Element('{' + NS + '}svg', width='1600', height='1000', viewBox='0 0 1600 1000')
        element(self.svg, 'title').text = title
        element(self.svg, 'desc').text = subtitle
        defs = element(self.svg, 'defs')
        for name, shape, fill in [('arrow', 'M0 0 L10 5 L0 10', 'none'), ('triangle', 'M0 0 L10 5 L0 10 Z', 'white')]:
            marker = element(defs, 'marker', id=name, markerWidth=12, markerHeight=12, refX=10, refY=5, orient='auto', markerUnits='userSpaceOnUse')
            element(marker, 'path', d=shape, fill=fill, stroke=MUTED, stroke_width=1.7)
        element(self.svg, 'rect', width=1600, height=1000, fill='white')
        self.text(42, 25, 1516, 44, title, size=30, bold=True)
        self.text(42, 79, 1516, 45, subtitle, size=17, color=MUTED)
        self.text(42, 954, 1516, 32, 'Grove | SQL session update | 15 September 2026 | feature/sql-summary-integration | based on bb5b28d', size=13, color=MUTED)
        PAGES.append(self)

    def cell(self, value, x, y, w, h, style):
        self.count += 1
        cell = E.SubElement(self.root, 'mxCell', id=str(self.count), value=value, style=style, vertex='1', parent='1')
        E.SubElement(cell, 'mxGeometry', x=str(x), y=str(y), width=str(w), height=str(h), **{'as': 'geometry'})
        return str(self.count)

    def text(self, x, y, w, h, value, size=17, color=INK, bold=False, center=False):
        lines = []
        for paragraph in value.split('\n'):
            lines.extend(textwrap.wrap(paragraph, max(1, int(w / (size * .56))), break_long_words=False, break_on_hyphens=False) or [''])
        if len(lines) * (size + 7) > h + 8:
            raise ValueError(f'Text exceeds allocated height on {self.slug}: {value}')
        self.cell('\n'.join(lines), x, y, w, h, f'text;html=0;whiteSpace=wrap;align={"center" if center else "left"};verticalAlign=top;fontSize={size};fontColor={color};fontStyle={1 if bold else 0};')
        t = element(self.svg, 'text', x=x+w/2 if center else x, y=y+size, font_family='Arial, sans-serif', font_size=size, fill=color, font_weight=600 if bold else 400, text_anchor='middle' if center else 'start')
        t.set('data-bounds', f'{x},{y},{w},{h}')
        for i, line in enumerate(lines):
            element(t, 'tspan', x=x+w/2 if center else x, dy=0 if i == 0 else size+7).text = line

    def box(self, x, y, w, h, title, body='', tint=PURPLE, kind='component'):
        label = f'«{kind}» {title}' if kind else title
        self.cell('', x, y, w, h, f'rounded=1;arcSize=6;html=0;fillColor={tint};strokeColor={LINE};')
        element(self.svg, 'rect', x=x, y=y, width=w, height=h, rx=8, fill=tint, stroke=LINE)
        self.text(x+16, y+14, w-32, 32, label, size=18, bold=True)
        element(self.svg, 'line', x1=x, y1=y+52, x2=x+w, y2=y+52, stroke=LINE)
        self.cell('', x, y+51, w, 1, f'line;strokeColor={LINE};')
        if body:
            self.text(x+16, y+67, w-32, h-76, body, size=16)

    def edge(self, points, label='', label_at=None, dashed=False, arrow=True, triangle=False):
        self.count += 1
        style = f'html=0;endArrow={"block" if triangle else "open" if arrow else "none"};endFill=0;strokeColor={MUTED};strokeWidth=1.6;dashed={int(dashed)};'
        cell = E.SubElement(self.root, 'mxCell', id=str(self.count), value='', style=style, edge='1', parent='1')
        geo = E.SubElement(cell, 'mxGeometry', relative='1', **{'as': 'geometry'})
        E.SubElement(geo, 'mxPoint', x=str(points[0][0]), y=str(points[0][1]), **{'as': 'sourcePoint'})
        E.SubElement(geo, 'mxPoint', x=str(points[-1][0]), y=str(points[-1][1]), **{'as': 'targetPoint'})
        if len(points) > 2:
            arr = E.SubElement(geo, 'Array', **{'as': 'points'})
            for x, y in points[1:-1]:
                E.SubElement(arr, 'mxPoint', x=str(x), y=str(y))
        attrs = dict(points=' '.join(f'{x},{y}' for x,y in points), fill='none', stroke=MUTED, stroke_width=1.6)
        if dashed:
            attrs['stroke_dasharray'] = '7 5'
        if arrow:
            attrs['marker_end'] = 'url(#triangle)' if triangle else 'url(#arrow)'
        element(self.svg, 'polyline', **attrs)
        if label:
            x, y, w = label_at
            self.text(x, y, w, 52, label, size=14, color=MUTED)

    def note(self, x, y, w, h, title, body):
        self.box(x, y, w, h, title, body, tint=AMBER, kind='note')

    def sequence(self, actors, bottom=780):
        xs = [140 + i * (1320 / (len(actors)-1)) for i in range(len(actors))]
        for x, title in zip(xs, actors):
            self.box(x-105, 140, 210, 74, title, kind='')
            self.edge([(x,214),(x,bottom)], dashed=True, arrow=False)
        return xs

    def message(self, xs, source, target, y, text, response=False):
        left, right = sorted((xs[source], xs[target]))
        self.edge([(xs[source],y),(xs[target],y)], dashed=response)
        self.text(left+12, y-44, right-left-24, 42, text, size=13)



# Explicit model reviewed against the summary integration, based on bb5b28d.
p = Page('overview', '01 / Team summary storage flow', 'The session component owns temporary data. System passes the completed DTO to permanent storage.')
p.box(45,165,340,185,'Frontend','Start / pause / stop\nHistory and Past Sessions\nHTTP action + content')
p.box(475,165,390,185,'System','Authenticates owner and role\nCoordinates session and DB managers\nConfirms commit before cleanup')
p.box(965,165,590,185,'UserSessionCoordinator','Owns session lifecycle and pending summaries\nUses StopSession / GenerateSummary\nSessionSummaryForDB is the handoff')
p.edge([(385,255),(475,255)],'HTTP',(396,218,76))
p.edge([(865,255),(965,255)],'calls',(880,218,75))
p.box(475,470,390,195,'DataBaseManager','Implements IDataBaseManager\nReceives summary; stores and fetches\nSessionRepository owns SQLite SQL\nNever reads or deletes temp files',GREEN)
p.edge([(665,350),(665,470)],'summary save / history read',(680,393,265))
p.box(965,470,590,195,'UserSessionDataManager','Owns temporary session JSON files\nAtomic replacement + fsync\nRetains frozen summary for retry\nDeletes when session coordinator requests it',GREEN)
p.edge([(1260,350),(1260,470)],'temporary storage operations',(1272,394,285))
p.note(45,745,760,155,'Permanent information','New sessions store exactly the supplied summary fields.\nExisting SQL records and their detailed activity remain readable.')
p.note(865,745,690,155,'No new AI model','Scores/productivity come from the session component.\nOptional returned analysis is stored against the original session.')

p = Page('classes','02 / Runtime classes and interfaces','System calls both managers. The database component has no dependency on the session component.')
p.box(40,145,400,200,'main.py','create_app(system)\nBearer extraction and HTTP errors\nPOST /backend; checkpoint task',kind='module')
p.box(545,145,445,200,'System','db_manager: IDataBaseManager\nfor_user(); run_user_session()\nsend_to_db_manager(data, user_id)\nrun_past_session(); checkpoint()',kind='class')
p.box(1090,145,470,200,'UserSessionCoordinator','user_session_manager()\nend_user_session(); pending_summaries\ndelete_old_session(session_id)',kind='class')
p.edge([(440,245),(545,245)],'calls',(451,209,80))
p.edge([(990,245),(1090,245)],'calls',(1001,209,85))
p.box(545,455,445,200,'IDataBaseManager','save_session(user_id, summary)\nget_history(user_id)\nget_session_details(user_id, id)\nCredentials, preferences, AI results',kind='interface')
p.edge([(765,345),(765,455)],'storage boundary',(778,390,240))
p.box(545,775,445,140,'DataBaseManager','repository: SessionRepository\nImplements supplied-data persistence',GREEN,'class')
p.edge([(765,775),(765,655)],'implements',(780,699,220),dashed=True,triangle=True)
p.box(40,775,400,140,'SessionRepository','SQLite connections + transactions\nOwner-scoped queries',GREEN,'class')
p.edge([(545,845),(440,845)],'calls',(452,804,80))
p.box(1090,455,470,175,'UserSessionDataManager','Atomic temporary JSON\nFrozen summary for retry\ndelete_current_session_json()',GREEN,'class')
p.edge([(1325,345),(1325,455)],'uses',(1340,390,170))
p.box(1090,775,470,140,'SessionSummaryForDB','Team dataclass: 12 fields\nProduced by GenerateSummary',kind='dataclass')
p.note(40,455,400,200,'Other existing components','PastSessionManager formats History.\nSettings validates preferences.\nBackendRequests builds responses.\nAll receive data through System.')

p = Page('finalization','03 / Completion, commit, and cleanup','System coordinates the order; file deletion remains inside the session component.')
xs = p.sequence(['System','Session manager','Temp manager','DB manager / SQL'],bottom=775)
p.message(xs,0,1,255,'end_user_session / timer expiry')
p.message(xs,1,2,325,'Freeze end time and summary in JSON')
p.message(xs,1,0,395,'Return SessionSummaryForDB',True)
p.message(xs,0,3,465,'send_to_db_manager: save_session(owner, summary)')
p.message(xs,3,0,535,'Return only after commit / verified retry',True)
p.message(xs,0,1,605,'delete_old_session(session_id)')
p.message(xs,1,2,675,'delete_current_session_json(session_id)')
p.message(xs,1,0,745,'Cleanup complete; remove pending entry',True)
p.note(42,820,475,115,'Database failure','Keep terminal JSON and frozen summary.\nRetry via System request/checkpoint/restart.')
p.note(558,820,480,115,'Cleanup failure','Retry the same summary without duplicating it.\nExisting analysis remains attached.')
p.note(1078,820,480,115,'Durable boundary','A later error cannot restore a running session.\nDifferent content with the same ID is rejected.')

p = Page('sql-model','04 / Persistent data and DTO mapping','No schema migration is needed. Existing detailed archives stay readable alongside new summary-only records.')
p.box(45,155,610,345,'SessionSummaryForDB','session_id: int; session_topic: str\nsession_start_time; session_end_time\nset_session_duration; actual_session_duration\nproductive_time; session_score\nnumber_of_tabs; time_spent_on_tabs\nmost_used_tab; most_often_blocked\n\nDurations: seconds; timestamps preserved',kind='dataclass')
p.box(890,155,665,345,'sessions','PK (user_id, id); FK user_id -> users.id\nTopic, status, start/end, duration columns\npayload.source_summary retains all DTO fields\npayload.detail_level = summary\nsummary stores the History display mapping\nNew DTOs do not supply visits or events',GREEN,'table')
p.edge([(655,325),(890,325)],'normalize supplied data',(674,280,203))
p.box(45,605,450,220,'users / access_keys','Profiles own sessions\nHashed keys resolve user + role\nSystem supplies authenticated owner\nThe DTO has no caller-selected user_id',GREEN,'tables')
p.box(575,605,450,220,'analyses','PK (user_id, session_id)\nFK -> sessions(user_id, id)\nOptional result and updated_at\nSeparate from immutable DTO',GREEN,'table')
p.box(1105,605,450,220,'Existing data','visits / events: older detailed records\npreferences: settings + blocklist\nlegacy_imports: original sources\nExisting records are preserved',GREEN,'tables')
p.text(45,875,1500,54,'Summary-only does not mean zero activity: unavailable visits, pauses, and event details are not invented.',size=21,bold=True)

p = Page('states','05 / Lifecycle and persistence are separate','The DTO arrives after completion; its storage status can still be pending.')
p.box(45,170,420,155,'Running / paused','Session coordinator owns active state\nTemporary manager writes checkpoints')
p.box(590,170,420,155,'Ended / pending','End time and DTO are durable in JSON\nSystem attempts permanent save',AMBER)
p.box(1135,170,420,155,'Saved','SQL contains the summary\nTemporary JSON has been removed',GREEN)
p.edge([(465,245),(590,245)],'stop / expiry',(475,202,113))
p.edge([(1010,245),(1135,245)],'commit + delete',(1018,202,115))
p.edge([(800,325),(800,430),(965,430),(965,325)],'failure: retain and retry',(820,438,300))
p.note(45,570,705,225,'Restart recovery','Pending DTO: replay its frozen values.\nUnfinished work: close at the saved checkpoint.\nUnknown offline time is excluded.\nNo guessing of owner from shared legacy files.')
p.note(840,570,715,225,'Identity and timing','Large integer IDs preserve the team DTO contract.\nOwner + session ID scopes SQL and retries.\nActual duration follows the team wall-time calculation.\nA paused session can have a longer actual duration.')

p = Page('history-ai','06 / History, dashboard, and analysis','Permanent storage receives and returns data only; every application call goes through System.')
xs = p.sequence(['History + tab','System','DB manager / SQL','AI component'],bottom=770)
p.message(xs,0,1,255,'get_sessions / get_past_sessions / details')
p.message(xs,1,2,325,'get_history(owner) / get_session_details(owner, id)')
p.message(xs,2,1,395,'Saved summary (plus legacy details if present)',True)
p.message(xs,1,0,465,'Same records for History and the new tab',True)
p.message(xs,3,1,535,'User-scoped AI key: get_ai_session')
p.message(xs,1,2,605,'Read saved input using original owner/session')
p.message(xs,3,1,675,'save_session_analysis(session_id, result)')
p.message(xs,1,2,745,'Store optional result against original record')
p.note(45,810,700,120,'Honest presentation','Summary-only records offer summary JSON/CSV.\nDetailed visits/events remain available for older archives.')
p.note(845,810,710,120,'Existing AI workflow','No new model is added. The evaluator is still a stub.\nDashboard remains usable without returned analysis.')

p = Page('migration','07 / Integration and existing data','Integration branch starts directly at the colleague’s StopSession commit bb5b28d.')
p.box(45,170,455,230,'Local recovery snapshot','backup/sql-before-team-summary-20260915\nCommit 07dd303 preserves earlier work\nNo old source work was discarded\nNo changes were pushed',AMBER,'Git')
p.box(575,170,455,230,'Current integration','feature/sql-summary-integration\nTeam session classes retained\nSQL summary storage + History added\nDTO class fields unchanged',GREEN,'Git')
p.box(1105,170,450,230,'Database continuity','Same configured SQLite file\nNo new server or schema upgrade\nExisting summaries/visits remain readable\nUser-scoped keys remain valid',GREEN,'storage')
p.note(45,560,710,230,'Legacy JSON imports','Stop the backend before importing.\nUse DataBase.manage import-legacy USER_ID SOURCE.\nAssign the actual owner explicitly.\nSources remain untouched; imports are repeatable.')
p.note(845,560,710,230,'Team boundary','UserSessionDataManager owns temporary files.\nUserSessionCoordinator requests their deletion.\nDataBaseManager owns permanent summaries.\nSystem coordinates save, acknowledgment, and reads.')

OUT.joinpath('uml').mkdir(exist_ok=True)
for page in PAGES:
    E.ElementTree(page.svg).write(OUT / 'uml' / (page.slug + '.svg'), encoding='utf-8', xml_declaration=True)
E.ElementTree(PAGES[0].svg).write(OUT / 'BackendUML.svg', encoding='utf-8', xml_declaration=True)
E.indent(BOOK, space='  ')
E.ElementTree(BOOK).write(OUT / 'BackendUML.drawio', encoding='utf-8', xml_declaration=True)
links = ''.join(f'<a href="#{p.slug}">{p.title}</a>' for p in PAGES)
slides = ''.join(f'<section id="{p.slug}"><img src="uml/{p.slug}.svg" alt="{p.title}"></section>' for p in PAGES)
OUT.joinpath('BackendUML.html').write_text('''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Grove — SQL session architecture</title><style>
*{box-sizing:border-box}body{margin:0;background:#f5f4f7;color:#292630;font:15px system-ui,sans-serif}header{padding:24px 32px;background:white;border-bottom:1px solid #e7e4ec}h1{margin:0 0 8px;font-size:24px}header p{margin:0;color:#746f7d}nav{display:flex;flex-wrap:wrap;gap:8px;padding:20px 32px}a{color:#55438d;background:#f1edf8;text-decoration:none;padding:8px 12px;border-radius:6px}section{max-width:1600px;margin:20px auto;background:white;box-shadow:0 2px 12px #29263012}img{display:block;width:100%;height:auto}section:target{outline:2px solid #6855a3}@page{size:16in 10in;margin:0}@media print{header,nav{display:none}body{background:white}section{margin:0;box-shadow:none;break-after:page;width:16in;height:10in}section:last-child{break-after:auto}img{width:16in;height:10in}}
</style></head><body><header><h1>Grove / SQL session architecture</h1><p>Team walkthrough · 15 September 2026 · Current local implementation · Print to PDF or edit BackendUML.drawio</p></header><nav>''' + links + '</nav>' + slides + '</body></html>', encoding='utf-8')
print(f'Generated {len(PAGES)} editable pages, SVGs, and the HTML walkthrough.')
