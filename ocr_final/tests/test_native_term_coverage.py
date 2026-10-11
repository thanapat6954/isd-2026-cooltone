import sqlite3,unittest
from scripts.database_build import validate_plan_terms
class TermCoverageTests(unittest.TestCase):
 def test_source_backed_additional_term_and_missing_regular_guard(self):
  with sqlite3.connect(':memory:') as db:
   db.row_factory=sqlite3.Row
   db.execute('create table plan_item(year integer,semester integer)');db.execute('create table plan_term_source(year integer,semester integer)')
   terms=[(y,s) for y in range(1,5) for s in (1,2)]+[(3,3)]
   db.executemany('insert into plan_item values (?,?)',terms)
   with self.assertRaises(ValueError):validate_plan_terms(db)
   with self.assertRaises(ValueError):validate_plan_terms(db,native=True)
   db.executemany('insert into plan_term_source values (?,?)',terms);validate_plan_terms(db,native=True)
   db.execute('delete from plan_item where year=4 and semester=2')
   with self.assertRaises(ValueError):validate_plan_terms(db,native=True)
