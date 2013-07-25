GIT_COMMIT = $(shell git rev-parse --short HEAD)
GIT_STATUS = $(shell test -n "`git status --porcelain`" && echo "+CHANGES")

all:
	go build -a -ldflags "-X main.GITCOMMIT $(GIT_COMMIT)$(GIT_STATUS)" -o ./bin/docker-registry

test:
	@go get github.com/remogatto/prettytest
	go test -v
