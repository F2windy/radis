# -*- coding: utf-8 -*-
"""
Created on Sat Nov 14 19:40:53 2015

@author: Erwan

Performance test with pint
- 2 times slower than numpy on np.std(np.exp())

Import neq.phys.units to get access to:

Use:

from radis.phys.units import Q_
- a = Q_(np.array([5,4,2]),'cm')
- a.to_base_units()

"""

from __future__ import absolute_import
from __future__ import print_function
import numpy as np
import os
from pint import UnitRegistry, DimensionalityError

ureg = UnitRegistry()
ureg.load_definitions(os.path.join(os.path.dirname(__file__), 'units.txt'))
Q_ = ureg.Quantity

# %% Pint aware arrays


class uarray(np.ndarray):
    ''' Unit-aware array based on Pint
    
    Use
    ------
    
    a = uarray(np.linspace(10, 100, 10), 'Td')
    
    '''

    def __new__(cls, input_array, unit=None):
        # Input array is an already formed ndarray instance
        # We first cast to be our class type

        obj = np.asarray(input_array).view(cls)
        # add the new attribute to the created instance

        if unit is not None:
            obj = Q_(obj, unit)

        # Finally, we must return the newly created object:
        return obj

    def __array_finalize__(self, obj):
        # see InfoArray.__array_finalize__ for comments
        if obj is None:
            return
#        self.info = getattr(obj, 'info', None)

def conv2(quantity, fromunit, tounit):
    ''' Converts `quantity` from unit `fromunit` to unit `tounit`
    
    Input
    ------
    
    quantity: array
        quantity to convert
        
    fromunit, tounit: str
        input unit, output unit
    
    Note that the output is still non dimensional. We don't transform `quantity` 
    into a pint array (or neq.phys.uarray) because this may create a performance
    drop in computationaly-expensive task. Instead, we assume we know for 
    sure the units in which some of our quantities will be created, and just
    want to let the users choose another output unit 
    
    Input
    ------
    
    quantity: array, float, etc.
    
    fromunit: str
    
    tounit: str
    
    '''

    try:
        a = Q_(quantity,fromunit)
        a = a.to(tounit)
    except TypeError:
        if 'cm-1' in fromunit or 'cm-1' in tounit:
            raise TypeError('Use cm_1 instead of cm-1 else it triggers errors in '+\
                            'pint (symbolic unit converter)')
        else:
            raise
            
    return a.magnitude


def is_homogeneous(unit1, unit2):
    ''' Tells if unit1 and unit2 are homogeneous, using the Pint library
    
    Input
    --------
    
    unit1, unit2: str
        units 

    '''
    
    try:
        Q_(unit1) + Q_(unit2)
        return True
    except DimensionalityError:
        return False
    
# %% Emission density conversion functions (with changes from ~1/nm in ~1/cm-1)

def convert_emi2cm(j_nm, wavenum, Iunit0, Iunit):
    '''
    Convert spectral emission density in wavelength base (typically ~mW/cm3/sr/nm) 
    to spectral emission density in wavenumber base (~mW/cm3/sr/cm_1)
    
    Input
    ---------
    
    j_nm: array
        spectral emission density in Iunit0 unit (~ per wavelength) )
        
    wavenum: array (cm-1)
        wavenumber
        
    Iunit0: str
        unit (~ per wavelength) to convert from 
        
    Iunit: str
        unit (~ per wavenumber) to convert to

    Description
    --------

    We use a variable substitution:
            dλ/dν = - 1/ν**2        [in SI]
            dλ/dν = - 10^7 / ν**2   [nm -> cm-1]

    We want   Lν.dν = Lλ.dλ
    so        Lν = - Lλ * 1e7 / ν^2

    Validation
    --------

    >>> w_nm, j_nm = s.get('emisscoeff', 'nm', 'mW/cm2/sr/nm')
    >>> w_cm, j_cm = s.get('emisscoeff', 'cm', 'mW/cm2/sr/cm_1')
    >>> print(trapz(y_nm, x_nm))
    >>> print(trapz(y_cm, x_cm))

    Both integrals are to be the same

    '''

    if Q_(Iunit0) != Q_('mW/cm3/sr/nm'):  # Q_ makes sure 'mW/sr/cm3/nm' == 'mW/cm3/sr/nm'
        j_nm = conv2(j_nm, Iunit0, 'mW/cm3/sr/nm')

    # Convert ''mW/cm3/sr/nm' to 'mW/cm3/sr/cm_1'
    j_cm = j_nm * 1e7 / wavenum**2
    # note that we discard the - sign.
    # This means that one of the integrals `trapz(j_nm, wavelen)` or
    # `trapz(j_cm, wavenum)` will be < 0 as they are sorted in opposite order.
    # But both plots look alright

    # Convert to whatever was wanted
    j_cm = conv2(j_cm, 'mW/cm3/sr/cm_1', Iunit)

    return j_cm


def convert_emi2nm(j_cm, wavenum, Iunit0, Iunit):
    '''
    Convert spectral emission density in wavenumber base (typically ~mW/cm3/sr/cm_1) to 
    spectral radiance in wavelength base (~mW/cm3/sr/nm)

    Input
    ---------
    
    j_cm: array
        spectral emission density in Iunit0 unit (~ per wavenumber)
        
    wavenum: array (cm-1)
        wavenumber
        
    Iunit0: str
        unit (~ per wavenumber) to convert from 
        
    Iunit: str
        unit (~ per wavelength) to convert to
        
    Description
    --------

    We use a variable substitution:
            dλ/dν = - 1/ν**2        [in SI]
            dλ/dν = - 10^7 / ν**2   [nm -> cm-1]

    We want   Lν.dν = Lλ.dλ
    so        Lλ  = - Lν * 1e-7 * ν^2

    '''

    if Q_(Iunit0) != Q_('mW/cm3/sr/cm_1'):  
        j_cm = conv2(j_cm, Iunit0, 'mW/cm3/sr/cm_1')

    # Convert 'mW/cm3/sr/cm_1' to 'mW/cm3/sr/nm'
    j_nm = j_cm * 1e-7 * wavenum**2
    # note that we discard the - sign.
    # This means that one of the integrals `trapz(L_nm, wavelen)` or
    # `trapz(L_cm, wavenum)` will be < 0 as they are sorted in opposite order.
    # But both plots look alright

    # Convert to whatever was wanted
    j_nm = conv2(j_nm, 'mW/cm3/sr/nm', Iunit)

    return j_nm


# %% Radiance conversion functions (with changes from ~1/nm in ~1/cm-1)
    
def convert_rad2cm(l_nm, wavenum, Iunit0, Iunit):
    '''
    Convert spectral radiance in wavelength base (~1/nm) to spectral radiance in
    wavenumber base (~1/cm_1)
    
    Input
    ---------
    
    l_nm: array
        spectral radiance in yunit0 unit (~ per wavelength)
        
    wavenum: array (cm-1)
        wavenumber
        
    Iunit0: str
        unit (~ per wavelength) to convert from 
        
    Iunit: str
        unit (~ per wavenumber) to convert to

    Description
    --------

    We use a variable substitution:
            dλ/dν = - 1/ν**2        [in SI]
            dλ/dν = - 10^7 / ν**2   [nm -> cm-1]

    We want   Lν.dν = Lλ.dλ
    so        Lν = - Lλ * 1e7 / ν^2

    Validation
    --------

    >>> x_nm, y_nm = s.get('radiance_noslit', 'nm', 'mW/cm2/sr/nm')
    >>> x_cm, y_cm = s.get('radiance_noslit', 'cm', 'mW/cm2/sr/cm_1')
    >>> print(trapz(y_nm, x_nm))
    >>> print(trapz(y_cm, x_cm))

    Both integrals are to be the same

    '''

    if Q_(Iunit0) != Q_('mW/cm2/sr/nm'):  # Q_ makes sure 'mW/sr/cm2/nm' == 'mW/cm2/sr/nm'
        l_nm = conv2(l_nm, Iunit0, 'mW/cm2/sr/nm')

    # Convert ''mW/cm2/sr/nm' to 'mW/cm2/sr/cm_1'
    l_cm = l_nm * 1e7 / wavenum**2
    # note that we discard the - sign.
    # This means that one of the integrals `trapz(L_nm, wavelen)` or
    # `trapz(L_cm, wavenum)` will be < 0 as they are sorted in opposite order.
    # But both plots look alright

    # Convert to whatever was wanted
    l_cm = conv2(l_cm, 'mW/cm2/sr/cm_1', Iunit)

    return l_cm


def convert_rad2nm(l_cm, wavenum, Iunit0, Iunit):
    '''
    Convert spectral radiance in wavenumber base (~1/cm_1) to spectral radiance in
    wavelength base (~1/nm)

    Input
    ---------
    
    l_cm: array
        spectral radiance in yunit0 unit (~ per wavenumber)
        
    wavenum: array (cm-1)
        wavenumber
        
    Iunit0: str
        unit (~ per wavenumber) to convert from 
        
    Iunit: str
        unit (~ per wavelength) to convert to
        
    Description
    --------

    We use a variable substitution:
            dλ/dν = - 1/ν**2        [in SI]
            dλ/dν = - 10^7 / ν**2   [nm -> cm-1]

    We want   Lν.dν = Lλ.dλ
    so        Lλ  = - Lν * 1e-7 * ν^2

    '''

    if Q_(Iunit0) != Q_('mW/cm2/sr/cm_1'):  # Q_ makes sure 'mW/sr/cm2/cm_1' == 'mW/cm2/sr/cm_1'
        l_cm = conv2(l_cm, Iunit0, 'mW/cm2/sr/cm_1')

    # Convert 'mW/cm2/sr/cm_1' to 'mW/cm2/sr/nm'
    l_nm = l_cm * 1e-7 * wavenum**2
    # note that we discard the - sign.
    # This means that one of the integrals `trapz(L_nm, wavelen)` or
    # `trapz(L_cm, wavenum)` will be < 0 as they are sorted in opposite order.
    # But both plots look alright

    # Convert to whatever was wanted
    l_nm = conv2(l_nm, 'mW/cm2/sr/nm', Iunit)

    return l_nm


def convert_universal(I, from_unit, to_unit, w_cm,
                     per_nm_is_like='mW/sr/cm2/nm', per_cm_is_like='mW/sr/cm2/cm_1'):
    ''' Return variable var in whatever unit, and converts to to_unit
    Also deal with cases where var is in ~1/nm (per_nm_is_like) or ~1/cm-1
    (per_cm_is_like)

    Input
    ------

    var: str
        variable to get. Usually 'radiance' or 'radiance_noslit'

    to_unit: str
        unit to convert variable to

    '''
    Iunit0 = from_unit
    Iunit = to_unit
    try:
        if is_homogeneous(Iunit0, per_nm_is_like) and is_homogeneous(
                Iunit, per_cm_is_like):
            I = convert_rad2cm(I, w_cm, Iunit0, Iunit)
            # note that there may still be a new DimensionalityError
            # raise here if the input was non-sense.
        elif is_homogeneous(Iunit0, per_cm_is_like) and is_homogeneous(
                Iunit, per_nm_is_like):
            I = convert_rad2nm(I, w_cm, Iunit0, Iunit)
            # note that there may still be a new DimensionalityError
            # raise here if the input was non-sense.
        else:  # general case: just convert
            I = conv2(I, Iunit0, Iunit)
    except DimensionalityError:
        raise DimensionalityError(Iunit0, Iunit)

    return I


# %% Test

def _test(verbose=True, *args, **kwargs):

    b = True

    # Test unit-ware arrays
    a = uarray(np.linspace(10, 100, 10), 'Td')          # NeQ pint-aware array
    res = Q_(np.linspace(1e-16, 1e-15, 10), 'V * cm^2')  # pint definition

    b *= (np.round(np.array(a.to('V * cm^2')) - np.array(res), 5)
         == np.zeros_like(res)).all()
#    b = (print(a.to('V * cm^2'))==print(res))


    # Test conversion 
    convtable = [
            (500, 'nm', 0.5, 'µm'),
            (1, 'erg/s', 1e-7, 'W'),
            (1, 'm2',10000,'cm2')
            ]
    for a, f, r, t in convtable:
        cr = conv2(a, f, t)
        print(('{0} {1} = {2} {3}'.format(a, f, cr, t)))
        b *= np.isclose(cr,r)

    return bool(b)

if __name__ == '__main__':

    print((_test()))