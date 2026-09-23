// Seed a raw-binary 8051 import with function entry points, before analysis.
//
// Ghidra's 8051 SLEIGH has no reset-vector concept, so importing a flat bank
// image and running auto-analysis finds *zero* functions -- measured, not
// assumed (ec/ghidra/README.md). This pre-script is what turns 0 functions
// into a function list: it disassembles at each seed address and creates a
// function there, and auto-analysis then propagates from those entry points.
//
// arg 0: seed spec CSV, header-only, columns: program,addr,basis
//        Rows whose `program` is not this program's name are ignored, so one
//        spec file can drive every program in a project.
//
// basis values, and what each one claims about the boundary:
//   vector           an entry in this program's own vector table
//   vector-target    the target of a vector table LJMP
//   stub             a Keil BL51 bank-switch stub (0x1100/0x1114/0x1128/0x113C)
//   call-target      an lcall/ljmp target from ec/annotations/bank-call-targets.csv
//
// The census behind `call-target` is a byte scan and an UPPER BOUND
// (ec/annotations/bank-call-audit.md §1): a target can land inside a data
// table. That is why the basis is carried through to the index and the
// exporter's header rather than being flattened into "function" -- see
// ec/annotations/static-refs-audit.md for the same reasoning applied to XDATA.
//
// What is deliberately NOT seeded: ajmp/sjmp/jc/jz/cjne/djnz targets. Those
// are jumps *within* a function, and seeding them would invent thousands of
// functions inside code that already has them.
//@category TongFang
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Listing;

import java.io.BufferedReader;
import java.io.FileReader;
import java.util.LinkedHashMap;
import java.util.Map;

public class SeedFunctions extends GhidraScript {

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 1) {
            throw new IllegalArgumentException("usage: SeedFunctions.java <seed-spec.csv>");
        }
        String programName = currentProgram.getName();
        Listing listing = currentProgram.getListing();

        // basis -> count, insertion-ordered so the report reads consistently.
        Map<String, Integer> created = new LinkedHashMap<>();
        Map<String, Integer> already = new LinkedHashMap<>();
        int noInstruction = 0;
        int otherProgram = 0;

        try (BufferedReader r = new BufferedReader(new FileReader(args[0]))) {
            String line = r.readLine();          // header
            if (line == null) {
                throw new IllegalArgumentException("empty seed spec: " + args[0]);
            }
            while ((line = r.readLine()) != null) {
                if (line.trim().isEmpty()) {
                    continue;
                }
                String[] f = line.split(",", -1);
                if (f.length < 3) {
                    throw new IllegalArgumentException("short seed row: " + line);
                }
                if (!matches(f[0], programName)) {
                    otherProgram++;
                    continue;
                }
                int addr;
                try {
                    addr = Integer.parseInt(f[1].trim().replace("0x", ""), 16);
                } catch (NumberFormatException e) {
                    throw new IllegalArgumentException("bad address in seed row: " + line);
                }
                String basis = f[2].trim();
                Address a = toAddr(addr);
                if (getFunctionAt(a) != null) {
                    bump(already, basis);
                    continue;
                }
                if (listing.getInstructionAt(a) == null) {
                    // Creates the instruction if the byte sequence decodes here.
                    // Returns false on a byte that cannot start an instruction,
                    // which is a real result (a phantom seed) and is counted,
                    // not hidden.
                    disassemble(a);
                }
                if (listing.getInstructionAt(a) == null) {
                    noInstruction++;
                    continue;
                }
                if (createFunction(a, null) != null) {
                    bump(created, basis);
                } else {
                    // Already inside a function body Ghidra found from another
                    // seed. Also a real result: it means the two seeds overlap.
                    bump(already, basis);
                }
            }
        }

        int total = 0;
        for (Integer v : created.values()) {
            total += v;
        }
        println("SeedFunctions " + programName + ": created " + total + " from spec "
            + args[0] + "  " + created
            + "; already-a-function-or-overlap " + already.values()
            + "; no instruction at " + noInstruction
            + "; rows for other programs skipped " + otherProgram);
    }

    private static void bump(Map<String, Integer> m, String k) {
        m.merge(k, 1, Integer::sum);
    }

    /**
     * A raw-binary import is named after the FILE, so the program Ghidra
     * reports is "bank0.bin" while the spec and the annotations both say
     * "bank0". Compare on the stem as well as the full name, so the spelling
     * a human writes in the CSV is the one that works.
     */
    private static boolean matches(String wanted, String programName) {
        if (wanted.equals(programName)) {
            return true;
        }
        int dot = programName.lastIndexOf('.');
        String stem = dot > 0 ? programName.substring(0, dot) : programName;
        return wanted.equals(stem);
    }
}
