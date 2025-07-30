# ignore: F405
import threading
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor

from bazoola import *

from .common import *
from .util import *


@use_tables("c", "e")
def test_concurrent_seqnum_generation_threads(db):
    """
    Test for race conditions in sequence number generation.
    Multiple threads inserting records simultaneously may get duplicate IDs.
    """
    results = []
    errors = []

    def insert_worker(worker_id):
        try:
            for i in range(10):
                result = db.insert("e", {"text": f"w{worker_id}_{i}"})
                results.append(result["id"])
        except Exception as e:
            errors.append(e)

    threads = []
    for i in range(5):
        t = threading.Thread(target=insert_worker, args=(i,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    id_counts = Counter(results)
    duplicates = [id_val for id_val, count in id_counts.items() if count > 1]

    assert not duplicates, f"Found duplicate IDs: {duplicates}"
    assert not errors, f"Unexpected errors: {errors}"

    # should have 50 unique IDs (5 workers * 10 inserts each)
    assert len(results) == 50, f"Expected 50 results, got {len(results)}"
    assert len(set(results)) == 50, f"Expected 50 unique IDs, got {len(set(results))}"


def process_worker(worker_id) -> list[int] | str:
    """
    Worker function that runs in separate process.
    """
    db = DB([TableE], base_dir=TEST_BASE_DIR)
    results = []
    try:
        for i in range(100):
            result = db.insert("e", {"text": f"{worker_id}_{i}"})
            results.append(result["id"])
        return results
    except Exception as e:
        return str(e)
    finally:
        db.close()


def test_concurrent_seqnum_generation_processes():
    """
    Test race conditions using multiple processes
    """
    ids = []
    errors = []
    with ProcessPoolExecutor(max_workers=10) as executor:
        for result in executor.map(process_worker, range(20)):
            if isinstance(result, list):
                ids.extend(result)
            else:
                errors.append(result)

    id_counts = Counter(ids)
    duplicates = [id_val for id_val, count in id_counts.items() if count > 1]

    assert not duplicates, f"Found duplicate IDs: {duplicates}"
    assert not errors, f"Process errors: {errors}"
    assert len(ids) == 2000
    assert len(set(ids)) == 2000


@use_tables("e")
def test_concurrent_delete_insert_race_condition(db):
    """
    Test race conditions in free space management.
    When records are deleted and new ones inserted simultaneously,
    the free space tracking can get corrupted.
    """
    initial_ids = []
    for i in range(20):
        result = db.insert("e", {"text": f"r_{i}"})
        initial_ids.append(result["id"])

    deleted_ids = []
    inserted_ids = []
    errors = []

    def delete_worker():
        try:
            for i in range(0, 20, 2):
                db.delete_by_id("e", initial_ids[i])
                deleted_ids.append(initial_ids[i])
        except Exception as e:
            errors.append(f"Delete error: {e}")

    def insert_worker():
        try:
            for i in range(10):
                result = db.insert("e", {"text": f"n_{i}"})
                inserted_ids.append(result["id"])
        except Exception as e:
            errors.append(f"Insert error: {e}")

    delete_thread = threading.Thread(target=delete_worker)
    insert_thread = threading.Thread(target=insert_worker)
    delete_thread.start()
    insert_thread.start()
    delete_thread.join()
    insert_thread.join()
    assert not errors, f"Unexpected errors: {errors}"

    all_records = db.find_all("e")
    assert len(all_records) == 20


@use_tables("c")
def test_concurrent_update_same_record(db):
    """
    Test race conditions when multiple threads update the same record.
    This can lead to data corruption or lost updates.
    """
    initial_record = db.insert("c", {"varchar": "init", "int": 0})
    record_id = initial_record["id"]

    update_results = []
    errors = []

    def update_worker(worker_id):
        try:
            for i in range(5):
                with db.lock():
                    current = db.find_by_id("c", record_id)
                    if not current:
                        errors.append(f"Worker {worker_id} error: {record_id=} is missing")
                        continue
                    new_value = current["int"] + 1
                    result = db.update_by_id(
                        "c", record_id, {"varchar": f"{worker_id}_{i}", "int": new_value}
                    )
                update_results.append((worker_id, i, result["int"]))
                # small delay to increase chance of race
                time.sleep(0.001)
        except Exception as e:
            errors.append(f"Worker {worker_id} error: {e}")

    threads = []
    for i in range(4):
        t = threading.Thread(target=update_worker, args=(i,))
        threads.append(t)
        t.start()
    for t in threads:
        t.join()

    final_record = db.find_by_id("c", record_id)
    assert not errors, f"Unexpected errors: {errors}"

    # the int field should be 20 (4 workers * 5 updates each)
    # but due to race conditions, it will likely be less
    expected_final_value = 20
    actual_final_value = final_record["int"]

    assert actual_final_value == expected_final_value, (
        f"Lost updates detected! Expected int={expected_final_value}, "
        f"but got int={actual_final_value}. "
        f"Update results: {update_results}"
    )


def stress_worker(worker_id):
    db = DB([TableE], base_dir=TEST_BASE_DIR)
    operations = []

    try:
        for i in range(20):
            if i % 3 == 0:
                # Insert
                result = db.insert("e", {"text": f"{worker_id}_{i}"})
                operations.append(("insert", result["id"]))
            elif i % 3 == 1 and operations:
                # Update
                insert_ops = [x for x in operations if x[0] == "insert"]
                if insert_ops:
                    target_id = insert_ops[-1][1]
                    db.update_by_id("e", target_id, {"text": f"u{worker_id}_{i}"})
                    operations.append(("update", target_id))
            else:
                # Delete
                insert_ops = [x for x in operations if x[0] == "insert"]
                if insert_ops:
                    target_id = insert_ops[-1][1]
                    try:
                        db.delete_by_id("e", target_id)
                        operations.append(("delete", target_id))
                    except Exception:
                        pass
        return len(operations)

    except Exception as e:
        return f"ERROR: {e}"
    finally:
        db.close()


def test_concurrent_file_corruption_simulation():
    """
    Test that simulates potential file corruption during concurrent writes.
    This test writes to the same database from multiple processes and
    verifies that the data files remain consistent.
    """
    results = []
    with ProcessPoolExecutor(max_workers=4) as executor:
        for result in executor.map(stress_worker, range(4)):
            results.append(result)

    db = DB([TableE], base_dir=TEST_BASE_DIR)
    try:
        all_records = db.find_all("e")
        for record in all_records:
            assert record["id"] is not None
            assert record["text"] is not None
            assert isinstance(record["id"], int)
            assert isinstance(record["text"], str)

        errors = [x for x in results if isinstance(x, str) and x.startswith("ERROR")]
        assert not errors

    finally:
        db.close()
