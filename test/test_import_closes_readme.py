"""Importing ``ovos_adapt`` from a directory that holds a README.md
must not leave the file open (a ResourceWarning on every test run)."""
import importlib
import os
import sys
import tempfile
import unittest
import warnings


class TestImportClosesReadme(unittest.TestCase):
    def test_no_resource_warning(self):
        cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as td:
            with open(os.path.join(td, "README.md"), "w", encoding="utf-8") as f:
                f.write("# doc\n")
            # the fresh import replaces the package and every submodule
            # entry; put the originals back so later tests see one
            # ovos_adapt, not two
            saved = {k: v for k, v in sys.modules.items()
                     if k == "ovos_adapt" or k.startswith("ovos_adapt.")}
            os.chdir(td)
            try:
                for k in saved:
                    sys.modules.pop(k, None)
                with warnings.catch_warnings(record=True) as caught:
                    warnings.simplefilter("always")
                    mod = importlib.import_module("ovos_adapt")
                    import gc
                    gc.collect()
            finally:
                os.chdir(cwd)
                for k in [k for k in sys.modules
                          if k == "ovos_adapt" or k.startswith("ovos_adapt.")]:
                    sys.modules.pop(k, None)
                sys.modules.update(saved)
        self.assertEqual(mod.__doc__, "# doc\n")
        leaks = [w for w in caught if issubclass(w.category, ResourceWarning)]
        self.assertEqual(leaks, [])
