# ImageForge

ImageForge is a Python library designed for building Linux distribution images specifically for ARM devices.

## Features

- **Modular and Extensible**: ImageForge is designed to be modular and extensible. You can easily add new components to the image building process.
- **Customizable**: You can customize the image building process by providing your own configuration files.

## Contributing

### Pre-commit

This repository uses [pre-commit](https://pre-commit.com/) to ensure code quality and consistency. The primary tool used is [PSF Black](https://github.com/psf/black) for code formatting.

#### Installation

To set up pre-commit in your local environment, follow these steps:
On archlinux:
```bash
sudo pacman -S pre-commit
```

On Ubuntu:
```bash
sudo apt install pre-commit
```

Then, run the following command in the repository root directory:
```bash
pre-commit install
```

