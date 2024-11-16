import subprocess
from .config import logging, cfg
from os import uname


def pacstrap_packages() -> None:
    """
    Install packages using pacstrap.

    This function installs packages using the pacstrap command. It takes no arguments and returns nothing.

    Parameters
    ----------
    None

    Returns
    -------
    Nothing
    """
    logging.info("Install dir is:" + cfg["install_dir"])
    if cfg["install_dir"] is None:
        logging.error("Install directory not set")
        exit(1)
    subprocess.run(
        [
            "pacstrap"
            + " -c"
            + " -C "
            + cfg["pacman_conf"]
            + " -M"
            + " -G "
            + cfg["install_dir"]
            + " "
            + " ".join(cfg["packages"]),
        ],
        check=True,
        shell=True,
    )
    logging.info("Pacstrap complete")


def debstrap_packages() -> None:
    """
    Install packages using mmdebstrap.

    This function installs packages using the mmdebstrap command. It takes no arguments and returns nothing.

    Parameters
    ----------
    None

    Returns
    -------
    Nothing
    """

    logging.info("Install dir is:" + cfg["install_dir"])
    if cfg["install_dir"] is None:
        logging.error("Install directory not set")
        exit(1)

    subprocess.run(
        [
            "mmdebstrap"
            + " --arch="
            + cfg["arch"]
            + " --include="
            + ",".join(cfg["packages"])
            + ' --components="'
            + " ".join(cfg["components"])
            + '"'
            + f" --customize-hook='{cfg["config_dir"] + "/customize.sh" + " " + cfg["install_dir"]}'"
            + " --verbose "
            + cfg["suite"]
            + " "
            + cfg["install_dir"]
            + " "
            + cfg["mirror"],
        ],
        check=True,
        shell=True,
    )
    logging.info("Debstrap complete")
