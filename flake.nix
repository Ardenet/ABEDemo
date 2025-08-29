{
  description = "A Nix-flake-based Python development environment";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = {nixpkgs, ...}@inputs:
    let
      supportedSystems = [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin" ];
      forEachSupportedSystem = f: nixpkgs.lib.genAttrs supportedSystems (system: f {
        pkgs = import nixpkgs { inherit system; };
      });

      /*
       * Change this value ({major}.{min}) to
       * update the Python virtual-environment
       * version. When you do this, make sure
       * to delete the `.venv` directory to
       * have the hook rebuild it for the new
       * version, since it won't overwrite an
       * existing one. After this, reload the
       * development shell to rebuild it.
       * You'll see a warning asking you to
       * do this when version mismatches are
       * present. For safety, removal should
       * be a manual step, even if trivial.
       */
      version = "3.10";
    in
    {
      packages = forEachSupportedSystem ({ pkgs }: rec {
        pbc-0514 = pkgs.callPackage ./deps/pbc-0.5.14.nix {};
        charm = pkgs.callPackage ./deps/charm.nix { inherit pbc-0514; };
      });
      devShells = forEachSupportedSystem ({ pkgs }:
        let
          concatMajorMinor = v:
            pkgs.lib.pipe v [
              pkgs.lib.versions.splitVersion
              (pkgs.lib.sublist 0 2)
              pkgs.lib.concatStrings
            ];

          python = pkgs."python${concatMajorMinor version}";
          pbc-0514 = pkgs.callPackage ./deps/pbc-0.5.14.nix {};
          charm-crypto = pkgs.callPackage ./deps/charm.nix { inherit pbc-0514; };
        in
        {
          default = pkgs.mkShell {
            venvDir = ".venv";

            postShellHook = ''
              venvVersionWarn() {
              	local venvVersion
              	venvVersion="$("$venvDir/bin/python" -c 'import platform; print(platform.python_version())')"
                echo "postShellHook run"

              	[[ "$venvVersion" == "${python.version}" ]] && return

              	cat <<EOF
              Warning: Python version mismatch: [$venvVersion (venv)] != [${python.version}]
                       Delete '$venvDir' and reload to rebuild for version ${python.version}
              EOF
              }

              "$venvDir/bin/python" -m pip install ${charm-crypto}/charm_crypto*.whl > /dev/null
            '';

            packages = with python.pkgs; [
              venvShellHook
              pip
              charm-crypto

              /* Add whatever else you'd like here. */
              # pkgs.basedpyright

              # pkgs.black
              /* or */
              # python.pkgs.black

              # pkgs.ruff
              /* or */
              # python.pkgs.ruff
            ];
          };
        });
    };
}
