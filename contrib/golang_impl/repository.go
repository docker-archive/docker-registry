package main

import (
	"io/ioutil"
	"path/filepath"
	"strings"
)

type Repository struct {
	Dir string
}

func (r *Repository) Images() (b []byte, err error) {
	return ioutil.ReadFile(r.Dir + "/images")
}

func (r *Repository) ImagesPath() string {
	return r.Dir + "/images"
}

func (r *Repository) IndexPath() string {
	return r.Dir + "/_index"
}

func (r *Repository) Tags() (m map[string]string) {
	m = make(map[string]string)
	files, err := filepath.Glob(r.Dir + "/tags/*")
	if err != nil {
		return
	}
	for _, path := range files {
		name := filepath.Base(path)
		if data, err := ioutil.ReadFile(path); err == nil {
			m[name] = strings.Replace(string(data), `"`, "", -1)
		}
	}
	return
}
