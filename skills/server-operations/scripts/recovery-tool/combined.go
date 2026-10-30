package main

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sort"
	"strings"
)

func manifestBytes(m Manifest) int64 {
	seen := map[string]bool{}
	var total int64
	for _, en := range m.Entries {
		if en.Kind == "file" && !seen[en.Hash] {
			total += en.Size
			seen[en.Hash] = true
		}
	}
	return total
}

func combineHosts(nas, vps Manifest) (Manifest, error) {
	if nas.Parent != "" || vps.Parent != "" || vps.Scope != "vps/gateway" {
		return nas, errors.New("combine requires standalone NAS and VPS captures")
	}
	nasEntries := append([]Entry(nil), nas.Entries...)
	nas.Entries = nil
	for _, capture := range []struct {
		host    string
		entries []Entry
	}{{"nas", nasEntries}, {"vps", vps.Entries}} {
		for _, en := range capture.entries {
			if !strings.HasPrefix(en.Path, "rootfs/") {
				return nas, errors.New("host entry outside rootfs")
			}
			en.Path = "hosts/" + capture.host + "/" + en.Path
			if en.Hardlink != "" {
				en.Hardlink = capture.host + ":" + en.Hardlink
			}
			nas.Entries = append(nas.Entries, en)
		}
	}
	nas.Scope = "nas-vps/full"
	nas.Notes = []string{"One standalone NAS/VPS package, compressed on NAS before copying to verified external storage. Frozen ALI is untouched.", "NAS capture: " + nas.Created.Format("2006-01-02T15:04:05Z07:00") + "; VPS capture: " + vps.Created.Format("2006-01-02T15:04:05Z07:00") + ". These are separate host capture times, not a cross-host atomic snapshot.", "NAS writers, including Portal, were paused only for the local cold copy. Restore one selected host into a new isolated POSIX directory before authorized production replacement."}
	if nas.Repositories == nil {
		nas.Repositories = map[string]string{}
	}
	for k, v := range vps.Repositories {
		nas.Repositories["vps/"+k] = v
	}
	sort.Slice(nas.Entries, func(i, j int) bool { return nas.Entries[i].Path < nas.Entries[j].Path })
	return nas, Validate(nas)
}

func selectHost(m Manifest, host string) (Manifest, error) {
	if m.Scope != "nas-vps/full" {
		if host != "" {
			return m, errors.New("--host applies only to a combined NAS/VPS package")
		}
		return m, nil
	}
	if host != "nas" && host != "vps" {
		return m, errors.New("combined restore requires --host nas or --host vps")
	}
	prefix := "hosts/" + host + "/"
	var entries []Entry
	for _, en := range m.Entries {
		if strings.HasPrefix(en.Path, prefix) {
			en.Path = strings.TrimPrefix(en.Path, prefix)
			entries = append(entries, en)
		}
	}
	if len(entries) == 0 {
		return m, errors.New("selected host is absent from package")
	}
	m.Entries, m.Scope = entries, host+"/full"
	return m, Validate(m)
}

func compressPackage(ctx context.Context, archive string, m Manifest, blobs map[string]string) error {
	f, e := os.OpenFile(archive+".part", os.O_CREATE|os.O_EXCL|os.O_WRONLY, 0600)
	if e != nil {
		return e
	}
	defer f.Close()
	if e = WriteStream(ctx, f, m, blobs, nil); e != nil {
		return e
	}
	if e = f.Sync(); e != nil {
		return e
	}
	if e = f.Close(); e != nil {
		return e
	}
	return publishNoReplace(archive+".part", archive)
}

func copyPackage(ctx context.Context, archive, id, exports string) error {
	stage := filepath.Join(exports, ".copy-"+id)
	if e := os.Mkdir(stage, 0700); e != nil {
		return e
	}
	part := filepath.Join(stage, "package.tar.gz.part")
	e := copyAndCheck(ctx, archive, part)
	if e != nil {
		return fmt.Errorf("external copy retained as %s: %w", part, e)
	}
	if e = ctx.Err(); e != nil {
		return e
	}
	if e = publishNoReplace(part, filepath.Join(exports, id+".tar.gz")); e != nil {
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
	return os.Remove(stage)
}

func copyAndCheck(ctx context.Context, archive, part string) error {
	in, e := os.Open(archive)
	if e != nil {
		return e
	}
	defer in.Close()
	i, e := in.Stat()
	if e != nil {
		return e
	}
	out, e := os.OpenFile(part, os.O_CREATE|os.O_EXCL|os.O_WRONLY, 0600)
	if e != nil {
		return e
	}
	defer out.Close()
	h := sha256.New()
	observed, finish := startProgress(ctx, "copying-package-to-external", i.Size())
	n, e := io.Copy(io.MultiWriter(out, h), contextReader{observed, in})
	if e == nil && n != i.Size() {
		e = errors.New("package changed size during copy")
	}
	if e == nil {
		e = out.Sync()
	}
	if closeError := out.Close(); e == nil {
		e = closeError
	}
	finish(e == nil)
	if e != nil {
		return e
	}
	observed, finish = startProgress(ctx, "external-readback", i.Size())
	digest, e := DigestContext(observed, part)
	if e == nil && digest != hex.EncodeToString(h.Sum(nil)) {
		e = errors.New("external package differs from NAS source")
	}
	finish(e == nil)
	if e == nil {
		fmt.Fprintf(os.Stderr, "{\"phase\":\"external-package-verified\",\"sha256\":%q,\"bytes\":%d}\n", digest, i.Size())
	}
	return e
}
