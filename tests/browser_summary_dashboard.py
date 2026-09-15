"""Isolated real Edge extension check for the team's summary-only handoff."""
import json
from pathlib import Path
import shutil
import sys
import tempfile

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
sys.path.insert(0, str(root / '.preview-tools'))
from playwright.sync_api import sync_playwright, expect
from test_api import ApiTests

out = Path(tempfile.mkdtemp(prefix='summary-browser-', dir=root / '.preview-artifacts'))
ApiTests.setUpClass()
try:
    extension = out / 'Frontend'
    shutil.copytree(root / 'Frontend', extension)
    for name in ('api/backend.js', 'manifest.json'):
        path = extension / name
        path.write_text(path.read_text(encoding='utf-8').replace('127.0.0.1:8000', f'127.0.0.1:{ApiTests.port}'), encoding='utf-8')
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(str(out / 'profile'), channel='msedge', headless=True,
            args=[f'--disable-extensions-except={extension}', f'--load-extension={extension}'], accept_downloads=True)
        try:
            worker = next(iter(context.service_workers), None) or context.wait_for_event('serviceworker')
            eid = worker.url.split('/')[2]
            worker.evaluate("() => { chrome.idle.queryState = async () => 'active'; }")
            popup = context.new_page()
            errors = []
            popup.on('pageerror', lambda error: errors.append(str(error)))
            popup.goto(f'chrome-extension://{eid}/popup.html')
            popup.get_by_label('Access key').fill(ApiTests.alice_key)
            popup.get_by_role('button', name='Connect', exact=True).click()
            popup.get_by_label('What are you working on?').fill('Team DTO verification')
            popup.get_by_role('button', name='Start session', exact=True).click()
            expect(popup.get_by_role('button', name='Pause', exact=True)).to_be_visible()
            sid = ApiTests.request('get_active_session', key=ApiTests.alice_key)[1]['content']['id']
            popup.get_by_role('button', name='Pause', exact=True).click()
            expect(popup.get_by_role('heading', name='Session paused')).to_be_visible()
            popup.get_by_role('button', name='Resume session').click()
            popup.get_by_role('button', name='Stop session').click()
            expect(popup.get_by_role('heading', name='Session complete', exact=True)).to_be_visible()
            popup.get_by_role('button', name='View session details').click()
            expect(popup.get_by_role('heading', name='Session results')).to_be_visible()
            expect(popup.get_by_role('heading', name='Website visits')).to_have_count(0)
            with popup.expect_download() as downloaded:
                popup.get_by_role('button', name='Export JSON', exact=True).click()
            exported = json.loads(Path(downloaded.value.path()).read_text(encoding='utf-8'))
            assert exported['session']['source_summary']['session_id'] == sid
            with popup.expect_download() as downloaded:
                popup.get_by_role('button', name='Summary CSV', exact=True).click()
            assert 'session_topic' in Path(downloaded.value.path()).read_text(encoding='utf-8')
            with context.expect_page() as opened:
                popup.get_by_role('link', name='Past Sessions (opens in a new tab)').click()
            dashboard = opened.value
            dashboard.on('pageerror', lambda error: errors.append(str(error)))
            dashboard.get_by_role('button', name='Team DTO verification').click()
            expect(dashboard.get_by_role('heading', name='Session results')).to_be_visible()
            expect(dashboard.get_by_text('No AI analysis is available yet.', exact=False)).to_be_visible()
            with dashboard.expect_download() as downloaded:
                dashboard.get_by_role('button', name='Export JSON', exact=True).click()
            dashboard_export = json.loads(Path(downloaded.value.path()).read_text(encoding='utf-8'))
            assert dashboard_export == exported
            ApiTests.request('save_session_analysis', {'session_id': sid, 'analysis': {'summary': 'Fixture analysis'}}, ApiTests.ai_key)
            dashboard.get_by_role('button', name='Refresh', exact=True).click()
            expect(dashboard.get_by_text('Fixture analysis', exact=True)).to_be_visible()
            dashboard.get_by_label('Find a session').fill('no match')
            expect(dashboard.get_by_text('No sessions match your search.')).to_be_visible()
            dashboard.get_by_label('Find a session').fill('')
            dashboard.screenshot(path=str(out / 'dashboard.png'), full_page=True)
            dashboard.set_viewport_size({'width': 390, 'height': 844})
            assert dashboard.evaluate('document.documentElement.scrollWidth <= innerWidth')
            dashboard.screenshot(path=str(out / 'mobile.png'), full_page=True)
            # Controlled request failure, followed by a successful retry.
            dashboard.route('**/backend', lambda route: route.abort())
            dashboard.get_by_role('button', name='Refresh', exact=True).click()
            expect(dashboard.get_by_role('button', name='Retry', exact=True)).to_be_visible()
            dashboard.unroute('**/backend')
            dashboard.get_by_role('button', name='Retry', exact=True).click()
            expect(dashboard.get_by_role('button', name='Team DTO verification')).to_be_visible()
            dashboard.evaluate('(key) => chrome.storage.local.set({groveAccessKey: key})', ApiTests.bob_key)
            expect(dashboard.get_by_text('No past sessions yet.', exact=False)).to_be_visible()
            assert not errors, errors
            assert not list((Path(ApiTests.temp.name) / 'team-active').rglob('session_*.json'))
            print(json.dumps({'result': 'PASS', 'artifacts': str(out),
                'checks': ['real extension start/pause/resume/end', 'SQL summary persistence', 'session-owned cleanup',
                           'History and new-tab dashboard exports agree', 'summary CSV', 'AI fixture', 'search',
                           'narrow layout', 'error retry', 'empty owner', 'no page errors']}))
        finally:
            context.close()
finally:
    ApiTests.doClassCleanups()
