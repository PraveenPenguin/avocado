# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# This code was inspired in the autotest project,
#
# client/base_utils.py
#
# Copyright: 2018 IBM
# Authors : Praveen K Pandey <praveen@linux.vnet.ibm.com>


"""
Disk utilities
"""


import os
import json
import re

from . import process


class DiskUtilsError(Exception):
    """
    Base Exception Class for all DiskUtils Error
    """


def freespace(path):
    fs_stats = os.statvfs(path)
    return fs_stats.f_bsize * fs_stats.f_bavail


def get_disk_blocksize(path):
    """Return the disk block size, in bytes"""
    fs_stats = os.statvfs(path)
    return fs_stats.f_bsize


def get_disks():
    """
    Returns the physical "hard drives" available on this system

    This is a simple wrapper around `lsblk` and will return all the
    top level physical (non-virtual) devices return by it.

    TODO: this is currently Linux specific.  Support for other
    platforms is desirable and may be implemented in the future.

    :returns: a list of paths to the physical disks on the system
    :rtype: list of str
    """
    json_result = process.run('lsblk --json')
    json_data = json.loads(json_result.stdout_text)
    return ['/dev/%s' % str(disk['name'])
            for disk in json_data['blockdevices']]


def get_available_filesystems():
    """
    Return a list of all available filesystem types

    :returns: a list of filesystem types
    :rtype: list of str
    """
    filesystems = set()
    with open('/proc/filesystems') as proc_fs:
        for proc_fs_line in proc_fs.readlines():
            filesystems.add(re.sub(r'(nodev)?\s*', '', proc_fs_line))
    return list(filesystems)


def get_filesystem_type(mount_point='/'):
    """
    Returns the type of the filesystem of mount point informed.
    The default mount point considered when none is informed
    is the root "/" mount point.

    :param str mount_point: mount point to asses the filesystem type, default "/"
    :returns: filesystem type
    :rtype: str
    """
    with open('/proc/mounts') as mounts:
        for mount_line in mounts.readlines():
            _, fs_file, fs_vfstype, _, _, _ = mount_line.split()
            if fs_file == mount_point:
                return fs_vfstype


def get_partition_info(device):
    """
    Get partition info

    :param device: the device, e.g. /dev/sda3

    :return: dictionary which has all partition info

    ## Todo
    #right now this utility works for block device
    #still nvme kind of device support need to be added
    """
    if device in get_disks():
        raise DiskUtilsError('provided disk partition not disk')

    values = list()

    disk_device = device.rstrip('0123456789')
    # Parse fdisk output to get partition info.  Ugly but it works.

    fdisk_fd = os.popen("/sbin/fdisk -l -u  '%s'" % disk_device)

    fdisk_lines = fdisk_fd.readlines()
    fdisk_fd.close()
    for line in fdisk_lines:
        if not line.startswith(device):
            continue
        value = re.split(r'\s+', line)
        if not value[1] == "*":
            device = value[0]
            boot = ''
            for data in range(1, len(value)):
                values.append(value[data])
            del value[:]
            value.append(device)
            value.append(boot)
            value.extend(values)
        if len(value) > 7:
            type_atribute = len(value) - 7
            type_data = value[7]
            for data in range(1, type_atribute):
                type_data = type_data + ' ' + value[7 + data]
            value[7] = type_data.strip(' ')

        return {
            "Device": value[0],
            "Boot": value[1],
            "Start": value[2],
            "End": value[3],
            "Sectors": value[4],
            "Size": value[5],
            "Id": value[6],
            "Type": value[7]}


def is_linux_fs_type(device):
    """
    Checks if specified partition is type is linux (83)

    :param device: the device, e.g. /dev/sda3
    :return: False if the supplied partition name is not type 83 linux, True
            otherwise

    ##TODO : nvme kind of device still support needed
    """

    if get_partition_info(device)['Type'] == 83:
        return True
    return False
