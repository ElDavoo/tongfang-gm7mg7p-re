// Decompile a program and write it out, with the provenance header this
// repository requires of generated tool output.
//
// Two modes, because the three components want different shapes:
//   per-function   one .c per function, file named by address (the EC's
//                  end state in ec/ghidra/README.md: a C codebase that mirrors
//                  the firmware function for function). File names are keyed
//                  on the ADDRESS and not the function name on purpose: names
//                  change as the reading improves, and a rename must not churn
//                  a file path in git. The index carries addr -> name.
//   per-program    one .c per program/module, the shape bios/decompiled/ and
//                  the Windows native export already use.
//
// args:
//   0  output directory (created if absent)
//   1  index CSV to append rows to (header written by the driver)
//   2  mode: per-function | per-program
//   3  context file, key=value lines, keys read here:
//        source, sha256, ghidra_version, generator, symbols, annotations,
//        component, evidence
//   4  seed basis CSV, header-only, columns: program,addr,basis (or "" )
//
// The decompiler-availability guard matters more than anything else here, and
// it is TongFang.openDecompiler() rather than a copy: Ghidra's native
// decompiler can fail to load -- e.g. if the release was unpacked by something
// that dropped the exec bit on
// Ghidra/Features/Decompiler/os/linux_x86_64/{decompile,sleigh} -- and when it
// does, DecompInterface.openProgram() returns FALSE and getErrorMessage() is
// the EMPTY STRING. That is indistinguishable, from the output, from "this
// function will not decompile", which is exactly the mistake
// windows/antitamper/README.md exists to stop people making about a different
// cause with the same shape. It used to live in this file, where the file that
// exists so it cannot drift did not have it, and ApplyAnnotations.java now
// opens a decompiler too and would have carried a second copy.
//@category TongFang
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;
import java.io.FileWriter;
import java.io.PrintWriter;
import java.util.HashMap;
import java.util.Map;

public class ExportDecompile extends GhidraScript {

    private static final int DECOMPILE_TIMEOUT_S = 120;

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 5) {
            throw new IllegalArgumentException("usage: ExportDecompile.java <outdir> <index.csv> "
                + "<per-function|per-program> <context.txt> <seed-basis.csv|->");
        }
        String outDir = args[0];
        String indexPath = args[1];
        String mode = args[2];
        Map<String, String> ctx = readContext(args[3]);
        Map<String, String> basis = readBasis(args[4]);

        // Identity for filenames and index rows. Normally the file stem, but a
        // stem is not unique: GamingCenter3_Cross.exe and GamingCenter3_Cross.dll
        // share one, and keying on it would have one program's export silently
        // overwrite the other's. A driver that imports both supplies
        // `label.<program name>=<label>` in the context file, and
        // assertDistinctLabels below turns a remaining collision into a loud
        // failure rather than a lost file.
        String program = labelFor(ctx, currentProgram.getName());
        assertDistinctLabels(ctx, program);
        // Two different byte counts, because they answer different questions and
        // only one of them is a coverage figure:
        //   instructionBytes -- bytes actually disassembled. The honest "how much
        //     of this image did analysis reach" number.
        //   bodyBytes        -- sum of function body lengths. NOT a coverage
        //     figure: Ghidra's function bodies can overlap, so this double-counts
        //     and can exceed the image size. Reported because it is the number
        //     the decompiler actually walks, not because it is a measurement.
        // Split at the bank window: 0x0000-0x7FFF is the common area, which
        // both bank programs carry, and 0x8000-0xFFFF is this bank's own code.
        // Reporting one total for a bank program would count the common area
        // into both banks and overstate each.
        long commonBytes = 0;
        long windowBytes = 0;
        long bodyBytes = 0;

        DecompInterface di = TongFang.openDecompiler(currentProgram, program);

        new File(outDir).mkdirs();
        FunctionIterator it = currentProgram.getFunctionManager().getFunctions(true);
        int n = 0, good = 0, bad = 0;
        ghidra.program.model.listing.InstructionIterator iit =
            currentProgram.getListing().getInstructions(true);
        while (iit.hasNext()) {
            ghidra.program.model.listing.Instruction ins = iit.next();
            if (ins.getAddress().getOffset() < 0x8000L) {
                commonBytes += ins.getLength();
            } else {
                windowBytes += ins.getLength();
            }
        }
        PrintWriter index = new PrintWriter(new FileWriter(indexPath, true));
        PrintWriter whole = "per-program".equals(mode)
            ? new PrintWriter(new FileWriter(new File(outDir, program + ".c")))
            : null;

        if (whole != null) {
            writeHeader(whole, program, ctx);
        }

        while (it.hasNext()) {
            Function f = it.next();
            n++;
            Address entry = f.getEntryPoint();
            String addrHex = entry.toString().toUpperCase().replace("CODE:", "");
            int size = (int) f.getBody().getNumAddresses();
            bodyBytes += size;
            String name = f.getName();
            String seedBasis = basis.get(addrHex.toUpperCase());
            if (seedBasis == null) {
                seedBasis = "auto";
            }
            String annotated = isPlaceholderName(name) ? "no" : "yes";

            DecompileResults r = di.decompileFunction(f, DECOMPILE_TIMEOUT_S, monitor);
            String c = null;
            if (r.decompileCompleted() && r.getDecompiledFunction() != null) {
                c = r.getDecompiledFunction().getC();
                good++;
            } else {
                bad++;
            }

            String outFile = "";
            if (c != null) {
                if (whole != null) {
                    printlnSeparator(whole, name, addrHex);
                    if ("call-target".equals(seedBasis)) {
                        writeBoundaryCaveat(whole);
                    }
                    whole.println(c);
                } else {
                    outFile = program + "/" + addrHex + ".c";
                    writeFunctionFile(new File(outDir, outFile), program, name, addrHex,
                        seedBasis, ctx, c);
                }
            } else {
                outFile = "(failed)";
                println("ExportDecompile: " + program + " " + name + " @ " + entry
                    + " did not decompile: '" + r.getErrorMessage() + "'");
            }

            // Ten fields, matching the header the driver writes: program, addr,
            // name, size, seed_basis, annotated, type, basis, evidence, out_file.
            // type/basis/evidence are joined in later from the annotations CSV.
            index.println(String.join("\t",
                program, addrHex, name, Integer.toString(size), seedBasis, annotated,
                "", "", "", outFile));
        }

        if (whole != null) {
            whole.close();
        }
        index.close();
        di.dispose();
        println("ExportDecompile " + program + " [" + mode + "]: functions=" + n
            + " decompiled=" + good + " failed=" + bad
            + " common_area_bytes=" + commonBytes
            + " window_bytes=" + windowBytes
            + " body_bytes=" + bodyBytes);
        try (PrintWriter m = new PrintWriter(new FileWriter(args[1] + "." + program + ".counts", true))) {
            m.println(program + "\t" + n + "\t" + good + "\t" + bad
                + "\t" + commonBytes + "\t" + windowBytes + "\t" + bodyBytes);
        }
    }

    private void writeHeader(PrintWriter w, String program, Map<String, String> ctx) {
        w.println("// " + program + ": Ghidra " + get(ctx, "ghidra_version", "unknown")
            + " decompile");
        w.println("// Generated by " + get(ctx, "generator", "unknown") + " -- do not edit;");
        w.println("// improve this by editing the annotations and re-running the generator.");
        w.println("// Source: " + sourceFor(ctx, program)
            + ", SHA-256 " + get(ctx, "sha256", "unknown"));
        String symbols = get(ctx, "symbols", "");
        if (!symbols.isEmpty()) {
            w.println("// XDATA symbols: " + symbols);
        }
        String annotations = get(ctx, "annotations", "");
        if (!annotations.isEmpty()) {
            w.println("// Names/comments: " + annotations);
        }
        w.println("// Machine output carrying this repository's symbols. Not the vendor's source.");
        w.println();
    }

    private void writeFunctionFile(File f, String program, String name, String addrHex,
        String seedBasis, Map<String, String> ctx, String c) throws Exception {
        f.getParentFile().mkdirs();
        try (PrintWriter w = new PrintWriter(new FileWriter(f))) {
            w.println("// " + program + " @ " + addrHex + "   " + name
                + (isPlaceholderName(name) ? "" : "   [named]"));
            w.println("// Ghidra " + get(ctx, "ghidra_version", "unknown")
                + " decompile, generated by " + get(ctx, "generator", "unknown") + " -- do not edit.");
            w.println("// Source: " + sourceFor(ctx, program)
                + ", SHA-256 " + get(ctx, "sha256", "unknown"));
            w.println("// Machine output carrying this repository's symbols. Not the vendor's source.");
            if ("call-target".equals(seedBasis)) {
                writeBoundaryCaveat(w);
            }
            w.println();
            w.println(c);
        }
    }

    /**
     * The call-target census is a byte scan and an upper bound
     * (ec/annotations/bank-call-audit.md §1), so a function boundary that came
     * from it is a hypothesis. Say so at the boundary rather than letting the
     * reading harden into a fact -- the rule CLAUDE.md puts above every other.
     */
    private void writeBoundaryCaveat(PrintWriter w) {
        w.println("// function boundary from a call-target byte scan; that census is an upper bound");
        w.println("// (ec/annotations/bank-call-audit.md §1), so this boundary is a hypothesis.");
    }

    private void printlnSeparator(PrintWriter w, String name, String addrHex) {
        w.println("// ==== " + name + " @ " + addrHex);
    }

    private static Map<String, String> readContext(String path) throws Exception {
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

    private static Map<String, String> readBasis(String path) throws Exception {
        Map<String, String> m = new HashMap<>();
        if (path == null || path.isEmpty() || "-".equals(path)) {
            return m;
        }
        try (BufferedReader r = new BufferedReader(new FileReader(path))) {
            String line = r.readLine();
            while ((line = r.readLine()) != null) {
                if (line.trim().isEmpty()) {
                    continue;
                }
                String[] f = line.split(",", -1);
                if (f.length >= 3) {
                    m.put(f[1].trim().toUpperCase().replace("0X", ""), f[2].trim());
                }
            }
        }
        return m;
    }

    /** `label.<program name>` when the driver supplied one, else the file stem. */
    private static String labelFor(Map<String, String> ctx, String programName) {
        String label = ctx.get("label." + programName);
        if (label != null && !label.isEmpty()) {
            return label;
        }
        return stem(programName);
    }

    /**
     * The context file may list every program in the invocation as
     * `programs=a,b,c` with their labels. If two of them resolve to the same
     * label, their exports would overwrite each other and their index rows
     * would collide -- so refuse, and name the label.
     */
    private void assertDistinctLabels(Map<String, String> ctx, String mine) {
        String list = ctx.get("programs");
        if (list == null || list.isEmpty()) {
            return;
        }
        java.util.Set<String> seen = new java.util.HashSet<>();
        for (String name : list.split(",")) {
            String label = labelFor(ctx, name.trim());
            if (!seen.add(label) && label.equals(mine)) {
                throw new IllegalArgumentException("EXPORT LABEL COLLISION: programs "
                    + list + " resolve to the same export label '" + label
                    + "'. Their .c files and index rows would overwrite each other. "
                    + "Give one of them a distinct 'label.<program name>' entry in the "
                    + "context file.");
            }
        }
    }

    /**
     * `source.<program>` when the driver supplied one, else `source`. One
     * context file drives a batched import of several programs, and the PD
     * image is a different program in a different part of the file -- a header
     * that named only the firmware would let a reader assume otherwise.
     */
    private static String sourceFor(Map<String, String> ctx, String program) {
        String specific = ctx.get("source." + program);
        if (specific == null || specific.isEmpty()) {
            specific = ctx.get("source." + stem(program));
        }
        if (specific != null && !specific.isEmpty()) {
            return specific;
        }
        return get(ctx, "source", "unknown");
    }

    private static String get(Map<String, String> m, String k, String dflt) {
        String v = m.get(k);
        return v == null || v.isEmpty() ? dflt : v;
    }

    /**
     * Ghidra's own placeholder names. Anything else in the program was named by
     * a person, or by ec/annotations/ghidra-functions.csv on their behalf. One
     * definition, used by both the index and the export header -- they used to
     * disagree, and a `thunk_FUN_...` came out marked [named].
     */
    private static boolean isPlaceholderName(String name) {
        return name.startsWith("FUN_") || name.startsWith("LAB_")
            || name.startsWith("SUB_") || name.startsWith("thunk_")
            || name.startsWith("dt_") || name.startsWith("entry")
            || name.startsWith("LABEL") || name.startsWith("UNDEF_")
            || name.startsWith("FUNCODE") || name.startsWith("switchD_");
    }

    /** "bank0.bin" -> "bank0": the file name is an artefact of the import, not an identity. */
    private static String stem(String name) {
        int dot = name.lastIndexOf('.');
        return dot > 0 ? name.substring(0, dot) : name;
    }
}
