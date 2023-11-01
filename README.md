# OSIRIS_fix_scripts
Converts DM4 images to TIF images with encoded scale and fixes resolution issues from ESPRIT.

## DM4_processing.py
The FEI Osiris TEM saves DM4 files with Gatan Micrograph and supports the ability to save images from the files with a scale bar. By using the information from Prof. Chris Boothroyd's <a href="https://personal.ntu.edu.sg/cbb/info/dmformat/index.html">documentation</a> of DMx formats, one can extract the scale and save it into TIF file tags so that it's readable by ImageJ. This approach offers more control over image contrast, preserving scale without imposing a scale bar, and permitting more precise scale information. These functions do not change the original files in any way.

## exif_fix.py
For an unknown reason, some STEM EDX maps saved by ESPRIT as TIF files at UNL are saved with the incorrect resolutions, creating problems with some programs when trying to use or view them (particularly PowerPoint). This script runs over a directory and attempts to fix the resolutions. This script will change the original files, so I recommend working on copies in case your system works differently from ours.
