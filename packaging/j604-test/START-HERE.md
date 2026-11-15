# MacBook Pro 14-inch M4 tester build — DRAFT, NOT YET BOOTED

This kit-in-progress is for the **MacBook Pro (14-inch, M4, 2024), Mac16,1 /
J604 / T8132**. It follows the J715 tester-kit pattern
([packaging/j715-test](../j715-test/START-HERE.md)) and is **not yet built,
not yet booted, and carries one unvalidated calibration** (the GPU power
curves — see below). It is not for any other Mac, and it is not endorsed by
Omarchy, Asahi, Gravity or Apple.

The hardware facts it relies on come from a read-only macOS survey of a real
J604 ([docs/j604-macos-survey.md](../../docs/j604-macos-survey.md)).

## What this kit contains so far

| File | What it does |
|---|---|
| `g16-j604.patch` | Kernel GPU module: admits `apple,j604`, and its own platform gate for the J604's eleven-group, 1578 MHz / 1060 mV ladder with a 27000 mW ceiling |
| `kboot-j604.patch` | Bootloader: a J604 row in `t8132_gpu_boards[]` (11 groups, 26288 mW, ten-core fallback mask). **The `pwr_calib` curves in it are an interpolated placeholder, not observed macOS init data** — replace them with a GPU-memory observation before sustained load |
| `../../patches/j604-board.dtso` | Board overlay on the J713 devicetree: `apple,j604` identity, `apple,guam` radios, `apple/tpmtfw-j604.bin` trackpad |
| `../../tools/build-j604-dtb.py` | Builds the J604 boot devicetree from the pinned J713 base |

## What still needs doing before a first boot

1. **Installer profile.** A `j604ap` entry in the asahi-installer `DEVICES`
   table pointing at a recovery-image stub that carries the J604's firmware
   (the `26.5.1` stub is the starting guess — verify the `guam` radio
   firmware and `tpmtfw-j604.bin` are in it before shipping).
2. **Kernel dockchannel HID gate.** Extend the J713/J715 gate to accept
   `apple,j604`, as the J715 kit did.
3. **The GPU calibration observation.** Read macOS's GPU-firmware init data
   on a running J604 (the method both existing board rows used) and replace
   the placeholder curves in `kboot-j604.patch`. Until then, treat the GPU as
   experimental: expect the power governor to be wrong under sustained load.
4. **Build the kernel + bootloader** with both patches and the J604
   devicetree, and assemble the kit the way `derive-j715-test-kit.py` does.

## What to expect on a first boot (once assembled)

| Part | Expectation |
|---|---|
| GPU | Should initialize (same T8132 silicon, B1 revision, same GPU ID as the Airs) — with placeholder calibration |
| Internal display | Likely black — DCP is not brought up on T8132. Use SSH/serial over USB; nothing in this kit needs the panel |
| Keyboard, trackpad | Should work (same MTP wiring as the Airs, J604 firmware) |
| Wi-Fi, Bluetooth | Should work with the `guam` firmware — **untested chip family (BCM4387) on this stack** |
| USB-C | Two of three ports (the Air-equivalent pair); `usb-drd3` is future work |
| Power | Shut down expected to work via the Abbey PMU; **do not use Suspend** |
| Speakers | Off — the seven-amp system is its own bring-up |

## Safety

Installation changes partitions and boot policy. Back up first. The project's
board rule applies: this kit must refuse every model except Mac16,1, and
J604 moves from `testing` to `qualified` only with boot evidence recorded in
this repository.
