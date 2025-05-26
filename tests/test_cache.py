import unittest
import os
import json
import shutil
import tempfile
import time
from datetime import datetime, timedelta

# Add project root to sys.path to allow importing job_recommender modules
import sys
from typing import Optional # Import Optional
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from job_recommender.cache import JobCache

class TestJobCache(unittest.TestCase):

    def setUp(self):
        # Create a temporary directory for the cache
        self.test_dir = tempfile.mkdtemp()
        # print(f"setUp: Created temp_dir: {self.test_dir}")
        self.cache_dir = os.path.join(self.test_dir, ".cache")
        
        # Basic JobCache instance
        self.job_cache = JobCache(cache_dir=self.cache_dir, cache_duration=24) # Default 24h duration

        # Instance for testing max_files
        self.job_cache_max_files = JobCache(cache_dir=self.cache_dir, cache_duration=24, max_cache_files=3)

        # Instance for testing max_size
        self.job_cache_max_size = JobCache(cache_dir=self.cache_dir, cache_duration=24, max_cache_size_bytes=1024) # 1KB limit

        # Ensure the main cache dir for JobCache instances is created by JobCache itself if it doesn't exist
        # For direct manipulations, we might need to create self.cache_dir if JobCache doesn't do it.
        # However, JobCache._ensure_cache_dir() should handle this.


    def tearDown(self):
        # Remove the temporary directory and all its contents
        # print(f"tearDown: Removing temp_dir: {self.test_dir}")
        shutil.rmtree(self.test_dir)

    def _create_dummy_cache_file(self, cache_instance: JobCache, site: str, query: str, location: str, jobs: list, timestamp: Optional[datetime] = None): # type: ignore
        """Helper to create a cache file directly for testing purposes."""
        cache_key = cache_instance._get_cache_key(site, query, location)
        cache_file_path = cache_instance._get_cache_file(cache_key)
        
        # Ensure cache directory exists (it should due to JobCache init, but good for direct calls)
        os.makedirs(os.path.dirname(cache_file_path), exist_ok=True)

        data_to_cache = {
            'timestamp': (timestamp or datetime.now()).isoformat(),
            'site': site,
            'query': query,
            'location': location,
            'jobs': jobs
        }
        with open(cache_file_path, 'w', encoding='utf-8') as f:
            json.dump(data_to_cache, f, indent=2)
        # print(f"Created dummy file: {cache_file_path} with timestamp {data_to_cache['timestamp']}")
        return cache_file_path

    def test_cache_creation_and_retrieval(self):
        self.job_cache.cache_jobs("SiteA", "Query1", "LocationX", [{"title": "Job1"}])
        cached_jobs = self.job_cache.get_cached_jobs("SiteA", "Query1", "LocationX")
        self.assertIsNotNone(cached_jobs)
        self.assertEqual(len(cached_jobs), 1)
        self.assertEqual(cached_jobs[0]['title'], "Job1")

    def test_cache_expiration(self):
        # Create a cache entry that is already expired
        expired_time = datetime.now() - timedelta(hours=48) # Older than 24h default
        self._create_dummy_cache_file(self.job_cache, "SiteB", "Query2", "LocationY", [{"title": "Job2"}], timestamp=expired_time)
        
        cached_jobs = self.job_cache.get_cached_jobs("SiteB", "Query2", "LocationY")
        self.assertIsNone(cached_jobs, "Expired cache should return None")

    def test_lru_eviction_max_files(self):
        # Initial population of the cache up to its limit (max_cache_files = 3)
        self.job_cache_max_files.cache_jobs("Site1", "QueryA", "Loc1", [{"id": 1}]) # Should be oldest initially
        time.sleep(0.2) # Ensure distinct timestamp
        self.job_cache_max_files.cache_jobs("Site2", "QueryB", "Loc2", [{"id": 2}])
        time.sleep(0.2) # Ensure distinct timestamp
        self.job_cache_max_files.cache_jobs("Site3", "QueryC", "Loc3", [{"id": 3}]) # Should be newest among these three
        time.sleep(0.2) # Ensure Site3's timestamp is distinct before next operation

        # Cache is now full (3 files: Site1, Site2, Site3).
        # Adding Site4 should evict Site1 (the oldest).
        # Order by st_atime (oldest to newest): Site1, Site2, Site3
        self.job_cache_max_files.cache_jobs("Site4", "QueryD", "Loc4", [{"id": 4}]) # Site4 becomes newest
        time.sleep(0.2) # Allow eviction to complete and timestamps to settle

        # After adding Site4: Site1 evicted. Cache should contain Site2, Site3, Site4.
        # LRU order (oldest to newest): Site2, Site3, Site4
        self.assertIsNone(self.job_cache_max_files.get_cached_jobs("Site1", "QueryA", "Loc1"), "File for Site1 should be evicted")
        self.assertIsNotNone(self.job_cache_max_files.get_cached_jobs("Site2", "QueryB", "Loc2"), "File for Site2 should exist")
        time.sleep(0.2) # Update Site2's access time by getting it, then pause
        self.assertIsNotNone(self.job_cache_max_files.get_cached_jobs("Site3", "QueryC", "Loc3"), "File for Site3 should exist")
        time.sleep(0.2) # Update Site3's access time
        self.assertIsNotNone(self.job_cache_max_files.get_cached_jobs("Site4", "QueryD", "Loc4"), "File for Site4 should exist")
        time.sleep(0.2) # Update Site4's access time

        # At this point, after the assertions, the access times have been updated.
        # The LRU order (oldest to newest) due to the above get_cached_jobs calls should be:
        # The first one accessed in the assertions (Site2) is now the oldest among them,
        # then Site3, then Site4 is the newest from these get() calls.
        # So, effectively: Site2, Site3, Site4. (This matches the creation order after Site1 was evicted)

        # Now, access "Site2" again to make it the most recently used among Site2, Site3, Site4.
        # Current LRU (oldest to newest): Site2, Site3, Site4
        self.job_cache_max_files.get_cached_jobs("Site2", "QueryB", "Loc2")
        time.sleep(0.2) # Crucial sleep: allow Site2's access time to be updated and be distinct.
                        # After this, LRU order (oldest to newest): Site3, Site4, Site2

        # Adding "Site5" should cause "Site3" (now the oldest) to be evicted.
        self.job_cache_max_files.cache_jobs("Site5", "QueryE", "Loc5", [{"id": 5}])
        time.sleep(0.2) # Allow eviction to complete

        self.assertIsNone(self.job_cache_max_files.get_cached_jobs("Site3", "QueryC", "Loc3"), "Site3 should be evicted after Site2 was accessed and Site5 added")
        self.assertIsNotNone(self.job_cache_max_files.get_cached_jobs("Site2", "QueryB", "Loc2"))
        self.assertIsNotNone(self.job_cache_max_files.get_cached_jobs("Site4", "QueryD", "Loc4"))
        self.assertIsNotNone(self.job_cache_max_files.get_cached_jobs("Site5", "QueryE", "Loc5"))
        
        # Verify file count
        files_in_cache = [f for f in os.listdir(self.cache_dir) if f.endswith('.json')]
        self.assertEqual(len(files_in_cache), 3, "Cache should contain exactly max_cache_files files")

    def test_lru_eviction_max_size(self):
        # Adjusted limit and data sizes for clearer test scenario
        # Target: file1 and file2 evicted, file3 and file4 remain.
        # max_cache_size_bytes = 700
        # Override self.job_cache_max_size to use this new limit for this test
        self.job_cache_max_size.max_cache_size_bytes = 700 # Adjusted limit

        # File 1 (small, oldest) ~180-200B with indent=2
        file1_data = "small_data_content" #len 20
        file1_path = self._create_dummy_cache_file(self.job_cache_max_size, "SiteS1", "QueryS_A", "LocS1", [{"id": 1, "data": file1_data}])
        time.sleep(0.01) # ensure different st_atime

        # File 2 (medium) ~200-250B
        file2_data = "medium_data_to_ensure_eviction_of_this_file" #len 46
        file2_path = self._create_dummy_cache_file(self.job_cache_max_size, "SiteS2", "QueryS_B", "LocS2", [{"id": 2, "data": file2_data}])
        time.sleep(0.01)

        # File 3 (large enough to remain with file4) ~300-350B
        file3_data = 'x' * 150 
        file3_path = self._create_dummy_cache_file(self.job_cache_max_size, "SiteS3", "QueryS_C", "LocS3", [{"id": 3, "data": file3_data}])
        time.sleep(0.01)
        
        # At this point, no eviction has occurred. Sizes are estimates for planning.
        # file1_size = os.path.getsize(file1_path) # ~200
        # file2_size = os.path.getsize(file2_path) # ~230
        # file3_size = os.path.getsize(file3_path) # ~330
        # Initial total: ~200+230+330 = ~760. This is > 700, but _enforce_cache_limits hasn't run on job_cache_max_size yet with all these files.

        # File 4 (large enough to remain with file3, newest) ~300-350B
        # This call to cache_jobs will trigger _enforce_cache_limits
        file4_data = 'y' * 150
        self.job_cache_max_size.cache_jobs("SiteS4", "QueryS_D", "LocS4", [{"id": 4, "data": file4_data}])
        file4_path = self.job_cache_max_size._get_cache_file(self.job_cache_max_size._get_cache_key("SiteS4", "QueryS_D", "LocS4"))
        
        # Expected state after cache_jobs("SiteS4",...) and _enforce_cache_limits():
        # Files initially considered (approx sizes with indent=2):
        # file1: ~200B (SiteS1, QueryS_A, LocS1, data len 20)
        # file2: ~230B (SiteS2, QueryS_B, LocS2, data len 46)
        # file3: ~330B (SiteS3, QueryS_C, LocS3, data 'x'*150)
        # file4: ~330B (SiteS4, QueryS_D, LocS4, data 'y'*150) - newest
        # Total ~1090B. Limit = 700B.
        # LRU order for eviction: file1, file2, file3, file4.
        # 1. Evict file1 (200B). Remaining: 1090-200=890B. Still > 700.
        # 2. Evict file2 (230B). Remaining: 890-230=660B. Now <= 700. Stop.
        # Expected to remain: file3, file4.

        self.assertFalse(os.path.exists(file1_path), "File1 should be evicted by size")
        self.assertFalse(os.path.exists(file2_path), "File2 should be evicted by size")
        self.assertTrue(os.path.exists(file3_path), "File3 should remain")
        self.assertTrue(os.path.exists(file4_path), "File4 (newest) should remain")

        final_cache_files = [os.path.join(self.cache_dir, f) for f in os.listdir(self.cache_dir) if f.endswith('.json')]
        final_size = sum(os.path.getsize(f) for f in final_cache_files)
        self.assertTrue(final_size <= self.job_cache_max_size.max_cache_size_bytes, f"Final cache size {final_size} should be within limit {self.job_cache_max_size.max_cache_size_bytes} (actual files: {final_cache_files})")
        # Also assert that exactly file3 and file4 are present
        self.assertIn(file3_path, final_cache_files)
        self.assertIn(file4_path, final_cache_files)
        self.assertEqual(len(final_cache_files), 2, "Only file3 and file4 should remain")

    def test_clear_cache_granular_and_full(self):
        # Setup: Create several cache files
        file_s1q1l1 = self._create_dummy_cache_file(self.job_cache, "Site1", "Query1", "Loc1", [{"id": "s1q1l1"}])
        file_s1q1l2 = self._create_dummy_cache_file(self.job_cache, "Site1", "Query1", "Loc2", [{"id": "s1q1l2"}])
        file_s1q2l1 = self._create_dummy_cache_file(self.job_cache, "Site1", "Query2", "Loc1", [{"id": "s1q2l1"}])
        file_s2q1l1 = self._create_dummy_cache_file(self.job_cache, "Site2", "Query1", "Loc1", [{"id": "s2q1l1"}])

        # Test clearing by site
        self.job_cache.clear_cache(site="Site2")
        self.assertFalse(os.path.exists(file_s2q1l1), "File for Site2 should be cleared")
        self.assertTrue(os.path.exists(file_s1q1l1), "File for Site1 should remain")

        # Re-create Site2 file for next tests
        file_s2q1l1 = self._create_dummy_cache_file(self.job_cache, "Site2", "Query1", "Loc1", [{"id": "s2q1l1"}])

        # Test clearing by site and query
        self.job_cache.clear_cache(site="Site1", query="Query2")
        self.assertFalse(os.path.exists(file_s1q2l1), "File for Site1, Query2 should be cleared")
        self.assertTrue(os.path.exists(file_s1q1l1), "File for Site1, Query1 should remain")
        
        # Test clearing by site, query, and location
        self.job_cache.clear_cache(site="Site1", query="Query1", location="Loc2")
        self.assertFalse(os.path.exists(file_s1q1l2), "File for Site1, Query1, Loc2 should be cleared")
        self.assertTrue(os.path.exists(file_s1q1l1), "File for Site1, Query1, Loc1 should remain")

        # Test clearing non-existent query (should not fail, clears nothing relevant)
        self.job_cache.clear_cache(query="NonExistentQuery")
        self.assertTrue(os.path.exists(file_s1q1l1)) # Check a remaining file
        self.assertTrue(os.path.exists(file_s2q1l1)) # Check another remaining file

        # Test clearing all cache
        self.job_cache.clear_cache() # No arguments
        self.assertFalse(os.path.exists(file_s1q1l1), "All files should be cleared")
        self.assertFalse(os.path.exists(file_s2q1l1), "All files should be cleared")
        self.assertEqual(len(os.listdir(self.cache_dir)), 0, "Cache directory should be empty")

    def test_clear_expired_cache(self):
        # cache_duration for self.job_cache is 24 hours
        now = datetime.now()
        expired_time = now - timedelta(hours=48)
        non_expired_time = now - timedelta(hours=12)

        # Create an expired file
        file_expired = self._create_dummy_cache_file(self.job_cache, "SiteExp1", "QueryExp", "LocExp", [{"id": "exp"}], timestamp=expired_time)
        # Create a non-expired file
        file_non_expired = self._create_dummy_cache_file(self.job_cache, "SiteNonExp1", "QueryNonExp", "LocNonExp", [{"id": "non_exp"}], timestamp=non_expired_time)
        # Create another non-expired file using cache_jobs to ensure it uses current time
        self.job_cache.cache_jobs("SiteNonExp2", "QueryNonExp2", "LocNonExp2", [{"id": "non_exp2"}])
        file_non_expired_2 = self.job_cache._get_cache_file(self.job_cache._get_cache_key("SiteNonExp2", "QueryNonExp2", "LocNonExp2"))


        self.assertTrue(os.path.exists(file_expired))
        self.assertTrue(os.path.exists(file_non_expired))
        self.assertTrue(os.path.exists(file_non_expired_2))

        self.job_cache.clear_expired_cache()

        self.assertFalse(os.path.exists(file_expired), "Expired file should be cleared")
        self.assertTrue(os.path.exists(file_non_expired), "Non-expired file should remain")
        self.assertTrue(os.path.exists(file_non_expired_2), "Second non-expired file should remain")
        
        # Test with a cache that has a very short expiration time
        short_lived_cache = JobCache(cache_dir=self.cache_dir, cache_duration=0.001) # approx 3.6 seconds
        file_short_exp = self._create_dummy_cache_file(short_lived_cache, "SiteShort1", "QueryShort", "LocShort", [{"id": "short_exp"}])
        time.sleep(5) # Wait for it to expire
        short_lived_cache.clear_expired_cache()
        self.assertFalse(os.path.exists(file_short_exp), "File in short-lived cache should be expired and cleared")


if __name__ == '__main__':
    unittest.main()
