// Package backup implements checksummed, content-addressed full and incremental archives.
// Archives never apply changes to a running system. Recovery materializes a new staging directory.
package main

import (
	"archive/tar"
	"bufio"
	"compress/gzip"
	"context"
	"crypto/rand"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"filippo.io/age"
	"fmt"
	"io"
	"io/fs"
	"os"
	"os/user"
	"path"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"syscall"
	"time"
)

type Entry struct {
	Path     string    `json:"path"`
	Service  string    `json:"service"`
	Kind     string    `json:"kind"`
	Hash     string    `json:"sha256,omitempty"`
	Link     string    `json:"link,omitempty"`
	Hardlink string    `json:"hardlinkGroup,omitempty"`
	Size     int64     `json:"size"`
	Mode     uint32    `json:"mode"`
	UID      int       `json:"uid"`
	GID      int       `json:"gid"`
	User     string    `json:"user"`
	Group    string    `json:"group"`
	Modified time.Time `json:"modified"`
}
type Manifest struct {
	Version      int               `json:"version"`
	ID           string            `json:"id"`
	Parent       string            `json:"parent,omitempty"`
	ParentHash   string            `json:"parentHash,omitempty"`
	Scope        string            `json:"scope"`
	Created      time.Time         `json:"created"`
	Entries      []Entry           `json:"entries"`
	Removed      []string          `json:"removed"`
	Notes        []string          `json:"notes"`
	Repositories map[string]string `json:"repositories"`
}
type Source struct {
	Path    string
	Target  string
	Service string
	Skip    func(string, fs.DirEntry) bool
}

const maxManifestBytes = 128 << 20

func NewID() string {
	b := make([]byte, 16)
	if _, e := rand.Read(b); e != nil {
		panic(e)
	}
	return time.Now().UTC().Format("20060102T150405Z") + "-" + hex.EncodeToString(b)
}
func Hash(m Manifest) string {
	b, _ := json.Marshal(m)
	h := sha256.Sum256(b)
	return hex.EncodeToString(h[:])
}
func validHash(s string) bool {
	if len(s) != 64 {
		return false
	}
	_, e := hex.DecodeString(s)
	return e == nil && s == strings.ToLower(s)
}
func validPath(s string) bool {
	return s != "" && path.Clean(s) == s && s != "." && !strings.HasPrefix(s, "/") && s != ".." && !strings.HasPrefix(s, "../") && !strings.ContainsAny(s, "\\\x00")
}
func Validate(m Manifest) error {
	if m.Version != 1 || m.ID == "" || len(m.Entries) > 200000 {
		return errors.New("unsupported manifest")
	}
	if (m.Parent == "") != (m.ParentHash == "") {
		return errors.New("invalid parent")
	}
	seen := map[string]string{}
	groups := map[string]Entry{}
	for _, e := range m.Entries {
		if !validPath(e.Path) || seen[e.Path] != "" || e.Size < 0 || e.Mode > 0777 {
			return errors.New("invalid entry")
		}
		if e.Kind != "file" && e.Kind != "directory" && e.Kind != "symlink" {
			return errors.New("invalid file kind")
		}
		if e.Kind == "file" && !validHash(e.Hash) {
			return errors.New("invalid hash")
		}
		if e.Hardlink != "" {
			if e.Kind != "file" {
				return errors.New("only regular files may share a hardlink group")
			}
			if first, ok := groups[e.Hardlink]; ok {
				if first.Hash != e.Hash || first.Size != e.Size || first.Mode != e.Mode || first.UID != e.UID || first.GID != e.GID || !first.Modified.Equal(e.Modified) {
					return errors.New("inconsistent hardlink group")
				}
			} else {
				groups[e.Hardlink] = e
			}
		}
		seen[e.Path] = e.Kind
	}
	for _, e := range m.Entries {
		for p := path.Dir(e.Path); p != "."; p = path.Dir(p) {
			if seen[p] != "" && seen[p] != "directory" {
				return errors.New("non-directory ancestor")
			}
		}
	}
	for _, p := range m.Removed {
		if !validPath(p) || seen[p] != "" {
			return errors.New("invalid deletion")
		}
	}
	return nil
}
func Scan(sources []Source, scope string) (Manifest, map[string]string, error) {
	return ScanContext(context.Background(), sources, scope)
}

func ScanContext(ctx context.Context, sources []Source, scope string) (Manifest, map[string]string, error) {
	m := Manifest{Version: 1, ID: NewID(), Created: time.Now().UTC(), Scope: scope, Entries: []Entry{}, Removed: []string{}, Repositories: map[string]string{}}
	blobs := map[string]string{}
	seen := map[string]bool{}
	// Historical media snapshots can reference one inode thousands of times.
	// Reuse only an unchanged hardlink's digest; archive writing hashes it again.
	type cachedDigest struct {
		info os.FileInfo
		hash string
	}
	digests := map[string]cachedDigest{}
	for _, src := range sources {
		err := filepath.WalkDir(src.Path, func(p string, d fs.DirEntry, err error) error {
			if e := ctx.Err(); e != nil {
				return e
			}
			if err != nil {
				return err
			}
			rel, e := filepath.Rel(src.Path, p)
			if e != nil {
				return e
			}
			if src.Skip != nil && src.Skip(rel, d) {
				if d.IsDir() {
					return filepath.SkipDir
				}
				return nil
			}
			target := path.Join(src.Target, filepath.ToSlash(rel))
			if seen[target] {
				return fmt.Errorf("duplicate source %s", target)
			}
			seen[target] = true
			i, e := d.Info()
			if e != nil {
				return e
			}
			en := Entry{Path: target, Service: src.Service, Mode: uint32(i.Mode().Perm()), Modified: i.ModTime(), Size: i.Size()}
			if st, ok := i.Sys().(*syscall.Stat_t); ok {
				if i.Mode().IsRegular() && st.Nlink > 1 {
					en.Hardlink = fmt.Sprintf("%x-%x", st.Dev, st.Ino)
				}
				en.UID = int(st.Uid)
				en.GID = int(st.Gid)
				if u, e := user.LookupId(strconv.Itoa(en.UID)); e == nil {
					en.User = u.Username
				}
				if g, e := user.LookupGroupId(strconv.Itoa(en.GID)); e == nil {
					en.Group = g.Name
				}
			}
			switch {
			case i.Mode().IsRegular():
				en.Kind = "file"
				cached, ok := digests[en.Hardlink]
				if en.Hardlink != "" && ok && os.SameFile(cached.info, i) && cached.info.Size() == i.Size() && cached.info.ModTime().Equal(i.ModTime()) {
					en.Hash = cached.hash
				} else {
					en.Hash, e = Digest(p)
				}
				if e != nil {
					return e
				}
				after, e := os.Lstat(p)
				if e != nil || !os.SameFile(i, after) || after.Size() != i.Size() || !after.ModTime().Equal(i.ModTime()) {
					return fmt.Errorf("source changed: %s", p)
				}
				if en.Hardlink != "" {
					digests[en.Hardlink] = cachedDigest{info: i, hash: en.Hash}
				}
				blobs[en.Hash] = p
			case i.IsDir():
				en.Kind = "directory"
				en.Size = 0
			case i.Mode()&os.ModeSymlink != 0:
				en.Kind = "symlink"
				en.Link, e = os.Readlink(p)
				if e != nil {
					return e
				}
				en.Size = 0
			default:
				return fmt.Errorf("unsupported special file: %s", p)
			}
			m.Entries = append(m.Entries, en)
			return nil
		})
		if err != nil {
			return m, nil, err
		}
	}
	sort.Slice(m.Entries, func(i, j int) bool { return m.Entries[i].Path < m.Entries[j].Path })
	return m, blobs, Validate(m)
}
func Delta(m *Manifest, parent Manifest) error {
	if err := Validate(parent); err != nil {
		return err
	}
	if m.Scope != parent.Scope {
		return errors.New("incremental scope differs from parent")
	}
	m.Parent = parent.ID
	m.ParentHash = Hash(parent)
	present := map[string]bool{}
	for _, e := range m.Entries {
		present[e.Path] = true
	}
	for _, e := range parent.Entries {
		if !present[e.Path] {
			m.Removed = append(m.Removed, e.Path)
		}
	}
	sort.Strings(m.Removed)
	return nil
}
func Write(out string, m Manifest, blobs map[string]string, parent *Manifest) error {
	return WriteContext(context.Background(), out, m, blobs, parent)
}

func WriteContext(ctx context.Context, out string, m Manifest, blobs map[string]string, parent *Manifest) error {
	if _, e := os.Lstat(out); !os.IsNotExist(e) {
		return errors.New("output already exists")
	}
	f, e := os.OpenFile(out+".part", os.O_CREATE|os.O_EXCL|os.O_WRONLY, 0600)
	if e != nil {
		return e
	}
	complete := false
	defer func() {
		f.Close()
		if !complete {
			os.Remove(out + ".part")
		}
	}()
	if e = WriteStream(ctx, f, m, blobs, parent); e != nil {
		return e
	}
	if e = f.Sync(); e != nil {
		return e
	}
	if e = f.Close(); e != nil {
		return e
	}
	if e = publishNoReplace(out+".part", out); e != nil {
		return e
	}
	complete = true
	return nil
}

func WriteStream(ctx context.Context, out io.Writer, m Manifest, blobs map[string]string, parent *Manifest) error {
	if e := Validate(m); e != nil {
		return e
	}
	b, e := json.MarshalIndent(m, "", "  ")
	if e != nil {
		return e
	}
	if len(b) > maxManifestBytes {
		return errors.New("manifest exceeds 128 MiB; reduce retained history or backup scope")
	}
	gz := gzip.NewWriter(out)
	tw := tar.NewWriter(gz)
	if e = tw.WriteHeader(&tar.Header{Name: "manifest.json", Mode: 0600, Size: int64(len(b))}); e != nil {
		return e
	}
	if _, e = tw.Write(b); e != nil {
		return e
	}
	old := map[string]bool{}
	if parent != nil {
		if m.Parent != parent.ID || m.ParentHash != Hash(*parent) {
			return errors.New("parent mismatch")
		}
		for _, x := range parent.Entries {
			if x.Kind == "file" {
				old[x.Hash] = true
			}
		}
	} else if m.Parent != "" {
		return errors.New("missing parent")
	}
	written := map[string]bool{}
	for _, en := range m.Entries {
		if en.Kind != "file" || old[en.Hash] || written[en.Hash] {
			continue
		}
		p, ok := blobs[en.Hash]
		if !ok {
			return fmt.Errorf("missing blob %s", en.Hash)
		}
		in, e := os.Open(p)
		if e != nil {
			return e
		}
		e = tw.WriteHeader(&tar.Header{Name: "blobs/" + en.Hash, Mode: 0600, Size: en.Size})
		if e != nil {
			in.Close()
			return e
		}
		h := sha256.New()
		n, e := io.Copy(tw, io.TeeReader(contextReader{ctx, in}, h))
		in.Close()
		if e != nil {
			return e
		}
		if n != en.Size || hex.EncodeToString(h.Sum(nil)) != en.Hash {
			return errors.New("source changed during archive")
		}
		written[en.Hash] = true
	}
	if e = tw.Close(); e != nil {
		return e
	}
	if e = gz.Close(); e != nil {
		return e
	}
	return nil
}

type contextReader struct {
	ctx context.Context
	r   io.Reader
}

func (r contextReader) Read(b []byte) (int, error) {
	if e := r.ctx.Err(); e != nil {
		return 0, e
	}
	return r.r.Read(b)
}

// Read accepts plain gzip archives and legacy age archives, checking all payloads.
func Read(file, blobDir string, identity age.Identity) (Manifest, error) {
	return ReadContext(context.Background(), file, blobDir, identity)
}

func ReadContext(ctx context.Context, file, blobDir string, identity age.Identity) (Manifest, error) {
	var m Manifest
	f, e := os.Open(file)
	if e != nil {
		return m, e
	}
	defer f.Close()
	reader := bufio.NewReader(f)
	header, e := reader.Peek(2)
	if e != nil {
		return m, e
	}
	var payload io.Reader = reader
	if header[0] != 0x1f || header[1] != 0x8b {
		if identity == nil {
			return m, errors.New("legacy encrypted backup requires --identity recovery.key")
		}
		payload, e = age.Decrypt(reader, identity)
		if e != nil {
			return m, e
		}
	}
	gz, e := gzip.NewReader(payload)
	if e != nil {
		return m, e
	}
	defer gz.Close()
	tr := tar.NewReader(gz)
	h, e := tr.Next()
	if e != nil || h.Name != "manifest.json" || h.Size > maxManifestBytes || h.Typeflag != tar.TypeReg {
		return m, errors.New("missing or oversized manifest")
	}
	b, e := io.ReadAll(tr)
	if e != nil {
		return m, e
	}
	if e = json.Unmarshal(b, &m); e != nil {
		return m, e
	}
	if e = Validate(m); e != nil {
		return m, e
	}
	expected := map[string]int64{}
	for _, en := range m.Entries {
		if en.Kind == "file" {
			if n, ok := expected[en.Hash]; ok && n != en.Size {
				return m, errors.New("conflicting sizes")
			}
			expected[en.Hash] = en.Size
		}
	}
	seen := map[string]bool{}
	if e = os.MkdirAll(blobDir, 0700); e != nil {
		return m, e
	}
	for {
		h, e = tr.Next()
		if e == io.EOF {
			break
		}
		if e != nil {
			return m, e
		}
		hash := strings.TrimPrefix(h.Name, "blobs/")
		size, ok := expected[hash]
		if h.Typeflag != tar.TypeReg || h.Name != "blobs/"+hash || !validHash(hash) || !ok || seen[hash] || h.Size != size {
			return m, errors.New("unexpected archive member")
		}
		seen[hash] = true
		tmp, e := os.CreateTemp(blobDir, ".blob-")
		if e != nil {
			return m, e
		}
		hasher := sha256.New()
		n, err := io.Copy(io.MultiWriter(tmp, hasher), contextReader{ctx, tr})
		if err == nil {
			err = tmp.Sync()
		}
		ce := tmp.Close()
		if err == nil {
			err = ce
		}
		if err == nil && (n != size || hex.EncodeToString(hasher.Sum(nil)) != hash) {
			err = errors.New("blob checksum mismatch")
		}
		if err != nil {
			os.Remove(tmp.Name())
			return m, err
		}
		if e = os.Rename(tmp.Name(), filepath.Join(blobDir, hash)); e != nil {
			os.Remove(tmp.Name())
			return m, e
		}
	}
	// Drain the gzip checksum and, for legacy archives, the age authentication tag.
	if _, e = io.Copy(io.Discard, contextReader{ctx, gz}); e != nil {
		return m, e
	}
	if _, e = io.Copy(io.Discard, contextReader{ctx, payload}); e != nil {
		return m, e
	}
	return m, nil
}
func Chain(files []string, blobDir string, identity age.Identity) (Manifest, error) {
	return ChainContext(context.Background(), files, blobDir, identity)
}

func ChainContext(ctx context.Context, files []string, blobDir string, identity age.Identity) (Manifest, error) {
	var prev Manifest
	for i, f := range files {
		m, e := ReadContext(ctx, f, blobDir, identity)
		if e != nil {
			return m, e
		}
		if i == 0 {
			if m.Parent != "" {
				return m, errors.New("first archive must be a full backup")
			}
		} else {
			if m.Parent != prev.ID || m.ParentHash != Hash(prev) || m.Scope != prev.Scope {
				return m, errors.New("broken or reordered backup chain")
			}
			want := m
			want.Removed = nil
			if e = Delta(&want, prev); e != nil {
				return m, e
			}
			actual := append([]string{}, m.Removed...)
			sort.Strings(actual)
			if strings.Join(actual, "\x00") != strings.Join(want.Removed, "\x00") {
				return m, errors.New("deletion list mismatch")
			}
		}
		for _, en := range m.Entries {
			if en.Kind != "file" {
				continue
			}
			i, e := os.Stat(filepath.Join(blobDir, en.Hash))
			if e != nil || i.Size() != en.Size {
				return m, fmt.Errorf("missing content for %s", en.Path)
			}
		}
		prev = m
	}
	if len(files) == 0 {
		return prev, errors.New("no backup files")
	}
	return prev, nil
}
func Materialize(m Manifest, blobs, out string) error {
	if e := Validate(m); e != nil {
		return e
	}
	if e := os.Mkdir(out, 0700); e != nil {
		return e
	}
	// Files are created before symlinks, and no entry may have a symlink ancestor.
	hardlinks := map[string]string{}
	for _, en := range m.Entries {
		p := filepath.Join(out, filepath.FromSlash(en.Path))
		if e := os.MkdirAll(filepath.Dir(p), 0700); e != nil {
			return e
		}
		if en.Kind == "directory" {
			if e := os.MkdirAll(p, 0700); e != nil {
				return e
			}
		}
		if en.Kind != "file" {
			continue
		}
		if en.Hardlink != "" {
			if first, ok := hardlinks[en.Hardlink]; ok {
				if e := os.Link(first, p); e != nil {
					return e
				}
				continue
			}
			hardlinks[en.Hardlink] = p
		}
		in, e := os.Open(filepath.Join(blobs, en.Hash))
		if e != nil {
			return e
		}
		f, e := os.OpenFile(p, os.O_CREATE|os.O_EXCL|os.O_WRONLY, 0600)
		if e != nil {
			in.Close()
			return e
		}
		h := sha256.New()
		n, e := io.Copy(io.MultiWriter(f, h), in)
		in.Close()
		ce := f.Close()
		if e != nil {
			return e
		}
		if ce != nil {
			return ce
		}
		if n != en.Size || hex.EncodeToString(h.Sum(nil)) != en.Hash {
			return errors.New("restored checksum mismatch")
		}
		if e = os.Chmod(p, fs.FileMode(en.Mode)); e != nil {
			return e
		}
		if e = os.Chtimes(p, en.Modified, en.Modified); e != nil {
			return e
		}
	}
	for _, en := range m.Entries {
		if en.Kind == "symlink" {
			if e := os.Symlink(en.Link, filepath.Join(out, filepath.FromSlash(en.Path))); e != nil {
				return e
			}
		}
	}
	for i := len(m.Entries) - 1; i >= 0; i-- {
		en := m.Entries[i]
		if en.Kind == "directory" {
			p := filepath.Join(out, filepath.FromSlash(en.Path))
			if e := os.Chmod(p, fs.FileMode(en.Mode)); e != nil {
				return e
			}
		}
	}
	b, _ := json.MarshalIndent(m, "", "  ")
	return Atomic(filepath.Join(out, "manifest.json"), b, 0600)
}
func Merge(files []string, identity age.Identity, out string) error {
	d, e := os.MkdirTemp("", "agent-merge-")
	if e != nil {
		return e
	}
	defer os.RemoveAll(d)
	m, e := Chain(files, d, identity)
	if e != nil {
		return e
	}
	m.ID = NewID()
	m.Parent = ""
	m.ParentHash = ""
	m.Removed = []string{}
	m.Notes = append(m.Notes, "Merged as a standalone full archive; state timestamp preserved.")
	blobs := map[string]string{}
	for _, en := range m.Entries {
		if en.Kind == "file" {
			blobs[en.Hash] = filepath.Join(d, en.Hash)
		}
	}
	return Write(out, m, blobs, nil)
}
