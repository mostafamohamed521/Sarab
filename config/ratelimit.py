from django.core.cache import cache


def get_client_ip(request):
    # Prefer X-Forwarded-For only if you trust your proxy layer to set
    # it correctly; falls back to REMOTE_ADDR either way.
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', 'unknown')


def is_rate_limited(request, bucket, max_attempts=5, window_seconds=300):
    """
    Simple fixed-window counter per (bucket, client IP), backed by
    Django's cache (LocMemCache by default — fine for a single
    process; for multi-worker deployments point CACHES at Redis/
    Memcached so all workers share the same counter).

    Returns True if the caller should be blocked. Callers are expected
    to increment via record_attempt() only on the paths that matter
    (e.g. a failed login), not on every request.
    """
    key = f'ratelimit:{bucket}:{get_client_ip(request)}'
    count = cache.get(key, 0)
    return count >= max_attempts


def record_attempt(request, bucket, window_seconds=300):
    key = f'ratelimit:{bucket}:{get_client_ip(request)}'
    try:
        count = cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=window_seconds)
        count = 1
    return count
