package main

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"sync/atomic"
	"time"
)

type progressKey struct{}
type progress struct {
	phase  string
	total  atomic.Int64
	start  time.Time
	done   atomic.Int64
	output atomic.Int64
	stop   chan bool
}

// Progress counts input bytes; compression output is reported separately.
func startProgress(ctx context.Context, phase string, total int64) (context.Context, func(bool)) {
	p := &progress{phase: phase, start: time.Now(), stop: make(chan bool)}
	p.total.Store(total)
	closed := make(chan struct{})
	go func() {
		defer close(closed)
		ticker := time.NewTicker(10 * time.Second)
		defer ticker.Stop()
		last, lastTime := int64(0), p.start
		emit := func(state string) {
			now, done, total := time.Now(), p.done.Load(), p.total.Load()
			rate := float64(done-last) / now.Sub(lastTime).Seconds()
			if rate < 0 {
				rate = 0
			}
			event := map[string]any{"phase": phase, "state": state, "doneBytes": done, "totalBytes": total, "bytesPerSecond": rate, "elapsedSeconds": now.Sub(p.start).Seconds(), "outputBytes": p.output.Load(), "percent": nil, "etaSeconds": nil}
			if total > 0 {
				event["percent"] = min(100.0, 100*float64(done)/float64(total))
				if rate > 0 {
					event["etaSeconds"] = float64(max(0, total-done)) / rate
				}
			}
			b, _ := json.Marshal(event)
			fmt.Fprintln(os.Stderr, string(b))
			last, lastTime = done, now
		}
		emit("running")
		for {
			select {
			case <-ticker.C:
				emit("running")
			case success := <-p.stop:
				state := "failed"
				if success {
					state = "completed"
				}
				emit(state)
				return
			}
		}
	}()
	return context.WithValue(ctx, progressKey{}, p), func(success bool) { p.stop <- success; <-closed }
}

func inputProgress(ctx context.Context, n int) {
	if p, ok := ctx.Value(progressKey{}).(*progress); ok {
		p.done.Add(int64(n))
	}
}

func totalProgress(ctx context.Context, n int64) {
	if p, ok := ctx.Value(progressKey{}).(*progress); ok {
		p.total.Store(n)
	}
}

type progressWriter struct {
	ctx context.Context
	out interface{ Write([]byte) (int, error) }
}

func (w progressWriter) Write(b []byte) (int, error) {
	n, e := w.out.Write(b)
	if p, ok := w.ctx.Value(progressKey{}).(*progress); ok {
		p.output.Add(int64(n))
	}
	return n, e
}
