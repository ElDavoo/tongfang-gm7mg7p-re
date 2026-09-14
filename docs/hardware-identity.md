# Hardware identity

| | |
|---|---|
| `sys_vendor` | PCSpecialist |
| `board_vendor` / `board_name` | TongFang / **GM7MG7P** |
| Uniwill platform name | **GM5MG7Y** (`FBM-GM5MG7Y0024PCS`) |
| `bios_vendor` / `bios_version` / `bios_date` | American Megatrends Inc. / `N.1.09A08` / 2021-03-18 |
| CPU / GPU | i7-10875H / RTX 3070 Laptop |
| EC | ITE-based, firmware string `ITE EC-V14.6`, dumped as `GMxMGxx_11.800` |
| ACPI HID | `INOU0000` (matches Linux `uniwill-laptop` and Windows `ACPIDriver.inf`) |
| EC `PROJECT_ID` (`0x0740`) | `0x0F` = `PROJECT_ID_CML_GAMING` (per both `uniwill-laptop` and vendor `ITE_SPEC.EC_PROJECT_CML_Gaming`) |
| Battery | 4S Li-ion, `voltage_min_design` 15.2V, design capacity 4100 mAh / ~62.3 Wh |
| Battery (current) | 445 cycles, ~48.8% health (2000/4100 mAh `charge_full`/`charge_full_design`) |
| RGB controllers | Two ITE 8291 HID devices: `048D:CE00` (usage page `0xFF12`, 4-zone keyboard) and `048D:6005` (usage page `0xFF03`, lightbar — **not currently claimed by any Linux driver**) |

This board is **not** in `uniwill-laptop`'s DMI match table (which only
lists TUXEDO/Schenker/Intel-NUC-rebrand models) — everything in this repo
exists to build a correct, evidence-backed DMI entry / feature descriptor
for an eventual upstream PR, and to resolve the charge-limit discrepancy
between Windows and Linux before claiming that feature works.
