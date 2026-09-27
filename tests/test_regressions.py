import bz2
import gzip
import io
import os
import tempfile
import tarfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import simple_extract


class SecurityRegressionTests(unittest.TestCase):
    def test_zip_password_creation_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "secret.txt"
            src.write_text("secret", encoding="utf-8")
            out = Path(tmp) / "secret.zip"

            ok, error = simple_extract.Compressor.compress(
                [str(src)],
                str(out),
                fmt="zip",
                password="password",
            )

            self.assertFalse(ok)
            self.assertIn("未対応", error)
            self.assertFalse(out.exists())

    def test_zip_preview_does_not_use_full_entry_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "large.zip"
            with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("large.txt", b"A" * (2 * 1024 * 1024))

            with patch.object(zipfile.ZipFile, "read", side_effect=AssertionError("full read used")):
                data, error = simple_extract.Extractor.preview_file(
                    str(archive),
                    "large.txt",
                    max_bytes=4096,
                )

            self.assertIsNone(error)
            self.assertEqual(4096, len(data))

    def test_standalone_gzip_enforces_runtime_uncompressed_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "large.gz"
            with gzip.open(archive, "wb") as stream:
                stream.write(b"A" * 4096)
            dest = Path(tmp) / "out"

            with patch.object(simple_extract.Extractor, "ZIPBOMB_MAX_UNCOMPRESSED", 1024):
                ok, error = simple_extract.Extractor.extract(
                    str(archive), str(dest), None, lambda _value: None, lambda _message: None
                )

            self.assertFalse(ok)
            self.assertIn("大きすぎます", error)
            self.assertFalse((dest / "large").exists())

    def test_standalone_bz2_enforces_runtime_uncompressed_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "large.bz2"
            archive.write_bytes(bz2.compress(b"A" * 4096))
            dest = Path(tmp) / "out"

            with patch.object(simple_extract.Extractor, "ZIPBOMB_MAX_UNCOMPRESSED", 1024):
                ok, error = simple_extract.Extractor.extract(
                    str(archive), str(dest), None, lambda _value: None, lambda _message: None
                )

            self.assertFalse(ok)
            self.assertIn("大きすぎます", error)
            self.assertFalse((dest / "large").exists())

    def test_tar_symlink_outside_destination_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "unsafe.tar"
            with tarfile.open(archive, "w") as tf:
                link = tarfile.TarInfo("safe-link")
                link.type = tarfile.SYMTYPE
                link.linkname = "../../outside"
                tf.addfile(link)
            dest = Path(tmp) / "out"

            ok, error = simple_extract.Extractor.extract(
                str(archive), str(dest), None, lambda _value: None, lambda _message: None
            )

            self.assertTrue(ok, error)
            self.assertFalse((dest / "safe-link").exists())

    def test_tar_hardlink_outside_destination_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "unsafe-hardlink.tar"
            with tarfile.open(archive, "w") as tf:
                link = tarfile.TarInfo("safe-hardlink")
                link.type = tarfile.LNKTYPE
                link.linkname = "../../outside"
                tf.addfile(link)
            dest = Path(tmp) / "out"

            ok, error = simple_extract.Extractor.extract(
                str(archive), str(dest), None, lambda _value: None, lambda _message: None
            )

            self.assertTrue(ok, error)
            self.assertFalse((dest / "safe-hardlink").exists())

    def test_source_sendto_command_includes_script_path(self):
        with patch.object(simple_extract.sys, "frozen", False, create=True):
            target, arguments = simple_extract.AssociationManager._sendto_target_and_arguments()

        self.assertEqual(simple_extract.sys.executable, target)
        self.assertIn(os.path.abspath(simple_extract.__file__), arguments)
        self.assertIn('"%1"', arguments)

    def test_update_checker_points_to_this_repository(self):
        self.assertEqual(
            "https://api.github.com/repos/neoenox/SimpleExtract/releases/latest",
            simple_extract.UpdateChecker.URL,
        )


if __name__ == "__main__":
    unittest.main()
