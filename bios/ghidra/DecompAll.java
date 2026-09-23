// Decompile every function of the current program into <outdir>/<name>.c,
// where <name> is the imported file name without its extension.
// Used by bios/tools/bios_extract.py as a -postScript; arg 0 is <outdir>.
//@category BIOS
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;
import java.io.FileWriter;
import java.io.PrintWriter;

public class DecompAll extends GhidraScript {
    @Override
    public void run() throws Exception {
        String outDir = getScriptArgs()[0];
        String name = currentProgram.getName().replaceFirst("\\.[^.]*$", "");
        DecompInterface di = new DecompInterface();
        di.openProgram(currentProgram);
        try (PrintWriter pw = new PrintWriter(new FileWriter(outDir + "/" + name + ".c"))) {
            pw.println("// " + currentProgram.getName() + ": Ghidra "
                + currentProgram.getLanguageID() + " decompile, unedited");
            FunctionIterator it = currentProgram.getFunctionManager().getFunctions(true);
            while (it.hasNext()) {
                Function f = it.next();
                DecompileResults r = di.decompileFunction(f, 60, monitor);
                pw.println("// ==== " + f.getName() + " @ " + f.getEntryPoint());
                if (r.decompileCompleted()) {
                    pw.println(r.getDecompiledFunction().getC());
                } else {
                    pw.println("// decompile failed: " + r.getErrorMessage());
                }
            }
        }
    }
}
