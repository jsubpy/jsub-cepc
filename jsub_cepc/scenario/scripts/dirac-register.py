#!/usr/bin/env python

import os

from DIRAC import S_OK, S_ERROR, gLogger, exit
from DIRAC.Core.Base import Script

Script.setUsageMessage('Register files to DFC')
Script.parseCommandLine(ignoreErrors=False)

from DIRAC.Core.Utilities.Adler import fileAdler
from DIRAC.Core.Utilities.File import makeGuid
from DIRAC.DataManagementSystem.Client.DataManager import DataManager

from DIRAC.Resources.Catalog.FileCatalogClient import FileCatalogClient
fcc = FileCatalogClient('DataManagement/FileCatalog')

files = Script.getPositionalArgs()

_bufferSize = 100
_se = 'IHEP-STORM'


def main():
    dm = DataManager()

    fileTupleBuffer = []

    counter = 0
    for f in files:
        counter += 1

        if not f.startswith('/cefs'):
            gLogger.error('File must be under "/cefs"')
            return 1

        lfn = '/cepc/lustre-ro' + f

        result = fcc.isFile(lfn)
        if result['OK'] and lfn in result['Value']['Successful'] and result['Value']['Successful'][lfn]:
            continue

        size = os.path.getsize(f)
        adler32 = fileAdler(f)
        guid = makeGuid()
        fileTuple = (lfn, f, size, _se, guid, adler32)
        fileTupleBuffer.append(fileTuple)
        gLogger.debug('Register to lfn: %s' % lfn)
        gLogger.debug('fileTuple: %s' % (fileTuple,))

        if len(fileTupleBuffer) >= _bufferSize:
            result = dm.registerFile(fileTupleBuffer)
            print('register result', result)
            if not result['OK']:
                gLogger.error('Register file failed')
                return 1
            del fileTupleBuffer[:]
            gLogger.debug('%s files registered' % counter)

    if fileTupleBuffer:
        result = dm.registerFile(fileTupleBuffer)
        print('register result', result)
        if not result['OK']:
            gLogger.error('Register file failed')
            return 1
        del fileTupleBuffer[:]

    gLogger.info('Totally %s files registered' % counter)
    return 0


if __name__ == '__main__':
    exit(main())
