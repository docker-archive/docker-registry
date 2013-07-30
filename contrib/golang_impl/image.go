package main

import (
	"encoding/json"
	"io/ioutil"
	"path/filepath"
)

type Image struct {
	Dir string
}

func (i *Image) Id() (id string) {
	return filepath.Base(i.Dir)
}

func (i *Image) LayerPath() (id string) {
	return i.Dir + "/layer"
}

func (i *Image) Ancestry() (a []string) {
	a = []string{i.Id()}
	current := i
	for {
		atts, err := current.Attributes()
		if err != nil {
			logger.Error(err.Error())
			break
		}
		if atts.Parent != "" {
			a = append(a, atts.Parent)
			current = &Image{filepath.Dir(current.Dir) + "/" + atts.Parent}
		} else {
			break
		}
	}
	return
}

func (i *Image) Attributes() (a *ImageAttributes, err error) {
	a = &ImageAttributes{}
	path := i.Dir + "/json"
	logger.Debug("reading attributes from path", path)
	if data, err := ioutil.ReadFile(path); err == nil {
		err = json.Unmarshal(data, a)
	}
	return
}

type ImageAttributes struct {
	Id, Parent, Container string
}
