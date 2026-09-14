{
  config,
  pkgs,
  ...
}: let
  uniwill-laptop = config.boot.kernelPackages.callPackage ../pkgs/uniwill-laptop.nix {};

  # setta il refresh del pannello interno: refresh-rate [165|40|auto]
  # (il BOE supporta solo questi due mode; "auto" sceglie in base
  # all'alimentazione). Funziona sia da utente che da root (udev).
  refresh-rate = pkgs.writeShellApplication {
    name = "refresh-rate";
    runtimeInputs = [
      config.programs.hyprland.package
      pkgs.util-linux
      pkgs.coreutils
    ];
    text = ''
      rate="''${1:-auto}"
      if [ "$rate" = auto ]; then
        if [ "$(cat /sys/class/power_supply/AC0/online)" = 1 ]; then
          rate=165
        else
          rate=40
        fi
      fi
      for sock in /run/user/*/hypr/*/.socket.sock; do
        [ -e "$sock" ] || continue
        rundir="''${sock%/hypr/*}"
        sig="''${sock#*/hypr/}"
        sig="''${sig%%/*}"
        # config Lua: "hyprctl keyword" non è supportato, serve eval
        cmd=(env "XDG_RUNTIME_DIR=$rundir" "HYPRLAND_INSTANCE_SIGNATURE=$sig" \
          hyprctl eval "hl.monitor({output = \"desc:BOE 0x0974\", mode = \"2560x1440@$rate.0\", position = \"1920x0\", scale = 1.6})")
        if [ "$(id -u)" = 0 ]; then
          runuser -u "$(stat -c %U "$rundir")" -- "''${cmd[@]}"
        else
          "''${cmd[@]}"
        fi
      done
    '';
  };
in {
  environment.systemPackages = [refresh-rate];

  # al cambio di alimentazione adegua il refresh (165 su AC, 40 a batteria)
  services.udev.extraRules = ''
    SUBSYSTEM=="power_supply", ATTR{type}=="Mains", RUN+="${refresh-rate}/bin/refresh-rate auto"
  '';

  # risparmio energetico aggressivo a batteria (TLP è già abilitato da
  # nixos-hardware common-pc-laptop, qui solo le impostazioni)
  services.tlp.settings = {
    # EPP al minimo consumo invece del default balance_power
    CPU_ENERGY_PERF_POLICY_ON_BAT = "power";

    # niente turbo boost a batteria: sul i7-10875H è il singolo
    # risparmio più grande, al costo di picchi di CPU più lenti
    CPU_BOOST_ON_BAT = 0;
    CPU_HWP_DYN_BOOST_ON_BAT = 0;

    # runtime PM per tutti i dispositivi PCIe e powersave wifi
    RUNTIME_PM_ON_BAT = "auto";
    WIFI_PWR_ON_BAT = "on";

    # NON sospendere via USB il controller Bluetooth: l'autosuspend del
    # combo Intel (8087:0026) dopo ~2s di idle causa il "firmware bug"
    # (missing completion reports) → il transport A2DP cade e le cuffie
    # si spengono da sole. Escluso da TLP, power/control resta "on".
    USB_EXCLUDE_BTUSB = 1;

    # ASPM aggressivo sui link PCIe a batteria
    PCIE_ASPM_ON_BAT = "powersupersave";

    # powersave audio dopo 1 secondo di inattività
    SOUND_POWER_SAVE_ON_BAT = 1;

    # limita la iGPU a batteria (range hardware: 350-1200 MHz)
    INTEL_GPU_MAX_FREQ_ON_BAT = 800;
    INTEL_GPU_BOOST_FREQ_ON_BAT = 800;
  };

  # --- profilo di ricarica della batteria -----------------------------------
  #
  # La scheda non è nella tabella DMI del driver (quella elenca solo modelli
  # TUXEDO/Schenker/Intel NUC), quindi serve force=1. force abilita tutte le
  # feature TRANNE la soglia numerica charge_control_end_threshold, che viene
  # mascherata apposta per non danneggiare la batteria su schede non validate.
  # Non è una perdita: il registro della soglia (EC 0x07B9) su questo firmware
  # non è nemmeno mappato in ACPI, la field list di ECMG salta esattamente
  # quel byte. Resta l'interfaccia a profili, che è quella giusta per i GM7.
  boot.extraModulePackages = [uniwill-laptop];
  boot.extraModprobeConfig = "options uniwill-laptop force=1";

  # Niente autoload: gli alias DMI del modulo non coprono questa scheda.
  boot.kernelModules = ["uniwill-laptop"];

  # ATTENZIONE ai nomi, sono controintuitivi. La mappatura driver → EC è:
  #   Standard    → HIGH_CAPACITY (100%)
  #   Long Life   → BALANCED      (~90%)
  #   Trickle     → STATIONARY    (~80%, e carica anche più lenta)
  # Quindi il profilo "stationary" da scrivere è "Trickle", NON "Long Life".
  systemd.services.battery-charge-profile = {
    description = "Battery charging profile (Uniwill EC) → stationary";
    wantedBy = ["multi-user.target"];
    after = ["systemd-modules-load.service"];

    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = true;
    };

    script = ''
      attr=/sys/class/power_supply/BAT0/charge_types

      # il battery hook del driver si registra poco dopo il probe
      for _ in $(seq 20); do
        [ -e "$attr" ] && break
        sleep 0.25
      done

      if [ ! -e "$attr" ]; then
        echo "$attr assente: il driver non ha esposto i profili di ricarica" >&2
        exit 1
      fi

      echo Trickle > "$attr"

      # l'EC può accettare la scrittura e ignorarla: rileggiamo per sapere
      # se il profilo è davvero attivo (l'attivo è quello fra parentesi)
      if ! grep -q '\[Trickle\]' "$attr"; then
        echo "profilo non applicato, l'EC riporta: $(cat "$attr")" >&2
        exit 1
      fi
    '';
  };
}
