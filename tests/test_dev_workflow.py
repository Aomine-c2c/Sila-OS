import unittest
import os
import subprocess

class TestDeveloperWorkflowScripts(unittest.TestCase):
    def setUp(self):
        self.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    def test_workflow_scripts_exist_and_nonempty(self):
        scripts = [
            "check-environment",
            "build",
            "clean",
            "test",
            "build-iso",
            "run-vm"
        ]
        for s in scripts:
            script_path = os.path.join(self.root_dir, "scripts", s)
            self.assertTrue(os.path.isfile(script_path), f"Script {s} must exist in scripts/")
            self.assertGreater(os.path.getsize(script_path), 50, f"Script {s} must not be empty")

    def test_adr_0001_linux_base_exists(self):
        adr_path = os.path.join(self.root_dir, "docs", "adr", "0001-linux-base.md")
        self.assertTrue(os.path.isfile(adr_path), "docs/adr/0001-linux-base.md must exist")
        with open(adr_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("Fedora Linux", content)
        self.assertIn("PREEMPT_RT", content)

    def test_build_environment_doc_exists(self):
        doc_path = os.path.join(self.root_dir, "docs", "build", "BUILD_ENVIRONMENT.md")
        self.assertTrue(os.path.isfile(doc_path), "BUILD_ENVIRONMENT.md must exist")
        with open(doc_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("Supported Host Systems", content)
        self.assertIn("Minimum & Recommended Hardware Requirements", content)

if __name__ == "__main__":
    unittest.main()
