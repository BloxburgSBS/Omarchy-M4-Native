# J604 kernel patch — the built-in keyboard and trackpad

The alpha.1 kit ships the stock `boot/Image.gz`. On a J604 its
`drivers/hid/dockchannel-hid` driver refuses to wake the MTP input path, so
the built-in keyboard and trackpad enumerate as input devices and then do
nothing.

## Why the stock kernel refuses

`CONFIG_HID_DOCKCHANNEL=y` is compiled into the kernel image, not a
loadable module, so the board gate inside it cannot be changed by swapping a
`.ko`. In the build-18 source the driver asks the board three times whether
the machine is a J713:

```c
400:  of_machine_is_compatible("apple,j713") &&   /* AFE action enabled? */
557:  !of_machine_is_compatible("apple,j713") ||   /* version-2 power requests */
576:  of_machine_is_compatible("apple,j713") &&   /* second gate */
```

All three sit behind `m4_power_v2` and `m4_afe_action`, which the J604 boot
arguments already set:

```
dockchannel_hid.m4_power_v2=1 dockchannel_hid.m4_afe_action=1
```

The board gate is the only thing missing. The device tree already carries the
other half of the fix — `apple,remap-streams = <1 0>, <2 0>, <3 0>` on the
MTP's DART, because the J604's iBoot leaves the MTP halted on stream 0 where
the J713 hands it over running on stream 1.

## The patch used in this kit

The three call sites share **one** string literal in the built image: the
whole 57 MB `Image` contains a single occurrence of `apple,j713`, at offset
**33 963 185**, because the linker merged the identical literals from every
translation unit into one mergeable section. Overwriting those ten bytes
therefore redirects all three gates at once.

```diff
- apple,j713
+ apple,j604
```

`apple,j713` and `apple,j604` are both ten bytes, so the swap is in place:
no offset moves, no relocation changes, and the image size is identical.

The J604's root `compatible` already lists `apple,j604`, so the driver now
asks a question the device tree can answer.

## What else that literal touches

Five files in the tree reference `apple,j713`, and the merge makes them share
the patched literal. The other four are unaffected on this board:

| File | Gate | Effect on the J604 |
|---|---|---|
| `drivers/hid/dockchannel-hid/dockchannel-hid.c` | three board checks | **opens — this is the fix** |
| `init/m4bench_trace.c` | `selected && of_machine_is_compatible(...)` | inert: `selected` comes from the `m4bench_select` boot argument, which is absent and defaults to 0 |
| `drivers/usb/gadget/function/f_acm.c` | `m4bench_no_acm_notify && ...` | inert: `early_param`, default off |
| `drivers/usb/typec/tipd/core.c` | `m4bench_usb2_device && ...` | inert: `early_param`, default off |
| `arch/arm64/kernel/apple-adt-reserve.c` | `fdt_node_check_compatible(..., "apple,j713") || fdt_node_check_compatible(..., "apple,t8132")` | no change: the second condition already matches this board, so the function returned early before the patch too |

## Reproducing and verifying

```sh
gunzip -c boot/Image.gz > Image
# exactly one occurrence, at 33963185
grep -boa 'apple,j713' Image
printf 'apple,j604' | dd of=Image bs=1 seek=33963185 conv=notrunc
gzip -9 -n -c Image > Image.gz
```

`gzip -n` omits the timestamp so the compressed output is reproducible. The
compressed bytes will not match the original gzip stream, which is fine: the
loader only decompresses it. The installer records the new hash in
`IMAGE.json`, `KIT.json` and `SHA256SUMS`.

Verification after the swap:

- the image differs from the original in exactly three bytes, all inside the
  literal (`713` → `604`; the seven-byte `apple,j` prefix is shared)
- `apple,j713` count is 0, `apple,j604` count is 1
- the image size is unchanged and `gzip -t` passes

## The source-level equivalent

`patches-kernel/j715-input/dockchannel-hid-accept-j715.patch` makes the same
change at source level: it replaces the three board checks with a
`dchid_m4_air()` helper that accepts `apple,j713`, `apple,j715` and
`apple,j604` on `apple,t8132`. Building the kernel from that patch produces a
functionally identical driver. The binary route was used here to avoid a full
kernel rebuild; the source patch remains the upstreamable form of the fix.
