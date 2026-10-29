"""The physical Acer A/B installer must report the real dpkg failure.

apt-get captures stdout and stderr separately. Debian writes package-script
failures to stdout, while the harmless "debconf: delaying..." advisory can be
the only useful-looking text on stderr. Previous Greia code selected stderr
and lost the failing package entirely.
"""
from __future__ import annotations

import subprocess
import unittest
from unittest import mock

from greia_installer.device_seams import (
    SubprocessHardwareSupportRunner,
    _apt_failure_detail,
)
from greia_installer.fresh_ab_install import FreshAbInstallError


class DpkgErrorReportingTests(unittest.TestCase):
    def test_stdout_package_failure_beats_harmless_stderr(self) -> None:
        stdout = (
            "Preparing to unpack...\n"
            "Setting up firmware-iwlwifi (20230210-5) ...\n"
            "update-initramfs: Generating /boot/initrd.img-6.1.0\n"
            "dpkg: error processing package firmware-iwlwifi (--configure):\n"
            " installed firmware-iwlwifi package post-installation script subprocess returned error exit status 1\n"
            "Errors were encountered while processing:\n"
            " firmware-iwlwifi\n"
        )
        stderr = (
            "debconf: delaying package configuration, since apt-utils is not installed\n"
            "E: Sub-process /usr/bin/dpkg returned an error code (1)\n"
        )
        with mock.patch(
            "subprocess.run",
            return_value=subprocess.CompletedProcess(
                ["apt-get", "install"], 100, stdout, stderr
            ),
        ):
            with self.assertRaises(FreshAbInstallError) as ctx:
                SubprocessHardwareSupportRunner().run(["apt-get", "install"])
        message = str(ctx.exception)
        self.assertIn("firmware-iwlwifi", message)
        self.assertIn("dpkg: error processing package", message)
        self.assertNotIn("debconf: delaying", message)

    def test_low_space_details_are_not_lost(self) -> None:
        message = _apt_failure_detail(
            "dpkg: error processing package example (--configure):\n"
            "cannot write new file: No space left on device\n",
            "debconf: delaying package configuration, since apt-utils is not installed\n",
        )
        self.assertIn("No space left on device", message)

    def test_stderr_only_fatal_detail_is_still_reported(self) -> None:
        result = _apt_failure_detail(None, "fatal error: cannot configure package")
        self.assertIn("fatal error", result)

    def test_journal_receives_both_output_streams_on_failure(self) -> None:
        completed = subprocess.CompletedProcess(
            ["apt-get", "install"],
            100,
            "dpkg: error processing package example (--configure):\n",
            "E: Sub-process /usr/bin/dpkg returned an error code (1)\n",
        )
        from io import StringIO

        err = StringIO()
        with mock.patch("subprocess.run", return_value=completed), mock.patch(
            "sys.stderr", err
        ):
            with self.assertRaises(FreshAbInstallError):
                SubprocessHardwareSupportRunner().run(["apt-get", "install"])
        self.assertIn("dpkg: error processing package", err.getvalue())
        self.assertIn("E: Sub-process", err.getvalue())
        self.assertIn("exit=100", err.getvalue())


if __name__ == "__main__":
    unittest.main()
