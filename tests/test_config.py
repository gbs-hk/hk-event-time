import unittest

from app.config import Config


class ConfigTests(unittest.TestCase):
    def test_normalizes_legacy_postgres_scheme(self):
        original = Config.DATABASE_URL
        try:
            Config.DATABASE_URL = "postgres://user:pass@host:5432/dbname"
            self.assertEqual(
                Config.normalized_database_url(),
                "postgresql+psycopg://user:pass@host:5432/dbname",
            )
        finally:
            Config.DATABASE_URL = original

    def test_adds_psycopg_driver_to_postgresql_scheme(self):
        original = Config.DATABASE_URL
        try:
            Config.DATABASE_URL = "postgresql://user:pass@host:5432/dbname"
            self.assertEqual(
                Config.normalized_database_url(),
                "postgresql+psycopg://user:pass@host:5432/dbname",
            )
        finally:
            Config.DATABASE_URL = original


if __name__ == "__main__":
    unittest.main()
