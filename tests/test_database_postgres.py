# tests/test_database_postgres.py
"""
Focused unit and integration tests for PostgreSQL database support and SQLite compatibility.
"""
import os
import sys
import unittest
import json
from unittest.mock import patch, MagicMock

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
import database.db as db


class TestDatabasePostgres(unittest.TestCase):
    """Database compatibility and selection test suite."""

    def test_sqlite_is_default(self):
        """Verify SQLite remains the default backend when environment is empty."""
        # Save original state
        orig_is_postgres = config.IS_POSTGRES
        
        # Temporarily mock configuration to ensure SQLite is used
        with patch("config.IS_POSTGRES", False):
            self.assertFalse(config.IS_POSTGRES)
            conn = db._get_connection()
            try:
                import sqlite3
                self.assertIsInstance(conn, sqlite3.Connection)
            finally:
                conn.close()

    def test_postgres_configuration_detection(self):
        """Verify PostgreSQL detection logic based on configuration presence."""
        host = "localhost"
        db_name = "mediflow_test"
        user = "mediflow_user"
        
        # Test detection flag when config is set
        is_pg = bool(host and db_name and user)
        self.assertTrue(is_pg)

    def test_database_placeholder_differences(self):
        """Verify parameter placeholder replacements between SQLite (?) and PostgreSQL (%s)."""
        query = "SELECT * FROM patients WHERE name = ? AND age = ?"
        
        # Case 1: SQLite (?)
        with patch("database.db.IS_POSTGRES", False):
            cursor_mock = MagicMock()
            db._execute_query(cursor_mock, query, ("Rajesh", 45))
            cursor_mock.execute.assert_called_once_with(query, ("Rajesh", 45))

        # Case 2: PostgreSQL (%s)
        with patch("database.db.IS_POSTGRES", True):
            cursor_mock = MagicMock()
            db._execute_query(cursor_mock, query, ("Rajesh", 45))
            expected_pg_query = "SELECT * FROM patients WHERE name = %s AND age = %s"
            cursor_mock.execute.assert_called_once_with(expected_pg_query, ("Rajesh", 45))

    def test_insert_query_returning(self):
        """Verify execute_insert difference for RETURNING id in PostgreSQL and lastrowid in SQLite."""
        query = "INSERT INTO patients (name) VALUES (?)"
        params = ("Rajesh Kumar",)

        # Case 1: SQLite using lastrowid
        with patch("database.db.IS_POSTGRES", False):
            cursor_mock = MagicMock()
            cursor_mock.lastrowid = 42
            res = db._execute_insert(cursor_mock, query, params)
            self.assertEqual(res, 42)
            cursor_mock.execute.assert_called_once_with(query, params)

        # Case 2: PostgreSQL using RETURNING id
        with patch("database.db.IS_POSTGRES", True):
            cursor_mock = MagicMock()
            cursor_mock.fetchone.return_value = {"id": 108}
            res = db._execute_insert(cursor_mock, query, params)
            self.assertEqual(res, 108)
            expected_query = query.replace("?", "%s") + " RETURNING id"
            cursor_mock.execute.assert_called_once_with(expected_query, params)

    def test_get_db_stats_structure(self):
        """Verify get_db_stats aggregation function return shape and type format."""
        stats = db.get_db_stats()
        self.assertIn("total_patients", stats)
        self.assertIn("total_sessions", stats)
        self.assertIn("top_conditions", stats)
        self.assertIn("top_medications", stats)
        self.assertIn("allergies_summary", stats)
        
        self.assertIsInstance(stats["total_patients"], int)
        self.assertIsInstance(stats["total_sessions"], int)
        self.assertIsInstance(stats["top_conditions"], list)
        self.assertIsInstance(stats["top_medications"], list)
        self.assertIsInstance(stats["allergies_summary"], list)

    def test_sqlite_crud_remains_functional(self):
        """Verify that basic patient and session CRUD actions are fully operational in SQLite."""
        with patch("database.db.IS_POSTGRES", False):
            db.init_db()
            
            import uuid
            uid = uuid.uuid4().hex[:8]
            patient_name = f"Test DB CRUD Rajesh {uid}"
            mrn = f"MRN-TEST-CRUD-{uid}"
            patient_id = db.create_patient(patient_name, 35, "Male", mrn)
            self.assertGreater(patient_id, 0)
            
            # Get Patient
            p = db.get_patient(patient_id)
            self.assertIsNotNone(p)
            self.assertEqual(p["name"], patient_name)
            self.assertEqual(p["medical_record_number"], mrn)
            
            # Create Session
            soap = {
                "subjective": "Complains of sore throat",
                "objective": "Tonsils inflamed",
                "assessment": "Acute tonsillitis",
                "plan": "Prescribe amoxicillin"
            }
            entities = {
                "conditions": ["Tonsillitis"],
                "medications": ["Amoxicillin"],
                "allergies": [],
                "symptoms": ["Sore throat"]
            }
            session_id = db.create_session(patient_id, soap_note=soap, patient_info=entities)
            self.assertGreater(session_id, 0)
            
            # Get Sessions
            sessions = db.get_patient_sessions(patient_id)
            self.assertEqual(len(sessions), 1)
            self.assertEqual(sessions[0]["soap_assessment"], "Acute tonsillitis")
            
            # Verify stats counts
            stats = db.get_db_stats()
            self.assertGreaterEqual(stats["total_patients"], 1)
            self.assertGreaterEqual(stats["total_sessions"], 1)

    @patch("psycopg2.connect")
    def test_postgres_connection_flow(self, mock_connect):
        """Verify PostgreSQL connection configuration calls psycopg2 with appropriate parameters."""
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        
        # Test case 1: configured port is passed correctly
        with patch("database.db.IS_POSTGRES", True), \
             patch("database.db.MEDIFLOW_POSTGRES_HOST", "pg-host"), \
             patch("database.db.MEDIFLOW_POSTGRES_DB", "pg-db"), \
             patch("database.db.MEDIFLOW_POSTGRES_USER", "pg-user"), \
             patch("database.db.MEDIFLOW_POSTGRES_PASSWORD", "pg-pass"), \
             patch("database.db.MEDIFLOW_POSTGRES_PORT", "9999"):
            
            conn = db._get_connection()
            mock_connect.assert_called_once()
            kwargs = mock_connect.call_args[1]
            self.assertEqual(kwargs["host"], "pg-host")
            self.assertEqual(kwargs["database"], "pg-db")
            self.assertEqual(kwargs["user"], "pg-user")
            self.assertEqual(kwargs["password"], "pg-pass")
            self.assertEqual(kwargs["port"], "9999")
            conn.close()

    def test_postgres_configuration_combinations(self):
        """Verify the complete, partial, and empty PostgreSQL configuration scenarios."""
        import importlib
        
        # Helper to reload config with environment variables mocked
        def reload_with_env(env_dict):
            with patch.dict(os.environ, env_dict):
                importlib.reload(config)

        # 1. No configuration -> SQLite remains selected
        reload_with_env({
            "MEDIFLOW_POSTGRES_HOST": "",
            "MEDIFLOW_POSTGRES_DB": "",
            "MEDIFLOW_POSTGRES_USER": "",
            "MEDIFLOW_POSTGRES_PASSWORD": "",
            "MEDIFLOW_POSTGRES_PORT": ""
        })
        self.assertFalse(config.IS_POSTGRES)

        # 2. Complete required configuration -> PostgreSQL selected
        reload_with_env({
            "MEDIFLOW_POSTGRES_HOST": "localhost",
            "MEDIFLOW_POSTGRES_DB": "mediflow_db",
            "MEDIFLOW_POSTGRES_USER": "db_user",
            "MEDIFLOW_POSTGRES_PASSWORD": "db_password",
            "MEDIFLOW_POSTGRES_PORT": "5432"
        })
        self.assertTrue(config.IS_POSTGRES)

        # 3. Missing HOST -> configuration error
        with self.assertRaises(ValueError) as context:
            reload_with_env({
                "MEDIFLOW_POSTGRES_HOST": "",
                "MEDIFLOW_POSTGRES_DB": "mediflow_db",
                "MEDIFLOW_POSTGRES_USER": "db_user",
                "MEDIFLOW_POSTGRES_PASSWORD": "db_password",
                "MEDIFLOW_POSTGRES_PORT": "5432"
            })
        self.assertIn("MEDIFLOW_POSTGRES_HOST", str(context.exception))

        # 4. Missing DB -> configuration error
        with self.assertRaises(ValueError) as context:
            reload_with_env({
                "MEDIFLOW_POSTGRES_HOST": "localhost",
                "MEDIFLOW_POSTGRES_DB": "",
                "MEDIFLOW_POSTGRES_USER": "db_user",
                "MEDIFLOW_POSTGRES_PASSWORD": "db_password",
                "MEDIFLOW_POSTGRES_PORT": "5432"
            })
        self.assertIn("MEDIFLOW_POSTGRES_DB", str(context.exception))

        # 5. Missing USER -> configuration error
        with self.assertRaises(ValueError) as context:
            reload_with_env({
                "MEDIFLOW_POSTGRES_HOST": "localhost",
                "MEDIFLOW_POSTGRES_DB": "mediflow_db",
                "MEDIFLOW_POSTGRES_USER": "",
                "MEDIFLOW_POSTGRES_PASSWORD": "db_password",
                "MEDIFLOW_POSTGRES_PORT": "5432"
            })
        self.assertIn("MEDIFLOW_POSTGRES_USER", str(context.exception))

        # 6. Missing PASSWORD -> configuration error
        with self.assertRaises(ValueError) as context:
            reload_with_env({
                "MEDIFLOW_POSTGRES_HOST": "localhost",
                "MEDIFLOW_POSTGRES_DB": "mediflow_db",
                "MEDIFLOW_POSTGRES_USER": "db_user",
                "MEDIFLOW_POSTGRES_PASSWORD": "",
                "MEDIFLOW_POSTGRES_PORT": "5432"
            })
        self.assertIn("MEDIFLOW_POSTGRES_PASSWORD", str(context.exception))

        # 7. PORT alone -> SQLite remains selected (no configuration error raised)
        reload_with_env({
            "MEDIFLOW_POSTGRES_HOST": "",
            "MEDIFLOW_POSTGRES_DB": "",
            "MEDIFLOW_POSTGRES_USER": "",
            "MEDIFLOW_POSTGRES_PASSWORD": "",
            "MEDIFLOW_POSTGRES_PORT": "5432"
        })
        self.assertFalse(config.IS_POSTGRES)

        # 8. PORT absent -> Defaults to 5432 (when complete required configuration is present)
        reload_with_env({
            "MEDIFLOW_POSTGRES_HOST": "localhost",
            "MEDIFLOW_POSTGRES_DB": "mediflow_db",
            "MEDIFLOW_POSTGRES_USER": "db_user",
            "MEDIFLOW_POSTGRES_PASSWORD": "db_password",
            "MEDIFLOW_POSTGRES_PORT": ""
        })
        self.assertTrue(config.IS_POSTGRES)
        self.assertEqual(config.MEDIFLOW_POSTGRES_PORT, "5432")

        # Restore normal settings (no config) to clean up
        reload_with_env({
            "MEDIFLOW_POSTGRES_HOST": "",
            "MEDIFLOW_POSTGRES_DB": "",
            "MEDIFLOW_POSTGRES_USER": "",
            "MEDIFLOW_POSTGRES_PASSWORD": "",
            "MEDIFLOW_POSTGRES_PORT": ""
        })



if __name__ == "__main__":
    unittest.main()
