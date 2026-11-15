# J604 XDR display — DCP bring-up plan

Research record for the internal Liquid Retina XDR panel (3024 × 1964,
mini-LED) of the MacBook Pro 14-inch (M4, 2024) / J604 / T8132. Companion to
the hardware facts in [j604-macos-survey.md](j604-macos-survey.md).

Nothing in the first J604 kit needs the panel: the GPU, evdi virtual display,
storage, Wi-Fi and input all work without it. This document is the plan for
the panel itself.

## What this machine already has

| Piece | State on the J604 |
|---|---|
| DCP coprocessor | Present and instantiated by macOS: `DCPEXT0`, `DCPEXT1`, 14 `DCPEndpoint`s, `AppleT8132DPTXPort`, `AppleT8132DisplayCrossbar`, four `AppleDCPDPTXRemotePortProxy` (the TB4 outputs), `AppleDCPExpert` |
| DCP firmware image | `/System/Volumes/Preboot/<vol>/restore/Firmware/dcp/t8132dcp.im4p` (4.1 MB, LZVN-compressed IMG4 payload) |
| DCP firmware generation | **27.0** — this machine's iBoot is `20457.1.29`, which m1n1 already knows as `[V27_0] = {V27_0, "27.0", {27, 0, 0}, 3, "mBoot-20457.1.29"}` |
| ADT geometry | `dcp@AE00000`, `dart-dcp@A340000`, `dart-disp0@A300000` — the same node shape the t8132 gap analysis records as blocked, all values decodable from this machine's own ADT dump |
| Panel | mini-LED XDR, 3024 × 1964 |

## What exists upstream (reusable, not J604-specific)

**m1n1 (loader) is already generic for the DCP.** `src/dcp.c` does
`rtkit_init("dcp", …)`, `src/kboot.c` carves out the DCP's display regions
(`dt_carveout_reserved_regions("dcp", "disp0", …)`) and reserves the DCP
mappings (`dt_reserve_dcp_mappings`). There is no T8132-specific DCP code in
m1n1 — the firmware file is picked up by name (`dcp`) from the firmware
volume, and the asahi firmware extraction renames `t8132dcp.im4p` to it. The
loader side is therefore mostly reuse; the compatibility string it publishes
is the only lever (see below).

**The kernel DCP driver supports three firmware generations**, each with its
own IOMFB implementation over a shared template:

| Generation | Kernel enum | IOMFB file | Lines |
|---|---|---|---|
| 12.3 | `DCP_FIRMWARE_V_12_3` | `iomfb_v12_3.c` | 110 |
| 13.3 / 13.5 | `DCP_FIRMWARE_V_13_5` | `iomfb_v13_3.c` | 115 |
| 14.7 | `DCP_FIRMWARE_V_14_7` | `iomfb_v14_7.c` | 118 |
| shared | — | `iomfb_template.c` | 1495 |

`dcp_check_firmware_version()` in `drivers/gpu/drm/apple/dcp.c` reads
`apple,firmware-compat` from the device tree and accepts only `"12.3.0"`,
`"13.3.0"`/`"13.5.0"` and `"14.7.0"`. Anything else returns
`DCP_FIRMWARE_UNKNOWN` and the probe fails.

The driver matches these compatibles, with a per-SoC port count:

```
apple,t6020-dcp  (M2 Pro/Max)   num_dptx_ports = 1
apple,t8112-dcp  (M2)           num_dptx_ports = 2
apple,dcp        (generic)      num_dptx_ports = 0
apple,dcpext     (extended)     num_dptx_ports = 2
```

The **mini-LED panel path already exists**: `dcp.c` looks for a child
compatible `apple,panel-mini-led` (falling back to `apple,panel`), reads
`apple,max-brightness`, `width-mm` and `height-mm` off it, and sets
`DRM_MODE_CONNECTOR_eDP`. The 14-inch M1 Pro/Max and M2 Pro MacBook Pros run
this same 3024 × 1964 mini-LED XDR panel class on Linux today.

## The gap, precisely

The T8132's DCP firmware is generation **27.0**. The newest the kernel driver
knows is **14.7**. So on a J604:

1. m1n1's `kboot.c` maps the OS firmware version to a compatibility string.
   `V27_0` falls to the `default:` arm, which publishes `os_firmware` itself —
   i.e. `"27.0.0"`.
2. The kernel's `dcp_check_firmware_version()` sees `"27.0.0"`, matches no
   known generation, logs `DCP firmware-compat 27.0.0 (FW: …) is not
   supported` and returns `DCP_FIRMWARE_UNKNOWN`.
3. The DCP probe fails, so no DCP, no internal panel, no IOMFB, and the
   `disp0` carveouts stay unused.

That is the whole blocker, and it is the same shape of blocker the project has
already cleared twice (13.3 → 13.5, and 14.7 for the M2 Pro/Max).

## The work

### 1. Loader side (m1n1) — small

- Add a `V27_0` arm in the compatibility mapping in `src/kboot.c` if the
  generation needs to publish a *different* compatibility string than its own
  version (the 13.3/13.5 pair is the precedent: m1n1 reported 13.5 as
  compatible with 13.3, and the kernel only accepted the pair when the real
  firmware version was also checked).
- Confirm the DCP firmware the loader picks up is the T8132's
  `t8132dcp.im4p` (renamed `dcp` by the firmware extraction) and that the
  firmware volume's `DeviceTree.j604ap.im4p` is what the ADT comes from — the
  J715 survey did exactly this read against the 26.5.1 IPSW with HTTP range
  requests.

### 2. Kernel side — the real work

- `drivers/gpu/drm/apple/version_utils.h`: add `DCP_FIRMWARE_V_27_0`.
- `drivers/gpu/drm/apple/dcp.c`: accept the new compatibility string in
  `dcp_check_firmware_version()`; add the generation to the `fw_compat`
  switches in `_dcp_poweroff()`, `dcp_sleep()` and `dcp_poweron()`.
- `drivers/gpu/drm/apple/iomfb_v27_0.c`: a new IOMFB generation, following
  `iomfb_v14_7.c` as the template — the per-version delta is small in code
  (≈120 lines) but every register offset and endpoint semantic in it has to
  come from reading the 27.0 DCP firmware.
- Possibly `drivers/gpu/drm/apple/dptxep.c` and the `apple,dcpext` port
  count, if the 27.0 firmware changed the DP transmitter endpoint interface
  (it changed between 13.3 and 13.5; the driver comments call this out).

### 3. Device tree — all values available today

The node set the gap analysis calls "blocked" is fully enumerable from the
J604's own ADT: `dcp@AE00000` registers, `dart-dcp@A340000`,
`dart-disp0@A300000`, their DART geometry, the firmware carveout, the
`disp0` piodma alias, and the panel child (`apple,panel-mini-led`,
`apple,max-brightness`, `width-mm`, `height-mm`). The gap analysis lists
exactly this set as the reason it was left blocked: *"DCP has a large
multi-register contract, firmware/carveouts, mailbox, DART and panel wiring;
a partial node would not be useful."*

### 4. m1n1's DCP parser

`m1n1/src/dcp/parser.c` and the endpoint files (`system_ep.c`,
`dptx_port_ep.c`, `dpav_ep.c`) talk to the DCP firmware during boot. If the
27.0 firmware changed those endpoint semantics, m1n1's parser needs the same
treatment the kernel's IOMFB does. m1n1 already carries
`src/dcp_iboot.c` for the display stack.

## Honest effort estimate

- Steps 1 and 3 are mechanical once the values are extracted: the ADT dump
  and the IPSW read are both scripted (the J715 survey's method).
- Step 2 is the project-sized piece. Each previous generation cost the
  upstream project a firmware reverse-engineering pass; the code delta is
  small but the knowledge is not.
- The 14-inch M1/M2 Pro precedent matters here: the *panel* is not the
  unknown, the *firmware generation* is. The XDR panel family, its backlight
  control and its connector handling are already supported by the driver.

So: the display is a **firmware-generation port**, not a panel port. It is the
same problem the project has solved twice before, with a machine whose
firmware and ADT are both fully available for reading.
