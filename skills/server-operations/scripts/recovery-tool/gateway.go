package main

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"regexp"
	"strings"
)

// Streaming gateway capture writes no recovery archive to VPS or the maintenance Mac.
func gatewayStream(ctx context.Context, paths []string) (err error) {
	if os.Geteuid() != 0 || len(paths) == 0 {
		return errors.New("gateway-stream requires administrator SSH and explicit source roots")
	}
	unlock, e := Lock("/run/lock/server-maintenance.lock")
	if e != nil {
		return e
	}
	defer unlock()
	if Unit("certbot-renew.service")["ActiveState"] == "active" || Unit("certbot-renew.service")["ActiveState"] == "activating" {
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
		return errors.New("VPS certificate renewal started before timer pause; wait before capture")
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
	m.Notes = []string{"VPS gateway/proxy configuration and programs captured through trusted agent SSH. NAS application data is separate. Source configuration writers must be paused or excluded through maintenance coordination before capture."}
	return WriteStream(ctx, os.Stdout, m, blobs, nil)
}

func receiveGateway(ctx context.Context, c Config) error {
	exports, close, e := OpenExports(c, true)
	if e != nil {
		return e
	}
	defer close()
	unlock, e := Lock("/run/lock/server-maintenance.lock")
	if e != nil {
		return e
	}
	defer unlock()
	id := "gateway-" + NewID()
	stage := filepath.Join(exports, id)
	if e = os.Mkdir(stage, 0700); e != nil {
		return e
	}
	archive := filepath.Join(stage, "archive.tar.gz")
	f, e := os.OpenFile(archive, os.O_CREATE|os.O_EXCL|os.O_WRONLY, 0600)
	if e != nil {
		return e
	}
	_, e = io.Copy(f, contextReader{ctx, os.Stdin})
	if e == nil {
		e = f.Sync()
	}
	ce := f.Close()
	if e != nil {
		return fmt.Errorf("incomplete gateway stage %s: %w", id, e)
	}
	if ce != nil {
		return ce
	}
	m, e := ChainContext(ctx, []string{archive}, filepath.Join(stage, "verify"), nil)
	if e != nil {
		return fmt.Errorf("gateway stage %s failed verification: %w", id, e)
	}
	if m.Scope != "vps/gateway" {
		return errors.New("not a VPS gateway package")
	}
	b, _ := json.MarshalIndent(m, "", "  ")
	if e = Atomic(filepath.Join(stage, "manifest.json"), b, 0600); e != nil {
		return e
	}
	fmt.Println(id)
	return nil
}

// Publish only after both SSH processes exited successfully in the calling script.
func acceptGateway(ctx context.Context, c Config, id string) error {
	if !regexp.MustCompile(`^gateway-[A-Za-z0-9-]{1,100}$`).MatchString(id) {
		return errors.New("invalid gateway staging ID")
	}
	exports, close, e := OpenExports(c, false)
	if e != nil {
		return e
	}
	defer close()
	unlock, e := Lock("/run/lock/server-maintenance.lock")
	if e != nil {
		return e
	}
	defer unlock()
	stage := filepath.Join(exports, id)
	m, e := ChainContext(ctx, []string{filepath.Join(stage, "archive.tar.gz")}, filepath.Join(stage, "recheck"), nil)
	if e != nil {
		return e
	}
	if m.Scope != "vps/gateway" {
		return errors.New("not a VPS gateway package")
	}
	if e = publishNoReplace(filepath.Join(stage, "archive.tar.gz"), filepath.Join(exports, id+".tar.gz")); e != nil {
		return e
	}
	if e = publishNoReplace(filepath.Join(stage, "manifest.json"), filepath.Join(exports, id+".json")); e != nil {
		return e
	}
	d, e := os.Open(exports)
	if e != nil {
		return e
	}
	e = d.Sync()
	d.Close()
	if e != nil {
		return e
	}
	if e = os.RemoveAll(stage); e != nil {
		return e
	}
	fmt.Println(filepath.Join(c.Exports, id+".tar.gz"))
	return nil
}
