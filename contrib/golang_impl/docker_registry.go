package main

import (
	"flag"
	"net/http"
)

var logger = &Logger{}

var (
	GITCOMMIT string
)


func startServer(listenOn, dataDir string) {
	logger.Info("using version ", GITCOMMIT)
	logger.Info("starting server on ", listenOn)
	logger.Info("using dataDir ", dataDir)
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
	flag.Parse()

	logger.Level = INFO
	if *doDebug {
		logger.Level = DEBUG
	}
	startServer(*listenOn, *dataDir)
}
