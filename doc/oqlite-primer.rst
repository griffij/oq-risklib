The OQ-Lite Primer
=====================================

`oq-lite` is a command-line tool to run hazard and risk calculations
on a single machine (be it a server or a laptop) bypassing the
OpenQuake Engine.

The big advantage of using `oq-lite` is that it is much easier to
install than the OpenQuake Engine and runs on many more platforms, in
particular on Windows and Mac OS X. Moreover `oq-lite` is faster and
more efficient than the engine. On the other hands, it uses exactly
the same underlying OpenQuake libraries and its results are guaranteed
to be consistent with the ones provided by the engine.

`oq-lite` is a younger tool than the engine and for this reason it is
not feature-complete nor as battle-tested. Still, unless you have
a cluster of machines, `oq-lite` should be preferred over the engine.

Installing oq-lite
-----------------------

Right now `oq-lite` is still in active development and moving at a
fast pace. For this reason the recommended way to get it is to
*install oq-lite from sources on an isolated virtualenv*. In this
way you can be sure to avoid conflicts and/or confusions with the
engine, that maybe installed on your system with a version older
and inconsistent with the latest oq-lite.
Here are the instructions, assuming you want to install into a directory
called `oqsource`::

   $ venv oqsource
   $ cd oqsource
   $ bin/activate
   $ pip install pip
   $ pip install futures
   $ pip install http://ftp.openquake.org/python-wheels/numpy-1.8.2-cp27-none-linux_x86_64.whl
   $ pip install http://ftp.openquake.org/python-wheels/scipy-0.16.0-cp27-none-linux_x86_64.whl
   $ pip install http://ftp.openquake.org/python-wheels/Cython-0.22.1-cp27-none-linux_x86_64.whl
   $ pip install http://ftp.openquake.org/python-wheels/Shapely-1.5.9-py2-none-any.whl
   $ pip install http://ftp.openquake.org/python-wheels/h5py-2.2.1-cp27-none-linux_x86_64.whl
   $ pip install https://github.com/gem/oq-hazardlib/archive/master.zip
   $ python setup.py develop

Using oq-lite
-------------------------------------

`oq-lite` provides several commands to perform different kind of
operations.  The most important one is `run` that allows to run
calculations. The OpenQuake suite comes with a suite of demos that you
can run to get some experience.  The demos can be found in the
directory `oq-lite/demos` and are split in hazard and risk
subdirectories. The first demo in alphabetical order is the 
`AreaSourceClassicalPSHA` demo. Let's start from it:

$ cd oq-lite/demos/hazard/AreaSourceClassicalPSHA/

Inside the directory there are several files, which are described in
the OpenQuake manual. The most important one is the configuration file
`job.ini`. Running a computation is a simple as giving the following
command:

$ oq-lite run job.ini
...
See the output with hdfview /home/michele/oqdata/calc_3096.hdf5

The calculator will read all of the needed files (in particular the source
model and the logic trees for sources and GMPEs) and will produce hazard
curves in parallel, by using up to 10 cores. The source model
in this demo contains a single AreaSource which is split in 205 PointSource
objects::

  from openquake.commonlib import readinput
  oq = readinput.get_oqparam('job.ini')
  sitecol = readinput.get_site_collection(oq)
  csm = readinput.get_composite_source_model(oq, sitecol)
  sources = csm.get_sources()
  assert len(sources) == 205

The number of sources generated is determined by the parameter
`area_source_discretization`: if you increase it, you will produce
less point sources.
  
The `job.ini` file contains a line

  `concurrent_tasks = 10`

therefore `oq-lite` will try to split the whole computation in 10 tasks.
Actually the number in `concurrent_tasks` is just a *hint* the real number
of tasks spawned can be different. In this case `oq-lite` will spawn 9 tasks
(notice that this number is implementation-specific and subject to change)

$ oq-lite show -1 source_chunks
num_srcs:uint32:,weight:float32:
24,4.80000019E+00
24,4.80000019E+00
24,4.80000019E+00
24,4.80000019E+00
24,4.80000019E+00
24,4.80000019E+00
24,4.80000019E+00
24,4.80000019E+00
13,2.59999990E+00

The first task gets the first 24 sources, the second task the second
24 sources, the third task the third 24 sources and so on. At the end
the last task (the nineth) will get the 13 remaining sources.
If your machine has less than 9 cores (say 4 cores) each core will get
more than one task; if you machine has more than 9 cores some cores
will get wasted and will not run anything. In that case change the
`job.ini` and increase the parameter `concurrent_tasks`; for instance,
if you increase it to 32 you can generate 21 tasks.

The precalculation report
-------------------------------------------

It is possible to know how many tasks will be generated without running
the entire computation:

10 x 20 + 5 sources

oq-lite info -r job.ini

Open the report and search for *Number of tasks to generate*.
The report will also tells you very important information like the following
one::

  Estimated sources to send          500.39 KB
  Estimated hazard curves to receive 27 MB    

This is information is extremely useful for large computations. If the
estimated sources to send and/or to receive exceed the gigabyte, then
the computation can be impossible to run on your machine, depening on
your memory constraint. In such a case you should get a better machine
of think of ways to reduce the computation (this will be discussed
extensively later on).

The reports contains all kind of information. For instance the number
of sites (2112 in this example): the number is controlled by the
`region_grid_spacing` since the demo uses the grid functionality of
OpenQuake.
