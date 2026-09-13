"""
Patch 6: OS File Descriptor & Socket Starvation Guard
Prevents OS File Descriptor Exhaustion (OSError: [Errno 24] Too many open files).
Monitors POSIX ulimit limits and automatically clamps safe concurrency bounds.
"""
import logging

logger = logging.getLogger("BehavioralEvasion.OSResourceGuard")


class OSResourceGuard:
    """
    Prevents OS File Descriptor Exhaustion (OSError: [Errno 24] Too many open files).
    Monitors POSIX ulimit limits and automatically clamps safe concurrency bounds.
    """
    def __init__(self) -> None:
        pass

    def check_os_limits(self, concurrency_estimate: int = 50) -> int:
        """Validates limits and clamps maximum safe concurrency pool size."""
        logger.info("OSResourceGuard: Validating OS environment resource boundaries.")
        soft_limit = 8192
        hard_limit = 8192

        try:
            import resource
            soft_limit, hard_limit = resource.getrlimit(resource.RLIMIT_NOFILE)
            logger.info(f"OSResourceGuard: POSIX ulimit -n detected -> Soft: {soft_limit}, Hard: {hard_limit}")

            if soft_limit < 4096 and soft_limit < hard_limit:
                new_soft = min(4096, hard_limit)
                try:
                    resource.setrlimit(resource.RLIMIT_NOFILE, (new_soft, hard_limit))
                    soft_limit = new_soft
                except Exception as ex:
                    logger.warning(f"OSResourceGuard: Unable to auto-raise soft file descriptor ulimit: {ex}")
        except ImportError:
            logger.info("OSResourceGuard: Non-POSIX platform. Defaulting to standard safety parameters.")

        # Estimate safe bounds (Chromium processes consume around 20 file descriptors)
        safe_concurrency_max = max(1, soft_limit // 20)

        if concurrency_estimate > safe_concurrency_max:
            logger.warning(
                f"OSResourceGuard: High Concurrency Danger! Requested {concurrency_estimate} workers, "
                f"but ulimit suggests a safe cap of {safe_concurrency_max} to avoid fd starvation."
            )
            return safe_concurrency_max
        return concurrency_estimate
