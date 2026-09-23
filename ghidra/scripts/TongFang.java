// Helpers every script in this directory uses, so the things that must not
// drift exist once: the context-file contract, the export-identity rules, the
// CSV parser, and Ghidra's placeholder-name list.
//
// This is a plain class, not a GhidraScript. Ghidra compiles every .java on the
// script path into the default package and only *runs* the ones named on the
// command line, so a shared class here costs nothing at runtime.
//
// The reason it exists rather than being copied per script: the export-label
// collision check and the decompiler-availability guard are the two checks that
// turn a silent export loss into a loud failure, and a copy in each of four
// files is four chances to weaken one. See ghidra/README.md.

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
