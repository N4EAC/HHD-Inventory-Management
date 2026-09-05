#!/usr/bin/env bash
set -Eeuo pipefail

# Native Linux package builder. Run on the oldest Linux release you intend to
# support because PyInstaller bundles native libraries from the build host.
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
cd "$ROOT"
APP_VERSION="1.5.8"
PKG="hhd-inventory-manager"
# Keep the executable basename identical to the freedesktop desktop-file ID.
# GNOME uses this as a fallback when matching a running window to its launcher.
EXE="$PKG"
PYTHON_BIN="${PYTHON_BIN:-python3}"
FORMAT=auto
INSTALL_DEPS=1
ASSUME_YES=0
RUN_TESTS=1

usage() { cat <<'EOF'
Usage: ./build.linux.sh [options]
  --format auto|deb|rpm|arch|tar  Override detected package format
  --python PATH                   Python executable (default: python3)
  --no-install                    Do not install system prerequisites
  --yes                           Noninteractive package-manager confirmation
  --skip-tests                    Skip tests (not recommended)
  -h, --help                      Show help

Outputs are written to dist/linux. A portable tar.gz is always created.
EOF
}
log() { printf '\n==> %s\n' "$*"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
have() { command -v "$1" >/dev/null 2>&1; }

while (($#)); do case "$1" in
  --format) [[ $# -gt 1 ]] || die "--format needs a value"; FORMAT="$2"; shift 2;;
  --python) [[ $# -gt 1 ]] || die "--python needs a value"; PYTHON_BIN="$2"; shift 2;;
  --no-install) INSTALL_DEPS=0; shift;;
  --yes) ASSUME_YES=1; shift;;
  --skip-tests) RUN_TESTS=0; shift;;
  -h|--help) usage; exit 0;;
  *) die "Unknown option: $1";;
esac; done
case "$FORMAT" in auto|deb|rpm|arch|tar) ;; *) die "Invalid format: $FORMAT";; esac
[[ "$(uname -s)" == Linux ]] || die "This builder must run on Linux."

ID=unknown; ID_LIKE=""; PRETTY_NAME=Linux
if [[ -r /etc/os-release ]]; then
  # shellcheck disable=SC1091
  source /etc/os-release
fi
DISTRO_ID="${ID:-unknown}"; DISTRO_LIKE="${ID_LIKE:-}"; DISTRO_NAME="${PRETTY_NAME:-Linux}"
ARCH="$(uname -m)"
case "$ARCH" in
  x86_64|amd64) DEB_ARCH=amd64; RPM_ARCH=x86_64; ARCH_ARCH=x86_64;;
  aarch64|arm64) DEB_ARCH=arm64; RPM_ARCH=aarch64; ARCH_ARCH=aarch64;;
  armv7*) DEB_ARCH=armhf; RPM_ARCH=armv7hl; ARCH_ARCH=armv7h;;
  i?86) DEB_ARCH=i386; RPM_ARCH=i686; ARCH_ARCH=i686;;
  *) DEB_ARCH="$ARCH"; RPM_ARCH="$ARCH"; ARCH_ARCH="$ARCH";;
esac

if have apt-get; then PM=apt
elif have dnf; then PM=dnf
elif have yum; then PM=yum
elif have zypper; then PM=zypper
elif have pacman; then PM=pacman
elif have apk; then PM=apk
elif have xbps-install; then PM=xbps
else PM=none; fi

if [[ "$FORMAT" == auto ]]; then
  case " $DISTRO_ID $DISTRO_LIKE " in
    *" debian "*|*" ubuntu "*) FORMAT=deb;;
    *" fedora "*|*" rhel "*|*" centos "*|*" suse "*|*" rocky "*|*" alma "*) FORMAT=rpm;;
    *" arch "*|*" manjaro "*|*" endeavouros "*) FORMAT=arch;;
    *) FORMAT=tar;;
  esac
fi
log "Detected $DISTRO_NAME ($DISTRO_ID), $ARCH; package manager=$PM, format=$FORMAT"

root_run() {
  if [[ ${EUID:-$(id -u)} -eq 0 ]]; then "$@"
  elif have sudo; then sudo "$@"
  elif have doas; then doas "$@"
  else die "Root access requires sudo or doas."; fi
}

install_deps() {
  [[ $INSTALL_DEPS -eq 1 ]] || return 0
  log "Installing/confirming build prerequisites"
  case "$PM" in
    apt) root_run apt-get update; f=(); [[ $ASSUME_YES -eq 1 ]] && f=(-y); root_run apt-get install "${f[@]}" python3 python3-venv python3-pip python3-tk build-essential binutils patchelf fakeroot dpkg-dev file;;
    dnf|yum) f=(); [[ $ASSUME_YES -eq 1 ]] && f=(-y); root_run "$PM" install "${f[@]}" python3 python3-pip python3-tkinter gcc make binutils patchelf rpm-build file;;
    zypper) f=(); [[ $ASSUME_YES -eq 1 ]] && f=(--non-interactive); root_run zypper "${f[@]}" install python3 python3-pip python3-tk gcc make binutils patchelf rpm-build file;;
    pacman) f=(--needed); [[ $ASSUME_YES -eq 1 ]] && f+=(--noconfirm); root_run pacman -Syu "${f[@]}" python python-pip tk base-devel patchelf libarchive zstd file;;
    apk) root_run apk add python3 py3-pip py3-virtualenv tk gcc musl-dev python3-dev binutils patchelf file;;
    xbps) f=(-S); [[ $ASSUME_YES -eq 1 ]] && f+=(-y); root_run xbps-install "${f[@]}" python3 python3-pip python3-tkinter base-devel patchelf file;;
    none) die "No supported package manager. Install Python 3, venv, Tk, compiler, binutils, patchelf and packaging tools; rerun with --no-install.";;
  esac
}
install_deps
have "$PYTHON_BIN" || die "Python not found: $PYTHON_BIN"
"$PYTHON_BIN" -c 'import sys; assert sys.version_info >= (3,9)' || die "Python 3.9+ required"
"$PYTHON_BIN" -c 'import tkinter' || die "Tkinter missing for $PYTHON_BIN"
case "$FORMAT" in
  deb) have dpkg-deb || die "dpkg-deb missing";;
  rpm) have rpmbuild || die "rpmbuild missing";;
  arch) have bsdtar && have zstd || die "bsdtar and zstd required";;
esac

SOURCE_VERSION="$($PYTHON_BIN -c 'import hhd_inventory_manager as a; print(a.APP_VERSION)')"
[[ "$SOURCE_VERSION" == "$APP_VERSION" ]] || die "Version mismatch: script=$APP_VERSION source=$SOURCE_VERSION"
BUILD="$ROOT/build/linux"; DIST="$ROOT/dist/linux"; STAGE="$BUILD/root"
[[ "$BUILD" == "$ROOT/build/linux" && "$DIST" == "$ROOT/dist/linux" ]] || die "Unsafe paths"
rm -rf -- "$BUILD"; mkdir -p "$BUILD" "$DIST"

log "Creating isolated build environment"
"$PYTHON_BIN" -m venv "$BUILD/venv"
VPY="$BUILD/venv/bin/python"
"$VPY" -m pip install --upgrade pip setuptools wheel pyinstaller pillow
if [[ $RUN_TESTS -eq 1 ]]; then
  "$VPY" -m py_compile hhd_inventory_manager.py
  "$VPY" -m unittest discover -s tests -p 'test_*.py' -v
fi

log "Building application"
"$VPY" -m PyInstaller --noconfirm --clean --windowed --name "$EXE" \
  --specpath "$BUILD" --workpath "$BUILD/pyinstaller" --distpath "$BUILD/app" \
  --add-data "$ROOT/hhd_inventory_manager.png:." \
  --add-data "$ROOT/hhd_inventory_manager_about.png:." \
  --add-data "$ROOT/hhd_menu_icon.png:." "$ROOT/hhd_inventory_manager.py"
APP="$BUILD/app/$EXE"; [[ -x "$APP/$EXE" ]] || die "Incomplete PyInstaller output"

log "Creating freedesktop payload"
install -d "$STAGE/opt/$PKG" "$STAGE/usr/bin" "$STAGE/usr/share/applications" \
  "$STAGE/usr/share/doc/$PKG" "$STAGE/usr/share/pixmaps"
cp -a "$APP/." "$STAGE/opt/$PKG/"
install -m644 "$ROOT/hhd_inventory_manager.png" "$STAGE/usr/share/pixmaps/$PKG.png"
for size in 16 32 48 64 128 256 512; do
  icon_dir="$STAGE/usr/share/icons/hicolor/${size}x${size}/apps"
  install -d "$icon_dir"
  "$VPY" -c 'from PIL import Image; import sys; Image.open(sys.argv[1]).resize((int(sys.argv[3]), int(sys.argv[3])), Image.Resampling.LANCZOS).save(sys.argv[2])' \
    "$ROOT/hhd_inventory_manager.png" "$icon_dir/$PKG.png" "$size"
done
install -m644 README.md LICENSE "$STAGE/usr/share/doc/$PKG/"
printf '#!/bin/sh\nexport BAMF_DESKTOP_FILE_HINT=/usr/share/applications/%s.desktop\nexec /opt/%s/%s "$@"\n' "$PKG" "$PKG" "$EXE" >"$STAGE/usr/bin/$PKG"; chmod 755 "$STAGE/usr/bin/$PKG"
cat >"$STAGE/usr/share/applications/$PKG.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=HHD Inventory Manager
Comment=Track home hemodialysis inventory and treatments
Exec=$PKG
Icon=/usr/share/pixmaps/$PKG.png
Terminal=false
Categories=Office;Utility;
StartupNotify=true
StartupWMClass=HHDInventoryManager
X-GNOME-UsesNotifications=false
EOF

PORT="$BUILD/$PKG-$APP_VERSION-$ARCH"; mkdir -p "$PORT"; cp -a "$APP/." "$PORT/"
printf '#!/bin/sh\nD=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)\nexec "$D/%s" "$@"\n' "$EXE" >"$PORT/run-hhd-inventory-manager.sh"; chmod 755 "$PORT/run-hhd-inventory-manager.sh"
tar -C "$BUILD" -czf "$DIST/$PKG-$APP_VERSION-$ARCH.tar.gz" "$(basename "$PORT")"

build_deb() {
  install -d "$STAGE/DEBIAN"; size="$(du -sk "$STAGE" | awk '{print $1}')"
  cat >"$STAGE/DEBIAN/control" <<EOF
Package: $PKG
Version: $APP_VERSION
Section: utils
Priority: optional
Architecture: $DEB_ARCH
Installed-Size: $size
Maintainer: HHD Inventory Manager Project <noreply@n4eac.com>
Depends: libc6, libx11-6, libxext6, libxrender1, libxft2, libfontconfig1
Recommends: hicolor-icon-theme, desktop-file-utils
Description: Home hemodialysis inventory and treatment manager
 Tracks supplies, treatment activity, lots and inventory history locally.
EOF
  cat >"$STAGE/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e
command -v gtk-update-icon-cache >/dev/null 2>&1 && gtk-update-icon-cache -f -t /usr/share/icons/hicolor || true
command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database /usr/share/applications || true
exit 0
EOF
  cat >"$STAGE/DEBIAN/postrm" <<'EOF'
#!/bin/sh
set -e
command -v gtk-update-icon-cache >/dev/null 2>&1 && gtk-update-icon-cache -f -t /usr/share/icons/hicolor || true
command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database /usr/share/applications || true
exit 0
EOF
  chmod 755 "$STAGE/DEBIAN/postinst" "$STAGE/DEBIAN/postrm"
  dpkg-deb --build --root-owner-group "$STAGE" "$DIST/${PKG}_${APP_VERSION}_${DEB_ARCH}.deb"
}
build_rpm() {
  top="$BUILD/rpmbuild"; mkdir -p "$top"/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS}; cp -a "$STAGE" "$top/SOURCES/payload"
  cat >"$top/SPECS/$PKG.spec" <<EOF
Name: $PKG
Version: $APP_VERSION
Release: 1%{?dist}
Summary: Home hemodialysis inventory and treatment manager
License: MIT
BuildArch: $RPM_ARCH
Requires: glibc, libX11, libXext, libXrender, libXft, fontconfig
%description
Tracks home hemodialysis supplies, treatments and inventory history.
%prep
%build
%install
rm -rf %{buildroot}
cp -a %{_sourcedir}/payload/. %{buildroot}/
%files
/opt/$PKG
/usr/bin/$PKG
/usr/share/applications/$PKG.desktop
/usr/share/icons/hicolor/*/apps/$PKG.png
/usr/share/pixmaps/$PKG.png
/usr/share/doc/$PKG
%post
command -v gtk-update-icon-cache >/dev/null 2>&1 && gtk-update-icon-cache -f -t /usr/share/icons/hicolor || true
command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database /usr/share/applications || true
%postun
command -v gtk-update-icon-cache >/dev/null 2>&1 && gtk-update-icon-cache -f -t /usr/share/icons/hicolor || true
command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database /usr/share/applications || true
EOF
  rpmbuild --define "_topdir $top" -bb "$top/SPECS/$PKG.spec"
  find "$top/RPMS" -type f -name '*.rpm' -exec cp -v {} "$DIST/" \;
}
build_arch() {
  cat >"$STAGE/.PKGINFO" <<EOF
pkgname = $PKG
pkgbase = $PKG
pkgver = $APP_VERSION-1
pkgdesc = Home hemodialysis inventory and treatment manager
url = https://github.com/N4EAC/HHD-Inventory-Management
builddate = $(date +%s)
packager = HHD Inventory Manager Project
size = $(du -sb "$STAGE" | awk '{print $1}')
arch = $ARCH_ARCH
license = MIT
depend = glibc
depend = libx11
depend = libxext
depend = libxrender
depend = libxft
depend = fontconfig
EOF
  (cd "$STAGE" && bsdtar --uid 0 --gid 0 -cf - .) | zstd -19 -T0 -o "$DIST/$PKG-$APP_VERSION-1-$ARCH_ARCH.pkg.tar.zst"
}
case "$FORMAT" in deb) build_deb;; rpm) build_rpm;; arch) build_arch;; tar) log "Portable package only for $DISTRO_NAME";; esac
log "Build complete"
find "$DIST" -maxdepth 1 -type f -printf '%f  %k KiB\n' | sort
