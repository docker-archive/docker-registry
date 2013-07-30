package main

import (
	"flag"
	"fmt"
	"io/ioutil"
	"net/http"
	"os"
	"os/signal"
	"strconv"
	"syscall"
)

var logger = &Logger{}

var (
	GITCOMMIT string
)

func createPidFile(pidFile string) error {
	if pidString, err := ioutil.ReadFile(pidFile); err == nil {
		pid, err := strconv.Atoi(string(pidString))
		if err == nil {
			if _, err := os.Stat(fmt.Sprintf("/proc/%d/", pid)); err == nil {
				return fmt.Errorf("pid file found, ensure docker-registry is not running or delete %s", pidFile)
			}
		}
	}

	file, err := os.Create(pidFile)
	if err != nil {
		return err
	}

	defer file.Close()

	_, err = fmt.Fprintf(file, "%d", os.Getpid())
	return err
}

func removePidFile(pidFile string) {
	if err := os.Remove(pidFile); err != nil {
		logger.Error("Error removing %s: %s", pidFile, err)
	}
}

func startServer(listenOn, dataDir string, pidFile string) {
	logger.Info("using version ", GITCOMMIT)
	logger.Info("starting server on ", listenOn)
	logger.Info("using dataDir ", dataDir)
	logger.Info("using pidFile", pidFile)

	if err := createPidFile(pidFile); err != nil {
		logger.Error(err)
		os.Exit(1)
	}
	defer removePidFile(pidFile)

	c := make(chan os.Signal, 1)
	signal.Notify(c, os.Interrupt, os.Kill, os.Signal(syscall.SIGTERM))
	go func() {
		sig := <-c
		logger.Debug("Received signal '%v', exiting\n", sig)
		removePidFile(pidFile)
		os.Exit(0)
	}()

	if err := http.ListenAndServe(listenOn, NewHandler(dataDir)); err != nil {
		logger.Error(err.Error())
	}
}

func main() {
	var listenOn *string
	var dataDir *string
	var doDebug *bool

	listenOn = flag.String("l", ":80", "Address on which to listen.")
	dataDir = flag.String("d", "/data/docker_index", "Directory to store data in")
	doDebug = flag.Bool("D", false, "set log level to debug")
	pidFile := flag.String("p", "/var/run/docker-registry.pid", "File containing process PID")
	flag.Parse()

	logger.Level = INFO
	if *doDebug {
		logger.Level = DEBUG
	}
	startServer(*listenOn, *dataDir, *pidFile)
}
