#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

export PYTHONPATH="src:."

python3 -m unittest \
  tests.test_hardware_enablement \
  tests.test_hardware_support_pool_manifest \
  tests.test_hardware_support_pool_finalize \
  tests.test_hardware_support_pool_build_script \
  tests.test_live_hardware_firmware_build_script \
  tests.test_hardware_enablement_build_contract \
  tests.test_hardware_enablement_initramfs_contract \
  tests.test_installer_builder_hardware_support \
  tests.test_installer_hardware_support_pool \
  tests.test_installer_hardware_enablement \
  tests.test_installer_hardware_support_install \
  tests.test_installer_hardware_support_service \
  tests.test_installer_engine \
  -v

python3 -m unittest \
  tests.test_installer_wifi \
  tests.test_installer_wifi_setup \
  tests.test_installer_wifi_persistence \
  tests.test_installer_wifi_build_contract \
  tests.test_installer_state \
  tests.test_build_profiles \
  -v

make verify
