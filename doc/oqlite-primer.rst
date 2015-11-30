The OQ-Lite Primer
=====================================


`oq-lite` is a command-line tool to run hazard and risk calculation by
using directly the OpenQuake libraries and bypassing the OpenQuake Engine.

The big advantage of using `oq-lite` is that it is much easier to
install than the OpenQuake Engine and runs on many more platforms, in
particular on Windows and Mac OS X. Moreover `oq-lite` is faster and
more efficient than the engine.

`oq-lite` is a younger tool than the engine and for this reason it is
not feature-complete nor as battle-tested. Still, unless you have
a cluster of machines `oq-lite` should be preferred over the engine.

Installing oq-lite
-----------------------

1. The recommended way is to *install oq-lite from sources*. In other
words, do not install it from packages and
*make sure that you do not have the engine installed!*



  - pip install futures
  - pip install http://ftp.openquake.org/python-wheels/numpy-1.8.2-cp27-none-linux_x86_64.whl
  - pip install http://ftp.openquake.org/python-wheels/scipy-0.16.0-cp27-none-linux_x86_64.whl
  - pip install http://ftp.openquake.org/python-wheels/Cython-0.22.1-cp27-none-linux_x86_64.whl
  - pip install http://ftp.openquake.org/python-wheels/Shapely-1.5.9-py2-none-any.whl
  - pip install http://ftp.openquake.org/python-wheels/h5py-2.2.1-cp27-none-linux_x86_64.whl
  - pip install https://github.com/gem/oq-hazardlib/archive/master.zip
  - python setup.py install
