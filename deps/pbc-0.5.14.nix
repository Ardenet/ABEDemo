{ stdenv, fetchzip, flex, bison, gmp }: stdenv.mkDerivation {
  pname = "pbc";
  version = "0.5.14";

  src = fetchzip {
    url = "https://crypto.stanford.edu/pbc/files/pbc-0.5.14.tar.gz";
    sha256 = "sha256-Uy0sg6xlHXMZD3KEzBQU5pt5gKOcN0H6Kx/DV2exomA=";
  };
  buildInputs = [ flex bison gmp ];
}
