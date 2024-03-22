import cv2 as cv
import numpy as np
import tifffile as tf
import warnings
import os
from struct import unpack

''' Dictionary of the data type name and size according to data type flag '''
dm4_tagdtypes = {2: ("signed short", 2),
                 3: ("signed long", 2), 
                 4: ("unsigned short", 2), 
                 5: ("unsigned long", 4),
                 6: ("float", 4), 
                 7: ("double", 8),
                 8: ("boolean", 1), 
                 9: ("char", 1),
                 10: ("signed char", 1), 
                 11: ("long long", 8),
                 14: ("unknown", 0), 
                 15: ("group of data", 0),
                 18: ("string", 0), 
                 20: ("array or groups of data", 0)
                }

''' TIF file functions '''

def printTags(file_path):
    """
        Print all pages and tags on those pages from TIF file
    """
    tags = {}
    with tf.TiffFile(file_path) as tif:
        for page in tif.pages:
            print(f'Page: {page}')
            print('Name\tTag')
            for tag in page.tags:
                print(f'{page.tags[tag].name}:\t{page.tags[tag].value}')
                
    return tags


def getImageJScale(file_path):
    """
        Get the scale assuming it was written for ImageJ
        Returns: unit name, scale in x, scale in y
    """
    scales = {}
    with tf.TiffFile(file_path) as tif:
        descr  = tif.pages[0].tags['ImageDescription'].value
        unit   = descr[descr.find("unit")+5:]
        scalex = tif.pages[0].tags['XResolution'].value[0]/tif.pages[0].tags['XResolution'].value[1]
        scaley = tif.pages[0].tags['YResolution'].value[0]/tif.pages[0].tags['YResolution'].value[1]
    return unit, scalex, scaley

''' DM4 functions '''

def getDM4Endianness(file_path, verbose=False):
    """
        Open a DM4 file and determine endianness
        Optional 'verbose' parameter will print result
        Returns: '<' if big-endian or '>' if little-endian
    """
    with open(file_path, 'rb') as f:
        val = f.read(16)[-1] # position of flag
        if val == 0:
            if verbose:
                print('Big-endian')
            return '>' # big endian
        else:
            if verbose:
                print('Little-endian')
            return '<' # little endian

def getDM4Scale(file_path, endianness='<', verbose=False):
    """
        Open a DM4 file and determine the image scale
        Inputs: file, endianness (default: little), verbose
        Returns: scale, scale unit
    """
    scale = 0
    with open(file_path, 'rb') as f:
        # find file length so as to not run over it
        spos = 0
        f.seek(0, os.SEEK_END)
        size = f.tell()
        f.seek(0)
        
        # find the proper 'ImageData' tag
        image_data_pos = -1
        first_data_found = False
        while spos < size:
            chunk = f.read(1024)
            spos = f.tell()
            pos = chunk.find(b"ImageData")
            if pos > -1:
                if first_data_found:
                    image_data_pos = spos - 1024 + pos
                    break
                else:
                    first_data_found = True
            else:
                f.seek(f.tell() - 8) # to avoid the situation where 'ImageData' is split across chunks
                    
        # get chunk of data beginning with 'ImageData', find the right 'Scale' tag, and decode
        f.seek(image_data_pos)
        chunk = f.read(1024)
        pos = chunk.find(b"Scale")
        scale_chunk = chunk[pos:pos+37]
        
        # it's not the first scale tag but the third one
        for i in range(2):
            pos = chunk[pos+37:].find(b"Scale") + pos + 37
        
        scale_hex = chunk[pos+33:pos+37]
        
        scale = unpack(endianness + 'f', scale_hex)[0]
        
        # get unit label
        pos = chunk[pos:].find(b"Units") + pos + 41
        lbl_len = unpack('>Q', chunk[pos:pos+8])[0]
        lbl = ''
        for i in range(0, lbl_len*2, 2):
            lbl += chr(chunk[pos+8+i])
        if verbose:
            print(f"Scale: {scale} {lbl}")
    return scale, lbl

def getDM4Image(file_path, endianness='<', verbose=False):
    """
        Open a DM4 file and extract the image
        Inputs: file, endianness (default: little), verbose
        Returns: raw image, thumbnail image
    """
    with open(file_path, 'rb') as f:
        # find file length so as to not run over it
        spos = 0
        f.seek(0, os.SEEK_END)
        size = f.tell()
        f.seek(0)
        first = False
        # find the image 'Data' tag; the first is the thumbnail
        image_data_pos = -1
        first_data_found = False
        while spos < size:
            if spos + 1024 < size:
                   chunk = f.read(1024)
            else:
                chunk = f.read(size-spos)

            pos = chunk.find(b"\x15\x00\x04Data")
            if pos > -1:
                # get data header and data bytes
                f.seek(spos + pos)
                tag_header = f.read(19)
                tlen = unpack('>q', tag_header[7:15])[0]
                ninfo = unpack('>q', f.read(8))[0]
                tdtype = f.read(8)[-1]
                dtype = f.read(8)[-1]
                narray = unpack('>q', f.read(8))[0]
                image_bytes = f.read(narray*4) # floats take 4 bytes

                # get dimensions
                cpos = f.tell()
                chunk = f.read(256)
                dpos = chunk.find(b"Dimensions")
                f.seek(cpos + dpos)
                chunk = f.read(98)
                dim1 = unpack(endianness + 'L', chunk[59:63])[0]
                dim2 = unpack(endianness + 'L', chunk[94:98])[0]

                # retrieve image
                image = np.zeros([int(narray)], order='F')
                for i in range(0, int(narray)):
                    image[i] = unpack(endianness + 'f', image_bytes[i*4:i*4+4])[0]
                try:
                    image.resize([dim2, dim1])
                except MemoryError:
                    print(f'({dim2}, {dim1})')
                    raise(MemoryError)
                if not first:
                    if verbose:
                        print("Thumbnail found: ({}, {})".format(dim2, dim1))
                    thumbnail = {"img": image, "dim": (dim2, dim1)}
                    first = True
                else:
                    if verbose:
                        print("Image found: ({}, {})".format(dim2, dim1))
                    raw = {"img": image, "dim": (dim2, dim1)}
                    break
                if verbose:
                    print("\ttlen: {}".format(tlen))
                    print("\tninfo: {}".format(ninfo))
                    print("\ttag data type: {}".format(dm4_tagdtypes[tdtype]))
                    print("\tdata type: {}".format(dm4_tagdtypes[dtype]))
                    print("\tnarray: {}".format(narray))
                    print("\tImage at position: {}".format(f.tell()))
                    print("\tDimensions: {}, {}".format(dim1, dim2))
            spos = f.tell()
    return raw, thumbnail

def convertDM4DirectoryToTiff(directory, destination=None, contrast=True, prefix='', verbose=False):
    """
        Take a directory containing DM4 images and saves them as TIF images
        with scale included in ImageJ format. Raw DM4 images do not necessarily 
        have high contrast but by default this function will write images with
        appreciable contrast.
        Inputs:
            destination: if not specified images will be written to directory
            contrast: if True will automatically adjust to have contrast (default: True)
            prefix: prefix to preappend to image filenames (default: '')
    """
    if destination == None:
        destination = directory
    # get total number of dm4 files
    if prefix == '':
        prefix_name = ''
    else:
        prefix_name = prefix + '_'
    num = 0
    for root, dirs, files in os.walk(directory):
        for name in files:
            if name[-3:] == 'dm4':
                num = num + 1
    # process dm4 files
    i = 0
    for root, dirs, files in os.walk(directory):
        for name in files:
            if name[-3:] == 'dm4':
                path = os.path.join(root, name)
                dest = destination + '\\' + prefix_name + name[:-3] + 'tif'
                if verbose:
                    print("Full input file path: {}".format(path))
                endianness = getDM4Endianness(path, verbose=verbose)
                scale, units = getDM4Scale(path, endianness=endianness, verbose=verbose)
                units = units.replace('µ', 'u').replace('μ', 'u')
                image, thumbnail = getDM4Image(path, endianness, verbose=verbose)
                norm_img = (image['img'] - np.amin(image['img']))/np.amax(image['img'] - np.amin(image['img']))
                if contrast:
                    hist, edges = np.histogram(norm_img, bins=256, density=True)
                    minedge = None
                    maxedge = None
                    tot = 0
                    for j in range(0, len(hist)-1):
                        tot = tot + hist[j]/256
                        if minedge == None and hist[j+1]-hist[j] != 0 and tot > .001:
                            minedge = edges[j]
                        if maxedge == None and hist[j+1]-hist[j] != 0 and tot > 1-1.5e-4:
                            maxedge = edges[j+1]
                    img = (norm_img-minedge)*255/(maxedge-minedge)
                    img = np.where(img > 255, 255, img)
                    img = np.where(img < 0, 0, img).astype(np.uint8, copy=False)
                else:
                    img = (norm_img*255).astype(np.uint8, copy=False)
                if verbose:
                    print("Maximum: {}\tMedian: {}\tMinimum: {}".format(np.amax(img), np.median(img), np.amin(img)))
                meta = {'unit': units}
                try:
                    tf.imwrite(dest, img, imagej=True, metadata=meta, resolution=(1/scale,1/scale))
                    if verbose:
                        print(f'Full output filepath: {dest}')
                except UnicodeEncodeError as exc:
                    warnings.warn(f"UnicodeEncodeError for file {name};\nMetadata:\n{meta};\n\tScale: {scale} {units};\nLikely tried to write a mu inside the unit.", UnicodeWarning)
                i = i + 1
                print("{}/{}".format(i, num))
    print("Conversions done.")

def convertDM4ToTiff(src, destination=None, verbose=False):
    """
        Take a DM4 image and saves it as a TIF image with scale included in ImageJ 
        format. The saved image does not necessarily have appreciable contrast
        Inputs:
            destination: if not specified images will be written to directory
    """
    if not os.path.isfile(src) or src[-3:] != 'dm4':
        return
    filename = os.path.basename(src)
    if destination == None:
        destination = src[:-len(filname)] + '\\' + filename[:-3] + 'tif'
    endianness = getDM4Endianness(src, verbose=verbose)
    scale = getDM4Scale(src, endianness=endianness, verbose=verbose)
    image, thumbnail = getDM4Image(src, endianness, verbose=verbose)
    norm_img = (image['img'] - np.amin(image['img']))/np.amax(image['img'] - np.amin(image['img']))
    img = (norm_img*128/np.median(norm_img)).astype(np.uint8)
    if verbose:
        print("Maximum: {}\tMedian: {}\tMinimum: {}".format(np.amax(img), np.median(img), np.amin(img)))
    meta = {'Info': 'ImageJ=1.53k\nunit=nm'}
    tf.imwrite(destination, img, imagej=True, metadata=meta, resolution=(1/scale,1/scale))
    print("Conversion done.")


