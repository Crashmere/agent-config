package main

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"io"
	"io/fs"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"slices"
	"strings"
	"syscall"
)

type App struct {
	ID    string   `json:"id"`
	Root  string   `json:"root"`
	Repo  string   `json:"repo"`
	Units []string `json:"units"`
}
type Config struct {
	Host         string   `json:"host"`
	Mount        string   `json:"mount"`
	UUID         string   `json:"uuid"`
	Exports      string   `json:"exports"`
	RegistryDir  string   `json:"registryDir"`
	ExpectedApps []string `json:"expectedApps"`
	Shared       []string `json:"shared"`
	HostUnits    []string `json:"hostUnits"`
	Apps         []App    `json:"-"`
	Path         string   `json:"-"`
}

func LoadConfig(path string) (Config, error) {
	var c Config
	f, e := os.Open(path)
	if e != nil {
		return c, e
	}
	defer f.Close()
	d := json.NewDecoder(io.LimitReader(f, 1<<20))
	d.DisallowUnknownFields()
	if e = d.Decode(&c); e != nil {
		return c, e
	}
	if d.Decode(new(any)) != io.EOF {
		return c, errors.New("expected one configuration object")
	}
	if c.Host != "nas" || c.RegistryDir != "/opt/serverportal/registry.d" || len(c.ExpectedApps) == 0 {
		return c, errors.New("NAS host, registry and expected application coverage required")
	}
	c.Path = path
	for _, unit := range c.HostUnits {
		if unit != "nas-lan-tls.timer" && unit != "nas-lan-tls.service" {
			return c, errors.New("unsupported host configuration writer")
		}
	}
	for _, p := range []string{c.Mount, c.Exports} {
		if !filepath.IsAbs(p) || filepath.Clean(p) != p || p == "/" {
			return c, errors.New("absolute clean external paths required")
		}
	}
	rel, e := filepath.Rel(c.Mount, c.Exports)
	if e != nil || !filepath.IsLocal(rel) || rel == "." || strings.ContainsAny(c.UUID, "/\\\x00") {
		return c, errors.New("exports must stay below external mount; invalid UUID")
	}
	ds, e := os.ReadDir(c.RegistryDir)
	if e != nil {
		return c, e
	}
	seen := map[string]bool{}
	id := regexp.MustCompile(`^[a-z][a-z0-9-]{0,63}$`)
	for _, entry := range ds {
		if !strings.HasSuffix(entry.Name(), ".json") {
			continue
		}
		appID := strings.TrimSuffix(entry.Name(), ".json")
		if !id.MatchString(appID) || appID == "serverportal" {
			return c, errors.New("invalid registry application")
		}
		p := filepath.Join(c.RegistryDir, entry.Name())
		resolved, err := filepath.EvalSymlinks(p)
		if err != nil || resolved != "/opt/"+appID+"/config/portal.json" {
			return c, errors.New("registry link must resolve to its own managed declaration")
		}
		b, err := os.ReadFile(p)
		if err != nil {
			return c, err
		}
		var a App
		if err = json.Unmarshal(b, &a); err != nil {
			return c, err
		}
		if a.ID != appID || a.Root != "/opt/"+appID || seen[appID] {
			return c, errors.New("invalid or duplicate application root")
		}
		// Legacy declarations must never reactivate retired backup schedules.
		a.Units = slices.DeleteFunc(a.Units, func(u string) bool { return strings.Contains(u, "-backup.") })
		seen[appID] = true
		c.Apps = append(c.Apps, a)
	}
	for _, expected := range c.ExpectedApps {
		if !seen[expected] {
			return c, errors.New("missing expected application: " + expected)
		}
	}
	c.Apps = append(c.Apps, App{ID: "serverportal", Root: "/opt/serverportal", Repo: "https://github.com/Crashmere/ServerPortal", Units: []string{"serverportal.service", "serverportal-agent.service"}})
	for _, a := range c.Apps {
		for _, u := range a.Units {
			if !regexp.MustCompile("^" + regexp.QuoteMeta(a.ID) + `(?:-[a-z0-9-]+)?\.(?:service|timer)$`).MatchString(u) {
				return c, errors.New("unit outside application ownership")
			}
		}
		if !contains(a.Units, a.ID+".service") {
			return c, errors.New("main writer unit missing")
		}
	}
	paths := []string{}
	for _, a := range c.Apps {
		paths = append(paths, a.Root)
	}
	for _, p := range c.Shared {
		if p == backupStaging || strings.HasPrefix(p, backupStaging+"/") || strings.HasPrefix(backupStaging, p+"/") {
			return c, errors.New("backup staging cannot be a recovery source")
		}
		if !filepath.IsAbs(p) || filepath.Clean(p) != p || p == "/" || strings.HasPrefix(p, c.Mount+"/") || p == c.Mount {
			return c, errors.New("invalid shared recovery source")
		}
		for _, other := range paths {
			if p == other || strings.HasPrefix(p, other+"/") || strings.HasPrefix(other, p+"/") {
				return c, errors.New("overlapping recovery sources")
			}
		}
		paths = append(paths, p)
	}
	return c, nil
}

func contains(list []string, value string) bool {
	for _, item := range list {
		if item == value {
			return true
		}
	}
	return false
}
func transient(rel string, d fs.DirEntry) bool {
	return d.Type()&(os.ModeSocket|os.ModeNamedPipe|os.ModeDevice) != 0 || filepath.Base(rel) == ".portal-state.lock"
}
func Lock(path string) (func(), error) {
	f, e := os.OpenFile(path, os.O_CREATE|os.O_RDWR, 0600)
	if e != nil {
		return nil, e
	}
	if e = syscall.Flock(int(f.Fd()), syscall.LOCK_EX|syscall.LOCK_NB); e != nil {
		f.Close()
		return nil, e
	}
	return func() { syscall.Flock(int(f.Fd()), syscall.LOCK_UN); f.Close() }, nil
}
func Unit(name string) map[string]string {
	b, e := exec.Command("systemctl", "show", name, "--property=LoadState,ActiveState,Result").Output()
	m := map[string]string{}
	if e != nil {
		return m
	}
	for _, line := range strings.Split(string(b), "\n") {
		k, v, ok := strings.Cut(line, "=")
		if ok {
			m[k] = v
		}
	}
	return m
}
func Available(path string) (int64, error) {
	var s syscall.Statfs_t
	e := syscall.Statfs(path, &s)
	return int64(s.Bavail) * int64(s.Bsize), e
}
func ReadSmall(path string, n int64) string {
	f, e := os.Open(path)
	if e != nil {
		return ""
	}
	defer f.Close()
	b, _ := io.ReadAll(io.LimitReader(f, n))
	return strings.TrimSpace(string(b))
}
func Digest(path string) (string, error) {
	return DigestContext(context.Background(), path)
}
func DigestContext(ctx context.Context, path string) (string, error) {
	f, e := os.Open(path)
	if e != nil {
		return "", e
	}
	defer f.Close()
	h := sha256.New()
	if _, e = io.Copy(h, contextReader{ctx, f}); e != nil {
		return "", e
	}
	return hex.EncodeToString(h.Sum(nil)), nil
}
func Atomic(path string, b []byte, mode fs.FileMode) error {
	f, e := os.CreateTemp(filepath.Dir(path), ".write-")
	if e != nil {
		return e
	}
	defer os.Remove(f.Name())
	defer f.Close()
	if e = f.Chmod(mode); e != nil {
		return e
	}
	if _, e = f.Write(b); e != nil {
		return e
	}
	if e = f.Sync(); e != nil {
		return e
	}
	if e = f.Close(); e != nil {
		return e
	}
	if e = os.Rename(f.Name(), path); e != nil {
		return e
	}
	d, e := os.Open(filepath.Dir(path))
	if e != nil {
		return e
	}
	defer d.Close()
	return d.Sync()
}
