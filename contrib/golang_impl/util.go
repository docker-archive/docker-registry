package main

import (
	"fmt"
	"io"
	"os"
	"path/filepath"
	"time"
)

func writeFile(path string, r io.ReadCloser) (e error) {
	started := time.Now()
	logger.Info("writing to ", path)
	e = os.MkdirAll(filepath.Dir(path), 0755)
	if e != nil {
		return
	}

	tmpName := path + ".tmp"
	out, e := os.Create(tmpName)
	if e != nil {
		return
	}
	defer out.Close()
	cnt, e := io.Copy(out, r)
	if e != nil {
		return
	}
	logger.Info(fmt.Sprintf("Wrote %d bytes in %.06f", cnt, time.Now().Sub(started).Seconds()))
	e = os.Rename(tmpName, path)
	return
}
