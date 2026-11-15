#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 BloxburgSBS
"""Build the MacBook Pro 14-inch M4 (J604) boot devicetree from the J713 one
(docs/j604-macos-survey.md). Modeled on tools/build-j715-dtb.py."""
import argparse
import importlib.util
from pathlib import Path
import struct
import subprocess
import tempfile

SPEC = importlib.util.spec_from_file_location(
    'ecluster_dtb', Path(__file__).resolve().with_name('build-j713-ecluster-dtb.py'))
ECLUSTER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ECLUSTER)
require, sha, tree = ECLUSTER.require, ECLUSTER.sha, ECLUSTER.tree

# The front-USB J713 devicetree (docs/j713-front-usb.md), the newest the Air boots.
BASE_SHA256 = '352bfa74351ad7d12d993f752fe9c09d682511bca0d4a60177cda0d716d1d614'
J713 = b'apple,j713\0apple,t8132\0apple,arm-platform\0'
J604 = b'apple,j604\0apple,t8132\0apple,arm-platform\0'
J713_MODEL = b'Apple MacBook Air (13-inch, M4, 2025)\0'
J604_MODEL = b'Apple MacBook Pro (14-inch, M4, 2024)\0'
PORT0 = '/soc/pcie@1cb0000000/pci@0,0'
RADIOS = (PORT0 + '/wifi@0,0', PORT0 + '/bluetooth@0,1')
TRACKPAD = '/soc/fifo@394b14000/input@8000/multi-touch'
MTP_DART = '/soc/iommu@394800000'
MTP_DART_REMAP = struct.pack('>6I', 1, 0, 2, 0, 3, 0)


def expected_nodes(old):
    """Return the exact tree the overlay must produce."""
    expected = {path: dict(props) for path, props in old.items()}
    expected['/'].update(compatible=J604, model=J604_MODEL)
    for radio in RADIOS:
        expected[radio]['brcm,board-type'] = b'apple,guam\0'
    expected[TRACKPAD]['firmware-name'] = b'apple/tpmtfw-j604.bin\0'
    expected[MTP_DART]['apple,remap-streams'] = MTP_DART_REMAP
    return expected


def check_base(old):
    require(old['/'].get('compatible') == J713 and old['/'].get('model') == J713_MODEL, 'Wrong board')
    require(all(radio in old and old[radio].get('brcm,board-type') == b'apple,garden\0' for radio in RADIOS),
            'Unexpected radios')
    require(TRACKPAD in old and old[TRACKPAD].get('firmware-name') == b'apple/tpmtfw-j713.bin\0',
            'Unexpected trackpad firmware')
    require(MTP_DART in old and 'apple,remap-streams' not in old[MTP_DART],
            'Unexpected MTP DART stream remap')


def build(base, output, overlay, dtc='dtc', fdtoverlay='fdtoverlay'):
    require(base.is_file() and not base.is_symlink(), 'Base must be a regular file')
    original = base.read_bytes()
    require(sha(original) == BASE_SHA256, 'Unqualified J713 base DTB')
    require(overlay.is_file() and not overlay.is_symlink(), 'Overlay must be a regular file')
    require(not output.exists() and not output.is_symlink(), 'Output must not exist')
    require(output.parent.is_dir(), 'Output directory must exist')
    old, reservations, cpu = tree(original)
    check_base(old)
    with tempfile.TemporaryDirectory(prefix='j604-dtb-', dir=output.parent) as scratch:
        compiled = Path(scratch) / 'j604.dtbo'
        candidate = Path(scratch) / 'candidate.dtb'
        subprocess.run([dtc, '-q', '-I', 'dts', '-O', 'dtb', '-o', str(compiled), str(overlay)], check=True)
        subprocess.run([fdtoverlay, '-i', str(base), '-o', str(candidate), str(compiled)], check=True)
        data = candidate.read_bytes()
        new, new_reservations, new_cpu = tree(data)
        require(new_reservations == reservations and new_cpu == cpu and new == expected_nodes(old),
                'Candidate changed data beyond the J604 board identity')
        require(base.read_bytes() == original, 'Base changed during build')
        with output.open('xb') as stream:
            stream.write(data)
    return {'base_sha256': sha(original), 'output_sha256': sha(data), 'output_bytes': len(data),
            'overlay_sha256': sha(overlay.read_bytes()), 'board': 'apple,j604',
            'radios': 'apple,guam', 'trackpad_firmware': 'apple/tpmtfw-j604.bin',
            'mtp_dart_remap_streams': '1->0,2->0,3->0',
            'other_properties_reservations_and_boot_cpu_unchanged': True, 'kernel_changed': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--overlay', type=Path,
                        default=Path(__file__).resolve().parents[1] / 'patches/j604-board.dtso')
    parser.add_argument('--dtc', default='dtc')
    parser.add_argument('--fdtoverlay', default='fdtoverlay')
    args = parser.parse_args()
    report = build(args.base, args.output, args.overlay, args.dtc, args.fdtoverlay)
    for key in sorted(report):
        print(f'{key}: {report[key]}')


if __name__ == '__main__':
    main()
