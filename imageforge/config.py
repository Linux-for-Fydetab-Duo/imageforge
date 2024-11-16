"""Global configuration storage for imageforge"""

import os
import argparse
import sys
import subprocess
import pathlib
import logging


def parse_args():
    parser = argparse.ArgumentParser(description="Create Images")
    parser.add_argument("-w", "--work_dir", help="Directory to work in", required=True)
    parser.add_argument(
        "-x", "--no-compress", help="Do not compress into a .xz", action="store_true"
    )
    parser.add_argument(
        "-ff", "--fast-forward", help="Compress very briefly .xz", action="store_true"
    )
    parser.add_argument(
        "-c", "--config_dir", help="Folder with config files", required=True
    )
    parser.add_argument(
        "-o", "--out_dir", help="Folder to put output files", required=True
    )
    return parser.parse_args()


def realpath(path: str) -> str:
    """
    Function to get the real path of a file or directory.

    Parameters
    ----------
    path : str
        Path of the file or directory.

    Returns
    -------
    The real path of the file or directory.
    """
    return subprocess.check_output(["readlink", "-f", path]).decode("utf-8").split()[0]


args = parse_args()
work_dir = realpath(args.work_dir)
config_dir = realpath(args.config_dir)
out_dir = realpath(args.out_dir)
LOGGING_FORMAT: str = "%(asctime)s [%(levelname)s] %(message)s (%(funcName)s)"
LOGGING_DATE_FORMAT: str = "%H:%M:%S"

logging.basicConfig(
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt=LOGGING_DATE_FORMAT,
    encoding="utf-8",
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(pathlib.Path(config_dir + "/imageforge.log"), mode="w"),
    ],
)


class Config:
    def __init__(self, params: dict):
        self.cfg = {}

        # Extract parameters from the passed dictionary
        self.cfg["arch"] = params.get("arch", None)
        self.cfg["cmdline"] = params.get("cmdline", None)
        self.cfg["configtxt"] = params.get("configtxt", None)
        self.cfg["configtxt_suffix"] = params.get("configtxt_suffix", None)
        self.cfg["edition"] = params.get("edition", None)
        self.cfg["fs"] = params.get("fs", "ext4")
        self.cfg["img_backend"] = params.get("img_backend", "loop")
        self.cfg["img_name"] = params.get("img_name", "default_img_name")
        self.cfg["img_type"] = params.get("img_type", "image")
        self.cfg["img_version"] = params.get("img_version", None)
        self.cfg["perms"] = params.get("perms", None)
        self.cfg["grubcmdl"] = params.get("grubcmdl", None)
        self.cfg["grubdtb"] = params.get("grubdtb", None)
        self.cfg["part_type"] = "gpt" if params.get("use_gpt", False) else "msdos"
        self.cfg["boot_set_esp"] = params.get("boot_set_esp", False)
        self.cfg["partition_table"] = params.get("partition_table", None)
        self.cfg["partition_table_boot"] = params.get("partition_table_boot", None)
        self.cfg["partition_table_root"] = params.get("partition_table_root", None)
        self.cfg["pacman_conf"] = params.get("pacman_conf", None)
        self.cfg["partition_suffix"] = params.get(
            "partition_suffix", lambda config_dir, disk: []
        )
        self.cfg["partition_prefix"] = params.get(
            "partition_prefix", lambda config_dir, disk: []
        )
        self.cfg["has_uefi"] = params.get("has_uefi", False)
        self.cfg["base"] = params.get("base", "arch")

        # Create directories
        self.cfg["work_dir"] = work_dir
        self.cfg["config_dir"] = config_dir
        self.cfg["out_dir"] = out_dir
        self.cfg["mnt_dir"] = os.path.join(self.cfg["work_dir"], "mnt")
        self.cfg["install_dir"] = os.path.join(self.cfg["work_dir"], self.cfg["arch"])
        for directory in [
            self.cfg["work_dir"],
            self.cfg["mnt_dir"],
            self.cfg["install_dir"],
            self.cfg["out_dir"],
        ]:
            if not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)

        packages_file = os.path.join(
            self.cfg["config_dir"], "packages." + self.cfg["arch"]
        )
        self.cfg["packages_file"] = packages_file
        if self.cfg["base"] == "arch":
            self.cfg["pacman_conf"] = os.path.join(
                self.cfg["config_dir"], "pacman.conf." + self.cfg["arch"]
            )

        self.cfg["components"] = params.get("components", None)
        self.cfg["suite"] = params.get("suite", None)
        self.cfg["mirror"] = params.get("mirror", None)

        # Validation
        self._validate()

        # Read packages
        self._read_packages(packages_file)
        global cfg
        cfg = self.cfg

    def _validate(self):
        if not self.cfg["img_name"]:
            logging.error("Image name not set")
            exit(1)
        if not self.cfg["img_version"]:
            logging.error("Image version not set")
            exit(1)
        if self.cfg["fs"] not in ["ext4", "btrfs"]:
            logging.error("Filesystem not supported use ext4 or btrfs")
            exit(1)
        if not os.path.isfile(self.cfg["packages_file"]):
            logging.error(
                "Packages file doesn't exist. Create the file packages."
                + self.cfg["arch"]
            )
            exit(1)
        if self.cfg["img_type"] not in ["image", "rootfs"]:
            logging.error("Image type not supported. Use image or rootfs")
            exit(1)
        if self.cfg["img_backend"] not in ["loop"]:
            logging.error("Image backend not supported. Use loop")
            exit(1)
        if self.cfg["base"] == "arch":
            if os.path.isfile(
                os.path.join(config_dir, "/pacman.conf.", self.cfg["arch"])
            ):
                logging.error(
                    "Pacman config file not found "
                    + os.path.join(config_dir, "/pacman.conf.", self.cfg["arch"])
                )
                exit(1)
        elif self.cfg["base"] == "debian":
            # if os.path.isfile(config_dir + '/sources.list.' + self.cfg["arch"]):
            #     logging.error("Sources list file not found")
            #     exit(1)
            pass

    def _read_packages(self, packages_file):
        with open(packages_file, "r") as f:
            packages = map(lambda package: package.strip(), f.readlines())
            packages = list(
                filter(lambda package: not package.startswith("#"), packages)
            )
            self.cfg["packages"] = packages
