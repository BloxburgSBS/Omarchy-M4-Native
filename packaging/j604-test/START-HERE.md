# MacBook Pro 14-inch M4 tester build — J604

For the **MacBook Pro (14-inch, M4, 2024), Mac16,1 / J604 / T8132**. It
follows the J715 tester-kit pattern
([packaging/j715-test](../j715-test/START-HERE.md)) and is built from the
**alpha.1** base kit (`v0.1.0-alpha.1-update.4`). It is not for any other
Mac, and it is not endorsed by Omarchy, Asahi, Gravity or Apple.

The hardware facts it relies on come from a read-only macOS survey of a real
J604 ([docs/j604-macos-survey.md](../../docs/j604-macos-survey.md)).

## What this kit contains

| File | What it does |
|---|---|
| `g16-j604.patch` | The kernel GPU module, patched against the **alpha.1** source packet (`omarchy-j713-v0.1.0-alpha.1-gpu-air-source.tar.gz`), not against `develop`. It admits `apple,j604` in `firmware_allowed`, and gives the J604 its own platform gate |
| `../../patches/j604-board.dtso` | Board overlay on the J713 devicetree: `apple,j604` identity, `apple,guam` radios, `apple/tpmtfw-j604.bin` trackpad, `mtp_dart` stream-0 remap |
| `../../tools/build-j604-dtb.py` | Builds the J604 boot devicetree from the pinned J713 base (`j713-usb0.dtb`, sha256 `352bfa74…`) |
| `../../patches-kernel/j715-input/dockchannel-hid-accept-j715.patch` | Kernel `dockchannel-hid` gate accepting `apple,j715` and `apple,j604` on the T8132 MTP input path |
| `kboot-j604-develop-tree.patch` | **Not used by this kit.** A J604 row for the `develop` tree's table-based loader. The alpha.1 loader in this kit has no per-board table — see below |

## The loader needs no change

The alpha.1 loader (`m1n1/src/kboot_gpu.c`, `src/m4_power.h`) does not carry
per-board calibration curves. It **computes** the power model from the ADT
ladder, the leakage register at `0x3882c81dc`, the core count read from the
GPU, and the `gpu-supports-higher-mA` selector:

```c
float maximum = higher_ma ? 37000.0f : 24800.0f;   /* mA clamp */
*result = (uint32_t)(voltage * current);            /* mW */
```

and it already accepts an eleven-group ladder
(`if (groups != 10 && groups != 11) bail(...)`). The J604's ADT has exactly
eleven groups and sets `gpu-supports-higher-mA`, so the loader emits the
J604's own limit without a patch.

Running the loader's own `m4_power_mw` over the J604 ladder (ten cores,
`higher_ma` set) gives:

| Leakage | Derived `apple,m4-max-power-mw` |
|---|---|
| 2 | 32 655 mW |
| 64 | 32 888 mW |
| 512 | 34 572 mW |
| 2048 | 39 111 mW |
| 4096+ | 39 219 mW (clamped at 37 000 mA) |

So the module's gate accepts **32 655 … 39 219 mW** for the J604. (The Air's
derived value is 24 800 mW for *every* leakage value, because its 24 800 mA
clamp always binds — which is why alpha.1 could compare the Air's power
exactly, and why the J604 needs a range.)

The relative power table the loader emits for the J604 at leakage 512 is
`[0, 7, 13, 19, 25, 33, 42, 51, 58, 76, 100]` — computed, not observed, so
no macOS GPU-memory dump is needed for this board.

## What the module patch changes

Three things, all in `drivers/gpu/drm/asahi/g16.rs`:

1. `firmware_allowed` admits `apple,j715` and `apple,j604` alongside
   `apple,j713` (inline, so the extracted policy functions stay
   standalone-compilable for the gate tests).
2. The board identity is hoisted out of the qualification block.
3. The platform check becomes board-aware. The Air path keeps alpha.1's
   strictness exactly (mask `0x3ff`, ten groups, 1470 MHz, power exactly
   24800); the J604 path accepts the ten-core mask `0x3ff` (or a fused
   eight-core subset), eleven groups, 1578 MHz, and the derived power range
   above.

## What still needs doing before a first boot

1. **Build the module**: run `gpu/j713/build-test-module.sh` in the
   `m4-gravity-builder:20261008` container with the alpha.1
   `kernel-controller.tar.gz` and the GPU source packet. The script rebuilds
   alpha.1 first and requires the shipped module hash `80cf3669…`, so the
   build proves itself before the J604 delta is applied.
2. **Rebuild the kernel with the updated dockchannel HID gate**:
   `patches-kernel/j715-input/dockchannel-hid-accept-j715.patch` now admits
   `apple,j604`, and `patches/j604-board.dtso` sets
   `apple,remap-streams = <1 0>, <2 0>, <3 0>` on `mtp_dart`
   (`/soc/iommu@394800000`) for the J604's halted stream-0 iBoot handoff —
   build `boot/Image.gz` with `tools/build-j715-kernel.sh` so the shipped
   kernel carries the updated gate.
3. **The installer profile**: the `j604ap` entry is in
   `patches/installer/j713-recovery-radio-profile.patch`, with the BCM4388 C2
   "guam" Wi-Fi and Bluetooth mappings.
4. **The third TB4 controller** (`usb-drd3`) is not in the J713 tree; the
   first kit brings up the two Air-equivalent ports.
5. **The speakers** (six `sn012776` amps, acoustic ID 30) are off in the
   first kit.

## What to expect on a first boot

| Part | Expectation |
|---|---|
| GPU | Should initialize — same T8132 silicon, B1 revision, same GPU ID as the Airs, and a loader that needs no change for it |
| Internal display | Likely black — DCP is not brought up on T8132. Use SSH or USB serial; nothing in this kit needs the panel |
| Keyboard, trackpad | Should work (same MTP wiring as the Airs, J604 firmware) |
| Wi-Fi, Bluetooth | Should work with the `guam` firmware |
| USB-C | Two of three ports |
| Power | Shut down expected to work via the Abbey PMU; **do not use Suspend** |

## Watch item

`get_t8132_core_mask()` in the loader compares the GPU's hardware performance
map (registers `0xe01400` / `0xe01480`) against the ADT's `index_a`/`index_b`
and bails on a mismatch. With eleven groups it reads six register pairs. The
J604's ADT and its GPU firmware come from the same Apple source, so they
should agree, but this is the first board to exercise the eleven-group path
through that check.

## Safety

Installation changes partitions and boot policy. Back up first. The project's
board rule applies: this kit must refuse every model except Mac16,1, and
J604 moves from `testing` to `qualified` only with boot evidence recorded in
this repository.
