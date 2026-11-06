package main

import (
	"context"
	"errors"
	"flag"
	"fmt"
	"log"
	"net/http"
	"net/netip"
	"os"
	"os/signal"
	"strconv"
	"strings"
	"syscall"
	"time"
)

func main() {
	listen := flag.String("listen", "", "Explicit private or loopback IPv4 address:port")
	peer := flag.String("peer", "", "Only allowed client IPv4 address")
	flag.Parse()
	address, err := netip.ParseAddrPort(*listen)
	if err != nil || !address.Addr().Is4() || address.Port() == 0 ||
		!(address.Addr().IsPrivate() || address.Addr().IsLoopback()) {
		log.Fatal("-listen must specify a private or loopback IPv4 address and nonzero port")
	}
	allowed, err := netip.ParseAddr(*peer)
	if err != nil || !allowed.Is4() || allowed.IsUnspecified() {
		log.Fatal("-peer must specify a nonzero IPv4 address")
	}
	if flag.NArg() != 0 {
		log.Fatal("unexpected positional arguments")
	}
	payload := strings.Repeat("0123456789abcdef", 1024)
	handler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		remote, err := netip.ParseAddrPort(r.RemoteAddr)
		if err != nil || remote.Addr().Unmap() != allowed {
			http.Error(w, "forbidden", http.StatusForbidden)
			return
		}
		if r.Method != http.MethodGet && r.Method != http.MethodHead {
			w.Header().Set("Allow", "GET, HEAD")
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}
		body := "udp-tunnel-probe-ok\n"
		switch r.URL.Path {
		case "/healthz":
		case "/payload":
			body = payload
		default:
			http.NotFound(w, r)
			return
		}
		w.Header().Set("Content-Type", "text/plain; charset=utf-8")
		w.Header().Set("Cache-Control", "no-store")
		w.Header().Set("Content-Length", strconv.Itoa(len(body)))
		w.WriteHeader(http.StatusOK)
		if r.Method == http.MethodGet {
			_, _ = fmt.Fprint(w, body)
		}
	})
	server := &http.Server{
		Addr: address.String(), Handler: handler, MaxHeaderBytes: 4096,
		ReadHeaderTimeout: 3 * time.Second, ReadTimeout: 5 * time.Second,
		WriteTimeout: 5 * time.Second, IdleTimeout: 10 * time.Second,
	}
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()
	result := make(chan error, 1)
	go func() { result <- server.ListenAndServe() }()
	log.Printf("synthetic probe listen=%s peer=%s", address, allowed)
	select {
	case err = <-result:
	case <-ctx.Done():
		shutdown, cancel := context.WithTimeout(context.Background(), 3*time.Second)
		defer cancel()
		if err := server.Shutdown(shutdown); err != nil {
			log.Printf("shutdown: %v", err)
			_ = server.Close()
		}
		err = <-result
	}
	if err != nil && !errors.Is(err, http.ErrServerClosed) {
		log.Fatal(err)
	}
}
