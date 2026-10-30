package main

import (
	"archive/tar"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"syscall"
)

const backupStaging = "/var/lib/server-backups"

// VPS sends an uncompressed transport stream; the only gzip package is built on NAS.
func gatewayStream(ctx context.Context, paths []string) (err error) {
	if os.Geteuid() != 0 || len(paths) == 0 {
		return errors.New("gateway-stream requires administrator SSH and explicit source roots")
	}
	unlock, e := Lock("/run/lock/server-maintenance.lock")
	if e != nil {
		return e
	}
	defer unlock()
	if state := Unit("certbot-renew.service")["ActiveState"]; state == "active" || state == "activating" {
		return errors.New("VPS certificate renewal is active; wait before capture")
	}
	timer := Unit("certbot-renew.timer")
	if timer["LoadState"] != "loaded" {
		return errors.New("cannot establish VPS certificate timer state")
	}
	if timer["ActiveState"] == "active" {
		defer func() { err = errors.Join(err, unitAction(context.Background(), "start", "certbot-renew.timer")) }()
		if e = unitAction(ctx, "stop", "certbot-renew.timer"); e != nil {
			return e
		}
	}
	if state := Unit("certbot-renew.service")["ActiveState"]; state == "active" || state == "activating" {
		return errors.New("VPS renewal started before timer pause; wait before capture")
	}
	var sources []Source
	for _, p := range paths {
		if !filepath.IsAbs(p) || filepath.Clean(p) != p || p == "/" {
			return errors.New("absolute source roots required")
		}
		sources = append(sources, Source{Path: p, Target: "rootfs/" + strings.TrimPrefix(p, "/"), Service: "vps", Skip: transient})
	}
	m, blobs, e := ScanContext(ctx, sources, "vps/gateway")
	if e != nil {
		return e
	}
	m.Notes = []string{"VPS configuration captured under its maintenance lock with certificate renewal paused; live gateway/proxy services remain running."}
	observed, finish := startProgress(ctx, "vps-transfer", manifestBytes(m))
	e = writeTarStream(observed, progressWriter{observed, os.Stdout}, m, blobs, nil)
	finish(e == nil)
	return e
}

func stagingRoot() error {
	if e := os.MkdirAll(backupStaging, 0700); e != nil {
		return e
	}
	info, e := os.Lstat(backupStaging)
	if e != nil || !info.IsDir() || info.Mode().Perm() != 0700 || info.Sys().(*syscall.Stat_t).Uid != 0 {
		return errors.New("NAS staging must be a root-owned private directory, not a symlink")
	}
	return nil
}

func gatewayStage(id string) (string, error) {
	if !regexp.MustCompile(`^gateway-[A-Za-z0-9-]{1,100}$`).MatchString(id) {
		return "", errors.New("invalid gateway staging ID")
	}
	if e := stagingRoot(); e != nil {
		return "", e
	}
	stage := filepath.Join(backupStaging, id)
	i, e := os.Lstat(stage)
	if e != nil || !i.IsDir() || i.Mode().Perm() != 0700 || i.Sys().(*syscall.Stat_t).Uid != 0 {
		return "", errors.New("gateway stage is not a root-owned private directory")
	}
	return stage, nil
}

func receiveGateway(ctx context.Context, c Config) error {
	// Missing external media stops the job before any internal recovery data is staged.
	_, closeVolume, e := OpenExports(c, true)
	if e != nil {
		return e
	}
	defer closeVolume()
	unlock, e := Lock("/run/lock/server-maintenance.lock")
	if e != nil {
		return e
	}
	defer unlock()
	if e = stagingRoot(); e != nil {
		return e
	}
	id := "gateway-" + NewID()
	stage := filepath.Join(backupStaging, id)
	if e = os.Mkdir(stage, 0700); e != nil {
		return e
	}
	observed, finish := startProgress(ctx, "nas-receive-vps", 0)
	m, e := readTarPayload(observed, tar.NewReader(os.Stdin), filepath.Join(stage, "gateway-blobs"), true)
	finish(e == nil)
	if e != nil {
		return fmt.Errorf("incomplete internal gateway stage %s: %w", stage, e)
	}
	if m.Scope != "vps/gateway" || m.Parent != "" {
		return errors.New("not a full VPS gateway capture; staging retained")
	}
	b, _ := json.MarshalIndent(m, "", "  ")
	if e = Atomic(filepath.Join(stage, "gateway.json"), b, 0600); e != nil {
		return e
	}
	fmt.Println(id)
	return nil
}

func loadGateway(stage string) (Manifest, map[string]string, error) {
	var m Manifest
	b, e := os.ReadFile(filepath.Join(stage, "gateway.json"))
	if e != nil {
		return m, nil, e
	}
	if e = json.Unmarshal(b, &m); e != nil {
		return m, nil, e
	}
	if e = Validate(m); e != nil {
		return m, nil, e
	}
	if m.Scope != "vps/gateway" || m.Parent != "" {
		return m, nil, errors.New("full VPS gateway capture required")
	}
	blobs := map[string]string{}
	for _, en := range m.Entries {
		if !strings.HasPrefix(en.Path, "rootfs/") {
			return m, nil, errors.New("gateway entry outside rootfs")
		}
		if en.Kind == "file" {
			blobs[en.Hash] = filepath.Join(stage, "gateway-blobs", en.Hash)
		}
	}
	return m, blobs, nil
}

// The maintenance script acknowledges only after both SSH transports exit successfully.
func acceptGateway(ctx context.Context, c Config, id string) error {
	stage, e := gatewayStage(id)
	if e != nil {
		return e
	}
	unlock, e := Lock("/run/lock/server-maintenance.lock")
	if e != nil {
		return e
	}
	defer unlock()
	m, _, e := loadGateway(stage)
	if e != nil {
		return e
	}
	return Atomic(filepath.Join(stage, "gateway-accepted"), []byte(Hash(m)), 0600)
}
