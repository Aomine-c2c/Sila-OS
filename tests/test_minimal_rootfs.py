import unittest
import os
import sys
import subprocess

class TestMinimalRootfs(unittest.TestCase):
    def setUp(self):
        self.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.rootfs = os.path.join(self.root_dir, "build", "rootfs")

    def test_fhs_hierarchy_complete(self):
        fhs_dirs = [
            "boot", "etc", "home", "root", "usr", "var", "opt", "run",
            "tmp", "dev", "proc", "sys", "mnt", "media", "srv"
        ]
        for d in fhs_dirs:
            p = os.path.join(self.rootfs, d)
            self.assertTrue(os.path.exists(p), f"FHS directory '{d}' must exist in rootfs")

    def test_os_release_metadata(self):
        os_release = os.path.join(self.rootfs, "etc", "os-release")
        self.assertTrue(os.path.isfile(os_release), "/etc/os-release must exist")
        with open(os_release, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn('NAME="KAIROS OS"', content)
        self.assertIn('ID=kairos', content)
        self.assertIn('VERSION_CODENAME="aethelgard"', content)

    def test_users_and_groups(self):
        passwd = os.path.join(self.rootfs, "etc", "passwd")
        group = os.path.join(self.rootfs, "etc", "group")
        self.assertTrue(os.path.isfile(passwd), "/etc/passwd must exist")
        self.assertTrue(os.path.isfile(group), "/etc/group must exist")
        with open(passwd, "r", encoding="utf-8") as f:
            passwd_content = f.read()
        self.assertIn("root:x:0:0:", passwd_content)
        self.assertIn("kairos:x:1000:1000:", passwd_content)
        self.assertIn("kairos-risk:x:990:1003:", passwd_content)

    def test_fstab_mounts(self):
        fstab = os.path.join(self.rootfs, "etc", "fstab")
        self.assertTrue(os.path.isfile(fstab), "/etc/fstab must exist")
        with open(fstab, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("LABEL=KAIROS_ROOT", content)
        self.assertIn("subvol=@", content)

    def test_kairos_system_info_utility(self):
        kairos_bin = os.path.join(self.rootfs, "usr", "bin", "kairos")
        self.assertTrue(os.path.isfile(kairos_bin), "/usr/bin/kairos must exist")
        env = os.environ.copy()
        env["KAIROS_ROOTFS"] = self.rootfs
        res = subprocess.run([sys.executable, kairos_bin, "system", "info"], env=env, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0)
        self.assertIn("KAIROS OS", res.stdout)
        self.assertIn("System Uptime", res.stdout)
        self.assertIn("Memory Total", res.stdout)
        self.assertIn("Root Filesystem", res.stdout)

    def test_kernel_and_initramfs_exist(self):
        kernel = os.path.join(self.rootfs, "boot", "vmlinuz-kairos")
        initrd = os.path.join(self.rootfs, "boot", "initramfs-kairos.img")
        self.assertTrue(os.path.isfile(kernel), "vmlinuz-kairos must exist in /boot")
        self.assertTrue(os.path.isfile(initrd), "initramfs-kairos.img must exist in /boot")
        self.assertGreater(os.path.getsize(kernel), 10_000_000, "Kernel must be non-empty binary")
        self.assertGreater(os.path.getsize(initrd), 500_000, "Initramfs must be non-empty image (> 500 KB)")

if __name__ == "__main__":
    unittest.main()
