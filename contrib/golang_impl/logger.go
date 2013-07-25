package main

import (
	"fmt"
)

type Logger struct {
	Level int
}

const (
	DEBUG = iota
	INFO
	WARN
	ERROR
)

func (l *Logger) Error(s ...interface{}) {
	if l.Level <= ERROR {
		str := fmt.Sprint(s...)
		fmt.Println("ERROR", str)
	}
}

func (l *Logger) Debug(s ...interface{}) {
	if l.Level <= DEBUG {
		str := fmt.Sprint(s...)
		fmt.Println("DEBUG", str)
	}
}

func (l *Logger) Info(s ...interface{}) {
	if l.Level <= INFO {
		str := fmt.Sprint(s...)
		fmt.Println("INFO", str)
	}
}
