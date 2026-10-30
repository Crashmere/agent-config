package main

import (
	"os"
	"path/filepath"
	"testing"
)

func TestEscapedSystemdNameRoundTrip(t *testing.T) {
	if filepath.Separator != '/' {
		t.Skip("literal backslash filenames require POSIX paths")
	}
	root := t.TempDir()
	source := filepath.Join(root, "source")
	name := `dev-virtio\x2dports-org.qemu.guest_agent.0.device.wants`
	if err := os.MkdirAll(filepath.Join(source, name), 0755); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink("/usr/lib/systemd/system/qemu-guest-agent.service", filepath.Join(source, name, "qemu-guest-agent.service")); err != nil {
		t.Fatal(err)
	}
	m, blobs, err := Scan([]Source{{Path: source, Target: "rootfs/etc/systemd/system", Service: "vps"}}, "fixture")
	if err != nil {
		t.Fatal(err)
	}
	archive := filepath.Join(root, "package.tar.gz")
	if err := Write(archive, m, blobs, nil); err != nil {
		t.Fatal(err)
	}
	blobDir := filepath.Join(root, "blobs")
	if err := os.Mkdir(blobDir, 0700); err != nil {
		t.Fatal(err)
	}
	verified, err := Read(archive, blobDir, nil)
	if err != nil {
		t.Fatal(err)
	}
	out := filepath.Join(root, "restored")
	if err := Materialize(verified, blobDir, out); err != nil {
		t.Fatal(err)
	}
	link, err := os.Readlink(filepath.Join(out, "rootfs/etc/systemd/system", name, "qemu-guest-agent.service"))
	if err != nil || link != "/usr/lib/systemd/system/qemu-guest-agent.service" {
		t.Fatalf("restored systemd link: %q, %v", link, err)
	}
	for _, unsafe := range []string{"../escape", "/absolute", "rootfs/../../escape", "rootfs/../escape", "rootfs/\x00name"} {
		if validPath(unsafe) {
			t.Errorf("unsafe path accepted: %q", unsafe)
		}
	}
}
