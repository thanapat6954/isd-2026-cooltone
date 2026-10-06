import unittest
from pathlib import Path

from lab10_fastapi.curriculum_app.main import app, index


class WebRoutingTests(unittest.TestCase):
    def test_root_redirects_to_real_thai_frontend(self):
        response = index()
        self.assertEqual(response.status_code, 307)
        self.assertEqual(response.headers['location'], '/frontend/')

    def test_frontend_and_both_question_contracts_are_registered(self):
        routes = {route.path: route for route in app.routes}
        self.assertIn('/frontend', routes)
        self.assertIn('POST', routes['/ask'].methods)
        self.assertIn('POST', routes['/api/ask'].methods)
        self.assertTrue((Path(routes['/frontend'].app.directory) / 'index.html').is_file())

    def test_backend_frontend_uses_same_origin(self):
        script = Path(__file__).resolve().parents[1] / 'frontend/app.js'
        text = script.read_text(encoding='utf-8')
        self.assertIn('window.location.origin', text)
        self.assertIn('startsWith("/frontend/")', text)

    def test_launcher_uses_bounded_elapsed_time_and_keeps_api_port_guard(self):
        text=(Path(__file__).resolve().parents[1]/'scripts/start_web.ps1').read_text(encoding='utf-8')
        self.assertIn('$StartupTimeoutSeconds = 60',text)
        self.assertIn('[DateTime]::UtcNow -lt $startupDeadline',text)
        self.assertIn('Port $Port is occupied; readiness check failed',text)
        self.assertIn('Assert-CurriculumBackend', text)
        checks = (Path(__file__).resolve().parents[1] / 'scripts/web_common.ps1').read_text(encoding='utf-8')
        self.assertIn('expectedModule', checks)
        self.assertIn('queryable_database_count', checks)
        self.assertIn('ollama_ready', checks)
        self.assertIn('Start-Process',text)
        self.assertIn('-WindowStyle Hidden',text)
        self.assertIn('$probeUrl = "http://127.0.0.1:$Port"',text)
        self.assertIn('$lastReadinessError = $_.Exception.Message',text)


if __name__ == '__main__':
    unittest.main()
