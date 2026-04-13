"""CLI entry point — run the daily job once without starting the server."""

from app.config import get_settings
from app.scheduler import run_daily_job


def main():
    settings = get_settings()
    result = run_daily_job(settings)
    print(result)


if __name__ == "__main__":
    main()
