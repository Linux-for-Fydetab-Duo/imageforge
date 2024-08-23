import subprocess
from .config import logging, cfg


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
