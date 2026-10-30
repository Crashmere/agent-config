package main

import (
	"context"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"os"
	"os/signal"
	"os/user"
	"path/filepath"
	"strconv"
	"strings"
	"syscall"

	"filippo.io/age"
)

func main() {
	if e := run(os.Args[1:]); e != nil {
		fmt.Fprintln(os.Stderr, e)
		os.Exit(1)
	}
}
func run(args []string) error {
	if len(args) == 0 {
		return errors.New("usage: server-recovery status|backup|resume|verify|restore|merge|pack")
	}
	f := flag.NewFlagSet(args[0], flag.ContinueOnError)
	config := f.String("config", "/etc/server-recovery.json", "agent-owned NAS volume and coverage configuration")
	work := f.String("work-dir", "", "explicit existing scratch parent; external storage on NAS")
	out := f.String("out", "", "new isolated output path; must not exist")
	identity := f.String("identity", "", "legacy age identity file; no new encryption workflow")
	scope := f.String("scope", "fixture", "pack scope (offline fixtures or gateway)")
	ownership := f.Bool("ownership", false, "restore owners by local user/group names; root and compatible POSIX target required")
	if e := f.Parse(args[1:]); e != nil {
		return e
	}
	ctx, cancel := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM, syscall.SIGHUP)
	defer cancel()
	if args[0] == "gateway-stream" {
		return gatewayStream(ctx, f.Args())
	}
	if args[0] == "receive-gateway" || args[0] == "accept-gateway" {
		if os.Geteuid() != 0 || ReadSmall("/etc/server-maintenance-host", 100) != "nas" {
			return errors.New("gateway receiver requires administrator SSH on NAS")
		}
		c, e := LoadConfig(*config)
		if e != nil {
			return e
		}
		if args[0] == "receive-gateway" && f.NArg() == 0 {
			return receiveGateway(ctx, c)
		}
		if args[0] == "accept-gateway" && f.NArg() == 1 {
			return acceptGateway(ctx, c, f.Arg(0))
		}
		return errors.New("invalid gateway receiver arguments")
	}
	if args[0] == "status" || args[0] == "backup" || args[0] == "resume" {
		if f.NArg() != 0 {
			return errors.New("unexpected arguments")
		}
		c, e := LoadConfig(*config)
		if e != nil {
			return e
		}
		if args[0] == "status" {
			return json.NewEncoder(os.Stdout).Encode(ManualPolicy(c))
		}
		if os.Geteuid() != 0 || ReadSmall("/etc/server-maintenance-host", 100) != "nas" {
			return errors.New("backup/resume require administrator SSH on a marked NAS host")
		}
		if args[0] == "resume" {
			return ResumeInterrupted(c)
		}
		if _, e = os.Lstat(pausedReceipt); !os.IsNotExist(e) {
			return errors.New("interrupted job receipt exists; inspect and run resume first")
		}
		_, path, e := GenerateManual(ctx, c, func(phase string) { fmt.Fprintln(os.Stderr, phase) })
		if e != nil {
			return e
		}
		fmt.Println(path)
		return nil
	}
	if *work == "" || !filepath.IsAbs(*work) {
		return errors.New("--work-dir must name an existing absolute scratch parent")
	}
	info, e := os.Stat(*work)
	if e != nil || !info.IsDir() {
		return errors.New("scratch parent is unavailable")
	}
	// NAS verification never silently stages on its root filesystem.
	if ReadSmall("/etc/server-maintenance-host", 100) == "nas" {
		var c Config
		b, e := os.ReadFile(*config)
		if e != nil {
			return e
		}
		if e = json.Unmarshal(b, &c); e != nil {
			return e
		}
		volume, e := openExternalMount(c.Mount, c.UUID)
		if e != nil {
			return e
		}
		defer volume.Close()
		v, e := volume.Stat()
		if e != nil || v.Sys().(*syscall.Stat_t).Dev != info.Sys().(*syscall.Stat_t).Dev {
			return errors.New("NAS scratch parent must be on its verified external volume")
		}
		parent, e := os.Open(*work)
		if e != nil {
			return e
		}
		defer parent.Close()
		pinned, e := parent.Stat()
		if e != nil || pinned.Sys().(*syscall.Stat_t).Dev != v.Sys().(*syscall.Stat_t).Dev {
			return errors.New("external scratch changed while opening")
		}
		*work = fmt.Sprintf("/proc/self/fd/%d", parent.Fd())
		if args[0] == "merge" {
			if !filepath.IsAbs(*out) || filepath.Clean(*out) != *out {
				return errors.New("absolute new --out required")
			}
			outputParent, e := os.Open(filepath.Dir(*out))
			if e != nil {
				return e
			}
			defer outputParent.Close()
			outputInfo, e := outputParent.Stat()
			if e != nil || !outputInfo.IsDir() || outputInfo.Sys().(*syscall.Stat_t).Dev != v.Sys().(*syscall.Stat_t).Dev {
				return errors.New("NAS merged archive must stay on its verified external volume")
			}
			*out = fmt.Sprintf("/proc/self/fd/%d/%s", outputParent.Fd(), filepath.Base(*out))
		}
		if args[0] == "pack" {
			return errors.New("pack is offline fixture tooling; NAS uses backup")
		}
	}
	tmp, e := os.MkdirTemp(*work, ".agent-check-")
	if e != nil {
		return e
	}
	defer os.RemoveAll(tmp)
	var key age.Identity
	if *identity != "" {
		b, e := os.ReadFile(*identity)
		if e != nil {
			return e
		}
		keys, e := age.ParseIdentities(strings.NewReader(string(b)))
		if e != nil || len(keys) != 1 {
			return errors.New("exactly one legacy age identity required")
		}
		key = keys[0]
	}
	if args[0] == "pack" {
		if *out == "" || f.NArg() == 0 || (*scope != "fixture" && *scope != "vps/gateway") {
			return errors.New("pack requires --out, source roots and fixture or vps/gateway scope")
		}
		var sources []Source
		for _, p := range f.Args() {
			if !filepath.IsAbs(p) || filepath.Clean(p) != p || p == "/" {
				return errors.New("absolute source roots required")
			}
			sources = append(sources, Source{Path: p, Target: "rootfs/" + strings.TrimPrefix(p, "/"), Service: *scope, Skip: transient})
		}
		m, blobs, e := ScanContext(ctx, sources, *scope)
		if e != nil {
			return e
		}
		if e = WriteContext(ctx, *out, m, blobs, nil); e != nil {
			return e
		}
		_, e = ChainContext(ctx, []string{*out}, tmp, nil)
		return e
	}
	if args[0] == "merge" {
		if *out == "" {
			return errors.New("--out required")
		}
		// Merge's legacy temporary blobs use the caller's explicit external parent.
		if e = os.Setenv("TMPDIR", *work); e != nil {
			return e
		}
		return Merge(f.Args(), key, *out)
	}
	if args[0] != "verify" && args[0] != "restore" {
		return errors.New("unknown command")
	}
	m, e := ChainContext(ctx, f.Args(), tmp, key)
	if e != nil {
		return e
	}
	if args[0] == "restore" {
		if *out == "" || !filepath.IsAbs(*out) || filepath.Clean(*out) != *out {
			return errors.New("absolute new --out required")
		}
		if e = checkRestoreFS(filepath.Dir(*out)); e != nil {
			return e
		}
		if e = Materialize(m, tmp, *out); e != nil {
			return e
		}
		if *ownership {
			if os.Geteuid() != 0 {
				return errors.New("ownership restoration requires root; isolated files retained")
			}
			for _, en := range m.Entries {
				u, e := user.Lookup(en.User)
				if e != nil {
					return fmt.Errorf("restore identity %s first: %w", en.User, e)
				}
				g, e := user.LookupGroup(en.Group)
				if e != nil {
					return fmt.Errorf("restore group %s first: %w", en.Group, e)
				}
				uid, e := strconv.Atoi(u.Uid)
				if e != nil {
					return e
				}
				gid, e := strconv.Atoi(g.Gid)
				if e != nil {
					return e
				}
				if e = os.Lchown(filepath.Join(*out, filepath.FromSlash(en.Path)), uid, gid); e != nil {
					return e
				}
			}
		}
	}
	fmt.Printf("Verified %s: %d entries, scope %s; isolatedRestore=%t\n", m.ID, len(m.Entries), m.Scope, args[0] == "restore")
	return nil
}
