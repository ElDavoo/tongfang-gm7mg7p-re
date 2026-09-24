// Helpers every script in this directory uses, so the things that must not
// drift exist once: the context-file contract, the export-identity rules, the
// CSV parser, Ghidra's placeholder-name lists, and the decompiler-availability
// guard.
//
// This is a plain class, not a GhidraScript. Ghidra compiles every .java on the
// script path into the default package and only *runs* the ones named on the
// command line, so a shared class here costs nothing at runtime.
//
// The reason it exists rather than being copied per script: the export-label
// collision check and the decompiler-availability guard are the two checks that
// turn a silent export loss into a loud failure, and a copy in each of four
// files is four chances to weaken one. See ghidra/README.md.

import ghidra.app.decompiler.DecompInterface;
import ghidra.program.model.listing.Program;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

public final class TongFang {

    private TongFang() {
    }

    /**
     * The context file is `key=value` lines. `label.<program name>` gives a
     * program a distinct export label, and `source.<program>` gives it its own
     * provenance line, because one context file drives a batched import of
     * several programs drawn from different parts of one input file.
     */
    public static Map<String, String> readContext(String path) throws Exception {
        Map<String, String> m = new HashMap<>();
        if (path == null || path.isEmpty() || "-".equals(path)) {
            return m;
        }
        try (BufferedReader r = new BufferedReader(new FileReader(path))) {
            String line;
            while ((line = r.readLine()) != null) {
                int eq = line.indexOf('=');
                if (eq > 0) {
                    m.put(line.substring(0, eq).trim(), line.substring(eq + 1).trim());
                }
            }
        }
        return m;
    }

    /** Seed basis, `program,addr,basis`, header-only. */
    public static Map<String, String> readBasis(String path) throws Exception {
        Map<String, String> m = new HashMap<>();
        if (path == null || path.isEmpty() || "-".equals(path)) {
            return m;
        }
        try (BufferedReader r = new BufferedReader(new FileReader(path))) {
            r.readLine();
            String line;
            while ((line = r.readLine()) != null) {
                if (line.trim().isEmpty()) {
                    continue;
                }
                String[] f = splitCsvLine(line);
                if (f.length >= 3) {
                    m.put(f[1].trim().toUpperCase().replace("0X", ""), f[2].trim());
                }
            }
        }
        return m;
    }

    /** `label.<program name>` when the driver supplied one, else the file stem. */
    public static String labelFor(Map<String, String> ctx, String programName) {
        String label = ctx.get("label." + programName);
        if (label != null && !label.isEmpty()) {
            return label;
        }
        return stem(programName);
    }

    /**
     * A stem is not unique: GamingCenter3_Cross.exe and GamingCenter3_Cross.dll
     * share one, and keying on it would have one program's export silently
     * overwrite the other's. The context file may list every program in the
     * invocation as `programs=a,b,c`; if two resolve to the same label their
     * .c files and index rows collide, so refuse and name the label.
     */
    public static void assertDistinctLabels(Map<String, String> ctx, String mine) {
        String list = ctx.get("programs");
        if (list == null || list.isEmpty()) {
            return;
        }
        Set<String> seen = new HashSet<>();
        for (String name : list.split(",")) {
            String label = labelFor(ctx, name.trim());
            if (!seen.add(label) && label.equals(mine)) {
                throw new IllegalArgumentException("EXPORT LABEL COLLISION: programs "
                    + list + " resolve to the same export label '" + label
                    + "'. Their output files and index rows would overwrite each other. "
                    + "Give one of them a distinct 'label.<program name>' entry in the "
                    + "context file.");
            }
        }
    }

    /** `source.<program>`, else `source.<stem>`, else `source`. */
    public static String sourceFor(Map<String, String> ctx, String program) {
        String specific = ctx.get("source." + program);
        if (specific == null || specific.isEmpty()) {
            specific = ctx.get("source." + stem(program));
        }
        if (specific != null && !specific.isEmpty()) {
            return specific;
        }
        return get(ctx, "source", "unknown");
    }

    public static String get(Map<String, String> m, String k, String dflt) {
        String v = m.get(k);
        return v == null || v.isEmpty() ? dflt : v;
    }

    /**
     * Ghidra's own placeholder names. Anything else in the program was named by
     * a person, or by <component>/annotations/ghidra-functions.csv on their
     * behalf. One definition, used by every exporter and by the index -- they
     * used to disagree, and a `thunk_FUN_...` came out marked [named].
     */
    public static boolean isPlaceholderName(String name) {
        return name.startsWith("FUN_") || name.startsWith("LAB_")
            || name.startsWith("SUB_") || name.startsWith("thunk_")
            || name.startsWith("dt_") || name.equals("entry")
            || name.startsWith("LABEL") || name.startsWith("UNDEF_")
            || name.startsWith("FUNCODE") || name.startsWith("switchD_");
    }

    /** "bank0.bin" -> "bank0": the file name is an artefact of the import. */
    public static String stem(String name) {
        int dot = name.lastIndexOf('.');
        return dot > 0 ? name.substring(0, dot) : name;
    }

    /**
     * Ghidra's own placeholder names for VARIABLES, as distinct from
     * {@link #isPlaceholderName} for function symbols.
     *
     * Separate rather than folded in, because the two answer different
     * questions and merging them is how one of them stops being right: the
     * index's `annotated` column asks whether a FUNCTION symbol is still
     * Ghidra's, and a variable placeholder never appears there, while the
     * variable-annotation layer keys on exactly these. The families are the
     * ones the committed EC export actually carries, measured over all 2,708
     * files -- `param_`/`uVar`/`cVar`/`bVar`/`sVar` and the rest -- so this
     * list is a reading of the output rather than a guess at the naming scheme.
     *
     * Deliberately NOT here: `DAT_EXTMEM_`. Those are GLOBAL symbols read from
     * the XDATA address map, and they are named by ec/ghidra/xdata-symbols.csv
     * from ec/annotations/registers.yaml. A variable row that renamed one would
     * be a back door for register naming, which is the layer that has the
     * `status:` discipline behind it.
     */
    public static boolean isVariablePlaceholder(String name) {
        return name.startsWith("param_") || name.startsWith("uVar")
            || name.startsWith("cVar") || name.startsWith("bVar")
            || name.startsWith("iVar") || name.startsWith("sVar")
            || name.startsWith("uStack_") || name.startsWith("local_")
            || name.startsWith("in_") || name.startsWith("extraout_")
            || name.startsWith("CONCAT") || name.startsWith("switchD_")
            || name.matches("(i|c|u|b|s)Var[0-9]+")
            || name.matches("extraout_[0-9]+")
            || name.matches("uStack_[0-9A-Fa-f]+");
    }

    /**
     * Open the native decompiler, or refuse loudly.
     *
     * Ghidra's decompiler can be present and still unusable, and it fails
     * SILENTLY: `openProgram()` returns false and `getLastMessage()` is the
     * empty string. From the output alone that is indistinguishable from
     * "this function will not decompile" -- the same shape as the ConfuserEx
     * anti-tamper trap in windows/antitamper/README.md, and the mistake this
     * message exists to stop. Every script that opens one calls this.
     */
    public static DecompInterface openDecompiler(Program program, String label)
            throws Exception {
        DecompInterface di = new DecompInterface();
        if (!di.openProgram(program)) {
            String why = di.getLastMessage();
            di.dispose();
            throw new Exception("DECOMPILER UNAVAILABLE for " + label
                + ": openProgram() returned false, getLastMessage()='" + why
                + "'. An empty message means Ghidra's native decompiler did not "
                + "load -- check the exec bits on $GHIDRA_INSTALL_DIR/Ghidra/"
                + "Features/Decompiler/os/linux_x86_64/{decompile,sleigh}. This is "
                + "NOT a function that will not decompile, and the build must not be "
                + "read as saying it is.");
        }
        return di;
    }

    /**
     * RFC4180 field split. `String.split(",")` is wrong here: the annotations
     * CSV quotes comment cells that contain commas, and a naive split shifted
     * the comment, type and evidence columns by one -- which is a silent
     * mis-citation, the failure this repository's rules care about most.
     */
    /**
     * True when a line ends inside a quoted field, i.e. the record continues
     * on the next line. Counts quotes the way RFC4180 does: a doubled quote
     * inside a quoted field is an escaped quote, not a terminator.
     */
    public static boolean unbalancedQuotes(String line) {
        boolean inQuotes = false;
        for (int i = 0; i < line.length(); i++) {
            if (line.charAt(i) != '"') {
                continue;
            }
            if (inQuotes && i + 1 < line.length() && line.charAt(i + 1) == '"') {
                i++;
            } else {
                inQuotes = !inQuotes;
            }
        }
        return inQuotes;
    }

    public static String[] splitCsvLine(String line) {
        List<String> out = new ArrayList<>();
        StringBuilder cur = new StringBuilder();
        boolean quoted = false;
        for (int i = 0; i < line.length(); i++) {
            char c = line.charAt(i);
            if (quoted) {
                if (c == '"') {
                    if (i + 1 < line.length() && line.charAt(i + 1) == '"') {
                        cur.append('"');
                        i++;
                    } else {
                        quoted = false;
                    }
                } else {
                    cur.append(c);
                }
            } else if (c == '"') {
                quoted = true;
            } else if (c == ',') {
                out.add(cur.toString());
                cur.setLength(0);
            } else {
                cur.append(c);
            }
        }
        out.add(cur.toString());
        return out.toArray(new String[0]);
    }

    /**
     * The address key the index and the seed-basis map use: uppercase, no
     * `0x`, no address-space prefix.
     */
    public static String addrKey(String addr) {
        return addr.toUpperCase().replace("0X", "").replace("CODE:", "");
    }

    /** One file per function, keyed on the address so a rename does not churn paths. */
    public static String functionFileName(String program, String addrHex) {
        return program + "/" + addrKey(addrHex) + ".c";
    }

    public static void mkdirs(File dir) {
        if (dir != null && !dir.isDirectory()) {
            dir.mkdirs();
        }
    }
}
