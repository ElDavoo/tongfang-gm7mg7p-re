{
  description = "Toolchain for the repository's analysis and gate scripts";

  # Pinned so `nix develop` gives the same tools on every machine, and so the
  # numbers quoted in the READMEs are reproducible rather than "whatever was
  # installed". CI does not use this: .github/actions/project-setup builds its
  # own Ghidra and JDK, and the gates there run on ubuntu-latest with the
  # Python and shellcheck that image ships. This is for the local run, where
  # three of the four things below were missing and the failure was silent-ish
  # (`No module named 'yaml'`, `shellcheck: command not found`).
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.05";

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" ];
      forAll = f: nixpkgs.lib.genAttrs systems (system: f nixpkgs.legacyPackages.${system});
    in
    {
      devShells = forAll (pkgs: {
        default = pkgs.mkShell {
          name = "tongfang-gm7mg7p-re";

          packages = with pkgs; [
            # The gate script's own requirements. `python3` alone is not enough:
            # agent-gates.sh parses ec/annotations/registers.yaml, and PyYAML is
            # not in a bare interpreter's path.
            python3
            python3Packages.pyyaml
            shellcheck

            # The 8051 assembler ec/tools/verify_reassembly.py re-encodes the
            # committed disassembly with. It is the independent half of the
            # 1:1 check: Ghidra decodes, sdas8051 encodes, the firmware
            # arbitrates. Without it the tool says it did not run and
            # `--check` falls back to comparing the committed report against
            # the committed listings.
            sdcc

            # Not strictly needed -- the Ghidra scripts are plain Java and the
            # tools are plain Python -- but the BIOS extraction shells out to
            # these, and having them here means a full local rebuild works.
            # `p7zip`, not `7zip`: an attribute name starting with a digit is
            # not a Nix identifier, and `with pkgs; [ 7zip ]` silently
            # produces a non-derivation that only fails at build time.
            unzip
            p7zip
            innoextract
            jre
          ];

          shellHook = ''
            echo "tongfang-gm7mg7p-re dev shell"
            echo "  python3      $(command -v python3) (with PyYAML)"
            echo "  shellcheck   $(command -v shellcheck)"
            echo "  sdas8051     $(command -v sdas8051 || echo 'not on PATH')"
            echo
            echo "  gates        bash .github/scripts/agent-gates.sh"
            echo "  tests        bash tools/run-tests.sh"
            echo "  1:1 check    python3 ec/tools/verify_reassembly.py --work /tmp/ec --report"
            echo "  EC rebuild   python3 ec/tools/build_ec_decompile.py --work /tmp/ec"
            echo
            echo "  Ghidra is NOT here: it is 12.1.3 and a committed project only"
            echo "  reopens in the version that wrote it, so install the same one"
            echo "  .github/actions/project-setup pins. Put its support/ on PATH:"
            echo "    export PATH=/path/to/ghidra_12.1.3_PUBLIC/support:\$PATH"
            echo "    export JAVA_HOME=/path/to/jdk-21"
          '';
        };
      });
    };
}
