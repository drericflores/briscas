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
  "$build_dir/usr/share/icons/hicolor/1024x1024/apps" "$build_dir/usr/share/doc/briscas" "$output_dir"
mkdir -p "$build_dir/usr/lib/python3/dist-packages/briscas"
cp "$project_dir/src/briscas/"*.py "$build_dir/usr/lib/python3/dist-packages/briscas/"
cp "$project_dir/assets/cards/"*.png "$build_dir/usr/share/games/briscas/cards/"
cp "$project_dir/assets/sounds/"*.wav "$build_dir/usr/share/games/briscas/sounds/"
install -m 0755 "$project_dir/packaging/debian/briscas.wrapper" "$build_dir/usr/bin/briscas"
install -m 0644 "$project_dir/packaging/debian/com.ericflores.briscas.desktop" "$build_dir/usr/share/applications/"
install -m 0644 "$project_dir/assets/icons/briscas-lily.png" \
  "$build_dir/usr/share/icons/hicolor/1024x1024/apps/com.ericflores.briscas.png"
install -m 0644 "$project_dir/README.md" "$build_dir/usr/share/doc/briscas/README"
installed_size=$(du -sk "$build_dir/usr" | cut -f1)
sed -e "s/@VERSION@/$version/g" -e "s/@INSTALLED_SIZE@/$installed_size/g" \
  "$project_dir/packaging/debian/control.in" > "$build_dir/DEBIAN/control"
find "$build_dir" -type d -exec chmod 0755 {} +
find "$build_dir" -type f ! -path "$build_dir/usr/bin/briscas" -exec chmod 0644 {} +
dpkg-deb --root-owner-group --build "$build_dir" "$output_dir/briscas_${version}_all.deb"
sha256sum "$output_dir/briscas_${version}_all.deb" > "$output_dir/SHA256SUMS"
