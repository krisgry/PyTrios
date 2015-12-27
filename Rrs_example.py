#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Example/Template for pytrios use

This is a partially tested configuration of the revamped library (Dec 2015)
Works for a set of SAM sensors connected through an IPS box.
Other uses may very well be buggy! Please file issues on github.

Call from command line with option -h for help

Enjoy--
"""
from __future__ import print_function
import pytrios.PyTrios as ps
import pytrios.ramses_calibrate as rcal
import sys
import time
import datetime
import argparse
from numpy import arange
import matplotlib.pyplot as plt
# force mathtext to use sans serif
plt.rcParams['mathtext.fontset'] = 'stixsans'
plt.rcParams['mathtext.default'] = 'regular'


def run(args):
    if args.calpath is not None:
        try:
            caldict = rcal.importCalFiles(args.calpath)
        except Exception, m:
            print("Failed to import calibration files:\n{0}".format(m),
                  file=sys.stderr)
            sys.exit(1)

    coms = ps.TMonitor(args.COM, baudrate=9600)

    # set verbosity for com channel (com messages / errors)
    # 0/1/2/3/4 = none, errors, queries(default), measurements, all
    coms[0].verbosity = args.vcom

    # identify connected instruments
    ps.TCommandSend(coms[0], commandset=None, command='query')
    time.sleep(0.25)  # wait for query results

    # identify SAM instruments from identified channels
    tk = ps.tchannels.keys()
    tc = ps.tchannels
    sams = [k for k in tk if ps.tchannels[k].TInfo.ModuleType == 'SAM']  # keys
    chns = [tc[k].TInfo.TID for k in sams]  # channel addressing
    sns = [tc[k].TInfo.serialn for k in sams]  # sensor ids
    print("found SAM modules: {0}".format(zip(chns, sns)), file=sys.stdout)

    if len(sams) == 0:
        ps.TClose(coms)
        raise Exception("no SAM modules found")

    for s in sams:
        tc[s].verbosity = args.vcom  # set verbosity level for each sensor

    for go in range(10):  # 10 measurements
        for s in sams:
            lasttrigger = datetime.datetime.now()
            if args.inttime > 0:
                # trigger single measurement at fixed integration time
                tc[s].startIntSet(coms[0], args.inttime, trigger=lasttrigger)
            else:
                # trigger single measurement at auto integration time
                tc[s].startIntAuto(coms[0], trigger=lasttrigger)

        # follow progress
        npending = len(sams)
        while npending > 0:
            nfinished = sum([1 for s in sams if tc[s].is_finished()])
            npending = sum([1 for s in sams if tc[s].is_pending()])
            # print(nfinished, npending)
            time.sleep(0.05)

        # how long did the longest of the set take?
        delays = [tc[s].TSAM.lastRawSAMTime - lasttrigger for s in sams]
        delaysec = max([d.total_seconds() for d in delays])

        print("\t{0} spectra received, triggered at {1} ({2} s)"
              .format(nfinished, lasttrigger, delaysec), file=sys.stdout)

        if nfinished == len(sams):
            print("{0} --- All triggered measurements received".format(go),
                  file=sys.stdout)

        if nfinished == 0:
            # no response? re-send query to see who is still talking
            ps.TCommandSend(coms[0], commandset=None, command='query')
            time.sleep(0.25)  # wait for query results
            # identify SAM instruments from identified channels
            tk = ps.tchannels.keys()
            tc = ps.tchannels
            sams = [k for k in tk if ps.tchannels[k].TInfo.ModuleType == 'SAM']
            chns = [tc[k].TInfo.TID for k in sams]  # channel addressing
            sns = [tc[k].TInfo.serialn for k in sams]  # sensor ids
            print("found SAM modules: {0}".format(zip(chns, sns)),
                  file=sys.stdout)

        else:
            # gather succesful results
            specs = [tc[s].TSAM.lastRawSAM
                     for s in sams if tc[s].is_finished()]
            sids = [tc[s].TInfo.serialn
                    for s in sams if tc[s].is_finished()]

            if args.calpath is not None:  # get calibrated spectra
                cspecs = []
                wlOut = arange(320, 955, 3.3)
                for spec, sid in zip(specs, sids):
                    csp = rcal.raw2cal_intercal(spec, lasttrigger,
                                                sid, caldict,
                                                wlOut=wlOut)
                    cspecs.append(csp)

            # plot results
            plt.ion()
            fig = plt.figure(1)
            fig.clf()
            ax1 = fig.add_axes((0.1, 0.1, 0.8, 0.8))
            if args.calpath is not None:  # get calibrated spectra
                p = [ax1.plot(wlOut, cs, label=sid)
                     for cs, sid in zip(cspecs, sids)]
            else:
                p = [ax1.plot(sp, label=sid)
                     for sp, sid in zip(specs, sids)]
            plt.title("spectrum {0} at {1}".format(go, lasttrigger))
            plt.legend()
            plt.draw()
            plt.pause(0.01)

    # close COM connections and listening threads cleanly
    ps.TClose(coms)

    raw_input('Press enter to close')


if __name__ == '__main__':
    prog = "pytrios version {0} by {1} ({2})".format(ps.__version__,
                                                     ps.__author__,
                                                     ps.__license__)
    example = 'Rrs_example 4 5 6 -vcom 1 -vchn 4'
    parser = argparse.ArgumentParser(description=None, epilog=example)
    parser.add_argument('-COM', nargs='+', type=int, default=4,
                        help='COM port or ports to watch')
    parser.add_argument("-vcom", type=int, choices=[0, 1, 2, 3, 4],
                        help="set verbosity on COM objects", default=1)
    parser.add_argument("-vchn", type=int, choices=[0, 1, 2, 3, 4],
                        help="set verbosity on channel objects", default=3)
    parser.add_argument("-errorlog", type=str,
                        help="error logfile path (not yet implemented)")
    parser.add_argument("-rawout", type=str,
                        help="raw data output file path (not yet implemented)")
    parser.add_argument("-calout", type=str,
                        help="calibrated data output file path (not yet implmented)")
    parser.add_argument("-calpath", type=str, default=None,
                        help="path to search for calibration files")
    parser.add_argument("-inttime", type=int, default=0,
                        choices=[0, 4, 8, 16, 32, 64, 128, 256, 512, 1024,
                                 2048, 4096, 8192],
                        help="Integration time in ms (0 = Auto)")
    args = parser.parse_args()
    run(args)
