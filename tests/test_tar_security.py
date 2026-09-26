import io
import os
import tarfile
import tempfile
import unittest

import simple_extract


class TarSafetyTests(unittest.TestCase):
    def _extract(self, archive_path, dest_dir):
        logs = []
        ok, message = simple_extract.Extractor.extract(
            archive_path,
            dest_dir,
            None,
            lambda _value: None,
            logs.append,
        )
        self.assertTrue(ok, message)
        return logs

    def test_symlink_member_is_not_created(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = os.path.join(tmp, "symlink.tar")
            dest = os.path.join(tmp, "out")
            with tarfile.open(archive, "w") as tf:
                info = tarfile.TarInfo("safe-link")
                info.type = tarfile.SYMTYPE
                info.linkname = "../../outside"
                tf.addfile(info)

            logs = self._extract(archive, dest)

            self.assertFalse(os.path.lexists(os.path.join(dest, "safe-link")))
            self.assertTrue(any("安全でないTARメンバー" in line for line in logs))

    def test_hardlink_member_is_not_created(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = os.path.join(tmp, "hardlink.tar")
            dest = os.path.join(tmp, "out")
            with tarfile.open(archive, "w") as tf:
                payload = b"safe"
                file_info = tarfile.TarInfo("inside.txt")
                file_info.size = len(payload)
                tf.addfile(file_info, io.BytesIO(payload))

                link_info = tarfile.TarInfo("hard-link")
                link_info.type = tarfile.LNKTYPE
                link_info.linkname = "../../outside"
                tf.addfile(link_info)

            logs = self._extract(archive, dest)

            self.assertTrue(os.path.isfile(os.path.join(dest, "inside.txt")))
            self.assertFalse(os.path.lexists(os.path.join(dest, "hard-link")))
            self.assertTrue(any("安全でないTARメンバー" in line for line in logs))


if __name__ == "__main__":
    unittest.main()
