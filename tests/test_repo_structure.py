import unittest
import os

class TestRepositoryStructure(unittest.TestCase):
    def setUp(self):
        self.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    def test_top_level_directories_exist(self):
        expected_dirs = [
            "boot", "build", "config", "docs", "kernel", "iso", "packages",
            "system", "services", "desktop", "shell", "apps", "plugins",
            "trading", "research", "agents", "adaptive", "security", "scripts",
            "tests", "tools", "recovery", "installer", "assets"
        ]
        for d in expected_dirs:
            dir_path = os.path.join(self.root_dir, d)
            self.assertTrue(os.path.isdir(dir_path), f"Directory {d} must exist")

    def test_mandatory_root_documents_exist(self):
        expected_files = [
            "README.md", "ARCHITECTURE.md", "ROADMAP.md",
            "CONTRIBUTING.md", "SECURITY.md", "LICENSE", "CHANGELOG.md", "kairos.toml"
        ]
        for f in expected_files:
            file_path = os.path.join(self.root_dir, f)
            self.assertTrue(os.path.isfile(file_path), f"File {f} must exist in root")

    def test_docs_subdirectories_exist(self):
        expected_doc_dirs = [
            "architecture", "build", "boot", "hardware", "desktop",
            "security", "services", "trading", "research", "adaptive",
            "development", "release", "adr"
        ]
        for d in expected_doc_dirs:
            dir_path = os.path.join(self.root_dir, "docs", d)
            self.assertTrue(os.path.isdir(dir_path), f"Docs subdirectory {d} must exist")

    def test_foundation_scripts_exist(self):
        scripts = [
            "env_detect.sh", "check_deps.sh", "build.sh", "test.sh",
            "clean.sh", "package.sh", "iso_generate.sh", "vm_boot.sh", "hardware_validate.sh"
        ]
        for s in scripts:
            script_path = os.path.join(self.root_dir, "scripts", s)
            self.assertTrue(os.path.isfile(script_path), f"Script {s} must exist in scripts/")

    def test_manifest_structure(self):
        manifest_path = os.path.join(self.root_dir, "kairos.toml")
        self.assertTrue(os.path.isfile(manifest_path))
        with open(manifest_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("[project]", content)
        self.assertIn("[architecture]", content)
        self.assertIn("[invariants]", content)
        self.assertIn("hard_risk_gatekeeper = true", content)

if __name__ == "__main__":
    unittest.main()
