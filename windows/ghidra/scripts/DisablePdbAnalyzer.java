// Disable Ghidra's PDB analyzer before auto-analysis, for the one Windows
// binary that has a PDB.
//
// WHY THIS EXISTS. GamingCenter3_Cross.dll (27 MB, native) has a matching
// 144 MB GamingCenter3_Cross.pdb committed in the .appxsym. Left enabled,
// Ghidra's PDB "Function Internals" background pass runs for 10+ minutes and
// ~2 GB and the import appears to hang. The driver
// (windows/tools/decompile_native.py) runs this as a -preScript and gives that
// one import its own long timeout, so a pathological run cannot hang a whole
// build.
//
// WHICH NAME ACTUALLY WORKS. The UI calls the pass "PDB Function Internals",
// but that is not a settable analysis-option name -- Ghidra logs
// "PDB Function Internals could not be found for this program" and the option
// is a no-op. The analyzer that actually OWNS the internals grind is named
// "PDB Universal" (PdbUniversalAnalyzer in Ghidra's PDB.jar), and disabling
// that is what stops the grind. This script tries both names and prints which
// one stuck, so the driver can record the route that worked rather than a
// guess. Disabling the whole analyzer trades the PDB-derived type names for a
// bounded import -- a deliberate, documented trade for a reproducible build.
//
// This script is Windows-only (it lives beside the PDB that exists only for
// the Windows UWP core). The exporter, the annotation applier and the seeder
// are shared across all three components and live in ghidra/scripts/.
//
//@category TongFang
import ghidra.app.script.GhidraScript;

public class DisablePdbAnalyzer extends GhidraScript {

    @Override
    public void run() throws Exception {
        // Order matters only for the report: "PDB Universal" is the real one.
        String[] names = { "PDB Function Internals", "PDB Universal" };
        for (String n : names) {
            try {
                setAnalysisOption(currentProgram, n, "false");
                println("PDB_DISABLE_OK: " + n);
            } catch (Throwable t) {
                println("PDB_DISABLE_FAIL: " + n + " -> " + t);
            }
        }
    }
}
