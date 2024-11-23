import subprocess
from .config import (
    cfg,
    logging,
)


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


def copy_skel_to_users() -> None:
    """
    Copies the contents of the skeleton directory to non-root users' home directories.

    Parameters
    ----------
    None

    Returns
    -------
    Nothing
    """
    non_root_users = []

    try:
        with open(cfg["install_dir"] + "/etc/passwd", "r") as passwd_file:
            lines = passwd_file.readlines()

        for line in lines:
            parts = line.split(":")
            username = parts[0]
            uid = int(parts[2])

            if (
                uid != 0 and uid > 1000 and uid < 2000
            ):  # Check if the user ID is not root (UID 0)
                non_root_users.append(username)

    except FileNotFoundError:
        print("Error: No passwd file not found.")

    for user in non_root_users:
        logging.info("Copying skel to " + user)
        subprocess.run(["mkdir", "-p", cfg["install_dir"] + "/home/" + user])
        subprocess.run(
            "cp -r "
            + cfg["install_dir"]
            + "/etc/skel/. "
            + cfg["install_dir"]
            + "/home/"
            + user,
            shell=True,
        )


def fixperms() -> None:
    """
    Fix the permissions of the specified target file or directory.

    Parameters
    ----------
        target (str): The path to the target file or directory.

    Raises
    ------
        OSError: If the target file or directory is out of bounds.

    Returns
    -------
    Nothing

    """
    realtarget = realpath(cfg["install_dir"])
    for i in cfg["perms"].keys():
        if realpath(realtarget + i) != realtarget + (i if not i[-1] == "/" else i[:-1]):
            raise OSError("Out of bounds permission fix!")
        if i[-1] == "/":
            subprocess.run(
                [
                    "chown",
                    "-Rh",
                    "--",
                    cfg["perms"][i][0] + ":" + cfg["perms"][i][1],
                    realtarget + i,
                ]
            )
        else:
            subprocess.run(
                [
                    "chown",
                    "-hv",
                    "--",
                    cfg["perms"][i][0] + ":" + cfg["perms"][i][1],
                    realtarget + i,
                ]
            )
        subprocess.run(["chmod", "--", cfg["perms"][i][2], realtarget + i])


def run_chroot_cmd(work_dir: str, cmd: list) -> None:
    """
    Run a command inside a chroot environment.

    Parameters
    ----------
        work_dir (str): The path to the chroot environment.
        cmd (list): The command to be executed inside the chroot environment.

    Returns
    -------
    Nothing
    """
    subprocess.run(["arch-chroot", work_dir] + cmd)


def compressimage(ff: bool = False) -> None:
    """
    Compresses the image file using the xz compression algorithm.

    Parameters
    ----------
        ff (bool, optional): Flag indicating whether to use fast compression. Defaults to False.

    Returns
    -------
    Nothing
    """
    logging.info("Compressing " + cfg["img_name"] + ".img")
    subprocess.run(
        [
            "xz",
            "-k",
            "-5" if not ff else "-1",
            "-T0",
            "--verbose",
            "-f",
            "-M",
            "65%",
            cfg["work_dir"] + "/" + cfg["img_name"] + ".img",
        ]
    )
    # Move the image to the correct output directory
    subprocess.run(
        [
            "mv",
            cfg["work_dir"] + "/" + cfg["img_name"] + ".img.xz",
            cfg["out_dir"] + "/" + cfg["img_name"] + ".img.xz",
        ]
    )
    subprocess.run(["chmod", "-R", "777", cfg["out_dir"]])
    logging.info("Compressed " + cfg["img_name"] + ".img")


def copyimage() -> None:
    """
    Copies the image file to the output directory.

    This function moves the image file from the working directory to the output directory.
    It also sets the appropriate permissions for the output directory.

    Parameters
    ----------
    None

    Returns
    -------
    Nothing
    """
    logging.info("Copying " + cfg["img_name"] + ".img")
    # Move the image to the correct output directory
    subprocess.run(
        [
            "cp",
            cfg["work_dir"] + "/" + cfg["img_name"] + ".img",
            cfg["out_dir"] + "/" + cfg["img_name"] + ".img",
        ]
    )
    subprocess.run(["chmod", "-R", "777", cfg["out_dir"]])
    logging.info("Copied " + cfg["img_name"] + ".img")


def copyfiles(ot: str, to: str, retainperms=False) -> None:
    """
    Copy files from one directory to another.

    Parameters
    ----------
        ot (str): The source directory path.
        to (str): The destination directory path.
        retainperms (bool, optional): Whether to retain the permissions of the copied files. Defaults to False.

    Returns
    -------
    Nothing
    """
    logging.info("Copying files to " + to)
    if retainperms:
        subprocess.run(f"rsync -ah --progress --exclude=proc/* {ot}/ {to}/", shell=True)
    else:
        subprocess.run("cp -ar " + ot + "/* " + to, shell=True)


def remove_machine_id() -> None:
    """
    Removes the machine ID file from the installation directory.

    Parameters
    ----------
    None

    Returns
    -------
    Nothing
    """
    subprocess.run(
        " ".join(
            [
                "rm",
                "-rf",
                cfg["install_dir"] + "/etc/machine-id",
                cfg["install_dir"] + "/var/lib/dbus/machine-id",
            ]
        ),
        shell=True,
    )


def unmount(ldev: str, ldev_alt: str = None) -> None:  # type: ignore
    """
    Unmounts a device and releases loop devices.

    Parameters
    ----------
        ldev (str): The device to unmount.
        ldev_alt (str, optional): An alternative device to unmount. Defaults to None.

    Returns
    -------
    Nothing
    """
    logging.info("Unmounting!")
    subprocess.run(["umount", "-R", cfg["mnt_dir"]])
    subprocess.run(["losetup", "-d", ldev])
    if ldev_alt is not None:
        subprocess.run(["losetup", "-d", ldev_alt])


def get_size(path: str) -> int:
    """
    Get the size of a file or directory.

    Parameters
    ----------
        path (str): The path to the file or directory.

    Returns
    -------
    int: The size of the file or directory in kilobytes.
    """
    return int(
        subprocess.check_output(["du", "-s", "--exclude=proc", path])
        .split()[0]
        .decode("utf-8")
    )


def next_loop() -> str:
    """
    Returns the next available loop device.

    Parameters
    ----------
    None

    Returns
    -------
        str: The next available loop device.
    """

    return subprocess.check_output(["losetup", "-f"]).decode("utf-8").strip("\n")
