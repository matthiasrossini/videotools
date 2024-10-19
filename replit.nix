{pkgs}: {
  deps = [
    pkgs.ffmpeg
    pkgs.libGLU
    pkgs.libGL
    pkgs.postgresql
    pkgs.openssl
  ];
}