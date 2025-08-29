{ stdenv, fetchFromGitHub, gmp, pbc-0514, openssl, which, python310, python310Packages, wget }: stdenv.mkDerivation {
    pname = "charm";
    version = "v0.50";

    src = fetchFromGitHub {
        owner = "JHUISI";
        repo = "charm";
        rev = "dev";
        sha256 = "sha256-/jfDdzjDkl+AmSFRPyILKp/E5vUpr5iQfd1PUug9/Mo=";
    };
    
    buildInputs = [ gmp pbc-0514 openssl python310 wget which python310Packages.pip python310Packages.setuptools ];

    configureScript = "./configure.sh --python=${python310}/bin/python";
    installPhase = ''
      python setup.py bdist_wheel
      mkdir -p $out
      cp dist/charm_crypto*.whl $out/
    '';
}
