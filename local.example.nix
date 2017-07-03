# default.nix calls out to the file local.nix if it exists, expecting a function which it will call, applying first
# the args passed to the original default.nix and then `oldAttrs`, the attrset originally applied to mkDerivation.
#
# the function should return an attrset altered to the local user's desires, as they would wish to be applied to
# mkDerivation to produce the env

args: oldAttrs: oldAttrs // {
  # here we add some of our favourite packages to the environment which aren't necessarily to everyone's tastes
  buildInputs = oldAttrs.buildInputs ++ [
    args.pkgs.vim
    args.pythonPackages.ipython
  ];

  shellHook =  oldAttrs.shellHook + ''
    # PS1 can't be set as a normal derivation attr as it gets clobbered early on in the upstream shellHook script
    export PS1="⚡$PS1⚡"

    # inject some whimsy into our session - note here we access a package which we don't actually end up
    # explicitly exposing to the final environment
    ${args.pkgs.fortune}/bin/fortune
  '';
}
