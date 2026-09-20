#!/bin/sh
set -eu
project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
version=$(sed -n 's/^__version__ = "\([^"]*\)"/\1/p' "$project_dir/src/briscas/__init__.py")
build_dir="$project_dir/build/deb-root"
output_dir="$project_dir/dist"
rm -rf "$build_dir"
mkdir -p "$build_dir/DEBIAN" "$build_dir/usr/bin" \
  "$build_dir/usr/lib/python3/dist-packages" "$build_dir/usr/share/applications" \
  "$build_dir/usr/share/games/briscas/cards" "$build_dir/usr/share/games/briscas/sounds" \
  "$build_dir/usr/share/pixmaps" "$build_dir/usr/share/doc/briscas" "$output_dir"
mkdir -p "$build_dir/usr/lib/python3/dist-packages/briscas"
cp "$project_dir/src/briscas/"*.py "$build_dir/usr/lib/python3/dist-packages/briscas/"
cp "$project_dir/assets/cards/"*.png "$build_dir/usr/share/games/briscas/cards/"
cp "$project_dir/assets/sounds/"*.wav "$build_dir/usr/share/games/briscas/sounds/"
install -m 0755 "$project_dir/packaging/debian/briscas.wrapper" "$build_dir/usr/bin/briscas"
install -m 0644 "$project_dir/packaging/debian/com.ericflores.briscas.desktop" "$build_dir/usr/share/applications/"

# hicolor's own index.theme only lists these apps sizes (plus "scalable"); a size it
# doesn't list (e.g. the source image's native 1024x1024) is invisible to the standard
# icon lookup GNOME/COSMIC use for the app grid, dock, and search.
icon_src="$project_dir/assets/icons/briscas-lily.png"
for size in 16 22 24 32 36 48 64 72 96 128 192 256 512; do
  mkdir -p "$build_dir/usr/share/icons/hicolor/${size}x${size}/apps"
done
QT_QPA_PLATFORM=offscreen python3 - "$icon_src" "$build_dir/usr/share/icons/hicolor" <<'PYEOF'
import sys
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QApplication

src, hicolor_root = sys.argv[1], sys.argv[2]
app = QApplication.instance() or QApplication(["briscas-icon-resize"])
source = QPixmap(src)
for size in (16, 22, 24, 32, 36, 48, 64, 72, 96, 128, 192, 256, 512):
    scaled = source.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    scaled.save(f"{hicolor_root}/{size}x{size}/apps/com.ericflores.briscas.png")
PYEOF
# Long-standing fallback path some launchers still check directly by filename.
install -m 0644 "$icon_src" "$build_dir/usr/share/pixmaps/com.ericflores.briscas.png"

install -m 0644 "$project_dir/README.md" "$build_dir/usr/share/doc/briscas/README"
install -m 0644 "$project_dir/LICENSE" "$build_dir/usr/share/doc/briscas/LICENSE"
install -m 0644 "$project_dir/packaging/debian/copyright" "$build_dir/usr/share/doc/briscas/copyright"
installed_size=$(du -sk "$build_dir/usr" | cut -f1)
sed -e "s/@VERSION@/$version/g" -e "s/@INSTALLED_SIZE@/$installed_size/g" \
  "$project_dir/packaging/debian/control.in" > "$build_dir/DEBIAN/control"
find "$build_dir" -type d -exec chmod 0755 {} +
find "$build_dir" -type f ! -path "$build_dir/usr/bin/briscas" -exec chmod 0644 {} +
# Maintainer scripts refresh the desktop/icon caches so the menu entry and its icon
# appear immediately after install/remove, without waiting for an unrelated trigger
# or a logout. Installed after the blanket chmod above so they keep their exec bit.
install -m 0755 "$project_dir/packaging/debian/postinst" "$build_dir/DEBIAN/postinst"
install -m 0755 "$project_dir/packaging/debian/postrm" "$build_dir/DEBIAN/postrm"
dpkg-deb --root-owner-group --build "$build_dir" "$output_dir/briscas_${version}_all.deb"
sha256sum "$output_dir/briscas_${version}_all.deb" > "$output_dir/SHA256SUMS"
