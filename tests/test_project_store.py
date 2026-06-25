import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import config
import project_store


def _state(topic="光合作用", slides=3, mode="grounded"):
    return {
        "inputParams": {"topic": topic, "scenario": "teaching", "outputLanguage": "zh",
                        "generationMode": mode},
        "scenario": "teaching",
        "outputLanguage": "zh",
        "generationContext": {"mode": mode, "factTable": []},
        "outline": {"title": topic, "slides": [{"page_number": i + 1} for i in range(slides)]},
    }


class TestProjectStore(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._orig_root = config.PROJECT_ROOT
        config.PROJECT_ROOT = Path(self._tmp.name)

    def tearDown(self):
        config.PROJECT_ROOT = self._orig_root
        self._tmp.cleanup()

    def test_save_list_load_round_trip(self):
        meta = project_store.save_project({"title": "光合作用入门", "state": _state(slides=4)})
        self.assertTrue(meta["id"])
        self.assertEqual(meta["summary"]["slide_count"], 4)
        self.assertEqual(meta["summary"]["topic"], "光合作用")
        self.assertEqual(meta["summary"]["generation_mode"], "grounded")

        listed = project_store.list_projects()
        self.assertEqual(len(listed), 1)
        self.assertNotIn("state", listed[0])  # list view is summary-only

        full = project_store.load_project(meta["id"])
        self.assertEqual(full["state"]["outline"]["title"], "光合作用")

    def test_upsert_by_id_updates_in_place(self):
        meta = project_store.save_project({"title": "v1", "state": _state(slides=3)})
        pid = meta["id"]
        meta2 = project_store.save_project({"id": pid, "title": "v2", "state": _state(slides=6)})
        self.assertEqual(meta2["id"], pid)
        # exactly one file, updated not duplicated
        files = list(project_store.projects_dir().glob("*.json"))
        self.assertEqual(len(files), 1)
        full = project_store.load_project(pid)
        self.assertEqual(full["title"], "v2")
        self.assertEqual(full["summary"]["slide_count"], 6)
        self.assertEqual(full["created_at"], meta["created_at"])  # created_at preserved

    def test_list_orders_newest_first_and_limits(self):
        ids = []
        for i in range(7):
            m = project_store.save_project({"title": f"p{i}", "state": _state(topic=f"t{i}")})
            ids.append(m["id"])
            # force distinct, increasing updated_at
            path = project_store.projects_dir() / f"{m['id']}.json"
            text = path.read_text(encoding="utf-8").replace(
                m["updated_at"], f"2026-06-2{i}T00:00:00Z"
            )
            path.write_text(text, encoding="utf-8")
        recent = project_store.list_projects(limit=5)
        self.assertEqual(len(recent), 5)
        self.assertEqual(recent[0]["title"], "p6")  # newest
        self.assertEqual(len(project_store.list_projects(limit=None)), 7)  # all

    def test_invalid_id_rejected(self):
        with self.assertRaises(project_store.ProjectStoreError):
            project_store.load_project("../etc/passwd")
        with self.assertRaises(project_store.ProjectStoreError):
            project_store.load_project("a/b")

    def test_save_with_bad_id_generates_safe_id(self):
        meta = project_store.save_project({"id": "../evil", "state": _state()})
        self.assertRegex(meta["id"], r"^[A-Za-z0-9_-]+$")
        files = list(project_store.projects_dir().glob("*.json"))
        self.assertEqual(len(files), 1)

    def test_load_missing_raises(self):
        with self.assertRaises(project_store.ProjectStoreError):
            project_store.load_project("deadbeef")

    def test_oversized_state_rejected(self):
        big = {"blob": "x" * (project_store.MAX_STATE_BYTES + 10)}
        with self.assertRaises(project_store.ProjectStoreError):
            project_store.save_project({"title": "big", "state": big})

    def test_delete(self):
        meta = project_store.save_project({"title": "del", "state": _state()})
        self.assertTrue(project_store.delete_project(meta["id"]))
        self.assertFalse(project_store.delete_project(meta["id"]))
        self.assertEqual(project_store.list_projects(), [])


class TestProjectEndpoints(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._orig_root = config.PROJECT_ROOT
        config.PROJECT_ROOT = Path(self._tmp.name)
        import app
        self.client = app.app.test_client()

    def tearDown(self):
        config.PROJECT_ROOT = self._orig_root
        self._tmp.cleanup()

    def test_save_then_get_then_delete(self):
        resp = self.client.post("/api/projects", json={"title": "课件", "state": _state(slides=5)})
        self.assertEqual(resp.status_code, 200)
        pid = resp.get_json()["id"]
        self.assertTrue(pid)

        listed = self.client.get("/api/projects").get_json()
        self.assertTrue(listed["success"])
        self.assertEqual(len(listed["projects"]), 1)

        full = self.client.get(f"/api/projects/{pid}").get_json()
        self.assertEqual(full["project"]["state"]["outline"]["slides"].__len__(), 5)

        all_resp = self.client.get("/api/projects?all=1").get_json()
        self.assertEqual(len(all_resp["projects"]), 1)

        deleted = self.client.delete(f"/api/projects/{pid}").get_json()
        self.assertTrue(deleted["deleted"])

    def test_empty_state_rejected(self):
        resp = self.client.post("/api/projects", json={"title": "x", "state": {}})
        self.assertEqual(resp.status_code, 422)

    def test_missing_project_404(self):
        resp = self.client.get("/api/projects/nope")
        self.assertEqual(resp.status_code, 404)


if __name__ == "__main__":
    unittest.main()
