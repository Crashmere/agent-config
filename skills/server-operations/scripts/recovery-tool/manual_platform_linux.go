//go:build linux

package main

import (
	"context"
	"encoding/json"
	"errors"
	"os"
	"os/exec"
	"path/filepath"
	"syscall"
	"time"

	"golang.org/x/sys/unix"
)

func checkRestoreFS(parent string) error {
	var s unix.Statfs_t
	if e := unix.Statfs(parent, &s); e != nil {
		return e
	}
	if s.Type == unix.EXFAT_SUPER_MAGIC || s.Type == unix.MSDOS_SUPER_MAGIC {
		return errors.New("isolated restore needs a POSIX filesystem; exFAT/FAT can store archives but not their metadata")
	}
	return nil
}

func openExternalMount(mount, uuid string) (*os.File, error) {
	if uuid == "" || !filepath.IsAbs(mount) || filepath.Clean(mount) != mount || mount == "/" {
		return nil, volumeError("unconfigured", errors.New("valid external mount and nonempty UUID required"))
	}
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	b, e := exec.CommandContext(ctx, "findmnt", "--json", "--mountpoint", mount, "--output", "TARGET,UUID").Output()
	if e != nil {
		return nil, mountCommandError(e, ctx.Err())
	}
	var mounts struct {
		Filesystems []struct {
			Target string `json:"target"`
			UUID   string `json:"uuid"`
		} `json:"filesystems"`
	}
	if e = json.Unmarshal(b, &mounts); e != nil || len(mounts.Filesystems) != 1 {
		return nil, volumeError("error", errors.New("cannot read the configured mounted filesystem"))
	}
	if mounts.Filesystems[0].Target != mount || mounts.Filesystems[0].UUID != uuid {
		return nil, volumeError("mismatch", errors.New("mounted volume does not match the registered UUID"))
	}
	f, e := os.Open(mount)
	if e != nil {
		return nil, e
	}
	info, e := f.Stat()
	root, rootError := os.Stat("/")
	if e != nil || rootError != nil || !info.IsDir() {
		f.Close()
		return nil, errors.New("cannot identify the mounted filesystem")
	}
	if info.Sys().(*syscall.Stat_t).Dev == root.Sys().(*syscall.Stat_t).Dev {
		f.Close()
		return nil, volumeError("mismatch", errors.New("the backup volume must not be the NAS root filesystem"))
	}
	// Recheck after opening so replacement between lookup and open is rejected.
	b, e = exec.CommandContext(ctx, "findmnt", "--json", "--mountpoint", mount, "--output", "TARGET,UUID").Output()
	var again struct {
		Filesystems []struct {
			Target string `json:"target"`
			UUID   string `json:"uuid"`
		} `json:"filesystems"`
	}
	current, statError := os.Stat(mount)
	if e != nil {
		f.Close()
		return nil, mountCommandError(e, ctx.Err())
	}
	if json.Unmarshal(b, &again) != nil || len(again.Filesystems) != 1 {
		f.Close()
		return nil, volumeError("error", errors.New("cannot recheck the configured mounted filesystem"))
	}
	if again.Filesystems[0].Target != mount || again.Filesystems[0].UUID != uuid || statError != nil || !os.SameFile(info, current) {
		f.Close()
		return nil, volumeError("mismatch", errors.New("external mount changed during validation"))
	}
	return f, nil
}

func mountCommandError(err, contextError error) error {
	var exit *exec.ExitError
	if contextError == nil && errors.As(err, &exit) && exit.ExitCode() == 1 {
		return volumeError("disconnected", errors.New("registered external volume is not mounted"))
	}
	if errors.Is(err, exec.ErrNotFound) {
		return volumeError("unsupported", errors.New("the agent recovery tool requires findmnt to identify the external volume"))
	}
	return volumeError("error", errors.New("cannot inspect the configured external mount"))
}

func externalMountReadOnly(volume *os.File) (bool, error) {
	var stat unix.Statfs_t
	if err := unix.Fstatfs(int(volume.Fd()), &stat); err != nil {
		return false, err
	}
	return stat.Flags&unix.ST_RDONLY != 0, nil
}

func publishNoReplace(from, to string) error {
	return unix.Renameat2(unix.AT_FDCWD, from, unix.AT_FDCWD, to, unix.RENAME_NOREPLACE)
}
