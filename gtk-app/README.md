# Kindle Series Manager GTK App

Native GTK2 application for Kindle, targeting both `kindlepw2` (soft-float, FW <5.16.3) and `kindlehf` (hard-float, FW >=5.16.3).

## Prerequisites (WSL2)

```sh
# Toolchain dependencies
sudo apt-get install build-essential autoconf automake bison flex gawk libtool libtool-bin libncurses-dev curl file git gperf help2man texinfo unzip wget

# SDK dependencies
sudo apt-get install curl sed libarchive-dev nettle-dev

# Meson and GTK2 (for local testing)
sudo apt-get install meson gtk2.0 libgtk2.0-dev
```

## Building the Toolchains

```sh
# Clone koxtoolchain
git clone --recursive --depth=1 https://github.com/koreader/koxtoolchain.git
cd koxtoolchain
chmod +x ./gen-tc.sh

# Build for PW2+ (soft-float, FW <5.16.3)
./gen-tc.sh kindlepw2

# Build for hard-float (FW >=5.16.3)
./gen-tc.sh kindlehf
```

Toolchains install to `~/x-tools/`.

## Setting up the SDK

```sh
git clone --recursive --depth=1 https://github.com/KindleModding/kindle-sdk.git
cd kindle-sdk
chmod +x ./gen-sdk.sh

# Install for both targets
./gen-sdk.sh kindlepw2
./gen-sdk.sh kindlehf
```

Note the `meson-crosscompile.txt` paths returned for each target.

## Building

### Local (for testing on your PC)

```sh
meson setup builddir
meson compile -C builddir
```

### Cross-compile for Kindle PW2+ (soft-float)

```sh
meson setup --cross-file <path-to-kindlepw2-meson-crosscompile.txt> builddir_kindlepw2
meson compile -C builddir_kindlepw2
```

### Cross-compile for Kindle HF (hard-float)

```sh
meson setup --cross-file <path-to-kindlehf-meson-crosscompile.txt> builddir_kindlehf
meson compile -C builddir_kindlehf
```

## Deploying to Kindle

Copy the compiled binary to the Kindle and run it. The window title string `L:A_N:application_ID:org.mlapaglia.kindle-series-manager_PC:T` tells the Kindle window manager to treat it as a full application window.
