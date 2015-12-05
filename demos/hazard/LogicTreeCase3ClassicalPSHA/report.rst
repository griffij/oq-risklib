Classical PSHA with non-trivial logic tree (1 source model + relative uncertainties on G-R b value and maximum magnitude and 2 GMPEs per tectonic region type)
==============================================================================================================================================================

num_sites = 1

Parameters
----------
============================ =========
calculation_mode             classical
number_of_logic_tree_samples 0        
maximum_distance             200.0    
investigation_time           50.0     
ses_per_logic_tree_path      1        
truncation_level             3.0      
rupture_mesh_spacing         2.0      
complex_fault_mesh_spacing   2.0      
width_of_mfd_bin             0.1      
area_source_discretization   5.0      
random_seed                  23       
master_seed                  0        
concurrent_tasks             32       
============================ =========

Input files
-----------
======================= ============================================================
Name                    File                                                        
======================= ============================================================
gsim_logic_tree         `gmpe_logic_tree.xml <gmpe_logic_tree.xml>`_                
job_ini                 `job.ini <job.ini>`_                                        
source                  `source_model.xml <source_model.xml>`_                      
source_model_logic_tree `source_model_logic_tree.xml <source_model_logic_tree.xml>`_
======================= ============================================================

Composite source model
----------------------
=========== ========== ====================================== =============== ================ ===========
smlt_path   weight     source_model_file                      gsim_logic_tree num_realizations num_sources
=========== ========== ====================================== =============== ================ ===========
b11_b21_b31 0.11088900 `source_model.xml <source_model.xml>`_ complex(2,2)    4/4              1539       
b11_b21_b32 0.11088900 `source_model.xml <source_model.xml>`_ complex(2,2)    4/4              1544       
b11_b21_b33 0.11122200 `source_model.xml <source_model.xml>`_ complex(2,2)    4/4              1549       
b11_b22_b31 0.11088900 `source_model.xml <source_model.xml>`_ complex(2,2)    4/4              1539       
b11_b22_b32 0.11088900 `source_model.xml <source_model.xml>`_ complex(2,2)    4/4              1544       
b11_b22_b33 0.11122200 `source_model.xml <source_model.xml>`_ complex(2,2)    4/4              1549       
b11_b23_b31 0.11122200 `source_model.xml <source_model.xml>`_ complex(2,2)    4/4              1539       
b11_b23_b32 0.11122200 `source_model.xml <source_model.xml>`_ complex(2,2)    4/4              1544       
b11_b23_b33 0.11155600 `source_model.xml <source_model.xml>`_ complex(2,2)    4/4              1549       
=========== ========== ====================================== =============== ================ ===========

Required parameters per tectonic region type
--------------------------------------------
====== ================================= =========== ======================= =================
trt_id gsims                             distances   siteparams              ruptparams       
====== ================================= =========== ======================= =================
0      BooreAtkinson2008 ChiouYoungs2008 rx rjb rrup vs30measured z1pt0 vs30 ztor mag rake dip
1      Campbell2003 ToroEtAl2002         rjb rrup                            mag              
2      BooreAtkinson2008 ChiouYoungs2008 rx rjb rrup vs30measured z1pt0 vs30 ztor mag rake dip
3      Campbell2003 ToroEtAl2002         rjb rrup                            mag              
4      BooreAtkinson2008 ChiouYoungs2008 rx rjb rrup vs30measured z1pt0 vs30 ztor mag rake dip
5      Campbell2003 ToroEtAl2002         rjb rrup                            mag              
6      BooreAtkinson2008 ChiouYoungs2008 rx rjb rrup vs30measured z1pt0 vs30 ztor mag rake dip
7      Campbell2003 ToroEtAl2002         rjb rrup                            mag              
8      BooreAtkinson2008 ChiouYoungs2008 rx rjb rrup vs30measured z1pt0 vs30 ztor mag rake dip
9      Campbell2003 ToroEtAl2002         rjb rrup                            mag              
10     BooreAtkinson2008 ChiouYoungs2008 rx rjb rrup vs30measured z1pt0 vs30 ztor mag rake dip
11     Campbell2003 ToroEtAl2002         rjb rrup                            mag              
12     BooreAtkinson2008 ChiouYoungs2008 rx rjb rrup vs30measured z1pt0 vs30 ztor mag rake dip
13     Campbell2003 ToroEtAl2002         rjb rrup                            mag              
14     BooreAtkinson2008 ChiouYoungs2008 rx rjb rrup vs30measured z1pt0 vs30 ztor mag rake dip
15     Campbell2003 ToroEtAl2002         rjb rrup                            mag              
16     BooreAtkinson2008 ChiouYoungs2008 rx rjb rrup vs30measured z1pt0 vs30 ztor mag rake dip
17     Campbell2003 ToroEtAl2002         rjb rrup                            mag              
====== ================================= =========== ======================= =================

Realizations per (TRT, GSIM)
----------------------------

::

  <RlzsAssoc(36)
  0,BooreAtkinson2008: ['<0,b11_b21_b31,b11_b21,w=0.02772225>', '<1,b11_b21_b31,b11_b22,w=0.02772225>']
  0,ChiouYoungs2008: ['<2,b11_b21_b31,b12_b21,w=0.02772225>', '<3,b11_b21_b31,b12_b22,w=0.02772225>']
  1,Campbell2003: ['<1,b11_b21_b31,b11_b22,w=0.02772225>', '<3,b11_b21_b31,b12_b22,w=0.02772225>']
  1,ToroEtAl2002: ['<0,b11_b21_b31,b11_b21,w=0.02772225>', '<2,b11_b21_b31,b12_b21,w=0.02772225>']
  2,BooreAtkinson2008: ['<4,b11_b21_b32,b11_b21,w=0.02772225>', '<5,b11_b21_b32,b11_b22,w=0.02772225>']
  2,ChiouYoungs2008: ['<6,b11_b21_b32,b12_b21,w=0.02772225>', '<7,b11_b21_b32,b12_b22,w=0.02772225>']
  3,Campbell2003: ['<5,b11_b21_b32,b11_b22,w=0.02772225>', '<7,b11_b21_b32,b12_b22,w=0.02772225>']
  3,ToroEtAl2002: ['<4,b11_b21_b32,b11_b21,w=0.02772225>', '<6,b11_b21_b32,b12_b21,w=0.02772225>']
  4,BooreAtkinson2008: ['<8,b11_b21_b33,b11_b21,w=0.0278055>', '<9,b11_b21_b33,b11_b22,w=0.0278055>']
  4,ChiouYoungs2008: ['<10,b11_b21_b33,b12_b21,w=0.0278055>', '<11,b11_b21_b33,b12_b22,w=0.0278055>']
  5,Campbell2003: ['<9,b11_b21_b33,b11_b22,w=0.0278055>', '<11,b11_b21_b33,b12_b22,w=0.0278055>']
  5,ToroEtAl2002: ['<8,b11_b21_b33,b11_b21,w=0.0278055>', '<10,b11_b21_b33,b12_b21,w=0.0278055>']
  6,BooreAtkinson2008: ['<12,b11_b22_b31,b11_b21,w=0.02772225>', '<13,b11_b22_b31,b11_b22,w=0.02772225>']
  6,ChiouYoungs2008: ['<14,b11_b22_b31,b12_b21,w=0.02772225>', '<15,b11_b22_b31,b12_b22,w=0.02772225>']
  7,Campbell2003: ['<13,b11_b22_b31,b11_b22,w=0.02772225>', '<15,b11_b22_b31,b12_b22,w=0.02772225>']
  7,ToroEtAl2002: ['<12,b11_b22_b31,b11_b21,w=0.02772225>', '<14,b11_b22_b31,b12_b21,w=0.02772225>']
  8,BooreAtkinson2008: ['<16,b11_b22_b32,b11_b21,w=0.02772225>', '<17,b11_b22_b32,b11_b22,w=0.02772225>']
  8,ChiouYoungs2008: ['<18,b11_b22_b32,b12_b21,w=0.02772225>', '<19,b11_b22_b32,b12_b22,w=0.02772225>']
  9,Campbell2003: ['<17,b11_b22_b32,b11_b22,w=0.02772225>', '<19,b11_b22_b32,b12_b22,w=0.02772225>']
  9,ToroEtAl2002: ['<16,b11_b22_b32,b11_b21,w=0.02772225>', '<18,b11_b22_b32,b12_b21,w=0.02772225>']
  10,BooreAtkinson2008: ['<20,b11_b22_b33,b11_b21,w=0.0278055>', '<21,b11_b22_b33,b11_b22,w=0.0278055>']
  10,ChiouYoungs2008: ['<22,b11_b22_b33,b12_b21,w=0.0278055>', '<23,b11_b22_b33,b12_b22,w=0.0278055>']
  11,Campbell2003: ['<21,b11_b22_b33,b11_b22,w=0.0278055>', '<23,b11_b22_b33,b12_b22,w=0.0278055>']
  11,ToroEtAl2002: ['<20,b11_b22_b33,b11_b21,w=0.0278055>', '<22,b11_b22_b33,b12_b21,w=0.0278055>']
  12,BooreAtkinson2008: ['<24,b11_b23_b31,b11_b21,w=0.0278055>', '<25,b11_b23_b31,b11_b22,w=0.0278055>']
  12,ChiouYoungs2008: ['<26,b11_b23_b31,b12_b21,w=0.0278055>', '<27,b11_b23_b31,b12_b22,w=0.0278055>']
  13,Campbell2003: ['<25,b11_b23_b31,b11_b22,w=0.0278055>', '<27,b11_b23_b31,b12_b22,w=0.0278055>']
  13,ToroEtAl2002: ['<24,b11_b23_b31,b11_b21,w=0.0278055>', '<26,b11_b23_b31,b12_b21,w=0.0278055>']
  14,BooreAtkinson2008: ['<28,b11_b23_b32,b11_b21,w=0.0278055>', '<29,b11_b23_b32,b11_b22,w=0.0278055>']
  14,ChiouYoungs2008: ['<30,b11_b23_b32,b12_b21,w=0.0278055>', '<31,b11_b23_b32,b12_b22,w=0.0278055>']
  15,Campbell2003: ['<29,b11_b23_b32,b11_b22,w=0.0278055>', '<31,b11_b23_b32,b12_b22,w=0.0278055>']
  15,ToroEtAl2002: ['<28,b11_b23_b32,b11_b21,w=0.0278055>', '<30,b11_b23_b32,b12_b21,w=0.0278055>']
  16,BooreAtkinson2008: ['<32,b11_b23_b33,b11_b21,w=0.027889>', '<33,b11_b23_b33,b11_b22,w=0.027889>']
  16,ChiouYoungs2008: ['<34,b11_b23_b33,b12_b21,w=0.027889>', '<35,b11_b23_b33,b12_b22,w=0.027889>']
  17,Campbell2003: ['<33,b11_b23_b33,b11_b22,w=0.027889>', '<35,b11_b23_b33,b12_b22,w=0.027889>']
  17,ToroEtAl2002: ['<32,b11_b23_b33,b11_b21,w=0.027889>', '<34,b11_b23_b33,b12_b21,w=0.027889>']>

Number of ruptures per tectonic region type
-------------------------------------------
=========== =====
#TRT models 18   
#sources    13896
#ruptures   58176
=========== =====

================ ====== ======================== =========== ============
source_model     trt_id trt                      num_sources num_ruptures
================ ====== ======================== =========== ============
source_model.xml 0      Active Shallow Crust     1334        1334        
source_model.xml 1      Stable Continental Crust 205         4100        
source_model.xml 2      Active Shallow Crust     1339        1339        
source_model.xml 3      Stable Continental Crust 205         5125        
source_model.xml 4      Active Shallow Crust     1344        1344        
source_model.xml 5      Stable Continental Crust 205         6150        
source_model.xml 6      Active Shallow Crust     1334        1334        
source_model.xml 7      Stable Continental Crust 205         4100        
source_model.xml 8      Active Shallow Crust     1339        1339        
source_model.xml 9      Stable Continental Crust 205         5125        
source_model.xml 10     Active Shallow Crust     1344        1344        
source_model.xml 11     Stable Continental Crust 205         6150        
source_model.xml 12     Active Shallow Crust     1334        1334        
source_model.xml 13     Stable Continental Crust 205         4100        
source_model.xml 14     Active Shallow Crust     1339        1339        
source_model.xml 15     Stable Continental Crust 205         5125        
source_model.xml 16     Active Shallow Crust     1344        1344        
source_model.xml 17     Stable Continental Crust 205         6150        
================ ====== ======================== =========== ============

Expected data transfer for the sources
--------------------------------------
================================== =======
Number of tasks to generate        45     
Estimated sources to send          46.9 MB
Estimated hazard curves to receive 13 KB  
================================== =======