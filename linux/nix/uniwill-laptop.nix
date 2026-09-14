{
  lib,
  stdenv,
  fetchFromGitHub,
  kernel,
}:
# Driver per l'EC dei portatili Uniwill/TongFang (mattone è un GM5MG7Y, che si
# presenta come TongFang GM7MG7P). Sta in mainline dal 7.2 come
# CONFIG_UNIWILL_LAPTOP, ma nixpkgs non lo abilita
# (X86_PLATFORM_DRIVERS_UNIWILL non è settato), quindi lo compiliamo fuori
# albero. Il sorgente è identico a quello mainline: l'unica differenza del repo
# upstream è il -DDEBUG nel Makefile, che lasciamo perché i dev_dbg aiutano a
# capire se l'EC accetta davvero i comandi.
stdenv.mkDerivation {
  pname = "uniwill-laptop";
  version = "unstable-2026-08-29-${kernel.version}";

  src = fetchFromGitHub {
    owner = "Wer-Wolf";
    repo = "uniwill-laptop";
    rev = "5a24248f6422a0b673a47cbfd65e19a98eb4c8a9";
    hash = "sha256-KTxlcOgOWq4l2azQcyNwxDNWkW/k8X743iXg0JfQMJQ=";
  };

  nativeBuildInputs = kernel.moduleBuildDependencies;

  # Il Makefile del repo passa da `uname -r`, che in sandbox punta al kernel
  # sbagliato: invochiamo kbuild direttamente sull'albero del kernel target.
  buildPhase = ''
    runHook preBuild
    make -C ${kernel.dev}/lib/modules/${kernel.modDirVersion}/build \
      M=$(pwd) modules
    runHook postBuild
  '';

  installPhase = ''
    runHook preInstall
    install -Dm444 uniwill-laptop.ko \
      -t $out/lib/modules/${kernel.modDirVersion}/kernel/drivers/platform/x86
    runHook postInstall
  '';

  meta = {
    description = "Linux driver for Uniwill/TongFang laptops (charging profiles, fan and lightbar control)";
    homepage = "https://github.com/Wer-Wolf/uniwill-laptop";
    license = lib.licenses.gpl2Only;
    platforms = lib.platforms.linux;
    broken = kernel.kernelOlder "7.2";
  };
}
