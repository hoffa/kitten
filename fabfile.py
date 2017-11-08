#!/usr/bin/env python2
# coding = utf-8

import fabric.api


def run(command):
    """<command> Run command"""
    fabric.api.run(command)


def sudo(command):
    """<command> Run command as root"""
    fabric.api.sudo(command)


def get(path):
    """<path> Download file"""
    fabric.api.get(path, use_sudo=True)


def put(local_path, remote_path):
    """<local-path>,<remote-path> Upload file"""
    fabric.api.put(local_path, remote_path, use_sudo=True)
