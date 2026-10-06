"""Absent source facts remain unknown during an additive schema upgrade."""
import sqlite3
import unittest
from scripts.upgrade_fidelity_schema import FIELDS, upgrade


class FidelityUpgradeTests(unittest.TestCase):
    def test_additive_and_idempotent_without_guessed_values(self):
        con = sqlite3.connect(':memory:')
        try:
            con.execute('CREATE TABLE plan_item(id INTEGER, code TEXT, credits INTEGER)')
            con.execute("INSERT INTO plan_item VALUES(1, 'ELEC-SLOT-001', 3)")
            self.assertEqual(set(upgrade(con)), set(FIELDS))
            self.assertEqual(con.execute('SELECT id,code,credits FROM plan_item').fetchone(), (1, 'ELEC-SLOT-001', 3))
            self.assertEqual(con.execute('SELECT is_placeholder,raw_code FROM plan_item').fetchone(), (None, None))
            self.assertEqual(upgrade(con), [])
        finally:
            con.close()
