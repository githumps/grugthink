import os

import pytest

from grug_db import GrugDB


@pytest.fixture(scope="function")
def db_instance():
    # Setup: Create a temporary database for testing
    test_db_path = "test_grug_lore.db"
    test_index_path = "test_grug_lore.index"

    # Clean up any previous test artifacts
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
    if os.path.exists(test_index_path):
        os.remove(test_index_path)

    db = GrugDB(test_db_path)
    yield db

    # Teardown: Close the database and remove the test files
    db.close()
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
    if os.path.exists(test_index_path):
        os.remove(test_index_path)

def test_add_fact(db_instance):
    assert db_instance.add_fact("Grug like big rock.")
    assert not db_instance.add_fact("Grug like big rock.") # Test adding duplicate
    facts = db_instance.get_all_facts()
    assert "Grug like big rock." in facts
    assert len(facts) == 1

def test_search_facts(db_instance):
    db_instance.add_fact("Grug hunt mammoth.")
    db_instance.add_fact("Ugga make good fire.")
    db_instance.add_fact("Bork find shiny stone.")
    db_instance.add_fact("Grug think sky is blue.")

    results = db_instance.search_facts("what grug hunt?", k=1)
    assert "Grug hunt mammoth." in results
    assert len(results) == 1

    results = db_instance.search_facts("who make fire?", k=1)
    assert "Ugga make good fire." in results

    results = db_instance.search_facts("what bork find?", k=1)
    assert "Bork find shiny stone." in results

    results = db_instance.search_facts("color of sky?", k=1)
    assert "Grug think sky is blue." in results



def test_get_all_facts(db_instance):
    db_instance.add_fact("Fact one.")
    db_instance.add_fact("Fact two.")
    facts = db_instance.get_all_facts()
    assert len(facts) == 2
    assert "Fact one." in facts
    assert "Fact two." in facts

def test_rebuild_index(db_instance):
    db_instance.add_fact("Fact for rebuild.")
    initial_ntotal = db_instance.index.ntotal
    db_instance.rebuild_index()
    assert db_instance.index.ntotal == initial_ntotal

def test_db_close(db_instance):
    # The fixture handles closing, but we can test if it doesn't raise an error
    # when called explicitly (though it's usually called once in teardown)
    db_instance.close()
    # Re-initializing to ensure it can be opened again after close
    new_db = GrugDB("test_grug_lore.db")
    assert new_db is not None
    new_db.close()

def test_invalid_db_path():
    with pytest.raises(Exception):
        GrugDB("/invalid/path/to/db.sqlite")
