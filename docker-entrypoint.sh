#!/bin/sh

case "$1" in
    aws)
        shift
        exec python aws.py "$@"
        ;;
    ssh)
        shift
        exec fab --skip-bad-hosts --warn-only "$@"
        ;;
    *)
        echo "Usage: hoffa/damn (aws|ssh) [options]"
        exit 1
esac
