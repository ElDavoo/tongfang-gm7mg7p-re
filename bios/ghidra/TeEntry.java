// Pre-script for a TE image loaded raw (BinaryLoader) at its XIP address:
// disassemble and name the entry point so auto-analysis follows calls from it.
// Used by bios/tools/bios_extract.py; arg 0 is the entry address in hex.
//@category BIOS
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;

public class TeEntry extends GhidraScript {
    @Override
    public void run() throws Exception {
        Address entry = toAddr(Long.parseLong(getScriptArgs()[0], 16));
        disassemble(entry);
        createFunction(entry, "entry");
        currentProgram.getSymbolTable().addExternalEntryPoint(entry);
    }
}
