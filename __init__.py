import numpy as np
from netCDF4 import Dataset

import sh
from collections import OrderedDict




class ncfile(object):
    '''
    Th class is initiated with original netCDF file object
    created by Dataset from netCDF4 package. The properties of the file
    are copied to the attributes of the class and cna be then saved together
    with data of the original file. The purpose is to be able to fix
    description of the netCDF file, like dimention names, attributes and so on,
    but to save the rest of the structure of the original file as much as
    possible.
    Initial version of the class is base on the code from here
    https://github.com/Unidata/netcdf4-python/blob/master/netCDF4/utils.py

    '''

    def __init__(self, ifile):

        self.ifile = ifile
        self.nchunk = 10
        self.istop = -1
        self.nchunk = 10
        self.istart = 0
        self.istop = -1

        # Read dimentions
        dims = OrderedDict()
        for dimname, dim in ifile.dimensions.items():
            dims[dimname] = OrderedDict()
            dims[dimname]['name'] = dim.name
            dims[dimname]['size'] = len(dim)
            dims[dimname]['isunlimited'] = dim.isunlimited()

        self.dims = dims

        # Read variable names
        varnames = ifile.variables.keys()

        # I am not sure what this fix is for...
        for dimname in ifile.dimensions.keys():
            if dimname in ifile.variables.keys() and dimname not in varnames:
                    varnames.append(dimname)

        self.varnames = varnames

        # Collect variables
        variab = OrderedDict()
        for varname in varnames:
            variab[varname] = OrderedDict()
            ncvar = ifile.variables[varname]
            variab[varname]['data'] = ncvar
            variab[varname]['dimentions']= ncvar.dimensions
            hasunlimdim = False
            # Check if dimention is unlimited
            for vdim in variab[varname]['dimentions']:
                if ifile.dimensions[vdim].isunlimited():
                    hasunlimdim = True
                    variab[varname]['unlimdimname'] = vdim
            variab[varname]['hasunlimdim'] = hasunlimdim
            variab[varname]['datatype'] =  ncvar.dtype

            if hasattr(ncvar, '_FillValue'):
                variab[varname]['FillValue'] = ncvar._FillValue
            else:
                variab[varname]['FillValue'] = None

            attdict = ncvar.__dict__
            if '_FillValue' in attdict: del attdict['_FillValue']
            variab[varname]['attributes'] = attdict

        self.variab = variab

    def add_dim(self, name, size, isunlimited=False):
        '''
        Add dimention to the list of dimentions already copied from the file.
        '''
        self.dims[name] = OrderedDict()
        self.dims[name]['name'] = name
        self.dims[name]['size'] = size
        self.dims[name]['isunlimited'] = isunlimited

    def rename_dim(self, oldname, newname, renameall = True):
        newdim = OrderedDict((newname if k == oldname else k, v) for k, v in
                             self.dims.viewitems())
        newdim[newname]['name'] = newname
        self.dims = newdim
        if renameall:
            for var in self.variab:
                vardims = self.variab[var]['dimentions']
                print vardims
                if oldname in vardims:
                    print 'find old name'
                    tempdim = list(vardims)
                    for i in range(len(tempdim)):
                        if tempdim[i] == oldname:
                            tempdim[i] = newname
                            print tempdim
                    self.variab[var]['dimentions'] = tuple(tempdim)

    def save(self, fname):

        try:
            sh.rm(fname)
        except:
            pass

        ncfile4 = Dataset(fname,'w',clobber=False,format='NETCDF4_CLASSIC')

        # Create dimentions
        for dim in self.dims.itervalues():
            #print(dim)
            if dim["isunlimited"]:
                ncfile4.createDimension(dim['name'],None)
                if self.istop == -1: self.istop=dim['size']
            else:
                ncfile4.createDimension(dim['name'],dim['size'])

        # Loop over variables
        for vari in self.variab:
            #print vari
            perem  = self.variab[vari]
            var = ncfile4.createVariable(vari,
                                         perem['datatype'],
                                         perem['dimentions'], \
                                         fill_value=perem['FillValue'],\
                                         complevel=1)

            attdict = perem['data'].__dict__
            if '_FillValue' in attdict: del attdict['_FillValue']
            var.setncatts(attdict)

            if perem['hasunlimdim']: # has an unlim dim, loop over unlim dim index.
                # range to copy
                if self.nchunk:
                    start = self.istart; stop = self.istop; step = self.nchunk
                    if step < 1: step = 1
                    for n in range(start, stop, step):
                        nmax = n+step
                        if nmax > self.istop: nmax=self.istop
                        idata = perem['data'][n:nmax]
                        var[n-self.istart:nmax-self.istart] = idata
                else:
                    idata = perem['data'][:]
                    var[0:len(unlimdim)] = idata

            else: # no unlim dim or 1-d variable, just copy all data at once.
                idata = perem['data'][:]
                var[:] = idata
            ncfile4.sync() # flush data to disk

        gattrs = self.ifile.ncattrs()
        for gatt in gattrs:
            setattr(ncfile4, gatt, getattr(self.ifile,gatt))


        ncfile4.close()


