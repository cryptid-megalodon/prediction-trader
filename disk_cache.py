import os
import pickle
from datetime import datetime, timedelta
import hashlib

class DiskCache:
    def __init__(self, cache_dir="api_cache", expiry_hours=24):
        self.cache_dir = cache_dir
        self.expiry_delta = timedelta(hours=expiry_hours)
        os.makedirs(cache_dir, exist_ok=True)
    
    def _get_cache_path(self, key):
        # Use hash for filename to avoid invalid characters
        hashed_key = hashlib.md5(key.encode('utf-8')).hexdigest()
        return os.path.join(self.cache_dir, f"{hashed_key}.pkl")
    
    def get(self, key):
        cache_path = self._get_cache_path(key)
        if not os.path.exists(cache_path):
            return None
            
        try:
            with open(cache_path, 'rb') as f:
                cached_data = pickle.load(f)
                
            # Check if the cache has expired
            if datetime.now() - cached_data['timestamp'] > self.expiry_delta:
                return None
                
            return cached_data['data']
        except (pickle.PickleError, EOFError, KeyError):
            # Handle corrupted cache files
            if os.path.exists(cache_path):
                os.remove(cache_path)
            return None
    
    def set(self, key, data):
        cache_path = self._get_cache_path(key)
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump({
                    'timestamp': datetime.now(),
                    'data': data
                }, f)
        except (pickle.PickleError, IOError) as e:
            print(f"Cache write error: {e}")