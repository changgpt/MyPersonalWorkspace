"""Manual ordering within a bucket, and the Today page's completed toggle.

`position` is 0 for anything never dragged, which is what lets an existing
database behave exactly as it did before the column existed; once a bucket
*is* reordered its rows get 1..n and the manual order wins.
"""
from daybook import db as db_module


def _ids(bucket="today", **kwargs):
    return [t["id"] for t in db_module.list_tasks_by_bucket(bucket, **kwargs)]


def test_untouched_bucket_still_sorts_by_priority_then_date(db):
    low = db_module.create_task(title="Low", priority="low", bucket="today")
    high = db_module.create_task(title="High", priority="high", bucket="today")
    med = db_module.create_task(title="Med", priority="medium", bucket="today")
    # No reorder has happened, so priority ordering is untouched.
    assert _ids() == [high, med, low]


def test_set_bucket_order_wins_over_priority(db):
    low = db_module.create_task(title="Low", priority="low", bucket="today")
    high = db_module.create_task(title="High", priority="high", bucket="today")
    db_module.set_bucket_order([low, high])
    assert _ids() == [low, high]


def test_reordering_renumbers_from_one(db):
    a = db_module.create_task(title="A", bucket="today")
    b = db_module.create_task(title="B", bucket="today")
    db_module.set_bucket_order([b, a])
    positions = {t["id"]: t["position"] for t in db_module.list_tasks_by_bucket("today")}
    assert positions == {b: 1, a: 2}


def test_done_tasks_sink_regardless_of_position(db):
    a = db_module.create_task(title="A", bucket="today")
    b = db_module.create_task(title="B", bucket="today")
    db_module.set_bucket_order([a, b])
    db_module.set_task_status(a, "done")
    assert _ids(include_done=True) == [b, a]


def test_moving_buckets_lands_at_the_end_of_the_destination(db):
    first = db_module.create_task(title="First", bucket="long_term")
    second = db_module.create_task(title="Second", bucket="long_term")
    db_module.set_bucket_order([first, second])
    moved = db_module.create_task(title="Moved", priority="high", bucket="today")

    db_module.set_task_bucket(moved, "long_term")
    # High priority, but dropped in last -- a drop has to mean *somewhere*,
    # and the end is the only answer that doesn't reshuffle what's there.
    assert _ids("long_term") == [first, second, moved]


def test_moving_into_an_unordered_bucket_does_not_pin_it(db):
    # The destination has never been hand-ordered, so the moved task should
    # fall into its priority place rather than being stuck at the bottom.
    db_module.create_task(title="Existing low", priority="low", bucket="background")
    moved = db_module.create_task(title="Moved high", priority="high", bucket="today")
    db_module.set_task_bucket(moved, "background")
    assert _ids("background")[0] == moved


def test_a_new_task_joins_the_end_of_an_ordered_bucket(db):
    a = db_module.create_task(title="A", priority="low", bucket="today")
    b = db_module.create_task(title="B", priority="low", bucket="today")
    db_module.set_bucket_order([a, b])
    fresh = db_module.create_task(title="Fresh", priority="high", bucket="today")
    assert _ids() == [a, b, fresh]


# --- include_done / the toggle ----------------------------------------

def test_completed_tasks_are_hidden_by_default(db):
    open_id = db_module.create_task(title="Open", bucket="long_term")
    done_id = db_module.create_task(title="Done", bucket="long_term")
    db_module.set_task_status(done_id, "done")
    assert _ids("long_term") == [open_id]
    assert set(_ids("long_term", include_done=True)) == {open_id, done_id}


def test_the_overdue_pull_forward_never_includes_done_tasks(db):
    # Pre-existing behaviour, pinned because it's easy to assume otherwise:
    # the overdue clause carries its own `status != 'done'`, so a completed
    # task from another bucket is not pulled into Today even with
    # include_done -- that flag only widens the bucket's own rows.
    task_id = db_module.create_task(title="Was overdue", bucket="long_term",
                                     due_date="2000-01-01")
    assert task_id in _ids("today")
    db_module.set_task_status(task_id, "done")
    assert task_id not in _ids("today")
    assert task_id not in _ids("today", include_done=True)
    # It's still there in its own bucket with the toggle on.
    assert task_id in _ids("long_term", include_done=True)


# --- the route ---------------------------------------------------------

def test_today_page_hides_completed_until_toggled(client, db):
    done_id = db_module.create_task(title="Already finished", bucket="today")
    db_module.set_task_status(done_id, "done")
    assert "Already finished" not in client.get("/tasks").get_data(as_text=True)
    on = client.get("/tasks?done=1").get_data(as_text=True)
    assert "Already finished" in on
    # The chip reflects the state it's in, not just that it can be pressed.
    assert 'aria-checked="true"' in on


def test_move_endpoint_applies_an_order(client, db):
    a = db_module.create_task(title="A", bucket="today")
    b = db_module.create_task(title="B", bucket="today")
    response = client.post(f"/tasks/{b}/move", data={"bucket": "today", "order": f"{b},{a}"})
    assert response.status_code == 204
    assert _ids() == [b, a]


def test_move_endpoint_ignores_ids_that_are_not_real_tasks(client, db):
    a = db_module.create_task(title="A", bucket="today")
    b = db_module.create_task(title="B", bucket="today")
    client.post(f"/tasks/{b}/move", data={"order": f"{b},9999,{a}"})
    # The bogus id is dropped; the two real ones still get 1 and 2.
    positions = {t["id"]: t["position"] for t in db_module.list_tasks_by_bucket("today")}
    assert positions == {b: 1, a: 2}


def test_move_endpoint_refuses_an_order_without_the_moved_task(client, db):
    # Guards against a request that renumbers rows the mover isn't touching.
    a = db_module.create_task(title="A", bucket="today")
    b = db_module.create_task(title="B", bucket="today")
    db_module.set_bucket_order([a, b])
    other = db_module.create_task(title="Other", bucket="background")
    client.post(f"/tasks/{other}/move", data={"order": f"{b},{a}"})
    assert _ids() == [a, b], "an unrelated task's move rewrote this bucket"


def test_move_endpoint_still_handles_a_plain_bucket_change(client, db):
    task_id = db_module.create_task(title="A", bucket="today")
    assert client.post(f"/tasks/{task_id}/move", data={"bucket": "background"}).status_code == 204
    assert db_module.get_task(task_id)["bucket"] == "background"


def test_the_toggle_links_to_the_opposite_state(client, db):
    # Regression: the chip used to sit outside the swapped region, so it
    # was never re-rendered and kept linking to the state you were already
    # in -- the toggle only ever turned on.
    off = client.get("/tasks").get_data(as_text=True)
    assert "done=1" in off
    on = client.get("/tasks?done=1").get_data(as_text=True)
    assert "done=0" in on


def test_quick_add_keeps_completed_showing(client, db):
    done_id = db_module.create_task(title="Already finished", bucket="today")
    db_module.set_task_status(done_id, "done")
    # The quick-add form posts with no query string, so it carries the
    # toggle in its body instead.
    body = client.post("/tasks", data={"title": "Fresh", "done": "1"},
                       headers={"HX-Request": "true"}).get_data(as_text=True)
    assert "Fresh" in body
    assert "Already finished" in body, "adding a task reset the Completed toggle"
