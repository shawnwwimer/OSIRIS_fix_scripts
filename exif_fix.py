#!/usr/bin/env python

"""
    Some EDX map images saved by ESPRIT for the FEI Osiris TEM at my institution 
    are saved with incorrect resolutions, posing issues with some programs (notably
    PowerPoint). This script iterates over all TIF images in a directory and fixes
    the tags.
"""


import os
import exifread
from PIL import Image
import piexif

directory = r'STEM'

for (dirpath, dirnames, filenames) in os.walk(directory):
    for filename in filenames:
        if filename.endswith('.tif'):
            fullname = os.sep.join([dirpath, filename])
        
            with open(fullname, 'rb') as f:
                tags = exifread.process_file(f)
        
            keys = ["Image XResolution", "Image YResolution"]
            
            with Image.open(fullname) as im:
                try:
                    tags = piexif.load(fullname)
                except ValueError:
                    continue
            
                w,h = im.size
                try:
                    xres = tags['0th'][piexif.ImageIFD.XResolution][0]
                except KeyError:
                    print(f'File {fullname} did not have xres tag; skipping.')
                    continue

                try:
                    yres = tags['0th'][piexif.ImageIFD.YResolution][0]
                except KeyError:
                    print(f'File {fullname} did not have yres tag; skipping.')
                    continue
                
                print(f"{fullname} (xres, yres): ({xres}, {yres})")
                
                if not (xres > 10*yres or 10*xres < yres):
                    continue
            
                sfile = fullname[:-4] + '.tif'
                try:
                    im.save(sfile, resolution=1)
                except ValueError:
                    print("ValueError on save.")
                except OSError:
                    print("OSError on save.")