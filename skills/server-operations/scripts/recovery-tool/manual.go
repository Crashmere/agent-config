package main

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"io/fs"
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"sort"
	"strings"
	"syscall"
	"time"
)

const pausedReceipt = "/run/lock/agent-backup-paused.json"

type VolumeError struct {
	State string
	Err   error
}

func (e *VolumeError) Error() string { return e.Err.Error() }
func (e *VolumeError) Unwrap() error { return e.Err }

func volumeError(state string, err error) error {
	return &VolumeError{State: state, Err: err}
}

func ReadinessState(err error) string {
	if err == nil {
		return "ready"
	}
	var volume *VolumeError
	if errors.As(err, &volume) {
		return volume.State
	}
	return "error"
}

// OpenExports pins the verified volume through an open mount descriptor. A
// detached/replaced mount can never redirect a job to the NAS root filesystem.
func OpenExports(c Config, create bool) (string, func(), error) {

	if c.UUID == "" {
		return "", nil, volumeError("unconfigured", errors.New("External volume UUID is not configured; identify the device through SSH first"))
	}
	root, e := openExternalMount(c.Mount, c.UUID)
	if e != nil {
		return "", nil, fmt.Errorf("External backup storage unavailable: %w", e)
	}
	rel, e := filepath.Rel(c.Mount, c.Exports)
	if e != nil || !filepath.IsLocal(rel) || rel == "." {
		root.Close()
		return "", nil, errors.New("invalid external export directory")
	}
	pinned, e := os.OpenRoot(fmt.Sprintf("/proc/self/fd/%d", root.Fd()))
	if e != nil {
		root.Close()
		return "", nil, e
	}
	defer pinned.Close()
	if create {
		e = pinned.MkdirAll(rel, 0700)
	}
	if e != nil {
		root.Close()
		return "", nil, e
	}
	exports, e := pinned.Open(rel)
	if e != nil {
		root.Close()
		return "", nil, e
	}
	info, e := exports.Stat()
	mountInfo, mountError := root.Stat()
	root.Close()
	if e != nil || mountError != nil || !info.IsDir() || info.Sys().(*syscall.Stat_t).Dev != mountInfo.Sys().(*syscall.Stat_t).Dev {
		exports.Close()
		return "", nil, errors.New("export directory must remain on the registered external volume")
	}
	path := fmt.Sprintf("/proc/self/fd/%d", exports.Fd())
	return path, func() { exports.Close() }, nil
}

func ManualPolicy(c Config) map[string]any {

	p := map[string]any{"mode": "nas-stage-single-package", "state": "unconfigured", "scope": "nas-vps/full", "host": c.Host, "mount": c.Mount, "staging": backupStaging, "available": false}
	if c.UUID == "" {
		p["error"] = "External volume UUID is not configured; identify the device through SSH first"
		return p
	}
	volume, e := openExternalMount(c.Mount, c.UUID)
	if e != nil {
		p["state"] = ReadinessState(e)
		p["error"] = e.Error()
	} else {
		defer volume.Close()
		readOnly, e := externalMountReadOnly(volume)
		if e != nil || readOnly {
			p["state"] = "error"
			p["error"] = "Cannot establish external volume writability"
			if readOnly {
				p["error"] = "External volume is mounted read-only; inspect mount settings through SSH"
			}
		} else {
			p["state"] = "ready"
			p["available"] = true
		}
	}
	return p
}

func backupUnits(c Config) []string {
	seen := map[string]bool{}
	for _, unit := range c.HostUnits {
		seen[unit] = true
	}
	for _, app := range c.Apps {
		for _, unit := range app.Units {
			if strings.HasSuffix(unit, ".service") || strings.HasSuffix(unit, ".timer") {
				seen[unit] = true
			}
		}
	}
	units := make([]string, 0, len(seen))
	for unit := range seen {
		units = append(units, unit)
	}
	// Timers stop before services so no new scheduled work can begin.
	sort.Slice(units, func(i, j int) bool {
		if strings.HasSuffix(units[i], ".timer") != strings.HasSuffix(units[j], ".timer") {
			return strings.HasSuffix(units[i], ".timer")
		}
		return units[i] < units[j]
	})
	return units
}

func unitAction(ctx context.Context, action, unit string) error {
	ctx, cancel := context.WithTimeout(ctx, 5*time.Minute)
	defer cancel()
	b, e := exec.CommandContext(ctx, "systemctl", action, unit).CombinedOutput()
	if e != nil {
		return fmt.Errorf("%s %s: %w (%s)", action, unit, e, strings.TrimSpace(string(b)))
	}
	return nil
}

func resumeUnits(units []string) error {
	var failures []error
	for i := len(units) - 1; i >= 0; i-- {
		if e := unitAction(context.Background(), "start", units[i]); e != nil {
			failures = append(failures, e)
		}
	}
	if len(failures) != 0 {
		return errors.Join(failures...)
	}
	if e := os.Remove(pausedReceipt); e != nil && !os.IsNotExist(e) {
		return e
	}
	return nil
}

// ResumeInterrupted is an explicit administrator operation after an interrupted agent job.
func ResumeInterrupted(c Config) error {
	b, e := os.ReadFile(pausedReceipt)
	if os.IsNotExist(e) {
		return nil
	}
	if e != nil {
		return e
	}
	unlock, e := Lock("/run/lock/server-maintenance.lock")
	if e != nil {
		return fmt.Errorf("cannot recover interrupted backup while maintenance is active: %w", e)
	}
	defer unlock()
	var units []string
	if e = json.Unmarshal(b, &units); e != nil {
		return e
	}
	allowed := map[string]bool{}
	for _, unit := range backupUnits(c) {
		allowed[unit] = true
	}
	for _, unit := range units {
		if !allowed[unit] {
			return errors.New("interrupted backup receipt contains an unregistered unit")
		}
	}
	return resumeUnits(units)
}

func coldSources(c Config) []Source {
	var sources []Source
	for _, app := range c.Apps {
		app := app
		sources = append(sources, Source{Path: app.Root, Target: "rootfs/" + strings.TrimPrefix(app.Root, "/"), Service: app.ID, Skip: func(rel string, d fs.DirEntry) bool {
			first := strings.Split(filepath.ToSlash(rel), "/")[0]
			return first == "backups" || first == "releases" || transient(rel, d)
		}})
	}
	for _, path := range c.Shared {
		sources = append(sources, Source{Path: path, Target: "rootfs/" + strings.TrimPrefix(path, "/"), Service: "shared", Skip: transient})
	}
	return sources
}

func stageBlobs(ctx context.Context, stage string, blobs map[string]string) (map[string]string, error) {
	staged := make(map[string]string, len(blobs))
	for hash, source := range blobs {
		if e := ctx.Err(); e != nil {
			return nil, e
		}
		destination := filepath.Join(stage, hash)
		in, e := os.Open(source)
		if e != nil {
			return nil, e
		}
		out, e := os.OpenFile(destination, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0600)
		if e != nil {
			in.Close()
			return nil, e
		}
		h := sha256.New()
		_, e = io.Copy(out, io.TeeReader(contextReader{ctx, in}, h))
		in.Close()
		if e == nil {
			e = out.Sync()
		}
		if closeError := out.Close(); e == nil {
			e = closeError
		}
		if e != nil {
			return nil, e
		}
		if hex.EncodeToString(h.Sum(nil)) != hash {
			return nil, fmt.Errorf("source changed during cold copy: %s", source)
		}
		staged[hash] = destination
	}
	return staged, nil
}

func sourceBytes(sources []Source) (int64, error) {
	var total int64
	for _, source := range sources {
		e := filepath.WalkDir(source.Path, func(p string, d fs.DirEntry, e error) error {
			if e != nil {
				return e
			}
			rel, e := filepath.Rel(source.Path, p)
			if e != nil {
				return e
			}
			if source.Skip != nil && source.Skip(rel, d) {
				if d.IsDir() {
					return filepath.SkipDir
				}
				return nil
			}
			info, e := d.Info()
			if e == nil && info.Mode().IsRegular() {
				total += info.Size()
			}
			return e
		})
		if e != nil {
			return 0, e
		}
	}
	return total, nil
}

// GenerateManual combines an acknowledged VPS capture with cold NAS state locally.
func GenerateManual(ctx context.Context, c Config, gatewayID string, phase func(string)) (m Manifest, out string, err error) {
	if e := ctx.Err(); e != nil {
		return m, "", e
	}
	stage, e := gatewayStage(gatewayID)
	if e != nil {
		return m, "", e
	}
	gateway, gatewayBlobs, e := loadGateway(stage)
	if e != nil {
		return m, "", e
	}
	if ReadSmall(filepath.Join(stage, "gateway-accepted"), 100) != Hash(gateway) {
		return m, "", errors.New("VPS transport has not been acknowledged; use the unified backup script")
	}
	exports, close, e := OpenExports(c, true)
	if e != nil {
		return m, "", e
	}
	defer close()
	var unlocks []func()
	defer func() {
		for i := len(unlocks) - 1; i >= 0; i-- {
			unlocks[i]()
		}
	}()
	locks := []string{"server-maintenance", "portal-registry"}
	for _, app := range c.Apps {
		locks = append(locks, app.ID+"-deploy")
	}
	for _, name := range locks {
		unlock, e := Lock("/run/lock/" + name + ".lock")
		if e != nil {
			return m, "", fmt.Errorf("maintenance is busy (%s): %w", name, e)
		}
		unlocks = append(unlocks, unlock)
	}
	// Reject registry/configuration drift between initial inspection and locking.
	if c.Path != "" {
		fresh, e := LoadConfig(c.Path)
		if e != nil {
			return m, "", e
		}
		if !reflect.DeepEqual(c, fresh) {
			return m, "", errors.New("configuration or registry changed before locking; inspect and retry")
		}
	}
	sources := coldSources(c)
	bytes, e := sourceBytes(sources)
	if e != nil {
		return m, "", e
	}
	available, e := Available(stage)
	if e != nil || available < 2*bytes+manifestBytes(gateway)+(1<<30) {
		return m, "", errors.New("NAS needs headroom for cold state, combined archive and 1 GiB operating reserve")
	}
	available, e = Available(exports)
	if e != nil || available < bytes+manifestBytes(gateway)+(512<<20) {
		return m, "", errors.New("external storage needs headroom for the full combined package")
	}
	claim, e := os.OpenFile(filepath.Join(stage, "job-started"), os.O_CREATE|os.O_EXCL|os.O_WRONLY, 0600)
	if e != nil {
		return m, "", errors.New("this staging job has already started; inspect it instead of duplicating backup")
	}
	claim.Close()
	blobStage := filepath.Join(stage, "nas-blobs")
	if e = os.Mkdir(blobStage, 0700); e != nil {
		return m, "", e
	}
	var stopped []string
	resumed := false
	defer func() {
		if !resumed {
			if e := resumeUnits(stopped); e != nil {
				err = errors.Join(err, fmt.Errorf("services need recovery: %w", e))
			}
		}
		if err != nil {
			err = fmt.Errorf("%w; internal staging retained as %s", err, stage)
		}
	}()
	phase("pausing")
	for _, unit := range backupUnits(c) {
		info := Unit(unit)
		if info["LoadState"] != "loaded" || info["ActiveState"] == "" {
			return m, "", fmt.Errorf("cannot establish runtime state of %s", unit)
		}
		state := info["ActiveState"]
		if state == "activating" || state == "deactivating" || unit == "nas-lan-tls.service" && state == "active" {
			return m, "", fmt.Errorf("%s is busy; retry later", unit)
		}
		if state != "active" {
			continue
		}
		stopped = append(stopped, unit)
		b, _ := json.Marshal(stopped)
		if e = Atomic(pausedReceipt, b, 0600); e != nil {
			return m, "", e
		}
		if e = unitAction(ctx, "stop", unit); e != nil {
			return m, "", e
		}
		after := Unit(unit)
		if after["ActiveState"] != "inactive" || after["Result"] != "" && after["Result"] != "success" {
			return m, "", fmt.Errorf("%s did not stop gracefully", unit)
		}
	}
	phase("scanning-nas")
	observed, finish := startProgress(ctx, "scanning-nas", bytes)
	m, blobs, e := ScanContext(observed, sources, "full")
	finish(e == nil)
	if e != nil {
		return m, "", e
	}
	observed, finish = startProgress(ctx, "staging-nas", manifestBytes(m))
	copied, e := stageBlobs(observed, blobStage, blobs)
	finish(e == nil)
	if e != nil {
		return m, "", e
	}
	for _, app := range c.Apps {
		m.Repositories[app.ID] = app.Repo + "@" + ReadSmall(filepath.Join(app.Root, "current-commit"), 100)
	}
	m, e = combineHosts(m, gateway)
	if e != nil {
		return m, "", e
	}
	for hash, path := range gatewayBlobs {
		if _, ok := copied[hash]; !ok {
			copied[hash] = path
		}
	}
	if e = Validate(m); e != nil {
		return m, "", e
	}
	phase("resuming")
	if e = resumeUnits(stopped); e != nil {
		return m, "", e
	}
	resumed = true
	phase("compressing")
	archive := filepath.Join(stage, m.ID+".tar.gz")
	observed, finish = startProgress(ctx, "compressing", manifestBytes(m))
	e = compressPackage(observed, archive, m, copied)
	finish(e == nil)
	if e != nil {
		return m, "", e
	}
	phase("verifying-nas-package")
	observed, finish = startProgress(ctx, "verifying-nas-package", manifestBytes(m))
	verified, e := readCompressed(observed, archive, "", nil, false)
	finish(e == nil)
	if e != nil {
		return m, "", fmt.Errorf("NAS archive verification failed: %w", e)
	}
	if Hash(verified) != Hash(m) {
		return m, "", errors.New("NAS archive manifest changed during read-back")
	}
	if e = ctx.Err(); e != nil {
		return m, "", e
	}
	phase("copying-package-to-external")
	if e = copyPackage(ctx, archive, m.ID, exports); e != nil {
		return m, "", e
	}
	currentVolume, e := openExternalMount(c.Mount, c.UUID)
	if e != nil {
		return m, "", e
	}
	current, currentError := currentVolume.Stat()
	pinned, pinnedError := os.Stat(exports)
	currentVolume.Close()
	if currentError != nil || pinnedError != nil || current.Sys().(*syscall.Stat_t).Dev != pinned.Sys().(*syscall.Stat_t).Dev {
		return m, "", errors.New("external mount changed before internal cleanup; verified package and staging retained")
	}
	// Staging belongs solely to this successful job, never to another archive.
	if e = os.RemoveAll(stage); e != nil {
		return m, "", e
	}
	phase("completed")
	return m, filepath.Join(c.Exports, m.ID+".tar.gz"), nil
}
