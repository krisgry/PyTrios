@echo off
set tcom=4
set samples=3
set period=1
set vchn=1
set vcom=1
set calpath=calfiles
set caloutfile=cal.txt
set rawoutfile=raw.txt
set gps=13
set inttime=0

@echo on
python Rrs_example.py %tcom% -samples %samples% -period %period% -plotting -vchn %vchn% -vcom %vcom% -calpath %calpath% -calout %caloutfile% -rawout %rawoutfile% -GPS %gps% -inttime %inttime%

