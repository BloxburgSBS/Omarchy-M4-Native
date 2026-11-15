# J604 (MacBook Pro 14-inch, M4) — macOS-side survey

Read-only survey of a MacBook Pro (14-inch, M4, 2024) (Mac16,1), made on
the owner's machine on 2026-11-15, following the J715 methodology
([j715-macos-survey.md](j715-macos-survey.md)). Nothing on this page needed
anything installed on the machine. The raw dumps (`ioreg -p IODeviceTree -l
-w0`, `ioreg -a -l`, `system_profiler`, `sw_vers`, `sysctl hw.model`) are kept
privately; this page keeps only hardware facts.

## Identity

| Field | Value | Source |
|---|---|---|
| Model | `Mac16,1` | `sysctl hw.model`, ADT `/model` |
| Target | `J604` / `J604AP` | ADT `/target-type`, `/target-sub-type` |
| Platform | `t8132` | ADT `/platform-name` |
| arm-io compatible | `arm-io,t8132` | ADT `/arm-io` |
| chip-revision | `0x11` | ADT `/arm-io/chip-revision` |
| SoC generation | `H16` | ADT `/arm-io/soc-generation` |
| Die count | 1 | ADT `/arm-io/die-count` |
| System firmware | see below | `system_profiler` |
| macOS | 27.0 (26A428) | `sw_vers` |

The same T8132 SoC and the same chip revision (B1, `0x11`) as the 13-inch
Air (J713) and the 15-inch Air (J715). The device-tree tag is
`EmbeddedDeviceTrees-12661.1.5`.

## Hardware seen from macOS

| Block | What macOS reports |
|---|---|
| CPU | 10 cores: 4 P (`apple,everest`) + 6 E (`apple,sawtooth`) |
| GPU | 10 cores, `gpu,t8132`, `gpu-supports-higher-mA` set |
| Memory | 16 GB |
| Display | Internal Liquid Retina XDR, 3024 × 1964 (`AppleCLCD2`/Parade TCON class) |
| Wi-Fi / Bluetooth | **BCM4388 C2** (Willamette) over PCIe, module `guam` (J713: `garden`, J715: `kos` — same chip family, different module name). The ADT's `wlan-pcie,bcm4387` compatible is Apple's generic binding, present on the Airs too; the silicon is BCM4388C2 per the live registry and `system_profiler` |
| Speakers | `sn012776` amplifiers on `i2c3` (0x38 and its speaker1..5), acoustic ID 30 (J713: 4, AID 37; J715: 6, AID 38). The upstream `t8132-j604.dts` counts six |
| Headphones | `cs42l84` at `i2c1` 0x4b, as on both Airs |
| USB | `atc-phy0`…`atc-phy3`, `usb-drd0`, `usb-drd1`, `usb-drd3` (three TB4 ports; the Airs have two) |
| DCP | `dcp` node present; `DCPEXT0`/`DCPEXT1` with 14 endpoints, `AppleT8132DPTXPort`, `AppleT8132DisplayCrossbar` instantiated |

## GPU: the table differs from both Airs

The `sgx` node carries 16 perf-state rows (`gpu-num-perf-states` = 15 usable
plus the off row), which group into **eleven voltage groups** — the Airs
qualify ten. The top of the ladder is a state the Airs do not have:

| Property | J713 Air (qualified) | J715 Air (testing) | **J604 (this unit)** |
|---|---|---|---|
| Voltage groups | 10 | 10 (assumed as J713) | **11** |
| Top frequency | 1470 MHz | 1470 MHz | **1578 MHz** |
| Top voltage | ~1000 mV (980–1000 mV per unit) | 990 mV | **1060 mV** |
| Derived max power | 24800 mW (ceiling) | 24552 mW | **~26288 mW** (1060 mV × 24800 mA) |
| `gpu-supports-higher-mA` | (not recorded) | (not recorded) | **set** |

Decoded `perf-states` (freq in kHz, voltage in the ADT's raw unit; the J713
module treats the same unit as mV):

```
off:      0        MHz  @ 125
state 1:  338      MHz  @ 640
state 2:  618      MHz  @ 655
state 3:  796      MHz  @ 680
state 4:  928      MHz  @ 725
state 5:  952      MHz  @ 780
state 6:  1056     MHz  @ 780
state 7:  1053     MHz  @ 825
state 8:  1170     MHz  @ 825
state 9:  1152     MHz  @ 865
state 10: 1278     MHz  @ 865
state 11: 1204     MHz  @ 895
state 12: 1338     MHz  @ 895
state 13: 1326     MHz  @ 970
state 14: 1470     MHz  @ 970
state 15: 1578     MHz  @ 1060   <- boost state the Airs' table does not reach
```

Consequences for the port:

- `g16.rs`'s Air gate (`groups == 10`, `max_mhz == 1470`, and, in alpha.1,
  `max_power == 24800` exactly) rejects this table. The J604 needs its own
  gate values: 11 groups, 1578 MHz, and a power *range* rather than one
  number — see below.
- **The alpha.1 loader needs no change for this board.** It has no
  per-board calibration table: it computes the power model from the ADT
  ladder, the leakage register at `0x3882c81dc`, the core count read from
  the GPU, and the `gpu-supports-higher-mA` selector
  (`m1n1/src/m4_power.h`, `float maximum = higher_ma ? 37000.0f :
  24800.0f;`). It already accepts an eleven-group ladder
  (`if (groups != 10 && groups != 11) bail(...)`), and this board sets
  `gpu-supports-higher-mA`, so the J604's own limit is emitted without a
  patch. Running that model over this ladder gives a derived limit of
  **32 655 mW** at the lowest plausible leakage and **39 219 mW** at the
  37 000 mA clamp, so the module's gate takes 32 655 … 39 219 mW. (The Air's
  derived value is 24 800 mW for *every* leakage value, because its 24 800 mA
  clamp always binds — which is why alpha.1 could compare the Air's power
  exactly.)
- The relative power table the loader emits for the J604 is therefore
  computed, not observed: `[0, 7, 13, 19, 25, 33, 42, 51, 58, 76, 100]` at
  leakage 512. No macOS GPU-memory observation is needed for this board.
- The `develop` tree's loader (`GravityLinux/bootloader src/kboot_gpu.c`)
  *does* carry per-board tables (`J773g`: 11 groups, 37237 mW; `J713`: 10
  groups, 26250 mW) and would need a J604 row with observed curves — but
  that is a different loader from the one the alpha.1 kit ships.
- The GPU ID check (`0x0a021100`, revision B1) should match, since the chip
  revision equals the Airs'.

## CPU

`voltage-states5-sram` (P) is the same 20-state ladder as both Airs, 912 to
4464 MHz, top-state value 1115 in the ADT's raw unit (both Airs' surveys
record the same top state). `voltage-states1-sram` (E) is 900 to 2892 MHz,
matching the J715's E ladder exactly. The J713 cpufreq, idle, boost-gate and
CPU-temperature work should carry over unchanged.

## Board wiring that differs from the Airs

| Item | J713 / J715 | J604 |
|---|---|---|
| `compatible` / `model` | `apple,j713` / `apple,j715` | `apple,j604`, "Apple MacBook Pro (14-inch, M4, 2024)" |
| Wi-Fi and Bluetooth | BCM4388 C2, `brcm,board-type` `apple,garden` / `apple,kos` | BCM4388 C2, `brcm,board-type` `apple,guam` — same chip family as the Airs, different module firmware, collected by the installer profile |
| Trackpad firmware name | `apple/tpmtfw-j713.bin` / `apple/tpmtfw-j715.bin` | `apple/tpmtfw-j604.bin` (to verify against the recovery image's firmware volume) |
| Speaker amplifiers | 4 (J713) / 6 (J715) `sn012776` | 7 × `sn012776`, acoustic ID 30 — needs its own speaker bring-up; not in the first kit |
| USB-C ports | 2 (`usb-drd0`, `usb-drd1`) | 3 TB4 ports: `usb-drd0`, `usb-drd1`, **`usb-drd3`** (plus `atc-phy0`…`atc-phy3`) |
| Headphone codec | `cs42l84` | same |
| Internal panel | LCD (60 Hz class) | mini-LED XDR 3024×1964 (see the DCP note below) |

The dockchannel MTP sits at the same address as the Airs'
(`dockchannel-mtp@94B00000`, fifo at `0x94b14000`), so the Linux
`/soc/fifo@394b14000/input@8000/multi-touch` trackpad path carries over.
The `apcie@B0000000` complex matches the Airs' register map, so the radios'
PCIe path in the Linux tree is expected to carry over as
`/soc/pcie@1cb0000000/pci@0,0/{wifi,bluetooth}@…` (to confirm on first boot).

## DCP (the internal XDR panel)

`dcp` is present with the same node shape the t8132 gap analysis records as
blocked, and macOS instantiates the full stack: `DCPEXT0`/`DCPEXT1`, 14
`DCPEndpoint`s, `AppleT8132DPTXPort`, `AppleT8132DisplayCrossbar`, four
`AppleDCPDPTXRemotePortProxy` (the TB4 display outputs) and
`AppleDCPExpert`. All register geometry needed for a DCP node (registers,
carveouts, mailbox, `dart-dcp`, `dart-disp0`) is enumerable from this
machine's ADT, and the mainline Asahi DCP driver runs the same 3024×1964
mini-LED XDR panel family on the 14-inch M1 Pro/Max and M2 Pro MacBook Pros.

Two facts that decide the shape of the work:

- **The DCP firmware image is on this machine**:
  `/System/Volumes/Preboot/<volume>/restore/Firmware/dcp/t8132dcp.im4p`
  (4.1 MB, IMG4 with an LZVN-compressed payload).
- **Its generation is 27.0.** This machine's iBoot is `20457.1.29`, which
  m1n1 already knows as `[V27_0] = {V27_0, "27.0", {27, 0, 0}, 3,
  "mBoot-20457.1.29"}`. The kernel's DCP driver accepts 12.3, 13.3/13.5 and
  14.7 only — so the panel needs a *new firmware generation* ported, not a
  new panel driver.

See [j604-xdr-display-plan.md](j604-xdr-display-plan.md) for the full plan.

## What stands between this board and an installer

Checked on `develop` at `df7dc6f`.

- **Board table.** `J604` is `refused` with no installer profile. Moving it
  to `testing` needs a kit and, per the project's rule, boot evidence from
  the board.
- **Boot devicetree.** As for the J715, a J604 devicetree can be built by
  applying a small board overlay (`compatible`, `model`, the radios'
  `brcm,board-type` = `apple,guam`, trackpad firmware name) to the newest
  J713 devicetree — with the USB caveat below.
- **USB.** The Air kit enables `usb-drd0`/`usb-drd1` wiring; the J604's
  third controller (`usb-drd3`) and its ATC PHY are additional board nodes
  the J713 tree does not carry. First kit: bring up the two Air-equivalent
  ports, leave the third for follow-up.
- **GPU module + loader.** `g16.rs` needs the J604 board string and its own
  platform gate (11 groups, 1578 MHz, ~26.3 W), and the loader needs a J604
  row in `t8132_gpu_boards[]` — the one piece whose power-calibration
  numbers are not yet observed from macOS on this board.
- **Speakers.** Seven-amp bring-up with acoustic ID 30 is its own project,
  as the J715's was. Off in the first kit.
