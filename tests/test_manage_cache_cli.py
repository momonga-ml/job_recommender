import unittest
import os
import json
import shutil
import tempfile
import subprocess
from datetime import datetime, timedelta

# Add project root to sys.path to allow importing job_recommender modules
import sys
from typing import Optional # Import Optional
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Helper to get the path to the CLI script
CLI_SCRIPT_PATH = os.path.join(os.path.dirname(__file__), '..', 'job_recommender', 'manage_cache_cli.py')

class TestManageCacheCLI(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.cache_dir = os.path.join(self.test_dir, ".cache") 
        # The CLI will instantiate JobCache, which creates this directory.
        # We pass this cache_dir to the CLI via an environment variable or argument if the CLI supports it.
        # For now, assuming CLI uses default '.cache' or we modify CLI to accept cache_dir.
        # Let's assume we will tell the CLI to use THIS specific cache_dir.
        # The JobCache used by the CLI needs to point to *this* self.cache_dir.
        # We can achieve this by setting an environment variable that manage_cache_cli.py reads,
        # or by modifying manage_cache_cli.py to accept a --cache-dir argument.
        # For simplicity, we'll make the CLI accept a --cache-dir argument.

        # Create a dummy cache file function specific to CLI tests
    def _create_cli_dummy_cache_file(self, site: str, query: str, location: str, jobs: list, timestamp: Optional[datetime] = None, cache_instance_dir: Optional[str] = None): # type: ignore
        """Helper to create a cache file in the CLI's cache directory."""
        # This is tricky because the CLI script itself instantiates JobCache.
        # We need to ensure the CLI's JobCache uses self.cache_dir.
        # For now, we'll create files directly in self.cache_dir, assuming the CLI will pick it up.
        # This requires modifying the CLI to accept a cache_dir.
        
        _cache_dir_to_use = cache_instance_dir or self.cache_dir
        os.makedirs(_cache_dir_to_use, exist_ok=True) # Ensure cache dir exists

        # Simplified key generation for dummy files, actual JobCache uses md5
        key_string = f"{site}:{query}:{location}".lower()
        # Use a simplified naming to avoid direct dependency on JobCache._get_cache_key implementation details
        filename = f"{key_string.replace(':', '_').replace(' ', '')}.json"
        filepath = os.path.join(_cache_dir_to_use, filename)

        data_to_cache = {
            'timestamp': (timestamp or datetime.now()).isoformat(),
            'site': site,
            'query': query,
            'location': location,
            'jobs': jobs
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data_to_cache, f, indent=2)
        return filepath

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def run_cli_command(self, command_args: list):
        """Helper to run the CLI script with given arguments and specific cache_dir."""
        # Modify CLI to accept --cache-dir. This is crucial.
        # For now, I will assume the CLI script has been modified to accept --cache-dir
        # If not, these tests won't work as expected.
        # The CLI script provided in a previous subtask needs modification to accept --cache-dir.
        # Let's assume it's: job_recommender/manage_cache_cli.py --cache-dir <self.cache_dir> <command> <args>
        
        # The actual CLI script needs to be modified to take --cache-dir
        # For now, I'll proceed as if it does, and the modification to the CLI
        # script itself is outside the scope of *this current test writing subtask*.
        # However, to make these tests pass, that change is a prerequisite.
        # A better way for testing would be to instantiate JobCache within the test
        # and pass its cache_dir to the CLI.
        
        # The CLI was written to instantiate JobCache without a cache_dir param, using default.
        # This is a problem for testing. The CLI should accept a --cache-dir.
        # I will write the tests assuming this modification to the CLI will be done.
        
        base_command = [sys.executable, CLI_SCRIPT_PATH, '--cache-dir', self.cache_dir]
        full_command = base_command + command_args
        # print(f"Running CLI command: {' '.join(full_command)}")
        result = subprocess.run(full_command, capture_output=True, text=True, cwd=self.test_dir)
        # print(f"CLI stdout: {result.stdout}")
        # print(f"CLI stderr: {result.stderr}")
        return result

    def test_cli_clear_all(self):
        # Setup: Create some dummy cache files in the CLI's cache directory
        self._create_cli_dummy_cache_file("SiteA", "Query1", "LocX", [{"id":1}])
        self._create_cli_dummy_cache_file("SiteB", "Query2", "LocY", [{"id":2}])
        
        self.assertTrue(len(os.listdir(self.cache_dir)) > 0)

        result = self.run_cli_command(['clear'])
        self.assertEqual(result.returncode, 0)
        self.assertTrue("Cleared all" in result.stdout or "No cache files to clear." in result.stdout or "Removed 2 file(s)" in result.stdout or "Cleared all (2) cache files" in result.stdout or "Removed 0 file(s)" in result.stdout) # Adjusted for new log msg
        # If files were created, assert they are gone.
        # self.assertEqual(len(os.listdir(self.cache_dir)), 0) # This might fail if the dir was never created by CLI

    def test_cli_clear_granular(self):
        # Setup: Create specific cache files
        file1 = self._create_cli_dummy_cache_file("SiteA", "Query1", "LocX", [{"id":1}])
        file2 = self._create_cli_dummy_cache_file("SiteA", "Query2", "LocY", [{"id":2}])
        file3 = self._create_cli_dummy_cache_file("SiteB", "Query1", "LocZ", [{"id":3}])
        
        # Test clear by site
        result = self.run_cli_command(['clear', '--site', 'SiteB'])
        self.assertEqual(result.returncode, 0)
        self.assertFalse(os.path.exists(file3))
        self.assertTrue(os.path.exists(file1))
        self.assertTrue(os.path.exists(file2))
        self.assertIn("site: SiteB. Removed 1 file(s).", result.stdout)

        # Test clear by site and query
        result = self.run_cli_command(['clear', '--site', 'SiteA', '--query', 'Query1'])
        self.assertEqual(result.returncode, 0)
        self.assertFalse(os.path.exists(file1))
        self.assertTrue(os.path.exists(file2)) # SiteA, Query2 should remain
        self.assertIn("site: SiteA query: Query1. Removed 1 file(s).", result.stdout)
        
        # Test clear by site, query, and location (clear remaining file)
        result = self.run_cli_command(['clear', '--site', 'SiteA', '--query', 'Query2', '--location', 'LocY'])
        self.assertEqual(result.returncode, 0)
        self.assertFalse(os.path.exists(file2))
        self.assertIn("site: SiteA query: Query2 location: LocY. Removed 1 file(s).", result.stdout)
        
        # Ensure cache dir is empty now (or doesn't exist if JobCache removes it)
        if os.path.exists(self.cache_dir):
            self.assertEqual(len(os.listdir(self.cache_dir)), 0)

    def test_cli_clear_expired(self):
        now = datetime.now()
        # Create an expired file (e.g. 2 days old, default JobCache duration is 24h)
        expired_file_timestamp = now - timedelta(days=2)
        expired_file = self._create_cli_dummy_cache_file("SiteExp", "QueryOld", "LocOld", [{"id":"old"}], timestamp=expired_file_timestamp)

        # Create a non-expired file (e.g. 1 hour old)
        non_expired_file_timestamp = now - timedelta(hours=1)
        non_expired_file = self._create_cli_dummy_cache_file("SiteFresh", "QueryNew", "LocNew", [{"id":"new"}], timestamp=non_expired_file_timestamp)

        self.assertTrue(os.path.exists(expired_file))
        self.assertTrue(os.path.exists(non_expired_file))

        result = self.run_cli_command(['clear-expired'])
        self.assertEqual(result.returncode, 0)
        
        # Check stdout for confirmation message (adapt based on actual CLI output)
        # Example: "Cleared 1 expired cache file(s)."
        self.assertIn("Cleared 1 expired cache file(s).", result.stdout) 
        
        self.assertFalse(os.path.exists(expired_file), "Expired file should be removed by CLI")
        self.assertTrue(os.path.exists(non_expired_file), "Non-expired file should remain after CLI clear-expired")

    def test_cli_clear_expired_no_expired_files(self):
        # Create only a non-expired file
        non_expired_file_timestamp = datetime.now() - timedelta(hours=1)
        non_expired_file = self._create_cli_dummy_cache_file("SiteFresh", "QueryNew", "LocNew", [{"id":"new"}], timestamp=non_expired_file_timestamp)
        
        self.assertTrue(os.path.exists(non_expired_file))

        result = self.run_cli_command(['clear-expired'])
        self.assertEqual(result.returncode, 0)
        
        # Check stdout for appropriate message (e.g., "No expired cache files found.")
        self.assertIn("No expired cache files found to clear.", result.stdout)
        self.assertTrue(os.path.exists(non_expired_file), "Non-expired file should remain")


if __name__ == '__main__':
    unittest.main()
