# J604 XDR display — DCP bring-up plan

Plan for the internal Liquid Retina XDR panel (3024 × 1964, mini-LED) of the
MacBook Pro 14-inch (M4, 2024) / J604 / T8132. Companion to the hardware facts
in [j604-macos-survey.md](j604-macos-survey.md).

Nothing in the first J604 kit needs the panel: the GPU, evdi virtual display,
storage, Wi-Fi and input all work without it.

## Headline: the J604 board tree already exists upstream

`aurora-silicon/linux` carries a complete, working **`t8132-j604.dts`**:

```
arch/arm64/boot/dts/apple/t8132-j604.dts        (619 lines)
```

It is not a sketch. It contains:

- **the internal panel through DCP** — `&dcp { apple,panel-width-mm = <302>;
  apple,panel-height-mm = <196>; }` for the full 3024 × 1964 including the
  notch rows, plus the firmware framebuffer's 3024 × 1890 area below the
  notch as a `fb_panel` with `width-mm = <302>, height-mm = <189>`;
- **the M4 PMGR fix** for it — the shared boot framebuffer's
  `power-domains` property is deleted, because the M4 PMGR policy disables
  `ps_dptx_phy` while the loader keeps the display on (the same situation as
  the J713);
- **both external display pipes** — `apple,dp-alt-mode` on the ATC PHYs and
  `dcpext0`/`dcpext1` mailboxes and DARTs enabled, routed through each port's
  display crossbar to its ATC PHY in DisplayPort alt mode (left ports on
  ATC0/ATC1 with typec0/typec1, right port on ATC3 with typec3);
- **the speaker stack** — six `sn012776` amplifiers on `i2c3` (0x38 and its
  `speaker1..5`), each on the SDZ fail-closed group, with the interrupt on
  AP GPIO 14 level-low and the sense slots from `speaker-config`;
- **the audio jack** — `compatible = "apple,j604-macaudio-jack"`.

That is the J604 board bring-up, already written. The Omarchy M4 project's
tree does not carry it, so the work is **porting this board tree and the
DCP support it needs**, not reverse-engineering the panel.

## The firmware-generation question, answered

The concern that a J604 DCP port would need a new IOMFB generation is
mostly resolved. `aurora-silicon/linux`'s `drivers/gpu/drm/apple/version_utils.h`
says it plainly:

> 26.x firmware exists in two unrelated wire lineages. The H17-generation
> firmware (A18 Pro, M5) is a new protocol; **the M4-generation desktop
> firmware (T6041, the M4 Pro/Max) continues the 14.7 IOMFB.** A desktop 26.x
> template instance marks its version with `DCP_FW_DESKTOP`, so that the plain
> ordering against older versions still holds.

This board's DCP firmware is generation **27.0** (`mBoot-20457.1.29`), which
m1n1 already knows as `[V27_0] = {V27_0, "27.0", {27, 0, 0}, 3,
"mBoot-20457.1.29"}`. It is in the M4-generation lineage, so it continues the
14.7 wire format — the work is the version handling (`DCP_FW_DESKTOP`, the
H17-vs-desktop split) that the aurora tree already implements, not a new
IOMFB port.

## Prior art: a sibling MacBook Pro on the same firmware generation

`MikaVohl/omarchy-M5-pro` documents a complete working bring-up of the
**M5 Pro MacBook Pro (J716s / T6050 / Mac17,8)** on `mBoot-20457.60.65.0.1`
(macOS 27.3 beta) — the same 20457 firmware generation as this board:

| Subsystem | Their observed result |
|---|---|
| Panel | **Native DCP, full-notch 3456 × 2234 at 120 Hz** |
| GPU | native, with the board's own GPU config |
| Video encode | **AVE H.264/HEVC Main hardware encode passed** 30-frame software-decode and pixel comparison per codec |
| Video decode | AVD HEVC Main hardware decode bit-identical to software |
| Speakers | protected output with the speaker-guard graph |
| Touch ID | finger enrolled, PAM authentication and unlock observed |
| Streaming | 1080p/60 hardware H.264 Moonlight stream observed |
| Not qualified | suspend/resume, external displays, camera, stability |

Two of those matter directly here: **DCP on this firmware generation works**,
and **the AVE hardware encoder is reachable on Apple Silicon Linux** (the
Omarchy M4 gap analysis lists the media engines as "blocked/longer-term",
which is a statement about that tree's state, not a silicon limit).

Their kernel is `rolotrealanis98/linux` at
`8ab10100a4c1c944797e3fc8345589aff57777df`, derived from the
`aurora-silicon/linux` lineage, with a `apple/t6050-j716s.dtb` in the tree.

## What the J604 path is

1. **Bring across `t8132-j604.dts`** (and the `t8132-j713-j715.dtsi`
   board family it relates to) from `aurora-silicon/linux` into whichever
   kernel tree the kit builds. This single file carries the panel, the
   external display pipes, the speakers and the audio jack.
2. **Bring across the DCP version handling** the aurora tree uses for
   M4-generation 26.x/27.x firmware: the `DCP_FW_DESKTOP` marker, the
   H17-versus-desktop lineage split, and the loader-side
   `apple,firmware-compat` publishing for `V27_0`.
3. **Check the loader's DCP firmware selection**: this board's image is
   `Firmware/dcp/t8132dcp.im4p`, and m1n1's DCP bring-up is generic
   (`rtkit_init("dcp", …)`), so the firmware extraction has to hand it over
   under the name m1n1 expects.
4. **The media engines**, if hardware video encode is wanted for streaming:
   the aurora/avd-fw lineage shows the path (firmware admission, ABI
   matching, host queue interface). This is the one piece that changes the
   streaming story — a hardware encoder removes the CPU cost that software
   x264 puts on the same cores FEX uses.

## What stays J604-specific regardless

- The GPU power-calibration curves (see the survey): the loader's board row
  needs values observed from macOS's GPU-firmware init data, and no such
  observation has been made on a J604 yet. The aurora lineage may have a
  different loader path for T8132 GPUs, which would make this moot — worth
  checking before doing the macOS-as-guest observation.
- The radios: BCM4387 C2 "guam" firmware, a different family from the Airs'.
- The seven (six, per the aurora DTS) speaker amps with acoustic ID 30.
- The third TB4 controller, `usb-drd3`, beyond the two the Air tree carries.

## Effort shape

The display is no longer the open-ended research project it looked like: the
board tree exists, the firmware lineage question is answered, and a sibling
MacBook Pro has already proved the hardware and the firmware generation.
What remains is porting and qualification, which is mechanical work with a
known-good reference — and the same shape of work the Omarchy M4 project has
already done for the J713 and J715.
