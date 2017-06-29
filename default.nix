{
  pkgs ? import <nixpkgs> {},
  pythonPackages ? pkgs.python36Packages,
  forDev ? true
}:
{
  digitalMarketplaceApiEnv = pkgs.stdenv.mkDerivation {
    name = "digitalmarketplace-api-env";
    buildInputs = [
      pythonPackages.virtualenv
      pkgs.libffi
      pkgs.libyaml
      # pip requires git to fetch some of its dependencies
      pkgs.git
      # for `cryptography`
      pkgs.openssl
      # we *would* just depend on the pkgs.postgresql.lib output but pip wants to use the `pg_config` binary during the
      # install process
      pkgs.postgresql
    ] ++ pkgs.stdenv.lib.optionals forDev [
      # exotic things possibly go here
    ];

    hardeningDisable = pkgs.stdenv.lib.optionals pkgs.stdenv.isDarwin [ "format" ];

    VIRTUALENV_ROOT = "venv${pythonPackages.python.pythonVersion}";
    VIRTUAL_ENV_DISABLE_PROMPT = "1";
    SOURCE_DATE_EPOCH = "315532800";

    # if we don't have this, we get unicode troubles in a --pure nix-shell
    LANG="en_GB.UTF-8";

    shellHook = ''
      if [ ! -e $VIRTUALENV_ROOT ]; then
        ${pythonPackages.virtualenv}/bin/virtualenv $VIRTUALENV_ROOT
      fi
      source $VIRTUALENV_ROOT/bin/activate
      make requirements${pkgs.stdenv.lib.optionalString forDev "-dev"}
    '';
  };
}
