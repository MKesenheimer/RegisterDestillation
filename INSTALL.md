# RegisterDestillation Installation Guide

## Prerequisites

- **Python 3.8+** with pip
- **CMake 3.16+** for building the debugprobe
- **picotool** (Raspberry Pi Pico utility)
- **git** with submodule support

## Quick Setup

### 1. Clone Repository

```bash
git clone --recursive <todo-repo-url>
cd RegisterDestillation
```

The `--recursive` flag ensures the `debugprobe` library submodule is also cloned.

### 2. Install Python Dependencies

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install findus
```

### 3. Build and Load debugprobe

```bash
# Clone Pico SDK if not present
cd <your-sdks-path>
git clone --recursive https://github.com/raspberrypi/pico-sdk.git
```

Add to your shell configuration (`~/.bashrc` or `~/.zshrc`):

```bash
export PICO_SDK_PATH='<your-sdks-path>/pico-sdk'
export PATH="$PICO_SDK_PATH:$PATH"
```

```bash
# Install picotool (Arch Linux example)
yay -Sy picotool

# Build the debug firmware
cd debugprobe
mkdir build && cd build
cmake ..
make
picotool load debugprobe.bin
```

### 4. Build and install openocd

```bash
cd openocd
./bootstrap
./configure
make && sudo make install
```

## Additional Resources

- **[README.md](./README.md)** - Overview and usage examples
- **[DETAILS.md](./DETAILS.md)** - Technical deep dive into the attack methodology
