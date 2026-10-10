# Tracing 0x0391 and DB0B's arithmetic sources (issue #1486)

This write-up traces the source of the values fed into the `×10 + 0x0AAA` and `×10 + 0x0A46` arithmetic in two writers of `0x0502`/`0x0503` by walking `0x0391`'s writer and DB0B's arithmetic through the committed decompiled code, and determines whether these values are converted temperature readings.

**No live test was run and none could be.** Everything below is a static reading of the committed listings and decompiled C; the strongest claim it makes is that a value's provenance is traceable through the code to its source in the `0x1C00` block poll.

---

## 1. The two writers of `0x0502`/`0x0503` that use the `×10 + offset` arithmetic

### Writer 1: `bank1/E100` at `E100.asm:105-108`

`FUN_CODE_e100` computes `R0 × 10 + 0x0AAA` and writes it to `0x0502` and `0x0504`:

```
E1A5     mov      B, #0xa
E1A8     mul      AB         ; R0 × 0x0a
E1A9     add      A, #0xaa   ; low byte += 0xaa
E1AB     mov      R1, A      ; store low byte
E1AC     mov      A, B       ; carry to high byte
E1AE     addc     A, #0xa    ; high byte += 0x0a + carry
E1B0     mov      R2, A      ; store high byte
E1B5     ;; write to 0x502 via lcall 0x888c
E1B9     lcall    0x888c
```

The value in R0 comes from `0x0391` at `E100.asm:67-69`:

```
E171     mov      DPTR, #0x391
E174     movx     A, @DPTR   ; load [0x0391] into A
E175     mov      R0, A      ; store in R0
```

### Writer 2: `bank1/DB0B` at `DB0B.asm:115-126`

`FUN_CODE_db0b` computes `R3 × 10 + 0x0AAA` and writes it to `0x0502`:

```
DBE3     mov      A, R3      ; load R3
DBE4     mov      B, #0xa    ; B = 0x0a
DBE7     mul      AB         ; R3 × 0x0a
DBE8     mov      R3, A      ; store low byte of product
DBE9     mov      A, #0xaa   ; A = 0xaa
DBEB     add      A, R3      ; add low byte of product
DBEC     mov      R3, A      ; store in R3
DBED     mov      A, #0xa    ; A = 0x0a
DBEF     addc     A, B       ; add high byte of product + carry
DBF1     mov      R4, A      ; store in R4
DBF2     mov      DPTR, #0x502
DBF5     lcall    0x889e     ; write R3:R4 to 0x0502
```

The value in R3 at line DBE3 comes from R3 being overwritten after a poll succeeds. (The instruction is part of the carry-clear arm at `DB0B.asm:100`, `mov A, R3`, following the poll at `:98`.)

### Writer 3: `bank1/E8A4` at `E8A4.asm:45-51`

`compute_097e_times_10_write_0386_0387` computes `R5 × 10 + 0x0A46` and writes it to `0x0502` and `0x0504`:

```
E8E5     mov      B, #0xa
E8E8     mul      AB         ; R5 × 0x0a
E8E9     mov      R3, A      ; store low byte
E8EA     mov      R4, B      ; store high byte
E8EC     mov      R1, #0x46  ; R1 = constant 0x46
E8EE     mov      R2, #0x0a  ; R2 = constant 0x0a
E8F0     lcall    0x8854     ; add constants to product
;; then write to 0x0502 and 0x0504 via 0x889e
```

(E8A4 computes `R5 × 10` and then adds 0x0A46 via a helper function at 0x8854. The value in R5 is built up through a loop and represents something tracked by 0x097E.)

---

## 2. Where `0x0391`'s value comes from: the `0x1C00` block poll

### 0x0391 is NOT param_1 of DB0B

Per `docs/findings/xdata-0390-0391-filter-pair.md` §3, the register-tracking artifact in Ghidra's decompile renders the store at `DB0B.asm:100-102` as `XDATA_0391 = param_1`, but this is incorrect:

- The instruction is `mov A, R3` at `DB0B.asm:100`.
- R3 enters the function as param_1 (the function's first argument).
- But the poll immediately before the store, `lcall 0xc4f0` at `DB0B.asm:97`, overwrites R3 with the low byte of the 16-bit value returned from XDATA `0x1C04`:0x1C05.
- The hand-decode at `C4F0.c:10` already records this: R3 is loaded from XDATA 0x1C04 on the poll's success path.

Therefore, **`0x0391` holds the value from XDATA `0x1C04`, not the function's argument.**

### The source: `bank1/C4F0` poll

`poll_1c00_status_up_to_100_cycles` (`C4F0.c:10`) loads the value:

```
XDATA_1C03 = DAT_EXTMEM_0975
XDATA_1C02 = DAT_EXTMEM_0976
DAT_EXTMEM_1c00 = 0xff
XDATA_1C01 = 0x48
... poll up to 100 cycles ...
if ((DAT_EXTMEM_1c00 & 0x7c) == 0) {
    load R3 from XDATA 0x1C04
    load R4 from XDATA 0x1C05
    return with carry clear (success)
}
```

The poll is called from multiple sites: `DB0B.asm:97` (with carry-clear arm writing to `0x0391`), `E100` earlier in the execution chain, and elsewhere.

### What writes to 0x1C04

Per the registers.yaml search result on `0x1C3A` (which receives 0x1C04's paired value), 0x1C04 is written by:

- `copy_0866_86b_to_1c04_1c3a`: Copies from XDATA 0x0866 (and other addresses) to three destinations including 0x1C04.
- Case handlers at 0xD221, 0xD24E that write it from XDATA 0x0863 and 0x0864.

**The committed decompile does not identify what 0x0866 contains or what command/request triggers the 0x1C00 block transfer.** The next hop in the provenance chain — what populates 0x0866 — is not settled here.

---

## 3. Is the `×10 + offset` arithmetic consistent with temperature conversion?

### The offset values

- `0x0AAA` = 2730 decimal = 273.0 × 10 = 273.0 K
- `0x0A46` = 2630 decimal = 263.0 × 10 = 263.0 K

### The hypothesis

If a value **X** represents:
- A temperature in deciCelsius (tenths of Celsius), i.e., `X = T°C × 10`

Then the arithmetic `X × 10 + 0x0AAA` becomes:
- `(T°C × 10) × 10 + 273.0 × 10` = `T°C × 100 + 2730` (in deciCelsius)
- Which is equivalent to `T°C + 273` (in Kelvin) × 10 = **deciKelvin conversion**.

The shape `value × 10 + 0xAA` (or `0xAAA`), where the offset is 273.0 K, **is consistent with converting deciCelsius into deciKelvin.**

### Limitations

This is an arithmetic identity, not evidence of behaviour:

1. **The input's nature is not established by static analysis.** The value written to 0x1C04 comes from 0x0866 (and other sources), which the decompile does not identify. No method in this analysis determines whether 0x1C04 represents a temperature, a loop count, a channel selector, or any other quantity.

2. **Live behaviour is needed to confirm the hypothesis.** A physical test reading the byte from hardware as different values, observing how it affects downstream calculations, and checking whether the results correspond to temperature changes would settle whether 0x1C04 is a temperature.

3. **The third writer, E8A4, uses `×10 + 0x0A46` (100 dK lower).** If all three were independent channels, the different offset might suggest a tuning constant rather than a universal temperature conversion. But E8A4 explicitly computes `R5 × 10` — a different source — and the two are not known to be interchangeable.

---

## 4. What is established and what is not

**Established by static analysis:**

- 0x0391 is written from XDATA 0x1C04 (via the 0x1C00 block poll), not from DB0B's param_1.
- 0x0391's value is fed into the `×10 + 0xAA` arithmetic in E100.
- The arithmetic shape `value × 10 + 273.0 K` is consistent with deciCelsius-to-deciKelvin conversion.

**Not established, method named:**

- **What 0x1C04 represents** — static scan of committed decompile lists the copy sites (0xD0xx functions) but does not identify a source beyond 0x0866, and the consumer of 0x1C04 is not named in the decompile. Tracing 0x0866 backward would require a decompile of the EC's *command handler*, which is not available in the committed listings.
- **Whether the input is actually a temperature** — this requires live observation (reading the byte at different points, observing downstream effects, and comparing against known temperatures).

**Conclusion for register status:** 0x0391 is confirmed to be written and read in committed decompiled code, but its semantic meaning (whether it is a temperature, scale, or other quantity) cannot be determined without additional evidence. Status: `present-untested`.

---

## 5. Update to PACK_TEMP_DK note

The existing note in `registers.yaml` for `PACK_TEMP_DK` states:

> "0xAF06's third route copies 0x0502/0x0503, whose four writers are bank1 0xAC84, 0xDB0B, 0xE100 and 0xE8A4 -- two of which compute `value x 10 + 0x0AAA` and one `value x 10 + 0x0A46`, so the word is at minimum overwritten by scaled arithmetic on four paths."

This characterization is **still accurate** after tracing the sources:

- The two writers that compute `value x 10 + 0x0AAA` are E100 (from 0x0391 = 0x1C04) and DB0B (also from 0x1C04 via the poll).
- Both use the same value source, but E100 and DB0B write on different code paths (one on success of the poll, one conditionally later).
- The statement "whether the EC ever reaches [0x0502/0x0503] with a real temperature is **not** established" remains true: the input's provenance in 0x1C04 goes back to 0x0866 and command handlers that are not decoded here.

No change to the PACK_TEMP_DK note is needed; the existing wording holds.

---

## 6. What would settle the questions

1. **To identify what 0x1C04 carries:** A decompile of the EC's 0x1C00 block command handlers (the functions that write 0x0866) and a trace of what calls them.

2. **To confirm whether it is a temperature:** A live test reading 0x1C04 at multiple points under different thermal conditions and checking whether the resulting 0x0502/0x0503 values correspond to known battery or ambient temperatures.

3. **To distinguish the three writers' use cases:** Hardware observation of when each of 0xAC84/0xDB0B, 0xE100, and 0xE8A4 are invoked, and what conditions differ between them.
