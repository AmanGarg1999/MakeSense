import { useState, useEffect, useCallback } from 'react';

// Get user ID from localStorage or generate one
export function getUserId() {
  let id = localStorage.getItem('makesense_user_id');
  if (!id) {
    id = '1'; // Default demo user
    localStorage.setItem('makesense_user_id', id);
  }
  return id;
}

export function useApi(url, options = {}) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await fetch(url, options);
      if (!response.ok) throw new Error(`API error: ${response.status}`);
      const json = await response.json();
      setData(json);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [url]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { data, loading, error, refetch: fetchData };
}
