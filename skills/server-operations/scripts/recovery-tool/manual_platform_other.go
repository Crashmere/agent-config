//go:build !linux

package main

import (
	"errors"
	"os"
)

func checkRestoreFS(parent string) error { return nil }

func openExternalMount(mount, uuid string) (*os.File, error) {
	return nil, volumeError("unsupported", errors.New("manual external backups require the Linux agent recovery tool"))
}

func externalMountReadOnly(volume *os.File) (bool, error) {
	return false, errors.New("manual external backups require the Linux agent recovery tool")
}

func publishNoReplace(from, to string) error {
	if e := os.Link(from, to); e != nil {
		return e
	}
	return os.Remove(from)
}
