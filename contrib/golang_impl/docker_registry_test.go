package main

import (
	"bytes"
	"github.com/remogatto/prettytest"
	"io/ioutil"
	"net/http"
	"net/http/httptest"
	"os"
	"regexp"
	"testing"
)

type testSuite struct {
	prettytest.Suite
}

func TestRunner(t *testing.T) {
	logger.Level = WARN
	prettytest.RunWithFormatter(
		t,
		new(prettytest.TDDFormatter),
		new(testSuite),
	)
}

func (t *testSuite) TestRegexp() {
	re := regexp.MustCompile("^/v(\\d+)/ping")
	str := re.FindAllStringSubmatch("/v1/ping", -1)
	t.True(len(str) > 0)
}

func (t *testSuite) TestRepositories() {
	dir, _ := os.Getwd()
	root := dir + "/fixtures/index"
	repo := &Repository{root + "/repositories/dynport/redis/"}
	tags := repo.Tags()
	t.Equal(tags["latest"], "e0acc43660ac918e0cd7f21f1020ee3078fec7b2c14006603bbc21499799e7d5")
}

func (t *testSuite) TestImage() {
	dir, _ := os.Getwd()
	root := dir + "/fixtures/index"
	image := &Image{root + "/images/e0acc43660ac918e0cd7f21f1020ee3078fec7b2c14006603bbc21499799e7d5"}
	atts, err := image.Attributes()
	if err != nil {
		t.Failed()
	}
	t.Equal(atts.Parent, "0e03f25112cd513ade7c194109217b9381835ac2298bd0ffb61d28fbe47081a8")
	ancestry := image.Ancestry()
	t.Equal(len(ancestry), 3)
	t.Equal(ancestry[0], "e0acc43660ac918e0cd7f21f1020ee3078fec7b2c14006603bbc21499799e7d5")
	t.Equal(ancestry[1], "0e03f25112cd513ade7c194109217b9381835ac2298bd0ffb61d28fbe47081a8")
	t.Equal(ancestry[2], "8dbd9e392a964056420e5d58ca5cc376ef18e2de93b5cc90e868a1bbc8318c1c")
}

func resetTmpDataDir() string {
	dir, _ := os.Getwd()
	dataDir := dir + "/tmp/data"
	os.RemoveAll(dataDir)
	os.MkdirAll(dataDir, 0755)
	return dataDir
}

func (t *testSuite) TestWriteImageResource() {
	h := NewHandler(resetTmpDataDir())
	ser := httptest.NewServer(h)
	defer ser.Close()

	reader := bytes.NewReader([]byte("content"))
	req, _ := http.NewRequest("PUT", ser.URL+"/v1/images/1234/json", reader)
	client := http.Client{}
	rsp, _ := client.Do(req)

	t.Equal(rsp.StatusCode, 200)

	data, err := ioutil.ReadFile(h.DataDir + "/images/1234/json")
	if err != nil {
		logger.Error(err.Error())
	}
	t.Equal(string(data), "content")
}

func (t *testSuite) TestPutRepositoryTag() {
	h := NewHandler(resetTmpDataDir())
	ser := httptest.NewServer(h)
	defer ser.Close()

	reader := bytes.NewReader([]byte("thetag"))
	req, _ := http.NewRequest("PUT", ser.URL+"/v1/repositories/dynport/test/tags/latest", reader)
	client := http.Client{}
	rsp, _ := client.Do(req)

	t.Equal(rsp.StatusCode, 200)

	data, err := ioutil.ReadFile(h.DataDir + "/repositories/dynport/test/tags/latest")
	if err != nil {
		logger.Error(err.Error())
	}
	t.Equal(string(data), "thetag")
}

func (t *testSuite) TestPutRepositoryImages() {
	h := NewHandler(resetTmpDataDir())
	ser := httptest.NewServer(h)
	defer ser.Close()

	reader := bytes.NewReader([]byte("imagesdata"))
	req, _ := http.NewRequest("PUT", ser.URL+"/v1/repositories/dynport/test/images", reader)
	client := http.Client{}
	rsp, _ := client.Do(req)

	t.Equal(rsp.StatusCode, 204)

	data, err := ioutil.ReadFile(h.DataDir + "/repositories/dynport/test/images")
	if err != nil {
		logger.Error(err.Error())
	}
	t.Equal(string(data), "imagesdata")
}

func (t *testSuite) TestGetImageJson() {
	h := NewHandler(resetTmpDataDir())
	ser := httptest.NewServer(h)
	defer ser.Close()

	reader := bytes.NewReader([]byte("just a test"))
	req, _ := http.NewRequest("GET", ser.URL+"/v1/images/123/json", reader)
	client := http.Client{}
	rsp, _ := client.Do(req)

	t.Equal(rsp.StatusCode, 404)
}

func (t *testSuite) TestPutRepository() {
	h := NewHandler(resetTmpDataDir())
	ser := httptest.NewServer(h)
	defer ser.Close()

	reader := bytes.NewReader([]byte("just a test"))
	req, _ := http.NewRequest("PUT", ser.URL+"/v1/repositories/dynport/test/", reader)
	client := http.Client{}
	rsp, _ := client.Do(req)

	t.Equal(rsp.StatusCode, 200)

	data, err := ioutil.ReadFile(h.DataDir + "/repositories/dynport/test/_index")
	if err != nil {
		logger.Error(err.Error())
	}

	t.Equal(string(data), "just a test")
}

func (t *testSuite) TestReadFromServer() {
	dir, _ := os.Getwd()
	dataDir := dir + "/fixtures/index"
	h := NewHandler(dataDir)
	ser := httptest.NewServer(h)
	defer ser.Close()

	r, _ := http.Get(ser.URL + "/v1/_ping")
	t.Equal(r.StatusCode, 200)
	body, _ := ioutil.ReadAll(r.Body)
	r.Body.Close()
	t.Equal(string(body), "pong")
	t.Equal(r.Header.Get("X-Docker-Registry-Version"), "0.0.1")

	r, _ = http.Get(ser.URL + "/v1/images/e0acc43660ac918e0cd7f21f1020ee3078fec7b2c14006603bbc21499799e7d5/json")
	t.Equal(r.StatusCode, 200)
	t.Equal(r.Header.Get("X-Docker-Size"), "93")

	r, _ = http.Get(ser.URL + "/v1/images/e0acc43660ac918e0cd7f21f1020ee3078fec7b2c14006603bbc21499799e7d5/ancestry")
	t.Equal(r.StatusCode, 200)
}
