#!/usr/bin/env python

import numpy as np
from numpy.linalg import norm, inv
import argparse
import os, warnings, sys
with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=FutureWarning)
    import nibabel as nib

PRECISION= 17
np.set_printoptions(precision= PRECISION)


def read_bvecs(bvec_file):

    with open(bvec_file, 'r') as f:
        bvecs = [[float(num) for num in line.split()] for line in f.read().split('\n') if line]

    # bvec_file can be 3xN or Nx3
    # we want to return as Nx3
    if len(bvecs) == 3:
        bvecs = tranpose(bvecs)

    return bvecs


def read_bvals(bval_file):

    with open(bval_file, 'r') as f:
        bvals = [float(num) for num in f.read().split()]

    # bval_file can be 1 line or N lines
    return bvals

def tranpose(bvecs):

    # bvecs_T = matrix(list(map(list, zip(*bvecs))))
    bvecs_T = list(map(list, zip(*bvecs)))

    return bvecs_T

def bvec_scaling(bval, bvec, b_max):
    
    if bval:
        factor= np.sqrt(bval/b_max)
        if norm(bvec)!=factor:
            bvec= np.array(bvec)*factor

    # bvec= [str(np.round(x, precision)) for x in bvec]
    bvec= [str(x) for x in bvec]

    return ('   ').join(bvec)


def matrix_string(A):
    # A= np.array(A)
    
    A= str(A.tolist())
    A= A.replace(', ',',')
    A= A.replace('],[',') (')
    return '('+A[2:-2]+')'
    

def main():

    parser = argparse.ArgumentParser(description='NIFTI to NHDR conversion tool setting byteskip = -1')
    parser.add_argument('--nifti', type=str, required=True, help='nifti file')
    parser.add_argument('--bval', type=str, help='bval file')
    parser.add_argument('--bvec', type=str, help='bvec file')
    parser.add_argument('--nhdr', type=str, help='output nhdr file')

    args = parser.parse_args()

    if args.nifti.endswith('.gz'):
        encoding = 'gzip'
    elif args.nifti.endswith('.nii'):
        encoding = 'raw'
    else:
        raise ValueError('Invalid nifti file')

    img= nib.load(args.nifti)
    hdr= img.header

    if not args.nhdr:
        args.nhdr= os.path.abspath(args.nifti).split('.')[0]
    elif not args.nhdr.endswith('nhdr'):
        raise AttributeError('Output file must be nhdr')
    else:
        args.nhdr= os.path.abspath(args.nhdr)

    f= open(os.path.abspath(args.nhdr), 'w')
    console= sys.stdout
    sys.stdout= f

    dim= hdr['dim'][0]
    dtype= hdr.get_data_dtype()
    np_to_nrrd = {
        'int8': 'int8',
        'int16': 'short',
        'int32': 'int',
        'int64': 'longlong',
        'uint8': 'uchar',
        'uint16': 'ushort',
        'uint32': 'uint',
        'uint64': 'ulonglong',
        'float32': 'float',
        'float64': 'double'
        }

    print(f'NRRD0005\n# This nhdr file was generated by pnl.bwh.harvard.edu pipeline\n\
# See https://github.com/pnlbwh for more info\n\
# Complete NRRD file format specification at:\n\
# http://teem.sourceforge.net/nrrd/format.html\n\
type: {np_to_nrrd[dtype.name]}\ndimension: {dim}\nspace: right-anterior-superior')

    sizes= hdr['dim'][1:dim+1]
    print('sizes: {}'.format((' ').join(str(x) for x in sizes)))

    spc_dir= hdr.get_qform()[0:3,0:3].T

    # most important key
    print('byteskip: -1')

    endian= 'little' if dtype.byteorder=='<' else 'big'
    print(f'endian: {endian}')
    print(f'encoding: {encoding}')
    print('space units: "mm" "mm" "mm"')

    spc_orig= hdr.get_qform()[0:3,3]
    print('space origin: ({})'.format((',').join(str(x) for x in spc_orig)))

    print('data file: ', args.nifti)

    if dim==4:
        print(f'space directions: {matrix_string(spc_dir)} none')
        print('centerings: cell cell cell ???')
        print('kinds: space space space list')

        affine_det= np.linalg.det(hdr.get_qform())
        if affine_det < 0:
            mf = np.eye(3, dtype= 'int')
        elif affine_det > 0:
            mf = np.array([[-1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype= 'int')

        # mf = spc_dir @ inv(np.diag(hdr['pixdim'][1:4]))
        print(f'measurement frame: {matrix_string(mf)}')

        bvecs = read_bvecs(args.bvec)
        bvals = read_bvals(args.bval)

        print('modality:=DWMRI')

        b_max = max(bvals)
        print(f'DWMRI_b-value:={b_max}')
        for ind in range(len(bvals)):
            scaled_bvec = bvec_scaling(bvals[ind], bvecs[ind], b_max)
            print(f'DWMRI_gradient_{ind:04}:={scaled_bvec}')

    else:
        print(f'space directions: {matrix_string(spc_dir)}')
        print('centerings: cell cell cell')
        print('kinds: space space space')

        
    f.close()
    sys.stdout= console


if __name__ == '__main__':
    main()
