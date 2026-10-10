"""Regression checks for first visits through workspace deep links."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch
import io

with patch.dict('os.environ', {'JWT_SECRET':'synthetic-test-secret','MULTICA_DEFAULT_USER_ID':'synthetic-user','MULTICA_DEFAULT_EMAIL':'test@example.invalid','MULTICA_DEFAULT_NAME':'Test'}):
    spec=importlib.util.spec_from_file_location('default_login',Path(__file__).with_name('default_login.py'))
    login=importlib.util.module_from_spec(spec);spec.loader.exec_module(login)


class DestinationTests(unittest.TestCase):
    def test_missing_expired_and_valid_sessions(self):
        self.assertFalse(login.authenticated(''))
        with patch.object(login.urllib.request, 'urlopen', side_effect=OSError('synthetic auth failure')):
            self.assertFalse(login.authenticated('multica_auth=expired'))
        with patch.object(login.urllib.request, 'urlopen', return_value=io.BytesIO(b'{"id":"synthetic-user"}')):
            self.assertTrue(login.authenticated('multica_auth=synthetic'))

    def test_workspace_deep_links_preserve_path_and_query(self):
        for path in ['/leo/issues','/leo/agents','/leo/chat?agent=synthetic']:
            self.assertEqual(login.destination(path),path)

    def test_login_paths_and_external_redirects_use_default_destination(self):
        for path in ['/','/login','//evil.invalid/leo/issues','https://evil.invalid/leo/issues','/leo/\\evil','/leo/issues\r\nX-Test: injected']:
            self.assertEqual(login.destination(path),'/leo/issues')


if __name__=='__main__':unittest.main()
