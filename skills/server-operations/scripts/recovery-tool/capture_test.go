package main

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestDataCaptureExcludesRuntime(t *testing.T) {
	root := t.TempDir()
	app := filepath.Join(root, "aura")
	files := map[string]string{
		"data/aura.sqlite":                  "database fixture",
		"data/assets/aa/photo.pth":          "user original with model-like extension",
		"data/incoming/upload.bin":          "acknowledged upload",
		"data/derived/photo-dino.json":      "per-photo vector",
		"data/work/pending":                 "durable work",
		"config/private.json":               "private fixture",
		"current-commit":                    "source fixture",
		"bin/aura":                          "rebuildable program",
		"bin/dino/model.pth":                "downloadable weights",
		"bin/dino/.venv/lib/library.so":     "CUDA runtime",
		"bin/dino-eval/package-cache/wheel": "download cache",
		"bin/dino-eval/fixtures/photo.jpg":  "benchmark fixture",
		"staging/candidate/model.pth":       "deployment candidate",
		"backups/old":                       "historical backup",
		"releases/old":                      "program rollback",
	}
	for name, content := range files {
		path := filepath.Join(app, filepath.FromSlash(name))
		if err := os.MkdirAll(filepath.Dir(path), 0700); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(path, []byte(content), 0600); err != nil {
			t.Fatal(err)
		}
	}
	if err := os.Symlink("/unavailable/model", filepath.Join(app, "bin/dino/external")); err != nil {
		t.Fatal(err)
	}
	sources := coldSources(Config{Apps: []App{{ID: "aura", Root: app}}})
	size, err := sourceBytes(sources)
	if err != nil {
		t.Fatal(err)
	}
	expected := int64(0)
	for path, content := range files {
		if strings.HasPrefix(path, "data/") || strings.HasPrefix(path, "config/") || path == "current-commit" {
			expected += int64(len(content))
		}
	}
	if size != expected {
		t.Fatalf("preflight included runtime: %d vs %d", size, expected)
	}
	manifest, blobs, err := Scan(sources, "fixture")
	if err != nil {
		t.Fatal(err)
	}
	seen := map[string]bool{}
	for _, entry := range manifest.Entries {
		rel := strings.TrimPrefix(entry.Path, sources[0].Target+"/")
		seen[rel] = true
		if entry.Kind == "file" && blobs[entry.Hash] == "" {
			t.Fatalf("missing blob: %s", rel)
		}
	}
	for path := range files {
		want := strings.HasPrefix(path, "data/") || strings.HasPrefix(path, "config/") || path == "current-commit"
		if seen[path] != want {
			t.Fatalf("capture %s: got %v want %v", path, seen[path], want)
		}
	}
	// Exercise package verification and materialization as well as scan selection.
	archive := filepath.Join(root, "package.tar.gz")
	if err = Write(archive, manifest, blobs, nil); err != nil {
		t.Fatal(err)
	}
	blobDir := filepath.Join(root, "blobs")
	if err = os.Mkdir(blobDir, 0700); err != nil {
		t.Fatal(err)
	}
	verified, err := Read(archive, blobDir, nil)
	if err != nil {
		t.Fatal(err)
	}
	out := filepath.Join(root, "restored")
	if err = Materialize(verified, blobDir, out); err != nil {
		t.Fatal(err)
	}
	for path, content := range files {
		if !seen[path] {
			continue
		}
		got, err := os.ReadFile(filepath.Join(out, sources[0].Target, path))
		if err != nil || string(got) != content {
			t.Fatalf("restore %s: %v", path, err)
		}
	}
	if _, err = os.Lstat(filepath.Join(out, sources[0].Target, "bin")); !os.IsNotExist(err) {
		t.Fatal("runtime included in package")
	}
}

func TestRetainedRuntimeBoundary(t *testing.T) {
	cases := map[string]bool{
		"/var/lib/server-upgrades/aura/release/bin":                 true,
		"/var/lib/server-upgrades/aura/release/bin/dino/model.pth":  true,
		"/var/lib/server-upgrades/aura/release/data/bin/original":   false,
		"/var/lib/server-upgrades/aura/release/data/photo.pth":      false,
		"/var/lib/server-upgrades/aura/release/config/private.json": false,
		"/opt/aura/data/bin": false,
	}
	for path, want := range cases {
		if got := retainedRuntime(path); got != want {
			t.Errorf("%s: %v want %v", path, got, want)
		}
	}
	root := t.TempDir()
	if err := os.WriteFile(filepath.Join(root, "fixture"), []byte("fixture"), 0600); err != nil {
		t.Fatal(err)
	}
	entries, err := os.ReadDir(root)
	if err != nil {
		t.Fatal(err)
	}
	source := coldSources(Config{Shared: []string{"/var/lib/server-upgrades"}})[0]
	for _, rel := range []string{"aura/release/bin/dino/model.pth", "aura/release/data/photo.pth", "aura/release/config/private.json", "aura/release/snapshot.json"} {
		want := strings.HasPrefix(rel, "aura/release/bin/")
		if got := source.Skip(rel, entries[0]); got != want {
			t.Errorf("shared snapshot capture %s: %v want %v", rel, got, want)
		}
	}
}
