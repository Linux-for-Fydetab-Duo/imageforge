"""Partitioning module for imageforge."""

import subprocess
import os
from .common import run_chroot_cmd
from .config import (
    cfg,
    logging,
)


def get_fsline(partition: str) -> str:  # type: ignore
    """
    Function to get the UUID of a partition.

    Parameters
    ----------

    partition : str
        Path of the partition.

    Returns
    -------
    The UUID of the partition.
    """
    fl = subprocess.check_output(["blkid", partition]).decode("utf-8")
    spl = fl.split(" ")
    for i in spl:
        if i.startswith("UUID="):
            return str(i.replace('"', ""))


def get_parttype(partition: str) -> str:  # type: ignore
    """
    Function to get the filesystem of a partition.

    Parameters
    ----------

    partition : str
        Path of the partition.

    Returns
    -------
    The filesystem of the partition.
    """
    fl = subprocess.check_output(["blkid", partition]).decode("utf-8")
    spl = fl.split(" ")
    for i in spl:
        if i.startswith("TYPE="):
            return i[6:-1]


def makeimg(img_size: int, ldev: str) -> None:
    """
    Function to create an image file and attach it to a loop device.

    Parameters
    ----------

    img_size : int
        Size of the image file in kilobytes.
    img_name : str
        Name of the image file.
    ldev : str
        Loop device to attach the image file to.

    Returns
    -------
    Nothing
    """
    logging.info("Creating image file " + cfg["img_name"] + ".img")
    subprocess.run(
        [
            "fallocate",
            "-l",
            str(img_size) + "K",
            cfg["work_dir"] + "/" + cfg["img_name"] + ".img",
        ]
    )

    subprocess.run(["modprobe", "loop"])
    logging.info(
        "Attaching image file " + cfg["img_name"] + ".img to loop device " + ldev
    )
    subprocess.run(["losetup", ldev, cfg["work_dir"] + "/" + cfg["img_name"] + ".img"])

    logging.info("Image file created")


def partition(disk: str, img_size: int, split: bool = False) -> None:
    """
    Partition the specified disk.

    Parameters
    ----------
        disk (str): The path of the disk to be partitioned.
        split (bool, optional): Whether to split the partition. Defaults to False.
    Returns
    -------
    """
    # Rest of the code...
    table = [["Partition", "Start", "End", "Size", "Filesystem"]]
    if cfg["has_uefi"]:
        prtd_cmd = [
            "parted",
            "--script",
            disk,
            "--align",
            "optimal",
        ]
    else:
        prtd_cmd = [
            "parted",
            "--script",
            disk,
            "--align",
            "optimal",
            "mklabel",
            cfg["part_type"],
        ]
    ld_partition_table = cfg["partition_table"](img_size, cfg["fs"])

    for i in ld_partition_table.keys():
        if ld_partition_table[i][3] == "fat32":
            if cfg["has_uefi"]:
                part_num = str(2)
            else:
                part_num = str(1)
            prtd_cmd += [
                "mkpart",
                "primary",
                "fat32",
                ld_partition_table[i][0],
                ld_partition_table[i][1],
                "set",
                part_num,
                "boot",
                "on",
            ]
            if cfg["boot_set_esp"]:
                prtd_cmd += ["set", part_num, "esp", "on"]
        elif ld_partition_table[i][3] == "NONE":
            pass
        else:
            prtd_cmd += [
                "mkpart",
                "primary",
                ld_partition_table[i][3],
                ld_partition_table[i][0],
                ld_partition_table[i][1],
            ]

    if not split:
        for i in cfg["partition_prefix"](cfg["config_dir"], disk):
            subprocess.run(i)

    logging.info(f"Full command: {prtd_cmd}")
    subprocess.run(prtd_cmd)

    if not split:
        for i in cfg["partition_suffix"](cfg["config_dir"], disk):
            subprocess.run(i)

    if not os.path.exists(cfg["mnt_dir"]):
        os.mkdir(cfg["mnt_dir"])

    idf = "p3" if cfg["has_uefi"] else ("p2" if not split else "p1")

    if cfg["fs"] == "ext4":
        subprocess.run("mkfs.ext4 -F -L PRIMARY " + disk + idf, shell=True)
        subprocess.run("mount " + disk + idf + " " + cfg["mnt_dir"], shell=True)
        os.mkdir(cfg["mnt_dir"] + "/boot")
    elif cfg["fs"] == "btrfs":
        p2 = disk + idf + " "
        subprocess.run("mkfs.btrfs -f -L ROOTFS " + p2, shell=True)
        subprocess.run(
            "mount -t btrfs -o compress=zstd " + p2 + cfg["mnt_dir"], shell=True
        )
        for i in ["/@", "/@home", "/@log", "/@pkg", "/@.snapshots"]:
            subprocess.run("btrfs su cr " + cfg["mnt_dir"] + i, shell=True)
        subprocess.run("umount " + p2, shell=True)
        subprocess.run(
            "mount -t btrfs -o compress=zstd,subvol=@ " + p2 + cfg["mnt_dir"],
            shell=True,
        )
        os.mkdir(cfg["mnt_dir"] + "/home")
        subprocess.run(
            "mount -t btrfs -o compress=zstd,subvol=@home "
            + p2
            + cfg["mnt_dir"]
            + "/home",
            shell=True,
        )
        os.mkdir(cfg["mnt_dir"] + "/boot")
        if cfg["has_uefi"]:
            os.mkdir(cfg["mnt_dir"] + "/boot/efi")

    logging.info("Partitioned successfully")


def create_fstab(ldev, ldev_alt=None, simple_vfat=False) -> None:
    """
    Create the /etc/fstab file with the appropriate mount points and options based on the given parameters.

    Parameters
    ----------
        ldev (str): The logical device path.
        ldev_alt (str, optional): An alternate logical device path. Defaults to None.
        simple_vfat (bool, optional): Flag indicating whether to use simple VFAT options. Defaults to False.
    Returns
    -------
    Nothing
    """
    if cfg["has_uefi"]:
        id1 = get_fsline(ldev + "p2")
        id2 = get_fsline(ldev + "p3")
    else:
        id1 = get_fsline(ldev + "p1")
        id2 = get_fsline((ldev_alt + "p1") if ldev_alt is not None else (ldev + "p2"))

    if cfg["fs"] == "ext4":
        with open(cfg["mnt_dir"] + "/etc/fstab", "a") as f:
            f.write(id1 + " / ext4 defaults 0 0\n")
    else:
        with open(cfg["mnt_dir"] + "/etc/fstab", "a") as f:
            f.write(
                id2
                + " /"
                + 21 * " "
                + "btrfs rw,relatime,ssd"
                + ",compress=zstd,space_cache=v2,subvol=/@ 0 0\n"
            )
            f.write(
                id2
                + " /.snapshots"
                + 11 * " "
                + "btrfs rw,relatime,ssd,discard=async,compress=zstd,"
                + "space_cache=v2,subvol=/@.snapshots 0 0\n"
            )
            f.write(
                id2
                + " /home"
                + 17 * " "
                + "btrfs rw,relatime,ssd,discard=async,compress=zstd,"
                + "space_cache=v2,subvol=/@home 0 0\n"
            )
            f.write(
                id2
                + " /var/cache/pacman/pkg btrfs rw,relatime,ssd,discard=async,"
                + "space_cache=v2,subvol=/@pkg 0 0\n"
            )
            f.write(
                id2
                + " /var/log"
                + 14 * " "
                + "btrfs rw,relatime,ssd,discard=async,compress=zstd,"
                + "space_cache=v2,subvol=/@log 0 0\n"
            )
    with open(cfg["mnt_dir"] + "/etc/fstab", "a") as f:
        if cfg["has_uefi"]:
            boot_fs = get_parttype(ldev + "p2")
            mount_point = "/boot/efi"
        else:
            boot_fs = get_parttype(ldev + "p1")
            mount_point = "/boot"
        if boot_fs == "vfat":
            f.write(
                id1
                + ((28 * " ") if len(id1) == 14 else "")
                + mount_point
                + 17 * " "
                + boot_fs
                + (" " if cfg["fs"] == "btrfs" else "")
                + "  rw,relatime,fmask=0022,dmask=0022,codepage=437,"
                + ("iocharset=ascii," if not simple_vfat else "")
                + "shortname=mixed,utf8,errors=remount-ro 0 2\n"
            )
        else:
            f.write(
                (
                    get_fsline(ldev + "p2")
                    if not cfg["has_uefi"]
                    else get_fsline(ldev + "p1")
                )
                + " "
                + mount_point
                + 17 * " "
                + boot_fs
                + (" " if cfg["fs"] == "btrfs" else "")
                + " rw,relatime,errors=remount-ro 0 2\n"
            )


def create_extlinux_conf(ldev) -> None:
    """
    Creates an extlinux configuration file.

    Parameters
    ----------
        ldev: The logical device path.

    Returns
    -------
    Nothing
    """
    if not os.path.exists(cfg["mnt_dir"] + "/boot/extlinux"):
        os.mkdir(cfg["mnt_dir"] + "/boot/extlinux")
        subprocess.run(["touch", cfg["mnt_dir"] + "/boot/extlinux/extlinux.conf"])
    with open(cfg["mnt_dir"] + "/boot/extlinux/extlinux.conf", "w") as f:
        f.write(cfg["configtxt"])
        # add append root=UUID=... + cmdline
        if "partition_table_root" in cfg:
            root_uuid = get_fsline(ldev + "p1")
        else:
            root_uuid = get_fsline(ldev + "p2")
        f.write("    append root=" + root_uuid + " " + cfg["cmdline"])
        if cfg["configtxt_suffix"] is not None:
            f.write(cfg["configtxt_suffix"])


def grub_install(arch: str = "arm64-efi") -> None:
    """
    Installs GRUB bootloader and generates the GRUB configuration file.

    Parameters
    ----------
        arch (str, optional): The architecture for the bootloader. Defaults to "arm64-efi".

    Returns
    -------
    Nothing
    """
    grubfile = open(cfg["mnt_dir"] + "/etc/default/grub")
    grubconf = grubfile.read()
    grubfile.close()
    grubcmdl = cfg["grubcmdl"]
    grubdtb = cfg["grubdtb"]
    grubconf = grubconf.replace(
        'GRUB_CMDLINE_LINUX_DEFAULT="loglevel=3 quiet"',
        f'GRUB_CMDLINE_LINUX_DEFAULT="{grubcmdl}"',
    )
    if cfg["base"] == "debian":
        if grubdtb:
            grubconf += f'\nGRUB_DTB="{grubdtb}"'
    else:
        if grubdtb:
            grubconf = grubconf.replace(
                '# GRUB_DTB="path_to_dtb_file"', f'GRUB_DTB="{grubdtb}"'
            )
    grubfile = open(cfg["mnt_dir"] + "/etc/default/grub", "w")
    grubfile.write(grubconf)
    grubfile.close()
    run_chroot_cmd(
        cfg["mnt_dir"],
        [
            "/sbin/grub-install",
            f"--target={arch}",
            "--efi-directory=/boot/efi",
            "--removable",
            f"--bootloader-id={cfg['base']}",
        ],
    )
    if not os.path.exists(cfg["mnt_dir"] + "/boot/grub"):
        os.mkdir(cfg["mnt_dir"] + "/boot/grub")
    run_chroot_cmd(cfg["mnt_dir"], ["/sbin/grub-mkconfig", "-o", "/boot/grub/grub.cfg"])


def cleanup() -> None:
    """
    Cleans up the work directory.

    Returns
    -------
    Nothing
    """
    logging.info("Cleaning up")
    subprocess.run(["rm", "-rf", cfg["work_dir"]])
